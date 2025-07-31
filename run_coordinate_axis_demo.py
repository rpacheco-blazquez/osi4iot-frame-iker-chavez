#!/usr/bin/env python3
"""Script de demostración para el dibujador de ejes de coordenadas.

Este script muestra cómo usar el CoordinateAxisDrawer junto con las detecciones
existentes para añadir un sistema de coordenadas visual a los frames.
"""

import cv2
import numpy as np
import sys
from pathlib import Path

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent / "src"))

from vision.detector import YOLOPoseDetector
from postprocess.coordinate_axis_drawer import CoordinateAxisDrawer, add_coordinate_system_to_frame
from postprocess.distance_calculator import DistanceCalculator
from postprocess.marker_distance_calculator import MarkerDistanceCalculator
from utils.helpers import ConfigManager

def main():
    """Función principal del demo."""
    print("🎯 Demo del Sistema de Coordenadas")
    print("Controles:")
    print("  'q' - Salir")
    print("  '1' - Esquina inferior derecha (default)")
    print("  '2' - Esquina inferior izquierda")
    print("  '3' - Esquina superior derecha")
    print("  '4' - Esquina superior izquierda")
    print("  '+' - Aumentar tamaño")
    print("  '-' - Disminuir tamaño")
    print("  'c' - Cambiar colores")
    print("  's' - Guardar frame actual")
    print()
    
    # Configuración
    config_path = "config/config.yaml"
    
    try:
        # Inicializar componentes
        detector = YOLOPoseDetector(config_path)
        detector.load_model()
        
        distance_calculator = DistanceCalculator(pixels_per_cm=10.0)
        marker_calculator = MarkerDistanceCalculator(pixels_per_cm=10.0)
        
        # Inicializar dibujador de coordenadas
        coord_drawer = CoordinateAxisDrawer(
            position="bottom_right",
            size=80,
            margin=30
        )
        
        # Inicializar cámara
        cap = cv2.VideoCapture(0)  # Usar cámara por defecto
        
        if not cap.isOpened():
            print("❌ Error: No se pudo abrir la cámara")
            return
        
        print("✅ Cámara inicializada")
        print("✅ Detector YOLO cargado")
        print("✅ Sistema de coordenadas listo")
        print()
        
        # Variables para el demo
        color_mode = 0
        color_schemes = [
            {"x_color": (0, 0, 255), "z_color": (0, 255, 0), "origin_color": (255, 255, 255)},  # Rojo/Verde
            {"x_color": (255, 0, 0), "z_color": (0, 255, 255), "origin_color": (255, 255, 255)},  # Azul/Amarillo
            {"x_color": (255, 0, 255), "z_color": (0, 255, 255), "origin_color": (255, 255, 255)},  # Magenta/Cian
            {"x_color": (128, 0, 255), "z_color": (0, 255, 128), "origin_color": (255, 255, 255)}   # Púrpura/Verde lima
        ]
        
        frame_counter = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Error: No se pudo leer el frame")
                break
            
            frame_counter += 1
            
            try:
                # Realizar detecciones
                detections = detector.detect(frame)
                
                # Dibujar detecciones básicas
                processed_frame = detector.draw_detections(frame, detections)
                
                # Añadir cálculos de distancia si hay detecciones
                if detections:
                    # Distancia pulsador-pórtico
                    processed_frame = distance_calculator.draw_distance_on_frame(
                        processed_frame, detections, show_distance=True, show_line=True
                    )
                    
                    # Distancia del marcador
                    processed_frame = marker_calculator.draw_distance_on_frame(
                        processed_frame, detections, show_distance=True, show_line=True
                    )
                
                # Añadir sistema de coordenadas
                processed_frame = coord_drawer.draw_coordinate_system(processed_frame)
                
                # Añadir información del sistema
                info_text = f"Frame: {frame_counter} | Detecciones: {len(detections) if detections else 0}"
                cv2.putText(processed_frame, info_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Información del sistema de coordenadas
                coord_info = f"Posicion: {coord_drawer.position} | Tamaño: {coord_drawer.size}px"
                cv2.putText(processed_frame, coord_info, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                # Mostrar frame
                cv2.imshow("Demo Sistema de Coordenadas", processed_frame)
                
                # Manejar teclas
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('1'):
                    coord_drawer.set_position("bottom_right")
                    print("📍 Posición: Esquina inferior derecha")
                elif key == ord('2'):
                    coord_drawer.set_position("bottom_left")
                    print("📍 Posición: Esquina inferior izquierda")
                elif key == ord('3'):
                    coord_drawer.set_position("top_right")
                    print("📍 Posición: Esquina superior derecha")
                elif key == ord('4'):
                    coord_drawer.set_position("top_left")
                    print("📍 Posición: Esquina superior izquierda")
                elif key == ord('+') or key == ord('='):
                    new_size = min(coord_drawer.size + 10, 150)
                    coord_drawer.set_size(new_size)
                    print(f"📏 Tamaño aumentado: {new_size}px")
                elif key == ord('-'):
                    new_size = max(coord_drawer.size - 10, 30)
                    coord_drawer.set_size(new_size)
                    print(f"📏 Tamaño reducido: {new_size}px")
                elif key == ord('c'):
                    color_mode = (color_mode + 1) % len(color_schemes)
                    coord_drawer.set_colors(**color_schemes[color_mode])
                    print(f"🎨 Esquema de colores cambiado: {color_mode + 1}")
                elif key == ord('s'):
                    filename = f"coordinate_demo_frame_{frame_counter}.jpg"
                    cv2.imwrite(filename, processed_frame)
                    print(f"💾 Frame guardado: {filename}")
                
            except Exception as e:
                print(f"⚠️ Error procesando frame: {e}")
                continue
        
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Limpiar recursos
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        print("🧹 Recursos liberados")

def demo_static_image():
    """Demo con imagen estática para pruebas."""
    print("🖼️ Demo con imagen estática")
    
    # Crear una imagen de prueba
    height, width = 480, 640
    test_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Añadir algunos elementos de prueba
    cv2.rectangle(test_image, (50, 50), (200, 150), (100, 100, 100), -1)
    cv2.circle(test_image, (320, 240), 50, (150, 150, 150), -1)
    cv2.putText(test_image, "Imagen de Prueba", (220, 400),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Probar diferentes posiciones
    positions = ["bottom_right", "bottom_left", "top_right", "top_left"]
    
    for i, position in enumerate(positions):
        # Crear imagen con sistema de coordenadas
        result = add_coordinate_system_to_frame(
            test_image.copy(), 
            position=position, 
            size=60, 
            margin=20
        )
        
        # Añadir título
        title = f"Posicion: {position}"
        cv2.putText(result, title, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Mostrar y guardar
        cv2.imshow(f"Demo Estático - {position}", result)
        cv2.imwrite(f"demo_static_{position}.jpg", result)
        
        print(f"✅ Imagen guardada: demo_static_{position}.jpg")
        
        # Esperar tecla para continuar
        cv2.waitKey(2000)  # 2 segundos
    
    cv2.destroyAllWindows()
    print("🎯 Demo estático completado")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo del Sistema de Coordenadas")
    parser.add_argument("--static", action="store_true", 
                       help="Ejecutar demo con imagen estática")
    
    args = parser.parse_args()
    
    if args.static:
        demo_static_image()
    else:
        main()