"""
src/collision_logic.py — Motor de Deteccion de Colisiones v3

Fusion multi-senal (7 indicadores) + deteccion dashcam mejorada.

Cambio clave v3: Deteccion de colision dashcam basada en 3 senales:
  1. CRECIMIENTO RAPIDO del bounding box (vehiculo acercandose)
  2. PERDIDA DE TRACKING (vehiculo desaparece durante impacto)
  3. REAPARICION CON CAMBIO BRUSCO (post-impacto)

Estos 3 patrones combinados son diagnosticos de impacto frontal dashcam:
el vehiculo de enfrente crece, llena la camara (YOLO lo pierde), y cuando
reaparece el carro ya esta en otra posicion/velocidad.

Referencias:
  - ByteTrack (Zhang et al., ECCV 2022)
  - CADP (Shah et al., AVSS 2018)
  - DoTA (Yao et al., IEEE TPAMI 2022)
  - ISO 22839: Time-to-Collision standard
"""

import numpy as np
from collections import defaultdict
from config import (
    COLLISION_IOU_THRESHOLD, COLLISION_MIN_FRAMES,
    COLLISION_VELOCITY_CHANGE, COLLISION_SCORE_THRESHOLD,
    PERSISTENCE_FRAMES, EVENT_COOLDOWN_FRAMES,
    CONTACT_DISTANCE_RATIO, CONTACT_IOU_THRESHOLD,
    SUDDEN_SPEED_DROP_RATIO, FRAME_HISTORY,
    TTC_CRITICAL_FRAMES, TTC_MIN_CLOSING_RATE,
    TRACK_MIN_AGE, TRACK_MAX_MISSED,
    SINGLE_VEHICLE_CRASH_ENABLED,
    SINGLE_VEHICLE_MIN_AREA_RATIO,
    SINGLE_VEHICLE_MIN_SPEED_DROP,
)
from src.utils import get_iou, get_box_distance, get_box_diagonal

# -- Estado global (persistencia entre frames) --
_pair_streak   = defaultdict(int)
_pair_cooldown = defaultdict(int)

# Estado para deteccion dashcam
_track_area_history = defaultdict(list)  # {tid: [(frame, area_ratio), ...]}
_track_lost_at = {}                       # {tid: (frame_lost, last_area_ratio, last_speed)}
_dashcam_cooldown = 0

# Resolucion del video
_frame_width  = 1280
_frame_height = 720


def set_frame_dimensions(w: int, h: int):
    """Llamar al inicio de cada video para calculos de area relativa."""
    global _frame_width, _frame_height
    _frame_width  = max(1, w)
    _frame_height = max(1, h)


def reset_state():
    """Reinicia el estado global (llamar al procesar un nuevo video)."""
    global _dashcam_cooldown
    _pair_streak.clear()
    _pair_cooldown.clear()
    _track_area_history.clear()
    _track_lost_at.clear()
    _dashcam_cooldown = 0


# ======================================================================= #
#  Senal 7: Time-to-Collision (TTC) [ISO 22839]                           #
# ======================================================================= #

def compute_ttc(track1, track2) -> float:
    """
    Tiempo hasta colision en frames basado en la tasa de acercamiento.
    TTC = distancia_actual / tasa_de_acercamiento
    """
    boxes1 = list(track1.boxes)
    boxes2 = list(track2.boxes)

    if len(boxes1) < 2 or len(boxes2) < 2:
        return float('inf')

    d_current  = get_box_distance(boxes1[-1], boxes2[-1])
    d_previous = get_box_distance(boxes1[-2], boxes2[-2])
    closing_rate = d_previous - d_current

    if closing_rate >= TTC_MIN_CLOSING_RATE:
        ttc = d_current / closing_rate
        return max(0.0, float(ttc))

    return float('inf')


# ======================================================================= #
#  Deteccion de colision entre PARES de vehiculos                         #
# ======================================================================= #

