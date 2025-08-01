#!/usr/bin/env python3
"""
Script de debug específico para el calculador de marcador
"""

import sys
import os
import time

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from mqtt.dicapua_publisher import DicapuaPublisher
    from postprocess.marker_distance_calculator import MarkerDistanceCalculator
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)

def create_marker_detections(offset=0):
    """Crea detecciones de marcador con variación"""
    return [
        {
            'class_name': 'marcador',
            'bbox': [400 + offset, 100 + offset, 450 + offset, 200 + offset],
            'confidence': 0.85,
            'keypoints': [
                [420 + offset, 120 + offset, 0.8],  # keypoint 0
                [430 + offset, 120 + offset, 0.8],  # keypoint 1
                [420 + offset, 180 + offset, 0.8],  # keypoint 2
                [430 + offset, 180 + offset, 0.8]   # keypoint 3
            ]
        }
    ]

def test_marker_calculator():
    """Prueba específica del calculador de marcador"""
    print("🧪 === DEBUG CALCULADOR DE MARCADOR ===")
    
    try:
        # Crear publisher
        print("1️⃣ Creando DicapuaPublisher...")
        publisher = DicapuaPublisher()
        
        if not publisher.start_client_direct_mode():
            print("❌ Error al conectar")
            return False
        
        time.sleep(2)
        print(f"✅ Conectado: {publisher.dicapua_connected}")
        
        # Crear calculador de marcador
        print("2️⃣ Creando MarkerDistanceCalculator...")
        marker_calc = MarkerDistanceCalculator(
            pixels_per_cm=8.0,
            enable_mqtt=True,
            dicapua_publisher=publisher
        )
        
        print(f"✅ Calculador creado - MQTT habilitado: {marker_calc.enable_mqtt}")
        print(f"✅ MQTT conectado: {marker_calc.mqtt_connected}")
        print(f"✅ Publisher asignado: {marker_calc.dicapua_publisher is not None}")
        
        # Probar cálculos con movimiento significativo
        print("3️⃣ Probando cálculos con movimiento...")
        
        for i in range(10):
            # Crear detecciones con movimiento significativo
            offset = i * 10  # Movimiento más pronunciado
            detections = create_marker_detections(offset)
            
            print(f"\n--- Iteración {i+1} (offset: {offset}) ---")
            
            # Obtener puntos individuales
            bbox_point = marker_calc.get_marker_bbox_top_midpoint(detections)
            keypoints_point = marker_calc.get_marker_keypoints_midpoint(detections)
            
            print(f"📍 Bbox point: {bbox_point}")
            print(f"📍 Keypoints point: {keypoints_point}")
            
            if bbox_point and keypoints_point:
                # Calcular distancia en píxeles
                distance_px = marker_calc.calculate_euclidean_distance(bbox_point, keypoints_point)
                print(f"📏 Distancia píxeles: {distance_px:.2f}")
                
                # Convertir a cm
                distance_cm = marker_calc.pixels_to_cm(distance_px)
                print(f"📏 Distancia cm: {distance_cm:.2f}")
                
                # Llamar al método principal que debería enviar datos
                result_distance = marker_calc.calculate_marker_distance(detections)
                print(f"📏 Resultado calculate_marker_distance: {result_distance}")
                
                # Verificar estado del detector de movimiento
                metrics = marker_calc.movement_detector.get_movement_metrics()
                print(f"📊 Métricas movimiento: {metrics}")
                
                # Verificar si se debe enviar
                should_send = marker_calc.movement_detector.should_send_distance(distance_cm)
                print(f"🤔 ¿Debería enviar?: {should_send}")
                
            time.sleep(0.5)
        
        # Verificar estado final del publisher
        print("\n4️⃣ Estado final del publisher...")
        print(f"📊 last_marker_data: {publisher.last_marker_data}")
        print(f"📊 last_portico_data: {publisher.last_portico_data}")
        
        # Probar envío directo
        print("\n5️⃣ Probando envío directo...")
        test_payload = {
            'distance_cm': 15.5,
            'timestamp': '2024-01-01T12:00:00Z',
            'type': 'marker_distance'
        }
        
        result = publisher.send_marker_distance(test_payload)
        print(f"📤 Resultado envío directo: {result}")
        print(f"📊 last_marker_data después: {publisher.last_marker_data}")
        
        return publisher.last_marker_data is not None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            if 'publisher' in locals():
                publisher.stop_client()
        except:
            pass

def test_movement_detector_directly():
    """Prueba el detector de movimiento directamente"""
    print("\n🧪 === DEBUG DETECTOR DE MOVIMIENTO ===")
    
    try:
        from postprocess.movement_detector import MovementDetector
        
        # Crear detector con configuración permisiva
        detector = MovementDetector(
            distance_threshold_cm=0.1,
            velocity_threshold_cm_s=0.05,
            position_stability_frames=2,
            temporal_window_seconds=0.5
        )
        
        print("✅ Detector creado")
        
        # Simular actualizaciones
        for i in range(5):
            bbox_pos = (400 + i*5, 100 + i*5)
            keypoints_pos = (425 + i*5, 150 + i*5)
            distance = 10.0 + i*2
            
            print(f"\n--- Actualización {i+1} ---")
            print(f"📍 Posiciones: bbox={bbox_pos}, keypoints={keypoints_pos}")
            print(f"📏 Distancia: {distance}")
            
            detector.update_positions(bbox_pos, keypoints_pos, distance)
            should_send = detector.should_send_distance(distance)
            
            print(f"🤔 ¿Debería enviar?: {should_send}")
            
            metrics = detector.get_movement_metrics()
            print(f"📊 Métricas: {metrics}")
            
            time.sleep(0.1)
        
        return True
        
    except Exception as e:
        print(f"❌ Error en detector: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 DEBUG CALCULADOR DE MARCADOR")
    print("=" * 50)
    
    # Test 1: Detector de movimiento
    success1 = test_movement_detector_directly()
    
    # Test 2: Calculador completo
    success2 = test_marker_calculator()
    
    print("\n" + "=" * 50)
    print("📋 RESUMEN DEBUG:")
    print(f"✅ Detector de movimiento: {'OK' if success1 else 'FALLO'}")
    print(f"✅ Calculador completo: {'OK' if success2 else 'FALLO'}")
    
    if success2:
        print("\n🎉 ¡El calculador de marcador está funcionando!")
    else:
        print("\n❌ Hay problemas en el calculador de marcador")

if __name__ == "__main__":
    main()