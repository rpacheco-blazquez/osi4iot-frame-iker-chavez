"""Calculador de distancia para la clase marcador.

Este módulo calcula la distancia en tiempo real entre el punto medio de la bounding box
superior de la clase 'marcador' y el punto medio de los keypoints de la misma clase.
"""

import cv2
import numpy as np
import math
import time
from typing import List, Dict, Optional, Tuple
from collections import deque
from scipy.optimize import least_squares


class MarkerDistanceCalculator:
    """Calculador de distancia para la clase marcador."""
    
    def __init__(self, pixels_per_cm: float = 10.0, enable_mqtt: bool = True, config_path: str = None, dicapua_publisher=None):
        """
        Inicializa el calculador de distancia para marcador.
        
        Args:
            pixels_per_cm: Factor de conversión píxeles a centímetros
            enable_mqtt: Si habilitar la comunicación directa
            config_path: Ruta al archivo de configuración (no usado actualmente)
            dicapua_publisher: Instancia de DicapuaPublisher para comunicación directa
        """
        self.pixels_per_cm = pixels_per_cm
        self.auto_calibrated = False
        self.calibration_history = deque(maxlen=10)
        self.dicapua_publisher = dicapua_publisher
        
        # Filtros Kalman para suavizado
        self.kalman_filters = {}
        
        # Configuración de validación
        self.max_distance_cm = 100.0  # Distancia máxima válida
        self.error_threshold = 0.3  # Umbral de error para validación geométrica
        
        # Configuración de comunicación directa
        self.enable_mqtt = enable_mqtt
        self.mqtt_connected = True if dicapua_publisher else False
        self.last_distance_sent = None
        
        # Detector de movimiento
        from postprocess.movement_detector import MovementDetector
        import os
        config_file = os.path.join(os.path.dirname(__file__), 'movement_config.json')
        self.movement_detector = MovementDetector(
            distance_threshold_cm=0.5,
            velocity_threshold_cm_s=10.0,
            position_stability_frames=1,
            temporal_window_seconds=0.5,
            config_file=config_file if os.path.exists(config_file) else None
        )
        
        # Deshabilitar filtros problemáticos para el marcador
        self.movement_detector.enable_filter('velocity', False)
        self.movement_detector.enable_filter('relative_movement', False)
        
        print(f"🔧 MarkerDistanceCalculator inicializado en modo {'directo' if dicapua_publisher else 'standalone'}")
        
    def get_marker_bbox_top_midpoint(self, detections: List[Dict]) -> Optional[Tuple[float, float]]:
        """
        Obtiene el punto medio de la parte superior de la bounding box de la clase 'marcador'.
        
        Args:
            detections: Lista de detecciones con bounding boxes
            
        Returns:
            Coordenadas del punto medio superior de la bbox del marcador o None
        """
        for detection in detections:
            if detection.get('class_name') == 'marcador' and 'bbox' in detection:
                bbox = detection['bbox']
                # bbox formato: [x1, y1, x2, y2]
                x1, y1, x2, y2 = bbox
                
                # Punto medio de la parte superior
                mid_x = (x1 + x2) / 2
                top_y = y1  # Parte superior de la bbox
                
                return (mid_x, top_y)
        return None
        
    def get_marker_keypoints_midpoint(self, detections: List[Dict]) -> Optional[Tuple[float, float]]:
        """
        Obtiene el punto medio de todos los keypoints de la clase 'marcador'.
        
        Args:
            detections: Lista de detecciones con keypoints
            
        Returns:
            Coordenadas del punto medio de los keypoints del marcador o None
        """
        for detection in detections:
            if detection.get('class_name') == 'marcador' and 'keypoints' in detection:
                keypoints = detection['keypoints']
                
                # Filtrar keypoints válidos (con confianza > 0.5)
                valid_keypoints = []
                for kp in keypoints:
                    if len(kp) >= 3 and kp[2] > 0.5:  # x, y, confidence
                        valid_keypoints.append((kp[0], kp[1]))
                
                if valid_keypoints:
                    # Calcular punto medio
                    x_coords = [kp[0] for kp in valid_keypoints]
                    y_coords = [kp[1] for kp in valid_keypoints]
                    
                    mid_x = sum(x_coords) / len(x_coords)
                    mid_y = sum(y_coords) / len(y_coords)
                    
                    return (mid_x, mid_y)
        return None
        
    def calculate_euclidean_distance(self, point1: Tuple[float, float], 
                                   point2: Tuple[float, float]) -> float:
        """
        Calcula la distancia euclidiana entre dos puntos.
        
        Args:
            point1: Primer punto (x, y)
            point2: Segundo punto (x, y)
            
        Returns:
            Distancia euclidiana en píxeles
        """
        x1, y1 = point1
        x2, y2 = point2
        return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
    def pixels_to_cm(self, distance_pixels: float) -> float:
        """
        Convierte distancia en píxeles a centímetros.
        
        Args:
            distance_pixels: Distancia en píxeles
            
        Returns:
            Distancia en centímetros
        """
        return distance_pixels / self.pixels_per_cm
        
    def calculate_marker_distance(self, detections: List[Dict]) -> Optional[float]:
        """
        Calcula la distancia entre el punto medio superior de la bbox del marcador
        y el punto medio de sus keypoints.
        
        Args:
            detections: Lista de detecciones
            
        Returns:
            Distancia en centímetros o None si no se puede calcular
        """
        bbox_midpoint = self.get_marker_bbox_top_midpoint(detections)
        keypoints_midpoint = self.get_marker_keypoints_midpoint(detections)
        
        if bbox_midpoint is None or keypoints_midpoint is None:
            return None
            
        distance_pixels = self.calculate_euclidean_distance(bbox_midpoint, keypoints_midpoint)
        distance_cm = self.pixels_to_cm(distance_pixels) -0.9 # Ajuste para el muelle provisional del marcador (luego quitar)
        
        # Convertir distancias negativas a 0 cm
        if distance_cm < 0:
            distance_cm = 0.0
        
        # Validar límite máximo
        if distance_cm > self.max_distance_cm:
            # Aplicar corrección suave si está ligeramente por encima
            if distance_cm < self.max_distance_cm * 1.1:
                distance_cm = self.max_distance_cm
            else:
                return None  # Distancia demasiado grande, probablemente error
        
        # Enviar datos por comunicación directa si está habilitado
        if distance_cm is not None:
            self._send_distance_mqtt(detections, distance_cm)
        
        return distance_cm 
        
    def _connect_local_mqtt(self):
        """
        Método mantenido por compatibilidad pero no usado en modo directo.
        """
        if self.dicapua_publisher:
            # En modo directo, la conexión ya está establecida
            self.mqtt_connected = True
            return
            
        # Modo standalone (sin dicapua_publisher)
        self.mqtt_connected = False
        print("⚠️ MarkerDistanceCalculator en modo standalone - sin comunicación externa")
        
    def _send_distance_mqtt(self, detections: List[Dict], distance_cm: float):
        """
        Envía datos de distancia por comunicación directa.

        Args:
            detections: Lista de detecciones
            distance_cm: Distancia calculada en centímetros
        """
        if not self.enable_mqtt or not self.mqtt_connected:
            return

        # Obtener posiciones para el detector de movimiento
        bbox_pos = self.get_marker_bbox_top_midpoint(detections)
        keypoints_pos = self.get_marker_keypoints_midpoint(detections)

        # Actualizar detector de movimiento con posiciones actuales
        self.movement_detector.update_positions(bbox_pos, keypoints_pos, distance_cm)

        # Solo enviar si hay variación significativa en la distancia
        # (por ejemplo, si la diferencia con el último valor enviado supera un umbral)
        min_variation_cm = 0.2  # Puedes ajustar este valor
        if self.last_distance_sent is None or abs(distance_cm - self.last_distance_sent) > min_variation_cm:
            try:
                # Enviar por comunicación directa
                if self.dicapua_publisher:
                    import datetime

                    payload = {
                        "distance_cm": float(distance_cm),
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": "marker_distance"
                    }

                    # Enviar directamente al publisher
                    self.dicapua_publisher.send_marker_distance(payload)
                    self.last_distance_sent = distance_cm

                    # Log de métricas de movimiento
                    metrics = self.movement_detector.get_movement_metrics()
                    print(f"📤 Distancia marcador enviada directamente: {distance_cm:.2f} cm")
                    print(f"📊 Métricas marcador: Vel_bbox={metrics.get('pulsador_velocity_px_s', 0):.2f}px/s, "
                          f"Vel_relativa={metrics.get('relative_velocity_px_s', 0):.2f}px/s, "
                          f"Vel_distancia={metrics.get('distance_velocity_cm_s', 0):.2f}cm/s")

            except Exception as e:
                print(f"❌ Error al enviar datos marcador por comunicación directa: {e}")
        
    def draw_distance_on_frame(self, frame: np.ndarray, detections: List[Dict], 
                              show_distance: bool = True, show_line: bool = True) -> np.ndarray:
        """
        Dibuja la distancia calculada del marcador en el frame.
        
        Args:
            frame: Frame de video
            detections: Lista de detecciones
            show_distance: Si mostrar el texto de distancia
            show_line: Si mostrar la línea de distancia
            
        Returns:
            Frame con la distancia dibujada
        """
        frame_copy = frame.copy()
        
        # Calcular distancia
        distance_cm = self.calculate_marker_distance(detections)
        
        if distance_cm is not None:
            # Obtener puntos para dibujar
            bbox_midpoint = self.get_marker_bbox_top_midpoint(detections)
            keypoints_midpoint = self.get_marker_keypoints_midpoint(detections)
            
            if bbox_midpoint and keypoints_midpoint:
                pt1 = (int(bbox_midpoint[0]), int(bbox_midpoint[1]))
                pt2 = (int(keypoints_midpoint[0]), int(keypoints_midpoint[1]))
                
                # Dibujar línea entre los puntos si está habilitado
                if show_line:
                    cv2.line(frame_copy, pt1, pt2, (255, 165, 0), 2)  # Línea naranja
                    
                    # Punto medio para mostrar distancia
                    mid_x = int((pt1[0] + pt2[0]) / 2)
                    mid_y = int((pt1[1] + pt2[1]) / 2)
                    cv2.putText(frame_copy, f"{distance_cm:.1f}cm", (mid_x, mid_y - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
                
                # Dibujar puntos
                cv2.circle(frame_copy, pt1, 5, (255, 0, 255), -1)  # Punto magenta para bbox superior
                cv2.circle(frame_copy, pt2, 5, (0, 255, 255), -1)  # Punto cian para keypoints
                
                # Etiquetas
                cv2.putText(frame_copy, "Bbox", (pt1[0] + 10, pt1[1] - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                cv2.putText(frame_copy, "Keypts", (pt2[0] + 10, pt2[1] - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                # Dibujar texto con la distancia si está habilitado
                if show_distance:
                    text = f"Z Distance: {distance_cm:.2f} cm"
                    text_position = (30, 110)  # Posición diferente al otro calculador
                    
                    # Fondo para el texto
                    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                    cv2.rectangle(frame_copy, 
                                (text_position[0] - 10, text_position[1] - text_size[1] - 10),
                                (text_position[0] + text_size[0] + 10, text_position[1] + 10),
                                (0, 0, 0), -1)
                    
                    # Texto
                    cv2.putText(frame_copy, text, text_position,
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2)
                          
        else:
            # Mostrar mensaje cuando no se puede detectar el marcador
            cv2.putText(frame_copy, "No se detecta marcador con keypoints", (30, 110),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                      
        return frame_copy
        
    def get_distance_info(self, detections: List[Dict]) -> Dict:
        """
        Obtiene información completa sobre la distancia calculada del marcador.
        
        Args:
            detections: Lista de detecciones
            
        Returns:
            Diccionario con información de la distancia
        """
        bbox_midpoint = self.get_marker_bbox_top_midpoint(detections)
        keypoints_midpoint = self.get_marker_keypoints_midpoint(detections)
        distance_cm = self.calculate_marker_distance(detections)
        
        # Obtener métricas de movimiento
        movement_metrics = self.movement_detector.get_movement_metrics()
        filter_statistics = self.movement_detector.get_filter_statistics()
        
        return {
            'marker_bbox_midpoint': bbox_midpoint,
            'marker_keypoints_midpoint': keypoints_midpoint,
            'distance_cm': distance_cm,
            'distance_pixels': self.calculate_euclidean_distance(bbox_midpoint, keypoints_midpoint) if bbox_midpoint and keypoints_midpoint else None,
            'calibration_factor': self.pixels_per_cm,
            'movement_metrics': movement_metrics,
            'filter_statistics': filter_statistics
        }
        
    def disconnect_mqtt(self):
        """
        Desconecta la comunicación directa.
        """
        if self.dicapua_publisher:
            self.mqtt_connected = False
            print("🔌 Comunicación directa marcador desconectada")
        else:
            self.mqtt_connected = False
            print("🔌 MarkerDistanceCalculator desconectado")
    
    def set_mqtt_enabled(self, enabled: bool, broker_host: str = None, broker_port: int = None):
        """
        Habilita o deshabilita la comunicación directa.
        
        Args:
            enabled: True para habilitar, False para deshabilitar
            broker_host: No usado en modo directo
            broker_port: No usado en modo directo
        """
        if enabled and not self.enable_mqtt:
            self.enable_mqtt = True
            if self.dicapua_publisher:
                self.mqtt_connected = True
                print("✅ Comunicación directa habilitada para marcador")
            else:
                self.mqtt_connected = False
                print("⚠️ Sin dicapua_publisher - modo standalone")
        elif not enabled and self.enable_mqtt:
            self.disconnect_mqtt()
            self.enable_mqtt = False
            print("🔌 Comunicación directa deshabilitada para marcador")
            
    def set_calibration(self, pixels_per_cm: float):
        """
        Establece el factor de calibración para conversión píxeles-cm.
        
        Args:
            pixels_per_cm: Número de píxeles que equivalen a 1 cm
        """
        self.pixels_per_cm = pixels_per_cm
    
    def set_dicapua_publisher(self, dicapua_publisher):
        """
        Establece la instancia de DicapuaPublisher para comunicación directa.
        
        Args:
            dicapua_publisher: Instancia de DicapuaPublisher
        """
        self.dicapua_publisher = dicapua_publisher
        if dicapua_publisher:
            self.mqtt_connected = True
            print("✅ DicapuaPublisher configurado para marker_distance_calculator")
        else:
            self.mqtt_connected = False
            print("⚠️ DicapuaPublisher removido de marker_distance_calculator")
    
    def get_mqtt_status(self) -> Dict:
        """
        Obtiene el estado actual de la comunicación directa.
        
        Returns:
            Diccionario con el estado de comunicación
        """
        return {
            'enabled': self.enable_mqtt,
            'connected': self.mqtt_connected,
            'last_distance_sent': self.last_distance_sent,
            'mode': 'direct' if self.dicapua_publisher else 'standalone',
            'dicapua_publisher_available': self.dicapua_publisher is not None
        }