def detect_collision_advanced(track1, track2, frame_history: int = None):
    """
    Detecta colision entre dos tracks DISTINTOS usando fusion ponderada
    de 7 senales cinematicas.

    Returns:
        (is_collision: bool, score: float, severity: str)
    """
    if frame_history is None:
        frame_history = FRAME_HISTORY

    boxes1 = list(track1.boxes)
    boxes2 = list(track2.boxes)

    if len(boxes1) < 2 or len(boxes2) < 2:
        return False, 0.0, ""

    curr_box1 = track1.get_current_box()
    curr_box2 = track2.get_current_box()

    # Filtro: caja siempre solapada = mismo objeto YOLO
    iou = get_iou(curr_box1, curr_box2)
    if iou > 0.80:
        limit = min(8, len(boxes1), len(boxes2))
        alguna_vez_separados = any(
            get_iou(boxes1[-i], boxes2[-i]) < 0.20
            for i in range(2, limit)
        )
        if not alguna_vez_separados:
            return False, 0.0, ""

    # -- Senal 1: IoU --
    iou_score = float(iou)

    # -- Senal 2: Distancia normalizada --
    distance      = get_box_distance(curr_box1, curr_box2)
    mean_diag     = max(1.0, (get_box_diagonal(curr_box1) + get_box_diagonal(curr_box2)) / 2.0)
    dist_threshold = mean_diag * CONTACT_DISTANCE_RATIO
    distance_score = max(0.0, 1.0 - distance / (dist_threshold + 1e-6))

    contacto_fisico = (iou > COLLISION_IOU_THRESHOLD) or (distance <= dist_threshold)

    # -- Senal 3: Velocidad relativa --
    v1 = track1.get_velocity()
    v2 = track2.get_velocity()
    vel_diff  = np.sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)
    vel_score = min(1.0, vel_diff / 10.0) if vel_diff > COLLISION_VELOCITY_CHANGE else 0.0

    # -- Senal 4: Persistencia --
    n_hist = min(frame_history, len(boxes1), len(boxes2))
    consecutive_contact = 0
    for i in range(n_hist):
        b1 = boxes1[-(i + 1)]
        b2 = boxes2[-(i + 1)]
        in_contact = (
            get_iou(b1, b2) > (COLLISION_IOU_THRESHOLD * 0.5) or
            get_box_distance(b1, b2) <= dist_threshold
        )
        if in_contact:
            consecutive_contact += 1
        else:
            break
    iou_persistence = min(1.0, consecutive_contact / max(COLLISION_MIN_FRAMES, 1))

    # -- Senal 5: Caida brusca de velocidad --
    sp1_hist = track1.get_historical_speed(frame_history)
    sp2_hist = track2.get_historical_speed(frame_history)
    sp1_curr = track1.get_current_speed()
    sp2_curr = track2.get_current_speed()

    speed_drop_score = 0.0
    max_drop = 0.0
    if sp1_hist > 3.0 or sp2_hist > 3.0:
        drop1 = (sp1_hist - sp1_curr) / sp1_hist if sp1_hist > 0 else 0.0
        drop2 = (sp2_hist - sp2_curr) / sp2_hist if sp2_hist > 0 else 0.0
        max_drop = max(drop1, drop2)
        if max_drop > SUDDEN_SPEED_DROP_RATIO:
            speed_drop_score = min(1.0, max_drop)

    # -- Senal 6: Cambio angular --
    angle_score = 0.0
    for track in (track1, track2):
        vec_hist = np.array(track.get_velocity_vector(frame_history))
        vec_curr = np.array(track.get_velocity_vector(2))
        if np.linalg.norm(vec_hist) > 1.0 and np.linalg.norm(vec_curr) > 1.0:
            cos_t = np.dot(vec_hist, vec_curr) / (
                np.linalg.norm(vec_hist) * np.linalg.norm(vec_curr)
            )
            angle_diff = np.arccos(np.clip(cos_t, -1.0, 1.0)) * (180.0 / np.pi)
            angle_score = max(angle_score, angle_diff / 45.0)

    # -- Senal 7: TTC --
    ttc = compute_ttc(track1, track2)
    ttc_score = max(0.0, 1.0 - ttc / TTC_CRITICAL_FRAMES) if ttc < float('inf') else 0.0

    # -- Fusion ponderada --
    weights = [0.06, 0.06, 0.08, 0.12, 0.30, 0.18, 0.20]
    signals = [
        iou_score,
        distance_score,
        vel_score,
        iou_persistence,
        speed_drop_score,
        min(1.0, angle_score),
        ttc_score,
    ]
    collision_score = sum(w * s for w, s in zip(weights, signals))

    is_collision = (
        contacto_fisico and
        collision_score > COLLISION_SCORE_THRESHOLD and
        consecutive_contact >= COLLISION_MIN_FRAMES
    )

    if max_drop > 0.70 or angle_score > 0.80 or (ttc < 2 and ttc_score > 0.8):
        severity = "Severo"
    elif max_drop > 0.50 or angle_score > 0.40 or ttc_score > 0.6:
        severity = "Moderado"
    else:
        severity = "Leve"

    return is_collision, float(collision_score), severity


