# Pruebas y Validación — Project Crash AI

## Estrategia de Pruebas

El sistema sigue una estrategia de pruebas en tres niveles:

| Nivel | Tipo | Herramienta |
|-------|------|-------------|
| Unitario | Funciones individuales (geometría, señales) | `tests/test_collision_logic.py` |
| Integración | Pipeline completo sobre videos reales | `tests/test_video_processor.py` |
| Visual | Revisión de video de salida anotado | Manual |

---

## Videos de Prueba

| Video | Descripción | Colisiones Esperadas | Resultado |
|-------|-------------|---------------------|-----------|
| `ccd_crash_01.mp4` | Colisión frontal entre 2 vehículos | ≥ 1 | ✅ |
| `ccd_crash_02.mp4` | Colisión lateral en intersección | ≥ 1 | ✅ |
| `ccd_crash_03.mp4` | Tráfico sin colisión | 0 | ✅ |
| `ccd_crash_04.mp4` | Múltiples vehículos, colisión múltiple | ≥ 2 | ✅ |
| `test_video_simple.mp4` | Video sin vehículos colisionando | 0 | ✅ |

---

## Desafíos Técnicos y Soluciones

### Problema 1: YOLO pierde los vehículos durante el impacto

**Causa:** Al momento del choque, los vehículos se deforman, se bloquean mutuamente
o cambian de clase abruptamente (de car → truck). YOLO deja de detectarlos por 3-5 frames.

**Solución implementada:**
- **Grace Period** (`TRACK_MAX_MISSED = 5`): el sistema conserva el último estado conocido
  del track por hasta 5 frames sin detección antes de excluirlo del análisis.
- **ByteTrack**: usa detecciones de baja confianza (`conf < 0.40`) para re-adquirir
  el objeto antes de que el grace period expire.

---

### Problema 2: Falsos positivos en vehículos que se cruzan sin chocar

**Causa:** Dos vehículos que se cruzan en un semáforo tienen IoU alto momentáneamente,
generando una falsa alarma.

**Soluciones implementadas:**
1. **Persistencia temporal** (`PERSISTENCE_FRAMES = 3`): requiere 3 frames consecutivos
   con señal positiva antes de reportar el evento.
2. **Filtro histórico de duplicados**: si dos cajas siempre estuvieron solapadas desde
   que entraron al video, se ignoran (son el mismo objeto detectado dos veces por YOLO).
3. **Fusión multi-señal**: el cruce sin choque no produce caída de velocidad ni cambio
   angular, por lo que el score de fusión queda por debajo del umbral.

---

### Problema 3: IDs cambiantes del tracker (ID switching)

**Causa:** El tracker simple basado en distancia euclidiana asignaba nuevos IDs a los
vehículos cuando se movían rápido entre frames o se ocluían parcialmente.

**Solución implementada:**
- Migración a **ByteTrack** via `model.track(persist=True)` de Ultralytics.
- ByteTrack mantiene un estado Kalman por objeto, prediciendo la posición futura
  y evitando que las detecciones rápidas rompan el hilo del track.

---

## Cómo Ejecutar las Pruebas

```bash
# Pruebas unitarias
python -m pytest tests/ -v

# Prueba de integración en un video específico
python main.py --video ccd_crash_01.mp4

# Evaluación con métricas (si existe ground truth)
python evaluate_collisions.py gt_report.json data/output/report_*.json
```

---

## Métricas de Evaluación

El módulo `evaluate_collisions.py` calcula:

| Métrica | Fórmula | Descripción |
|---------|---------|-------------|
| **Precision** | TP / (TP + FP) | De los eventos reportados, ¿cuántos son reales? |
| **Recall** | TP / (TP + FN) | De los eventos reales, ¿cuántos detectamos? |
| **F1** | 2·P·R / (P+R) | Media armónica (balance Precision/Recall) |

Tolerancia temporal: `EVAL_TOLERANCE_FRAMES = 5` frames.
Un evento detectado se considera TP si ocurre dentro de ±5 frames del evento real.
