import os
import json
import numpy as np
import cv2
from datetime import datetime
from config import INPUT_DIR, OUTPUT_DIR


def ensure_dirs():
    """Asegura que existen los directorios necesarios."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def list_input_files(extension='.mp4'):
    """Lista archivos de entrada con extensión específica."""
    files = []
    try:
        for f in os.listdir(INPUT_DIR):
            if f.lower().endswith(extension):
                files.append(os.path.join(INPUT_DIR, f))
    except FileNotFoundError:
        pass
    return files


def get_iou(box1, box2):
    """Calcula la Intersection over Union entre dos cajas."""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    
    if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
        return 0.0
    
    inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0


def get_box_center(box):
    """Obtiene el centro de una caja delimitadora."""
    x_min, y_min, x_max, y_max = box
    return ((x_min + x_max) / 2, (y_min + y_max) / 2)


def get_box_distance(box1, box2):
    """Calcula la distancia euclidiana entre los centros de dos cajas."""
    c1 = get_box_center(box1)
    c2 = get_box_center(box2)
    return np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)


def save_report(results, output_file):
    """Guarda un reporte JSON con los resultados de detección."""
    ensure_dirs()
    filepath = os.path.join(OUTPUT_DIR, output_file)
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    return filepath


def draw_box(frame, box, label, color=(0, 255, 0), thickness=2):
    """Dibuja una caja en un frame."""
    x_min, y_min, x_max, y_max = [int(v) for v in box]
    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, thickness)
    cv2.putText(frame, label, (x_min, y_min - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return frame


def draw_alert(frame, frame_num, confidence=None, severity=""):
    """Dibuja alerta de colisión detectada en el frame."""
    h, w = frame.shape[:2]
    
    # Colores por severidad
    bg_color = (0, 0, 255) # Rojo por defecto
    if severity == "Leve":
        bg_color = (0, 165, 255) # Naranja
    elif severity == "Moderado":
        bg_color = (0, 100, 255) # Naranja oscuro
    elif severity == "Severo":
        bg_color = (0, 0, 255) # Rojo
        
    # Banner en la parte superior
    cv2.rectangle(frame, (0, 0), (w, 60), bg_color, -1)
    
    # Texto de alerta
    text = f"COLISION DETECTADA"
    if severity:
        text += f" [{severity.upper()}]"
    else:
        text += f" - Frame: {frame_num}"
    
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    if confidence:
        confidence_text = f"Conf: {confidence:.2f}"
        cv2.putText(frame, confidence_text, (w - 250, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return frame

def draw_trajectory(frame, track, color=(0, 255, 255), thickness=2):
    """Dibuja la estela de la trayectoria (historial de centros) de un track."""
    if len(track.boxes) < 2:
        return frame
    
    points = []
    for box in track.boxes:
        c = get_box_center(box)
        points.append([int(c[0]), int(c[1])])
        
    pts = np.array(points, np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(frame, [pts], False, color, thickness)
    return frame


def format_time(frame_num, fps=30):
    """Convierte número de frame a hh:mm:ss."""
    seconds = frame_num / fps
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

