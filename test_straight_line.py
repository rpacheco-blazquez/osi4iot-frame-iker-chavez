#!/usr/bin/env python3
"""
Script de prueba para verificar que la línea amarilla de distancia aparece recta.
"""

import sys
import os
import cv2
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from postprocess.distance_calculator import DistanceCalculator

def test_straight_line_visualization():
    """
    Prueba visual para verificar que la línea amarilla aparece recta.
    """
    print("🧪 Iniciando prueba de visualización de línea recta...")
    
    # Crear una imagen de prueba
    test_frame = np.zeros((600, 800, 3), dtype=np.uint8)
    test_frame.fill(50)  # Fondo gris oscuro
    
    # Crear instancia del calculador
    distance_calc = DistanceCalculator(pixels_per_cm=10.0)
    
    # Simular detecciones con puntos en diferentes alturas para probar la línea recta
    test_detections = [
        {
            'class_name': 'pulsador',
            'keypoints': [
                [200, 300, 0.9],  # keypoint 1
                [220, 320, 0.9],  # keypoint 2
                [240, 340, 0.9],  # keypoint 3
                [260, 360, 0.9]   # keypoint 4
            ]
        },
        {
            'class_name': 'portico',
            'keypoints': [
                [100, 100, 0.9],  # A
                [700, 100, 0.9],  # B - para calibración
                [700, 500, 0.9],  # C - para calibración
                [500, 200, 0.9]   # D - punto de referencia (diferente altura que pulsador)
            ]
        }
    ]
    
    print("📏 Forzando calibración automática...")
    distance_calc.auto_calibrate(test_detections)
    
    print("🎨 Dibujando línea de distancia en frame de prueba...")
    result_frame = distance_calc.draw_distance_on_frame(
        test_frame, 
        test_detections, 
        show_distance=True, 
        show_line=True
    )
    
    # Agregar información adicional al frame
    cv2.putText(result_frame, "Prueba: Linea Amarilla Recta", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(result_frame, "La linea amarilla debe ser horizontal", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(result_frame, "Presiona 'q' para salir", (10, result_frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Guardar imagen de prueba
    output_path = "test_straight_line_output.jpg"
    cv2.imwrite(output_path, result_frame)
    print(f"💾 Imagen guardada como: {output_path}")
    
    # Mostrar imagen
    print("🖼️ Mostrando imagen de prueba...")
    print("   - La línea amarilla debe aparecer horizontal")
    print("   - Conecta el pulsador (punto verde) con el pórtico D (punto azul)")
    print("   - La línea debe estar a la altura del pulsador")
    
    cv2.imshow("Prueba Linea Recta - Distancia Pulsador-Portico", result_frame)
    
    print("\n✅ Verificaciones:")
    print("   1. ¿La línea amarilla es horizontal? (debe ser SÍ)")
    print("   2. ¿La línea está a la altura del pulsador? (debe ser SÍ)")
    print("   3. ¿La distancia se muestra correctamente? (debe ser SÍ)")
    
    # Esperar tecla
    print("\n⌨️ Presiona cualquier tecla en la ventana de imagen para continuar...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print("🎯 Prueba completada!")
    print(f"📁 Revisa la imagen guardada: {output_path}")

if __name__ == "__main__":
    test_straight_line_visualization()