# ======================================================================= #
#  Deteccion DASHCAM: impacto frontal basado en patron de crecimiento     #
# ======================================================================= #

def _get_box_area(box):
    """Area del bounding box."""
    return max(0, (box[2] - box[0]) * (box[3] - box[1]))


def detect_dashcam_collision(tracks: dict, current_frame: int) -> list:
    """
    Detecta colision dashcam DURANTE el impacto, no despues.

    PATRON REAL (ccd_crash_01.mp4, 10fps):
    =======================================
    Frame 25-27: Track 30 activo, area ~8%, velocidad ~28 px/f
    Frame 28:    YOLO pierde el track (carro llena la camara = IMPACTO)
    Frame 29:    frames_since_update = 2
    Frame 30:    frames_since_update = 3 → DISPARO DE ALERTA AQUI
    Frame 31-36: Alerta persiste (carro sigue llenando camara)
    Frame 37:    Track reaparece (post-impacto)

    LOGICA:
    1. Cuando frames_since_update == 1 (primer miss), REGISTRAR el track
       con su area, velocidad, y historial de crecimiento.
    2. Cuando frames_since_update == 3 (miss confirmado), DISPARAR la
       colision si tenia area grande + velocidad + crecimiento.
    3. La alerta persiste hasta EVENT_COOLDOWN_FRAMES.

    Returns:
        list de tuplas (tid, tid, frame, confidence, severity, ttc)
    """
    global _dashcam_cooldown

    if not SINGLE_VEHICLE_CRASH_ENABLED:
        return []

    if _dashcam_cooldown > 0:
        _dashcam_cooldown -= 1
        return []

    collisions = []
    frame_area = max(1, _frame_width * _frame_height)

    for tid, track in tracks.items():
        box = track.get_current_box()
        area = _get_box_area(box)
        area_ratio = area / frame_area

        # Registrar historial de area para este track (ANTES del filtro age para capturar tamanos iniciales)
        _track_area_history[tid].append((current_frame, area_ratio))
        if len(_track_area_history[tid]) > 15:
            _track_area_history[tid] = _track_area_history[tid][-15:]

        if track.age < 2:
            continue

        hist = _track_area_history[tid]

        # ============================================================
        # PASO 1: Registrar track en PRIMER o SEGUNDO MISS
        # ============================================================
        # Se registra en missed==1 o missed==2 (el primero que cumpla age>=2).
        # En ccd_crash_01, track 30 tiene age=1 en missed=1 (no pasa),
        # pero age=2 en missed=2 (pasa). Sin esto no se registra nunca.
        if (track.frames_since_update in (1, 2) and
                area_ratio >= SINGLE_VEHICLE_MIN_AREA_RATIO and
                tid not in _track_lost_at):

            sp_h = track.get_historical_speed(FRAME_HISTORY)

            # Calcular si hubo crecimiento explosivo reciente (vehiculo se acercaba rapido)
            growth_happened = False
            if len(hist) >= 3:
                recent_hist = hist[-7:]
                earliest_ar = recent_hist[0][1]
                peak_ar = max(h[1] for h in recent_hist)
                if earliest_ar > 0.005:
                    total_growth = (peak_ar - earliest_ar) / earliest_ar
                    growth_happened = total_growth > 0.15  # crecio >= 15% en ultimos frames

            _track_lost_at[tid] = {
                'frame': current_frame,
                'area_ratio': area_ratio,
                'speed': sp_h,
                'growth': growth_happened,
            }

        # ============================================================
        # PASO 2: DISPARAR colision cuando loss se confirma (>=3 frames)
        # ============================================================
        # El track sigue en el diccionario pero YOLO no lo actualiza.
        # Cuando frames_since_update llega a 3, sabemos que el vehiculo
        # realmente desaparecio (llena la camara = impacto).
        #
        # Condiciones (ya validadas en PASO 1 al registrar):
        #  - Area >= umbral (vehiculo era prominente en pantalla)
        #  - Velocidad > 2 px/f (no estaba parado)
        #  - 3 frames perdidos = confirmacion de tracking loss
        if (track.frames_since_update == 3 and tid in _track_lost_at):

            info = _track_lost_at[tid]
            lost_ar = info['area_ratio']
            lost_speed = info['speed']
            growth = info['growth']

            # Condiciones para confirmar colision dashcam:
            #  - Area >= umbral (vehiculo era prominente en pantalla)
            #  - Velocidad > 2 px/f (no estaba parado)
            #  - Crecimiento detectado O el vehiculo llenaba >10% de pantalla
            if (lost_ar >= SINGLE_VEHICLE_MIN_AREA_RATIO and
                    lost_speed > 2.0 and
                    (growth or lost_ar > 0.10)):
                conf = min(1.0, max(lost_ar * 8.0, lost_speed / 30.0))
                severity = "Severo" if lost_speed > 15.0 else "Moderado"
                collisions.append((tid, tid, current_frame,
                                   conf, severity, float('inf')))
                _dashcam_cooldown = EVENT_COOLDOWN_FRAMES
                del _track_lost_at[tid]
                break

        # ============================================================
        # PASO 3: Backup — Reaparicion con cambio brusco post-impacto
        # ============================================================
        # Si el paso 2 no disparo (quizas no hubo crecimiento),
        # detectar por cambio brusco de velocidad al reaparecer.
        if (track.frames_since_update == 0 and tid in _track_lost_at):
            info = _track_lost_at[tid]
            frames_lost = current_frame - info['frame']

            is_crash = False
            if frames_lost >= 3 and info['area_ratio'] >= SINGLE_VEHICLE_MIN_AREA_RATIO:
                sp_c = track.get_current_speed()
                sp_h = track.get_historical_speed(FRAME_HISTORY)

                if sp_h > 2.0:
                    # Drop is only valid if speed decreased
                    drop = (sp_h - sp_c) / sp_h
                    if drop > SINGLE_VEHICLE_MIN_SPEED_DROP:
                        conf = min(1.0, drop)
                        severity = "Severo" if drop > 0.70 else "Moderado"
                        collisions.append((tid, tid, current_frame,
                                           conf, severity, float('inf')))
                        _dashcam_cooldown = EVENT_COOLDOWN_FRAMES
                        is_crash = True
                        
            # Limpiamos el registro de perdida porque el track ya reaparecio
            del _track_lost_at[tid]
            if is_crash:
                break

    # Limpiar tracks perdidos muy viejos (> 20 frames)
    stale = [tid for tid, info in _track_lost_at.items()
             if current_frame - info['frame'] > 20]
    for tid in stale:
        del _track_lost_at[tid]

    return collisions


