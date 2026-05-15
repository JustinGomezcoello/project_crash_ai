"""
app.py — Dashboard Streamlit: Sistema de Detección de Colisiones Vehiculares

Interfaz web profesional para:
  - Cargar videos y configurar parámetros
  - Procesar con YOLO + ByteTrack en tiempo real
  - Visualizar resultados: KPIs, tabla de eventos, galería de evidencias
  - Descargar video procesado y reporte JSON
  - Gráfico de confianza a lo largo del tiempo (Plotly)

Inspirado en:
  - 000jd/Accident-Detection-yolov8-streamlit
  - Udith-creates/Intellignet-Traffic-Incident-Detection
"""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Project Crash AI",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .metric-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 18px 24px;
        border-left: 4px solid #ff4b4b;
        margin: 6px 0;
    }
    .severity-severo   { color: #ff4b4b; font-weight: bold; }
    .severity-moderado { color: #ff8c00; font-weight: bold; }
    .severity-leve     { color: #ffd700; font-weight: bold; }
    .header-bar {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 24px 32px;
        border-radius: 14px;
        margin-bottom: 24px;
    }
    .evidence-frame { border-radius: 10px; border: 2px solid #ff4b4b; }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
    <h1 style="color:white; margin:0; font-size:2.2em;">🚗 Project Crash AI</h1>
    <p style="color:#8ab4f8; margin:6px 0 0 0; font-size:1.05em;">
        Sistema de Detección de Colisiones Vehiculares · YOLOv8 + ByteTrack + Análisis Cinemático
    </p>
</div>
""", unsafe_allow_html=True)


# ======================================================================= #
#  SIDEBAR — Configuración                                                  #
# ======================================================================= #
with st.sidebar:
    st.header("⚙️ Configuración")
    st.divider()

    uploaded = st.file_uploader(
        "📂 Cargar Video",
        type=["mp4", "avi", "mov"],
        help="Sube un video de tránsito para analizar colisiones"
    )

    st.subheader("Modelo")
    tracker_choice = st.selectbox(
        "Tracker", ["bytetrack", "botsort"],
        help="ByteTrack: más rápido. BoT-SORT: más preciso en oclusiones."
    )
    confidence = st.slider(
        "Confianza YOLO", 0.10, 0.90, 0.40, 0.05,
        help="Umbral mínimo de confianza para detectar vehículos"
    )

    st.subheader("Detección")
    score_thresh = st.slider(
        "Umbral de Colisión", 0.10, 0.80, 0.25, 0.05,
        help="Score mínimo de fusión de señales para reportar colisión"
    )

    st.divider()
    run_btn = st.button("▶ Analizar Video", type="primary", use_container_width=True)

    st.divider()
    st.caption("📚 Referencias\nYOLOv8 · ByteTrack · CADP Dataset · DoTA Dataset")


# ======================================================================= #
#  LÓGICA PRINCIPAL                                                         #
# ======================================================================= #

if not uploaded:
    # Pantalla de bienvenida
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**1. Cargar Video**\nSube un video MP4 de tránsito desde el panel lateral.")
    with col2:
        st.info("**2. Configurar**\nAjusta los parámetros del tracker y la confianza.")
    with col3:
        st.info("**3. Analizar**\nEl sistema detectará colisiones frame a frame.")

    st.markdown("---")
    st.subheader("🏗️ Arquitectura del Sistema")
    st.code("""
[Video Input] → [Frame Extraction] → [YOLOv8 Detection]
     → [ByteTrack Tracking] → [Collision Analysis]
          ├── Señal 1: IoU (solapamiento de cajas)
          ├── Señal 2: Distancia normalizada
          ├── Señal 3: Velocidad relativa
          ├── Señal 4: Persistencia temporal
          ├── Señal 5: Caída brusca de velocidad
          ├── Señal 6: Cambio angular de trayectoria
          └── Señal 7: Time-to-Collision (TTC / ISO 22839)
     → [Severidad: Leve | Moderado | Severo]
     → [Video Anotado] + [Reporte JSON] + [Evidencia Forense]
    """, language="")
    st.stop()


# ── Guardar video temporal ────────────────────────────────────────────────
tmp_dir  = tempfile.mkdtemp()
tmp_path = os.path.join(tmp_dir, uploaded.name)
with open(tmp_path, "wb") as f:
    f.write(uploaded.read())

st.subheader(f"📽️ Video cargado: `{uploaded.name}`")

# Preview del video original
with st.expander("▶ Ver video original", expanded=False):
    st.video(tmp_path)


# ── Procesar ─────────────────────────────────────────────────────────────
if run_btn:
    # Inyectar parámetros en config antes de importar VideoProcessor
    import config
    config.YOLO_TRACKER          = tracker_choice
    config.YOLO_CONFIDENCE       = confidence
    config.COLLISION_SCORE_THRESHOLD = score_thresh

    from src.video_processor import VideoProcessor

    st.divider()
    st.subheader("⚙️ Procesando...")

    progress_bar = st.progress(0, text="Iniciando...")
    status_text  = st.empty()

    out_path    = os.path.join(tmp_dir, f"result_{uploaded.name}")
    report_path = os.path.join(tmp_dir, "report.json")

    def cb(frame_num, total):
        pct = frame_num / max(total, 1)
        progress_bar.progress(pct, text=f"Frame {frame_num}/{total} ({pct*100:.0f}%)")
        status_text.caption(f"Procesando frame {frame_num}…")

    proc   = VideoProcessor(tracker=tracker_choice, confidence=confidence)
    report = proc.process_video(
        tmp_path,
        output_video=out_path,
        save_evidence=True,
        progress_callback=cb,
    )

    progress_bar.progress(1.0, text="✅ Completado")
    status_text.empty()

    if not report:
        st.error("Error al procesar el video.")
        st.stop()

    st.session_state["report"]   = report
    st.session_state["out_path"] = out_path


# ── Mostrar resultados ────────────────────────────────────────────────────
if "report" in st.session_state:
    report   = st.session_state["report"]
    out_path = st.session_state["out_path"]
    cols_det = report.get("collisions", [])

    st.divider()
    st.subheader("📊 Resultados del Análisis")

    # ── KPIs ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚨 Colisiones detectadas", len(cols_det))
    k2.metric("🎞️ Frames procesados",
              report.get("summary", {}).get("frames_processed", "–"))
    k3.metric("🚗 Detecciones totales",
              report.get("summary", {}).get("total_detections", "–"))
    avg_conf = (
        round(sum(c["confidence"] for c in cols_det) / len(cols_det), 3)
        if cols_det else "–"
    )
    k4.metric("📈 Confianza promedio", avg_conf)

    # ── Video procesado ───────────────────────────────────────────────────
    st.divider()
    st.subheader("🎬 Video Procesado")
    if os.path.exists(out_path):
        with open(out_path, "rb") as f:
            st.download_button(
                "⬇️ Descargar Video Procesado",
                f, file_name=f"crash_detected_{uploaded.name}",
                mime="video/mp4"
            )
        st.video(out_path)

    # ── Tabla de eventos ──────────────────────────────────────────────────
    if cols_det:
        st.divider()
        st.subheader("📋 Tabla de Eventos")

        def sev_badge(s):
            cls = {"Severo": "severity-severo", "Moderado": "severity-moderado",
                   "Leve": "severity-leve"}.get(s, "")
            return f'<span class="{cls}">{s}</span>'

        df = pd.DataFrame(cols_det)
        df_show = df[["timestamp", "track_id_1", "track_id_2",
                       "confidence", "severity"]].copy()
        df_show.columns = ["Timestamp", "Track 1", "Track 2", "Confianza", "Severidad"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # ── Gráfico de confianza por evento ──────────────────────────────
        st.subheader("📈 Confianza por Evento")
        fig = go.Figure()
        frames_x = [c["frame"] for c in cols_det]
        confs_y  = [c["confidence"] for c in cols_det]
        sevs     = [c["severity"] for c in cols_det]
        colors   = [
            "#ff4b4b" if s == "Severo" else
            "#ff8c00" if s == "Moderado" else
            "#ffd700"
            for s in sevs
        ]
        fig.add_trace(go.Scatter(
            x=frames_x, y=confs_y, mode="markers+lines",
            marker=dict(size=14, color=colors, line=dict(width=1, color="white")),
            line=dict(color="#4a9eff", width=2),
            text=[f"Frame {f}<br>Sev: {s}<br>Conf: {c:.3f}"
                  for f, s, c in zip(frames_x, sevs, confs_y)],
            hovertemplate="%{text}<extra></extra>"
        ))
        fig.update_layout(
            xaxis_title="Frame", yaxis_title="Confianza",
            plot_bgcolor="#1e2130", paper_bgcolor="#0e1117",
            font=dict(color="white"),
            yaxis=dict(range=[0, 1.05], gridcolor="#2d3250"),
            xaxis=dict(gridcolor="#2d3250"),
            margin=dict(l=40, r=20, t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Galería de evidencias ─────────────────────────────────────────────
    from config import EVIDENCE_FRAMES_DIR
    evidence_files = sorted(Path(EVIDENCE_FRAMES_DIR).glob("*.jpg"))
    if evidence_files:
        st.divider()
        st.subheader(f"🖼️ Evidencia Forense ({len(evidence_files)} capturas)")
        cols = st.columns(min(len(evidence_files), 3))
        for idx, ef in enumerate(evidence_files[-6:]):   # últimas 6
            col = cols[idx % len(cols)]
            img = cv2.imread(str(ef))
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                col.image(img_rgb, caption=ef.name, use_container_width=True)

    # ── Descargar reporte JSON ─────────────────────────────────────────────
    st.divider()
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    st.download_button(
        "⬇️ Descargar Reporte JSON",
        report_json,
        file_name=f"report_{Path(uploaded.name).stem}.json",
        mime="application/json"
    )
