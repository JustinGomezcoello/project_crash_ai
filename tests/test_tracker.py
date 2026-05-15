"""
tests/test_tracker.py — Pruebas de la Clase Track

Valida las señales cinemáticas: velocidad, velocidad histórica,
vector de dirección y comportamiento con historial corto.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.tracker import Track


class TestTrack:
    def test_initial_state(self):
        t = Track(1, [0, 0, 100, 100], 0.9)
        assert t.track_id == 1
        assert t.age == 0
        assert t.frames_since_update == 0
        assert t.get_current_box() == [0, 0, 100, 100]

    def test_velocity_insufficient_history(self):
        t = Track(1, [0, 0, 100, 100], 0.9)
        assert t.get_velocity() == (0.0, 0.0)

    def test_velocity_computed(self):
        t = Track(1, [0, 0, 100, 100], 0.9)
        t.update([10, 0, 110, 100], 0.9)  # centro pasa de 50→60
        vx, vy = t.get_velocity()
        assert vx == pytest.approx(10.0)
        assert vy == pytest.approx(0.0)

    def test_speed_zero_stationary(self):
        t = Track(1, [0, 0, 100, 100], 0.9)
        t.update([0, 0, 100, 100], 0.9)
        assert t.get_current_speed() == pytest.approx(0.0)

    def test_historical_speed(self):
        t = Track(1, [0, 0, 10, 10], 0.9)
        for i in range(1, 6):
            t.update([i * 10, 0, i * 10 + 10, 10], 0.9)
        # Velocidad promedio debe ser ~10 px/frame
        hs = t.get_historical_speed(4)
        assert hs == pytest.approx(10.0, abs=1.0)

    def test_mark_missed(self):
        t = Track(1, [0, 0, 100, 100], 0.9)
        t.mark_missed()
        assert t.frames_since_update == 1
        assert t.age == 1

    def test_update_resets_missed(self):
        t = Track(1, [0, 0, 100, 100], 0.9)
        t.mark_missed()
        t.mark_missed()
        assert t.frames_since_update == 2
        t.update([10, 0, 110, 100], 0.85)
        assert t.frames_since_update == 0

    def test_max_history_deque(self):
        t = Track(1, [0, 0, 10, 10], 0.9)
        for i in range(Track.MAX_HISTORY + 5):
            t.update([i, 0, i + 10, 10], 0.9)
        assert len(t.boxes) == Track.MAX_HISTORY

    def test_velocity_vector_returns_tuple(self):
        t = Track(1, [0, 0, 100, 100], 0.9)
        for i in range(5):
            t.update([i * 5, 0, i * 5 + 100, 100], 0.9)
        vx, vy = t.get_velocity_vector(3)
        assert isinstance(vx, float)
        assert isinstance(vy, float)

    def test_center_history_length(self):
        t = Track(1, [0, 0, 10, 10], 0.9)
        for i in range(4):
            t.update([i * 10, 0, i * 10 + 10, 10], 0.9)
        history = t.get_center_history()
        assert len(history) == 5  # 1 inicial + 4 updates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