# ======================================================================= #
#  Deteccion legacy de vehiculo unico (mantenida por compatibilidad)      #
# ======================================================================= #

def detect_single_vehicle_crash(track, frame_height: int = None,
                                 frame_width: int = None):
    """
    Detecta accidente en un solo vehiculo por caida brusca de velocidad.
    Complementa detect_dashcam_collision para casos donde el track
    NO se pierde pero si frena bruscamente.
    """
    if not SINGLE_VEHICLE_CRASH_ENABLED:
        return False, 0.0, ""

    if len(track.boxes) < 3:
        return False, 0.0, ""

    fh = frame_height or _frame_height
    fw = frame_width  or _frame_width
    frame_area = max(1, fh * fw)

    box        = track.get_current_box()
    area       = _get_box_area(box)
    area_ratio = area / frame_area

    if area_ratio < SINGLE_VEHICLE_MIN_AREA_RATIO:
        return False, 0.0, ""

    sp_h = track.get_historical_speed(FRAME_HISTORY)
    sp_c = track.get_current_speed()

    if sp_h < 2.0:
        return False, 0.0, ""

    drop = (sp_h - sp_c) / sp_h if sp_h > 0 else 0.0
    if drop < SINGLE_VEHICLE_MIN_SPEED_DROP:
        return False, 0.0, ""

    severity = "Severo" if drop > 0.70 else "Moderado"
    return True, min(1.0, float(drop)), severity


