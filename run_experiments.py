# Experiment Runner for Baseline and Full Pipeline
import os
import json
from pathlib import Path
from config import INPUT_DIR, OUTPUT_DIR, RESULTS_DIR
import subprocess

def run_baseline(input_video, output_json):
    # Simula baseline: solo detección, colisión si IoU > threshold en algún frame
    # Aquí deberías implementar la lógica real, esto es un placeholder
    result = {
        "collisions": [
            {"frame": 45, "confidence": 0.7, "type": "baseline"}
        ],
        "video": os.path.basename(input_video)
    }
    Path(output_json).write_text(json.dumps(result, indent=2))
    print(f"[BASELINE] Guardado: {output_json}")

def run_full_pipeline(input_video, output_json):
    # Ejecuta el pipeline real (main.py debe guardar el reporte en OUTPUT_DIR)
    # Aquí asumimos que main.py ya genera el reporte, solo lo copiamos a results
    video_name = Path(input_video).stem
    report_candidates = list(Path(OUTPUT_DIR).glob(f"report_*.json"))
    if not report_candidates:
        print(f"[FULL] No se encontró reporte para {input_video}")
        return
    latest = max(report_candidates, key=lambda p: p.stat().st_mtime)
    data = json.loads(latest.read_text())
    Path(output_json).write_text(json.dumps(data, indent=2))
    print(f"[FULL] Guardado: {output_json}")

def main():
    os.makedirs(os.path.join(RESULTS_DIR, "experiments"), exist_ok=True)
    test_videos = list(Path(INPUT_DIR).glob("*.mp4"))
    for vid in test_videos:
        # Baseline
        out_base = os.path.join(RESULTS_DIR, "experiments", f"baseline_{vid.stem}.json")
        run_baseline(str(vid), out_base)
        # Full pipeline (asume que ya corriste main.py y generó el reporte)
        out_full = os.path.join(RESULTS_DIR, "experiments", f"full_{vid.stem}.json")
        run_full_pipeline(str(vid), out_full)

if __name__ == "__main__":
    main()
