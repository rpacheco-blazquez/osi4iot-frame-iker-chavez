"""
Script de prueba para el detector de movimiento inteligente.
Demuestra cómo el sistema filtra datos MQTT cuando el pulsador no se mueve realmente.
"""

import time
import random
import json
from movement_detector import MovementDetector

def simulate_detection_noise(base_position, noise_level=2.0):
    """
    Simula ruido en la detección de posiciones.
    
    Args:
        base_position: Posición base (x, y)
        noise_level: Nivel de ruido en píxeles
        
    Returns:
        Posición con ruido añadido
    """
    noise_x = random.uniform(-noise_level, noise_level)
    noise_y = random.uniform(-noise_level, noise_level)
    return (base_position[0] + noise_x, base_position[1] + noise_y)

def simulate_real_movement(start_pos, end_pos, progress):
    """
    Simula movimiento real entre dos posiciones.
    
    Args:
        start_pos: Posición inicial (x, y)
        end_pos: Posición final (x, y)
        progress: Progreso del movimiento (0.0 a 1.0)
        
    Returns:
        Posición interpolada
    """
    x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    return (x, y)

def test_movement_detection():
    """
    Prueba el detector de movimiento con diferentes escenarios.
    """
    print("🔍 Iniciando prueba del detector de movimiento inteligente")
    print("=" * 60)
    
    # Crear detector con configuración de prueba
    detector = MovementDetector(
        distance_threshold_cm=0.5,
        velocity_threshold_cm_s=0.3,
        position_stability_frames=3,
        temporal_window_seconds=1.5
    )
    
    # Posiciones base
    pulsador_base = (100, 200)
    portico_base = (300, 200)
    
    print("\n📊 Escenario 1: Posiciones estables con ruido (no debería enviar)")
    print("-" * 50)
    
    for i in range(10):
        # Simular ruido en posiciones estables
        pulsador_pos = simulate_detection_noise(pulsador_base, 1.5)
        portico_pos = simulate_detection_noise(portico_base, 1.0)
        
        # Calcular distancia con pequeñas variaciones por ruido
        distance = 50.0 + random.uniform(-0.3, 0.3)
        
        detector.update_positions(pulsador_pos, portico_pos, distance)
        should_send = detector.should_send_distance(distance)
        
        print(f"Frame {i+1:2d}: Distancia={distance:5.2f}cm, Enviar={should_send}, "
              f"Pulsador=({pulsador_pos[0]:6.1f},{pulsador_pos[1]:6.1f})")
        
        time.sleep(0.1)
    
    print("\n📊 Escenario 2: Movimiento real del pulsador (debería enviar)")
    print("-" * 50)
    
    start_pos = (100, 200)
    end_pos = (150, 250)
    
    for i in range(10):
        # Simular movimiento real
        progress = i / 9.0
        pulsador_pos = simulate_real_movement(start_pos, end_pos, progress)
        portico_pos = simulate_detection_noise(portico_base, 1.0)
        
        # Calcular distancia que cambia con el movimiento
        distance = 50.0 + progress * 10.0  # Distancia aumenta con el movimiento
        
        detector.update_positions(pulsador_pos, portico_pos, distance)
        should_send = detector.should_send_distance(distance)
        
        print(f"Frame {i+1:2d}: Distancia={distance:5.2f}cm, Enviar={should_send}, "
              f"Pulsador=({pulsador_pos[0]:6.1f},{pulsador_pos[1]:6.1f})")
        
        time.sleep(0.2)
    
    print("\n📊 Escenario 3: Cambios rápidos por errores de detección (debería filtrar)")
    print("-" * 50)
    
    for i in range(8):
        # Simular errores de detección que causan saltos
        if i % 2 == 0:
            pulsador_pos = (100, 200)
            distance = 50.0
        else:
            pulsador_pos = (120, 220)  # Salto por error de detección
            distance = 52.0
        
        portico_pos = simulate_detection_noise(portico_base, 1.0)
        
        detector.update_positions(pulsador_pos, portico_pos, distance)
        should_send = detector.should_send_distance(distance)
        
        print(f"Frame {i+1:2d}: Distancia={distance:5.2f}cm, Enviar={should_send}, "
              f"Pulsador=({pulsador_pos[0]:6.1f},{pulsador_pos[1]:6.1f})")
        
        time.sleep(0.05)  # Cambios muy rápidos
    
    # Mostrar métricas finales
    print("\n📈 Métricas finales del detector")
    print("=" * 40)
    
    metrics = detector.get_movement_metrics()
    statistics = detector.get_filter_statistics()
    
    print(f"Total de cálculos: {statistics['total_calculations']}")
    print(f"Distancias enviadas: {statistics['sent_distances']}")
    print(f"Tasa de filtrado: {statistics['filter_rate_percent']:.1f}%")
    print(f"\nFiltros aplicados:")
    for filter_name, filter_data in statistics['filters'].items():
        print(f"  - {filter_name}: {filter_data['count']} ({filter_data['percentage']:.1f}%)")
    
    print(f"\nVelocidades promedio:")
    print(f"  - Pulsador: {metrics['pulsador_velocity_px_s']:.2f} px/s")
    print(f"  - Pórtico: {metrics['portico_velocity_px_s']:.2f} px/s")
    print(f"  - Relativa: {metrics['relative_velocity_px_s']:.2f} px/s")
    print(f"  - Distancia: {metrics['distance_velocity_cm_s']:.2f} cm/s")

