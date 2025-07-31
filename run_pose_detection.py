#!/usr/bin/env python3
"""Script para ejecutar detección de pose en tiempo real."""

from src.vision.detector import YOLOPoseDetector

def main():
    """Ejecuta la detección de pose en tiempo real."""
    print("🎯 Iniciando detección de pose en tiempo real...")
    
    # Crear detector
    detector = YOLOPoseDetector()
    
    # Ejecutar detección en tiempo real
    detector.run_real_time_detection()

if __name__ == "__main__":
    main()