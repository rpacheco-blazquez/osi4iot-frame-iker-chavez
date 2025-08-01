#!/usr/bin/env python3
"""
Script de prueba para verificar que la línea horizontal y el punto del pulsador
se dibujan a la altura del punto D del pórtico.
"""

import sys
import os
import cv2
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from postprocess.distance_calculator import DistanceCalculator

def test_line_at_portico_d_height():
    """
    Prueba que la línea horizontal se dibuje a la altura del punto D del pórtico.
    """
    print("🧪 Iniciando prueba de línea a la altura del punto D del pórtico...")
    
    # Crear imagen de prueba
    test_frame = np.zeros((600, 800, 3), dtype=np.uint8)
    test_frame.fill(50)  # Fondo gris oscuro
    
    # Crear instancia del calculador
    distance_calc = DistanceCalculator(pixels_per_cm=10.0)
    
    # Simular detecciones con pulsador y pórtico a diferentes alturas
    test_detections = [
        {
            'class_name': 'pulsador',
            'keypoints': [
                [200, 400, 0.9],  # keypoint 1 - pulsador en altura 400
                [220, 420, 0.9],  # keypoint 2
                [240, 440, 0.9],  # keypoint 3
                [260, 460, 0.9]   # keypoint 4
            ]
        },
        {
            'class_name': 'portico',
            'keypoints': [
                [100, 150, 0.9],  # A - esquina superior izquierda
                [600, 150, 0.9],  # B - esquina superior derecha
                [600, 350, 0.9],  # C - esquina inferior derecha
                [500, 250, 0.9]   # D - punto de referencia en altura 250
            ]
        }
    ]
    
    print("🔧 DistanceCalculator inicializado en modo standalone")
    
    # Forzar calibración automática
    print("📏 Forzando calibración automática...")
    distance_calc.auto_calibrate(test_detections)
    
    # Dibujar línea de distancia en frame de prueba
    print("🎨 Dibujando línea de distancia en frame de prueba...")
    result_frame = distance_calc.draw_distance_on_frame(
        test_frame, 
        test_detections, 
        show_distance=True, 
        show_line=True
    )
    
    # Agregar información visual para verificación
    pulsador_midpoint = distance_calc.get_pulsador_midpoint(test_detections)
    portico_keypoint_d = distance_calc.get_portico_keypoint_d(test_detections)
    
    if pulsador_midpoint and portico_keypoint_d:
        # Dibujar líneas de referencia para mostrar las alturas
        # Línea horizontal en la altura original del pulsador (para comparación)
        cv2.line(result_frame, (0, int(pulsador_midpoint[1])), (800, int(pulsador_midpoint[1])), 
                (100, 100, 100), 1)  # Línea gris tenue
        cv2.putText(result_frame, f"Altura original pulsador: {int(pulsador_midpoint[1])}", 
                   (10, int(pulsador_midpoint[1]) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        
        # Línea horizontal en la altura del punto D del pórtico
        cv2.line(result_frame, (0, int(portico_keypoint_d[1])), (800, int(portico_keypoint_d[1])), 
                (255, 255, 255), 1)  # Línea blanca
        cv2.putText(result_frame, f"Altura punto D portico: {int(portico_keypoint_d[1])}", 
                   (10, int(portico_keypoint_d[1]) + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Marcar el punto original del pulsador (para comparación)
        cv2.circle(result_frame, (int(pulsador_midpoint[0]), int(pulsador_midpoint[1])), 
                  3, (150, 150, 150), -1)  # Punto gris pequeño
        cv2.putText(result_frame, "Original", (int(pulsador_midpoint[0]) + 10, int(pulsador_midpoint[1])), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    
    # Agregar título y explicación
    cv2.putText(result_frame, "Prueba: Linea a la altura del punto D del portico", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    cv2.putText(result_frame, "- Punto verde: pulsador ajustado a altura D", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(result_frame, "- Punto azul: punto D del portico", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    cv2.putText(result_frame, "- Linea amarilla: distancia horizontal", (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # Guardar imagen
    output_path = "test_line_at_portico_d_height.jpg"
    cv2.imwrite(output_path, result_frame)
    print(f"💾 Imagen guardada como: {output_path}")
    
    # Mostrar imagen
    print("🖼️ Mostrando imagen de prueba...")
    print("   - La línea amarilla debe estar a la altura del punto D del pórtico")
    print("   - El punto verde del pulsador debe estar en la misma línea horizontal")
    print("   - El punto gris muestra la posición original del pulsador")
    
    cv2.imshow("Prueba: Linea a la altura del punto D", result_frame)
    
    print("\n✅ Verificaciones:")
    print("   1. ¿La línea amarilla está a la altura del punto D? (debe ser SÍ)")
    print("   2. ¿El punto verde está en la misma línea horizontal? (debe ser SÍ)")
    print("   3. ¿Se ve la diferencia con la posición original? (debe ser SÍ)")
    
    print("\n⌨️ Presiona cualquier tecla en la ventana de imagen para continuar...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print("🎯 Prueba completada!")
    print(f"📁 Revisa la imagen guardada: {output_path}")

if __name__ == "__main__":
    test_line_at_portico_d_height()