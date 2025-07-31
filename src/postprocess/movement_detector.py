import numpy as np
import time
import json
import os
from typing import List, Dict, Tuple, Optional, Deque, Any
from collections import deque
import math
import logging

class MovementDetector:
    """
    Detector de movimiento inteligente para evitar envío de datos MQTT
    cuando el pulsador no se mueve realmente.
    """
    
    def __init__(self, 
                 distance_threshold_cm: float = 0.5,
                 velocity_threshold_cm_s: float = 0.2,
                 position_stability_frames: int = 5,
                 temporal_window_seconds: float = 2.0,
                 config_file: Optional[str] = None):
        """
        Inicializa el detector de movimiento.
        
        Args:
            distance_threshold_cm: Umbral mínimo de cambio de distancia para considerar movimiento
            velocity_threshold_cm_s: Velocidad mínima en cm/s para considerar movimiento real
            position_stability_frames: Número de frames para considerar posición estable
            temporal_window_seconds: Ventana temporal para análisis de movimiento
            config_file: Ruta al archivo de configuración JSON
        """
        # Cargar configuración desde archivo si se proporciona
        if config_file and os.path.exists(config_file):
            self._load_config(config_file)
        else:
            # Usar valores por defecto
            self.distance_threshold_cm = distance_threshold_cm
            self.velocity_threshold_cm_s = velocity_threshold_cm_s
            self.position_stability_frames = position_stability_frames
            self.temporal_window_seconds = temporal_window_seconds
            self.position_noise_threshold = 2.0
            self.distance_noise_threshold = 0.3
            self.min_time_between_sends_ms = 500
            
            # Filtros habilitados
            self.enable_movement_detection = True
            self.enable_velocity_filter = True
            self.enable_stability_filter = True
            self.enable_relative_movement_filter = True
            self.enable_temporal_filter = True
            
            # Debug
            self.log_movement_metrics = True
            self.log_filtered_attempts = False
        
        # Inicializar estructuras de datos
        self._init_data_structures()
    
    def _load_config(self, config_file: str) -> None:
        """
        Carga la configuración desde un archivo JSON.
        
        Args:
            config_file: Ruta al archivo de configuración
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Configuración de detección de movimiento
            movement_config = config.get('movement_detection', {})
            self.distance_threshold_cm = movement_config.get('distance_threshold_cm', 0.5)
            self.velocity_threshold_cm_s = movement_config.get('velocity_threshold_cm_s', 0.2)
            self.position_stability_frames = movement_config.get('position_stability_frames', 5)
            self.temporal_window_seconds = movement_config.get('temporal_window_seconds', 2.0)
            self.position_noise_threshold = movement_config.get('position_noise_threshold_px', 2.0)
            self.distance_noise_threshold = movement_config.get('distance_noise_threshold_cm', 0.3)
            self.min_time_between_sends_ms = movement_config.get('min_time_between_sends_ms', 500)
            
            # Configuración de filtros MQTT
            mqtt_config = config.get('mqtt_filtering', {})
            self.enable_movement_detection = mqtt_config.get('enable_movement_detection', True)
            self.enable_velocity_filter = mqtt_config.get('enable_velocity_filter', True)
            self.enable_stability_filter = mqtt_config.get('enable_stability_filter', True)
            self.enable_relative_movement_filter = mqtt_config.get('enable_relative_movement_filter', True)
            self.enable_temporal_filter = mqtt_config.get('enable_temporal_filter', True)
            
            # Configuración de debug
            debug_config = config.get('debug', {})
            self.log_movement_metrics = debug_config.get('log_movement_metrics', True)
            self.log_filtered_attempts = debug_config.get('log_filtered_attempts', False)
            
            logging.info(f"Configuración de MovementDetector cargada desde {config_file}")
            
        except Exception as e:
            logging.error(f"Error cargando configuración de MovementDetector: {e}")
            # Usar valores por defecto en caso de error
            self.distance_threshold_cm = 0.5
            self.velocity_threshold_cm_s = 0.2
            self.position_stability_frames = 5
            self.temporal_window_seconds = 2.0
            self.position_noise_threshold = 2.0
            self.distance_noise_threshold = 0.3
            self.min_time_between_sends_ms = 500
            
            # Filtros habilitados
            self.enable_movement_detection = True
            self.enable_velocity_filter = True
            self.enable_stability_filter = True
            self.enable_relative_movement_filter = True
            self.enable_temporal_filter = True
            
            # Debug
            self.log_movement_metrics = True
            self.log_filtered_attempts = False
        
        # Inicializar estructuras de datos siempre
        self._init_data_structures()
    
    def _init_data_structures(self) -> None:
        """
        Inicializa las estructuras de datos del detector.
        """
        # Historial de posiciones y distancias
        max_len = max(20, self.position_stability_frames * 2)
        self.pulsador_positions: Deque[Tuple[float, float, float]] = deque(maxlen=max_len)
        self.portico_positions: Deque[Tuple[float, float, float]] = deque(maxlen=max_len)
        self.distance_history: Deque[Tuple[float, float]] = deque(maxlen=max_len)
        
        # Estado del movimiento
        self.last_movement_time = 0
        self.stable_position_count = 0
        self.last_sent_distance = None
        self.movement_detected = False
        
        # Contadores para estadísticas
        self.total_distance_calculations = 0
        self.filtered_by_distance_threshold = 0
        self.filtered_by_velocity = 0
        self.filtered_by_stability = 0
        self.filtered_by_relative_movement = 0
        self.filtered_by_temporal = 0
        self.sent_distances = 0
        
    def update_positions(self, 
                        pulsador_pos: Optional[Tuple[float, float]], 
                        portico_pos: Optional[Tuple[float, float]],
                        distance_cm: Optional[float]) -> None:
        """
        Actualiza las posiciones del pulsador y pórtico.
        
        Args:
            pulsador_pos: Posición del pulsador (x, y)
            portico_pos: Posición del pórtico (x, y)
            distance_cm: Distancia calculada en centímetros
        """
        current_time = time.time()
        
        if pulsador_pos:
            self.pulsador_positions.append((pulsador_pos[0], pulsador_pos[1], current_time))
        
        if portico_pos:
            self.portico_positions.append((portico_pos[0], portico_pos[1], current_time))
        
        if distance_cm is not None:
            self.distance_history.append((distance_cm, current_time))
    
    def calculate_velocity(self, positions: Deque[Tuple[float, float, float]]) -> float:
        """
        Calcula la velocidad promedio de movimiento en píxeles por segundo.
        
        Args:
            positions: Deque de posiciones (x, y, timestamp)
            
        Returns:
            Velocidad en píxeles por segundo
        """
        if len(positions) < 2:
            return 0.0
        
        # Filtrar posiciones dentro de la ventana temporal
        current_time = time.time()
        recent_positions = [
            pos for pos in positions 
            if current_time - pos[2] <= self.temporal_window_seconds
        ]
        
        if len(recent_positions) < 2:
            return 0.0
        
        # Calcular velocidades entre puntos consecutivos
        velocities = []
        for i in range(1, len(recent_positions)):
            pos1 = recent_positions[i-1]
            pos2 = recent_positions[i]
            
            # Distancia euclidiana
            distance = math.sqrt((pos2[0] - pos1[0])**2 + (pos2[1] - pos1[1])**2)
            time_diff = pos2[2] - pos1[2]
            
            if time_diff > 0:
                velocity = distance / time_diff
                velocities.append(velocity)
        
        return np.mean(velocities) if velocities else 0.0
    
    def calculate_distance_velocity(self) -> float:
        """
        Calcula la velocidad de cambio de distancia en cm/s.
        
        Returns:
            Velocidad de cambio de distancia en cm/s
        """
        if len(self.distance_history) < 2:
            return 0.0
        
        current_time = time.time()
        recent_distances = [
            dist for dist in self.distance_history 
            if current_time - dist[1] <= self.temporal_window_seconds
        ]
        
        if len(recent_distances) < 2:
            return 0.0
        
        # Calcular velocidades de cambio de distancia
        velocities = []
        for i in range(1, len(recent_distances)):
            dist1 = recent_distances[i-1]
            dist2 = recent_distances[i]
            
            distance_change = abs(dist2[0] - dist1[0])
            time_diff = dist2[1] - dist1[1]
            
            if time_diff > 0:
                velocity = distance_change / time_diff
                velocities.append(velocity)
        
        return np.mean(velocities) if velocities else 0.0
    
    def is_position_stable(self, positions: Deque[Tuple[float, float, float]]) -> bool:
        """
        Verifica si la posición es estable (sin movimiento significativo).
        
        Args:
            positions: Deque de posiciones
            
        Returns:
            True si la posición es estable
        """
        if len(positions) < self.position_stability_frames:
            return False
        
        # Tomar las últimas posiciones
        recent_positions = list(positions)[-self.position_stability_frames:]
        
        # Calcular varianza de posiciones
        x_coords = [pos[0] for pos in recent_positions]
        y_coords = [pos[1] for pos in recent_positions]
        
        x_variance = np.var(x_coords)
        y_variance = np.var(y_coords)
        
        # Considerar estable si la varianza es baja
        return (x_variance < self.position_noise_threshold**2 and 
                y_variance < self.position_noise_threshold**2)
    
    def detect_relative_movement(self) -> bool:
        """
        Detecta movimiento relativo entre pulsador y pórtico.
        
        Returns:
            True si hay movimiento relativo significativo
        """
        pulsador_velocity = self.calculate_velocity(self.pulsador_positions)
        portico_velocity = self.calculate_velocity(self.portico_positions)
        
        # Movimiento relativo = diferencia de velocidades
        relative_velocity = abs(pulsador_velocity - portico_velocity)
        
        # Convertir umbral de cm/s a px/s (asumiendo ~8 px/cm como en el calculador)
        velocity_threshold_px_s = self.velocity_threshold_cm_s * 8.0
        
        return relative_velocity > velocity_threshold_px_s
    
    def should_send_distance(self, current_distance: float) -> bool:
        """
        Determina si se debe enviar la distancia actual por MQTT.
        
        Args:
            current_distance: Distancia actual en centímetros
            
        Returns:
            True si se debe enviar la distancia
        """
        self.total_distance_calculations += 1
        current_time = time.time()
        
        if not self.enable_movement_detection:
            # Si la detección de movimiento está deshabilitada, enviar siempre
            self.last_movement_time = current_time
            self.last_sent_distance = current_distance
            self.sent_distances += 1
            return True
        
        # 1. Verificar umbral de cambio de distancia
        if (self.last_sent_distance is not None and 
            abs(current_distance - self.last_sent_distance) < self.distance_threshold_cm):
            self.filtered_by_distance_threshold += 1
            if self.log_filtered_attempts:
                logging.debug(f"Filtrado por umbral de distancia: {abs(current_distance - self.last_sent_distance):.2f} < {self.distance_threshold_cm}")
            return False
        
        # 2. Verificar velocidad de cambio de distancia
        if self.enable_velocity_filter:
            distance_velocity = self.calculate_distance_velocity()
            if distance_velocity < self.velocity_threshold_cm_s:
                self.filtered_by_velocity += 1
                if self.log_filtered_attempts:
                    logging.debug(f"Filtrado por velocidad: {distance_velocity:.2f} < {self.velocity_threshold_cm_s}")
                return False
        
        # 3. Verificar estabilidad de posiciones
        if self.enable_stability_filter:
            pulsador_stable = self.is_position_stable(self.pulsador_positions)
            portico_stable = self.is_position_stable(self.portico_positions)
            
            if pulsador_stable and portico_stable:
                self.stable_position_count += 1
                self.filtered_by_stability += 1
                if self.log_filtered_attempts:
                    logging.debug(f"Filtrado por estabilidad: pulsador={pulsador_stable}, portico={portico_stable}")
                return False
            else:
                self.stable_position_count = 0
        
        # 4. Verificar movimiento relativo
        if self.enable_relative_movement_filter:
            if not self.detect_relative_movement():
                self.filtered_by_relative_movement += 1
                if self.log_filtered_attempts:
                    logging.debug("Filtrado por falta de movimiento relativo")
                return False
        
        # 5. Filtro de ruido temporal
        if self.enable_temporal_filter:
            min_time_seconds = self.min_time_between_sends_ms / 1000.0
            if current_time - self.last_movement_time < min_time_seconds:
                self.filtered_by_temporal += 1
                if self.log_filtered_attempts:
                    logging.debug(f"Filtrado por tiempo: {(current_time - self.last_movement_time)*1000:.0f}ms < {self.min_time_between_sends_ms}ms")
                return False
        
        # Todas las verificaciones pasaron, enviar distancia
        self.last_movement_time = current_time
        self.last_sent_distance = current_distance
        self.movement_detected = True
        self.sent_distances += 1
        
        return True
    
    def get_movement_metrics(self) -> Dict[str, float]:
        """
        Obtiene métricas del movimiento para debugging.
        
        Returns:
            Diccionario con métricas de movimiento
        """
        pulsador_velocity = self.calculate_velocity(self.pulsador_positions)
        portico_velocity = self.calculate_velocity(self.portico_positions)
        distance_velocity = self.calculate_distance_velocity()
        relative_velocity = abs(pulsador_velocity - portico_velocity)
        
        pulsador_stable = self.is_position_stable(self.pulsador_positions)
        portico_stable = self.is_position_stable(self.portico_positions)
        
        # Calcular estadísticas de filtrado
        filter_rate = (self.total_distance_calculations - self.sent_distances) / max(1, self.total_distance_calculations) * 100
        
        return {
            'pulsador_velocity_px_s': pulsador_velocity,
            'portico_velocity_px_s': portico_velocity,
            'relative_velocity_px_s': relative_velocity,
            'distance_velocity_cm_s': distance_velocity,
            'pulsador_stable': pulsador_stable,
            'portico_stable': portico_stable,
            'stable_position_count': self.stable_position_count,
            'movement_detected': self.movement_detected,
            'last_sent_distance': self.last_sent_distance,
            'total_calculations': self.total_distance_calculations,
            'sent_distances': self.sent_distances,
            'filter_rate_percent': filter_rate,
            'filtered_by_distance_threshold': self.filtered_by_distance_threshold,
            'filtered_by_velocity': self.filtered_by_velocity,
            'filtered_by_stability': self.filtered_by_stability,
            'filtered_by_relative_movement': self.filtered_by_relative_movement,
            'filtered_by_temporal': self.filtered_by_temporal
        }
    
    def reset_movement_detection(self) -> None:
        """
        Reinicia el estado de detección de movimiento.
        """
        self.movement_detected = False
        self.stable_position_count = 0
        self.last_movement_time = 0
    
    def configure_thresholds(self, 
                           distance_threshold_cm: Optional[float] = None,
                           velocity_threshold_cm_s: Optional[float] = None,
                           position_stability_frames: Optional[int] = None) -> None:
        """
        Configura los umbrales de detección de movimiento.
        
        Args:
            distance_threshold_cm: Nuevo umbral de distancia
            velocity_threshold_cm_s: Nuevo umbral de velocidad
            position_stability_frames: Nuevo número de frames para estabilidad
        """
        if distance_threshold_cm is not None:
            self.distance_threshold_cm = distance_threshold_cm
        
        if velocity_threshold_cm_s is not None:
            self.velocity_threshold_cm_s = velocity_threshold_cm_s
        
        if position_stability_frames is not None:
            self.position_stability_frames = position_stability_frames
            # Actualizar maxlen de las deques
            max_len = max(20, position_stability_frames * 2)
            self.pulsador_positions = deque(self.pulsador_positions, maxlen=max_len)
            self.portico_positions = deque(self.portico_positions, maxlen=max_len)
    
    def enable_filter(self, filter_name: str, enabled: bool) -> None:
        """
        Habilita o deshabilita un filtro específico.
        
        Args:
            filter_name: Nombre del filtro ('velocity', 'stability', 'relative_movement', 'temporal', 'movement_detection')
            enabled: True para habilitar, False para deshabilitar
        """
        filter_map = {
            'velocity': 'enable_velocity_filter',
            'stability': 'enable_stability_filter',
            'relative_movement': 'enable_relative_movement_filter',
            'temporal': 'enable_temporal_filter',
            'movement_detection': 'enable_movement_detection'
        }
        
        if filter_name in filter_map:
            setattr(self, filter_map[filter_name], enabled)
            logging.info(f"Filtro '{filter_name}' {'habilitado' if enabled else 'deshabilitado'}")
        else:
            logging.warning(f"Filtro desconocido: {filter_name}")
    
    def get_filter_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas de filtrado.
        
        Returns:
            Diccionario con estadísticas de filtrado
        """
        total = max(1, self.total_distance_calculations)
        
        return {
            'total_calculations': self.total_distance_calculations,
            'sent_distances': self.sent_distances,
            'total_filtered': total - self.sent_distances,
            'filter_rate_percent': (total - self.sent_distances) / total * 100,
            'filters': {
                'distance_threshold': {
                    'count': self.filtered_by_distance_threshold,
                    'percentage': self.filtered_by_distance_threshold / total * 100
                },
                'velocity': {
                    'count': self.filtered_by_velocity,
                    'percentage': self.filtered_by_velocity / total * 100
                },
                'stability': {
                    'count': self.filtered_by_stability,
                    'percentage': self.filtered_by_stability / total * 100
                },
                'relative_movement': {
                    'count': self.filtered_by_relative_movement,
                    'percentage': self.filtered_by_relative_movement / total * 100
                },
                'temporal': {
                    'count': self.filtered_by_temporal,
                    'percentage': self.filtered_by_temporal / total * 100
                }
            },
            'filter_status': {
                'movement_detection': self.enable_movement_detection,
                'velocity_filter': self.enable_velocity_filter,
                'stability_filter': self.enable_stability_filter,
                'relative_movement_filter': self.enable_relative_movement_filter,
                'temporal_filter': self.enable_temporal_filter
            }
        }
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Actualiza la configuración de filtros de movimiento desde la interfaz.
        
        Args:
            config: Diccionario con la nueva configuración de filtros
        """
        try:
            # Actualizar filtros de distancia
            if 'distance_threshold' in config:
                dist_config = config['distance_threshold']
                if 'enabled' in dist_config:
                    self.enable_movement_detection = dist_config['enabled']
                if 'min_distance_cm' in dist_config:
                    self.distance_threshold_cm = dist_config['min_distance_cm']
            
            # Actualizar filtros de velocidad
            if 'velocity_threshold' in config:
                vel_config = config['velocity_threshold']
                if 'enabled' in vel_config:
                    self.enable_velocity_filter = vel_config['enabled']
                if 'min_velocity_cm_per_s' in vel_config:
                    self.velocity_threshold_cm_s = vel_config['min_velocity_cm_per_s']
            
            # Actualizar filtro de estabilidad
            if 'stability_threshold' in config:
                stab_config = config['stability_threshold']
                if 'enabled' in stab_config:
                    self.enable_stability_filter = stab_config['enabled']
            
            # Actualizar filtro de movimiento relativo
            if 'relative_movement' in config:
                rel_config = config['relative_movement']
                if 'enabled' in rel_config:
                    self.enable_relative_movement_filter = rel_config['enabled']
            
            # Actualizar filtro temporal
            if 'temporal_filter' in config:
                temp_config = config['temporal_filter']
                if 'enabled' in temp_config:
                    self.enable_temporal_filter = temp_config['enabled']
                if 'window_size' in temp_config:
                    # Convertir ventana de frames a segundos (asumiendo ~30 FPS)
                    self.temporal_window_seconds = temp_config['window_size'] / 30.0
                    # Actualizar también el tiempo mínimo entre envíos
                    self.min_time_between_sends_ms = (temp_config['window_size'] / 30.0) * 1000 / 2
            
            logging.info(f"Configuración de MovementDetector actualizada: {config}")
            
        except Exception as e:
            logging.error(f"Error actualizando configuración de MovementDetector: {e}")