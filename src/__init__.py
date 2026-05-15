"""
Project Crash AI — Sistema de Detección de Colisiones Vehiculares
Basado en YOLOv8 + ByteTrack + Análisis Cinemático Multi-señal

Módulos:
    detector       — Wrapper de YOLO para detección y tracking
    tracker        — Clase Track y gestión de estado por objeto
    collision_logic — Lógica de colisión: IoU, velocidad, TTC, ángulo
    video_processor — Pipeline principal de procesamiento de video
    utils           — Funciones de geometría, dibujo y E/S
"""
