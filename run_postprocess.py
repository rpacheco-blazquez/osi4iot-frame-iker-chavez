#!/usr/bin/env python3
"""
Script de lanzamiento para el postprocesamiento de detecciones.
Calcula distancias en tiempo real entre objetos detectados.

Uso:
    python run_postprocess.py
    
Controles:
    - 'q': Salir
    - 'c': Calibrar factor píxeles/cm
    - 's': Guardar frame actual
"""

import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from postprocess.video_processor import VideoPostProcessor

def main():
    """
    Función principal del postprocesamiento.
    """
    print("=" * 60)
    print("    POSTPROCESAMIENTO DE DETECCIONES - CÁLCULO DE DISTANCIAS")
    print("=" * 60)
    print()
    print("Este módulo calcula la distancia entre:")
    print("  • Punto medio de los 4 keypoints del 'pulsador'")
    print("  • Keypoint D del 'pórtico'")
    print()
    print("Controles:")
    print("  • 'q' - Salir")
    print("  • 'c' - Calibrar factor píxeles/cm")
    print("  • 's' - Guardar frame actual")
    print()
    print("Iniciando...")
    print("=" * 60)
    
    try:
        # Crear procesador con configuración por defecto
        processor = VideoPostProcessor(
            model_path="models/best.pt",
            pixels_per_cm=10.0  # Factor inicial, se puede calibrar en tiempo real
        )
        
        # Ejecutar procesamiento en tiempo real
        processor.run_real_time_processing()
        
    except FileNotFoundError as e:
        print(f"Error: No se encontró el archivo del modelo: {e}")
        print("Asegúrate de que el archivo 'models/best.pt' existe.")
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nPostprocesamiento finalizado.")

if __name__ == "__main__":
    main()