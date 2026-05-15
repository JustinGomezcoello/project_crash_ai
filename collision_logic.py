# filepath: d:\trabajo u\project_crash_ai\collision_logic.py
import numpy as np
from collections import defaultdict
from config import (
    COLLISION_IOU_THRESHOLD, COLLISION_MIN_FRAMES,
    COLLISION_VELOCITY_CHANGE, COLLISION_DISTANCE_THRESHOLD,
    PERSISTENCE_FRAMES, EVENT_COOLDOWN_FRAMES, CONTACT_DISTANCE_RATIO,
    SUDDEN_SPEED_DROP_RATIO, COLLISION_SCORE_THRESHOLD, FRAME_HISTORY
)
from utils import get_iou, get_box_distance, get_box_center


class Track:
    """Representa un objeto rastreado a lo largo del tiempo."""

    def __init__(self, track_id, box, confidence):
        self.track_id = track_id
        self.boxes = [box]
        self.confidences = [confidence]
        self.age = 0
        self.frames_since_update = 0

    def update(self, box, confidence):
        """Actualiza el track con una nueva detección."""
        self.boxes.append(box)
        self.confidences.append(confidence)
        self.frames_since_update = 0

    def increment_age(self):
        """Incrementa la edad del track."""
        self.age += 1
        self.frames_since_update += 1

    def get_velocity(self):
        """Estima la velocidad del objeto (diferencia de centros entre últimos frames)."""
        if len(self.boxes) < 2:
            return (0, 0)

        prev_center = get_box_center(self.boxes[-2])
        curr_center = get_box_center(self.boxes[-1])

        vx = curr_center[0] - prev_center[0]
        vy = curr_center[1] - prev_center[1]

        return (vx, vy)

    def get_historical_speed(self, frames_back):
        """Calcula la rapidez promedio histórica."""
        if len(self.boxes) < frames_back + 1:
            return 0.0
        
        speeds = []
        for i in range(len(self.boxes) - frames_back - 1, len(self.boxes) - 2):
            if i < 0:
                continue
            c1 = get_box_center(self.boxes[i])
            c2 = get_box_center(self.boxes[i+1])
            dist = np.sqrt((c2[0] - c1[0])**2 + (c2[1] - c1[1])**2)
            speeds.append(dist)
        
        return np.mean(speeds) if speeds else 0.0

    def get_current_speed(self):
        """Rapidez actual en el último movimiento."""
        vx, vy = self.get_velocity()
        return np.sqrt(vx**2 + vy**2)

    def get_velocity_vector(self, frames_back=3):
        if len(self.boxes) <= frames_back:
            return (0.0, 0.0)
        c1 = get_box_center(self.boxes[-(frames_back+1)])
        c2 = get_box_center(self.boxes[-1])
        return (c2[0] - c1[0], c2[1] - c1[1])

    def get_current_box(self):
        """Retorna la caja actual del track."""
        return self.boxes[-1] if self.boxes else None


class SimpleTracker:
    """Tracker simple basado en distancia euclidiana."""

    def __init__(self, max_distance=50, max_age=30):
        self.max_distance = max_distance
        self.max_age = max_age
        self.next_id = 0
        self.tracks = {}

    def update(self, detections):
        """
        Actualiza los tracks con nuevas detecciones.
        detections: lista de (box, confidence)
        Retorna: dict de {track_id: Track}
        """
        # Matching simple: asigna cada detección al track más cercano
        used_detections = set()
        used_tracks = set()

        for track_id, track in list(self.tracks.items()):
            best_distance = float('inf')
            best_idx = -1

            curr_box = track.get_current_box()

            for det_idx, (det_box, det_conf) in enumerate(detections):
                if det_idx in used_detections:
                    continue

                distance = get_box_distance(curr_box, det_box)

                if distance < best_distance and distance < self.max_distance:
                    best_distance = distance
                    best_idx = det_idx

            if best_idx != -1:
                box, conf = detections[best_idx]
                track.update(box, conf)
                used_detections.add(best_idx)
                used_tracks.add(track_id)
            else:
                track.increment_age()

        # Crear nuevos tracks para detecciones no asignadas
        for det_idx, (det_box, det_conf) in enumerate(detections):
            if det_idx not in used_detections:
                self.tracks[self.next_id] = Track(self.next_id, det_box, det_conf)
                self.next_id += 1

        # Eliminar tracks muy antiguos
        self.tracks = {
            tid: track for tid, track in self.tracks.items()
            if track.frames_since_update < self.max_age
        }

        return self.tracks


def detect_collision_simple(box1, box2):
    """Detección simple de colisión por solapamiento de cajas."""
    iou = get_iou(box1, box2)
    return iou > COLLISION_IOU_THRESHOLD


