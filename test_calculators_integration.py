#!/usr/bin/env python3
"""
Script de prueba para verificar la integración completa entre calculadores y DicapuaPublisher
Simula el comportamiento real de la aplicación con detecciones simuladas
"""

import sys
import os
import time
import json
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from mqtt.dicapua_publisher import DicapuaPublisher
    from postprocess.distance_calculator import DistanceCalculator
    from postprocess.marker_distance_calculator import MarkerDistanceCalculator
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de que los archivos estén en las rutas correctas")
    sys.exit(1)

def create_mock_detections():
    """Crea detecciones simuladas para probar los calculadores"""
    return [
        {
            'class_name': 'pulsador',
            'bbox': [100, 100, 150, 150],
            'confidence': 0.9,
            'keypoints': [
                [120, 110, 0.8],  # keypoint 0
                [130, 110, 0.8],  # keypoint 1
                [120, 140, 0.8],  # keypoint 2
                [130, 140, 0.8]   # keypoint 3
            ]
        },
        {
            'class_name': 'portico',
            'bbox': [200, 50, 300, 200],
            'confidence': 0.9,
            'keypoints': [
                [220, 70, 0.9],   # A
                [280, 70, 0.9],   # B
                [220, 180, 0.9],  # C
                [280, 180, 0.9]   # D
            ]
        },
        {
            'class_name': 'marcador',
            'bbox': [400, 100, 450, 200],
            'confidence': 0.85,
            'keypoints': [
                [420, 120, 0.8],  # keypoint 0
                [430, 120, 0.8],  # keypoint 1
                [420, 180, 0.8],  # keypoint 2
                [430, 180, 0.8]   # keypoint 3
            ]
        }
    ]

def test_integration():
    """Prueba la integración completa del sistema"""
    print("🧪 === PRUEBA DE INTEGRACIÓN COMPLETA ===")
    print("Simulando el comportamiento real de la aplicación...\n")
    
    try:
        # 1. Crear DicapuaPublisher
        print("1️⃣ Creando DicapuaPublisher...")
        publisher = DicapuaPublisher()
        
        # 2. Iniciar conexión
        print("2️⃣ Iniciando conexión a DicapuaIoT...")
        if not publisher.start_client_direct_mode():
            print("❌ Error al conectar a DicapuaIoT")
            return False
        
        # Esperar conexión
        time.sleep(2)
        
        if not publisher.dicapua_connected:
            print("❌ No se pudo establecer conexión")
            return False
        
        print("✅ Conexión establecida")
        
        # 3. Crear calculadores con el publisher
        print("3️⃣ Creando calculadores de distancia...")
        distance_calc = DistanceCalculator(
            pixels_per_cm=10.0,
            enable_mqtt=True,
            dicapua_publisher=publisher
        )
        
        marker_calc = MarkerDistanceCalculator(
            pixels_per_cm=8.0,
            enable_mqtt=True,
            dicapua_publisher=publisher
        )
        
        print("✅ Calculadores creados")
        
        # 4. Simular detecciones y cálculos
        print("4️⃣ Simulando detecciones y cálculos...")
        
        for i in range(5):
            print(f"\n--- Iteración {i+1} ---")
            
            # Crear detecciones simuladas con variaciones
            detections = create_mock_detections()
            
            # Agregar variación a las posiciones para simular movimiento
            for detection in detections:
                if 'keypoints' in detection:
                    for kp in detection['keypoints']:
                        kp[0] += i * 2  # Movimiento horizontal
                        kp[1] += i * 1  # Movimiento vertical
            
            # Calcular distancias (esto debería activar el envío automático)
            print("📏 Calculando distancia pórtico-pulsador...")
            portico_distance = distance_calc.calculate_pulsador_portico_distance(detections)
            
            print("📐 Calculando distancia marcador...")
            marker_distance = marker_calc.calculate_marker_distance(detections)
            
            if portico_distance:
                print(f"   Distancia pórtico: {portico_distance:.2f} cm")
            else:
                print("   No se pudo calcular distancia pórtico")
                
            if marker_distance:
                print(f"   Distancia marcador: {marker_distance:.2f} cm")
            else:
                print("   No se pudo calcular distancia marcador")
            
            # Esperar un poco entre iteraciones
            time.sleep(1)
        
        # 5. Verificar estado final
        print("\n5️⃣ Verificando estado final...")
        status = publisher.get_connection_status()
        print(f"📊 Estado de conexión: {status['dicapua_connected']}")
        
        latest = publisher.get_latest_distances()
        print(f"📊 Últimas distancias: {latest}")
        
        # 6. Verificar datos recibidos
        if publisher.last_marker_data and publisher.last_portico_data:
            print("\n✅ ¡ÉXITO! Se recibieron datos de ambos calculadores:")
            print(f"   Marcador: {publisher.last_marker_data['distance_cm']:.2f} cm")
            print(f"   Pórtico: {publisher.last_portico_data['distance_cm']:.2f} cm")
            return True
        elif publisher.last_marker_data:
            print("\n⚠️ Solo se recibieron datos del marcador")
            print(f"   Marcador: {publisher.last_marker_data['distance_cm']:.2f} cm")
            return False
        elif publisher.last_portico_data:
            print("\n⚠️ Solo se recibieron datos del pórtico")
            print(f"   Pórtico: {publisher.last_portico_data['distance_cm']:.2f} cm")
            return False
        else:
            print("\n❌ No se recibieron datos de ningún calculador")
            return False
            
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Limpiar
        try:
            if 'publisher' in locals():
                publisher.stop_client()
                print("🔌 Conexión cerrada")
        except:
            pass

