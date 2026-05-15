import re

# PATCH UTILS.PY
with open('utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add draw_alert support for severity
old_draw_alert = """def draw_alert(frame, frame_num, confidence=None):
    \"\"\"Dibuja alerta de colisiA3n detectada en el frame.\"\"\"
    h, w = frame.shape[:2]
    
    # Banner rojo en la parte superior
    cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 255), -1)
    
    # Texto de alerta
    text = f"COLISION DETECTADA - Frame: {frame_num}"
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    if confidence:
        confidence_text = f"Confianza: {confidence:.2f}"
        cv2.putText(frame, confidence_text, (w - 250, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return frame"""

new_draw_alert = """def draw_alert(frame, frame_num, confidence=None, severity=""):
    \"\"\"Dibuja alerta de colisiA3n detectada en el frame.\"\"\"
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
    
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    if confidence:
        confidence_text = f"Conf: {confidence:.2f}"
        cv2.putText(frame, confidence_text, (w - 250, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return frame

def draw_trajectory(frame, track, color=(0, 255, 255), thickness=2):
    \"\"\"Dibuja la estela de la trayectoria (historial de centros) de un track.\"\"\"
    if len(track.boxes) < 2:
        return frame
    
    points = []
    for box in track.boxes:
        c = get_box_center(box)
        points.append([int(c[0]), int(c[1])])
        
    pts = np.array(points, np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(frame, [pts], False, color, thickness)
    return frame"""

content = content.replace(old_draw_alert, new_draw_alert)

with open('utils.py', 'w', encoding='utf-8') as f:
    f.write(content)


# PATCH VIDEO_PROCESSOR.PY
with open('video_processor.py', 'r', encoding='utf-8') as f:
    vp_content = f.read()

# Make sure draw_trajectory is imported
if "from utils import " in vp_content:
    vp_content = re.sub(r'from utils import (.*)', r'from utils import \1, draw_trajectory', vp_content)

# Update collision unpacking
vp_content = vp_content.replace('for tid1, tid2, fn, conf in collisions:', 'for tid1, tid2, fn, conf, severity in collisions:')
vp_content = vp_content.replace('current_max_conf = max([c[3] for c in collisions], default=0)', 'current_max_conf = max([c[3] for c in collisions], default=0)\n                current_severity = collisions[0][4] if collisions else ""')

# Update draw_alert call
vp_content = vp_content.replace('frame_annotated = draw_alert(frame_annotated, frame_num, current_max_conf)', 'frame_annotated = draw_alert(frame_annotated, frame_num, current_max_conf, current_severity if "current_severity" in locals() else "")')

# Add draw_trajectory call inside tracks loop
track_loop_old = """                    if track_id in current_colliding_tracks:
                        color = (0, 0, 255)  # Rojo si esta colisionando (o ha colisionado recientemente)
                    
                    label = f"ID:{track_id}"
                    frame_annotated = draw_box(frame_annotated, box, label, color)"""

track_loop_new = """                    if track_id in current_colliding_tracks:
                        color = (0, 0, 255)  # Rojo si esta colisionando (o ha colisionado recientemente)
                    
                    label = f"ID:{track_id}"
                    frame_annotated = draw_box(frame_annotated, box, label, color)
                    # Dibujar trayectoria (estela)
                    frame_annotated = draw_trajectory(frame_annotated, track, color, thickness=1)"""

vp_content = vp_content.replace(track_loop_old, track_loop_new)

# Add severity to report
vp_content = vp_content.replace(
    "'confidence': float(conf)\n                    })",
    "'confidence': float(conf),\n                        'severity': severity\n                    })"
)

with open('video_processor.py', 'w', encoding='utf-8') as f:
    f.write(vp_content)

print("Patched video_processor.py and utils.py")
