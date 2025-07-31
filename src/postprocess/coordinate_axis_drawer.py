"""Dibujador de ejes de coordenadas para visualización en detecciones.

Este módulo añade un sistema de coordenadas visual en una esquina de la imagen
mostrando los ejes X (positivo hacia la derecha) y Z (positivo hacia abajo).
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional

class CoordinateAxisDrawer:
    """
    Dibujador de ejes de coordenadas para visualización en frames de detección.
    Añade un pequeño sistema de coordenadas en una esquina de la imagen.
    """
    
    def __init__(self, position: str = "bottom_right", size: int = 60, margin: int = 20):
        """
        Inicializa el dibujador de ejes de coordenadas.
        
        Args:
            position: Posición del sistema de coordenadas ("top_left", "top_right", "bottom_left", "bottom_right")
            size: Tamaño de los ejes en píxeles
            margin: Margen desde el borde de la imagen en píxeles
        """
        self.position = position
        self.size = size
        self.margin = margin
        
        # Colores para los ejes
        self.x_color = (0, 0, 255)    # Rojo para eje X
        self.z_color = (0, 255, 0)    # Verde para eje Z
        self.origin_color = (255, 255, 255)  # Blanco para el origen
        
        # Grosor de las líneas
        self.line_thickness = 2
        self.text_thickness = 1
        
    def _calculate_origin_position(self, frame_shape: Tuple[int, int]) -> Tuple[int, int]:
        """
        Calcula la posición del origen del sistema de coordenadas.
        
        Args:
            frame_shape: Forma del frame (height, width)
            
        Returns:
            Coordenadas (x, y) del origen
        """
        height, width = frame_shape[:2]
        
        if self.position == "top_left":
            origin_x = self.margin + self.size // 2
            origin_y = self.margin + self.size // 2
        elif self.position == "top_right":
            origin_x = width - self.margin - self.size // 2
            origin_y = self.margin + self.size // 2
        elif self.position == "bottom_left":
            origin_x = self.margin + self.size // 2
            origin_y = height - self.margin - self.size // 2
        else:  # bottom_right (default)
            origin_x = width - self.margin - self.size // 2
            origin_y = height - self.margin - self.size // 2
            
        return (origin_x, origin_y)
    
    def _draw_axis_arrow(self, frame: np.ndarray, start: Tuple[int, int], 
                        end: Tuple[int, int], color: Tuple[int, int, int]) -> None:
        """
        Dibuja una flecha para representar un eje.
        
        Args:
            frame: Frame donde dibujar
            start: Punto de inicio de la flecha
            end: Punto final de la flecha
            color: Color de la flecha (B, G, R)
        """
        # Dibujar línea principal
        cv2.line(frame, start, end, color, self.line_thickness)
        
        # Calcular puntas de la flecha
        arrow_length = 8
        angle = np.arctan2(end[1] - start[1], end[0] - start[0])
        
        # Puntas de la flecha
        arrow_angle = np.pi / 6  # 30 grados
        
        # Primera punta
        x1 = int(end[0] - arrow_length * np.cos(angle - arrow_angle))
        y1 = int(end[1] - arrow_length * np.sin(angle - arrow_angle))
        cv2.line(frame, end, (x1, y1), color, self.line_thickness)
        
        # Segunda punta
        x2 = int(end[0] - arrow_length * np.cos(angle + arrow_angle))
        y2 = int(end[1] - arrow_length * np.sin(angle + arrow_angle))
        cv2.line(frame, end, (x2, y2), color, self.line_thickness)
    
    def draw_coordinate_system(self, frame: np.ndarray) -> np.ndarray:
        """
        Dibuja el sistema de coordenadas en el frame.
        
        Args:
            frame: Frame de video donde dibujar el sistema de coordenadas
            
        Returns:
            Frame con el sistema de coordenadas dibujado
        """
        frame_copy = frame.copy()
        
        # Calcular posición del origen
        origin_x, origin_y = self._calculate_origin_position(frame_copy.shape)
        
        # Calcular puntos finales de los ejes
        axis_length = self.size // 2
        
        # Eje X (positivo hacia la derecha)
        x_end = (origin_x + axis_length, origin_y)
        
        # Eje Z (positivo hacia abajo)
        z_end = (origin_x, origin_y + axis_length)
        
        # Dibujar origen
        cv2.circle(frame_copy, (origin_x, origin_y), 3, self.origin_color, -1)
        
        # Dibujar ejes con flechas
        self._draw_axis_arrow(frame_copy, (origin_x, origin_y), x_end, self.x_color)
        self._draw_axis_arrow(frame_copy, (origin_x, origin_y), z_end, self.z_color)
        
        # Añadir etiquetas de los ejes
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        
        # Etiqueta X
        x_label_pos = (x_end[0] + 5, x_end[1] + 5)
        cv2.putText(frame_copy, "X+", x_label_pos, font, font_scale, self.x_color, self.text_thickness)
        
        # Etiqueta Z
        z_label_pos = (z_end[0] - 15, z_end[1] + 15)
        cv2.putText(frame_copy, "Z+", z_label_pos, font, font_scale, self.z_color, self.text_thickness)
        
        # Añadir fondo semitransparente para mejor visibilidad
        overlay = frame_copy.copy()
        
        # Calcular área del sistema de coordenadas
        if self.position == "top_left":
            rect_start = (self.margin, self.margin)
            rect_end = (self.margin + self.size + 20, self.margin + self.size + 20)
        elif self.position == "top_right":
            rect_start = (frame_copy.shape[1] - self.margin - self.size - 20, self.margin)
            rect_end = (frame_copy.shape[1] - self.margin, self.margin + self.size + 20)
        elif self.position == "bottom_left":
            rect_start = (self.margin, frame_copy.shape[0] - self.margin - self.size - 20)
            rect_end = (self.margin + self.size + 20, frame_copy.shape[0] - self.margin)
        else:  # bottom_right
            rect_start = (frame_copy.shape[1] - self.margin - self.size - 20, 
                         frame_copy.shape[0] - self.margin - self.size - 20)
            rect_end = (frame_copy.shape[1] - self.margin, frame_copy.shape[0] - self.margin)
        
        # Dibujar rectángulo semitransparente
        cv2.rectangle(overlay, rect_start, rect_end, (0, 0, 0), -1)
        alpha = 0.3  # Transparencia
        cv2.addWeighted(overlay, alpha, frame_copy, 1 - alpha, 0, frame_copy)
        
        # Redibujar ejes y etiquetas sobre el fondo
        cv2.circle(frame_copy, (origin_x, origin_y), 3, self.origin_color, -1)
        self._draw_axis_arrow(frame_copy, (origin_x, origin_y), x_end, self.x_color)
        self._draw_axis_arrow(frame_copy, (origin_x, origin_y), z_end, self.z_color)
        cv2.putText(frame_copy, "X+", x_label_pos, font, font_scale, self.x_color, self.text_thickness)
        cv2.putText(frame_copy, "Z+", z_label_pos, font, font_scale, self.z_color, self.text_thickness)
        
        return frame_copy
    
    def process_frame_with_coordinates(self, frame: np.ndarray, detections: List[Dict] = None) -> np.ndarray:
        """
        Procesa un frame añadiendo el sistema de coordenadas.
        
        Args:
            frame: Frame de video a procesar
            detections: Lista de detecciones (opcional, para compatibilidad)
            
        Returns:
            Frame procesado con el sistema de coordenadas
        """
        return self.draw_coordinate_system(frame)
    
    def set_position(self, position: str) -> None:
        """
        Cambia la posición del sistema de coordenadas.
        
        Args:
            position: Nueva posición ("top_left", "top_right", "bottom_left", "bottom_right")
        """
        valid_positions = ["top_left", "top_right", "bottom_left", "bottom_right"]
        if position in valid_positions:
            self.position = position
        else:
            raise ValueError(f"Posición inválida. Debe ser una de: {valid_positions}")
    
    def set_size(self, size: int) -> None:
        """
        Cambia el tamaño del sistema de coordenadas.
        
        Args:
            size: Nuevo tamaño en píxeles
        """
        if size > 0:
            self.size = size
        else:
            raise ValueError("El tamaño debe ser mayor que 0")
    
    def set_colors(self, x_color: Tuple[int, int, int] = None, 
                   z_color: Tuple[int, int, int] = None,
                   origin_color: Tuple[int, int, int] = None) -> None:
        """
        Cambia los colores del sistema de coordenadas.
        
        Args:
            x_color: Color del eje X en formato (B, G, R)
            z_color: Color del eje Z en formato (B, G, R)
            origin_color: Color del origen en formato (B, G, R)
        """
        if x_color is not None:
            self.x_color = x_color
        if z_color is not None:
            self.z_color = z_color
        if origin_color is not None:
            self.origin_color = origin_color


# Función de conveniencia para uso directo
def add_coordinate_system_to_frame(frame: np.ndarray, 
                                  position: str = "bottom_right",
                                  size: int = 60,
                                  margin: int = 20) -> np.ndarray:
    """
    Función de conveniencia para añadir un sistema de coordenadas a un frame.
    
    Args:
        frame: Frame de video
        position: Posición del sistema de coordenadas
        size: Tamaño de los ejes
        margin: Margen desde el borde
        
    Returns:
        Frame con el sistema de coordenadas añadido
    """
    drawer = CoordinateAxisDrawer(position, size, margin)
    return drawer.draw_coordinate_system(frame)