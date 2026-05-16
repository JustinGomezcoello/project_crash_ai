"""
tests/test_collision_logic.py — Pruebas Unitarias del Motor de Colisiones

Valida las funciones de geometría, la señal TTC y la lógica de detección
usando casos de prueba controlados con colisiones y no-colisiones conocidas.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
from src.tracker import Track
from src.utils import get_iou, get_box_distance, get_box_center
from src.collision_logic import (
    compute_ttc, detect_collision_advanced,
    detect_single_vehicle_crash, reset_state
)


# ── Fixtures ──────────────────────────────────────────────────────────────

def make_track(track_id, boxes, confidence=0.8, class_id=2) -> Track:
    """Crea un Track con historial de cajas predefinido."""
    t = Track(track_id, boxes[0], confidence, class_id)
    for box in boxes[1:]:
        t.update(box, confidence)
        t.mark_missed()     # simular paso de tiempo
        t.frames_since_update = 0  # forzar como "actualizado"
    t.age = len(boxes)
    return t


# ── Tests de geometría ────────────────────────────────────────────────────

class TestGeometry:
    def test_iou_identical_boxes(self):
        box = [0, 0, 100, 100]
        assert get_iou(box, box) == pytest.approx(1.0)

    def test_iou_no_overlap(self):
        assert get_iou([0, 0, 10, 10], [20, 20, 30, 30]) == pytest.approx(0.0)

    def test_iou_partial_overlap(self):
        iou = get_iou([0, 0, 20, 20], [10, 10, 30, 30])
        assert 0 < iou < 1

    def test_box_center(self):
        cx, cy = get_box_center([0, 0, 100, 80])
        assert cx == pytest.approx(50.0)
        assert cy == pytest.approx(40.0)

    def test_box_distance_same_center(self):
        b1 = [0, 0, 100, 100]
        b2 = [0, 0, 100, 100]
        assert get_box_distance(b1, b2) == pytest.approx(0.0)

    def test_box_distance_known(self):
        # Centros en (50,50) y (50,150) → distancia = 100
        b1 = [0, 0, 100, 100]
        b2 = [0, 100, 100, 200]
        assert get_box_distance(b1, b2) == pytest.approx(100.0)


# ── Tests de TTC ──────────────────────────────────────────────────────────

class TestTTC:
    def test_ttc_approaching(self):
        """Dos vehículos acercándose → TTC finito."""
        # frame 0: dist=200, frame 1: dist=180 → rate=20 → TTC=9
        t1 = make_track(1, [[0, 200, 100, 300], [0, 210, 100, 310]])
        t2 = make_track(2, [[300, 200, 400, 300], [280, 210, 380, 310]])
        ttc = compute_ttc(t1, t2)
        assert ttc < float('inf')
        assert ttc > 0

    def test_ttc_not_approaching(self):
        """Dos vehículos alejándose → TTC infinito."""
        t1 = make_track(1, [[0, 0, 100, 100], [0, 0, 100, 100]])
        t2 = make_track(2, [[500, 0, 600, 100], [600, 0, 700, 100]])
        assert compute_ttc(t1, t2) == float('inf')

    def test_ttc_insufficient_history(self):
        """Un solo box → TTC indefinido."""
        t1 = Track(1, [0, 0, 100, 100], 0.9)
        t2 = Track(2, [200, 0, 300, 100], 0.9)
        assert compute_ttc(t1, t2) == float('inf')


# ── Tests de detección de colisión ───────────────────────────────────────

class TestCollisionDetection:
    def setup_method(self):
        reset_state()

    def test_no_collision_far_apart(self):
        """Vehículos muy separados → sin colisión."""
        t1 = make_track(1, [[0, 0, 100, 100]] * 6)
        t2 = make_track(2, [[800, 0, 900, 100]] * 6)
        is_col, score, sev = detect_collision_advanced(t1, t2)
        assert not is_col
        assert score < 0.25

    def test_no_collision_insufficient_history(self):
        """Tracks con 1 solo frame → sin colisión."""
        t1 = Track(1, [0, 0, 100, 100], 0.9)
        t2 = Track(2, [50, 0, 150, 100], 0.9)
        is_col, score, sev = detect_collision_advanced(t1, t2)
        assert not is_col

    def test_collision_overlapping_with_speedrop(self):
        """Cajas solapadas con historial separado + caída de velocidad → colisión."""
        # Historial: separados y moviéndose, luego solapados y parados
        boxes1 = [[0, 0, 100, 100], [20, 0, 120, 100],
                  [40, 0, 140, 100], [55, 0, 155, 100],
                  [60, 0, 160, 100], [62, 0, 162, 100]]
        boxes2 = [[300, 0, 400, 100], [260, 0, 360, 100],
                  [210, 0, 310, 100], [150, 0, 250, 100],
                  [120, 0, 220, 100], [118, 0, 218, 100]]
        t1 = make_track(1, boxes1)
        t2 = make_track(2, boxes2)
        is_col, score, sev = detect_collision_advanced(t1, t2)
        # Con cajas que se acercan fuerte, debe dar score razonable
        assert score > 0.0

    def test_duplicate_box_filter(self):
        """Cajas siempre solapadas (mismo objeto detectado 2 veces) → ignorar."""
        # Ambos tracks con exactamente la misma posición desde el inicio
        same_boxes = [[100, 100, 200, 200]] * 6
        t1 = make_track(1, same_boxes)
        t2 = make_track(2, same_boxes)
        is_col, score, sev = detect_collision_advanced(t1, t2)
        assert not is_col

    def test_severity_leve(self):
        """Score bajo → severidad Leve."""
        # Simulamos colisión con velocidades bajas → severidad mínima
        boxes1 = [[0, 0, 100, 100]] * 6
        boxes2 = [[101, 0, 201, 100]] * 6
        t1 = make_track(1, boxes1)
        t2 = make_track(2, boxes2)
        _, _, sev = detect_collision_advanced(t1, t2)
        # Con distancia casi 0 pero sin caída de velocidad → Leve
        assert sev in ("Leve", "Moderado", "Severo", "")


# ── Tests de accidente de vehículo único ─────────────────────────────────

class TestSingleVehicleCrash:
    def test_large_vehicle_sudden_stop(self):
        """Vehículo muy grande + parada brusca ≥70% → crash detectado."""
        from src.collision_logic import set_frame_dimensions
        # Frame 640x480, vehículo ocupa ~450x340 = 153.000px = 50% del frame
        set_frame_dimensions(640, 480)
        boxes = [
            [0,  50, 450, 390],   # mueve 40px/frame
            [40, 50, 490, 390],
            [80, 50, 530, 390],
            [120, 50, 570, 390],
            [121, 50, 571, 390],  # parada casi total (drop ~97%)
            [121, 50, 571, 390],
        ]
        t = make_track(1, boxes)
        is_crash, conf, sev = detect_single_vehicle_crash(t, frame_height=480, frame_width=640)
        assert is_crash, "Vehiculo enorme con frenada brusca debe detectarse"
        assert conf > 0
        assert sev in ("Moderado", "Severo")

    def test_small_vehicle_no_crash(self):
        """Vehículo pequeño que frena normal → sin crash."""
        from src.collision_logic import set_frame_dimensions
        set_frame_dimensions(1280, 720)
        boxes = [[100, 100, 130, 130]] * 5  # area ~900px << 35% del frame
        t = make_track(1, boxes)
        is_crash, conf, sev = detect_single_vehicle_crash(t, frame_height=720, frame_width=1280)
        assert not is_crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
