"""
Módulo principal: VideoProcessor
Procesa videos de vigilancia para detectar colisiones de vehículos.
"""

import cv2
import json
import os
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO
from config import (
    YOLO_MODEL, YOLO_CONFIDENCE, INPUT_DIR, OUTPUT_DIR,
    TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS, MAINTAIN_ASPECT_RATIO
)
from collision_logic import SimpleTracker, analyze_collisions
from utils import ensure_dirs, list_input_files, draw_box, draw_alert, format_time, save_report, draw_trajectory


class VideoProcessor:
    """Procesa videos para detectar colisiones."""
    
    def __init__(self):
        self.ensure_dirs()
        print("[INFO] Cargando modelo YOLO...")
        self.model = YOLO(YOLO_MODEL)
        self.tracker = SimpleTracker()
        print("[INFO] Modelo cargado correctamente")
    
    def ensure_dirs(self):
        """Asegura directorios necesarios."""
        ensure_dirs()
    
    def process_video(self, video_path, output_video=None, output_report=None):
        """
        Procesa un video y detecta colisiones.
        
        Args:
            video_path: ruta del video de entrada
            output_video: ruta del video de salida (opcional)
            output_report: ruta del reporte JSON (opcional)
        
        Returns:
            dict con resultados
        """
        
        # Validar entrada
        if not os.path.exists(video_path):
            print(f"[ERROR] Archivo no encontrado: {video_path}")
            return None
        
        print(f"\n[INFO] Procesando: {os.path.basename(video_path)}")
        
        # Abrir video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("[ERROR] No se pudo abrir el video")
            return None
        
        # Obtener metadatos
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or TARGET_FPS
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"[INFO] Resolución: {frame_width}x{frame_height}")
        print(f"[INFO] FPS: {fps}, Frames: {total_frames}")
        
        # Preparar escritor de video de salida
        if output_video is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_video = os.path.join(OUTPUT_DIR, f"crash_detected_{timestamp}.mp4")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video, fourcc, fps, (frame_width, frame_height))
        
        # Procesamiento
        frame_num = 0
        detections_log = []
        collisions_detected = []
        collision_frames = {}  # {frame_num: [(tid1, tid2, conf), ...]}
        
        alert_frames_remaining = 0
        current_max_conf = 0.0
        current_colliding_tracks = set()
        
        print("[INFO] Iniciando detección...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detección con YOLO
            results = self.model(frame, conf=YOLO_CONFIDENCE, verbose=False)
            
            # Extraer detecciones (solo vehículos, clase 2 en COCO)
            detections = []
            for r in results:
                for box, conf, cls in zip(r.boxes.xyxy, r.boxes.conf, r.boxes.cls):
                    cls_id = int(cls.item())
                    # Clases COCO: 2=car, 5=bus, 7=truck, 9=bottle (ignorar)
                    if cls_id in [2, 5, 7]:  # vehículos
                        box_list = [float(x) for x in box.cpu().numpy()]
                        conf_val = float(conf.item())
                        detections.append((box_list, conf_val))
                        detections_log.append({
                            'frame': frame_num,
                            'box': box_list,
                            'confidence': conf_val,
                            'class': cls_id
                        })
            
            # Actualizar tracker
            tracks = self.tracker.update(detections)
            
            # Detectar colisiones
            collisions = analyze_collisions(tracks)
            if collisions:
                collision_frames[frame_num] = collisions
                alert_frames_remaining = 45  # Mantener la alerta en pantalla (aprox 1.5s)
                current_max_conf = max([c[3] for c in collisions], default=0)
                current_severity = collisions[0][4] if collisions else ""
                current_colliding_tracks.clear()
                
                for tid1, tid2, fn, conf, severity in collisions:
                    current_colliding_tracks.add(tid1)
                    current_colliding_tracks.add(tid2)
                    collisions_detected.append({
                        'frame': frame_num,
                        'timestamp': format_time(frame_num, fps),
                        'track_id_1': tid1,
                        'track_id_2': tid2,
                        'confidence': float(conf),
                        'severity': severity
                    })
            elif alert_frames_remaining > 0:
                alert_frames_remaining -= 1
                if alert_frames_remaining == 0:
                    current_colliding_tracks.clear()
            
            # Dibujar en frame
            frame_annotated = frame.copy()
            
            # Dibujar tracks
            for track_id, track in tracks.items():
                if len(track.boxes) >= 2:  # Solo tracks con historia
                    box = track.get_current_box()
                    color = (0, 255, 0)  # Verde por defecto
                    
                    if track_id in current_colliding_tracks:
                        color = (0, 0, 255)  # Rojo si esta colisionando (o ha colisionado recientemente)
                    
                    label = f"ID:{track_id}"
                    frame_annotated = draw_box(frame_annotated, box, label, color)
                    # Dibujar trayectoria (estela)
                    frame_annotated = draw_trajectory(frame_annotated, track, color, thickness=1)
            
            # Dibujar alerta de colisión
            if alert_frames_remaining > 0:
                frame_annotated = draw_alert(frame_annotated, frame_num, current_max_conf, current_severity if "current_severity" in locals() else "")
            
            # Escribir frame
            out.write(frame_annotated)
            
            # Progreso
            if (frame_num + 1) % 30 == 0:
                progress = (frame_num + 1) / total_frames * 100
                print(f"[PROGRESS] {frame_num + 1}/{total_frames} ({progress:.1f}%)")
            
            frame_num += 1
        
        # Cerrar recursos
        cap.release()
        out.release()
        
        print(f"\n[INFO] Video guardado: {output_video}")
        print(f"[INFO] Colisiones detectadas: {len(collisions_detected)}")
        
        # Generar reporte
        report = {
            'input_file': os.path.basename(video_path),
            'output_file': os.path.basename(output_video),
            'processing_timestamp': datetime.now().isoformat(),
            'video_info': {
                'resolution': f"{frame_width}x{frame_height}",
                'fps': fps,
                'total_frames': total_frames,
                'duration_seconds': total_frames / fps
            },
            'total_detections': len(detections_log),
            'total_frames_processed': frame_num,
            'collisions_detected': len(collisions_detected),
            'collisions': collisions_detected,
            'detections_log': detections_log
        }
        
        # Guardar reporte
        if output_report is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_report = f"report_{timestamp}.json"
        
        report_path = save_report(report, output_report)
        print(f"[INFO] Reporte guardado: {report_path}")
        
        return report
    
    def process_all_videos(self):
        """Procesa todos los videos en la carpeta input."""
        video_files = list_input_files('.mp4')
        
        if not video_files:
            print("[WARNING] No se encontraron archivos .mp4 en data/input/")
            return
        
        print(f"\n[INFO] Encontrados {len(video_files)} video(s)")
        
        all_results = []
        for video_path in video_files:
            result = self.process_video(video_path)
            if result:
                all_results.append(result)
        
        return all_results


def main():
    """Función principal."""
    print("="*80)
    print("SISTEMA DE DETECCIÓN DE COLISIONES DE TRÁNSITO")
    print("="*80)
    
    processor = VideoProcessor()
    processor.process_all_videos()
    
    print("\n" + "="*80)
    print("PROCESAMIENTO COMPLETADO")
    print("="*80)


if __name__ == '__main__':
    main()

