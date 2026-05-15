"""
evaluate_collisions.py — Evaluación de Precisión con Ground Truth

Compara los eventos detectados por el sistema contra un reporte
de referencia (ground truth) y calcula Precision, Recall y F1.

Uso:
    python evaluate_collisions.py gt_report.json data/output/report_*.json

Formato del ground truth JSON:
    {
      "collisions": [
        {"frame": 28, "severity": "Severo"},
        ...
      ]
    }
"""

import sys
import json
from config import EVAL_TOLERANCE_FRAMES


def load_collision_frames(report_path: str) -> list:
    """Extrae los frame numbers de colisiones de un reporte JSON."""
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [c["frame"] for c in data.get("collisions", [])]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"[ERROR] No se pudo leer {report_path}: {e}")
        return []


def match_events(gt_frames: list, pred_frames: list,
                 tolerance: int = EVAL_TOLERANCE_FRAMES) -> tuple:
    """
    Empareja eventos GT con predicciones dentro de la tolerancia temporal.

    Returns:
        (TP, FP, FN)
    """
    matched_gt  = set()
    matched_pred = set()

    for i, gt_f in enumerate(gt_frames):
        for j, pred_f in enumerate(pred_frames):
            if j in matched_pred:
                continue
            if abs(gt_f - pred_f) <= tolerance:
                matched_gt.add(i)
                matched_pred.add(j)
                break

    tp = len(matched_gt)
    fp = len(pred_frames) - len(matched_pred)
    fn = len(gt_frames) - tp
    return tp, fp, fn


def compute_metrics(tp: int, fp: int, fn: int) -> dict:
    """Calcula Precision, Recall y F1."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn}


def evaluate(gt_path: str, pred_path: str) -> dict:
    gt_frames   = load_collision_frames(gt_path)
    pred_frames = load_collision_frames(pred_path)

    print(f"\n[INFO] Ground truth:   {len(gt_frames)} evento(s) en: {gt_path}")
    print(f"[INFO] Predicciones:   {len(pred_frames)} evento(s) en: {pred_path}")
    print(f"[INFO] Tolerancia:     ±{EVAL_TOLERANCE_FRAMES} frames")

    tp, fp, fn = match_events(gt_frames, pred_frames)
    metrics    = compute_metrics(tp, fp, fn)

    print(f"\n── Resultados ──────────────────────")
    print(f"  TP (correctos):   {tp}")
    print(f"  FP (falsos pos.): {fp}")
    print(f"  FN (perdidos):    {fn}")
    print(f"  Precision:        {metrics['precision']:.3f}")
    print(f"  Recall:           {metrics['recall']:.3f}")
    print(f"  F1:               {metrics['f1']:.3f}")
    print(f"────────────────────────────────────")

    return metrics


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python evaluate_collisions.py <gt.json> <pred.json>")
        sys.exit(1)
    evaluate(sys.argv[1], sys.argv[2])
