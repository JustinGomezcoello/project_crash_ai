"""
debug_single.py — Diagnóstico de detección de vehículo único frame a frame.

Muestra para cada track: area_ratio, speed_hist, speed_curr, drop_ratio
para entender qué umbrales poner.

Uso:
    python debug_single.py ccd_crash_01.mp4
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
from config import INPUT_DIR, FRAME_HISTORY, TRACK_MIN_AGE, TRACK_MAX_MISSED
from src.detector import VehicleDetector
from src.collision_logic import set_frame_dimensions, reset_state


def main():
    video_name = sys.argv[1] if len(sys.argv) > 1 else "ccd_crash_01.mp4"
    video_path = os.path.join(INPUT_DIR, video_name)

    cap = cv2.VideoCapture(video_path)
    fps  = cap.get(cv2.CAP_PROP_FPS) or 10
    fw   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tot  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    set_frame_dimensions(fw, fh)
    reset_state()
    frame_area = fw * fh

    detector = VehicleDetector()
    cap = cv2.VideoCapture(video_path)

    print(f"\n{'='*80}")
    print(f"  DEBUG SINGLE: {video_name} | {fw}x{fh} | {tot} frames | area={frame_area}px")
    print(f"{'='*80}")
    print(f"{'F':>4} | {'ID':>5} | {'area_r':>7} | {'sp_h':>7} | {'sp_c':>7} | "
          f"{'drop%':>7} | {'age':>4} | PASS?")
    print("-"*70)

    frame_num = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        tracks = detector.process_frame(frame)

        for tid, t in sorted(tracks.items()):
            if t.age < TRACK_MIN_AGE:
                continue
            if t.frames_since_update > TRACK_MAX_MISSED:
                continue

            box  = t.get_current_box()
            area = (box[2] - box[0]) * (box[3] - box[1])
            ar   = area / frame_area
            sp_h = t.get_historical_speed(FRAME_HISTORY)
            sp_c = t.get_current_speed()
            drop = (sp_h - sp_c) / sp_h if sp_h > 0 else 0.0

            # ¿Pasaría los filtros?
            p1 = ar >= 0.18
            p2 = sp_h >= 2.0
            p3 = drop >= 0.40
            passes = p1 and p2 and p3
            flag = " <<< CRASH!" if passes else ""

            if ar > 0.05 or passes:  # solo mostrar los relevantes
                print(f"{frame_num:>4} | {tid:>5} | {ar:>7.3f} | {sp_h:>7.2f} | "
                      f"{sp_c:>7.2f} | {drop*100:>6.1f}% | {t.age:>4} |"
                      f" p1={int(p1)} p2={int(p2)} p3={int(p3)}{flag}")

        frame_num += 1

    cap.release()
    print("="*80)


if __name__ == "__main__":
    main()
