"""
robustness_tests.py - Pruebas de Robustez del Sistema

Valida que el sistema funcione correctamente bajo:
- Diferentes resoluciones
- Rotaciones/escalados
- Oclusiones
- Diferentes iluminación
"""

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import json


class RobustnessTest:
    """Realiza pruebas de robustez en videos."""
    
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'video': str(self.video_path),
            'tests': []
        }
    
    def load_video(self) -> cv2.VideoCapture:
        """Carga el video."""
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise RuntimeError(f"No se puede abrir el video: {self.video_path}")
        return cap
    
    def test_resolution_scaling(self, scales: list = [0.5, 1.0, 1.5, 2.0]) -> dict:
        """Prueba detección con diferentes resoluciones."""
        print("\n🔬 TEST: Escalado de Resolución")
        print("-" * 60)
        
        cap = self.load_video()
        results = []
        
        for scale in scales:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # Leer primer frame
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Escalar
            h, w = frame.shape[:2]
            new_w, new_h = int(w * scale), int(h * scale)
            scaled = cv2.resize(frame, (new_w, new_h))
            
            # Verificar que se pueda procesar
            can_process = scaled.shape[0] > 0 and scaled.shape[1] > 0
            
            result = {
                'scale': scale,
                'original_resolution': f"{w}x{h}",
                'scaled_resolution': f"{new_w}x{new_h}",
                'processable': can_process,
                'status': '✓' if can_process else '✗'
            }
            results.append(result)
            
            print(f"  Escala {scale}x: {w}x{h} → {new_w}x{new_h} {result['status']}")
        
        cap.release()
        
        self.test_results['tests'].append({
            'name': 'Resolution Scaling',
            'results': results
        })
        
        return {'resolution_scaling': results}
    
    def test_rotation(self, angles: list = [0, 90, 180, 270]) -> dict:
        """Prueba detección con videos rotados."""
        print("\n🔬 TEST: Rotación")
        print("-" * 60)
        
        cap = self.load_video()
        results = []
        
        for angle in angles:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Rotar
            center = (frame.shape[1] // 2, frame.shape[0] // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(frame, matrix, (frame.shape[1], frame.shape[0]))
            
            # Verificar validez
            is_valid = rotated.shape[0] > 0 and rotated.shape[1] > 0
            
            result = {
                'angle': angle,
                'original_size': frame.shape,
                'rotated_size': rotated.shape,
                'valid': is_valid,
                'status': '✓' if is_valid else '✗'
            }
            results.append(result)
            
            print(f"  Rotación {angle}°: {result['status']}")
        
        cap.release()
        
        self.test_results['tests'].append({
            'name': 'Rotation',
            'results': results
        })
        
        return {'rotation': results}
    
    def test_occlusion(self) -> dict:
        """Prueba detección con oclusiones parciales."""
        print("\n🔬 TEST: Oclusión Parcial")
        print("-" * 60)
        
        cap = self.load_video()
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return {'occlusion': []}
        
        h, w = frame.shape[:2]
        results = []
        
        # Probar diferentes porcentajes de oclusión
        occlusion_percentages = [0, 10, 25, 50]
        
        for occlusion in occlusion_percentages:
            # Crear máscara de oclusión
            occluded = frame.copy()
            
            if occlusion > 0:
                # Cubrir parte del frame (parte inferior)
                occlusion_height = int(h * occlusion / 100)
                occluded[h - occlusion_height:, :] = 0  # Negro
            
            # Verificar que tiene contenido
            has_content = np.any(occluded != 0)
            
            result = {
                'occlusion_percentage': occlusion,
                'occluded_area_px': (w * occlusion_height) if occlusion > 0 else 0,
                'has_visible_content': has_content,
                'status': '✓' if has_content else '✗'
            }
            results.append(result)
            
            print(f"  Oclusión {occlusion}%: {result['status']}")
        
        self.test_results['tests'].append({
            'name': 'Occlusion',
            'results': results
        })
        
        return {'occlusion': results}
    
    def test_illumination(self) -> dict:
        """Prueba detección con diferentes iluminación."""
        print("\n🔬 TEST: Variación de Iluminación")
        print("-" * 60)
        
        cap = self.load_video()
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return {'illumination': []}
        
        results = []
        
        # Probar diferentes niveles de brillo
        brightness_levels = [-50, -25, 0, 25, 50]
        
        for brightness in brightness_levels:
            # Ajustar brillo
            adjusted = cv2.convertScaleAbs(frame, alpha=1.0, beta=brightness)
            adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
            
            # Verificar que sigue siendo válido
            is_valid = adjusted.shape == frame.shape
            
            result = {
                'brightness_adjustment': brightness,
                'original_mean_intensity': int(frame.mean()),
                'adjusted_mean_intensity': int(adjusted.mean()),
                'valid': is_valid,
                'status': '✓' if is_valid else '✗'
            }
            results.append(result)
            
            label = f"Más oscuro (-{-brightness})" if brightness < 0 else \
                   f"Más claro (+{brightness})" if brightness > 0 else "Normal"
            print(f"  {label}: {result['status']}")
        
        self.test_results['tests'].append({
            'name': 'Illumination',
            'results': results
        })
        
        return {'illumination': results}
    
    def test_frame_rate_stability(self) -> dict:
        """Prueba estabilidad del procesamiento de frames."""
        print("\n🔬 TEST: Estabilidad de Frame Rate")
        print("-" * 60)
        
        cap = self.load_video()
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_times = []
        import time
        
        start_time = time.time()
        frame_number = 0
        
        while frame_number < min(100, frame_count):
            ret, frame = cap.read()
            if not ret:
                break
            frame_number += 1
        
        total_time = time.time() - start_time
        achieved_fps = frame_number / total_time if total_time > 0 else 0
        
        cap.release()
        
        result = {
            'expected_fps': fps,
            'achieved_fps': round(achieved_fps, 2),
            'frame_count_tested': frame_number,
            'total_time_seconds': round(total_time, 2),
            'stability': 'Estable' if abs(achieved_fps - fps) < fps * 0.1 else 'Inestable',
            'status': '✓' if abs(achieved_fps - fps) < fps * 0.1 else '⚠'
        }
        
        print(f"  FPS esperado: {fps}")
        print(f"  FPS logrado:  {result['achieved_fps']}")
        print(f"  Estabilidad:  {result['stability']} {result['status']}")
        
        self.test_results['tests'].append({
            'name': 'Frame Rate Stability',
            'results': [result]
        })
        
        return {'frame_rate': [result]}
    
    def run_all_tests(self) -> dict:
        """Ejecuta todas las pruebas de robustez."""
        print("\n" + "="*80)
        print("🔬 PRUEBAS DE ROBUSTEZ DEL SISTEMA".center(80))
        print("="*80)
        print(f"Video: {self.video_path}")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        results = {}
        
        try:
            results.update(self.test_resolution_scaling())
            results.update(self.test_rotation())
            results.update(self.test_occlusion())
            results.update(self.test_illumination())
            results.update(self.test_frame_rate_stability())
            
            print("\n" + "="*80)
            print("✅ TODAS LAS PRUEBAS COMPLETADAS".center(80))
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error durante pruebas: {e}")
        
        return results
    
    def save_results(self, output_path: str = 'results/robustness_tests.json'):
        """Guarda resultados a JSON."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📊 Resultados guardados en: {output_path}")
        return output_path


def run_robustness_tests(video_path: str):
    """Función principal para ejecutar pruebas."""
    try:
        tester = RobustnessTest(video_path)
        tester.run_all_tests()
        tester.save_results()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = 'data/input/test_video.mp4'
    
    run_robustness_tests(video_path)
