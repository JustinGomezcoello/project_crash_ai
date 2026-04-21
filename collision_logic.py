import numpy as np
from collections import defaultdict
from config import (
    COLLISION_IOU_THRESHOLD, COLLISION_MIN_FRAMES, 
    COLLISION_VELOCITY_CHANGE, COLLISION_DISTANCE_THRESHOLD
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


def detect_collision_advanced(track1, track2, frame_history=5):
    """
    Detección avanzada de colisión usando múltiples señales:
    - Solapamiento de cajas (IoU)
    - Cambio de velocidad relativa
    - Cercanía entre objetos
    - Persistencia temporal
    """
    
    if len(track1.boxes) < 2 or len(track2.boxes) < 2:
        return False, 0.0
    
    # Señal 1: IoU entre cajas actuales
    curr_box1 = track1.get_current_box()
    curr_box2 = track2.get_current_box()
    iou = get_iou(curr_box1, curr_box2)
    
    # Señal 2: Distancia entre centros
    distance = get_box_distance(curr_box1, curr_box2)
    distance_score = max(0, 1 - (distance / COLLISION_DISTANCE_THRESHOLD))
    
    # Señal 3: Cambio de velocidad relativa
    v1 = track1.get_velocity()
    v2 = track2.get_velocity()
    vel_diff = np.sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)
    vel_score = min(1, vel_diff / 10) if vel_diff > COLLISION_VELOCITY_CHANGE else 0
    
    # Señal 4: Historial de cercanía (frames consecutivos con IoU alto)
    consecutive_high_iou = 0
    for i in range(min(frame_history, len(track1.boxes), len(track2.boxes))):
        box1 = track1.boxes[-(i+1)]
        box2 = track2.boxes[-(i+1)]
        if get_iou(box1, box2) > (COLLISION_IOU_THRESHOLD * 0.5):
            consecutive_high_iou += 1
        else:
            break
    
    iou_persistence = min(1, consecutive_high_iou / COLLISION_MIN_FRAMES)
    
    # Fusión de señales (promedio ponderado)
    weights = [0.4, 0.2, 0.2, 0.2]  # IoU, distancia, velocidad, persistencia
    signals = [iou, distance_score, vel_score, iou_persistence]
    collision_score = sum(w * s for w, s in zip(weights, signals))
    
    # Umbral de decisión
    is_collision = (iou > COLLISION_IOU_THRESHOLD and 
                   distance < COLLISION_DISTANCE_THRESHOLD and
                   consecutive_high_iou >= COLLISION_MIN_FRAMES)
    
    return is_collision, collision_score


def analyze_collisions(tracks, min_age=3):
    """
    Analiza los tracks y detecta colisiones entre pares de vehículos.
    Retorna lista de (track_id1, track_id2, frame_num, confidence)
    """
    collisions = []
    
    # Filtrar tracks con edad mínima
    valid_tracks = {tid: t for tid, t in tracks.items() if t.age >= min_age}
    
    # Comparar todos los pares de tracks
    track_ids = sorted(valid_tracks.keys())
    for i in range(len(track_ids)):
        for j in range(i + 1, len(track_ids)):
            tid1, tid2 = track_ids[i], track_ids[j]
            track1, track2 = valid_tracks[tid1], valid_tracks[tid2]
            
            is_collision, confidence = detect_collision_advanced(track1, track2)
            
            if is_collision:
                frame_num = len(track1.boxes) - 1
                collisions.append((tid1, tid2, frame_num, confidence))
    
    return collisions

