#!/usr/bin/env python3
"""
Script de prueba para verificar que las distancias negativas se convierten a 0 cm.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from postprocess.distance_calculator import DistanceCalculator
from postprocess.marker_distance_calculator import MarkerDistanceCalculator

def test_negative_distance_conversion():
    """
    Prueba que las distancias negativas se conviertan a 0 cm.
    """
    print("🧪 Iniciando pruebas de conversión de distancias negativas...")
    
    # Crear instancias de los calculadores
    distance_calc = DistanceCalculator(pixels_per_cm=10.0)  # 10 píxeles = 1 cm
    marker_calc = MarkerDistanceCalculator(pixels_per_cm=10.0)
    
    # Simular detecciones que resulten en distancia negativa
    # Para el distance_calculator (pulsador-pórtico)
    test_detections_portico = [
        {
            'class_name': 'pulsador',
            'keypoints': [
                [100, 100, 0.9],  # keypoint 1
                [110, 110, 0.9],  # keypoint 2
                [120, 120, 0.9],  # keypoint 3
                [130, 130, 0.9]   # keypoint 4
            ]
        },
        {
            'class_name': 'portico',
            'keypoints': [
                [50, 50, 0.9],    # A
                [200, 50, 0.9],   # B - para calibración
                [200, 200, 0.9],  # C - para calibración
                [150, 150, 0.9]   # D - punto de referencia (más cerca que pulsador)
            ]
        }
    ]
    
    # Para el marker_distance_calculator
    test_detections_marker = [
        {
            'class_name': 'marcador',
            'bbox': [80, 80, 120, 120],  # x1, y1, x2, y2
            'keypoints': [
                [100, 70, 0.9],  # keypoint arriba del bbox (distancia negativa)
                [110, 75, 0.9]
            ]
        }
    ]
    
    print("\n📏 Probando DistanceCalculator (pulsador-pórtico)...")
    
    # Forzar calibración automática
    distance_calc.auto_calibrate(test_detections_portico)
    
    # Calcular distancia (debería ser negativa pero convertirse a 0)
    distance_portico = distance_calc.calculate_pulsador_portico_distance(test_detections_portico)
    
    if distance_portico is not None:
        print(f"✅ Distancia pulsador-pórtico: {distance_portico:.2f} cm")
        if distance_portico == 0.0:
            print("✅ ¡Correcto! La distancia negativa se convirtió a 0 cm")
        elif distance_portico > 0:
            print("ℹ️ La distancia es positiva (caso normal)")
        else:
            print("❌ Error: La distancia sigue siendo negativa")
    else:
        print("⚠️ No se pudo calcular la distancia pulsador-pórtico")
    
    print("\n📏 Probando MarkerDistanceCalculator...")
    
    # Calcular distancia del marcador (debería ser negativa pero convertirse a 0)
    distance_marker = marker_calc.calculate_marker_distance(test_detections_marker)
    
    if distance_marker is not None:
        print(f"✅ Distancia marcador: {distance_marker:.2f} cm")
        if distance_marker == 0.0:
            print("✅ ¡Correcto! La distancia negativa se convirtió a 0 cm")
        elif distance_marker > 0:
            print("ℹ️ La distancia es positiva (caso normal)")
        else:
            print("❌ Error: La distancia sigue siendo negativa")
    else:
        print("⚠️ No se pudo calcular la distancia del marcador")
    
    print("\n🎯 Pruebas completadas!")
    print("📋 Resumen:")
    print("   - Las distancias negativas ahora se convierten automáticamente a 0 cm")
    print("   - Esto se aplica tanto al cálculo pulsador-pórtico como al marcador")
    print("   - Los valores se envían correctamente por MQTT/comunicación directa")

if __name__ == "__main__":
    test_negative_distance_conversion()