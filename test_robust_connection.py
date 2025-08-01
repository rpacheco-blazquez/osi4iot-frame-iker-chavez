#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión robusta a DicapuaIoT
con reconexión automática y reintentos
"""

import sys
import os
import time
import logging

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from mqtt.dicapua_publisher import DicapuaPublisher

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_robust_connection():
    """Prueba la conexión robusta con reconexión automática"""
    logger.info("🚀 Iniciando prueba de conexión robusta a DicapuaIoT")
    logger.info("=" * 60)
    
    try:
        # Crear instancia del publisher
        publisher = DicapuaPublisher()
        
        # Iniciar conexión en modo directo
        logger.info("📡 Iniciando conexión...")
        if publisher.start_client_direct_mode():
            logger.info("✅ Cliente iniciado, esperando conexión...")
            
            # Esperar conexión inicial
            for i in range(10):
                time.sleep(1)
                if publisher.dicapua_connected:
                    logger.info(f"✅ Conectado después de {i+1} segundos")
                    break
                logger.info(f"⏳ Esperando conexión... ({i+1}/10)")
            
            if not publisher.dicapua_connected:
                logger.warning("⚠️ No se pudo establecer conexión inicial")
                logger.info("🔄 Esperando reconexión automática...")
                
                # Esperar reconexión automática
                for i in range(30):
                    time.sleep(2)
                    if publisher.dicapua_connected:
                        logger.info(f"✅ Reconectado automáticamente después de {(i+1)*2} segundos")
                        break
                    if i % 5 == 0:
                        logger.info(f"⏳ Esperando reconexión... ({(i+1)*2}/60 segundos)")
            
            # Probar envío de datos si estamos conectados
            if publisher.dicapua_connected:
                logger.info("📤 Probando envío de datos...")
                
                # Simular datos de marcador
                marker_data = {
                    "distance_cm": 7.5,
                    "timestamp": time.time(),
                    "type": "marker"
                }
                
                # Simular datos de pórtico
                portico_data = {
                    "distance_cm": 22.3,
                    "timestamp": time.time(),
                    "source": "portico_pulsador"
                }
                
                # Enviar datos
                logger.info("📊 Enviando datos de marcador...")
                success1 = publisher.send_marker_distance(marker_data)
                logger.info(f"Resultado marcador: {'✅ Éxito' if success1 else '❌ Error'}")
                
                time.sleep(2)
                
                logger.info("📊 Enviando datos de pórtico...")
                success2 = publisher.send_distance_data(portico_data)
                logger.info(f"Resultado pórtico: {'✅ Éxito' if success2 else '❌ Error'}")
                
                # Monitorear conexión por un tiempo
                logger.info("🔍 Monitoreando conexión por 30 segundos...")
                for i in range(30):
                    time.sleep(1)
                    status = publisher.get_connection_status()
                    
                    if i % 10 == 0:
                        logger.info(f"📊 Estado: DicapuaIoT={status['dicapua_connected']}, Local={status['local_connected']}")
                    
                    # Si se desconecta, esperar reconexión
                    if not publisher.dicapua_connected:
                        logger.warning(f"💔 Conexión perdida en segundo {i+1}")
                        logger.info("🔄 Esperando reconexión automática...")
                        
                        # Esperar hasta 60 segundos para reconexión
                        for j in range(60):
                            time.sleep(1)
                            if publisher.dicapua_connected:
                                logger.info(f"✅ Reconectado automáticamente después de {j+1} segundos")
                                break
                        break
                
                # Probar envío directo
                if publisher.dicapua_connected:
                    logger.info("📤 Probando envío directo...")
                    success3 = publisher.publish_distance(15.7, 8.2)
                    logger.info(f"Resultado envío directo: {'✅ Éxito' if success3 else '❌ Error'}")
            
            else:
                logger.error("❌ No se pudo establecer conexión")
            
            # Mostrar estado final
            final_status = publisher.get_connection_status()
            logger.info("\n📋 ESTADO FINAL:")
            logger.info(f"  DicapuaIoT: {'✅ Conectado' if final_status['dicapua_connected'] else '❌ Desconectado'}")
            logger.info(f"  Local: {'✅ Conectado' if final_status['local_connected'] else '❌ Desconectado'}")
            
        else:
            logger.error("❌ Error iniciando cliente")
        
        # Detener cliente
        logger.info("🔌 Deteniendo cliente...")
        publisher.stop_client()
        logger.info("✅ Cliente detenido")
        
    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """Función principal"""
    test_robust_connection()

if __name__ == "__main__":
    main()