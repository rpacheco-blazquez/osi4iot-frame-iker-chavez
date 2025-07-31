"""Punto de entrada principal del sistema de gemelo digital del pórtico."""

import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

# Agregar el directorio src al path para imports
sys.path.append(str(Path(__file__).parent))

# Imports de módulos del proyecto
from utils.helpers import Logger, ConfigManager, PerformanceMonitor
from vision.detector import YOLOPoseDetector
from vision.tracker import ObjectTracker
from mqtt.dicapua_publisher import DicapuaPublisher
from postprocess.distance_calculator import DistanceCalculator
from postprocess.marker_distance_calculator import MarkerDistanceCalculator
from visualization.visualizer import GantryVisualizer

# Dataclasses para datos
from dataclasses import dataclass
from typing import Optional

@dataclass
class ForceData:
    """Datos de fuerza para compatibilidad."""
    object_id: str
    force_x: float
    force_y: float
    force_z: float
    magnitude: float
    timestamp: str
    position_x: float
    position_y: float
    position_z: float

@dataclass
class PositionData:
    """Datos de posición."""
    object_id: str
    x: float
    y: float
    z: float
    velocity_x: float
    velocity_y: float
    velocity_z: float
    timestamp: str

class DigitalTwinSystem:
    """Sistema principal del gemelo digital del pórtico."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Inicializa el sistema de gemelo digital.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        # Configuración y logging
        self.config_manager = ConfigManager(config_path)
        self.logger = Logger("DigitalTwinSystem")
        self.performance_monitor = PerformanceMonitor()
        
        # Componentes del sistema
        self.detector = None
        self.tracker = None
        self.distance_calculator = None
        self.marker_distance_calculator = None
        self.mqtt_publisher = None
        self.visualizer = None
        
        # Estado del sistema
        self.running = False
        self.initialized = False
        
        self.logger.info("Sistema de gemelo digital inicializado")
    
    def initialize_components(self) -> bool:
        """Inicializa todos los componentes del sistema.
        
        Returns:
            True si la inicialización fue exitosa
        """
        try:
            self.logger.info("Inicializando componentes del sistema...")
            
            # Inicializar detector de visión
            self.performance_monitor.start_timer("detector_init")
            self.detector = YOLOPoseDetector(config_path="config/config.yaml")
            if not self.detector.load_model():
                self.logger.warning("No se pudo cargar el modelo YOLO, usando modo simulación")
            self.performance_monitor.end_timer("detector_init")
            
            # Inicializar tracker
            self.tracker = ObjectTracker()
            
            # Inicializar calculadores de distancia
            self.distance_calculator = DistanceCalculator(enable_mqtt=False)
            self.marker_distance_calculator = MarkerDistanceCalculator(enable_mqtt=False)
            
            # Inicializar publicador MQTT
            self.mqtt_publisher = DicapuaPublisher()
            if self.config_manager.get('communication.mqtt.enabled', True):
                try:
                    # Configurar calculadores con el publisher
                    self.distance_calculator.set_dicapua_publisher(self.mqtt_publisher)
                    self.marker_distance_calculator.set_dicapua_publisher(self.mqtt_publisher)
                    
                    # Conectar MQTT
                    self.mqtt_publisher.connect_dicapua_mqtt()
                    self.logger.info("Conexión MQTT establecida")
                except Exception as e:
                    self.logger.warning(f"No se pudo conectar a MQTT: {e}")
            
            # Inicializar visualizador
            if self.config_manager.get('visualization.enabled', True):
                self.visualizer = GantryVisualizer(config_path="config/config.yaml")
                self.visualizer.setup_2d_view()
                if self.config_manager.get('visualization.3d_enabled', True):
                    self.visualizer.setup_3d_view()
                self.visualizer.setup_force_plots()
                
                # Dibujar estructura del pórtico
                gantry_dimensions = self.config_manager.get('gantry.dimensions', {
                    'length': 10.0,
                    'width': 8.0,
                    'height': 6.0,
                    'beam_width': 0.3
                })
                
                for ax_name, ax in self.visualizer.axes.items():
                    if ax_name != 'trajectory' and ax_name != '3d':
                        self.visualizer.draw_gantry_structure(ax, gantry_dimensions)
                
                if '3d' in self.visualizer.axes:
                    self.visualizer.draw_gantry_structure(self.visualizer.axes['3d'], gantry_dimensions)
                
                self.logger.info("Visualizador inicializado")
            
            self.initialized = True
            self.logger.info("Todos los componentes inicializados exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al inicializar componentes: {e}")
            return False
    
    def start_system(self):
        """Inicia el sistema de gemelo digital."""
        if not self.initialized:
            if not self.initialize_components():
                self.logger.error("No se pudo inicializar el sistema")
                return
        
        self.logger.info("Iniciando sistema de gemelo digital...")
        self.running = True
        
        try:
            # Iniciar visualización en tiempo real si está habilitada
            if self.visualizer and self.config_manager.get('visualization.real_time_plots', True):
                self.visualizer.start_real_time_update()
                self.visualizer.create_animation()
            
            # Publicar estado inicial
            if self.mqtt_publisher:
                try:
                    status_data = {
                        'system_status': 'running',
                        'timestamp': datetime.now().isoformat(),
                        'components': {
                            'detector': 'active' if self.detector else 'inactive',
                            'tracker': 'active' if self.tracker else 'inactive',
                            'distance_calculator': 'active' if self.distance_calculator else 'inactive',
                            'marker_distance_calculator': 'active' if self.marker_distance_calculator else 'inactive',
                            'visualizer': 'active' if self.visualizer else 'inactive'
                        }
                    }
                    # Usar el método disponible en DicapuaPublisher
                    self.mqtt_publisher.publish_distance_data(status_data)
                except Exception as e:
                    self.logger.warning(f"No se pudo publicar estado inicial: {e}")
            
            self.logger.info("Sistema iniciado exitosamente")
            
            # Mostrar visualización si está habilitada
            if self.visualizer:
                self.visualizer.show_all()
            
        except Exception as e:
            self.logger.error(f"Error al iniciar el sistema: {e}")
            self.stop_system()
    
    def stop_system(self):
        """Detiene el sistema de gemelo digital."""
        self.logger.info("Deteniendo sistema de gemelo digital...")
        self.running = False
        
        try:
            # Detener visualización
            if self.visualizer:
                self.visualizer.stop_real_time_update()
                self.visualizer.close_all()
            
            # Desconectar MQTT
            if self.mqtt_publisher:
                try:
                    # Publicar estado final
                    status_data = {
                        'system_status': 'stopped',
                        'timestamp': datetime.now().isoformat()
                    }
                    self.mqtt_publisher.publish_distance_data(status_data)
                    
                    # Desconectar
                    self.mqtt_publisher.disconnect_dicapua_mqtt()
                except Exception as e:
                    self.logger.warning(f"Error al desconectar MQTT: {e}")
            
            # Mostrar estadísticas de rendimiento
            stats = self.performance_monitor.get_all_statistics()
            if stats:
                self.logger.info("Estadísticas de rendimiento:")
                for operation, data in stats.items():
                    self.logger.info(f"  {operation}: {data}")
            
            self.logger.info("Sistema detenido exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error al detener el sistema: {e}")
    
    def process_frame(self, frame, timestamp: datetime = None):
        """Procesa un frame de video/imagen.
        
        Args:
            frame: Frame de imagen (numpy array)
            timestamp: Timestamp del frame
        """
        if not self.running or not self.initialized:
            return
        
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            self.performance_monitor.start_timer("frame_processing")
            
            # Detección de objetos
            detections = self.detector.get_detections_data(frame)
            
            # Tracking de objetos
            tracked_objects = self.tracker.update(detections, frame)
            
            # Cálculo de distancias para cada objeto trackeado
            for object_id, obj_info in tracked_objects.items():
                centroid = obj_info['centroid']
                position_3d = (centroid[0], centroid[1], 0)  # Asumir z=0 para 2D
                
                # Calcular distancias usando los calculadores
                distance_result = self.distance_calculator.calculate_distances(frame, [obj_info])
                marker_distance_result = self.marker_distance_calculator.calculate_distances(frame, [obj_info])
                
                # Publicar datos si MQTT está conectado
                if self.mqtt_publisher:
                    try:
                        position_data = PositionData(
                            object_id=object_id,
                            x=position_3d[0],
                            y=position_3d[1],
                            z=position_3d[2],
                            velocity_x=0.0,  # Calcular velocidad si es necesario
                            velocity_y=0.0,
                            velocity_z=0.0,
                            timestamp=timestamp.isoformat()
                        )
                        
                        # Publicar datos de posición
                        self.mqtt_publisher.publish_position_data(position_data)
                        
                        # Publicar datos de distancia si están disponibles
                        if distance_result:
                            self.mqtt_publisher.publish_distance_data(distance_result)
                        
                    except Exception as e:
                        self.logger.warning(f"Error publicando datos MQTT: {e}")
                
                # Actualizar visualización
                if self.visualizer:
                    self.visualizer.update_load_position(position_3d)
                    
                    # Actualizar datos de distancia en visualización
                    if distance_result:
                        distance_dict = {
                            'distance': distance_result
                        }
                        try:
                            self.visualizer.update_distances(distance_dict)
                        except AttributeError:
                            # Método no disponible, usar alternativo
                            self.visualizer.update_load_position(position_3d, load_mass=10.0)
            
            self.performance_monitor.end_timer("frame_processing")
            
        except Exception as e:
            self.logger.error(f"Error al procesar frame: {e}")
    
    def run_demo_mode(self):
        """Ejecuta el sistema en modo demostración con datos simulados."""
        self.logger.info("Ejecutando en modo demostración...")
        
        import numpy as np
        import time
        
        # Simular movimiento de carga
        t = 0
        dt = 1.0 / 30.0  # 30 FPS
        
        try:
            while self.running:
                # Generar posición simulada (movimiento circular)
                x = 5 + 3 * np.cos(t * 0.5)
                y = 4 + 2 * np.sin(t * 0.5)
                z = 3 + 0.5 * np.sin(t * 2)
                
                # Crear frame simulado
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # Simular detección
                simulated_detection = {
                    'bbox': [int(x*50), int(y*50), int(x*50)+50, int(y*50)+50],
                    'confidence': 0.9,
                    'class_name': 'load'
                }
                
                # Procesar como si fuera un frame real
                self.process_frame(frame, datetime.now())
                
                # Actualizar visualización directamente con posición simulada
                if self.visualizer:
                    self.visualizer.update_load_position((x, y, z), load_mass=10.0)
                
                t += dt
                time.sleep(dt)
                
        except KeyboardInterrupt:
            self.logger.info("Demostración interrumpida por el usuario")
        except Exception as e:
            self.logger.error(f"Error en modo demostración: {e}")
    
    def get_system_status(self) -> dict:
        """Obtiene el estado actual del sistema.
        
        Returns:
            Diccionario con el estado del sistema
        """
        mqtt_connected = False
        try:
            mqtt_connected = self.mqtt_publisher is not None
        except:
            mqtt_connected = False
            
        return {
            'running': self.running,
            'initialized': self.initialized,
            'components': {
                'detector': self.detector is not None,
                'tracker': self.tracker is not None,
                'distance_calculator': self.distance_calculator is not None,
                'marker_distance_calculator': self.marker_distance_calculator is not None,
                'mqtt_publisher': mqtt_connected,
                'visualizer': self.visualizer is not None
            },
            'performance': self.performance_monitor.get_all_statistics()
        }

def main():
    """Función principal del programa."""
    parser = argparse.ArgumentParser(description='Sistema de Gemelo Digital del Pórtico')
    parser.add_argument('--config', '-c', default='config/config.yaml',
                       help='Ruta al archivo de configuración')
    parser.add_argument('--demo', '-d', action='store_true',
                       help='Ejecutar en modo demostración')
    parser.add_argument('--no-viz', action='store_true',
                       help='Deshabilitar visualización')
    parser.add_argument('--no-mqtt', action='store_true',
                       help='Deshabilitar comunicación MQTT')
    
    args = parser.parse_args()
    
    # Crear sistema
    system = DigitalTwinSystem(args.config)
    
    # Aplicar configuraciones de línea de comandos
    if args.no_viz:
        system.config_manager.set('visualization.enabled', False)
    
    if args.no_mqtt:
        system.config_manager.set('communication.mqtt.enabled', False)
    
    try:
        # Inicializar y arrancar sistema
        system.start_system()
        
        if args.demo:
            # Ejecutar en modo demostración
            system.run_demo_mode()
        else:
            # Modo normal - esperar entrada del usuario
            print("Sistema iniciado. Presiona Ctrl+C para detener.")
            print("Estado del sistema:")
            status = system.get_system_status()
            for key, value in status.items():
                print(f"  {key}: {value}")
            
            # Mantener el sistema corriendo
            try:
                while system.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nDeteniendo sistema...")
    
    except Exception as e:
        print(f"Error fatal: {e}")
    
    finally:
        # Asegurar que el sistema se detenga correctamente
        system.stop_system()

if __name__ == "__main__":
    main()