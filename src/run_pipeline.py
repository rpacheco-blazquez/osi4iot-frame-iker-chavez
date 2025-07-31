"""Pipeline de procesamiento para el gemelo digital del pórtico.

Este módulo maneja el flujo completo de datos:
captura -> detección -> tracking -> cálculo de distancias -> visualización -> comunicación
"""

import cv2
import numpy as np
import time
import threading
from queue import Queue, Empty
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
import sys
from dataclasses import dataclass

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent))

from utils.helpers import Logger, ConfigManager, PerformanceMonitor, DataManager
from vision.detector import YOLOPoseDetector
from vision.tracker import ObjectTracker
from visualization.visualizer import GantryVisualizer
from mqtt.dicapua_publisher import DicapuaPublisher
from postprocess.distance_calculator import DistanceCalculator
from postprocess.marker_distance_calculator import MarkerDistanceCalculator

@dataclass
class ForceData:
    """Estructura de datos para fuerzas."""
    object_id: int
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
    """Estructura de datos para posiciones."""
    object_id: int
    x: float
    y: float
    z: float
    velocity_x: float
    velocity_y: float
    velocity_z: float
    timestamp: str

@dataclass
class ObjectState:
    """Estado de un objeto trackeado."""
    position: tuple
    velocity: tuple
    acceleration: tuple
    timestamp: datetime

@dataclass
class Force:
    """Representación de una fuerza 3D."""
    x: float
    y: float
    z: float
    
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

