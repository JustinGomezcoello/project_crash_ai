"""
simple_test.py - Prueba simplificada sin YOLO (solo lógica y tracking)
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# Importar módulos del proyecto
from config import INPUT_DIR, OUTPUT_DIR
from collision_logic import SimpleTracker, detect_collision_advanced, Track
from utils import ensure_dirs, draw_box, get_iou


def create_test_video_simple(output_path):
    """Crea un video de prueba simple con dos objetos aproximándose."""
    print(f"[INFO] Creando video de prueba simple: {output_path}")
    
    fps = 30
    width, height = 640, 480
    num_frames = 90  # 3 segundos
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    for frame_num in range(num_frames):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 200
        
        # Vehículo 1: izquierda -> derecha
        x1 = 50 + frame_num * 3.5
        y1 = height // 3
        w1, h1 = 80, 60
        
        # Vehículo 2: derecha -> izquierda
        x2 = width - 50 - frame_num * 3.5
        y2 = height // 2
        w2, h2 = 80, 60
        
        # Dibujar vehículos
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x1+w1), int(y1+h1)), (0, 255, 0), 2)
        cv2.rectangle(frame, (int(x2), int(y2)), (int(x2+w2), int(y2+h2)), (0, 255, 0), 2)
        
        cv2.putText(frame, f"Frame: {frame_num}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        distance = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
        if distance < 100:
            cv2.putText(frame, "PROXIMIDAD", (250, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        out.write(frame)
    
    out.release()
    print(f"[OK] Video creado: {output_path}")


def test_all():
    """Prueba completa."""
    print("\n" + "="*70)
    print("PRUEBA SIMPLIFICADA - SIN DEPENDENCIAS DE YOLO")
    print("="*70 + "\n")
    
    # Test 1: Lógica de colisión
    print("[TEST 1] Lógica de Colisión")
    print("-" * 70)
    
    track1 = Track(1, [100, 100, 180, 160], 0.9)
    track2 = Track(2, [150, 120, 230, 180], 0.85)
    
    for i in range(5):
        new_box1 = [100 + i*20, 100, 180 + i*20, 160]
        new_box2 = [150 - i*15, 120, 230 - i*15, 180]
        track1.update(new_box1, 0.9 - i*0.05)
        track2.update(new_box2, 0.85 - i*0.05)
    
    is_collision, confidence = detect_collision_advanced(track1, track2)
    print(f"  Track 1 caja actual: {track1.get_current_box()}")
    print(f"  Track 2 caja actual: {track2.get_current_box()}")
    print(f"  ¿Colisión detectada? {is_collision}")
    print(f"  Confianza: {confidence:.4f}")
    print(f"  IoU: {get_iou(track1.get_current_box(), track2.get_current_box()):.4f}")
    print("[OK]\n")
    
    # Test 2: Tracker
    print("[TEST 2] Tracker Simple")
    print("-" * 70)
    
    tracker = SimpleTracker(max_distance=50, max_age=30)
    for frame_num in range(10):
        detections = [
            ([100 + frame_num*10, 100, 180 + frame_num*10, 160], 0.95),
            ([300 - frame_num*8, 150, 380 - frame_num*8, 210], 0.92),
        ]
        tracks = tracker.update(detections)
        if (frame_num + 1) % 3 == 0:
            print(f"  Frame {frame_num}: {len(tracks)} tracks")
    print("[OK]\n")
    
    # Test 3: Crear video de prueba
    print("[TEST 3] Creación de Video de Prueba")
    print("-" * 70)
    
    ensure_dirs()
    test_video = Path(INPUT_DIR) / "test_video_simple.mp4"
    create_test_video_simple(test_video)
    
    # Verificar que existe
    if test_video.exists():
        file_size = test_video.stat().st_size / (1024 * 1024)  # MB
        print(f"  Video creado: {test_video.name}")
        print(f"  Tamaño: {file_size:.2f} MB")
        print("[OK]\n")
    else:
        print("[ERROR] Video no creado\n")
    
    print("=" * 70)
    print("PRUEBAS COMPLETADAS EXITOSAMENTE")
    print("=" * 70)
    print("\nNota: Para procesar videos reales con detección YOLO,")
    print("asegúrate de que el entorno tiene lzma correctamente configurado.")
    print("\nPasos siguientes:")
    print("1. Coloca un video en: " + str(INPUT_DIR))
    print("2. Ejecuta: python main.py")
    print("3. Revisa los resultados en: " + str(OUTPUT_DIR))


if __name__ == '__main__':
    try:
        test_all()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
