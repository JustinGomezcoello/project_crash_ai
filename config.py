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
YOLO_CONFIDENCE = 0.40           # umbral de confianza de deteccion
YOLO_TRACKER    = "bytetrack"    # "bytetrack" | "botsort"

# Clases COCO de vehiculos: 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASS_IDS = (2, 3, 5, 7)

# ── Tracking ─────────────────────────────────────────────────────────────
MAX_DISTANCE     = 150   # pixeles max entre frames para asociar tracks
MAX_AGE          = 30    # frames max sin deteccion antes de eliminar track
TRACK_MIN_AGE    = 4     # frames minimos para considerar un track valido
TRACK_MAX_MISSED = 4     # grace period: frames perdidos antes de excluir

# ── Deteccion de Colisiones (par de vehiculos DISTINTOS) ─────────────────
# Aplica SOLO cuando hay dos IDs distintos interactuando.
# El falso positivo anterior venia de la logica de VEHICULO UNICO,
# no de aqui — por eso estos umbrales se mantienen moderados.
COLLISION_IOU_THRESHOLD   = 0.25
COLLISION_MIN_FRAMES      = 2
COLLISION_VELOCITY_CHANGE = 0.40
# ─────────────────────────────────────────────────────────────────────────
# UMBRAL PRINCIPAL de fusion de 7 senales
#   0.25 → demasiado sensible (FP anteriores)
#   0.52 → demasiado restrictivo (no detecta nada)
#   0.38 → punto medio calibrado
# ─────────────────────────────────────────────────────────────────────────
COLLISION_SCORE_THRESHOLD = 0.38

# ── Senales cinematicas ──────────────────────────────────────────────────
CONTACT_IOU_THRESHOLD   = 0.10
CONTACT_DISTANCE_RATIO  = 0.40
# ─────────────────────────────────────────────────────────────────────────
# CAIDA DE VELOCIDAD para pares de vehiculos
#   0.20 → frenada normal en semaforo la activa (FP original)
#   0.50 → solo impactos brutales (se pierde el choque real)
#   0.32 → punto medio: frenazo brusco pero no de emergencia
# ─────────────────────────────────────────────────────────────────────────
SUDDEN_SPEED_DROP_RATIO = 0.32
FRAME_HISTORY           = 6

# ── Time-to-Collision (TTC) ──────────────────────────────────────────────
TTC_CRITICAL_FRAMES  = 6
TTC_MIN_CLOSING_RATE = 2.0

# ── Anti-falsos positivos ────────────────────────────────────────────────
# 3 frames @ 10 FPS = 0.3 seg de senal sostenida antes de confirmar par
PERSISTENCE_FRAMES    = 3
EVENT_COOLDOWN_FRAMES = 25

# ── Deteccion de vehiculo unico (impacto frontal dashcam) ────────────────
# ─────────────────────────────────────────────────────────────────────────
# Diagnostico real sobre ccd_crash_0X.mp4:
#   - area_ratio maximo de los vehiculos: ~0.088 (8.8% del frame)
#   - Los vehiculos nunca llenan la pantalla (son colisiones a distancia)
#   - FP original (frame 40, ID:30): area=0.078, velocidad AUMENTANDO (-21.7%)
#     -> el sistema detectaba aceleracion como colision (bug en la logica)
#
# Umbrales calibrados sobre datos reales:
#   area  >= 0.07  -> vehiculo ocupa >= 7% del frame (visible y prominente)
#   drop  >= 0.35  -> frenazo brusco del 35%+ (no aceleracion ni crucero)
#   sp_h  >= 2.0   -> tenia movimiento previo (no estaba parado)
# ─────────────────────────────────────────────────────────────────────────
SINGLE_VEHICLE_CRASH_ENABLED   = True
SINGLE_VEHICLE_MIN_AREA_RATIO  = 0.07   # vehiculo >= 7% del frame
SINGLE_VEHICLE_MIN_SPEED_DROP  = 0.35   # frenazo >= 35%

# ── Video ────────────────────────────────────────────────────────────────
TARGET_FPS    = 30
TARGET_WIDTH  = 640
TARGET_HEIGHT = 480
MAINTAIN_ASPECT_RATIO = True

# ── Limpieza automatica de salidas ───────────────────────────────────────
CLEAR_OUTPUT_ON_RUN = True

# ── Evaluacion ───────────────────────────────────────────────────────────
EVAL_TOLERANCE_FRAMES = 5
LOGGING_LEVEL         = "INFO"
