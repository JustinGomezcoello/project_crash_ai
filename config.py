import os

ROOT = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT, "data")
INPUT_DIR = os.path.join(DATA_DIR, "input")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")

# Configuración del Modelo YOLO
YOLO_MODEL = "yolov8n.pt"  # nano model para velocidad
YOLO_CONFIDENCE = 0.5      # umbral de confianza

# Configuración de Tracking
MAX_DISTANCE = 150          # distancia máxima entre frames para asociar tracks
MAX_AGE = 30               # frames máximos sin detección antes de eliminar track

# Configuración de Detección de Colisiones
COLLISION_IOU_THRESHOLD = 0.3      # umbral de IoU para detectar solapamiento
COLLISION_MIN_FRAMES = 2            # frames consecutivos para confirmar colisión
COLLISION_VELOCITY_CHANGE = 0.4     # cambio de velocidad relativa para alerta
COLLISION_DISTANCE_THRESHOLD = 20   # píxeles de cercanía mínima

# Configuración de Video
TARGET_FPS = 30                     # frames por segundo objetivo
TARGET_WIDTH = 640                  # ancho de procesamiento
TARGET_HEIGHT = 480                 # alto de procesamiento
MAINTAIN_ASPECT_RATIO = True        # mantener relación de aspecto

# Añadido: parámetros de evaluación y logging
EVAL_TOLERANCE_FRAMES = 5       # tolerancia temporal para emparejar eventos
LOGGING_LEVEL = "INFO"          # DEBUG/INFO/WARNING/ERROR
RESULTS_DIR = os.path.join(ROOT, "results")

# Clases de vehículo (COCO): 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASS_IDS = (2, 3, 5, 7)

# Normalización/resize (reduce costo y estabiliza señales)
PROCESS_MAX_WIDTH = 960

# Contacto (candidato a colisión)
CONTACT_IOU_THRESHOLD = 0.08          # IoU bajo para "contacto" inicial
CONTACT_DISTANCE_RATIO = 0.45         # distancia <= mean_diag * ratio

# Persistencia/anti-falsos positivos
PERSISTENCE_FRAMES = 3                # frames consecutivos para confirmar evento
EVENT_COOLDOWN_FRAMES = 20            # evita repetir el mismo evento en frames seguidos
HISTORY_SIZE = 12                     # historial de centros por track (para velocidad)

# (Nuevo) Gate fuerte para reportar una colisión final (no solo contacto)
# Se recomienda mantenerlo bajo, pero exigir persistencia + señales temporales.
COLLISION_SCORE_THRESHOLD = 0.25

# (Nuevo) Caída de velocidad (heurística): si ambos reducen velocidad relativa bruscamente
SUDDEN_SPEED_DROP_RATIO = 0.2

# (Nuevo) Ventana temporal para estimar señales (frames)
FRAME_HISTORY = 5