# ======================================================================= #
#  Funcion publica: analyze_collisions                                    #
# ======================================================================= #

def analyze_collisions(tracks: dict, current_frame: int = 0) -> list:
    """
    Analiza todos los tracks activos y detecta colisiones.

    Combina 3 metodos de deteccion:
      1. Colision entre PARES de vehiculos distintos (fusion 7 senales)
      2. Deteccion DASHCAM (crecimiento + perdida de tracking)
      3. Vehiculo unico con caida brusca de velocidad

    Returns:
        list de tuplas (tid1, tid2, frame_num, confidence, severity, ttc)
    """
    collisions = []

    # Decrementar cooldowns de pares
    for pair in list(_pair_cooldown.keys()):
        if _pair_cooldown[pair] > 0:
            _pair_cooldown[pair] -= 1
        if _pair_cooldown[pair] <= 0:
            del _pair_cooldown[pair]

    # ============================================================
    # METODO 1: Deteccion DASHCAM (el mas importante para estos videos)
    # ============================================================
    dashcam_hits = detect_dashcam_collision(tracks, current_frame)
    collisions.extend(dashcam_hits)

    # Si ya detectamos dashcam collision, no necesitamos los otros metodos
    if collisions:
        return collisions

    # Tracks validos para metodos 2 y 3
    valid = {
        tid: t for tid, t in tracks.items()
        if t.age >= TRACK_MIN_AGE and t.frames_since_update <= TRACK_MAX_MISSED
    }

    # ============================================================
    # METODO 2: Vehiculo unico con caida brusca de velocidad
    # ============================================================
    for tid, track in valid.items():
        is_crash, conf, severity = detect_single_vehicle_crash(track)
        if is_crash:
            pair = (int(tid), int(tid))
            _pair_streak[pair] += 1
            if (_pair_streak[pair] >= PERSISTENCE_FRAMES and
                    not _pair_cooldown.get(pair, 0)):
                collisions.append((tid, tid, current_frame, conf, severity, float('inf')))
                _pair_cooldown[pair] = EVENT_COOLDOWN_FRAMES
                _pair_streak[pair] = 0
        else:
            single_pair = (int(tid), int(tid))
            _pair_streak[single_pair] = max(0, _pair_streak[single_pair] - 1)

    # ============================================================
    # METODO 3: Colisiones entre pares de vehiculos DISTINTOS
    # ============================================================
    track_ids = sorted(valid.keys())
    for i in range(len(track_ids)):
        for j in range(i + 1, len(track_ids)):
            tid1, tid2 = track_ids[i], track_ids[j]
            if tid1 == tid2:
                continue

            pair = (min(int(tid1), int(tid2)), max(int(tid1), int(tid2)))
            if _pair_cooldown.get(pair, 0) > 0:
                continue

            track1, track2 = valid[tid1], valid[tid2]
            is_col, conf, severity = detect_collision_advanced(track1, track2)

            if is_col:
                _pair_streak[pair] += 1
            else:
                _pair_streak[pair] = max(0, _pair_streak[pair] - 1)

            if _pair_streak[pair] >= PERSISTENCE_FRAMES:
                ttc = compute_ttc(track1, track2)
                collisions.append((tid1, tid2, current_frame, conf, severity, ttc))
                _pair_cooldown[pair] = EVENT_COOLDOWN_FRAMES
                _pair_streak[pair] = 0

    return collisions
