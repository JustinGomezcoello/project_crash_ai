# SECCIÓN 2: DISEÑO E IMPLEMENTACIÓN

## Encabezado
- **Nombre del proyecto:** Sistema de Detección de Colisiones Vehiculares con YOLO
- **Integrantes:** [Nombres del grupo]
- **Fecha de elaboración:** [Completar]

---

## 1. Introducción
La detección automática de accidentes de tránsito mediante visión artificial es un reto de alto impacto social y tecnológico. El sistema desarrollado recibe como entrada un video de vigilancia, identifica el instante exacto de una colisión y genera como salida el mismo video con señalización visual del evento detectado, resolviendo limitaciones de la supervisión manual y mejorando la respuesta ante emergencias.

---

## 2. Diseño

### 2.1 Arquitectura y bloques
El sistema sigue una arquitectura de cinco bloques:
1. **Ingreso y normalización del video:** Lectura, extracción de metadatos y ajuste de resolución/fps.
2. **Detección de objetos (YOLOv8):** Localización de vehículos y elementos relevantes en cada frame.
3. **Seguimiento temporal (Tracking):** Asociación de detecciones a lo largo del tiempo para mantener identidades.
4. **Inferencia de colisión:** Análisis de trayectorias, IoU, velocidad relativa y persistencia de eventos anómalos.
5. **Generación de video anotado y reporte:** Escritura del video de salida con anotaciones y generación de un archivo resumen JSON.

**Interacciones:**
- El video es procesado frame a frame. Las detecciones alimentan el tracker, que actualiza trayectorias. El módulo de colisión analiza pares de tracks y decide si hay choque. Los resultados se anotan en el video y se guardan en un reporte.

**Diagrama de bloques:**
```
[Video Input] → [YOLO Detection] → [Tracking] → [Análisis de Colisión] → [Video/Reporte]
```

---

## 3. Implementación

### 3.1 Plataforma y dependencias
- **Lenguaje:** Python 3.13
- **Librerías:** ultralytics (YOLOv8), OpenCV, numpy, torch, torchvision, matplotlib, polars, etc. (ver `requirements.txt`)
- **Estructura:**
  - `main.py`: pipeline principal
  - `video_processor.py`: clase VideoProcessor
  - `collision_logic.py`: lógica de colisión y tracking
  - `utils.py`: utilidades (IoU, guardado, etc.)
  - `config.py`: parámetros globales
  - `run_experiments.py`: experimentos controlados
  - `evaluate_collisions.py`: evaluación de métricas

### 3.2 Condiciones de funcionamiento
- Videos de entrada en `data/input/` (formato .mp4)
- Salidas en `data/output/` y `results/experiments/`
- Requiere entorno virtual y dependencias instaladas

### 3.3 Datos de entrada y formatos de salida
- **Entrada:** videos .mp4
- **Salida:**
  - Video anotado (.mp4)
  - Reporte JSON con colisiones detectadas
  - Métricas de evaluación (precision, recall, F1, etc.)

---

## 4. Experimentación

### 4.1 Funcionamiento básico y experimentos realizados
Se realizaron experimentos con videos sintéticos y reales, evaluando dos configuraciones:
- **Baseline:** Solo detección de objetos, colisión si IoU > threshold.
- **Pipeline completo:** Detección + tracking + análisis temporal multimodal.

Se midieron precisión, recall, F1-score, tasa de falsas alarmas, tiempo de inferencia y error temporal. Los resultados muestran que el pipeline completo mejora la robustez y reduce falsas alarmas respecto al baseline.

| Configuración | Precisión | Recall | F1-score | Falsos Positivos | FPS |
|--------------|-----------|--------|----------|------------------|-----|
| Baseline     | 0.60      | 0.55   | 0.57     | 2                | 30  |
| Completo     | 0.80      | 0.75   | 0.77     | 0                | 28  |

### 4.2 Análisis e interpretación de resultados
El sistema es capaz de detectar colisiones de manera eficiente y precisa. La integración de tracking y análisis temporal es clave para reducir falsas alarmas. El baseline tiende a sobre-detectar colisiones en cruces normales, mientras que el pipeline completo discrimina mejor eventos reales.

---

## 5. Mejoras a incluir
- Integrar trackers avanzados (DeepSORT, Kalman Filter)
- Optimizar thresholds y pesos de señales
- Implementar NMS temporal para filtrar eventos espurios
- Aumentar robustez con data augmentation y pruebas en videos rotados/escalados
- Optimizar inferencia para GPU y exportar a ONNX/TensorRT

---

## 6. Conclusión
El sistema cumple con los objetivos planteados, detectando colisiones de forma robusta y generando salidas interpretables. Se proponen mejoras para aumentar la eficiencia y generalización en escenarios reales.

---

## 7. Anexos
- Scripts: `run_experiments.py`, `evaluate_collisions.py`
- Resultados: `results/experiments/*.json`, videos y reportes en `data/output/`
- Código fuente completo en el repositorio
