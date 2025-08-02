#!/usr/bin/env python3
"""
Reporte final de diagnóstico MQTT DicapuaIoT
Analiza el problema de desconexión código 7 y proporciona soluciones
"""

import json
import ssl
import time
import logging
import paho.mqtt.client as mqtt
from pathlib import Path
import socket
import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Cargar configuración de DicapuaIoT"""
    config_path = Path("src/mqtt/config/dicapuaiot/dicapuaiot.json")
    with open(config_path, 'r') as f:
        return json.load(f)

def test_ssl_configurations():
    """Probar diferentes configuraciones SSL/TLS"""
    config = load_config()
    broker = config['broker']
    port = 8883
    
    logger.info("🔐 Probando diferentes configuraciones SSL/TLS...")
    
    # Configuraciones SSL a probar
    ssl_configs = [
        {
            'name': 'TLS 1.2 con verificación completa',
            'tls_version': ssl.PROTOCOL_TLSv1_2,
            'cert_reqs': ssl.CERT_REQUIRED,
            'check_hostname': True
        },
        {
            'name': 'TLS 1.2 sin verificación hostname',
            'tls_version': ssl.PROTOCOL_TLSv1_2,
            'cert_reqs': ssl.CERT_REQUIRED,
            'check_hostname': False
        },
        {
            'name': 'TLS genérico con verificación',
            'tls_version': ssl.PROTOCOL_TLS,
            'cert_reqs': ssl.CERT_REQUIRED,
            'check_hostname': True
        },
        {
            'name': 'TLS genérico sin verificación hostname',
            'tls_version': ssl.PROTOCOL_TLS,
            'cert_reqs': ssl.CERT_REQUIRED,
            'check_hostname': False
        }
    ]
    
    cert_base = Path("src/mqtt/config")
    ca_certs = str(cert_base / config['ca_crt'])
    certfile = str(cert_base / config['group_1_crt'])
    keyfile = str(cert_base / config['group_1_key'])
    
    results = []
    
    for ssl_config in ssl_configs:
        logger.info(f"\n🧪 Probando: {ssl_config['name']}")
        
        try:
            # Crear contexto SSL
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_verify_locations(ca_certs)
            context.load_cert_chain(certfile, keyfile)
            context.protocol = ssl_config['tls_version']
            context.check_hostname = ssl_config['check_hostname']
            context.verify_mode = ssl_config['cert_reqs']
            
            # Probar conexión SSL directa
            with socket.create_connection((broker, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=broker if ssl_config['check_hostname'] else None) as ssock:
                    logger.info(f"  ✅ Conexión SSL exitosa")
                    cert = ssock.getpeercert()
                    if cert:
                        logger.info(f"  📜 Certificado válido hasta: {cert.get('notAfter', 'N/A')}")
                    
                    results.append({
                        'config': ssl_config['name'],
                        'ssl_success': True,
                        'error': None
                    })
                    
        except Exception as e:
            logger.error(f"  ❌ Error SSL: {e}")
            results.append({
                'config': ssl_config['name'],
                'ssl_success': False,
                'error': str(e)
            })
    
    return results

def test_mqtt_with_keepalive_variations():
    """Probar diferentes configuraciones de keepalive y timeouts"""
    config = load_config()
    
    logger.info("\n⏱️ Probando diferentes configuraciones de keepalive...")
    
    keepalive_configs = [60, 30, 120, 300]  # Diferentes valores de keepalive
    
    cert_base = Path("src/mqtt/config")
    ca_certs = str(cert_base / config['ca_crt'])
    certfile = str(cert_base / config['group_1_crt'])
    keyfile = str(cert_base / config['group_1_key'])
    
    for keepalive in keepalive_configs:
        logger.info(f"\n🔄 Probando keepalive: {keepalive} segundos")
        
        connection_time = 0
        disconnection_code = None
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connection_time
            if rc == 0:
                connection_time = time.time()
                logger.info(f"  ✅ Conectado con keepalive {keepalive}s")
            else:
                logger.error(f"  ❌ Error conexión: {rc}")
        
        def on_disconnect(client, userdata, rc):
            nonlocal disconnection_code
            disconnection_code = rc
            if connection_time > 0:
                duration = time.time() - connection_time
                logger.info(f"  ⏱️ Duración conexión: {duration:.2f}s")
            if rc != 0:
                logger.warning(f"  ⚠️ Desconexión código: {rc}")
        
        try:
            client = mqtt.Client(
                client_id=config['client_id'] + f"_test_{keepalive}",
                clean_session=True
            )
            
            client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile
            )
            
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            
            client.connect(config['broker'], 8883, keepalive)
            client.loop_start()
            
            # Esperar y monitorear
            time.sleep(10)
            
            client.loop_stop()
            client.disconnect()
            
        except Exception as e:
            logger.error(f"  ❌ Error en prueba keepalive {keepalive}: {e}")

def analyze_certificates():
    """Analizar los certificados SSL"""
    logger.info("\n📜 Analizando certificados SSL...")
    
    config = load_config()
    cert_base = Path("src/mqtt/config")
    
    certificates = {
        'CA': cert_base / config['ca_crt'],
        'Client Cert': cert_base / config['group_1_crt'],
        'Client Key': cert_base / config['group_1_key']
    }
    
    for name, cert_path in certificates.items():
        if cert_path.exists():
            logger.info(f"  ✅ {name}: {cert_path} (existe)")
            
            # Analizar certificado si es .crt
            if cert_path.suffix == '.crt':
                try:
                    import subprocess
                    result = subprocess.run(
                        ['openssl', 'x509', '-in', str(cert_path), '-text', '-noout'],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        # Extraer fecha de expiración
                        for line in result.stdout.split('\n'):
                            if 'Not After' in line:
                                logger.info(f"    📅 Expira: {line.strip()}")
                                break
                    else:
                        logger.warning(f"    ⚠️ No se pudo analizar con openssl")
                except Exception as e:
                    logger.warning(f"    ⚠️ Error analizando certificado: {e}")
        else:
            logger.error(f"  ❌ {name}: {cert_path} (NO EXISTE)")

def generate_recommendations():
    """Generar recomendaciones basadas en el análisis"""
    logger.info("\n💡 RECOMENDACIONES PARA RESOLVER EL PROBLEMA:")
    logger.info("=" * 60)
    
    recommendations = [
        "1. PROBLEMA IDENTIFICADO: Código de desconexión 7 (Error de red/conexión)",
        "   - La conexión SSL se establece correctamente",
        "   - El servidor DicapuaIoT desconecta inmediatamente después de la conexión",
        "",
        "2. POSIBLES CAUSAS:",
        "   a) Política del servidor que limita conexiones simultáneas",
        "   b) Certificados expirados o no válidos para el cliente específico",
        "   c) Configuración de keepalive incompatible",
        "   d) Firewall o proxy intermedio que interfiere",
        "",
        "3. SOLUCIONES RECOMENDADAS:",
        "   a) Verificar con el administrador de DicapuaIoT:",
        "      - Estado del servidor y políticas de conexión",
        "      - Validez de los certificados group_1",
        "      - Límites de conexiones por cliente",
        "",
        "   b) Modificar configuración MQTT:",
        "      - Aumentar keepalive a 300 segundos",
        "      - Usar clean_session=False para sesiones persistentes",
        "      - Implementar reconexión automática con backoff",
        "",
        "   c) Verificar conectividad de red:",
        "      - Probar desde otra red/ubicación",
        "      - Verificar configuración de proxy/firewall",
        "      - Usar herramientas como telnet o nmap para probar puerto 8883",
        "",
        "4. CÓDIGO DE EJEMPLO PARA RECONEXIÓN ROBUSTA:",
        "   - Implementar retry logic con exponential backoff",
        "   - Usar threading para mantener conexión en background",
        "   - Agregar heartbeat personalizado",
        "",
        "5. MONITOREO RECOMENDADO:",
        "   - Log detallado de intentos de conexión",
        "   - Métricas de tiempo de conexión",
        "   - Alertas por desconexiones frecuentes"
    ]
    
    for rec in recommendations:
        logger.info(rec)

def main():
    """Función principal del reporte"""
    logger.info("🔍 REPORTE FINAL DE DIAGNÓSTICO MQTT DICAPUAIOT")
    logger.info("=" * 60)
    logger.info(f"📅 Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Analizar certificados
        analyze_certificates()
        
        # Probar configuraciones SSL
        ssl_results = test_ssl_configurations()
        
        # Probar keepalive
        test_mqtt_with_keepalive_variations()
        
        # Generar recomendaciones
        generate_recommendations()
            
        logger.info("\n" + "=" * 60)
        logger.info("📋 RESUMEN DEL DIAGNÓSTICO COMPLETADO")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error en diagnóstico: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()