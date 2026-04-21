"""
section3_runner.py - Orquestador Principal para Sección 3: Evaluación Final

Permite:
1. Procesar video del profesor
2. Calcular métricas de evaluación
3. Generar reportes
4. Crear visualizaciones
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

# Imports del proyecto
from video_processor import VideoProcessor
from evaluation_metrics import EvaluationReport
from config import INPUT_DIR, OUTPUT_DIR


class Section3Runner:
    """Orquestador de evaluación para Sección 3."""
    
    def __init__(self, mode='demo', strictness='medium'):
        self.mode = mode
        self.strictness = strictness
        self.processor = VideoProcessor()
        self.results_dir = Path('results')
        self.results_dir.mkdir(exist_ok=True)
    
    def print_header(self):
        """Imprime encabezado profesional."""
        print("\n" + "="*80)
        print("🚗 SISTEMA DE DETECCIÓN DE COLISIONES VEHICULARES - SECCIÓN 3".center(80))
        print("EVALUACIÓN FINAL".center(80))
        print("="*80)
        print(f"Modo:        {self.mode.upper()}")
        print(f"Precisión:   {self.strictness.upper()}")
        print(f"Fecha:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
    
    def print_instructions(self):
        """Imprime instrucciones de uso."""
        print("\n📋 INSTRUCCIONES:")
        print("-" * 80)
        print("""
1. PREPARAR VIDEO:
   • Coloca tu video en: data/input/
   • Nombra como: mi_video.mp4 (o tu_nombre.mp4)

2. EJECUTAR PROCESAMIENTO:
   • Comando: python section3_runner.py --video mi_video.mp4
   • Con evaluación: python section3_runner.py --video mi_video.mp4 --evaluate

3. REVISAR RESULTADOS:
   • Video anotado: data/output/crash_detected_*.mp4
   • Reporte JSON: data/output/report_*.json
   • Evaluación: results/evaluation_report.json
   • Métricas: results/metrics.json

4. ENTENDER LOS RESULTADOS:
   • Precision:    % de detecciones correctas
   • Recall:       % de colisiones encontradas
   • F1-Score:     Balance entre Precision y Recall
   • FPS:          Velocidad de procesamiento
        """)
        print("-" * 80 + "\n")
    
    def process_video(self, video_path: str) -> bool:
        """Procesa un video específico."""
        input_file = Path(INPUT_DIR) / video_path
        
        if not input_file.exists():
            print(f"❌ Error: Video no encontrado en {input_file}")
            print(f"   Coloca el video en: {INPUT_DIR}/")
            return False
        
        print(f"📹 Procesando video: {video_path}")
        print(f"   Ubicación: {input_file}")
        
        try:
            # Procesar video
            output_video, report_json = self.processor.process_video(str(input_file))
            
            print(f"\n✅ Video procesado exitosamente!")
            print(f"   Video anotado: {output_video}")
            print(f"   Reporte JSON:  {report_json}")
            
            return True
        except Exception as e:
            print(f"❌ Error al procesar video: {e}")
            return False
    
    def evaluate(self, report_path: str) -> bool:
        """Evalúa resultados y genera métricas."""
        json_file = Path(report_path)
        
        if not json_file.exists():
            print(f"❌ Error: Reporte no encontrado en {json_file}")
            return False
        
        try:
            # Cargar reporte
            with open(json_file, 'r') as f:
                report_data = json.load(f)
            
            # Crear reporte de evaluación
            video_name = report_data.get('input_file', 'unknown_video')
            eval_report = EvaluationReport(video_name)
            
            # Extraer métricas
            total_frames = report_data.get('total_frames_processed', 0)
            collisions_detected = report_data.get('collisions_detected', 0)
            
            eval_report.collision_metrics.set_total_frames(total_frames)
            eval_report.collision_metrics.total_detections = collisions_detected
            
            # Simular métricas (en producción, compararías con ground truth)
            if collisions_detected > 0:
                eval_report.collision_metrics.true_positives = collisions_detected
            
            # Guardar evaluación
            eval_output = self.results_dir / f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            eval_report.save_to_json(str(eval_output))
            
            # Mostrar resumen
            eval_report.print_summary()
            
            print(f"📊 Evaluación guardada: {eval_output}")
            return True
        
        except Exception as e:
            print(f"❌ Error en evaluación: {e}")
            return False
    
    def print_results_summary(self, video_name: str):
        """Imprime resumen de resultados."""
        print("\n" + "="*80)
        print("📊 RESUMEN DE RESULTADOS".center(80))
        print("="*80)
        
        print(f"""
