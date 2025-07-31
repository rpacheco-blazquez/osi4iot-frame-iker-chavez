"""Módulo de detección de pose usando YOLO."""

import cv2
import numpy as np
from typing import List, Optional
import yaml
import os
from ultralytics import YOLO

class YOLOPoseDetector:
    """Detector de pose usando YOLO."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Inicializa el detector YOLO para pose detection.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config = self._load_config(config_path)
        self.model = None
        self.confidence_threshold = self.config['vision']['confidence_threshold']
        self.model_path = self.config['vision']['yolo_model_path']
        
    def _load_config(self, config_path: str) -> dict:
        """Carga la configuración desde archivo YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
                
        except FileNotFoundError:
            print(f"❌ Archivo de configuración no encontrado: {config_path}")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Configuración por defecto si no se encuentra el archivo."""
        return {
            'vision': {
                'confidence_threshold': 0.87,
                'yolo_model_path': 'models/best.pt'
            }
        }
    
    def load_model(self) -> bool:
        """Carga el modelo YOLO para pose detection.
        
        Returns:
            True si el modelo se cargó correctamente, False en caso contrario
        """
        try:
            if not os.path.exists(self.model_path):
                print(f"❌ Archivo de modelo no encontrado: {self.model_path}")
                return False
            
            self.model = YOLO(self.model_path)
            print(f"✅ Modelo YOLO cargado exitosamente desde: {self.model_path}")
            print(f"📊 Clases del modelo: {list(self.model.names.values())}")
            return True
                
        except Exception as e:
            print(f"❌ Error al cargar el modelo: {e}")
            return False
    
    def detect(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Detecta poses en el frame y retorna el frame anotado.
        
        Args:
            frame: Frame de imagen en formato numpy array
            
        Returns:
            Frame anotado con bounding boxes y keypoints, o None si hay error
        """
        if self.model is None:
            print("❌ Modelo no cargado. Llamar a load_model() primero.")
            return None
        
        try:
            # Realizar detección con YOLO
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            # Usar el método plot() que automáticamente dibuja keypoints y bounding boxes
            annotated_frame = results[0].plot()
            return annotated_frame
            
        except Exception as e:
            print(f"⚠️ Error en detección YOLO: {e}")
            return None
    
    def get_detections_data(self, frame: np.ndarray) -> List[dict]:
        """Obtiene los datos de detección sin anotar el frame.
        
        Args:
            frame: Frame de imagen en formato numpy array
            
        Returns:
            Lista de detecciones con información de bounding boxes, keypoints y confianza
        """
        if self.model is None:
            print("❌ Modelo no cargado. Llamar a load_model() primero.")
            return []
        
        detections = []
        
        try:
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i, box in enumerate(boxes):
                        # Extraer información básica
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.model.names[class_id]
                        
                        detection = {
                            'bbox': [float(x1), float(y1), float(x2), float(y2)],
                            'confidence': confidence,
                            'class_id': class_id,
                            'class_name': class_name,
                            'keypoints': None
                        }
                        
                        # Agregar keypoints si están disponibles
                        if hasattr(result, 'keypoints') and result.keypoints is not None:
                            keypoints_data = result.keypoints
                            if i < len(keypoints_data.xy):
                                kpts_xy = keypoints_data.xy[i].cpu().numpy()
                                kpts_conf = keypoints_data.conf[i].cpu().numpy()
                                keypoints = np.column_stack([kpts_xy, kpts_conf])
                                detection['keypoints'] = keypoints
                        
                        detections.append(detection)
                        
        except Exception as e:
            print(f"⚠️ Error en detección: {e}")
            
        return detections

    def draw_detections(self, frame: np.ndarray, detections: List[dict]) -> np.ndarray:
        """Dibuja las detecciones en el frame.
        
        Args:
            frame: Frame original
            detections: Lista de detecciones
            
        Returns:
            Frame con las detecciones dibujadas
        """
        result_frame = frame.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            class_name = detection['class_name']
            keypoints = detection.get('keypoints')
            
            # Dibujar bounding box
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Dibujar etiqueta
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result_frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(result_frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            # Dibujar keypoints si están disponibles
            if keypoints is not None:
                for kpt in keypoints:
                    x, y, conf = kpt
                    if conf > 0.5:  # Solo dibujar keypoints con alta confianza
                        cv2.circle(result_frame, (int(x), int(y)), 3, (0, 0, 255), -1)
        
        return result_frame

    
    def run_real_time_detection(self, camera_index: int = 0) -> None:
        """Ejecuta detección en tiempo real usando la cámara.
        
        Args:
            camera_index: Índice de la cámara (0 por defecto)
        """
        print("🚀 Iniciando detección en tiempo real...")
        print(f"📁 Usando modelo: {self.model_path}")
        
        if not self.load_model():
            print("❌ No se pudo cargar el modelo.")
            return
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("❌ No se pudo abrir la cámara.")
            return
        
        print("📹 Presiona 'q' para salir.")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ No se pudo leer el frame de la cámara.")
                break
            
            # Realizar detección y obtener frame anotado
            annotated_frame = self.detect(frame)
            if annotated_frame is not None:
                cv2.imshow("Detección YOLO - Bounding Boxes y Keypoints", annotated_frame)
            else:
                cv2.imshow("Detección YOLO - Bounding Boxes y Keypoints", frame)
            
            # Salir si se presiona 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Limpiar recursos
        cap.release()
        cv2.destroyAllWindows()
        print("🔚 Detección finalizada.")


def main():
    """Función principal para ejecutar detección en tiempo real."""
    detector = YOLOPoseDetector()
    detector.run_real_time_detection()


if __name__ == "__main__":
    main()