def test_movement_detection():
    """Prueba específica del detector de movimiento"""
    print("\n🧪 === PRUEBA DE DETECCIÓN DE MOVIMIENTO ===")
    
    try:
        # Crear publisher
        publisher = DicapuaPublisher()
        if not publisher.start_client_direct_mode():
            print("❌ Error al conectar")
            return False
        
        time.sleep(2)
        
        # Crear calculador
        distance_calc = DistanceCalculator(
            pixels_per_cm=10.0,
            enable_mqtt=True,
            dicapua_publisher=publisher
        )
        
        print("Simulando movimiento gradual...")
        
        # Simular movimiento gradual
        base_detections = create_mock_detections()
        
        for i in range(10):
            # Crear detecciones con movimiento progresivo
            detections = []
            for detection in base_detections:
                new_detection = detection.copy()
                if 'keypoints' in new_detection:
                    new_keypoints = []
                    for kp in detection['keypoints']:
                        # Movimiento más pronunciado para activar el detector
                        new_kp = [kp[0] + i * 5, kp[1] + i * 3, kp[2]]
                        new_keypoints.append(new_kp)
                    new_detection['keypoints'] = new_keypoints
                detections.append(new_detection)
            
            # Calcular distancia
            distance = distance_calc.calculate_pulsador_portico_distance(detections)
            if distance:
                print(f"Iteración {i+1}: {distance:.2f} cm")
            
            time.sleep(0.5)
        
        # Verificar si se enviaron datos
        if publisher.last_portico_data:
            print(f"✅ Detector de movimiento funcionando: {publisher.last_portico_data['distance_cm']:.2f} cm")
            return True
        else:
            print("⚠️ El detector de movimiento puede estar filtrando los datos")
            return False
            
    except Exception as e:
        print(f"❌ Error en prueba de movimiento: {e}")
        return False
    
    finally:
        try:
            if 'publisher' in locals():
                publisher.stop_client()
        except:
            pass

def main():
    """Función principal"""
    print("🚀 PRUEBA DE INTEGRACIÓN CALCULADORES + DICAPUAPUBLISHER")
    print("=" * 60)
    
    # Prueba principal
    success1 = test_integration()
    
    # Prueba de movimiento
    success2 = test_movement_detection()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN FINAL:")
    print(f"✅ Integración completa: {'OK' if success1 else 'FALLO'}")
    print(f"✅ Detección de movimiento: {'OK' if success2 else 'FALLO'}")
    
    if success1 and success2:
        print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        print("Los calculadores están enviando datos correctamente a DicapuaIoT")
    elif success1:
        print("\n⚠️ Integración funciona, pero revisar configuración de movimiento")
    else:
        print("\n❌ Hay problemas en la integración. Revisar configuración.")

if __name__ == "__main__":
    main()