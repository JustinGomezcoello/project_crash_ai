# 🎬 GUÍA ULTRA RÁPIDA - 60 SEGUNDOS

## TL;DR (Para impacientes)

```powershell
# Paso 1: Coloca tu video
# →  Copia tu video a: D:\zzzz\project_crash_ai\data\input\nombre.mp4

# Paso 2: Ejecuta
python section3_runner.py

# Paso 3: Sigue las instrucciones en pantalla
```

**¡Eso es todo!** Los resultados estarán en `data/output/`

---

## ¿Qué resultado voy a obtener?

| Archivo | Contenido |
|---------|----------|
| `crash_detected_*.mp4` | Video con cajas ROJAS en colisiones |
| `report_*.json` | Datos de colisiones (timestamps, IDs) |
| `evaluation_*.json` | Métricas: Precision, Recall, F1-Score |

---

## Ejemplo de uso

```powershell
PS D:\zzzz\project_crash_ai> python section3_runner.py

╔════════════════════════════════════════════════════════════════╗
║   SISTEMA DE DETECCIÓN DE COLISIONES VEHICULARES              ║
╚════════════════════════════════════════════════════════════════╝

1. Procesar un video
2. Ver instrucciones
3. Listar videos disponibles
4. Salir

Selecciona una opción: 1

Ingresa el nombre del video: mi_video.mp4

✓ Buscando video...
✓ Procesando frames...
✓ Detectando colisiones...
✓ Generando reporte...
✓ ¡Completado!

Resultados guardados en: data/output/
```

---

## Opciones avanzadas (si quieres jugar)

```powershell
# Modo muy preciso (para profesor)
python section3_runner.py --video video.mp4 --mode professor

# Modo más sensible (detecta más)
python section3_runner.py --video video.mp4 --mode dev

# Con métricas automáticas
python section3_runner.py --video video.mp4 --evaluate
```

---

## Archivos importantes

- **QUICK_START.md** - Guía completa
- **SECTION3_EVALUATION.md** - Explicación de métricas
- **README.md** - Información general

---

**¿Preguntas?** Abre `SECTION3_EVALUATION.md` y busca "FAQ"
