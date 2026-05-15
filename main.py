"""main.py - Punto de entrada principal del proyecto

Configuración actual: procesa SOLO 'ccd_crash_01.mp4' que esté dentro de data/input/.
"""

import os

from config import INPUT_DIR, OUTPUT_DIR
from utils import ensure_dirs
from video_processor import VideoProcessor


def main():
    """Función principal."""
    print("=" * 80)
    print("SISTEMA DE DETECCIÓN DE COLISIONES DE TRÁNSITO")
    print("Basado en YOLO + Tracking + Análisis Temporal")
    print("=" * 80)

    ensure_dirs()
    print("\n[OK] Directorios verificados:")
    print(f"  INPUT:  {INPUT_DIR}")
    print(f"  OUTPUT: {OUTPUT_DIR}")

    target_name = "ccd_crash_01.mp4"
    video_path = os.path.join(INPUT_DIR, target_name)

    if not os.path.exists(video_path):
        print(f"\n[ERROR] No se encontró el video requerido: {video_path}")
        print("[INFO] Asegúrate de que exista en data/input/")
        return

    print(f"\n[INFO] Procesando SOLO: {target_name}\n")

    processor = VideoProcessor()
    result = processor.process_video(video_path)

    print("\n" + "=" * 80)
    print("PROCESAMIENTO COMPLETADO")
    print(f"Videos procesados: {1 if result else 0}")
    print("Resultados guardados en: " + OUTPUT_DIR)
    print("=" * 80)


if __name__ == "__main__":
    main()
