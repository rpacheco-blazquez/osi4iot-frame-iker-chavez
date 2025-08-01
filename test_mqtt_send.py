#!/usr/bin/env python3
"""
Script de prueba para verificar el envío de datos a DicapuaIoT
"""

import sys
import os
import time
import json
from datetime import datetime

# Agregar el directorio src al path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(src_path)

from mqtt.dicapua_publisher import DicapuaPublisher

def test_mqtt_connection():
    """Prueba la conexión y envío de datos a DicapuaIoT"""
    print("🧪 Iniciando prueba de conexión MQTT a DicapuaIoT...")
    
    try:
        # Crear instancia del publisher
        publisher = DicapuaPublisher()
        
        # Iniciar conexión
        if publisher.start_client_direct_mode():
            print("✅ Conexión establecida, esperando confirmación...")
            
            # Esperar a que se establezca la conexión
            time.sleep(3)
            
            if publisher.dicapua_connected:
                print("✅ Conexión confirmada, enviando datos de prueba...")
                
                # Simular datos de marcador y pórtico
                test_marker_data = {
                    'distance_cm': 15.5,
                    'timestamp': datetime.now().isoformat() + 'Z',
                    'source': 'test_marker'
                }
                
                test_portico_data = {
                    'distance_cm': 25.3,
                    'timestamp': datetime.now().isoformat() + 'Z',
                    'source': 'test_portico'
                }
                
                # Enviar datos de marcador
                print("📏 Enviando datos de marcador...")
                success1 = publisher.send_marker_distance(test_marker_data)
                print(f"Resultado marcador: {'✅ Éxito' if success1 else '❌ Error'}")
                
                time.sleep(1)
                
                # Enviar datos de pórtico
                print("🏗️ Enviando datos de pórtico...")
                success2 = publisher.send_distance_data(test_portico_data)
                print(f"Resultado pórtico: {'✅ Éxito' if success2 else '❌ Error'}")
                
                time.sleep(2)
                
                # Probar envío directo
                print("📤 Probando envío directo...")
                success3 = publisher.publish_distance(20.7, 12.4)
                print(f"Resultado envío directo: {'✅ Éxito' if success3 else '❌ Error'}")
                
                # Mostrar estado de conexión
                status = publisher.get_connection_status()
                print("\n📊 Estado de conexión:")
                print(f"  - DicapuaIoT conectado: {status['dicapua_connected']}")
                print(f"  - Broker: {status['dicapua_broker']}")
                print(f"  - Client ID: {status['client_id']}")
                print(f"  - Usando certificados: {status['use_certs']}")
                
                print("\n✅ Prueba completada. Los datos deberían aparecer en DicapuaIoT.")
                
            else:
                print("❌ No se pudo establecer la conexión a DicapuaIoT")
                
        else:
            print("❌ Error al iniciar el cliente MQTT")
            
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Limpiar recursos
        try:
            if 'publisher' in locals():
                publisher.stop_client()
                print("🔌 Conexión cerrada")
        except:
            pass

if __name__ == "__main__":
    test_mqtt_connection()