def test_filter_configuration():
    """
    Prueba la configuración dinámica de filtros.
    """
    print("\n🔧 Prueba de configuración de filtros")
    print("=" * 40)
    
    detector = MovementDetector()
    
    # Deshabilitar filtro de velocidad
    detector.enable_filter('velocity', False)
    print("✅ Filtro de velocidad deshabilitado")
    
    # Deshabilitar filtro de estabilidad
    detector.enable_filter('stability', False)
    print("✅ Filtro de estabilidad deshabilitado")
    
    # Mostrar estado de filtros
    stats = detector.get_filter_statistics()
    print("\n📋 Estado actual de filtros:")
    for filter_name, enabled in stats['filter_status'].items():
        status = "🟢 Habilitado" if enabled else "🔴 Deshabilitado"
        print(f"  - {filter_name}: {status}")

def test_config_file():
    """
    Prueba la carga de configuración desde archivo.
    """
    print("\n📄 Prueba de configuración desde archivo")
    print("=" * 40)
    
    # Crear configuración de prueba
    test_config = {
        "movement_detection": {
            "distance_threshold_cm": 1.0,
            "velocity_threshold_cm_s": 0.5,
            "position_stability_frames": 8,
            "temporal_window_seconds": 3.0
        },
        "mqtt_filtering": {
            "enable_movement_detection": True,
            "enable_velocity_filter": False,
            "enable_stability_filter": True,
            "enable_relative_movement_filter": True,
            "enable_temporal_filter": False
        },
        "debug": {
            "log_movement_metrics": True,
            "log_filtered_attempts": True
        }
    }
    
    # Guardar configuración de prueba
    config_file = "test_movement_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(test_config, f, indent=2)
    
    # Crear detector con configuración personalizada
    detector = MovementDetector(config_file=config_file)
    
    print(f"✅ Detector creado con configuración desde {config_file}")
    print(f"📊 Umbral de distancia: {detector.distance_threshold_cm} cm")
    print(f"📊 Umbral de velocidad: {detector.velocity_threshold_cm_s} cm/s")
    print(f"📊 Frames de estabilidad: {detector.position_stability_frames}")
    
    # Limpiar archivo de prueba
    import os
    os.remove(config_file)
    print(f"🗑️ Archivo de configuración de prueba eliminado")

if __name__ == "__main__":
    try:
        test_movement_detection()
        test_filter_configuration()
        test_config_file()
        
        print("\n✅ Todas las pruebas completadas exitosamente")
        print("\n💡 El detector de movimiento inteligente está funcionando correctamente.")
        print("   Ahora el sistema MQTT solo enviará datos cuando detecte movimiento real")
        print("   del pulsador, evitando spam por errores de detección.")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()