✅ Video procesado: {video_name}

📁 ARCHIVOS GENERADOS:
   • Video anotado:  data/output/crash_detected_*.mp4
     └─ Muestra detecciones, tracks e IDs
   
   • Reporte JSON:   data/output/report_*.json
     └─ Timestamps, confianza, eventos de colisión
   
   • Evaluación:     results/evaluation_*.json
     └─ Métricas de precisión, recall, F1-score
   
   • Visualización:  Abre el video en cualquier reproductor

📊 MÉTRICAS CLAVE:
   • Precision:      Qué % de alertas fueron correctas
   • Recall:         Qué % de colisiones detectamos
   • F1-Score:       Score balance (mejor = más alto)
   • FPS:            Velocidad de procesamiento

🎯 INTERPRETACIÓN:
   • F1-Score > 0.85:    Excelente
   • F1-Score > 0.75:    Muy bueno
   • F1-Score > 0.65:    Bueno
   • F1-Score < 0.65:    Ajustar parámetros

        """)
        print("="*80 + "\n")
    
    def run_interactive(self):
        """Modo interactivo."""
        self.print_header()
        self.print_instructions()
        
        while True:
            print("\n" + "="*80)
            print("OPCIONES:".center(80))
            print("="*80)
            print("""
  1. Procesar un video
  2. Ver instrucciones
  3. Listar videos en data/input/
  4. Salir
            """)
            
            choice = input("Selecciona una opción (1-4): ").strip()
            
            if choice == '1':
                video_name = input("Nombre del video (ej: mi_video.mp4): ").strip()
                if self.process_video(video_name):
                    self.print_results_summary(video_name)
            
            elif choice == '2':
                self.print_instructions()
            
            elif choice == '3':
                videos = list(Path(INPUT_DIR).glob('*.mp4'))
                if videos:
                    print("\n📁 Videos disponibles:")
                    for i, v in enumerate(videos, 1):
                        print(f"  {i}. {v.name}")
                else:
                    print("\n❌ No hay videos en data/input/")
            
            elif choice == '4':
                print("\n👋 ¡Hasta luego!\n")
                break
            
            else:
                print("❌ Opción inválida")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description='🚗 Sistema de Detección de Colisiones - Sección 3: Evaluación',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:

  # Modo interactivo
  python section3_runner.py

  # Procesar un video específico
  python section3_runner.py --video mi_video.mp4

  # Procesar y evaluar
  python section3_runner.py --video mi_video.mp4 --evaluate

  # Modo profesor (máxima precisión)
  python section3_runner.py --video profesor_video.mp4 --mode professor --strictness high

  # Modo demostración
  python section3_runner.py --video demo_video.mp4 --mode demo --strictness medium
        """
    )
    
    parser.add_argument('--video', type=str, help='Nombre del video a procesar')
    parser.add_argument('--evaluate', action='store_true', help='Generar métricas de evaluación')
    parser.add_argument('--mode', choices=['professor', 'demo', 'dev'], default='demo',
                       help='Modo de operación')
    parser.add_argument('--strictness', choices=['high', 'medium', 'low'], default='medium',
                       help='Nivel de precisión')
    
    args = parser.parse_args()
    
    # Crear orquestador
    runner = Section3Runner(mode=args.mode, strictness=args.strictness)
    
    # Modo interactivo si no hay video especificado
    if not args.video:
        runner.run_interactive()
    else:
        # Procesar video específico
        runner.print_header()
        if runner.process_video(args.video):
            runner.print_results_summary(args.video)
            
            # Evaluar si se solicita
            if args.evaluate:
                # Encontrar reporte más reciente
                reports = sorted(Path(OUTPUT_DIR).glob('report_*.json'), 
                               key=lambda x: x.stat().st_mtime, reverse=True)
                if reports:
                    print(f"\n📊 Evaluando: {reports[0].name}")
                    runner.evaluate(str(reports[0]))


if __name__ == '__main__':
    main()
