#!/usr/bin/env python3
"""
Script de comparación visual: línea inclinada vs línea recta.
"""

import sys
import os
import cv2
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from postprocess.distance_calculator import DistanceCalculator

def create_comparison_visualization():
    """
    Crea una imagen de comparación mostrando la diferencia entre línea inclinada y recta.
    """
    print("🧪 Creando comparación visual: línea inclinada vs recta...")
    
    # Crear imagen de comparación (lado a lado)
    comparison_frame = np.zeros((600, 1200, 3), dtype=np.uint8)
    comparison_frame.fill(50)  # Fondo gris oscuro
    
    # Crear instancia del calculador
    distance_calc = DistanceCalculator(pixels_per_cm=10.0)
    
    # Simular detecciones con puntos en diferentes alturas
    test_detections = [
        {
            'class_name': 'pulsador',
            'keypoints': [
                [150, 400, 0.9],  # keypoint 1
                [170, 420, 0.9],  # keypoint 2
                [190, 440, 0.9],  # keypoint 3
                [210, 460, 0.9]   # keypoint 4
            ]
        },
        {
            'class_name': 'portico',
            'keypoints': [
                [50, 100, 0.9],   # A
                [550, 100, 0.9],  # B - para calibración
                [550, 500, 0.9],  # C - para calibración
                [400, 200, 0.9]   # D - punto de referencia (diferente altura que pulsador)
            ]
        }
    ]
    
    # Forzar calibración
    distance_calc.auto_calibrate(test_detections)
    
    # Lado izquierdo: Simular línea inclinada (método anterior)
    left_frame = comparison_frame[:, :600].copy()
    
    # Obtener puntos
    pulsador_midpoint = distance_calc.get_pulsador_midpoint(test_detections)
    portico_keypoint_d = distance_calc.get_portico_keypoint_d(test_detections)
    distance_cm = distance_calc.calculate_pulsador_portico_distance(test_detections)
    
    if pulsador_midpoint and portico_keypoint_d and distance_cm is not None:
        # Puntos originales
        pt1 = (int(pulsador_midpoint[0]), int(pulsador_midpoint[1]))
        pt2 = (int(portico_keypoint_d[0]), int(portico_keypoint_d[1]))
        
        # Dibujar línea inclinada (método anterior)
        cv2.line(left_frame, pt1, pt2, (0, 255, 255), 3)  # Línea amarilla inclinada
        cv2.circle(left_frame, pt1, 6, (0, 255, 0), -1)  # Punto verde para pulsador
        cv2.circle(left_frame, pt2, 6, (255, 0, 0), -1)  # Punto azul para pórtico D
        
        # Texto en línea inclinada
        mid_x = int((pt1[0] + pt2[0]) / 2)
        mid_y = int((pt1[1] + pt2[1]) / 2)
        cv2.putText(left_frame, f"{distance_cm:.1f}cm", (mid_x, mid_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    # Lado derecho: Usar el método actual (línea recta)
    right_frame = comparison_frame[:, 600:].copy()
    
    # Ajustar coordenadas para el lado derecho
    test_detections_right = [
        {
            'class_name': 'pulsador',
            'keypoints': [
                [150, 400, 0.9],  # keypoint 1
                [170, 420, 0.9],  # keypoint 2
                [190, 440, 0.9],  # keypoint 3
                [210, 460, 0.9]   # keypoint 4
            ]
        },
        {
            'class_name': 'portico',
            'keypoints': [
                [50, 100, 0.9],   # A
                [550, 100, 0.9],  # B - para calibración
                [550, 500, 0.9],  # C - para calibración
                [400, 200, 0.9]   # D - punto de referencia
            ]
        }
    ]
    
    # Dibujar usando el método actual (línea recta)
    result_right = distance_calc.draw_distance_on_frame(
        right_frame, 
        test_detections_right, 
        show_distance=True, 
        show_line=True
    )
    
    # Combinar ambos lados
    comparison_frame[:, :600] = left_frame
    comparison_frame[:, 600:] = result_right
    
    # Agregar línea divisoria
    cv2.line(comparison_frame, (600, 0), (600, 600), (255, 255, 255), 2)
    
    # Agregar títulos
    cv2.putText(comparison_frame, "ANTES: Linea Inclinada", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(comparison_frame, "DESPUES: Linea Recta", (650, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Agregar explicaciones
    cv2.putText(comparison_frame, "Conecta directamente", (50, 550),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    cv2.putText(comparison_frame, "los dos puntos", (50, 570),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    
    cv2.putText(comparison_frame, "Linea horizontal a la", (650, 550),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    cv2.putText(comparison_frame, "altura del pulsador", (650, 570),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    
    # Guardar imagen de comparación
    output_path = "comparison_inclined_vs_straight.jpg"
    cv2.imwrite(output_path, comparison_frame)
    print(f"💾 Imagen de comparación guardada como: {output_path}")
    
    # Mostrar imagen
    print("🖼️ Mostrando comparación...")
    cv2.imshow("Comparacion: Linea Inclinada vs Linea Recta", comparison_frame)
    
    print("\n✅ Comparación:")
    print("   IZQUIERDA (ANTES): Línea inclinada que conecta directamente los puntos")
    print("   DERECHA (DESPUÉS): Línea horizontal que muestra la distancia X")
    print("   La línea recta es más clara para medir distancias horizontales")
    
    print("\n⌨️ Presiona cualquier tecla para cerrar...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print("🎯 Comparación completada!")
    print(f"📁 Revisa la imagen guardada: {output_path}")

if __name__ == "__main__":
    create_comparison_visualization()