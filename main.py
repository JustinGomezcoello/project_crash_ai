"""
main.py - Punto de entrada principal del proyecto
"""

from config import INPUT_DIR, OUTPUT_DIR
from utils import ensure_dirs, list_input_files
from video_processor import VideoProcessor


def main():
    """Función principal."""
    print("="*80)
    print("SISTEMA DE DETECCIÓN DE COLISIONES DE TRÁNSITO")
    print("Basado en YOLO + Tracking + Análisis Temporal")
    print("="*80)
    
    # Asegurar directorios
    ensure_dirs()
    print("\n[OK] Directorios verificados:")
    print(f"  INPUT:  {INPUT_DIR}")
    print(f"  OUTPUT: {OUTPUT_DIR}")
    
    # Verificar archivos de entrada
    video_files = list_input_files('.mp4')
    print(f"\n[INFO] Archivos .mp4 encontrados: {len(video_files)}")
    
    if not video_files:
        print("\n[WARNING] No hay videos .mp4 en la carpeta input/")
        print("[INFO] Por favor, coloca archivos de video en: " + INPUT_DIR)
        print("\nFormatos soportados: .mp4, .avi, .mov, .flv, etc.")
        return
    
    # Procesar videos
    print(f"\n[INFO] Iniciando procesamiento de {len(video_files)} video(s)...\n")
    
    processor = VideoProcessor()
    results = processor.process_all_videos()
    
    print("\n" + "="*80)
    print("PROCESAMIENTO COMPLETADO")
    print(f"Videos procesados: {len(results)}")
    print("Resultados guardados en: " + OUTPUT_DIR)
    print("="*80)


if __name__ == '__main__':
    main()

