"""
src/collision_logic.py — Motor de Detección de Colisiones

Implementa análisis multi-señal para detectar colisiones vehiculares:
  1. IoU (solapamiento de cajas)
  2. Distancia normalizada entre centros
  3. Velocidad relativa entre objetos
  4. Persistencia temporal (frames consecutivos)
  5. Caída brusca de velocidad (impacto inelástico)
  6. Cambio angular de trayectoria
  7. Time-to-Collision / TTC (aproximación estándar ISO 22839)

Referencia metodológica:
  - akshat4703/accident_prediction: fusión de señales geométricas y cinemáticas
  - CADP (Shah et al.): análisis espacio-temporal de accidentes en CCTV
  - DoTA (Yao et al.): tratamiento de accidentes como eventos temporales, no frames aislados
  - ISO 22839: definición estándar de Time-to-Collision
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
)
from src.utils import get_iou, get_box_distance, get_box_diagonal


# ── Estado global (persistencia entre frames) ───────────────────────────
_pair_streak   = defaultdict(int)   # {(id1,id2): frames_consecutivos_con_señal}
_pair_cooldown = defaultdict(int)   # {(id1,id2): frames_restantes_de_cooldown}


def reset_state():
    """Reinicia el estado global (llamar al procesar un nuevo video)."""
    _pair_streak.clear()
    _pair_cooldown.clear()


# ======================================================================= #
#  Señal 7: Time-to-Collision (TTC)                                        #
# ======================================================================= #

def compute_ttc(track1, track2) -> float:
    """
    Estima el tiempo hasta colisión en frames basado en la tasa de acercamiento.

    El TTC es la métrica estándar en sistemas ADAS (ISO 22839). Se calcula como:
        TTC = distancia_actual / tasa_de_acercamiento

    Returns:
        TTC en frames. float('inf') si los objetos no se acercan.
    """
    boxes1 = list(track1.boxes)
    boxes2 = list(track2.boxes)

    if len(boxes1) < 2 or len(boxes2) < 2:
        return float('inf')

    d_current  = get_box_distance(boxes1[-1], boxes2[-1])
    d_previous = get_box_distance(boxes1[-2], boxes2[-2])
    closing_rate = d_previous - d_current  # > 0 → se acercan

    if closing_rate >= TTC_MIN_CLOSING_RATE:
        ttc = d_current / closing_rate
        return max(0.0, float(ttc))

    return float('inf')


# ======================================================================= #
#  Función principal: detect_collision_advanced                            #
# ======================================================================= #

def detect_collision_advanced(track1, track2, frame_history: int = None):
    """
    Detecta colisión entre dos tracks usando fusión ponderada de 7 señales.

    Args:
        track1, track2: objetos Track con historial de cajas y velocidades
        frame_history:  ventana temporal de análisis (frames)

    Returns:
        (is_collision: bool, score: float, severity: str)
        severity ∈ {"Leve", "Moderado", "Severo", ""}
    """
    if frame_history is None:
        frame_history = FRAME_HISTORY

    boxes1 = list(track1.boxes)
    boxes2 = list(track2.boxes)

    if len(boxes1) < 2 or len(boxes2) < 2:
        return False, 0.0, ""

    curr_box1 = track1.get_current_box()
    curr_box2 = track2.get_current_box()

    # ── Filtro: cajas que siempre estuvieron solapadas (mismo objeto) ────
    iou = get_iou(curr_box1, curr_box2)
    if iou > 0.80:
        # Verificar si alguna vez estuvieron separadas (choque real vs. detección duplicada)
        limit = min(8, len(boxes1), len(boxes2))
        alguna_vez_separados = any(
            get_iou(boxes1[-i], boxes2[-i]) < 0.20
            for i in range(2, limit)
        )
        if not alguna_vez_separados:
            return False, 0.0, ""

    # ── Señal 1: IoU ─────────────────────────────────────────────────────
    iou_score = float(iou)

    # ── Señal 2: Distancia normalizada ───────────────────────────────────
    distance       = get_box_distance(curr_box1, curr_box2)
    mean_diag      = max(1.0, (get_box_diagonal(curr_box1) + get_box_diagonal(curr_box2)) / 2.0)
    dist_threshold = mean_diag * CONTACT_DISTANCE_RATIO
    distance_score = max(0.0, 1.0 - distance / (dist_threshold + 1e-6))

    # ¿Hay contacto físico posible?
    contacto_fisico = (iou > COLLISION_IOU_THRESHOLD) or (distance <= dist_threshold)

    # ── Señal 3: Velocidad relativa ───────────────────────────────────────
    v1 = track1.get_velocity()
    v2 = track2.get_velocity()
    vel_diff  = np.sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)
    vel_score = min(1.0, vel_diff / 10.0) if vel_diff > COLLISION_VELOCITY_CHANGE else 0.0

    # ── Señal 4: Persistencia temporal (frames consecutivos en contacto) ──
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

    # ── Señal 5: Caída brusca de velocidad (impacto inelástico) ──────────
    sp1_hist = track1.get_historical_speed(frame_history)
    sp2_hist = track2.get_historical_speed(frame_history)
    sp1_curr = track1.get_current_speed()
    sp2_curr = track2.get_current_speed()

    speed_drop_score = 0.0
    max_drop = 0.0
    if sp1_hist > 1.0 or sp2_hist > 1.0:
        drop1 = (sp1_hist - sp1_curr) / sp1_hist if sp1_hist > 0 else 0.0
        drop2 = (sp2_hist - sp2_curr) / sp2_hist if sp2_hist > 0 else 0.0
        max_drop = max(drop1, drop2)
        if max_drop > SUDDEN_SPEED_DROP_RATIO:
            speed_drop_score = min(1.0, max_drop)

    # ── Señal 6: Cambio angular de trayectoria ────────────────────────────
    angle_score = 0.0
    for track in (track1, track2):
        vec_hist = np.array(track.get_velocity_vector(frame_history))
        vec_curr = np.array(track.get_velocity_vector(2))
        if np.linalg.norm(vec_hist) > 1.0 and np.linalg.norm(vec_curr) > 1.0:
            cos_t = np.dot(vec_hist, vec_curr) / (
                np.linalg.norm(vec_hist) * np.linalg.norm(vec_curr)
            )
            angle_diff = np.arccos(np.clip(cos_t, -1.0, 1.0)) * (180.0 / np.pi)
            angle_score = max(angle_score, angle_diff / 45.0)  # normalizar a ~90°

    # ── Señal 7: Time-to-Collision (TTC) ─────────────────────────────────
    ttc = compute_ttc(track1, track2)
    ttc_score = max(0.0, 1.0 - ttc / TTC_CRITICAL_FRAMES) if ttc < float('inf') else 0.0

    # ── Fusión ponderada de señales ───────────────────────────────────────
    #  Pesos basados en relevancia: caída de vel. y TTC son las señales más
    #  discriminativas para accidentes reales vs. vehículos que solo se cruzan.
    weights = [0.08, 0.08, 0.07, 0.15, 0.25, 0.17, 0.20]
    signals = [
        iou_score,       # 1. IoU
        distance_score,  # 2. Distancia
        vel_score,       # 3. Vel. relativa
        iou_persistence, # 4. Persistencia
        speed_drop_score,# 5. Caída de velocidad
        min(1.0, angle_score), # 6. Ángulo
        ttc_score,       # 7. TTC
    ]
    collision_score = sum(w * s for w, s in zip(weights, signals))

    # ── Decisión final ────────────────────────────────────────────────────
    is_collision = (
        contacto_fisico and
        collision_score > COLLISION_SCORE_THRESHOLD and
        consecutive_contact >= COLLISION_MIN_FRAMES
    )

    # ── Clasificación de severidad ────────────────────────────────────────
    if max_drop > 0.70 or angle_score > 0.80 or (ttc < 2 and ttc_score > 0.8):
        severity = "Severo"
    elif max_drop > 0.40 or angle_score > 0.40 or ttc_score > 0.6:
        severity = "Moderado"
    else:
        severity = "Leve"

    return is_collision, float(collision_score), severity


# ======================================================================= #
#  Detección de accidente de vehículo único (dashcam / impacto frontal)   #
# ======================================================================= #

def detect_single_vehicle_crash(track, frame_history: int = None):
    """
    Detecta accidente en un solo vehículo (ej: impacto frontal contra la cámara).
    Señal: vehículo grande + parada brusca.

    Returns:
        (is_crash: bool, confidence: float, severity: str)
    """
    if frame_history is None:
        frame_history = FRAME_HISTORY

    if len(track.boxes) < 2:
        return False, 0.0, ""

    box   = track.get_current_box()
    area  = (box[2] - box[0]) * (box[3] - box[1])
    sp_h  = track.get_historical_speed(frame_history)
    sp_c  = track.get_current_speed()

    if sp_h > 1.5 and area > 10_000:
        drop = (sp_h - sp_c) / sp_h
        if drop > SUDDEN_SPEED_DROP_RATIO * 1.2:
            severity = "Severo" if drop > 0.80 else "Moderado"
            return True, min(1.0, float(drop)), severity

    return False, 0.0, ""


# ======================================================================= #
#  Función pública: analyze_collisions                                     #
# ======================================================================= #

def analyze_collisions(tracks: dict, current_frame: int = 0) -> list:
    """
    Analiza todos los pares de tracks activos y detecta colisiones.

    Implementa:
      - Persistencia (anti-falsopositivo): requiere N frames consecutivos
      - Cooldown: evita reportar el mismo evento repetidamente
      - Grace period: acepta tracks con hasta TRACK_MAX_MISSED frames sin detección

    Args:
        tracks:        dict {track_id: Track}
        current_frame: número de frame actual

    Returns:
        list de tuplas (tid1, tid2, frame_num, confidence, severity, ttc)
    """
    collisions = []

    # Decrementar cooldowns
    for pair in list(_pair_cooldown.keys()):
        if _pair_cooldown[pair] > 0:
            _pair_cooldown[pair] -= 1
        if _pair_cooldown[pair] <= 0:
            del _pair_cooldown[pair]

    # Filtrar tracks válidos para el análisis
    valid = {
        tid: t for tid, t in tracks.items()
        if t.age >= TRACK_MIN_AGE and t.frames_since_update <= TRACK_MAX_MISSED
    }

    # ── Accidente de vehículo único ───────────────────────────────────────
    for tid, track in valid.items():
        is_crash, conf, severity = detect_single_vehicle_crash(track)
        if is_crash:
            pair = (int(tid), int(tid))
            _pair_streak[pair] += 1
            if _pair_streak[pair] >= PERSISTENCE_FRAMES and not _pair_cooldown.get(pair, 0):
                ttc = float('inf')
                collisions.append((tid, tid, current_frame, conf, severity, ttc))
                _pair_cooldown[pair] = EVENT_COOLDOWN_FRAMES
                _pair_streak[pair] = 0

    # ── Colisiones entre pares ────────────────────────────────────────────
    track_ids = sorted(valid.keys())
    for i in range(len(track_ids)):
        for j in range(i + 1, len(track_ids)):
            tid1, tid2 = track_ids[i], track_ids[j]
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
