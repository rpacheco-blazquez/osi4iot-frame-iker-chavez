"""Módulo de seguimiento de objetos detectados."""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import time

class ObjectTracker:
    """Tracker para seguimiento de objetos detectados."""
    
    def __init__(self, max_disappeared: int = 30, max_distance: float = 100.0):
        """Inicializa el tracker.
        
        Args:
            max_disappeared: Máximo número de frames que un objeto puede desaparecer
            max_distance: Distancia máxima para asociar detecciones con tracks existentes
        """
        self.next_object_id = 0
        self.objects = {}  # ID -> centroide
        self.disappeared = defaultdict(int)
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.tracks = {}  # ID -> historial de posiciones
        
    def register(self, centroid: Tuple[float, float]) -> int:
        """Registra un nuevo objeto.
        
        Args:
            centroid: Centroide del objeto (x, y)
            
        Returns:
            ID del nuevo objeto
        """
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.tracks[self.next_object_id] = [centroid]
        
        object_id = self.next_object_id
        self.next_object_id += 1
        return object_id
    
    def deregister(self, object_id: int):
        """Elimina un objeto del tracking.
        
        Args:
            object_id: ID del objeto a eliminar
        """
        del self.objects[object_id]
        del self.disappeared[object_id]
        if object_id in self.tracks:
            del self.tracks[object_id]
    
    def update(self, detections: List[Dict]) -> Dict[int, Dict]:
        """Actualiza el tracker con nuevas detecciones.
        
        Args:
            detections: Lista de detecciones con bounding boxes
            
        Returns:
            Diccionario con objetos trackeados {object_id: info}
        """
        # Si no hay detecciones, marcar todos los objetos como desaparecidos
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            
            return self._get_tracked_objects()
        
        # Calcular centroides de las detecciones
        input_centroids = []
        for detection in detections:
            bbox = detection['bbox']
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            input_centroids.append((cx, cy))
        
        # Si no hay objetos existentes, registrar todos como nuevos
        if len(self.objects) == 0:
            for centroid in input_centroids:
                self.register(centroid)
        else:
            # Asociar detecciones existentes con objetos trackeados
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())
            
            # Calcular matriz de distancias
            D = self._compute_distance_matrix(object_centroids, input_centroids)
            
            # Encontrar la asignación óptima
            rows, cols = self._hungarian_assignment(D)
            
            # Actualizar objetos existentes
            used_row_indices = set()
            used_col_indices = set()
            
            for (row, col) in zip(rows, cols):
                if D[row, col] > self.max_distance:
                    continue
                
                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.disappeared[object_id] = 0
                
                # Actualizar historial de tracking
                if object_id in self.tracks:
                    self.tracks[object_id].append(input_centroids[col])
                    # Mantener solo los últimos 50 puntos
                    if len(self.tracks[object_id]) > 50:
                        self.tracks[object_id] = self.tracks[object_id][-50:]
                
                used_row_indices.add(row)
                used_col_indices.add(col)
            
            # Manejar objetos no asignados
            unused_row_indices = set(range(0, D.shape[0])).difference(used_row_indices)
            unused_col_indices = set(range(0, D.shape[1])).difference(used_col_indices)
            
            # Si hay más objetos que detecciones, marcar como desaparecidos
            if D.shape[0] >= D.shape[1]:
                for row in unused_row_indices:
                    object_id = object_ids[row]
                    self.disappeared[object_id] += 1
                    
                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)
            
            # Si hay más detecciones que objetos, registrar nuevos objetos
            else:
                for col in unused_col_indices:
                    self.register(input_centroids[col])
        
        return self._get_tracked_objects()
    
    def _compute_distance_matrix(self, object_centroids: List[Tuple], 
                               input_centroids: List[Tuple]) -> np.ndarray:
        """Calcula la matriz de distancias entre centroides."""
        D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - 
                          np.array(input_centroids), axis=2)
        return D
    
    def _hungarian_assignment(self, cost_matrix: np.ndarray) -> Tuple[List, List]:
        """Implementación simple del algoritmo húngaro para asignación."""
        # Implementación simplificada - en producción usar scipy.optimize.linear_sum_assignment
        rows, cols = [], []
        
        for i in range(min(cost_matrix.shape)):
            min_idx = np.unravel_index(np.argmin(cost_matrix), cost_matrix.shape)
            rows.append(min_idx[0])
            cols.append(min_idx[1])
            
            # Marcar fila y columna como usadas
            cost_matrix[min_idx[0], :] = np.inf
            cost_matrix[:, min_idx[1]] = np.inf
        
        return rows, cols
    
    def _get_tracked_objects(self) -> Dict[int, Dict]:
        """Obtiene información de objetos trackeados."""
        tracked_objects = {}
        
        for object_id, centroid in self.objects.items():
            tracked_objects[object_id] = {
                'centroid': centroid,
                'track': self.tracks.get(object_id, []),
                'disappeared_frames': self.disappeared[object_id]
            }
        
        return tracked_objects
    
    def get_velocity(self, object_id: int, fps: float = 30.0) -> Optional[Tuple[float, float]]:
        """Calcula la velocidad de un objeto.
        
        Args:
            object_id: ID del objeto
            fps: Frames por segundo del video
            
        Returns:
            Velocidad (vx, vy) en píxeles por segundo, o None si no hay suficientes datos
        """
        if object_id not in self.tracks or len(self.tracks[object_id]) < 2:
            return None
        
        track = self.tracks[object_id]
        
        # Calcular velocidad usando los últimos dos puntos
        p1 = np.array(track[-2])
        p2 = np.array(track[-1])
        
        velocity = (p2 - p1) * fps
        return tuple(velocity)
    
    def draw_tracks(self, frame: np.ndarray, tracked_objects: Dict[int, Dict]) -> np.ndarray:
        """Dibuja las trayectorias de los objetos trackeados.
        
        Args:
            frame: Frame original
            tracked_objects: Objetos trackeados
            
        Returns:
            Frame con las trayectorias dibujadas
        """
        result_frame = frame.copy()
        
        for object_id, obj_info in tracked_objects.items():
            track = obj_info['track']
            centroid = obj_info['centroid']
            
            # Dibujar trayectoria
            if len(track) > 1:
                points = np.array(track, dtype=np.int32)
                cv2.polylines(result_frame, [points], False, (0, 255, 255), 2)
            
            # Dibujar centroide actual
            cv2.circle(result_frame, (int(centroid[0]), int(centroid[1])), 
                      5, (0, 0, 255), -1)
            
            # Dibujar ID del objeto
            cv2.putText(result_frame, f"ID: {object_id}", 
                       (int(centroid[0]) - 10, int(centroid[1]) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return result_frame

class KalmanTracker:
    """Tracker usando filtro de Kalman para predicción de movimiento."""
    
    def __init__(self):
        """Inicializa el filtro de Kalman."""
        self.kalman = cv2.KalmanFilter(4, 2)
        self.kalman.measurementMatrix = np.array([[1, 0, 0, 0],
                                                 [0, 1, 0, 0]], np.float32)
        self.kalman.transitionMatrix = np.array([[1, 0, 1, 0],
                                               [0, 1, 0, 1],
                                               [0, 0, 1, 0],
                                               [0, 0, 0, 1]], np.float32)
        self.kalman.processNoiseCov = 0.03 * np.eye(4, dtype=np.float32)
        self.kalman.measurementNoiseCov = 0.1 * np.eye(2, dtype=np.float32)
        
    def predict(self) -> Tuple[float, float]:
        """Predice la siguiente posición.
        
        Returns:
            Posición predicha (x, y)
        """
        prediction = self.kalman.predict()
        return (float(prediction[0]), float(prediction[1]))
    
    def update(self, measurement: Tuple[float, float]):
        """Actualiza el filtro con una nueva medición.
        
        Args:
            measurement: Posición medida (x, y)
        """
        measurement_array = np.array([[measurement[0]], [measurement[1]]], dtype=np.float32)
        self.kalman.correct(measurement_array)
    
    def initialize(self, initial_position: Tuple[float, float]):
        """Inicializa el filtro con una posición inicial.
        
        Args:
            initial_position: Posición inicial (x, y)
        """
        self.kalman.statePre = np.array([initial_position[0], initial_position[1], 0, 0], 
                                       dtype=np.float32)
        self.kalman.statePost = np.array([initial_position[0], initial_position[1], 0, 0], 
                                        dtype=np.float32)