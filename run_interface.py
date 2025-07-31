#!/usr/bin/env python3
"""Script de lanzamiento para la interfaz interactiva de detección."""

import sys
from pathlib import Path

# Agregar el directorio src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from gui.interactive_interface import InteractiveDetectionInterface

def main():
    """Función principal para lanzar la interfaz."""
    print("Iniciando Interfaz Interactiva de Detección...")
    print("Características:")
    print("- Configuración de parámetros de detección en tiempo real")
    print("- Visualización de cámara en vivo con bounding boxes y keypoints")
    print("- Información detallada de detecciones")
    print("- Captura de frames")
    print("\nPresiona Ctrl+C para salir\n")
    
    try:
        # Crear y ejecutar interfaz
        interface = InteractiveDetectionInterface("config/config.yaml")
        interface.run()
    except KeyboardInterrupt:
        print("\nInterfaz cerrada por el usuario")
    except Exception as e:
        print(f"Error al ejecutar la interfaz: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()