def detect_collision_advanced(track1, track2, frame_history=None):
    """
    Detección avanzada de colisión usando múltiples señales:
    - Solapamiento de cajas (IoU)
    - Cambio de velocidad relativa
    - Cercanía entre objetos
    - Persistencia temporal
    - Caída brusca de velocidad (impacto real)
    """
    if frame_history is None:
        frame_history = FRAME_HISTORY

    if len(track1.boxes) < 2 or len(track2.boxes) < 2:
        return False, 0.0, ""

    # Señal 1: IoU entre cajas actuales
    curr_box1 = track1.get_current_box()
    curr_box2 = track2.get_current_box()
    
    # Filtro de cajas duplicadas/contenidas (mismo objeto detectado por YOLO)
    x1_min, y1_min, x1_max, y1_max = curr_box1
    x2_min, y2_min, x2_max, y2_max = curr_box2
    ix_min = max(x1_min, x2_min)
    iy_min = max(y1_min, y2_min)
    ix_max = min(x1_max, x2_max)
    iy_max = min(y1_max, y2_max)
    
    iou = get_iou(curr_box1, curr_box2)
    
    # Filtro de cajas duplicadas/contenidas (mismo objeto detectado por YOLO)
    if iou > 0.8:
        # Si el IoU es EXTREMADAMENTE alto, verificar si historicamente estuvieron separados
        historicamente_separados = False
        limit = min(8, len(track1.boxes), len(track2.boxes))
        for i in range(2, limit):
            if get_iou(track1.boxes[-i], track2.boxes[-i]) < 0.2:
                historicamente_separados = True
                break
        if not historicamente_separados:
            return False, 0.0, ""

    # Señal 2: Distancia entre centros (normalizada por diagonal promedio)
    distance = get_box_distance(curr_box1, curr_box2)
    diag1 = np.sqrt((curr_box1[2] - curr_box1[0])**2 + (curr_box1[3] - curr_box1[1])**2)
    diag2 = np.sqrt((curr_box2[2] - curr_box2[0])**2 + (curr_box2[3] - curr_box2[1])**2)
    mean_diag = max(1.0, (diag1 + diag2) / 2.0)
    
    distance_threshold = mean_diag * CONTACT_DISTANCE_RATIO
    distance_score = max(0, 1 - (distance / (distance_threshold + 1e-6)))

    # Verificar si hay contacto físico posible
    contacto_fisico = (iou > COLLISION_IOU_THRESHOLD) or (distance <= distance_threshold)

    # Señal 3: Cambio de velocidad relativa entre los dos
    v1 = track1.get_velocity()
    v2 = track2.get_velocity()
    vel_diff = np.sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)
    vel_score = min(1, vel_diff / 10) if vel_diff > COLLISION_VELOCITY_CHANGE else 0

    # Señal 4: Caída brusca de velocidad (choque inelástico)
    speed1_hist = track1.get_historical_speed(frame_history)
    speed2_hist = track2.get_historical_speed(frame_history)
    speed1_curr = track1.get_current_speed()
    speed2_curr = track2.get_current_speed()

    speed_drop_score = 0.0
    max_drop = 0.0
    if speed1_hist > 1.0 or speed2_hist > 1.0: # Si había movimiento
        drop1 = (speed1_hist - speed1_curr) / speed1_hist if speed1_hist > 0 else 0
        drop2 = (speed2_hist - speed2_curr) / speed2_hist if speed2_hist > 0 else 0
        
        # Consideramos colisión si alguno de los dos vehículos pierde velocidad drásticamente
        max_drop = max(drop1, drop2)
        if max_drop > SUDDEN_SPEED_DROP_RATIO:
            speed_drop_score = min(1.0, max_drop)

    vec_hist1 = track1.get_velocity_vector(frame_history)
    vec_curr1 = track1.get_velocity_vector(2)
    angle_score = 0.0
    if np.linalg.norm(vec_hist1) > 1 and np.linalg.norm(vec_curr1) > 1:
        cos_t1 = np.dot(vec_hist1, vec_curr1) / (np.linalg.norm(vec_hist1) * np.linalg.norm(vec_curr1))
        angle_diff1 = np.arccos(np.clip(cos_t1, -1.0, 1.0)) * (180 / np.pi)
        angle_score = max(angle_score, angle_diff1 / 45.0)
        
    vec_hist2 = track2.get_velocity_vector(frame_history)
    vec_curr2 = track2.get_velocity_vector(2)
    if np.linalg.norm(vec_hist2) > 1 and np.linalg.norm(vec_curr2) > 1:
        cos_t2 = np.dot(vec_hist2, vec_curr2) / (np.linalg.norm(vec_hist2) * np.linalg.norm(vec_curr2))
        angle_diff2 = np.arccos(np.clip(cos_t2, -1.0, 1.0)) * (180 / np.pi)
        angle_score = max(angle_score, angle_diff2 / 45.0)

    # Señal 5: Historial de cercanía (frames consecutivos con IoU alto o muy cerca)
    consecutive_high_iou = 0
    for i in range(min(frame_history, len(track1.boxes), len(track2.boxes))):
        box1 = track1.boxes[-(i+1)]
        box2 = track2.boxes[-(i+1)]
        if get_iou(box1, box2) > (COLLISION_IOU_THRESHOLD * 0.5) or get_box_distance(box1, box2) <= distance_threshold:
            consecutive_high_iou += 1
        else:
            break

    iou_persistence = min(1.0, consecutive_high_iou / COLLISION_MIN_FRAMES)

    # Fusión de señales (promedio ponderado)
    weights = [0.1, 0.1, 0.1, 0.2, 0.3, 0.2]  # IoU, distancia, vel_relativa, persistencia, caída_vel (lo más importante)
    signals = [iou, distance_score, vel_score, iou_persistence, speed_drop_score, min(1.0, angle_score)]
    collision_score = sum(w * s for w, s in zip(weights, signals))

    # Umbral de decisión: requerir señales de choque real, no solo contacto
    is_collision = (
        contacto_fisico and 
        (collision_score > COLLISION_SCORE_THRESHOLD) and 
        (consecutive_high_iou >= COLLISION_MIN_FRAMES)
    )

    severity = "Leve"
    try:
        max_drop_val = max_drop
    except NameError:
        max_drop_val = 0.0
        
    if max_drop_val > 0.7 or angle_score > 0.8:
        severity = "Severo"
    elif max_drop_val > 0.4 or angle_score > 0.4:
        severity = "Moderado"
        
    return is_collision, collision_score, severity


