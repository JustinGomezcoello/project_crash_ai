"""
config.py — Configuración Centralizada del Sistema

Todos los parámetros ajustables del sistema en un solo lugar.
Modifica aquí para calibrar el comportamiento sin tocar el código.
"""
import os

ROOT = os.path.dirname(__file__)

# ── Directorios principales ─────────────────────────────────────────────
DATA_DIR            = os.path.join(ROOT, "data")
INPUT_DIR           = os.path.join(DATA_DIR, "input")
OUTPUT_DIR          = os.path.join(DATA_DIR, "output")
EVIDENCE_DIR        = os.path.join(ROOT, "evidence")
EVIDENCE_FRAMES_DIR = os.path.join(EVIDENCE_DIR, "frames")
EVENTS_CSV          = os.path.join(EVIDENCE_DIR, "events.csv")
RESULTS_DIR         = os.path.join(ROOT, "results")

# ── Modelo YOLO ─────────────────────────────────────────────────────────
YOLO_MODEL      = "yolov8n.pt"   # yolov8n | yolov8s | yolov8m
YOLO_CONFIDENCE = 0.40           # umbral de confianza de detección
YOLO_TRACKER    = "bytetrack"    # "bytetrack" | "botsort"

# Clases COCO de vehículos: 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASS_IDS = (2, 3, 5, 7)

# ── Tracking ─────────────────────────────────────────────────────────────
MAX_DISTANCE = 150   # píxeles máx. entre frames para asociar tracks (tracker manual fallback)
MAX_AGE      = 30    # frames máx. sin detección antes de eliminar track
TRACK_MIN_AGE = 3    # frames mínimos para considerar un track válido
TRACK_MAX_MISSED = 5 # grace period: frames perdidos antes de excluir del análisis

# ── Detección de Colisiones ──────────────────────────────────────────────
COLLISION_IOU_THRESHOLD  = 0.30   # IoU mínimo para considerar contacto
COLLISION_MIN_FRAMES     = 2      # frames consecutivos para confirmar evento
COLLISION_VELOCITY_CHANGE = 0.40  # cambio mínimo de velocidad relativa
COLLISION_SCORE_THRESHOLD = 0.25  # score mínimo de fusión para reportar colisión

# ── Señales cinemáticas ──────────────────────────────────────────────────
CONTACT_IOU_THRESHOLD   = 0.08   # IoU bajo para detección de "contacto inicial"
CONTACT_DISTANCE_RATIO  = 0.45   # distancia <= mean_diagonal * ratio → contacto
SUDDEN_SPEED_DROP_RATIO = 0.20   # caída de velocidad > 20% → señal de impacto
FRAME_HISTORY           = 5      # ventana temporal para estimar señales

# ── Time-to-Collision (TTC) ──────────────────────────────────────────────
TTC_CRITICAL_FRAMES     = 8      # si TTC < 8 frames → riesgo alto
TTC_MIN_CLOSING_RATE    = 1.5    # píxeles/frame mínimos de acercamiento para activar TTC

# ── Anti-falsos positivos ────────────────────────────────────────────────
PERSISTENCE_FRAMES    = 3    # frames consecutivos necesarios para confirmar evento
EVENT_COOLDOWN_FRAMES = 20   # frames de espera tras evento (evita duplicados)

# ── Video ────────────────────────────────────────────────────────────────
TARGET_FPS    = 30
TARGET_WIDTH  = 640
TARGET_HEIGHT = 480
MAINTAIN_ASPECT_RATIO = True

# ── Evaluación ───────────────────────────────────────────────────────────
EVAL_TOLERANCE_FRAMES = 5    # tolerancia temporal para emparejar eventos GT
LOGGING_LEVEL         = "INFO"