class ProcessingPipeline:
    """Pipeline principal de procesamiento de datos."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Inicializa el pipeline de procesamiento.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        # Configuración y utilidades
        self.config_manager = ConfigManager(config_path)
        self.logger = Logger("ProcessingPipeline")
        self.performance_monitor = PerformanceMonitor()
        self.data_manager = DataManager()
        
        # Componentes del pipeline
        self.detector = YOLOPoseDetector(config_path)
        self.tracker = ObjectTracker()
        self.visualizer = GantryVisualizer(config_path)
        
        # Componentes de comunicación y cálculo
        self.mqtt_publisher = DicapuaPublisher()
        self.distance_calculator = DistanceCalculator(enable_mqtt=False)
        self.marker_distance_calculator = MarkerDistanceCalculator(enable_mqtt=False)
        
        # Colas para procesamiento asíncrono
        self.frame_queue = Queue(maxsize=10)
        self.detection_queue = Queue(maxsize=20)
        self.distance_queue = Queue(maxsize=20)
        
        # Threads de procesamiento
        self.capture_thread = None
        self.detection_thread = None
        self.tracking_thread = None
        self.distance_thread = None
        self.visualization_thread = None
        
        # Estado del pipeline
        self.running = False
        self.paused = False
        
        # Fuente de video
        self.video_source = None
        self.video_capture = None
        
        # Callbacks para eventos
        self.frame_callback = None
        self.detection_callback = None
        self.tracking_callback = None
        self.distance_callback = None
        
        # Estadísticas
        self.frame_count = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        
        # Estados de objetos para simulación de fuerzas
        self.object_states = {}
        
        self.logger.info("Pipeline de procesamiento inicializado")
    
    def initialize(self) -> bool:
        """Inicializa todos los componentes del pipeline.
        
        Returns:
            True si la inicialización fue exitosa
        """
        try:
            self.logger.info("Inicializando componentes del pipeline...")
            
            # Inicializar detector
            if not self.detector.load_model():
                self.logger.warning("Modelo YOLO no disponible, usando detección simulada")
            
            # Inicializar comunicación MQTT
            if self.config_manager.get('communication.mqtt.enabled', True):
                try:
                    # Configurar calculadores de distancia con el publisher
                    self.distance_calculator.set_dicapua_publisher(self.mqtt_publisher)
                    self.marker_distance_calculator.set_dicapua_publisher(self.mqtt_publisher)
                    
                    # Inicializar conexión MQTT
                    self.mqtt_publisher.connect_dicapua_mqtt()
                    self.logger.info("MQTT conectado y listo")
                except Exception as e:
                    self.logger.warning(f"No se pudo conectar a MQTT: {e}")
            
            # Inicializar visualización
            if self.config_manager.get('visualization.enabled', True):
                self.visualizer.setup_2d_view()
                self.visualizer.setup_3d_view()
                self.visualizer.setup_force_plots()
                self.logger.info("Visualización inicializada")
            
            self.logger.info("Pipeline inicializado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al inicializar pipeline: {e}")
            return False
    
    def set_video_source(self, source):
        """Establece la fuente de video.
        
        Args:
            source: Fuente de video (int para cámara, str para archivo)
        """
        self.video_source = source
        self.logger.info(f"Fuente de video establecida: {source}")
    
    def start_capture(self) -> bool:
        """Inicia la captura de video.
        
        Returns:
            True si la captura se inició exitosamente
        """
        try:
            if self.video_source is None:
                self.video_source = self.config_manager.get('vision.video_source', 0)
            
            self.video_capture = cv2.VideoCapture(self.video_source)
            
            if not self.video_capture.isOpened():
                self.logger.error(f"No se pudo abrir la fuente de video: {self.video_source}")
                return False
            
            # Configurar propiedades de captura
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.video_capture.set(cv2.CAP_PROP_FPS, 30)
            
            self.logger.info("Captura de video iniciada")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al iniciar captura: {e}")
            return False
    
    def stop_capture(self):
        """Detiene la captura de video."""
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
            self.logger.info("Captura de video detenida")
    
    def capture_worker(self):
        """Worker thread para captura de frames."""
        self.logger.info("Iniciando worker de captura")
        
        while self.running:
            try:
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                if not self.video_capture or not self.video_capture.isOpened():
                    time.sleep(0.1)
                    continue
                
                ret, frame = self.video_capture.read()
                
                if not ret:
                    self.logger.warning("No se pudo leer frame")
                    time.sleep(0.1)
                    continue
                
                timestamp = datetime.now()
                
                # Agregar frame a la cola si hay espacio
                try:
                    self.frame_queue.put((frame, timestamp), timeout=0.01)
                    self.frame_count += 1
                    
                    # Calcular FPS
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 1.0:
                        self.fps_counter = self.frame_count
                        self.frame_count = 0
                        self.last_fps_time = current_time
                    
                except:
                    # Cola llena, descartar frame
                    pass
                
            except Exception as e:
                self.logger.error(f"Error en captura: {e}")
                time.sleep(0.1)
    
    def detection_worker(self):
        """Worker thread para detección de objetos."""
        self.logger.info("Iniciando worker de detección")
        
        while self.running:
            try:
                # Obtener frame de la cola
                frame, timestamp = self.frame_queue.get(timeout=1.0)
                
                if self.paused:
                    continue
                
                self.performance_monitor.start_timer("detection")
                
                # Realizar detección
                detections = self.detector.get_detections_data(frame)
                
                # Dibujar detecciones en el frame
                annotated_frame = self.detector.draw_detections(frame, detections)
                
                detection_time = self.performance_monitor.end_timer("detection")
                
                # Enviar a cola de tracking
                detection_data = {
                    'frame': annotated_frame,
                    'detections': detections,
                    'timestamp': timestamp,
                    'processing_time': detection_time
                }
                
                try:
                    self.detection_queue.put(detection_data, timeout=0.01)
                except:
                    # Cola llena, descartar
                    pass
                
                # Callback si está definido
                if self.detection_callback:
                    self.detection_callback(detection_data)
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error en detección: {e}")
    
    def tracking_worker(self):
        """Worker thread para tracking de objetos."""
        self.logger.info("Iniciando worker de tracking")
        
        while self.running:
            try:
                # Obtener datos de detección
                detection_data = self.detection_queue.get(timeout=1.0)
                
                if self.paused:
                    continue
                
                self.performance_monitor.start_timer("tracking")
                
                # Realizar tracking
                tracked_objects = self.tracker.update(detection_data['detections'])
                
                # Dibujar tracks en el frame
                tracked_frame = self.tracker.draw_tracks(
                    detection_data['frame'], tracked_objects
                )
                
                tracking_time = self.performance_monitor.end_timer("tracking")
                
                # Preparar datos para cálculo de distancias
                tracking_data = {
                    'frame': tracked_frame,
                    'tracked_objects': tracked_objects,
                    'timestamp': detection_data['timestamp'],
                    'detection_time': detection_data['processing_time'],
                    'tracking_time': tracking_time
                }
                
                try:
                    self.distance_queue.put(tracking_data, timeout=0.01)
                except:
                    # Cola llena, descartar
                    pass
                
                # Callback si está definido
                if self.tracking_callback:
                    self.tracking_callback(tracking_data)
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error en tracking: {e}")
    
    def distance_calculation_worker(self):
        """Worker thread para cálculo de distancias."""
        self.logger.info("Iniciando worker de cálculo de distancias")
        
        while self.running:
            try:
                # Obtener datos de tracking
                tracking_data = self.distance_queue.get(timeout=1.0)
                
                if self.paused:
                    continue
                
                self.performance_monitor.start_timer("distance_calculation")
                
                distances_data = {}
                
                # Calcular distancias para cada objeto trackeado
                for object_id, obj_info in tracking_data['tracked_objects'].items():
                    centroid = obj_info['centroid']
                    
                    # Convertir a coordenadas 3D (asumir z=0 para 2D)
                    position_3d = (centroid[0], centroid[1], 0.0)
                    
                    # Calcular distancias usando los calculadores
                    distance_result = self.distance_calculator.calculate_distances(
                        tracking_data['frame'], [obj_info]
                    )
                    
                    marker_distance_result = self.marker_distance_calculator.calculate_distances(
                        tracking_data['frame'], [obj_info]
                    )
                    
                    distances_data[object_id] = {
                        'position_3d': position_3d,
                        'distance_result': distance_result,
                        'marker_distance_result': marker_distance_result
                    }
                
                distance_time = self.performance_monitor.end_timer("distance_calculation")
                
                # Preparar datos finales
                final_data = {
                    'frame': tracking_data['frame'],
                    'distances_data': distances_data,
                    'timestamp': tracking_data['timestamp'],
                    'processing_times': {
                        'detection': tracking_data['detection_time'],
                        'tracking': tracking_data['tracking_time'],
                        'distance_calculation': distance_time
                    }
                }
                
                # Publicar datos via MQTT
                self._publish_mqtt_data(final_data)
                
                # Actualizar visualización
                self._update_visualization(final_data)
                
                # Guardar datos si está configurado
                if self.config_manager.get('data.save_processed_data', True):
                    self._save_processed_data(final_data)
                
                # Callback si está definido
                if self.distance_callback:
                    self.distance_callback(final_data)
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error en cálculo de distancias: {e}")
    
    def _publish_mqtt_data(self, data: Dict[str, Any]):
        """Publica datos via MQTT."""
        if not self.mqtt_publisher or not self.mqtt_publisher.is_connected():
            return
        
        try:
            for object_id, obj_data in data['distances_data'].items():
                position = obj_data['position_3d']
                distance_result = obj_data['distance_result']
                
                # Datos de posición
                position_data = PositionData(
                    object_id=object_id,
                    x=position[0],
                    y=position[1],
                    z=position[2],
                    velocity_x=0.0,  # Calcular velocidad si es necesario
                    velocity_y=0.0,
                    velocity_z=0.0,
                    timestamp=data['timestamp'].isoformat()
                )
                
                self.mqtt_publisher.publish_position_data(position_data)
                
                # Publicar datos de distancia si están disponibles
                if distance_result:
                    self.mqtt_publisher.publish_distance_data(distance_result)
        
        except Exception as e:
            self.logger.error(f"Error al publicar datos MQTT: {e}")
    
    def _update_visualization(self, data: Dict[str, Any]):
        """Actualiza la visualización."""
        if not self.visualizer:
            return
        
        try:
            for object_id, obj_data in data['distances_data'].items():
                position = obj_data['position_3d']
                
                # Actualizar posición de la carga
                self.visualizer.update_load_position(position)
                
                # Actualizar datos de distancia si están disponibles
                if obj_data.get('distance_result'):
                    distance_dict = {
                        'distance': obj_data['distance_result']
                    }
                    self.visualizer.update_distances(distance_dict)
        
        except Exception as e:
            self.logger.error(f"Error al actualizar visualización: {e}")
    
    def _save_processed_data(self, data: Dict[str, Any]):
        """Guarda datos procesados."""
        try:
            # Preparar datos para guardar
            save_data = {
                'timestamp': data['timestamp'].isoformat(),
                'processing_times': data['processing_times'],
                'objects': {}
            }
            
            for object_id, obj_data in data['distances_data'].items():
                position = obj_data['position_3d']
                distance_result = obj_data.get('distance_result', {})
                marker_distance_result = obj_data.get('marker_distance_result', {})
                
                save_data['objects'][str(object_id)] = {
                    'position': position,
                    'distance_result': distance_result,
                    'marker_distance_result': marker_distance_result
                }
            
            # Guardar con timestamp en el nombre
            filename = f"processed_data_{data['timestamp'].strftime('%Y%m%d_%H%M%S_%f')}"
            self.data_manager.save_json(save_data, filename)
        
        except Exception as e:
            self.logger.error(f"Error al guardar datos: {e}")
    
    def start_pipeline(self) -> bool:
        """Inicia el pipeline completo.
        
        Returns:
            True si el pipeline se inició exitosamente
        """
        if self.running:
            self.logger.warning("Pipeline ya está ejecutándose")
            return True
        
        try:
            self.logger.info("Iniciando pipeline de procesamiento...")
            
            # Inicializar componentes
            if not self.initialize():
                return False
            
            # Iniciar captura de video
            if not self.start_capture():
                return False
            
            self.running = True
            
            # Iniciar threads de procesamiento
            self.capture_thread = threading.Thread(target=self.capture_worker, daemon=True)
            self.detection_thread = threading.Thread(target=self.detection_worker, daemon=True)
            self.tracking_thread = threading.Thread(target=self.tracking_worker, daemon=True)
            self.distance_thread = threading.Thread(target=self.distance_calculation_worker, daemon=True)
            
            self.capture_thread.start()
            self.detection_thread.start()
            self.tracking_thread.start()
            self.distance_thread.start()
            
            # Iniciar visualización en tiempo real
            if self.visualizer:
                self.visualizer.start_real_time_update()
                # Mostrar las ventanas de visualización
                self.visualizer.show_all()
            
            self.logger.info("Pipeline iniciado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al iniciar pipeline: {e}")
            self.stop_pipeline()
            return False
    
    def stop_pipeline(self):
        """Detiene el pipeline completo."""
        self.logger.info("Deteniendo pipeline...")
        
        self.running = False
        
        # Detener captura
        self.stop_capture()
        
        # Detener visualización
        if self.visualizer:
            self.visualizer.stop_real_time_update()
        
        # Desconectar MQTT
        if self.mqtt_publisher:
            self.mqtt_publisher.disconnect()
        
        # Esperar a que terminen los threads
        threads = [self.capture_thread, self.detection_thread, 
                  self.tracking_thread, self.distance_thread]
        
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=2)
        
        # Mostrar estadísticas finales
        stats = self.performance_monitor.get_all_statistics()
        self.logger.info("Estadísticas del pipeline:")
        for operation, data in stats.items():
            self.logger.info(f"  {operation}: {data}")
        
        self.logger.info("Pipeline detenido")
    
    def pause_pipeline(self):
        """Pausa el procesamiento."""
        self.paused = True
        self.logger.info("Pipeline pausado")
    
    def resume_pipeline(self):
        """Reanuda el procesamiento."""
        self.paused = False
        self.logger.info("Pipeline reanudado")
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Obtiene el estado del pipeline.
        
        Returns:
            Diccionario con el estado del pipeline
        """
        return {
            'running': self.running,
            'paused': self.paused,
            'fps': self.fps_counter,
            'queue_sizes': {
                'frames': self.frame_queue.qsize(),
                'detections': self.detection_queue.qsize(),
                'distances': self.distance_queue.qsize()
            },
            'performance': self.performance_monitor.get_all_statistics()
        }

