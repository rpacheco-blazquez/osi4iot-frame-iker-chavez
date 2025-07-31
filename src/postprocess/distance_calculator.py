import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
import math
import datetime
import os
import sys
from collections import deque
from scipy.optimize import least_squares
from pathlib import Path

# Agregar el directorio src al path para imports
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

# from mqtt.manager import MQTTManager  # Módulo no disponible
from postprocess.movement_detector import MovementDetector

class DistanceCalculator:
    """
    Calculadora de distancias para análisis de detecciones.
    Calcula distancias entre objetos detectados y keypoints.
    """
    
    def __init__(self, pixels_per_cm: float = 10.0, enable_mqtt: bool = True, config_path: str = "config/config.yaml", dicapua_publisher=None):
        """
        Inicializa el calculador de distancias con corrección de errores avanzada y comunicación directa.
        
        Args:
            pixels_per_cm: Factor de conversión de píxeles a centímetros (se calculará automáticamente)
            enable_mqtt: Si habilitar la comunicación (ahora comunicación directa)
            config_path: Ruta al archivo de configuración
            dicapua_publisher: Instancia de DicapuaPublisher para comunicación directa
        """
        self.pixels_per_cm = pixels_per_cm
        self.calibration_reference = None
        self.auto_calibrated = False
        self.reference_distance_cm = 21.0  # Distancia conocida entre keypoints C y B del pórtico
        self.calibration_history = deque(maxlen=10)
        self.keypoint_history = deque(maxlen=5)  # Para filtrado temporal
        self.max_distance_cm = 30.0  # Límite máximo de distancia
        
        # Dimensiones conocidas del rectángulo del pórtico
        self.portico_width_cm = 30.0  # D a C
        self.portico_height_cm = 21.0  # C a B y D a A
        
        # Filtros Kalman para cada keypoint
        self.kalman_filters = {}
        self.error_threshold = 0.15  # 15% de error máximo permitido
        
        # Configuración de comunicación directa
        self.enable_mqtt = enable_mqtt
        self.dicapua_publisher = dicapua_publisher
        self.mqtt_connected = True if dicapua_publisher else False
        self.last_distance_sent = None
        self.distance_send_threshold = 0.5  # Enviar solo si la distancia cambia más de 0.5 cm
        self.frame_counter = 0
        
        # Movement detector for intelligent sending
        config_file = os.path.join(os.path.dirname(__file__), 'movement_config.json')
        self.movement_detector = MovementDetector(
            distance_threshold_cm=0.5,
            velocity_threshold_cm_s=0.2,
            position_stability_frames=5,
            temporal_window_seconds=2.0,
            config_file=config_file if os.path.exists(config_file) else None
        )
        
        print(f"🔧 DistanceCalculator inicializado en modo {'directo' if dicapua_publisher else 'standalone'}")
        
    def set_calibration(self, pixels_per_cm: float):
        """
        Establece el factor de calibración para conversión píxeles-cm.
        
        Args:
            pixels_per_cm: Número de píxeles que equivalen a 1 cm
        """
        self.pixels_per_cm = pixels_per_cm
        
    def calculate_midpoint(self, points: List[Tuple[float, float]]) -> Tuple[float, float]:
        """
        Calcula el punto medio de una lista de puntos.
        
        Args:
            points: Lista de puntos (x, y)
            
        Returns:
            Tupla con las coordenadas del punto medio (x, y)
        """
        if not points:
            return (0.0, 0.0)
            
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        
        mid_x = sum(x_coords) / len(x_coords)
        mid_y = sum(y_coords) / len(y_coords)
        
        return (mid_x, mid_y)
        
    def get_pulsador_midpoint(self, detections: List[Dict]) -> Optional[Tuple[float, float]]:
        """
        Obtiene el punto medio del pulsador con filtrado temporal.
        """
        for detection in detections:
            if detection.get('class_name') == 'pulsador' and 'keypoints' in detection:
                keypoints = detection['keypoints']
                if len(keypoints) >= 4:
                    try:
                        # Aplicar filtrado Kalman a cada keypoint
                        filtered_keypoints = []
                        for i, kp in enumerate(keypoints[:4]):
                            if len(kp) >= 3 and kp[2] > 0.5:
                                filtered_x, filtered_y = self._filter_keypoint(kp, f"pulsador_{i}")
                                filtered_keypoints.append((filtered_x, filtered_y, kp[2]))
                        
                        if len(filtered_keypoints) >= 2:
                            # Calcular centro ponderado por confianza
                            total_weight = sum(kp[2] for kp in filtered_keypoints)
                            if total_weight > 0:
                                center_x = sum(kp[0] * kp[2] for kp in filtered_keypoints) / total_weight
                                center_y = sum(kp[1] * kp[2] for kp in filtered_keypoints) / total_weight
                                
                                # Agregar a historial para suavizado temporal
                                self.keypoint_history.append((center_x, center_y))
                                
                                # Promedio temporal
                                if len(self.keypoint_history) > 1:
                                    weights = np.exp(np.linspace(-0.5, 0, len(self.keypoint_history)))
                                    weights /= weights.sum()
                                    
                                    avg_x = np.average([p[0] for p in self.keypoint_history], weights=weights)
                                    avg_y = np.average([p[1] for p in self.keypoint_history], weights=weights)
                                    
                                    return (avg_x, avg_y)
                                else:
                                    return (center_x, center_y)
                            
                    except Exception:
                        continue
        
        return None
        
    def get_portico_keypoint_d(self, detections: List[Dict]) -> Optional[Tuple[float, float]]:
        """
        Obtiene el keypoint D del pórtico con filtrado y corrección.
        """
        for detection in detections:
            if detection.get('class_name') == 'portico' and 'keypoints' in detection:
                keypoints = detection['keypoints']
                if len(keypoints) >= 4:
                    try:
                        # Validar y corregir geometría si es necesario
                        keypoints_tuples = [(kp[0], kp[1], kp[2]) for kp in keypoints if len(kp) >= 3]
                        if not self._validate_rectangle_geometry(keypoints_tuples):
                            keypoints_tuples = self._correct_keypoints_geometry(keypoints_tuples)
                        
                        if len(keypoints_tuples) >= 4:
                            keypoint_d = keypoints_tuples[3]  # Keypoint D
                            
                            if keypoint_d[2] > 0.5:
                                # Aplicar filtrado Kalman
                                filtered_x, filtered_y = self._filter_keypoint(keypoint_d, "portico_d")
                                return (filtered_x, filtered_y)
                                
                    except Exception:
                        continue
        
        return None
        
    def get_portico_keypoint_c(self, detections: List[Dict]) -> Optional[Tuple[float, float]]:
        """
        Obtiene el keypoint C de la clase 'portico'.
        
        Args:
            detections: Lista de detecciones con keypoints
            
        Returns:
            Coordenadas del keypoint C del pórtico o None si no se encuentra
        """
        for detection in detections:
            if detection.get('class_name') == 'portico' and 'keypoints' in detection:
                keypoints = detection['keypoints']
                # Keypoint C es el índice 2 (0-indexed: A=0, B=1, C=2, D=3)
                if len(keypoints) > 2 and keypoints[2][2] > 0.5:  # Verificar visibilidad
                    return (keypoints[2][0], keypoints[2][1])
        return None
        
    def get_portico_keypoint_b(self, detections: List[Dict]) -> Optional[Tuple[float, float]]:
        """
        Obtiene el keypoint B de la clase 'portico'.
        
        Args:
            detections: Lista de detecciones con keypoints
            
        Returns:
            Coordenadas del keypoint B del pórtico o None si no se encuentra
        """
        for detection in detections:
            if detection.get('class_name') == 'portico' and 'keypoints' in detection:
                keypoints = detection['keypoints']
                # Keypoint B es el índice 1 (0-indexed: A=0, B=1, C=2, D=3)
                if len(keypoints) > 1 and keypoints[1][2] > 0.5:  # Verificar visibilidad
                    return (keypoints[1][0], keypoints[1][1])
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
        
    def _init_kalman_filter(self, keypoint_id: str) -> cv2.KalmanFilter:
        """
        Inicializa un filtro Kalman para un keypoint específico.
        """
        kalman = cv2.KalmanFilter(4, 2)
        kalman.measurementMatrix = np.array([[1, 0, 0, 0],
                                           [0, 1, 0, 0]], np.float32)
        kalman.transitionMatrix = np.array([[1, 0, 1, 0],
                                          [0, 1, 0, 1],
                                          [0, 0, 1, 0],
                                          [0, 0, 0, 1]], np.float32)
        kalman.processNoiseCov = 0.03 * np.eye(4, dtype=np.float32)
        kalman.measurementNoiseCov = 0.1 * np.eye(2, dtype=np.float32)
        kalman.errorCovPost = 0.1 * np.eye(4, dtype=np.float32)
        return kalman
    
    def _filter_keypoint(self, keypoint: Tuple[float, float, float], keypoint_id: str) -> Tuple[float, float]:
        """
        Aplica filtrado Kalman a un keypoint para reducir ruido.
        """
        if keypoint_id not in self.kalman_filters:
            self.kalman_filters[keypoint_id] = self._init_kalman_filter(keypoint_id)
            # Inicializar estado
            self.kalman_filters[keypoint_id].statePre = np.array([keypoint[0], keypoint[1], 0, 0], dtype=np.float32)
        
        kalman = self.kalman_filters[keypoint_id]
        
        # Predicción
        prediction = kalman.predict()
        
        # Actualización con medición
        measurement = np.array([[keypoint[0]], [keypoint[1]]], dtype=np.float32)
        kalman.correct(measurement)
        
        return float(prediction[0]), float(prediction[1])
    
    def _validate_rectangle_geometry(self, keypoints: List[Tuple[float, float, float]]) -> bool:
        """
        Valida que los keypoints formen un rectángulo con las dimensiones esperadas.
        """
        if len(keypoints) < 4:
            return False
        
        try:
            # Extraer puntos A, B, C, D
            points = [(kp[0], kp[1]) for kp in keypoints[:4] if kp[2] > 0.5]
            if len(points) < 4:
                return False
            
            # Calcular distancias
            dist_dc = math.sqrt((points[3][0] - points[2][0])**2 + (points[3][1] - points[2][1])**2)
            dist_cb = math.sqrt((points[2][0] - points[1][0])**2 + (points[2][1] - points[1][1])**2)
            dist_da = math.sqrt((points[3][0] - points[0][0])**2 + (points[3][1] - points[0][1])**2)
            
            # Verificar proporciones (debe ser aproximadamente 30:21)
            if dist_dc > 0 and dist_cb > 0:
                ratio = dist_dc / dist_cb
                expected_ratio = self.portico_width_cm / self.portico_height_cm
                error = abs(ratio - expected_ratio) / expected_ratio
                return error < self.error_threshold
                
        except (IndexError, ZeroDivisionError):
            pass
            
        return False
    
    def _correct_keypoints_geometry(self, keypoints: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
        """
        Corrige la geometría de los keypoints usando mínimos cuadrados.
        """
        if len(keypoints) < 4:
            return keypoints
        
        try:
            # Extraer puntos válidos
            points = np.array([(kp[0], kp[1]) for kp in keypoints[:4] if kp[2] > 0.5])
            confidences = [kp[2] for kp in keypoints[:4] if kp[2] > 0.5]
            
            if len(points) < 4:
                return keypoints
            
            # Función objetivo para optimización
            def objective(params):
                # params: [center_x, center_y, width, height, angle]
                cx, cy, w, h, angle = params
                
                # Calcular posiciones ideales del rectángulo
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                ideal_points = np.array([
                    [cx - w/2*cos_a + h/2*sin_a, cy - w/2*sin_a - h/2*cos_a],  # A
                    [cx - w/2*cos_a - h/2*sin_a, cy - w/2*sin_a + h/2*cos_a],  # B
                    [cx + w/2*cos_a - h/2*sin_a, cy + w/2*sin_a + h/2*cos_a],  # C
                    [cx + w/2*cos_a + h/2*sin_a, cy + w/2*sin_a - h/2*cos_a]   # D
                ])
                
                # Calcular error ponderado por confianza
                errors = []
                for i, (point, conf) in enumerate(zip(points, confidences)):
                    error = np.linalg.norm(point - ideal_points[i]) * conf
                    errors.append(error)
                
                return errors
            
            # Estimación inicial
            center = np.mean(points, axis=0)
            initial_params = [center[0], center[1], 100, 70, 0]  # Estimación inicial
            
            # Optimización
            result = least_squares(objective, initial_params)
            
            if result.success:
                cx, cy, w, h, angle = result.x
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                
                # Generar puntos corregidos
                corrected_points = [
                    (cx - w/2*cos_a + h/2*sin_a, cy - w/2*sin_a - h/2*cos_a, keypoints[0][2]),  # A
                    (cx - w/2*cos_a - h/2*sin_a, cy - w/2*sin_a + h/2*cos_a, keypoints[1][2]),  # B
                    (cx + w/2*cos_a - h/2*sin_a, cy + w/2*sin_a + h/2*cos_a, keypoints[2][2]),  # C
                    (cx + w/2*cos_a + h/2*sin_a, cy + w/2*sin_a - h/2*cos_a, keypoints[3][2])   # D
                ]
                
                return corrected_points + keypoints[4:]  # Mantener keypoints adicionales
                
        except Exception:
            pass
            
        return keypoints
    
    def auto_calibrate(self, detections: List[Dict]) -> bool:
        """
        Calibra automáticamente con validación geométrica y corrección de errores.
        """
        keypoint_c = self.get_portico_keypoint_c(detections)
        keypoint_b = self.get_portico_keypoint_b(detections)
        
        if keypoint_c is None or keypoint_b is None:
            return False
            
        # Calcular distancia en píxeles entre C y B
        distance_pixels_cb = self.calculate_euclidean_distance(keypoint_c, keypoint_b)
        
        if distance_pixels_cb > 0:
            # Calcular factor de calibración: píxeles / cm
            new_pixels_per_cm = distance_pixels_cb / self.reference_distance_cm
            self.calibration_history.append(new_pixels_per_cm)
            
            # Usar promedio ponderado (más peso a calibraciones recientes)
            weights = np.exp(np.linspace(-1, 0, len(self.calibration_history)))
            weights /= weights.sum()
            
            self.pixels_per_cm = np.average(list(self.calibration_history), weights=weights)
            self.auto_calibrated = True
            return True
            
        return False
        
    def pixels_to_cm(self, distance_pixels: float) -> float:
        """
        Convierte distancia en píxeles a centímetros.
        
        Args:
            distance_pixels: Distancia en píxeles
            
        Returns:
            Distancia en centímetros
        """
        return distance_pixels / self.pixels_per_cm
        
    def calculate_pulsador_portico_distance(self, detections: List[Dict]) -> Optional[float]:
        """
        Calcula la distancia con validación y corrección de errores.
        """
        # Realizar calibración automática si no se ha hecho
        if not self.auto_calibrated:
            self.auto_calibrate(detections)
            
        pulsador_midpoint = self.get_pulsador_midpoint(detections)
        portico_keypoint_d = self.get_portico_keypoint_d(detections)
        
        if pulsador_midpoint is None or portico_keypoint_d is None:
            return None
            
        distance_pixels = self.calculate_euclidean_distance(pulsador_midpoint, portico_keypoint_d)
        distance_cm = self.pixels_to_cm(distance_pixels)
        
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
        
        # Enviar datos por MQTT si está habilitado
        if distance_cm is not None:
            self._send_distance_mqtt(detections, distance_cm)
        
        return distance_cm
        
    def _connect_local_mqtt(self):
        """
        Método mantenido para compatibilidad - ahora usa comunicación directa.
        """
        if self.dicapua_publisher:
            self.mqtt_connected = True
            print("✅ Comunicación directa establecida para distance_calculator")
        else:
            self.mqtt_connected = False
            print("⚠️ No hay dicapua_publisher disponible para comunicación directa")
    
    def _send_distance_mqtt(self, detections: List[Dict], distance_cm: float):
        """
        Envía datos de distancia directamente a dicapua_publisher.
        
        Args:
            detections: Lista de detecciones
            distance_cm: Distancia calculada en centímetros
        """
        if not self.enable_mqtt or not self.dicapua_publisher:
            return
        
        # Obtener posiciones para el detector de movimiento
        pulsador_pos = self.get_pulsador_midpoint(detections)
        portico_pos = self.get_portico_keypoint_d(detections)
        
        # Actualizar detector de movimiento con posiciones actuales
        self.movement_detector.update_positions(pulsador_pos, portico_pos, distance_cm)
        
        # Verificar si se debe enviar basado en detección de movimiento inteligente
        if not self.movement_detector.should_send_distance(distance_cm):
            return
            
        try:
            # Validar distancia
            if 0 < distance_cm < 1000:
                # Convertir float32 a float para evitar errores de serialización
                distance_cm_float = float(distance_cm)
                
                # Crear payload para comunicación directa
                import datetime
                
                now_utc = datetime.datetime.now()
                timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                
                payload = {
                    "distance_cm": distance_cm_float,
                    "timestamp": timestamp,
                    "source": "distance_calculator",
                    "pulsador_position": pulsador_pos,
                    "portico_position": portico_pos
                }
                
                # Enviar directamente a dicapua_publisher
                success = self.dicapua_publisher.send_distance_data(payload)
                
                if success:
                    self.last_distance_sent = distance_cm_float
                    print(f"📤 Distancia pórtico-pulsador enviada directamente: {distance_cm_float:.2f} cm")
                    # Log de métricas de movimiento
                    metrics = self.movement_detector.get_movement_metrics()
                    print(f"📊 Métricas: Vel_pulsador={metrics['pulsador_velocity_px_s']:.2f}px/s, "
                          f"Vel_relativa={metrics['relative_velocity_px_s']:.2f}px/s, "
                          f"Vel_distancia={metrics['distance_velocity_cm_s']:.2f}cm/s")
                else:
                    print(f"⚠️ Error al enviar distancia directamente")
            else:
                print(f"⚠️ Distancia fuera de rango ignorada: {distance_cm}")
                
        except Exception as e:
            print(f"❌ Error al enviar datos directamente: {e}")
        
    def draw_distance_on_frame(self, frame: np.ndarray, detections: List[Dict], 
                              show_distance: bool = True, show_line: bool = True) -> np.ndarray:
        """
        Dibuja la distancia calculada en el frame con calibración automática.
        
        Args:
            frame: Frame de video
            detections: Lista de detecciones
            show_distance: Si mostrar el texto de distancia
            show_line: Si mostrar la línea de distancia
            
        Returns:
            Frame con la distancia dibujada
        """
        frame_copy = frame.copy()
        
        # Realizar calibración automática si no se ha hecho
        if not self.auto_calibrated:
            calibration_success = self.auto_calibrate(detections)
            if calibration_success:
                cv2.putText(frame_copy, "Calibracion automatica completada", (30, 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Dibujar keypoints de referencia para calibración (C y B del pórtico)
        keypoint_c = self.get_portico_keypoint_c(detections)
        keypoint_b = self.get_portico_keypoint_b(detections)
        
        if keypoint_c and keypoint_b:
            pt_c = (int(keypoint_c[0]), int(keypoint_c[1]))
            pt_b = (int(keypoint_b[0]), int(keypoint_b[1]))
            
            # Dibujar línea de referencia C-B
            cv2.line(frame_copy, pt_c, pt_b, (255, 0, 255), 2)  # Línea magenta
            cv2.circle(frame_copy, pt_c, 4, (255, 0, 255), -1)  # Punto C
            cv2.circle(frame_copy, pt_b, 4, (255, 0, 255), -1)  # Punto B
            
            # Etiquetas para los keypoints
            cv2.putText(frame_copy, "C", (pt_c[0] + 10, pt_c[1] - 10),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
            cv2.putText(frame_copy, "B", (pt_b[0] + 10, pt_b[1] - 10),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
        
        # Calcular distancia
        distance_cm = self.calculate_pulsador_portico_distance(detections)
        
        if distance_cm is not None:
            # Obtener puntos para dibujar
            pulsador_midpoint = self.get_pulsador_midpoint(detections)
            portico_keypoint_d = self.get_portico_keypoint_d(detections)
            
            if pulsador_midpoint and portico_keypoint_d:
                pt1 = (int(pulsador_midpoint[0]), int(pulsador_midpoint[1]))
                pt2 = (int(portico_keypoint_d[0]), int(portico_keypoint_d[1]))
                
                # Dibujar línea entre los puntos si está habilitado
                if show_line:
                    # Dibujar línea horizontal recta para mostrar la distancia X
                    # Usar la coordenada Y del punto D del pórtico como referencia
                    pt1_horizontal = (int(pulsador_midpoint[0]), int(portico_keypoint_d[1]))
                    pt2_horizontal = (int(portico_keypoint_d[0]), int(portico_keypoint_d[1]))
                    
                    cv2.line(frame_copy, pt1_horizontal, pt2_horizontal, (0, 255, 255), 2)  # Línea amarilla horizontal
                    
                    # Punto medio de la línea horizontal para mostrar coordenadas
                    mid_x = int((pt1_horizontal[0] + pt2_horizontal[0]) / 2)
                    mid_y = int(portico_keypoint_d[1])
                    cv2.putText(frame_copy, f"{distance_cm:.1f}cm", (mid_x, mid_y - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Dibujar puntos
                # Punto del pulsador ajustado a la altura del punto D del pórtico
                pt1_adjusted = (int(pulsador_midpoint[0]), int(portico_keypoint_d[1]))
                cv2.circle(frame_copy, pt1_adjusted, 5, (0, 255, 0), -1)  # Punto verde para pulsador (ajustado)
                cv2.circle(frame_copy, pt2, 5, (255, 0, 0), -1)  # Punto azul para pórtico D
                
                # Etiqueta para keypoint D
                cv2.putText(frame_copy, "D", (pt2[0] + 10, pt2[1] - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # Dibujar texto con la distancia si está habilitado
                if show_distance:
                    text = f"X Distance: {distance_cm:.2f} cm"
                    text_position = (30, 70)
                    
                    # Fondo para el texto
                    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                    cv2.rectangle(frame_copy, 
                                (text_position[0] - 10, text_position[1] - text_size[1] - 10),
                                (text_position[0] + text_size[0] + 10, text_position[1] + 10),
                                (0, 0, 0), -1)
                    
                    # Texto
                    cv2.putText(frame_copy, text, text_position,
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                          
        # Mostrar información de calibración
        if self.auto_calibrated:
            calib_text = f"Calibration: {self.pixels_per_cm:.2f} px/cm"
            cv2.putText(frame_copy, calib_text, (30, frame_copy.shape[0] - 30),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(frame_copy, "Esperando calibracion automatica...", (30, frame_copy.shape[0] - 30),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                      
        if distance_cm is None:
            # Mostrar mensaje cuando no se pueden detectar los objetos
            cv2.putText(frame_copy, "No se detectan pulsador y portico", (30, 70),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                      
        return frame_copy
        
    def _get_pulsador_keypoints(self, detections: List[Dict]) -> Optional[List[Tuple[float, float]]]:
        """
        Obtiene los keypoints del pulsador desde las detecciones.
        
        Args:
            detections: Lista de detecciones
            
        Returns:
            Lista de keypoints del pulsador o None
        """
        for detection in detections:
            if detection.get('class_name') == 'pulsador' and 'keypoints' in detection:
                keypoints = detection['keypoints']
                if len(keypoints) >= 4:
                    valid_keypoints = []
                    for kp in keypoints[:4]:
                        if len(kp) >= 3 and kp[2] > 0.5:
                            valid_keypoints.append((kp[0], kp[1]))
                    if valid_keypoints:
                        return valid_keypoints
        return None
    
    def _get_portico_keypoints(self, detections: List[Dict]) -> Optional[Dict[str, Tuple[float, float]]]:
        """
        Obtiene los keypoints del pórtico desde las detecciones.
        
        Args:
            detections: Lista de detecciones
            
        Returns:
            Diccionario con keypoints del pórtico {'A': (x,y), 'B': (x,y), 'C': (x,y), 'D': (x,y)} o None
        """
        for detection in detections:
            if detection.get('class_name') == 'portico' and 'keypoints' in detection:
                keypoints = detection['keypoints']
                if len(keypoints) >= 4:
                    keypoint_dict = {}
                    labels = ['A', 'B', 'C', 'D']
                    for i, (kp, label) in enumerate(zip(keypoints[:4], labels)):
                        if len(kp) >= 3 and kp[2] > 0.5:
                            keypoint_dict[label] = (kp[0], kp[1])
                    if keypoint_dict:
                        return keypoint_dict
        return None
    
    def _calculate_midpoint(self, keypoints: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """
        Calcula el punto medio de una lista de keypoints.
        
        Args:
            keypoints: Lista de keypoints
            
        Returns:
            Punto medio (x, y) o None
        """
        if not keypoints:
            return None
        
        x_coords = [kp[0] for kp in keypoints]
        y_coords = [kp[1] for kp in keypoints]
        
        mid_x = sum(x_coords) / len(x_coords)
        mid_y = sum(y_coords) / len(y_coords)
        
        return (mid_x, mid_y)
    
    def get_distance_info(self, detections: List[Dict]) -> Dict:
        """
        Obtiene información completa sobre la distancia calculada con calibración automática.
        
        Args:
            detections: Lista de detecciones
            
        Returns:
            Diccionario con información de la distancia
        """
        # Realizar calibración automática si no se ha hecho
        if not self.auto_calibrated:
            self.auto_calibrate(detections)
            
        pulsador_midpoint = self.get_pulsador_midpoint(detections)
        portico_keypoint_d = self.get_portico_keypoint_d(detections)
        portico_keypoint_c = self.get_portico_keypoint_c(detections)
        portico_keypoint_b = self.get_portico_keypoint_b(detections)
        distance_cm = self.calculate_pulsador_portico_distance(detections)
        
        # Calcular distancia de referencia C-B en píxeles
        reference_distance_pixels = None
        if portico_keypoint_c and portico_keypoint_b:
            reference_distance_pixels = self.calculate_euclidean_distance(portico_keypoint_c, portico_keypoint_b)
        
        # Obtener métricas de movimiento
        movement_metrics = self.movement_detector.get_movement_metrics()
        filter_statistics = self.movement_detector.get_filter_statistics()
        
        return {
            'pulsador_midpoint': pulsador_midpoint,
            'portico_keypoint_d': portico_keypoint_d,
            'portico_keypoint_c': portico_keypoint_c,
            'portico_keypoint_b': portico_keypoint_b,
            'distance_cm': distance_cm,
            'distance_pixels': self.calculate_euclidean_distance(pulsador_midpoint, portico_keypoint_d) if pulsador_midpoint and portico_keypoint_d else None,
            'calibration_factor': self.pixels_per_cm,
            'auto_calibrated': self.auto_calibrated,
            'reference_distance_cm': self.reference_distance_cm,
            'reference_distance_pixels': reference_distance_pixels,
            'movement_metrics': movement_metrics,
            'filter_statistics': filter_statistics
        }
        
    def disconnect_mqtt(self):
        """
        Desconecta la comunicación directa.
        """
        self.dicapua_publisher = None
        self.mqtt_connected = False
        print("🔌 Comunicación directa desconectada del calculador de distancias")
            
    def set_mqtt_enabled(self, enabled: bool, dicapua_publisher=None):
        """
        Habilita o deshabilita la comunicación directa.
        
        Args:
            enabled: True para habilitar, False para deshabilitar
            dicapua_publisher: Instancia de DicapuaPublisher para comunicación directa
        """
        if enabled and not self.enable_mqtt:
            if dicapua_publisher:
                self.dicapua_publisher = dicapua_publisher
            
            # Intentar habilitar comunicación directa
            self.enable_mqtt = True
            self._connect_local_mqtt()
            
            if self.mqtt_connected:
                print("✅ Comunicación directa habilitada")
            else:
                print("❌ No se pudo habilitar comunicación directa")
                self.enable_mqtt = False
        elif not enabled and self.enable_mqtt:
            # Deshabilitar
            self.disconnect_mqtt()
            self.enable_mqtt = False
            print("⏹️ Comunicación directa deshabilitada")
            
    def set_dicapua_publisher(self, dicapua_publisher):
        """
        Establece la instancia de DicapuaPublisher para comunicación directa.
        
        Args:
            dicapua_publisher: Instancia de DicapuaPublisher
        """
        self.dicapua_publisher = dicapua_publisher
        if dicapua_publisher:
            self.mqtt_connected = True
            print("✅ DicapuaPublisher configurado para distance_calculator")
        else:
            self.mqtt_connected = False
            print("⚠️ DicapuaPublisher removido de distance_calculator")
            
    def get_mqtt_status(self) -> Dict[str, any]:
        """
        Obtiene el estado actual de la comunicación directa.
        
        Returns:
            Diccionario con información del estado de comunicación
        """
        return {
            'enabled': self.enable_mqtt,
            'connected': self.mqtt_connected,
            'last_distance_sent': self.last_distance_sent,
            'communication_type': 'direct',
            'dicapua_publisher_available': self.dicapua_publisher is not None
        }