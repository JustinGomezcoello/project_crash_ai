"""
src/utils.py — Funciones Auxiliares de Geometría, Visualización y E/S

Funciones de geometría: IoU, distancia, centros.
Funciones de dibujo: cajas, alertas, trayectorias, panel de info.
Funciones de E/S: directorios, reportes JSON, log CSV de eventos.
"""

import os
import csv
import json
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from config import INPUT_DIR, OUTPUT_DIR, EVIDENCE_DIR, EVIDENCE_FRAMES_DIR, EVENTS_CSV


# ======================================================================= #
#  Gestión de directorios                                                   #
# ======================================================================= #

def ensure_dirs():
    """Crea todos los directorios necesarios del proyecto."""
    for d in [INPUT_DIR, OUTPUT_DIR, EVIDENCE_DIR, EVIDENCE_FRAMES_DIR]:
        os.makedirs(d, exist_ok=True)


def list_input_files(extension: str = '.mp4') -> list:
    """Lista archivos de entrada con extensión específica."""
    files = []
    try:
        for f in os.listdir(INPUT_DIR):
            if f.lower().endswith(extension):
                files.append(os.path.join(INPUT_DIR, f))
    except FileNotFoundError:
        pass
    return sorted(files)


# ======================================================================= #
#  Geometría                                                                #
# ======================================================================= #