def main():
    """Función principal para ejecutar el pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pipeline de Procesamiento del Gemelo Digital')
    parser.add_argument('--config', '-c', default='config/config.yaml',
                       help='Ruta al archivo de configuración')
    parser.add_argument('--source', '-s', default=None,
                       help='Fuente de video (cámara o archivo)')
    parser.add_argument('--output', '-o', default=None,
                       help='Directorio de salida para datos')
    
    args = parser.parse_args()
    
    # Crear pipeline
    pipeline = ProcessingPipeline(args.config)
    
    # Configurar fuente de video si se especifica
    if args.source is not None:
        try:
         
            source = int(args.source)
        except ValueError:
           
            source = args.source
        
        pipeline.set_video_source(source)
    
    try:
        # Iniciar pipeline
        if pipeline.start_pipeline():
            print("Pipeline iniciado. Presiona Ctrl+C para detener.")
            print("Las ventanas de visualización deberían estar abiertas.")
            
        
            import matplotlib.pyplot as plt
            
            last_status_time = time.time()
            while pipeline.running:
             
                try:
                    plt.pause(0.1)
                except:
                    pass
                
                current_time = time.time()
                if current_time - last_status_time >= 5:
                    status = pipeline.get_pipeline_status()
                    print(f"Estado: FPS={status['fps']}, Colas={status['queue_sizes']}")
                    last_status_time = current_time
        else:
            print("Error al iniciar el pipeline")
    
    except KeyboardInterrupt:
        print("\nDeteniendo pipeline...")
    
    finally:
        pipeline.stop_pipeline()

if __name__ == "__main__":
    main()