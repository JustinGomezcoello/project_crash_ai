"""
src/video_processor.py — Pipeline Principal de Procesamiento de Video

Orquesta el flujo completo:
  1. Lectura frame-by-frame con OpenCV
  2. Detección y tracking con YOLOv8 + ByteTrack (VehicleDetector)
  3. Análisis de colisiones multi-señal (analyze_collisions)
  4. Anotación visual (cajas, trayectorias, alertas, panel info)
  5. Escritura del video de salida
  6. Captura de frames de evidencia forense (JPG)
  7. Log de eventos (events.csv)
  8. Reporte JSON estructurado

Arquitectura inspirada en:
  - akshat4703/accident_prediction: fusión multi-señal y video etiquetado
  - 000jd/Accident-Detection-yolov8-streamlit: pipeline de carga y resultado
  - aayush010904/SaferoadAI: captura de frames de evidencia al momento del accidente
"""

import os
import glob
import csv
import cv2
from datetime import datetime
from pathlib import Path

from config import (
    OUTPUT_DIR, TARGET_FPS, YOLO_TRACKER,
    CLEAR_OUTPUT_ON_RUN,
    EVIDENCE_FRAMES_DIR, EVENTS_CSV,
)
from src.detector import VehicleDetector
from src.collision_logic import analyze_collisions, reset_state, set_frame_dimensions
from src.utils import (
    ensure_dirs, list_input_files,
    draw_box, draw_alert, draw_trajectory, draw_info_panel,
    format_time, save_report,
    save_evidence_frame, append_event_csv,
)


