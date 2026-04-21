import os

ROOT = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT, "data")
INPUT_DIR = os.path.join(DATA_DIR, "input")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")

# Configuración del Modelo YOLO
YOLO_MODEL = "yolov8n.pt"  # nano model para velocidad
YOLO_CONFIDENCE = 0.5      # umbral de confianza

# Configuración de Tracking
MAX_DISTANCE = 50          # distancia máxima entre frames para asociar tracks
MAX_AGE = 30               # frames máximos sin detección antes de eliminar track

# Configuración de Detección de Colisiones
COLLISION_IOU_THRESHOLD = 0.3      # umbral de IoU para detectar solapamiento
COLLISION_MIN_FRAMES = 3            # frames consecutivos para confirmar colisión
COLLISION_VELOCITY_CHANGE = 0.4     # cambio de velocidad relativa para alerta
COLLISION_DISTANCE_THRESHOLD = 20   # píxeles de cercanía mínima

# Configuración de Video
TARGET_FPS = 30                     # frames por segundo objetivo
TARGET_WIDTH = 640                  # ancho de procesamiento
TARGET_HEIGHT = 480                 # alto de procesamiento
MAINTAIN_ASPECT_RATIO = True        # mantener relación de aspecto
