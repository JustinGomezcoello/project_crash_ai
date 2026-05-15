# Referencias Académicas y Técnicas — Project Crash AI

Este documento lista las referencias que sustentan el diseño, la metodología
y las decisiones técnicas del sistema.

---

## Modelo de Detección

**[1] Jocher, G., Chaurasia, A., & Qiu, J. (2023).**
*Ultralytics YOLOv8.*
https://github.com/ultralytics/ultralytics
- Modelo de detección de objetos usado en el sistema.
- Clases COCO utilizadas: 2 (car), 3 (motorcycle), 5 (bus), 7 (truck).
- El sistema usa `yolov8n.pt` (nano, ~6.2 MB) para máxima velocidad en CPU.

---

## Algoritmos de Tracking

**[2] Zhang, Y., Sun, P., Jiang, Y., Yu, D., Weng, F., Yuan, Z., ... & Wang, X. (2022).**
*ByteTrack: Multi-Object Tracking by Associating Every Detection Box.*
ECCV 2022. https://arxiv.org/abs/2110.06864
- Tracker principal usado en el sistema.
- Clave: usa detecciones de BAJA confianza para recuperar objetos ocluidos,
  lo que permite mantener el historial de velocidad durante el momento del impacto.

**[3] Aharon, N., Orfaig, R., & Bobrovsky, B. Z. (2022).**
*BoT-SORT: Robust Associations Multi-Pedestrian Tracking.*
https://arxiv.org/abs/2206.14651
- Alternativa con ReID y compensación de movimiento de cámara.
- Disponible como opción en el sistema (--tracker botsort).

**[4] Wojke, N., Bewley, A., & Paulus, D. (2017).**
*Simple Online and Realtime Tracking with a Deep Association Metric (DeepSORT).*
ICIP 2017. https://arxiv.org/abs/1703.07402
- Base conceptual del tracking con apariencia para mantener IDs durante oclusiones.

---

## Datasets de Referencia

**[5] Shah, A. P., Lamare, J. B., Nguyen-Anh, T., & Hauptmann, A. (2018).**
*CADP: A Novel Dataset for CCTV Traffic Camera Based Accident Analysis.*
AVSS 2018. https://arxiv.org/abs/1902.01566
- Dataset de accidentes en cámaras CCTV fijas.
- Metodología: análisis espacio-temporal, detección de vehículos y forecasting.
- Justifica el uso de análisis de secuencias de video (no frames aislados).
- 1,416 segmentos de video con anotaciones espaciotemporales.

**[6] Yao, Y., Wang, X., Xu, M., Pu, Z., Wang, Y., Atkins, E., & Crandall, D. (2022).**
*DoTA: Detection of Traffic Anomaly.*
IEEE TPAMI 2022. https://arxiv.org/abs/2004.03456
- Dataset de 4,677 videos con 18 categorías de anomalías.
- Introduce métrica STAUC (Spatio-temporal AUC).
- Justifica tratar los accidentes como eventos temporales, no clasificación de imagen.
- Repositorio: https://github.com/MoonBlvd/Detection-of-Traffic-Anomaly

---

## Métricas y Estándares

**[7] ISO 22839:2013.**
*Intelligent transport systems — Forward vehicle collision mitigation systems (FVCMS) —
Performance requirements and test procedures.*
- Estándar industrial para Time-to-Collision (TTC).
- Define TTC = distancia / tasa_de_acercamiento.
- Usado en el sistema como Señal 7 de la fusión multi-señal.

---

## Proyectos de Referencia (Implementación)

**[8] akshat4703/accident_prediction** (GitHub)
- Combina análisis geométrico, aproximación, IoU y probabilidad de accidente.
- Inspiró la fusión multi-señal del sistema.

**[9] 000jd/Accident-Detection-yolov8-streamlit** (GitHub)
- Integra YOLOv8 con Streamlit para carga de video y visualización de resultados.
- Base de la arquitectura del dashboard.

**[10] aayush010904/SaferoadAI** (GitHub)
- Sistema con captura de frame de evidencia al momento del accidente.
- Inspiró el módulo de evidencia forense (evidence/frames/).

**[11] CodeByMoin/YOLO-Based-Accident-Detection-System** (GitHub)
- Arquitectura: video → YOLO → SORT → alerta → video procesado.
- Referencia para el pipeline de procesamiento lineal.

---

## Herramientas y Librerías

| Herramienta | Versión | Uso |
|-------------|---------|-----|
| Python | 3.12 | Lenguaje principal |
| Ultralytics | ≥8.0 | YOLOv8 + ByteTrack |
| OpenCV | ≥4.8 | Procesamiento de video |
| NumPy | ≥1.24 | Cálculos vectoriales |
| Streamlit | ≥1.32 | Dashboard web |
| Plotly | ≥5.18 | Gráficos interactivos |
| Pandas | ≥2.0 | Manejo de datos tabulares |
