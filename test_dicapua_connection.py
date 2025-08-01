#!/usr/bin/env python3
"""
Script de diagnóstico mejorado para probar la conexión a DicapuaIoT
Replica exactamente la configuración del DicapuaPublisher
"""

import json
import ssl
import time
import logging
import paho.mqtt.client as mqtt
from pathlib import Path
import sys
import os

# Agregar el directorio src al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from mqtt.config.config import MQTTConfig
except ImportError:
    print("⚠️ No se pudo importar MQTTConfig, usando configuración manual")
    MQTTConfig = None

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config_manual():
    """Cargar configuración manualmente si no se puede importar MQTTConfig"""
    config_path = Path("src/mqtt/config/dicapuaiot/dicapuaiot.json")
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    # Crear objeto de configuración simple
    class SimpleConfig:
        def __init__(self, data):
            self.broker = data['broker']
            self.client_id = data['client_id']
            self.username = data['username']
            self.password = data['password']
            self.connectCerts = True
            
            # Configurar certificados
            cert_base = Path("src/mqtt/config")
            self.certs = {
                "ca_certs": str(cert_base / data['ca_crt']),
                "certfile": str(cert_base / data['group_1_crt']),
                "keyfile": str(cert_base / data['group_1_key'])
            }
            
            # Topics
            self.topic = type('obj', (object,), {
                'publish': data['hashes']['publish']
            })
    
    return SimpleConfig(config_data)

