"""
test_implementation.py - Script de prueba para verificar la implementación
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# Importar módulos del proyecto
from config import INPUT_DIR, OUTPUT_DIR, TARGET_WIDTH, TARGET_HEIGHT
from collision_logic import SimpleTracker, detect_collision_advanced, Track
from utils import ensure_dirs, draw_box, draw_alert, get_iou, get_box_distance


def create_test_video(output_path, filename="test_video.mp4", duration=5):
    """Crea un video de prueba con dos vehículos aproximándose."""
    print(f"[INFO] Creando video de prueba: {filename}")
    
    # Parámetros
    fps = 30
    width, height = 640, 480
    num_frames = int(fps * duration)
    
    # Crear escritor
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Crear frames
    for frame_num in range(num_frames):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 200
        
        # Simular dos vehículos aproximándose
        # Vehículo 1: se mueve de izquierda a derecha
        x1 = 50 + frame_num * (width - 100) / num_frames
        y1 = height // 3
        w1, h1 = 80, 60
        
        # Vehículo 2: se mueve de derecha a izquierda
        x2 = width - 50 - frame_num * (width - 100) / num_frames
        y2 = height // 2
        w2, h2 = 80, 60
        
        # Dibujar vehículos
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x1+w1), int(y1+h1)), (0, 255, 0), 2)
        cv2.rectangle(frame, (int(x2), int(y2)), (int(x2+w2), int(y2+h2)), (0, 255, 0), 2)
        
        # Añadir texto
        cv2.putText(frame, f"Frame: {frame_num}/{num_frames}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Si están muy cerca, dibujar alerta
        distance = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
        if distance < 100:
            cv2.putText(frame, "PROXIMIDAD DETECTADA", (150, 400), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        out.write(frame)
    
    out.release()
    print(f"[OK] Video de prueba creado: {output_path}")
    return output_path


def test_collision_logic():
    """Prueba la lógica de colisión."""
    print("\n" + "="*60)
    print("PRUEBA: Lógica de Colisión")
    print("="*60)
    
    # Crear tracks de prueba
    track1 = Track(1, [100, 100, 180, 160], 0.9)
    track2 = Track(2, [150, 120, 230, 180], 0.85)
    
    # Simular movimiento (aproximación)
    for i in range(5):
        # Vehículo 1 se mueve a la derecha
        new_box1 = [100 + i*20, 100, 180 + i*20, 160]
        track1.update(new_box1, 0.9 - i*0.05)
        
        # Vehículo 2 se mueve a la izquierda
        new_box2 = [150 - i*15, 120, 230 - i*15, 180]
        track2.update(new_box2, 0.85 - i*0.05)
    
    # Analizar colisión
    is_collision, confidence = detect_collision_advanced(track1, track2)
    
    print(f"[TEST] Track 1 - Caja actual: {track1.get_current_box()}")
    print(f"[TEST] Track 2 - Caja actual: {track2.get_current_box()}")
    print(f"[TEST] ¿Colisión detectada? {is_collision}")
    print(f"[TEST] Confianza: {confidence:.4f}")
    
    # Calcular IoU
    iou = get_iou(track1.get_current_box(), track2.get_current_box())
    print(f"[TEST] IoU actual: {iou:.4f}")
    
    print("[OK] Prueba completada")


def test_tracker():
    """Prueba el tracker simple."""
    print("\n" + "="*60)
    print("PRUEBA: Tracker Simple")
    print("="*60)
    
    tracker = SimpleTracker(max_distance=50, max_age=30)
    
    # Simular detecciones en varios frames
    for frame_num in range(10):
        detections = [
            ([100 + frame_num*10, 100, 180 + frame_num*10, 160], 0.95),
            ([300 - frame_num*8, 150, 380 - frame_num*8, 210], 0.92),
        ]
        
        tracks = tracker.update(detections)
        
        print(f"Frame {frame_num}: {len(tracks)} tracks activos")
        for tid, track in tracks.items():
            print(f"  Track {tid} - Edad: {track.age}, Frames: {len(track.boxes)}")
    
    print("[OK] Prueba completada")


def test_integration():
    """Prueba de integración: crear video de prueba y procesarlo."""
    print("\n" + "="*60)
    print("PRUEBA: Integración Completa")
    print("="*60)
    
    ensure_dirs()
    
    # Crear video de prueba
    test_video = Path(INPUT_DIR) / "test_video.mp4"
    create_test_video(str(test_video), duration=3)
    
    # Procesar video
    from video_processor import VideoProcessor
    
    try:
        processor = VideoProcessor()
        result = processor.process_video(str(test_video))
        
        if result:
            print("\n[OK] Procesamiento completado")
            print(f"[INFO] Colisiones detectadas: {result['collisions_detected']}")
            print(f"[INFO] Video de salida: {result['output_file']}")
        else:
            print("[ERROR] El procesamiento falló")
    except Exception as e:
        print(f"[ERROR] Error durante el procesamiento: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Ejecuta todas las pruebas."""
    print("\n" + "="*60)
    print("PRUEBAS DE IMPLEMENTACIÓN")
    print("Sección 2: Diseño e Implementación")
    print("="*60)
    
    try:
        # Prueba 1: Lógica de colisión
        test_collision_logic()
        
        # Prueba 2: Tracker
        test_tracker()
        
        # Prueba 3: Integración
        test_integration()
        
        print("\n" + "="*60)
        print("TODAS LAS PRUEBAS COMPLETADAS")
        print("="*60)
        
    except Exception as e:
        print(f"\n[ERROR] Fallo en las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
