"""
src/detector.py — Wrapper de YOLO con ByteTrack Integrado

Encapsula la carga del modelo YOLOv8 y el tracking integrado de Ultralytics.
Usa model.track() con ByteTrack para mantener IDs estables entre frames,
incluyendo detecciones de baja confianza para recuperar objetos ocluidos.

Referencia:
  - Ultralytics Tracking: model.track(source, persist=True, tracker="bytetrack.yaml")
  - ByteTrack (Zhang et al., 2022): tracking con detecciones de alta Y baja confianza
  - BoT-SORT (Aharon et al., 2022): tracking con ReID y compensación de movimiento de cámara
"""

import numpy as np
from ultralytics import YOLO
from config import YOLO_MODEL, YOLO_CONFIDENCE, VEHICLE_CLASS_IDS
from src.tracker import Track


class VehicleDetector:
    """
    Wrapper de YOLOv8 con tracking integrado (ByteTrack/BoT-SORT).

    Gestiona:
      - Carga del modelo (una sola vez)
      - Ejecución de detección + tracking en cada frame
      - Mapeo de resultados del tracker a objetos Track con historial cinemático
      - Persistencia del estado de los tracks entre frames
    """

    def __init__(self, model_path: str = None, tracker: str = "bytetrack",
                 confidence: float = None):
        """
        Args:
            model_path: ruta al modelo YOLO (.pt). Default: config.YOLO_MODEL
            tracker:    "bytetrack" | "botsort"
            confidence: umbral de confianza. Default: config.YOLO_CONFIDENCE
        """
        self.model_path  = model_path or YOLO_MODEL
        self.tracker_name = tracker
        self.confidence  = confidence or YOLO_CONFIDENCE
        self.tracks: dict[int, Track] = {}   # {track_id: Track}
        self._model = None
        self._load_model()

    def _load_model(self):
        """Carga el modelo YOLO (solo se ejecuta una vez)."""
        print(f"[INFO] Cargando modelo YOLO: {self.model_path}")
        self._model = YOLO(self.model_path)
        print(f"[INFO] Modelo cargado. Tracker: {self.tracker_name.upper()}")

    def reset(self):
        """Reinicia el estado de tracks (llamar al procesar un nuevo video)."""
        self.tracks.clear()
        # Ultralytics track(persist=True) guarda el estado internamente.
        # Para purgarlo por completo entre videos, recargamos el modelo.
        self._load_model()

    def process_frame(self, frame) -> dict:
        """
        Procesa un frame: detecta vehículos y actualiza los tracks.

        Usa model.track() de Ultralytics, que internamente ejecuta ByteTrack
        o BoT-SORT para asignar IDs estables entre frames.

        Args:
            frame: imagen BGR (numpy array de OpenCV)

        Returns:
            dict {track_id: Track} con todos los tracks activos
        """
        results = self._model.track(
            frame,
            conf=self.confidence,
            persist=True,              # mantiene estado del tracker entre frames
            tracker=f"{self.tracker_name}.yaml",
            verbose=False,
            classes=list(VEHICLE_CLASS_IDS),
        )

        active_ids = set()

        if results and results[0].boxes is not None:
            boxes = results[0].boxes

            # Extraer IDs asignados por el tracker (puede ser None si tracking falla)
            ids = boxes.id
            if ids is not None:
                ids_np = ids.cpu().numpy().astype(int)
            else:
                ids_np = None

            for idx, (box, conf, cls) in enumerate(
                zip(boxes.xyxy, boxes.conf, boxes.cls)
            ):
                cls_id  = int(cls.item())
                conf_v  = float(conf.item())
                box_lst = [float(v) for v in box.cpu().numpy()]

                # Obtener ID del tracker (o generar uno temporal)
                if ids_np is not None and idx < len(ids_np):
                    tid = int(ids_np[idx])
                else:
                    # Fallback: asignar ID por orden si el tracker no entrega IDs
                    tid = -(idx + 1)

                active_ids.add(tid)

                if tid in self.tracks:
                    self.tracks[tid].update(box_lst, conf_v, cls_id)
                else:
                    self.tracks[tid] = Track(tid, box_lst, conf_v, cls_id)

        # Marcar tracks no actualizados en este frame
        for tid in list(self.tracks.keys()):
            if tid not in active_ids:
                self.tracks[tid].mark_missed()
                # Eliminar tracks muy antiguos sin detección
                if self.tracks[tid].frames_since_update > 30:
                    del self.tracks[tid]

        return self.tracks

    def get_detections_log_entry(self, frame_num: int) -> list:
        """
        Retorna una lista de dicts para el log de detecciones del reporte JSON.
        """
        entries = []
        for tid, track in self.tracks.items():
            if track.frames_since_update == 0:  # solo los detectados en este frame
                box = track.get_current_box()
                if box:
                    entries.append({
                        "frame": frame_num,
                        "track_id": tid,
                        "box": box,
                        "confidence": round(float(track.confidences[-1]), 4),
                        "class": track.class_id,
                    })
        return entries
