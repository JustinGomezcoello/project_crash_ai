"""
main.py — Punto de Entrada CLI del Sistema

Uso desde línea de comandos:
    python main.py                    → procesa todos los videos en data/input/
    python main.py --video mi.mp4     → procesa un video específico
    python main.py --no-evidence      → sin captura de frames de evidencia
"""

import os
import argparse
from config import INPUT_DIR, OUTPUT_DIR, EVIDENCE_DIR

from src.utils import ensure_dirs
from src.video_processor import VideoProcessor


def build_parser():
    p = argparse.ArgumentParser(
        description="Project Crash AI — Detección de Colisiones Vehiculares"
    )
    p.add_argument(
        "--video", type=str, default=None,
        help="Ruta o nombre del video a procesar (default: todos en data/input/)"
    )
    p.add_argument(
        "--tracker", type=str, default="bytetrack", choices=["bytetrack", "botsort"],
        help="Tracker a usar: bytetrack (rápido) | botsort (preciso)"
    )
    p.add_argument(
        "--confidence", type=float, default=0.40,
        help="Umbral de confianza YOLO (0.0-1.0, default: 0.40)"
    )
    p.add_argument(
        "--no-evidence", action="store_true",
        help="No guardar frames de evidencia ni log CSV"
    )
    return p


def print_banner():
    print("=" * 72)
    print("  PROJECT CRASH AI — Sistema de Detección de Colisiones Vehiculares")
    print("  YOLOv8 + ByteTrack + Análisis Cinemático Multi-señal")
    print("=" * 72)
    print(f"  Input:    {INPUT_DIR}")
    print(f"  Output:   {OUTPUT_DIR}")
    print(f"  Evidence: {EVIDENCE_DIR}")
    print("=" * 72)


def main():
    args = build_parser().parse_args()
    print_banner()
    ensure_dirs()

    processor = VideoProcessor(
        tracker=args.tracker,
        confidence=args.confidence,
    )
    save_ev = not args.no_evidence

    if args.video:
        # Un solo video
        video_path = (
            args.video if os.path.isabs(args.video)
            else os.path.join(INPUT_DIR, args.video)
        )
        if not os.path.exists(video_path):
            print(f"[ERROR] No se encontró: {video_path}")
            return
        result = processor.process_video(video_path, save_evidence=save_ev)
        n = 1 if result else 0
    else:
        # Todos los videos
        results = processor.process_all_videos(save_evidence=save_ev)
        n = len(results)

    print("\n" + "=" * 72)
    print(f"  PROCESAMIENTO COMPLETADO — {n} video(s) procesado(s)")
    print(f"  Resultados en: {OUTPUT_DIR}")
    if save_ev:
        print(f"  Evidencia en:  {EVIDENCE_DIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()