def test_connection_with_exact_config():
    """Probar conexión usando exactamente la misma configuración que DicapuaPublisher"""
    try:
        # Cargar configuración
        if MQTTConfig:
            config = MQTTConfig("dicapuaiot")
        else:
            config = load_config_manual()
        
        logger.info("📋 Configuración cargada")
        logger.info(f"🔗 Broker: {config.broker}")
        logger.info(f"👤 Client ID base: {config.client_id}")
        
        # Variables de estado
        connection_successful = False
        publish_successful = False
        messages_received = 0
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connection_successful
            if rc == 0:
                connection_successful = True
                logger.info("✅ Conectado exitosamente a DicapuaIoT (configuración exacta)")
                
                # Suscribirse al topic
                topic = config.topic.publish["YOLOframe"]["topic"]
                client.subscribe(topic)
                logger.info(f"📡 Suscrito al topic: {topic}")
            else:
                logger.error(f"❌ Error de conexión MQTT. Código: {rc}")
                error_codes = {
                    1: "Versión de protocolo incorrecta",
                    2: "Identificador de cliente inválido", 
                    3: "Servidor no disponible",
                    4: "Usuario o contraseña incorrectos",
                    5: "No autorizado"
                }
                logger.error(f"Descripción: {error_codes.get(rc, 'Error desconocido')}")
        
        def on_message(client, userdata, msg):
            nonlocal messages_received
            messages_received += 1
            logger.info(f"📨 Mensaje #{messages_received} recibido en {msg.topic}: {msg.payload.decode()[:100]}...")
        
        def on_publish(client, userdata, mid):
            nonlocal publish_successful
            publish_successful = True
            logger.info(f"✅ Mensaje publicado exitosamente (mid: {mid})")
        
        def on_disconnect(client, userdata, rc):
            nonlocal connection_successful
            connection_successful = False
            if rc != 0:
                logger.warning(f"⚠️ Desconexión inesperada. Código: {rc}")
                # Códigos de desconexión comunes
                disconnect_codes = {
                    1: "Versión de protocolo no aceptable",
                    2: "Identificador rechazado",
                    3: "Servidor no disponible",
                    4: "Usuario/contraseña malformados",
                    5: "No autorizado",
                    7: "Error de red/conexión",
                    8: "Timeout de conexión"
                }
                logger.warning(f"Razón: {disconnect_codes.get(rc, 'Desconocida')}")
            else:
                logger.info("🔌 Desconectado correctamente")
        
        # Crear cliente MQTT exactamente como DicapuaPublisher
        client = mqtt.Client(
            client_id=config.client_id + "_dicapua", 
            clean_session=True
        )
        
        # Configurar SSL/TLS exactamente como DicapuaPublisher
        if config.connectCerts:
            logger.info("🔐 Configurando SSL/TLS...")
            logger.info(f"  CA: {config.certs['ca_certs']}")
            logger.info(f"  Cert: {config.certs['certfile']}")
            logger.info(f"  Key: {config.certs['keyfile']}")
            
            # Verificar archivos
            for name, path in config.certs.items():
                if not Path(path).exists():
                    logger.error(f"❌ Archivo {name} no encontrado: {path}")
                    return False
            
            client.tls_set(
                ca_certs=config.certs["ca_certs"],
                certfile=config.certs["certfile"],
                keyfile=config.certs["keyfile"]
            )
            port = 8883
        else:
            client.username_pw_set(config.username, config.password)
            port = 1883
        
        # Configurar callbacks
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_publish = on_publish
        client.on_disconnect = on_disconnect
        
        # Conectar
        logger.info(f"🔗 Conectando a {config.broker}:{port} con client_id: {config.client_id}_dicapua")
        client.connect(config.broker, port, 60)
        
        # Iniciar loop
        client.loop_start()
        
        # Esperar conexión
        logger.info("⏳ Esperando conexión...")
        time.sleep(5)
        
        # Intentar enviar mensaje si estamos conectados
        if connection_successful:
            logger.info("📤 Enviando mensaje de prueba...")
            test_data = {
                "timestamp": "2025-01-29T20:00:00.000000Z",
                "markerZ": 0.78,
                "buttonX": 20.09,
                "marker": 7.098,
                "test": True
            }
            
            topic = config.topic.publish["YOLOframe"]["topic"]
            result = client.publish(topic, json.dumps(test_data))
            logger.info(f"📊 Datos enviados al topic: {topic}")
            logger.info(f"📋 Payload: {test_data}")
            
            # Esperar confirmación
            time.sleep(3)
        
        # Mantener conexión y monitorear
        logger.info("⏳ Monitoreando conexión por 15 segundos...")
        for i in range(15):
            time.sleep(1)
            if not connection_successful:
                logger.warning(f"💔 Conexión perdida en segundo {i+1}")
                break
            if i % 5 == 0:
                logger.info(f"💓 Conexión activa - segundo {i+1}/15")
        
        # Estadísticas finales
        logger.info("📊 Estadísticas finales:")
        logger.info(f"  Conexión exitosa: {'✅' if connection_successful else '❌'}")
        logger.info(f"  Publicación exitosa: {'✅' if publish_successful else '❌'}")
        logger.info(f"  Mensajes recibidos: {messages_received}")
        
        # Desconectar
        client.loop_stop()
        client.disconnect()
        
        return connection_successful and publish_successful
        
    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_network_connectivity():
    """Probar conectividad básica de red"""
    import socket
    
    logger.info("🌐 Probando conectividad de red...")
    
    # Probar resolución DNS
    try:
        ip = socket.gethostbyname("dicapuaiot.com")
        logger.info(f"✅ DNS resuelto: dicapuaiot.com -> {ip}")
    except Exception as e:
        logger.error(f"❌ Error DNS: {e}")
        return False
    
    # Probar conectividad TCP
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(("dicapuaiot.com", 8883))
        sock.close()
        
        if result == 0:
            logger.info("✅ Puerto 8883 accesible")
            return True
        else:
            logger.error(f"❌ Puerto 8883 no accesible: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Error conectividad TCP: {e}")
        return False

def main():
    """Función principal"""
    logger.info("🚀 Diagnóstico avanzado de conexión DicapuaIoT")
    logger.info("=" * 60)
    
    # Probar conectividad de red
    if not test_network_connectivity():
        logger.error("❌ Problemas de conectividad de red básica")
        return
    
    logger.info("=" * 60)
    
    # Probar conexión MQTT
    success = test_connection_with_exact_config()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ Diagnóstico completado - Conexión y publicación exitosas")
        logger.info("💡 El problema puede estar en el flujo de datos o timing")
    else:
        logger.info("❌ Diagnóstico completado - Problemas detectados")
        logger.info("💡 Revisar configuración de red, certificados o credenciales")

if __name__ == "__main__":
    main()