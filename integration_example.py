#!/usr/bin/env python3
"""Ejemplo de integración del sistema de coordenadas con la aplicación principal.

Este archivo muestra cómo integrar el CoordinateAxisDrawer con el sistema
existente de detección y post-procesamiento.
"""

import sys
from pathlib import Path

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent / "src"))

from postprocess.coordinate_axis_drawer import CoordinateAxisDrawer

def integrate_coordinate_system_example():
    """Ejemplo de cómo integrar el sistema de coordenadas en el flujo existente."""
    
    # En tu clase principal (por ejemplo, InteractiveDetectionInterface)
    # Añadir en el método __init__:
    
    # self.coordinate_drawer = CoordinateAxisDrawer(
    #     position="bottom_right",  # Posición por defecto
    #     size=60,                  # Tamaño del sistema de coordenadas
    #     margin=20,                # Margen desde el borde
    #     x_color=(0, 0, 255),      # Color del eje X (rojo)
    #     z_color=(0, 255, 0),      # Color del eje Z (verde)
    #     origin_color=(255, 255, 255),  # Color del origen (blanco)
    #     line_thickness=2,         # Grosor de las líneas
    #     text_scale=0.5,          # Escala del texto
    #     text_thickness=1         # Grosor del texto
    # )
    
    pass

def process_frame_with_coordinates_example(frame, detections=None):
    """Ejemplo de cómo procesar un frame añadiendo el sistema de coordenadas.
    
    Args:
        frame: Frame de video (numpy array)
        detections: Lista de detecciones (opcional)
        
    Returns:
        Frame procesado con sistema de coordenadas
    """
    
    # Crear el dibujador de coordenadas
    coord_drawer = CoordinateAxisDrawer()
    
    # Procesar el frame con detecciones existentes
    # (aquí irían tus procesamientos actuales: distancias, marcadores, etc.)
    processed_frame = frame.copy()
    
    # Añadir el sistema de coordenadas
    final_frame = coord_drawer.draw_coordinate_system(processed_frame)
    
    return final_frame

def add_coordinate_controls_to_gui_example():
    """Ejemplo de cómo añadir controles del sistema de coordenadas a la GUI."""
    
    # En tu interfaz gráfica, puedes añadir:
    
    # 1. Checkbox para mostrar/ocultar coordenadas
    # self.show_coordinates_var = tk.BooleanVar(value=True)
    # self.show_coordinates_check = ttk.Checkbutton(
    #     parent_frame,
    #     text="Mostrar ejes de coordenadas",
    #     variable=self.show_coordinates_var,
    #     command=self.toggle_coordinate_display
    # )
    
    # 2. Combobox para seleccionar posición
    # self.coord_position_var = tk.StringVar(value="bottom_right")
    # self.coord_position_combo = ttk.Combobox(
    #     parent_frame,
    #     textvariable=self.coord_position_var,
    #     values=["bottom_right", "bottom_left", "top_right", "top_left"],
    #     state="readonly"
    # )
    # self.coord_position_combo.bind("<<ComboboxSelected>>", self.on_position_changed)
    
    # 3. Scale para ajustar tamaño
    # self.coord_size_var = tk.IntVar(value=60)
    # self.coord_size_scale = ttk.Scale(
    #     parent_frame,
    #     from_=30,
    #     to=120,
    #     variable=self.coord_size_var,
    #     orient="horizontal",
    #     command=self.on_size_changed
    # )
    
    pass

def callback_methods_example():
    """Ejemplo de métodos callback para los controles de la GUI."""
    
    # def toggle_coordinate_display(self):
    #     """Alternar la visualización del sistema de coordenadas."""
    #     self.coordinate_drawer.enabled = self.show_coordinates_var.get()
    
    # def on_position_changed(self, event=None):
    #     """Cambiar la posición del sistema de coordenadas."""
    #     new_position = self.coord_position_var.get()
    #     self.coordinate_drawer.set_position(new_position)
    
    # def on_size_changed(self, value):
    #     """Cambiar el tamaño del sistema de coordenadas."""
    #     new_size = int(float(value))
    #     self.coordinate_drawer.set_size(new_size)
    
    pass

def integration_in_video_processor_example():
    """Ejemplo de integración en el procesador de video."""
    
    # En tu método de procesamiento de video principal:
    
    # def process_video_frame(self, frame):
    #     """Procesar frame de video con todas las funcionalidades."""
    #     
    #     # 1. Realizar detecciones
    #     detections = self.detector.detect(frame)
    #     
    #     # 2. Dibujar detecciones básicas
    #     processed_frame = self.detector.draw_detections(frame, detections)
    #     
    #     # 3. Añadir cálculos de distancia
    #     if detections and self.show_distances:
    #         processed_frame = self.distance_calculator.draw_distance_on_frame(
    #             processed_frame, detections, 
    #             show_distance=True, show_line=True
    #         )
    #     
    #     # 4. Añadir marcadores de distancia
    #     if detections and self.show_markers:
    #         processed_frame = self.marker_calculator.draw_distance_on_frame(
    #             processed_frame, detections,
    #             show_distance=True, show_line=True
    #         )
    #     
    #     # 5. Añadir sistema de coordenadas (NUEVO)
    #     if self.show_coordinates_var.get():
    #         processed_frame = self.coordinate_drawer.draw_coordinate_system(processed_frame)
    #     
    #     return processed_frame
    
    pass

def configuration_example():
    """Ejemplo de configuración del sistema de coordenadas."""
    
    # Configuración básica
    basic_config = {
        "position": "bottom_right",
        "size": 60,
        "margin": 20
    }
    
    # Configuración avanzada con colores personalizados
    advanced_config = {
        "position": "top_left",
        "size": 80,
        "margin": 30,
        "x_color": (0, 0, 255),      # Rojo para X
        "z_color": (0, 255, 0),      # Verde para Z
        "origin_color": (255, 255, 255),  # Blanco para origen
        "line_thickness": 3,
        "text_scale": 0.6,
        "text_thickness": 2
    }
    
    # Crear dibujador con configuración
    # coord_drawer = CoordinateAxisDrawer(**advanced_config)
    
    return basic_config, advanced_config

if __name__ == "__main__":
    print("📋 Ejemplo de Integración del Sistema de Coordenadas")
    print("="*50)
    print()
    print("Este archivo contiene ejemplos de cómo integrar el")
    print("CoordinateAxisDrawer en tu aplicación existente.")
    print()
    print("Funcionalidades incluidas:")
    print("✅ Integración en el flujo de procesamiento")
    print("✅ Controles de GUI para configuración")
    print("✅ Métodos callback para interactividad")
    print("✅ Configuración personalizable")
    print()
    print("Para usar en tu aplicación:")
    print("1. Importa CoordinateAxisDrawer")
    print("2. Crea una instancia en tu clase principal")
    print("3. Llama a draw_coordinate_system() en tu flujo de video")
    print("4. Añade controles opcionales a tu GUI")
    print()
    
    # Mostrar configuraciones de ejemplo
    basic, advanced = configuration_example()
    print("Configuración básica:")
    for key, value in basic.items():
        print(f"  {key}: {value}")
    print()
    print("Configuración avanzada:")
    for key, value in advanced.items():
        print(f"  {key}: {value}")