def clear_previous_outputs():
    """
    LIMPIEZA TOTAL: borra TODOS los archivos generados en ejecuciones
    anteriores para que solo queden los resultados de la ejecucion actual.

    Directorios limpiados:
      - data/output/   → TODOS los archivos (videos, reportes, cualquiera)
      - evidence/frames/ → TODOS los frames de evidencia
      - evidence/events.csv → se borra y recrea con cabecera limpia
    """
    # ── Borrar TODO en data/output/ ─────────────────────────────────────
    if os.path.isdir(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            fp = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except OSError:
                    pass

    # ── Borrar TODO en evidence/frames/ ─────────────────────────────────
    if os.path.isdir(EVIDENCE_FRAMES_DIR):
        for f in os.listdir(EVIDENCE_FRAMES_DIR):
            fp = os.path.join(EVIDENCE_FRAMES_DIR, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except OSError:
                    pass

    # ── Borrar events.csv y recrear con cabecera limpia ─────────────────
    try:
        if os.path.exists(EVENTS_CSV):
            os.remove(EVENTS_CSV)
    except OSError:
        pass

    print("[INFO] Resultados anteriores eliminados (limpieza automatica)")


class VideoProcessor:
    """
    Pipeline de procesamiento de video para detección de colisiones.

    Attributes:
        detector: VehicleDetector (YOLO + ByteTrack)
        confidence: umbral de confianza YOLO
        tracker_name: "bytetrack" | "botsort"
    """

    def __init__(self, tracker: str = None, confidence: float = None):
        """
        Args:
            tracker:    "bytetrack" | "botsort". Default: config.YOLO_TRACKER
            confidence: umbral de confianza YOLO. Default: config.YOLO_CONFIDENCE
        """
        ensure_dirs()
        tracker = tracker or YOLO_TRACKER
        self.detector = VehicleDetector(tracker=tracker, confidence=confidence)
        self._cleaned = False  # flag para evitar doble limpieza

    # ------------------------------------------------------------------ #

    def process_video(
        self,
        video_path: str,
        output_video: str = None,
        output_report: str = None,
        save_evidence: bool = True,
        progress_callback=None,
    ) -> dict:
        """
        Procesa un video completo y detecta colisiones.

        Args:
            video_path:       Ruta del video de entrada
            output_video:     Ruta del video de salida (None = auto)
            output_report:    Nombre del reporte JSON (None = auto)
            save_evidence:    Si guardar frames de evidencia y log CSV
            progress_callback: función(frame_num, total_frames) para Streamlit

        Returns:
            dict con reporte completo de resultados
        """
        if not os.path.exists(video_path):
            print(f"[ERROR] Archivo no encontrado: {video_path}")
            return None

        # Limpiar salidas de la ejecucion anterior (solo la primera vez)
        if CLEAR_OUTPUT_ON_RUN and not self._cleaned:
            clear_previous_outputs()
            self._cleaned = True

        video_name = os.path.basename(video_path)
        print(f"\n[INFO] Procesando: {video_name}")

        # ── Abrir video ───────────────────────────────────────────────────
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("[ERROR] No se pudo abrir el video")
            return None

        fps          = cap.get(cv2.CAP_PROP_FPS) or TARGET_FPS
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Informar al motor de colisiones las dimensiones reales del frame
        set_frame_dimensions(frame_w, frame_h)

        print(f"[INFO] Resolucion: {frame_w}x{frame_h} | FPS: {fps} | Frames: {total_frames}")

        # ── Preparar salida de video ──────────────────────────────────────
        if output_video is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_video = os.path.join(OUTPUT_DIR, f"crash_detected_{ts}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out    = cv2.VideoWriter(output_video, fourcc, fps, (frame_w, frame_h))

        # ── Reiniciar estado del motor de colisiones ──────────────────────
        reset_state()
        self.detector.reset()

        # ── Variables de estado del pipeline ─────────────────────────────
        frame_num           = 0
        detections_log      = []
        collisions_detected = []
        alert_remaining     = 0        # frames que queda activa la alerta visual
        current_severity    = ""
        current_conf        = 0.0
        current_ttc         = None
        colliding_ids       = set()

        print("[INFO] Iniciando detección...")

        # ── Loop principal ────────────────────────────────────────────────
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 1) Detección + tracking
            tracks = self.detector.process_frame(frame)
            detections_log.extend(self.detector.get_detections_log_entry(frame_num))

            # 2) Análisis de colisiones
            collisions = analyze_collisions(tracks, current_frame=frame_num)

            if collisions:
                alert_remaining  = int(fps * 2.5)   # alerta visible ~2.5 segundos
                current_conf     = max(c[3] for c in collisions)
                current_severity = collisions[0][4]
                current_ttc      = collisions[0][5] if len(collisions[0]) > 5 else None
                colliding_ids    = set()

                for col in collisions:
                    tid1, tid2, fn, conf, sev = col[:5]
                    ttc = col[5] if len(col) > 5 else float('inf')
                    colliding_ids.update({tid1, tid2})

                    event = {
                        "frame":       frame_num,
                        "timestamp":   format_time(frame_num, fps),
                        "track_id_1":  int(tid1) if str(tid1).lstrip('-').isdigit() else tid1,
                        "track_id_2":  int(tid2) if str(tid2).lstrip('-').isdigit() else tid2,
                        "confidence":  round(float(conf), 4),
                        "severity":    sev,
                        "ttc_frames":  round(float(ttc), 2) if ttc != float('inf') else None,
                    }
                    collisions_detected.append(event)

                    # 3) Guardar evidencia forense
                    if save_evidence:
                        ev_frame_annotated = self._annotate_frame(
                            frame.copy(), tracks, colliding_ids,
                            frame_num, fps, current_conf, current_severity, current_ttc,
                            alert_active=True
                        )
                        ev_filename = save_evidence_frame(ev_frame_annotated, frame_num, video_name)
                        append_event_csv(
                            video_name, frame_num, fps,
                            tid1, tid2, conf, sev, ev_filename
                        )

            elif alert_remaining > 0:
                alert_remaining -= 1
                if alert_remaining == 0:
                    colliding_ids.clear()

            # 4) Anotar y escribir frame
            annotated = self._annotate_frame(
                frame.copy(), tracks, colliding_ids,
                frame_num, fps, current_conf, current_severity, current_ttc,
                alert_active=(alert_remaining > 0)
            )
            out.write(annotated)

            # 5) Progreso
            if (frame_num + 1) % 30 == 0:
                pct = (frame_num + 1) / max(total_frames, 1) * 100
                print(f"[PROGRESS] {frame_num + 1}/{total_frames} ({pct:.1f}%)")
            if progress_callback:
                progress_callback(frame_num + 1, total_frames)

            frame_num += 1

        # ── Cerrar recursos ───────────────────────────────────────────────
        cap.release()
        out.release()

        print(f"[INFO] Video guardado: {output_video}")
        print(f"[INFO] Colisiones detectadas: {len(collisions_detected)}")

        # ── Generar reporte JSON ──────────────────────────────────────────
        report = {
            "input_file":    video_name,
            "output_file":   os.path.basename(output_video),
            "tracker":       self.detector.tracker_name,
            "processing_ts": datetime.now().isoformat(),
            "video_info": {
                "resolution":       f"{frame_w}x{frame_h}",
                "fps":              fps,
                "total_frames":     total_frames,
                "duration_seconds": round(total_frames / fps, 2),
            },
            "summary": {
                "total_detections":  len(detections_log),
                "frames_processed":  frame_num,
                "collisions_found":  len(collisions_detected),
            },
            "collisions":     collisions_detected,
            "detections_log": detections_log,
        }

        if output_report is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_report = f"report_{ts}.json"
        report_path = save_report(report, output_report)
        print(f"[INFO] Reporte guardado: {report_path}")

        return report

    # ------------------------------------------------------------------ #

    def _annotate_frame(self, frame, tracks: dict, colliding_ids: set,
                        frame_num: int, fps: float,
                        conf: float, severity: str, ttc,
                        alert_active: bool) -> object:
        """Aplica todas las anotaciones visuales a un frame."""

        # Dibujar tracks
        for tid, track in tracks.items():
            if len(track.boxes) < 1:
                continue

            box      = track.get_current_box()
            is_crash = tid in colliding_ids

            if is_crash:
                color = (0, 0, 255)      # Rojo → involucrado en colisión
                thick = 3
            elif track.frames_since_update > 0:
                color = (100, 100, 100)  # Gris → perdido temporalmente
                thick = 1
            else:
                color = (0, 220, 60)     # Verde → normal
                thick = 2

            label = f"ID:{tid}"
            speed = track.get_current_speed()
            if speed > 0.5:
                label += f" {speed:.1f}px/f"

            draw_box(frame, box, label, color, thick)
            draw_trajectory(frame, track, color, thickness=1)

        # Alerta de colisión
        if alert_active:
            draw_alert(frame, frame_num, conf, severity, ttc)

        # Panel de información
        draw_info_panel(frame, tracks, fps, frame_num)

        return frame

    # ------------------------------------------------------------------ #

    def process_all_videos(self, save_evidence: bool = True) -> list:
        """Procesa todos los videos en la carpeta input."""
        videos = list_input_files('.mp4')
        if not videos:
            print("[WARNING] No hay archivos .mp4 en data/input/")
            return []

        print(f"\n[INFO] Encontrados {len(videos)} video(s)")
        results = []
        for vp in videos:
            r = self.process_video(vp, save_evidence=save_evidence)
            if r:
                results.append(r)
        return results
