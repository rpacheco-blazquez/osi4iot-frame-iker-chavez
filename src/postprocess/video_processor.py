import cv2
import numpy as np
from typing import Optional, Callable
import threading
import time

from .distance_calculator import DistanceCalculator
from ..vision.detector import YOLOPoseDetector

class VideoPostProcessor:
    """
    Procesador de video en tiempo real con cálculo de distancias.
    """
    
    def __init__(self, model_path: str = "models/best.pt", pixels_per_cm: float = 10.0):
        """
        Inicializa el procesador de video.
        
        Args:
            model_path: Ruta al modelo YOLO
            pixels_per_cm: Factor de conversión píxeles a centímetros
        """
        self.detector = YOLOPoseDetector(model_path)
        # Cargar el modelo YOLO
        if not self.detector.load_model():
            print("⚠️ Advertencia: No se pudo cargar el modelo YOLO")
        
        self.distance_calculator = DistanceCalculator(pixels_per_cm)
        self.cap = None
        self.is_running = False
        self.current_frame = None
        self.current_detections = []
        self.current_distance = None
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        
    def set_calibration(self, pixels_per_cm: float):
        """
        Actualiza el factor de calibración.
        
        Args:
            pixels_per_cm: Nuevo factor de conversión
        """
        self.distance_calculator.set_calibration(pixels_per_cm)
        
    def start_camera(self, camera_index: int = 0) -> bool:
        """
        Inicia la captura de video desde la cámara.
        
        Args:
            camera_index: Índice de la cámara
            
        Returns:
            True si se inició correctamente, False en caso contrario
        """
        try:
            self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                print(f"Error: No se pudo abrir la cámara {camera_index}")
                return False
                
            # Configurar resolución
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            return True
        except Exception as e:
            print(f"Error al iniciar la cámara: {e}")
            return False
            
    def stop_camera(self):
        """
        Detiene la captura de video.
        """
        if self.cap:
            self.cap.release()
            self.cap = None
            
    def process_frame(self, frame: np.ndarray) -> tuple:
        """
        Procesa un frame individual.
        
        Args:
            frame: Frame de entrada
            
        Returns:
            Tupla (frame_procesado, detecciones, distancia_cm)
        """
        # Detectar objetos y keypoints
        detections = self.detector.get_detections_data(frame)
        
        # Calcular distancia
        distance_cm = self.distance_calculator.calculate_pulsador_portico_distance(detections)
        
        # Dibujar detecciones en el frame
        processed_frame = self.detector.detect(frame)
        
        # Dibujar distancia
        processed_frame = self.distance_calculator.draw_distance_on_frame(processed_frame, detections)
        
        # Actualizar información de estado
        self.current_detections = detections
        self.current_distance = distance_cm
        
        return processed_frame, detections, distance_cm
        
    def run_real_time_processing(self, window_name: str = "Postprocesamiento - Distancias"):
        """
        Ejecuta el procesamiento en tiempo real.
        
        Args:
            window_name: Nombre de la ventana de visualización
        """
        if not self.start_camera():
            return
            
        self.is_running = True
        self.start_time = time.time()
        self.frame_count = 0
        
        print("Iniciando procesamiento en tiempo real...")
        print("Presiona 'q' para salir")
        print("Presiona 'c' para calibrar (ajustar factor píxeles/cm)")
        
        try:
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: No se pudo leer el frame")
                    break
                    
                # Procesar frame
                processed_frame, detections, distance_cm = self.process_frame(frame)
                
                # Calcular FPS
                self.frame_count += 1
                elapsed_time = time.time() - self.start_time
                if elapsed_time > 0:
                    self.fps = self.frame_count / elapsed_time
                    
                # Agregar información de FPS
                cv2.putText(processed_frame, f"FPS: {self.fps:.1f}", (10, 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                          
                # Agregar información de calibración
                cv2.putText(processed_frame, f"Calibracion: {self.distance_calculator.pixels_per_cm:.1f} px/cm", 
                          (10, processed_frame.shape[0] - 20),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Mostrar frame
                cv2.imshow(window_name, processed_frame)
                
                # Manejar teclas
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('c'):
                    self._calibrate_interactive()
                    
        except KeyboardInterrupt:
            print("\nInterrumpido por el usuario")
        finally:
            self.stop_camera()
            cv2.destroyAllWindows()
            self.is_running = False
            
    def _calibrate_interactive(self):
        """
        Calibración interactiva del factor píxeles/cm.
        """
        print("\n=== CALIBRACIÓN ===")
        print(f"Factor actual: {self.distance_calculator.pixels_per_cm:.2f} píxeles/cm")
        try:
            new_factor = float(input("Introduce el nuevo factor (píxeles por cm): "))
            if new_factor > 0:
                self.set_calibration(new_factor)
                print(f"Nuevo factor establecido: {new_factor:.2f} píxeles/cm")
            else:
                print("Error: El factor debe ser positivo")
        except ValueError:
            print("Error: Introduce un número válido")
        print("==================\n")
        
    def get_current_info(self) -> dict:
        """
        Obtiene información actual del procesamiento.
        
        Returns:
            Diccionario con información actual
        """
        return {
            'fps': self.fps,
            'distance_cm': self.current_distance,
            'detections_count': len(self.current_detections),
            'calibration_factor': self.distance_calculator.pixels_per_cm,
            'is_running': self.is_running
        }
        
    def save_current_frame(self, filename: str = None):
        """
        Guarda el frame actual procesado.
        
        Args:
            filename: Nombre del archivo (opcional)
        """
        if self.current_frame is not None:
            if filename is None:
                timestamp = int(time.time())
                filename = f"postprocess_frame_{timestamp}.jpg"
                
            cv2.imwrite(filename, self.current_frame)
            print(f"Frame guardado como: {filename}")
        else:
            print("No hay frame actual para guardar")

def main():
    """
    Función principal para ejecutar el postprocesamiento.
    """
    processor = VideoPostProcessor()
    processor.run_real_time_processing()

if __name__ == "__main__":
    main()