#!/usr/bin/env python3
"""
Script de monitoreo continuo para DicapuaIoT
Verifica la estabilidad de la conexión y el envío de datos
"""

import sys
import os
import time
import logging
import threading
import json
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from mqtt.dicapua_publisher import DicapuaPublisher

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dicapua_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DicapuaMonitor:
    """Monitor continuo de conexión DicapuaIoT"""
    
    def __init__(self):
        self.publisher = None
        self.running = False
        self.stats = {
            'total_attempts': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'disconnections': 0,
            'reconnections': 0,
            'start_time': None
        }
        
    def start_monitoring(self, duration_minutes=30):
        """Inicia el monitoreo por el tiempo especificado"""
        logger.info(f"🚀 Iniciando monitoreo DicapuaIoT por {duration_minutes} minutos")
        logger.info("=" * 70)
        
        self.stats['start_time'] = datetime.now()
        self.running = True
        
        try:
            # Crear publisher
            self.publisher = DicapuaPublisher()
            
            # Iniciar conexión
            if not self.publisher.start_client_direct_mode():
                logger.error("❌ Error iniciando cliente")
                return
            
            # Esperar conexión inicial
            logger.info("⏳ Esperando conexión inicial...")
            connected = self._wait_for_connection(timeout=30)
            
            if not connected:
                logger.error("❌ No se pudo establecer conexión inicial")
                return
            
            logger.info("✅ Conexión inicial establecida")
            
            # Iniciar hilo de envío de datos
            send_thread = threading.Thread(target=self._data_sender, daemon=True)
            send_thread.start()
            
            # Monitorear por el tiempo especificado
            end_time = time.time() + (duration_minutes * 60)
            last_status_check = 0
            
            while time.time() < end_time and self.running:
                current_time = time.time()
                
                # Verificar estado cada 30 segundos
                if current_time - last_status_check >= 30:
                    self._check_connection_status()
                    last_status_check = current_time
                
                time.sleep(5)
            
            logger.info("⏰ Tiempo de monitoreo completado")
            
        except KeyboardInterrupt:
            logger.info("⚠️ Monitoreo interrumpido por usuario")
        except Exception as e:
            logger.error(f"❌ Error en monitoreo: {e}")
        finally:
            self.running = False
            self._cleanup()
            self._print_final_stats()
    
    def _wait_for_connection(self, timeout=30):
        """Espera a que se establezca la conexión"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.publisher and self.publisher.dicapua_connected:
                return True
            time.sleep(1)
        return False
    
    def _data_sender(self):
        """Hilo que envía datos periódicamente"""
        logger.info("📤 Iniciando envío periódico de datos")
        
        while self.running:
            try:
                if self.publisher and self.publisher.dicapua_connected:
                    # Generar datos simulados
                    marker_distance = 5.0 + (time.time() % 10)  # 5-15 cm
                    portico_distance = 15.0 + (time.time() % 20)  # 15-35 cm
                    
                    # Enviar datos de marcador
                    marker_data = {
                        "distance_cm": round(marker_distance, 2),
                        "timestamp": time.time(),
                        "type": "marker"
                    }
                    
                    # Enviar datos de pórtico
                    portico_data = {
                        "distance_cm": round(portico_distance, 2),
                        "timestamp": time.time(),
                        "source": "portico_pulsador"
                    }
                    
                    self.stats['total_attempts'] += 1
                    
                    # Enviar marcador
                    success1 = self.publisher.send_marker_distance(marker_data)
                    time.sleep(1)
                    
                    # Enviar pórtico
                    success2 = self.publisher.send_distance_data(portico_data)
                    
                    if success1 and success2:
                        self.stats['successful_sends'] += 1
                        logger.info(f"✅ Datos enviados: marker={marker_distance:.2f}cm, portico={portico_distance:.2f}cm")
                    else:
                        self.stats['failed_sends'] += 1
                        logger.warning(f"⚠️ Error enviando datos: marker={success1}, portico={success2}")
                
                else:
                    logger.warning("⚠️ No conectado, esperando...")
                    time.sleep(5)
                
                # Esperar antes del siguiente envío
                time.sleep(15)  # Enviar cada 15 segundos
                
            except Exception as e:
                logger.error(f"❌ Error en envío de datos: {e}")
                self.stats['failed_sends'] += 1
                time.sleep(10)
    
    def _check_connection_status(self):
        """Verifica el estado de la conexión"""
        if not self.publisher:
            return
        
        status = self.publisher.get_connection_status()
        
        # Detectar desconexiones
        if not status['dicapua_connected']:
            self.stats['disconnections'] += 1
            logger.warning("💔 Desconexión detectada")
            
            # Esperar reconexión
            logger.info("🔄 Esperando reconexión automática...")
            if self._wait_for_connection(timeout=60):
                self.stats['reconnections'] += 1
                logger.info("✅ Reconexión exitosa")
            else:
                logger.error("❌ Reconexión falló")
        
        # Log de estado periódico
        uptime = datetime.now() - self.stats['start_time']
        success_rate = (self.stats['successful_sends'] / max(1, self.stats['total_attempts'])) * 100
        
        logger.info(f"📊 Estado: Conectado={status['dicapua_connected']}, "
                   f"Uptime={str(uptime).split('.')[0]}, "
                   f"Éxito={success_rate:.1f}% ({self.stats['successful_sends']}/{self.stats['total_attempts']})")
    
    def _cleanup(self):
        """Limpia recursos"""
        if self.publisher:
            logger.info("🔌 Deteniendo cliente...")
            self.publisher.stop_client()
            logger.info("✅ Cliente detenido")
    
    def _print_final_stats(self):
        """Imprime estadísticas finales"""
        if not self.stats['start_time']:
            return
        
        duration = datetime.now() - self.stats['start_time']
        success_rate = (self.stats['successful_sends'] / max(1, self.stats['total_attempts'])) * 100
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 ESTADÍSTICAS FINALES DEL MONITOREO")
        logger.info("=" * 70)
        logger.info(f"⏰ Duración total: {str(duration).split('.')[0]}")
        logger.info(f"📤 Intentos de envío: {self.stats['total_attempts']}")
        logger.info(f"✅ Envíos exitosos: {self.stats['successful_sends']}")
        logger.info(f"❌ Envíos fallidos: {self.stats['failed_sends']}")
        logger.info(f"📈 Tasa de éxito: {success_rate:.1f}%")
        logger.info(f"💔 Desconexiones: {self.stats['disconnections']}")
        logger.info(f"🔄 Reconexiones: {self.stats['reconnections']}")
        
        if self.stats['disconnections'] > 0:
            avg_uptime = duration.total_seconds() / (self.stats['disconnections'] + 1)
            logger.info(f"⏱️ Tiempo promedio entre desconexiones: {avg_uptime:.1f} segundos")
        
        logger.info("=" * 70)
        
        # Guardar estadísticas en archivo
        stats_file = f"dicapua_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w') as f:
            stats_data = self.stats.copy()
            stats_data['start_time'] = stats_data['start_time'].isoformat()
            stats_data['end_time'] = datetime.now().isoformat()
            stats_data['duration_seconds'] = duration.total_seconds()
            stats_data['success_rate'] = success_rate
            json.dump(stats_data, f, indent=2)
        
        logger.info(f"📁 Estadísticas guardadas en: {stats_file}")

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor de conexión DicapuaIoT')
    parser.add_argument('--duration', type=int, default=30, 
                       help='Duración del monitoreo en minutos (default: 30)')
    
    args = parser.parse_args()
    
    monitor = DicapuaMonitor()
    monitor.start_monitoring(duration_minutes=args.duration)

if __name__ == "__main__":
    main()