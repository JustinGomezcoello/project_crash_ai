# Arquitectura del Sistema — Project Crash AI

## Visión General

Project Crash AI es un sistema de detección de colisiones vehiculares basado en visión por computadora. Procesa video de cámaras de tránsito (CCTV/dashcam) frame a frame para identificar eventos de colisión mediante un pipeline de análisis multi-señal.

## Diagrama de Flujo del Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VIDEO INPUT (.mp4)                          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  OpenCV frame-by-frame
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DETECCIÓN — YOLOv8n (Ultralytics)                │
│   Clases: car(2), motorcycle(3), bus(5), truck(7)  [COCO dataset]   │
│   Confianza mínima: 0.40  |  Modelo: yolov8n.pt (6.2 MB)           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  Bounding boxes + confidences
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│               TRACKING — ByteTrack (Zhang et al., 2022)             │
│   • Asigna IDs estables entre frames                                │
│   • Usa detecciones de ALTA y BAJA confianza (anti-oclusión)        │
│   • Integrado via model.track(persist=True, tracker="bytetrack")   │
│   • Clase Track: mantiene historial de cajas y velocidades          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  dict{track_id: Track}
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              ANÁLISIS DE COLISIONES — Fusión Multi-Señal            │
│                                                                     │
│   Señal 1 (peso 8%)  : IoU — solapamiento de cajas                 │
│   Señal 2 (peso 8%)  : Distancia normalizada por diagonal           │
│   Señal 3 (peso 7%)  : Velocidad relativa entre vehículos           │
│   Señal 4 (peso 15%) : Persistencia temporal (frames consecutivos)  │
│   Señal 5 (peso 25%) : Caída brusca de velocidad (impacto)         │
│   Señal 6 (peso 17%) : Cambio angular de trayectoria               │
│   Señal 7 (peso 20%) : Time-to-Collision / TTC (ISO 22839)         │
│                                                                     │
│   Anti-falso-positivos:                                             │
│     • Persistencia: N frames consecutivos para confirmar            │
│     • Cooldown: silencio de 20 frames tras evento reportado         │
│     • Grace period: hasta 5 frames sin detección (oclusión)        │
│     • Filtro duplicados: cajas siempre solapadas → ignorar          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  Colisiones + severidad + TTC
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  CLASIFICACIÓN DE SEVERIDAD                          │
│   Leve:     caída velocidad < 40% y ángulo < 40° y TTC > 4f        │
│   Moderado: caída velocidad 40-70% o ángulo 40-80° o TTC 2-4f      │
│   Severo:   caída velocidad > 70% o ángulo > 80° o TTC < 2f        │
└─────────────────────────────┬───────────────────────┬───────────────┘
                              │                       │
                              ▼                       ▼
┌──────────────────────┐  ┌──────────────────────────────────────────┐
│  SALIDA VISUAL       │  │  EVIDENCIA FORENSE                        │
│  • Video anotado     │  │  • evidence/frames/crash_*.jpg            │
│  • Cajas de color    │  │  • evidence/events.csv                    │
│  • Estelas trail     │  │  • data/output/report_*.json              │
│  • Banner de alerta  │  │                                           │
│  • Panel info        │  │                                           │
└──────────────────────┘  └──────────────────────────────────────────┘
```

## Módulos del Sistema

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Configuración | `config.py` | Parámetros centralizados y rutas |
| Detector | `src/detector.py` | Wrapper YOLO + ByteTrack, carga del modelo |
| Tracker | `src/tracker.py` | Clase `Track` con historial cinemático |
| Lógica | `src/collision_logic.py` | Fusión multi-señal, TTC, severidad |
| Pipeline | `src/video_processor.py` | Orquestación del flujo completo |
| Utilidades | `src/utils.py` | Geometría, dibujo, E/S de archivos |
| CLI | `main.py` | Punto de entrada por línea de comandos |
| Dashboard | `app.py` | Interfaz web Streamlit |

## Decisiones de Diseño

### ¿Por qué ByteTrack?
ByteTrack (Zhang et al., 2022) fue seleccionado sobre DeepSORT y BoT-SORT porque:
1. **Recuperación de oclusión sin ReID**: usa detecciones de baja confianza para mantener el track durante el momento del impacto (cuando YOLO pierde la caja)
2. **Velocidad**: ~30 FPS en CPU vs. ~15 FPS de BoT-SORT (que requiere ReID)
3. **Estático**: la cámara CCTV es fija, por lo que la compensación de movimiento de cámara de BoT-SORT no agrega valor

### ¿Por qué 7 señales fusionadas?
La literatura muestra que ninguna señal individual es suficiente:
- IoU solo → falsos positivos cuando los vehículos se cruzan
- Velocidad solo → falsos positivos por frenadas normales
- TTC solo → falsos negativos en impactos laterales

La fusión ponderada requiere evidencia en múltiples dimensiones simultáneamente, reduciendo radicalmente los falsos positivos.

### ¿Por qué TTC (Time-to-Collision)?
TTC es la métrica estándar en sistemas ADAS (ISO 22839) y se usa en todos los sistemas de alerta de colisión de producción. Mide el tiempo hasta el contacto físico basándose en la tasa de acercamiento, siendo predictivo (se activa ANTES del impacto) en lugar de reactivo.

## Parámetros Clave (config.py)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `YOLO_CONFIDENCE` | 0.40 | Umbral de confianza de detección |
| `COLLISION_SCORE_THRESHOLD` | 0.25 | Score mínimo para reportar colisión |
| `SUDDEN_SPEED_DROP_RATIO` | 0.20 | Caída de velocidad ≥ 20% → señal de impacto |
| `TTC_CRITICAL_FRAMES` | 8 | TTC < 8 frames → riesgo crítico |
| `PERSISTENCE_FRAMES` | 3 | Frames consecutivos para confirmar evento |
| `EVENT_COOLDOWN_FRAMES` | 20 | Frames de silencio post-evento |
| `TRACK_MAX_MISSED` | 5 | Grace period de oclusión en frames |