def get_box_center(box: list) -> tuple:
    """Centro (cx, cy) de una caja [x1, y1, x2, y2]."""
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def get_iou(box1: list, box2: list) -> float:
    """Intersection over Union entre dos cajas."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    a1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    a2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = a1 + a2 - inter
    return float(inter / union) if union > 0 else 0.0


def get_box_distance(box1: list, box2: list) -> float:
    """Distancia euclidiana entre centros de dos cajas."""
    c1 = get_box_center(box1)
    c2 = get_box_center(box2)
    return float(np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2))


def get_box_diagonal(box: list) -> float:
    """Diagonal de una caja (proxy del tamaño del objeto)."""
    return float(np.sqrt((box[2] - box[0])**2 + (box[3] - box[1])**2))


# ======================================================================= #
#  Visualización                                                            #
# ======================================================================= #

SEVERITY_COLORS = {
    "Leve":     (0, 165, 255),   # Naranja
    "Moderado": (0, 80, 255),    # Naranja-rojo
    "Severo":   (0, 0, 255),     # Rojo
    "":         (0, 0, 220),     # Rojo por defecto
}


def draw_box(frame, box: list, label: str = "", color: tuple = (0, 220, 0),
             thickness: int = 2) -> np.ndarray:
    """Dibuja una caja delimitadora con etiqueta opcional."""
    x1, y1, x2, y2 = [int(v) for v in box]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    if label:
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def draw_trajectory(frame, track, color: tuple = (0, 220, 255),
                    thickness: int = 2) -> np.ndarray:
    """
    Dibuja la estela de trayectoria del objeto (historial de centros).
    La línea se va haciendo más tenue hacia el pasado para dar efecto de movimiento.
    """
    centers = track.get_center_history()
    if len(centers) < 2:
        return frame
    pts = [(int(c[0]), int(c[1])) for c in centers]
    for i in range(1, len(pts)):
        # Opacidad progresiva: más brillante en el presente
        alpha = i / len(pts)
        c = tuple(int(ch * alpha) for ch in color)
        t = max(1, int(thickness * alpha))
        cv2.line(frame, pts[i - 1], pts[i], c, t, cv2.LINE_AA)
    # Punto actual más visible
    cv2.circle(frame, pts[-1], 4, color, -1, cv2.LINE_AA)
    return frame


def draw_alert(frame, frame_num: int, confidence: float = None,
               severity: str = "", ttc: float = None) -> np.ndarray:
    """
    Banner de alerta de colisión en la parte superior del frame.
    Muestra severidad, confianza y TTC si están disponibles.
    """
    h, w = frame.shape[:2]
    bg_color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS[""])

    # Fondo semitransparente (blend)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 72), bg_color, -1)
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

    # Borde inferior del banner
    cv2.line(frame, (0, 72), (w, 72), (255, 255, 255), 1)

    # Texto principal
    main_text = "!! COLISION DETECTADA"
    if severity:
        main_text += f"  [{severity.upper()}]"
    cv2.putText(frame, main_text, (18, 48),
                cv2.FONT_HERSHEY_DUPLEX, 1.15, (255, 255, 255), 2, cv2.LINE_AA)

    # Info secundaria (derecha)
    info_parts = []
    if confidence is not None:
        info_parts.append(f"Conf: {confidence:.2f}")
    if ttc is not None and ttc < 50:
        info_parts.append(f"TTC: {ttc:.1f}f")
    info_parts.append(f"Frame: {frame_num}")
    info_text = "  |  ".join(info_parts)
    cv2.putText(frame, info_text, (18, 66),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 220), 1, cv2.LINE_AA)

    return frame


def draw_info_panel(frame, tracks: dict, fps: float = 10.0,
                    frame_num: int = 0) -> np.ndarray:
    """Panel de información en la esquina inferior izquierda."""
    h, w = frame.shape[:2]
    active = sum(1 for t in tracks.values() if t.frames_since_update <= 2)
    ts = format_time(frame_num, fps)

    panel_lines = [
        f"Tiempo: {ts}",
        f"Frame: {frame_num}",
        f"Vehiculos: {active}",
    ]
    y_start = h - 10 - len(panel_lines) * 22
    # Fondo
    cv2.rectangle(frame, (8, y_start - 6), (200, h - 6), (0, 0, 0), -1)
    cv2.rectangle(frame, (8, y_start - 6), (200, h - 6), (80, 80, 80), 1)
    for i, line in enumerate(panel_lines):
        cv2.putText(frame, line, (14, y_start + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (180, 255, 180), 1, cv2.LINE_AA)
    return frame


# ======================================================================= #
#  Formateo de tiempo                                                       #
# ======================================================================= #

def format_time(frame_num: int, fps: float = 30.0) -> str:
    """Convierte número de frame a hh:mm:ss."""
    total_s = frame_num / max(fps, 1e-6)
    h = int(total_s // 3600)
    m = int((total_s % 3600) // 60)
    s = int(total_s % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ======================================================================= #
#  E/S de reportes y evidencia                                             #
# ======================================================================= #

def save_report(report: dict, filename: str) -> str:
    """Guarda un reporte JSON en el directorio de salida."""
    ensure_dirs()
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return filepath


def save_evidence_frame(frame, frame_num: int, video_name: str) -> str:
    """
    Guarda el frame anotado del momento de colisión como evidencia forense.
    Retorna la ruta del archivo guardado.
    """
    ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    vid_stem = Path(video_name).stem
    filename = f"crash_{vid_stem}_f{frame_num:04d}_{ts}.jpg"
    filepath = os.path.join(EVIDENCE_FRAMES_DIR, filename)
    cv2.imwrite(filepath, frame)
    return filename


def append_event_csv(video_name: str, frame_num: int, fps: float,
                     tid1, tid2, confidence: float, severity: str,
                     evidence_filename: str):
    """
    Añade un evento de colisión al CSV acumulativo de evidencias.
    Usa modo append para no sobreescribir eventos anteriores.
    """
    ensure_dirs()
    filepath = EVENTS_CSV
    file_exists = os.path.exists(filepath)
    with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                'timestamp', 'video_file', 'frame_num', 'time_in_video',
                'track_id_1', 'track_id_2', 'confidence', 'severity',
                'evidence_frame'
            ])
        writer.writerow([
            datetime.now().isoformat(),
            os.path.basename(video_name),
            frame_num,
            format_time(frame_num, fps),
            int(tid1) if str(tid1).isdigit() else tid1,
            int(tid2) if str(tid2).isdigit() else tid2,
            round(float(confidence), 4),
            severity,
            evidence_filename
        ])
