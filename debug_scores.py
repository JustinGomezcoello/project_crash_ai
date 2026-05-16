"""
debug_scores.py — Diagnóstico de scores de colisión frame a frame.

Muestra en qué frames CASI se detecta una colisión y qué señales
están activadas, para calibrar los umbrales correctamente.

Uso:
    python debug_scores.py ccd_crash_01.mp4
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
from collections import defaultdict

# Cargar config antes de modificar
from config import INPUT_DIR, YOLO_MODEL, YOLO_CONFIDENCE, FRAME_HISTORY

from src.detector import VehicleDetector
from src.tracker import Track
from src.collision_logic import (
    compute_ttc, reset_state, set_frame_dimensions
)
from src.utils import get_iou, get_box_distance, get_box_diagonal

# Duplicamos la lógica de detect_collision_advanced
# para poder ver cada señal individual
from config import (
    COLLISION_IOU_THRESHOLD, COLLISION_MIN_FRAMES,
    COLLISION_VELOCITY_CHANGE, COLLISION_SCORE_THRESHOLD,
    CONTACT_DISTANCE_RATIO, SUDDEN_SPEED_DROP_RATIO,
    TTC_CRITICAL_FRAMES, TTC_MIN_CLOSING_RATE,
    TRACK_MIN_AGE, TRACK_MAX_MISSED,
)


def score_pair(t1: Track, t2: Track):
    """Calcula el score de colisión entre dos tracks y retorna el desglose."""
    boxes1 = list(t1.boxes)
    boxes2 = list(t2.boxes)

    if len(boxes1) < 2 or len(boxes2) < 2:
        return None

    cb1 = t1.get_current_box()
    cb2 = t2.get_current_box()

    iou = get_iou(cb1, cb2)
    if iou > 0.80:
        return None  # mismo objeto

    distance   = get_box_distance(cb1, cb2)
    mean_diag  = max(1.0, (get_box_diagonal(cb1) + get_box_diagonal(cb2)) / 2.0)
    dist_th    = mean_diag * CONTACT_DISTANCE_RATIO
    dist_score = max(0.0, 1.0 - distance / (dist_th + 1e-6))
    contact    = (iou > COLLISION_IOU_THRESHOLD) or (distance <= dist_th)

    v1 = t1.get_velocity(); v2 = t2.get_velocity()
    vel_diff  = float(np.sqrt((v1[0]-v2[0])**2 + (v1[1]-v2[1])**2))
    vel_score = min(1.0, vel_diff/10.0) if vel_diff > COLLISION_VELOCITY_CHANGE else 0.0

    consec = 0
    for i in range(min(FRAME_HISTORY, len(boxes1), len(boxes2))):
        b1i, b2i = boxes1[-(i+1)], boxes2[-(i+1)]
        if (get_iou(b1i, b2i) > COLLISION_IOU_THRESHOLD*0.5 or
                get_box_distance(b1i, b2i) <= dist_th):
            consec += 1
        else:
            break
    persist = min(1.0, consec / max(COLLISION_MIN_FRAMES, 1))

    sp1h = t1.get_historical_speed(FRAME_HISTORY)
    sp2h = t2.get_historical_speed(FRAME_HISTORY)
    sp1c = t1.get_current_speed()
    sp2c = t2.get_current_speed()
    max_drop = 0.0; drop_score = 0.0
    if sp1h > 3.0 or sp2h > 3.0:
        d1 = (sp1h - sp1c) / sp1h if sp1h > 0 else 0.0
        d2 = (sp2h - sp2c) / sp2h if sp2h > 0 else 0.0
        max_drop = max(d1, d2)
        if max_drop > SUDDEN_SPEED_DROP_RATIO:
            drop_score = min(1.0, max_drop)

    angle_score = 0.0
    for t in (t1, t2):
        vh = np.array(t.get_velocity_vector(FRAME_HISTORY))
        vc = np.array(t.get_velocity_vector(2))
        if np.linalg.norm(vh) > 1.0 and np.linalg.norm(vc) > 1.0:
            cos_t = np.dot(vh, vc) / (np.linalg.norm(vh) * np.linalg.norm(vc))
            ang   = np.arccos(np.clip(cos_t, -1.0, 1.0)) * 180.0 / np.pi
            angle_score = max(angle_score, ang / 45.0)

    ttc = compute_ttc(t1, t2)
    ttc_score = max(0.0, 1.0 - ttc/TTC_CRITICAL_FRAMES) if ttc < float('inf') else 0.0

    weights = [0.06, 0.06, 0.08, 0.12, 0.30, 0.18, 0.20]
    signals = [iou, dist_score, vel_score, persist, drop_score,
               min(1.0, angle_score), ttc_score]
    total   = sum(w*s for w, s in zip(weights, signals))

    return {
        "iou": round(iou, 3),
        "dist": round(dist_score, 3),
        "vel":  round(vel_score, 3),
        "persist": round(persist, 3),
        "drop": round(drop_score, 3),
        "angle": round(min(1.0, angle_score), 3),
        "ttc": round(ttc_score, 3),
        "TOTAL": round(total, 3),
        "contact": contact,
        "consec": consec,
        "distance_px": round(distance, 1),
        "sp1_hist": round(sp1h, 2),
        "sp1_curr": round(sp1c, 2),
        "max_drop": round(max_drop, 3),
    }


def main():
    video_name = sys.argv[1] if len(sys.argv) > 1 else "ccd_crash_01.mp4"
    video_path = os.path.join(INPUT_DIR, video_name)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 10
    fw  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    set_frame_dimensions(fw, fh)
    reset_state()

    detector = VehicleDetector()
    cap = cv2.VideoCapture(video_path)

    print(f"\n{'='*70}")
    print(f"  DEBUG: {video_name} | {fw}x{fh} | {fps}fps | {total} frames")
    print(f"  Umbral de colision: {COLLISION_SCORE_THRESHOLD}")
    print(f"{'='*70}")
    print(f"{'Frame':>6} | {'IDs par':>12} | {'IoU':>5} | {'dist':>5} | "
          f"{'vel':>5} | {'drop':>5} | {'angle':>5} | {'TTC':>5} | {'TOTAL':>6} | {'Contact':>7}")
    print("-"*90)

    frame_num = 0
    max_scores = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        tracks = detector.process_frame(frame)

        # Filtrar tracks validos
        valid = {
            tid: t for tid, t in tracks.items()
            if t.age >= TRACK_MIN_AGE and t.frames_since_update <= TRACK_MAX_MISSED
        }

        track_ids = sorted(valid.keys())
        best_score = 0.0

        for i in range(len(track_ids)):
            for j in range(i+1, len(track_ids)):
                tid1, tid2 = track_ids[i], track_ids[j]
                if tid1 == tid2:
                    continue
                res = score_pair(valid[tid1], valid[tid2])
                if res is None:
                    continue

                if res["TOTAL"] > best_score:
                    best_score = res["TOTAL"]

                # Mostrar si el score es "interesante" (>0.10)
                if res["TOTAL"] > 0.10:
                    flag = " *** COLISION ***" if (
                        res["TOTAL"] > COLLISION_SCORE_THRESHOLD and
                        res["contact"] and res["consec"] >= COLLISION_MIN_FRAMES
                    ) else (" <<< CASI" if res["TOTAL"] > COLLISION_SCORE_THRESHOLD * 0.80 else "")
                    print(f"{frame_num:>6} | {str(tid1)+'-'+str(tid2):>12} | "
                          f"{res['iou']:>5} | {res['dist']:>5} | "
                          f"{res['vel']:>5} | {res['drop']:>5} | "
                          f"{res['angle']:>5} | {res['ttc']:>5} | "
                          f"{res['TOTAL']:>6} |{res['contact']:>7}{flag}")

        max_scores.append((frame_num, best_score))
        frame_num += 1

    cap.release()

    top5 = sorted(max_scores, key=lambda x: -x[1])[:5]
    print(f"\n{'='*70}")
    print("  Top 5 frames con mayor score de colision:")
    for fn, sc in top5:
        ts = f"{int(fn/fps)//60:02d}:{int(fn/fps)%60:02d}"
        print(f"    Frame {fn:>4} ({ts}) → score máx: {sc:.4f}")
    print(f"\n  Umbral actual: {COLLISION_SCORE_THRESHOLD}")
    if top5 and top5[0][1] > 0:
        recommended = round(top5[0][1] * 0.80, 3)
        print(f"  Umbral recomendado para detectar el top evento: {recommended}")
    print("="*70)


if __name__ == "__main__":
    main()