# Persistencia por pares y cooldown para evitar alertas repetidas
_pair_streak = defaultdict(int)    # {(id1,id2): consecutive_frames_with_signal}
_pair_cooldown = defaultdict(int)  # {(id1,id2): frames_left_in_cooldown}


def detect_single_vehicle_crash(track, frame_history=None):
    if frame_history is None:
        frame_history = FRAME_HISTORY
        
    if len(track.boxes) < 2:
        return False, 0.0, ""
        
    box = track.get_current_box()
    width = box[2] - box[0]
    height = box[3] - box[1]
    area = width * height
    
    speed_hist = track.get_historical_speed(frame_history)
    speed_curr = track.get_current_speed()
    
    # Impacto frontal con la camara (ego-vehicle): vehiculo grande y velocidad 2D cae abruptamente.
    if speed_hist > 1.5 and area > 10000:
        drop = (speed_hist - speed_curr) / speed_hist
        if drop > SUDDEN_SPEED_DROP_RATIO * 1.2:
            severity = "Severo" if drop > 0.8 else "Moderado"
            return True, min(1.0, drop), severity
            
    return False, 0.0, ""


def analyze_collisions(tracks, current_frame=0, min_age=3):
    """
    Analiza los tracks y detecta colisiones entre pares de vehículos.
    Retorna lista de (track_id1, track_id2, frame_num, confidence)
    """
    collisions = []

    # Decrementar cooldowns
    for pair in list(_pair_cooldown.keys()):
        if _pair_cooldown[pair] > 0:
            _pair_cooldown[pair] -= 1
            if _pair_cooldown[pair] <= 0:
                del _pair_cooldown[pair]

    # Filtrar tracks con edad mínima
    valid_tracks = {tid: t for tid, t in tracks.items() if t.age >= min_age and t.frames_since_update <= 5}

    # Analizar colisiones contra el vehiculo de la camara (dashcam)
    for tid, track in valid_tracks.items():
        is_crash, conf, severity = detect_single_vehicle_crash(track)
        if is_crash:
            pair = tuple(sorted((int(tid), int(tid))))
            _pair_streak[pair] += 1
            if _pair_streak[pair] >= PERSISTENCE_FRAMES and _pair_cooldown.get(pair, 0) == 0:
                frame_num = len(track.boxes) - 1
                collisions.append((tid, tid, frame_num, conf, severity))
                _pair_cooldown[pair] = EVENT_COOLDOWN_FRAMES
                _pair_streak[pair] = 0

    # Comparar todos los pares de tracks
    track_ids = sorted(valid_tracks.keys())
    for i in range(len(track_ids)):
        for j in range(i + 1, len(track_ids)):
            tid1, tid2 = track_ids[i], track_ids[j]
            pair = tuple(sorted((int(tid1), int(tid2))))
            track1, track2 = valid_tracks[tid1], valid_tracks[tid2]

            is_collision, confidence, severity = detect_collision_advanced(track1, track2)

            if is_collision:
                _pair_streak[pair] += 1
            else:
                _pair_streak[pair] = 0

            # Registrar evento solo si la racha alcanza el mínimo y no está en cooldown
            if _pair_streak[pair] >= PERSISTENCE_FRAMES and _pair_cooldown.get(pair, 0) == 0:
                frame_num = len(track1.boxes) - 1
                collisions.append((tid1, tid2, frame_num, confidence, severity))
                # Activar cooldown y resetear racha para este par
                _pair_cooldown[pair] = EVENT_COOLDOWN_FRAMES
                _pair_streak[pair] = 0

    return collisions
