import json
import os
from pathlib import Path
from typing import List, Dict
from config import EVAL_TOLERANCE_FRAMES, RESULTS_DIR

def match_events(detected: List[Dict], gt: List[Dict], tol: int):
    matched_gt = set()
    tp = 0
    for d in detected:
        df = int(d.get("frame", -1))
        found = False
        for i, g in enumerate(gt):
            if i in matched_gt: continue
            gf = int(g.get("frame", -1))
            if abs(df - gf) <= tol:
                tp += 1
                matched_gt.add(i)
                found = True
                break
    fp = len(detected) - tp
    fn = len(gt) - tp
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1}

def load_json(p: Path):
    return json.loads(p.read_text())

def main(gt_path, detected_path, out_path=None):
    gt = load_json(Path(gt_path))["collisions"] if Path(gt_path).exists() else []
    det = load_json(Path(detected_path))["collisions"] if Path(detected_path).exists() else []
    res = match_events(det, gt, EVAL_TOLERANCE_FRAMES)
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        Path(out_path).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("gt")
    p.add_argument("detected")
    p.add_argument("--out", default=os.path.join(RESULTS_DIR, "eval_summary.json"))
    args = p.parse_args()
    main(args.gt, args.detected, args.out)
