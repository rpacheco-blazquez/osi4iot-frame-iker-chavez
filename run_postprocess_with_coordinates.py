#!/usr/bin/env python3
"""Script de ejemplo para postprocesamiento con sistema de coordenadas.

Este script demuestra cómo usar el CoordinateAxisDrawer junto con
los calculadores de distancia existentes para añadir un sistema de
coordenadas visual a las detecciones.
"""

import cv2
import sys
from pathlib import Path

# Agregar el directorio src al path
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from vision.detector import YOLOPoseDetector
from postprocess.distance_calculator import DistanceCalculator
from postprocess.marker_distance_calculator import MarkerDistanceCalculator
from postprocess.coordinate_axis_drawer import CoordinateAxisDrawer

def main():
    """Función principal del script."""
    print("🚀 Iniciando postprocesamiento con sistema de coordenadas...")
    
    # Inicializar componentes
    detector = YOLOPoseDetector("config/config.yaml")
    distance_calc = DistanceCalculator(pixels_per_cm=10.0)
    marker_calc = MarkerDistanceCalculator(pixels_per_cm=10.0)
    coord_drawer = CoordinateAxisDrawer(position="bottom_right", size=80, margin=30)
    
    # Cargar modelo
    detector.load_model()
    print("✅ Modelo YOLO cargado")
    
    # Configurar captura de video
    cap = cv2.VideoCapture(0)  # Usar cámara por defecto
    
    if not cap.isOpened():
        print("❌ Error: No se pudo abrir la cámara")
        return
    
    print("📹 Cámara iniciada. Presiona 'q' para salir, 'p' para cambiar posición del sistema de coordenadas")
    
    # Posiciones disponibles para el sistema de coordenadas
    positions = ["bottom_right", "bottom_left", "top_right", "top_left"]
    current_pos_idx = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Error al capturar frame")
                break
            
            # Realizar detección
            detections = detector.get_detections_data(frame)
            
            # Aplicar postprocesamiento
            processed_frame = frame.copy()
            
            # 1. Dibujar distancias pulsador-pórtico
            processed_frame = distance_calc.draw_distance_on_frame(
                processed_frame, detections, show_distance=True, show_line=True
            )
            
            # 2. Dibujar distancias del marcador
            processed_frame = marker_calc.draw_distance_on_frame(
                processed_frame, detections, show_distance=True, show_line=True
            )
            
            # 3. Añadir sistema de coordenadas
            processed_frame = coord_drawer.draw_coordinate_system(processed_frame)
            
            # Añadir información en pantalla
            info_text = f"Detecciones: {len(detections)} | Posición ejes: {coord_drawer.position}"
            cv2.putText(processed_frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Instrucciones
            instructions = "Presiona 'q': salir | 'p': cambiar posición ejes"
            cv2.putText(processed_frame, instructions, (10, processed_frame.shape[0] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Mostrar frame
            cv2.imshow("Postprocesamiento con Sistema de Coordenadas", processed_frame)
            
            # Manejar teclas
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                # Cambiar posición del sistema de coordenadas
                current_pos_idx = (current_pos_idx + 1) % len(positions)
                new_position = positions[current_pos_idx]
                coord_drawer.set_position(new_position)
                print(f"🔄 Sistema de coordenadas movido a: {new_position}")
    
    except KeyboardInterrupt:
        print("\n⏹️ Interrumpido por el usuario")
    
    finally:
        # Limpiar recursos
        cap.release()
        cv2.destroyAllWindows()
        print("🧹 Recursos liberados")

if __name__ == "__main__":
    main()