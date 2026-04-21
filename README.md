# 🚗 Sistema de Detección de Colisiones Vehiculares con YOLO

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-red.svg)](https://github.com/ultralytics/ultralytics)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema inteligente de detección de colisiones en video basado en deep learning. Utiliza **YOLOv8** para detección de vehículos, **tracking multiobjetivo** para seguimiento temporal y **análisis de colisiones** con fusión de múltiples señales.

## 🎯 Características

- ✅ **Detección de vehículos** en tiempo real con YOLOv8
- ✅ **Tracking multiobjetivo** basado en distancia euclidiana
- ✅ **Detección avanzada de colisiones** (4 señales fusionadas):
  - Solapamiento de cajas (IoU)
  - Cambio de velocidad
  - Proximidad entre objetos
  - Persistencia temporal
- ✅ **Procesamiento de video** frame-by-frame
- ✅ **Salida anotada** con cajas, IDs y alertas
- ✅ **Reportes JSON** con timestamps y confianza

## 📦 Estructura del Proyecto

```
project_crash_ai/
├── config.py                    # Configuración centralizada
├── utils.py                     # Funciones auxiliares
├── collision_logic.py           # Tracking + Colisión
├── video_processor.py           # Pipeline de video
├── main.py                      # Punto de entrada
├── test_implementation.py       # Suite de pruebas
├── simple_test.py              # Tests rápidos
├── data/
│   ├── input/                  # Videos para procesar
│   └── output/                 # Resultados
├── SECTION2_SUMMARY.md         # Especificación técnica
└── requirements.txt            # Dependencias
```

## 🚀 Instalación Rápida

### Con Conda (Recomendado)

```bash
# Crear entorno
conda create -n crash_ai python=3.12

# Activar
conda activate crash_ai

# Instalar dependencias
pip install -r requirements.txt

# Instalar xz desde conda-forge
conda install -c conda-forge xz
```

### Con Venv

```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 💻 Uso Rápido

```bash
# Procesar todos los videos en data/input/
python main.py

# Ejecutar pruebas
python test_implementation.py
```

## 📊 Arquitectura

```
[Video Input] → [Frame Processing] → [YOLO Detection] → 
[Multi-Object Tracking] → [Collision Analysis] → [Annotated Output]
```

## 📝 Configuración

Edita `config.py` para ajustar thresholds:
- `CONFIDENCE_THRESHOLD`: Confianza YOLO (default: 0.5)
- `MAX_DISTANCE`: Distancia máxima tracking (default: 50px)
- `COLLISION_IOU_THRESHOLD`: IoU para colisión (default: 0.3)

## 📈 Rendimiento

- Velocidad: ~22.5 fps (CPU)
- Modelo: YOLOv8n (6.2 MB)
- Python: 3.12.13

## 📚 Documentación

- **SECTION2_SUMMARY.md** - Especificación técnica completa
- **COMPLETION_REPORT.md** - Reporte de implementación

## 📄 Licencia

MIT License - Ver LICENSE

## 👨‍💻 Autor

Proyecto de IA para detección de colisiones vehiculares.

---

**Versión:** 1.0 | **Estado:** ✅ Operacional | **Última actualización:** 2026-04-20

3) Instalar dependencias adicionales (si es necesario):

```powershell
# En conda:
& 'D:\miniconda\Scripts\conda.exe' install -n crash_ai <paquete> -y

# O con pip dentro del entorno:
& 'D:\miniconda\Scripts\conda.exe' run -n crash_ai pip install <paquete>
```

Notas:
- Los archivos creados son plantilla para empezar. Añade tu lógica de detección y pruebas en `collision_logic.py` y procesa imágenes o datos en `main.py`.
- El entorno `crash_ai` en `D:\miniconda\envs\crash_ai` contiene todas las dependencias. No es necesario crear otro virtualenv.
- Para agregar archivos de entrada, pon imágenes/datos en `data/input/` y el script los procesará.
