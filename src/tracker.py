"""
src/tracker.py — Gestión de Estado por Objeto Rastreado

Clase Track: mantiene el historial de cajas, velocidades y metadatos
de cada objeto detectado. Es independiente del algoritmo de tracking
subyacente (ByteTrack, BoT-SORT, etc.) y alimenta la lógica de colisión.

Referencia: ByteTrack (Zhang et al., 2022) — usa detecciones de baja
confianza para recuperar objetos temporalmente ocluidos, lo que permite
mantener el historial de movimiento durante el momento del impacto.
"""

import numpy as np
from collections import deque
from src.utils import get_box_center, get_box_distance


class Track:
    """
    Representa un objeto rastreado a lo largo del tiempo.

    Mantiene historial de posiciones para calcular señales cinemáticas:
    velocidad, aceleración, dirección y tasa de acercamiento a otros objetos.
    Estas señales son fundamentales para la heurística de detección de colisión.

    Attributes:
        track_id:           ID único del objeto (asignado por el tracker)
        boxes:              Historial de cajas [x1, y1, x2, y2]
        confidences:        Historial de confianzas YOLO
        age:                Frames desde la creación del track
        frames_since_update: Frames desde la última detección válida
        class_id:           Clase COCO del objeto (2=car, 5=bus, 7=truck)
    """

    MAX_HISTORY = 20  # Frames de historial máximo (evita uso excesivo de RAM)

    def __init__(self, track_id: int, box: list, confidence: float, class_id: int = 2):
        self.track_id = track_id
        self.boxes = deque([box], maxlen=self.MAX_HISTORY)
        self.confidences = deque([confidence], maxlen=self.MAX_HISTORY)
        self.age = 0
        self.frames_since_update = 0
        self.class_id = class_id

    def update(self, box: list, confidence: float, class_id: int = None):
        """Actualiza el track con una nueva detección."""
        self.boxes.append(box)
        self.confidences.append(confidence)
        self.frames_since_update = 0
        if class_id is not None:
            self.class_id = class_id

    def mark_missed(self):
        """Marca un frame sin detección (objeto temporalmente perdido)."""
        self.age += 1
        self.frames_since_update += 1

    def get_current_box(self) -> list:
        """Retorna la caja más reciente del track."""
        return list(self.boxes[-1]) if self.boxes else None

    # ------------------------------------------------------------------ #
    #  Señales cinemáticas                                                 #
    # ------------------------------------------------------------------ #

    def get_velocity(self) -> tuple:
        """Velocidad instantánea (diferencia de centros entre los 2 últimos frames)."""
        if len(self.boxes) < 2:
            return (0.0, 0.0)
        c_prev = get_box_center(self.boxes[-2])
        c_curr = get_box_center(self.boxes[-1])
        return (c_curr[0] - c_prev[0], c_curr[1] - c_prev[1])

    def get_current_speed(self) -> float:
        """Rapidez escalar instantánea (píxeles/frame)."""
        vx, vy = self.get_velocity()
        return float(np.sqrt(vx**2 + vy**2))

    def get_historical_speed(self, frames_back: int = 5) -> float:
        """
        Rapidez promedio histórica en los últimos `frames_back` frames.
        Se usa para detectar caída brusca de velocidad (señal de impacto).
        """
        n = min(frames_back, len(self.boxes) - 1)
        if n < 1:
            return 0.0
        speeds = []
        boxes_list = list(self.boxes)
        for i in range(len(boxes_list) - n - 1, len(boxes_list) - 1):
            if i < 0:
                continue
            c1 = get_box_center(boxes_list[i])
            c2 = get_box_center(boxes_list[i + 1])
            speeds.append(np.sqrt((c2[0] - c1[0])**2 + (c2[1] - c1[1])**2))
        return float(np.mean(speeds)) if speeds else 0.0

    def get_velocity_vector(self, frames_back: int = 3) -> tuple:
        """
        Vector de velocidad promediado sobre `frames_back` frames.
        Más estable que la diferencia instantánea para detectar cambios de dirección.
        """
        boxes_list = list(self.boxes)
        if len(boxes_list) <= frames_back:
            return (0.0, 0.0)
        c1 = get_box_center(boxes_list[-(frames_back + 1)])
        c2 = get_box_center(boxes_list[-1])
        return (c2[0] - c1[0], c2[1] - c1[1])

    def get_center_history(self) -> list:
        """Lista de centros históricos para dibujar trayectorias."""
        return [get_box_center(b) for b in self.boxes]

    def __repr__(self):
        box = self.get_current_box()
        return (f"Track(id={self.track_id}, age={self.age}, "
                f"missed={self.frames_since_update}, box={box})")
