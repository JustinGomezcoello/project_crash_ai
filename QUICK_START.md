# 🎥 GUÍA RÁPIDA - Sistema de Detección de Colisiones Vehiculares

## ¿Qué hace este sistema?

Detecta automáticamente colisiones entre vehículos en videos usando **Inteligencia Artificial (YOLO v8)** y genera:
- ✅ Video anotado con cajas alrededor de los vehículos
- ✅ Alertas visuales cuando detecta una colisión
- ✅ Reporte JSON con timestamps exactos
- ✅ Métricas de evaluación (Precisión, Recall, F1-Score)

---

## 🚀 INICIO RÁPIDO (3 pasos)

### Paso 1: Preparar el video
```
1. Coloca tu video en: D:\zzzz\project_crash_ai\data\input\
2. El video debe ser .mp4 (ej: choque_prueba.mp4)
```

### Paso 2: Ejecutar el sistema
```powershell
# Opción A: Modo interactivo (RECOMENDADO - más fácil)
python section3_runner.py

# O Opción B: Línea de comandos directa
python section3_runner.py --video choque_prueba.mp4 --evaluate
```

### Paso 3: Ver resultados
```
📹 Video anotado:  data\output\crash_detected_*.mp4
📄 Reporte JSON:   data\output\report_*.json
📊 Métricas:       results\evaluation_*.json
```

---

## 🎮 MODO INTERACTIVO (Lo más fácil)

```
$ python section3_runner.py

╔════════════════════════════════════════════════════════╗
║   SISTEMA DE DETECCIÓN DE COLISIONES VEHICULARES     ║
╚════════════════════════════════════════════════════════╝

1. Procesar un video
2. Ver instrucciones
3. Listar videos disponibles
4. Salir

Selecciona una opción: 1

Ingresa el nombre del video: choque_prueba.mp4

✓ Procesando...
✓ Completado!
✓ Resultados guardados en: data/output/
```

---

## ⚙️ PARÁMETROS AVANZADOS

### Modos de operación
```powershell
# Modo Professor (muy preciso, menos detecciones)
python section3_runner.py --video archivo.mp4 --mode professor

# Modo Demo (balance)
python section3_runner.py --video archivo.mp4 --mode demo

# Modo Dev (más sensible, más detecciones)
python section3_runner.py --video archivo.mp4 --mode dev
```

### Niveles de precisión
```powershell
# Alta precisión
python section3_runner.py --video archivo.mp4 --strictness high

# Precisión media
python section3_runner.py --video archivo.mp4 --strictness medium

# Baja precisión (más detecciones)
python section3_runner.py --video archivo.mp4 --strictness low
```

---

## 📊 INTERPRETAR RESULTADOS

### Video anotado (crash_detected_*.mp4)
- **Cajas VERDES** = Vehículos detectados normalmente
- **Cajas ROJAS** = Colisión detectada ⚠️
- **IDs numéricos** = Identificador único de cada vehículo
- **ALERT!** = Alerta de colisión en pantalla

### Reporte JSON (report_*.json)
```json
{
  "video_file": "choque_prueba.mp4",
  "total_frames": 300,
  "detections": [
    {
      "frame": 150,
      "vehicles": 2,
      "collision_detected": true,
      "confidence": 0.95,
      "vehicle_ids": [1, 2]
    }
  ]
}
```

### Métricas (evaluation_*.json)
| Métrica | Rango | Interpretación |
|---------|-------|---|
| **Precision** | 0-100% | % de detecciones correctas |
| **Recall** | 0-100% | % de colisiones capturadas |
| **F1-Score** | 0-1.0 | Balance entre Precision y Recall |
| **FPS** | >20 fps | Velocidad de procesamiento |

**Objetivo:** 
- Precision > 85% ✅
- Recall > 80% ✅
- F1-Score > 0.82 ✅

---

## 🧪 PRUEBAS DE ROBUSTEZ

Ejecuta el sistema con diferentes condiciones:

```powershell
# El sistema prueba automáticamente:
# ✓ Videos en diferentes resoluciones (0.5x, 1x, 1.5x, 2x)
# ✓ Videos rotados (0°, 90°, 180°, 270°)
# ✓ Videos con oclusión (10%, 25%, 50%)
# ✓ Diferentes niveles de brillo
# ✓ Diferentes velocidades de fotogramas
```

---

## 📁 ESTRUCTURA DE CARPETAS

```
project_crash_ai/
├── data/
│   ├── input/              ← Coloca los videos aquí
│   └── output/             ← Resultados generados
├── config.py               ← Configuración
├── section3_runner.py      ← EJECUTAR ESTO
├── evaluation_metrics.py   ← Métricas
├── robustness_tests.py     ← Pruebas de robustez
└── SECTION3_EVALUATION.md  ← Documentación completa
```

---

## ❓ PREGUNTAS FRECUENTES

**P: ¿Qué tipos de video acepta?**
R: Cualquier video .mp4. Mejor si tiene colisiones claras.

**P: ¿Cuál es el tiempo de procesamiento?**
R: Aproximadamente 1 segundo por 15 fotogramas (depende del PC).

**P: ¿Qué pasa si no hay colisión?**
R: El sistema reporta que no detectó colisión. Reporte vacío pero válido.

**P: ¿Cómo ajusto la sensibilidad?**
R: Usa `--mode professor` (menos sensible) o `--mode dev` (más sensible).

**P: El video está en otra resolución...**
R: El sistema se adapta automáticamente.

**P: ¿Necesito NVIDIA?**
R: No, también funciona con CPU. Más lento pero funciona.

---

## 🔧 CONFIGURACIÓN POR DEFECTO

| Parámetro | Valor | Descripción |
|-----------|-------|---|
| CONFIDENCE_THRESHOLD | 0.5 | Mínima confianza para detectar |
| IOU_THRESHOLD | 0.3 | Superposición para colisión |
| MAX_DISTANCE | 50 px | Distancia máxima entre vehículos |
| MIN_FRAMES | 3 | Fotogramas mínimos para confirmar |

Edita `config.py` para cambiar valores.

---

## 📞 SOPORTE

Si tienes problemas:
1. Revisa `SECTION3_EVALUATION.md` (guía completa)
2. Verifica que el video esté en `data/input/`
3. Intenta con `--mode dev` para mayor sensibilidad
4. Revisa el archivo de error en `data/output/`

---

## ✨ CARACTERÍSTICAS PRINCIPALES

✅ Detección con IA (YOLOv8)  
✅ Tracking de vehículos  
✅ Detección multi-señal (IoU + velocidad + distancia)  
✅ Reportes JSON automáticos  
✅ Métricas profesionales  
✅ 3 modos de operación  
✅ Interface amigable  
✅ Código 100% documentado  

---

**Versión:** 1.0  
**Status:** ✅ Producción  
**GitHub:** https://github.com/JustinGomezcoello/project_crash_ai
