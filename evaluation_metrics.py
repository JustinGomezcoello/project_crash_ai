"""
evaluation_metrics.py - Cálculo de métricas de evaluación para Sistema de Colisiones

Incluye:
- Precisión, Recall, F1-Score
- Matriz de confusión
- Tasa de falsos positivos
- Tiempo de inferencia
"""

import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class CollisionMetrics:
    """Calcula métricas de detección de colisiones."""
    
    def __init__(self):
        self.true_positives = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.total_detections = 0
        self.inference_times = []
        self.total_frames = 0
        
    def add_detection(self, is_correct: bool, inference_time: float):
        """Registra una detección."""
        if is_correct:
            self.true_positives += 1
        else:
            self.false_positives += 1
        self.total_detections += 1
        self.inference_times.append(inference_time)
    
    def add_missed_collision(self):
        """Registra una colisión perdida."""
        self.false_negatives += 1
    
    def set_total_frames(self, frames: int):
        """Establece el número total de frames procesados."""
        self.total_frames = frames
    
    @property
    def precision(self) -> float:
        """Precisión = TP / (TP + FP)"""
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)
    
    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)"""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)
    
    @property
    def f1_score(self) -> float:
        """F1-Score = 2 * (Precision * Recall) / (Precision + Recall)"""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)
    
    @property
    def false_positive_rate(self) -> float:
        """Tasa de falsos positivos = FP / (FP + TN)"""
        if self.total_frames == 0:
            return 0.0
        return self.false_positives / self.total_frames
    
    @property
    def average_inference_time(self) -> float:
        """Tiempo promedio de inferencia en ms."""
        if len(self.inference_times) == 0:
            return 0.0
        return np.mean(self.inference_times) * 1000  # Convertir a ms
    
    @property
    def fps(self) -> float:
        """Frames por segundo procesados."""
        if len(self.inference_times) == 0:
            return 0.0
        avg_time = np.mean(self.inference_times)
        return 1.0 / avg_time if avg_time > 0 else 0.0
    
    def get_confusion_matrix(self) -> Dict:
        """Retorna matriz de confusión."""
        return {
            'TP': self.true_positives,
            'FP': self.false_positives,
            'FN': self.false_negatives,
            'TN': self.total_frames - (self.true_positives + self.false_positives + self.false_negatives)
        }
    
    def get_summary(self) -> Dict:
        """Retorna resumen de todas las métricas."""
        return {
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1_score, 4),
            'false_positive_rate': round(self.false_positive_rate, 4),
            'average_inference_time_ms': round(self.average_inference_time, 2),
            'fps': round(self.fps, 2),
            'total_detections': self.total_detections,
            'true_positives': self.true_positives,
            'false_positives': self.false_positives,
            'false_negatives': self.false_negatives,
            'total_frames': self.total_frames,
            'confusion_matrix': self.get_confusion_matrix()
        }


class TrackingMetrics:
    """Calcula métricas de tracking multiobjetivo."""
    
    def __init__(self):
        self.id_switches = 0
        self.fragmentations = 0
        self.tracked_objects = 0
        self.total_objects = 0
        self.tracking_errors = []
    
    def add_id_switch(self):
        """Registra un cambio de ID."""
        self.id_switches += 1
    
    def add_fragmentation(self):
        """Registra una fragmentación de track."""
        self.fragmentations += 1
    
    def add_tracking_error(self, error_distance: float):
        """Registra error de distancia en tracking."""
        self.tracking_errors.append(error_distance)
    
    @property
    def mota(self) -> float:
        """MOTA (Multi-Object Tracking Accuracy)"""
        if self.total_objects == 0:
            return 0.0
        return 1.0 - (self.id_switches + self.fragmentations) / self.total_objects
    
    @property
    def average_tracking_error(self) -> float:
        """Error promedio de tracking en píxeles."""
        if len(self.tracking_errors) == 0:
            return 0.0
        return np.mean(self.tracking_errors)
    
    def get_summary(self) -> Dict:
        """Retorna resumen de métricas de tracking."""
        return {
            'id_switches': self.id_switches,
            'fragmentations': self.fragmentations,
            'mota': round(self.mota, 4),
            'average_tracking_error_px': round(self.average_tracking_error, 2),
            'tracked_objects': self.tracked_objects,
            'total_objects': self.total_objects
        }


class PerformanceMetrics:
    """Calcula métricas de rendimiento del sistema."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.fps_samples = []
    
    def start(self):
        """Inicia medición de tiempo."""
        self.start_time = datetime.now()
    
    def end(self):
        """Finaliza medición de tiempo."""
        self.end_time = datetime.now()
    
    @property
    def total_time_seconds(self) -> float:
        """Tiempo total de procesamiento en segundos."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
    
    def add_memory_sample(self, memory_mb: float):
        """Registra muestra de uso de memoria."""
        self.memory_usage.append(memory_mb)
    
    def add_fps_sample(self, fps: float):
        """Registra muestra de FPS."""
        self.fps_samples.append(fps)
    
    @property
    def average_memory_mb(self) -> float:
        """Uso promedio de memoria en MB."""
        if len(self.memory_usage) == 0:
            return 0.0
        return np.mean(self.memory_usage)
    
    @property
    def peak_memory_mb(self) -> float:
        """Uso máximo de memoria en MB."""
        if len(self.memory_usage) == 0:
            return 0.0
        return np.max(self.memory_usage)
    
    @property
    def average_fps(self) -> float:
        """FPS promedio."""
        if len(self.fps_samples) == 0:
            return 0.0
        return np.mean(self.fps_samples)
    
    def get_summary(self) -> Dict:
        """Retorna resumen de métricas de rendimiento."""
        return {
            'total_time_seconds': round(self.total_time_seconds, 2),
            'average_fps': round(self.average_fps, 2),
            'average_memory_mb': round(self.average_memory_mb, 2),
            'peak_memory_mb': round(self.peak_memory_mb, 2),
            'num_fps_samples': len(self.fps_samples)
        }


class EvaluationReport:
    """Genera reporte completo de evaluación."""
    
    def __init__(self, video_name: str):
        self.video_name = video_name
        self.timestamp = datetime.now().isoformat()
        self.collision_metrics = CollisionMetrics()
        self.tracking_metrics = TrackingMetrics()
        self.performance_metrics = PerformanceMetrics()
        self.detailed_results = []
    
    def add_frame_result(self, frame_num: int, collisions_detected: int, 
                        inference_time: float, description: str = ""):
        """Agrega resultado de un frame."""
        self.detailed_results.append({
            'frame': frame_num,
            'collisions_detected': collisions_detected,
            'inference_time_ms': round(inference_time * 1000, 2),
            'description': description
        })
    
    def save_to_json(self, output_path: str):
        """Guarda reporte a JSON."""
        report = {
            'metadata': {
                'video_name': self.video_name,
                'timestamp': self.timestamp,
                'evaluation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'collision_metrics': self.collision_metrics.get_summary(),
            'tracking_metrics': self.tracking_metrics.get_summary(),
            'performance_metrics': self.performance_metrics.get_summary(),
            'detailed_results': self.detailed_results
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return output_path
    
    def print_summary(self):
        """Imprime resumen en consola."""
        print("\n" + "="*80)
        print(f"EVALUACIÓN: {self.video_name}")
        print("="*80)
        
        # Métricas de colisión
        print("\n📊 MÉTRICAS DE COLISIÓN:")
        print(f"  Precisión:        {self.collision_metrics.precision:.2%}")
        print(f"  Recall:           {self.collision_metrics.recall:.2%}")
        print(f"  F1-Score:         {self.collision_metrics.f1_score:.2%}")
        print(f"  Falsos positivos: {self.collision_metrics.false_positive_rate:.2%}")
        
        # Métricas de tracking
        print("\n🎯 MÉTRICAS DE TRACKING:")
        print(f"  MOTA:             {self.tracking_metrics.mota:.2%}")
        print(f"  ID switches:      {self.tracking_metrics.id_switches}")
        print(f"  Fragmentaciones:  {self.tracking_metrics.fragmentations}")
        
        # Métricas de rendimiento
        print("\n⚡ MÉTRICAS DE RENDIMIENTO:")
        print(f"  FPS promedio:     {self.collision_metrics.fps:.2f}")
        print(f"  Tiempo inferencia:{self.collision_metrics.average_inference_time:.2f} ms")
        print(f"  Tiempo total:     {self.performance_metrics.total_time_seconds:.2f} s")
        print(f"  Memoria promedio: {self.performance_metrics.average_memory_mb:.2f} MB")
        
        print("\n" + "="*80 + "\n")


# Funciones de utilidad
def compare_metrics(metrics1: CollisionMetrics, metrics2: CollisionMetrics) -> Dict:
    """Compara dos conjuntos de métricas."""
    return {
        'precision_diff': round(metrics2.precision - metrics1.precision, 4),
        'recall_diff': round(metrics2.recall - metrics1.recall, 4),
        'f1_score_diff': round(metrics2.f1_score - metrics1.f1_score, 4),
        'improvement': "✓" if metrics2.f1_score > metrics1.f1_score else "✗"
    }


if __name__ == '__main__':
    # Ejemplo de uso
    report = EvaluationReport("test_video.mp4")
    
    # Simular detecciones
    report.collision_metrics.add_detection(True, 0.025)   # TP
    report.collision_metrics.add_detection(True, 0.028)   # TP
    report.collision_metrics.add_detection(False, 0.026)  # FP
    report.collision_metrics.add_detection(True, 0.024)   # TP
    report.collision_metrics.set_total_frames(90)
    
    # Simular tracking
    report.tracking_metrics.tracked_objects = 2
    report.tracking_metrics.total_objects = 2
    
    # Simular rendimiento
    report.performance_metrics.start()
    import time
    time.sleep(0.1)
    report.performance_metrics.end()
    report.performance_metrics.add_fps_sample(22.5)
    report.performance_metrics.add_memory_sample(150.5)
    
    # Mostrar y guardar
    report.print_summary()
    report.save_to_json('results/evaluation_report.json')
    print("✅ Reporte guardado en: results/evaluation_report.json")
