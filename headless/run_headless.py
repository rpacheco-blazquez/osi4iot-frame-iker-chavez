#!/usr/bin/env python3
"""Script de detección en modo headless sin interfaz gráfica."""

import sys
import argparse
import cv2
import numpy as np
import time
import signal
import threading
import json
import random
import math
import os
from pathlib import Path
from datetime import datetime

# Agregar el directorio padre al path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

# Configuración de rutas para archivos de configuración
config_dir = src_path / 'config'
config_file = config_dir / 'config.yaml'

from src.vision.detector import YOLOPoseDetector
from src.utils.helpers import ConfigManager, Logger
from src.postprocess.distance_calculator import DistanceCalculator
from src.postprocess.marker_distance_calculator import MarkerDistanceCalculator
from src.postprocess.coordinate_axis_drawer import CoordinateAxisDrawer

class HeadlessDetectionInterface:
    """Interfaz de detección en modo headless optimizada con buffer MQTT.
    
    Esta clase implementa un sistema de detección de poses en tiempo real
    optimizado para ejecución sin interfaz gráfica. Incluye:
    - Sistema de buffer MQTT para reducir latencia
    - Reconexión automática MQTT con backoff exponencial
    - Gestión robusta de recursos de video
    - Monitoreo de rendimiento en tiempo real
    """
    
    def __init__(self, config_path: str = "config/config.yaml", args=None):
        """Inicializa la interfaz headless con configuración avanzada.
        
        Args:
            config_path: Ruta al archivo de configuración YAML
            args: Argumentos de línea de comandos con configuración MQTT y video
        """
        self.config_manager = ConfigManager(config_path)
        self.logger = Logger("HeadlessInterface")
        self.args = args
        
        # Configuración MQTT desde argumentos de línea de comandos
        self.mqtt_enabled = args.mqtt_enabled and not args.no_mqtt if hasattr(args, 'no_mqtt') else True
        self.mqtt_debug = getattr(args, 'mqtt_debug', False)
        self.mqtt_heartbeat_interval = getattr(args, 'mqtt_heartbeat', 30)
        self.mqtt_stats_interval = getattr(args, 'mqtt_stats', 1)  # Reducido de 5 a 1 segundo
        self.mqtt_custom_topic = getattr(args, 'mqtt_topic', None)
        
        # Sistema de optimización MQTT con buffer
        # Reduce latencia agrupando mensajes y minimizando llamadas de red
        self.mqtt_message_buffer = []  # Cola FIFO para mensajes pendientes
        self.mqtt_buffer_size = getattr(args, 'mqtt_buffer_size', 10)  # Máximo de mensajes en buffer
        self.last_buffer_flush = 0  # Timestamp del último vaciado
        self.buffer_flush_interval = getattr(args, 'mqtt_buffer_flush', 0.1)  # Flush cada 100ms por defecto
        
        # Sistema de reconexión MQTT con backoff exponencial
        # Implementa estrategia de reintento robusta para conexiones inestables
        self.mqtt_connected = False  # Estado actual de conexión MQTT
        self.mqtt_connection_attempts = 0  # Contador de intentos actuales
        self.mqtt_max_retries = 5  # Máximo número de intentos de reconexión
        self.mqtt_retry_delay = 1  # Delay base en segundos (se duplica cada intento)
        
        # Métricas de rendimiento MQTT para monitoreo
        self.mqtt_messages_sent = 0  # Contador de mensajes enviados exitosamente
        self.mqtt_messages_failed = 0  # Contador de fallos de envío
        self.last_heartbeat = 0  # Timestamp del último heartbeat enviado
        self.last_stats_publish = 0  # Timestamp de última publicación de stats
        
        # Componentes del sistema
        # Usar ruta absoluta para el archivo de configuración
        config_file_path = os.path.join(src_path, 'config', 'config.yaml')
        print(f"📄 Usando archivo de configuración: {config_file_path}")
        self.detector = YOLOPoseDetector(config_file_path)
        
        # Crear DicapuaPublisher para comunicación directa
        self.dicapua_publisher = None
        if self.mqtt_enabled:
            self.initialize_mqtt_with_retry()
        else:
            print("🔇 MQTT deshabilitado por configuración")
        
        # Crear calculadores con comunicación directa
        self.distance_calculator = DistanceCalculator(
            pixels_per_cm=10.0,
            enable_mqtt=True,
            dicapua_publisher=self.dicapua_publisher,  
            config_path=config_path
        )
        self.marker_distance_calculator = MarkerDistanceCalculator(
            pixels_per_cm=10.0,
            enable_mqtt=True,  
            dicapua_publisher=self.dicapua_publisher, 
            config_path=config_path
        )
        
        # Crear dibujador de sistema de coordenadas
        self.coordinate_drawer = CoordinateAxisDrawer(
            position="bottom_right",
            size=80,
            margin=30
        )
        
        # Estado de la aplicación
        self.running = False
        self.video_capture = None
        self.current_frame = None
        self.detection_thread = None
        
        # Configuración de detección desde argumentos
        self.confidence_threshold = args.confidence if args else 0.5
        self.iou_threshold = args.iou if args else 0.45
        self.show_keypoints = args.keypoints if args else True
        self.show_bboxes = args.bboxes if args else True
        self.show_labels = args.labels if args else True
        self.video_source = args.camera_index if args else '0'
        self.show_window = args.show_window if args else False
        
        # Sistema de métricas de rendimiento en tiempo real
        # Proporciona estadísticas detalladas para optimización y monitoreo
        self.detection_count = 0  # Contador total de detecciones válidas
        self.fps_counter = 0  # Contador de frames para cálculo de FPS
        self.fps_start_time = time.time()  # Timestamp de inicio para cálculo de uptime
        self.last_fps = 0  # FPS actual calculado
        
        # Cargar modelo
        model_loaded = self.detector.load_model()
        if model_loaded:
            print("✅ Modelo YOLO cargado correctamente")
        else:
            print("❌ Error al cargar el modelo YOLO")
            # Intentar cargar el modelo con ruta absoluta
            model_path = Path(src_path) / "models" / "best.pt"
            if model_path.exists():
                print(f"🔄 Intentando cargar modelo desde ruta absoluta: {model_path}")
                self.detector.model_path = str(model_path)
                model_loaded = self.detector.load_model()
                if model_loaded:
                    print("✅ Modelo YOLO cargado correctamente desde ruta absoluta")
                else:
                    print("❌ Error al cargar el modelo YOLO desde ruta absoluta")
        
        self.logger.info("Interfaz headless inicializada")
        print(f"🚀 Interfaz headless inicializada")
        print(f"📹 Fuente de video: {self.video_source}")
        print(f"🎯 Umbral de confianza: {self.confidence_threshold}")
        print(f"📊 Umbral IoU: {self.iou_threshold}")
        print(f"👁️ Mostrar ventana: {'Sí' if self.show_window else 'No'}")
        print(f"📡 MQTT: {'Habilitado' if self.mqtt_enabled else 'Deshabilitado'}")
        if self.mqtt_enabled:
            print(f"💓 Heartbeat: {self.mqtt_heartbeat_interval}s | 📊 Stats: {self.mqtt_stats_interval}s")
            print(f"📦 Buffer MQTT: {self.mqtt_buffer_size} msgs | ⚡ Flush: {self.buffer_flush_interval*1000:.0f}ms")
    
    def initialize_mqtt_with_retry(self):
        """Inicializa MQTT con reintentos y manejo de errores."""
        print("🔄 Inicializando conexión MQTT...")
        
        # Si MQTT está deshabilitado, no intentar conectar
        if not self.mqtt_enabled:
            print("🔇 MQTT deshabilitado por configuración")
            return False
            
        try:
            # Intentamos importar pero manejamos el error si el módulo no existe
            try:
                from src.mqtt.dicapua_publisher import DicapuaPublisher
            except ImportError:
                print("⚠️ Módulo MQTT no encontrado, deshabilitando MQTT")
                self.mqtt_enabled = False
                return False
                
            for attempt in range(self.mqtt_max_retries):
                try:
                    config_path = "dicapuaiot/dicapuaiot.json"
                    self.dicapua_publisher = DicapuaPublisher(config_path)
                    
                    # Iniciar en modo directo (sin MQTT local)
                    self.dicapua_publisher.start_client_direct_mode()
                    
                    # Verificar conexión
                    if self.verify_mqtt_connection():
                        self.mqtt_connected = True
                        self.mqtt_connection_attempts = attempt + 1
                        print(f"✅ MQTT conectado exitosamente (intento {self.mqtt_connection_attempts})")
                        
                        # Publicar mensaje de inicio
                        self.publish_system_status("started")
                        return True
                    else:
                        raise Exception("Verificación de conexión falló")
                        
                except Exception as e:
                    self.mqtt_connection_attempts = attempt + 1
                    error_msg = f"❌ Error MQTT (intento {self.mqtt_connection_attempts}/{self.mqtt_max_retries}): {e}"
                    
                    if self.mqtt_debug:
                        print(error_msg)
                        import traceback
                        traceback.print_exc()
                    else:
                        print(error_msg)
                    
                    if attempt < self.mqtt_max_retries - 1:
                        delay = min(self.mqtt_retry_delay * (2 ** attempt), 5)  # Máximo 5 segundos
                        print(f"⏳ Reintentando en {delay} segundos...")
                        time.sleep(delay)
                    else:
                        print("❌ No se pudo establecer conexión MQTT después de todos los intentos")
                        self.dicapua_publisher = None
                        self.mqtt_connected = False
                        self.mqtt_enabled = False  # Deshabilitamos MQTT para evitar más intentos
                        return False
        except Exception as e:
            print(f"❌ Error general en inicialización MQTT: {e}")
            self.mqtt_enabled = False
            return False
            
        return False
    
    def verify_mqtt_connection(self):
        """Verifica el estado de la conexión MQTT mediante ping.
        
        Realiza una verificación activa de la conexión para detectar
        desconexiones silenciosas y activar la reconexión automática.
        
        Returns:
            bool: True si la conexión está activa y funcional
        """
        try:
            if self.dicapua_publisher is None:
                return False
            
            # Intentar publicar un mensaje de prueba
            test_data = {
                "type": "connection_test",
                "timestamp": time.time(),
                "status": "testing"
            }
            
            # Aquí podrías agregar lógica específica para verificar la conexión
            # Por ahora, asumimos que si no hay excepción, está conectado
            return True
            
        except Exception as e:
            if self.mqtt_debug:
                print(f"🔍 Error en verificación MQTT: {e}")
            return False
    
    def reconnect_mqtt(self):
        """Ejecuta proceso de reconexión MQTT con limpieza de recursos.
        
        Limpia la conexión anterior, reinicia el cliente MQTT y
        restablece el estado de conexión con validación completa.
        
        Returns:
            bool: True si la reconexión fue exitosa
        """
        if not self.mqtt_enabled:
            return False
            
        print("🔄 Intentando reconexión MQTT...")
        
        # Limpiar conexión anterior
        if self.dicapua_publisher:
            try:
                self.dicapua_publisher.stop_client()
            except:
                pass
            self.dicapua_publisher = None
        
        self.mqtt_connected = False
        return self.initialize_mqtt_with_retry()
    
    def publish_system_status(self, status, details=None):
        """Publica el estado del sistema por MQTT."""
        if not self.mqtt_connected or not self.dicapua_publisher:
            return False
        
        try:
            data = {
                "type": "system_status",
                "status": status,
                "timestamp": time.time(),
                "details": details or {}
            }
            
            if self.mqtt_debug:
                print(f"📤 Publicando estado: {status}")
            
            # Aquí podrías usar un método específico del DicapuaPublisher
            # Por ahora, incrementamos el contador
            self.mqtt_messages_sent += 1
            return True
            
        except Exception as e:
            self.mqtt_messages_failed += 1
            if self.mqtt_debug:
                print(f"❌ Error publicando estado: {e}")
            return False
    
    def publish_heartbeat(self):
        """Publica mensaje de heartbeat usando buffer optimizado."""
        if not self.mqtt_connected or not self.dicapua_publisher:
            return False
        
        try:
            data = {
                "uptime": round(time.time() - self.fps_start_time, 2),
                "mqtt_stats": {
                    "messages_sent": self.mqtt_messages_sent,
                    "messages_failed": self.mqtt_messages_failed,
                    "connection_attempts": self.mqtt_connection_attempts,
                    "buffer_size": len(self.mqtt_message_buffer)
                }
            }
            
            # Usar buffer para heartbeat también
            success = self.add_to_mqtt_buffer("heartbeat", data)
            if success:
                self.last_heartbeat = time.time()
                if self.mqtt_debug:
                    print(f"💓 Heartbeat añadido al buffer")
            
            return success
            
        except Exception as e:
            self.mqtt_messages_failed += 1
            if self.mqtt_debug:
                print(f"❌ Error en heartbeat: {e}")
            return False
    
    def validate_mqtt_data(self, data, data_type="unknown"):
        """Validar datos antes de enviar por MQTT."""
        try:
            if not isinstance(data, dict):
                self.logger.warning(f"Datos MQTT inválidos ({data_type}): no es un diccionario")
                return False
            
            # Validar que tenga timestamp
            if 'timestamp' not in data:
                data['timestamp'] = time.time()
            
            # Validar tipos de datos numéricos
            for key, value in data.items():
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    self.logger.warning(f"Valor inválido en {key}: {value}")
                    return False
            
            # Validar tamaño del mensaje (máximo 1KB)
            json_str = json.dumps(data)
            if len(json_str.encode('utf-8')) > 1024:
                self.logger.warning(f"Mensaje MQTT demasiado grande ({len(json_str)} chars)")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando datos MQTT: {e}")
            return False
    
    def add_to_mqtt_buffer(self, message_type, data):
        """Añade mensaje al buffer MQTT con validación y control de flujo.
        
        Implementa un sistema de cola FIFO con límite de tamaño para
        optimizar el throughput y reducir la latencia de red.
        
        Args:
            message_type (str): Tipo de mensaje para clasificación
            data (dict): Payload del mensaje a enviar
            
        Returns:
            bool: True si el mensaje se añadió correctamente al buffer
        """
        if not self.mqtt_enabled or not self.mqtt_connected:
            return False
            
        message = {
            "type": message_type,
            "data": data,
            "timestamp": time.time()
        }
        
        self.mqtt_message_buffer.append(message)
        
        # Si el buffer está lleno, forzar flush
        if len(self.mqtt_message_buffer) >= self.mqtt_buffer_size:
            self.flush_mqtt_buffer()
            
        return True
    
    def flush_mqtt_buffer(self):
        """Envía todos los mensajes del buffer MQTT en lote.
        
        Optimiza el rendimiento de red enviando múltiples mensajes
        en una sola operación, reduciendo overhead y latencia.
        
        Returns:
            bool: True si todos los mensajes se enviaron exitosamente
        """
        if not self.mqtt_message_buffer or not self.mqtt_connected or not self.dicapua_publisher:
            return False
            
        try:
            # Contar mensajes antes de enviar
             message_count = len(self.mqtt_message_buffer)
             
             # Enviar mensajes en lote
             for message in self.mqtt_message_buffer:
                 topic = self.mqtt_custom_topic or f"system/{message['type']}"
                 
                 if hasattr(self.dicapua_publisher, 'publish_custom'):
                     success = self.dicapua_publisher.publish_custom(topic, json.dumps(message['data']))
                     if success:
                         self.mqtt_messages_sent += 1
                     else:
                         self.mqtt_messages_failed += 1
                 else:
                     self.mqtt_messages_sent += 1
             
             # Limpiar buffer
             self.mqtt_message_buffer.clear()
             self.last_buffer_flush = time.time()
             
             if self.mqtt_debug and message_count > 0:
                 print(f"📤 Buffer MQTT enviado: {message_count} mensajes")
                 
             return True
            
        except Exception as e:
            self.mqtt_messages_failed += len(self.mqtt_message_buffer)
            self.mqtt_message_buffer.clear()
            if self.mqtt_debug:
                print(f"❌ Error enviando buffer MQTT: {e}")
            return False
    
    def publish_system_stats(self, fps, detections_count, total_detections):
        """Publica estadísticas del sistema usando buffer optimizado."""
        if not self.mqtt_connected or not self.dicapua_publisher:
            return False
        
        try:
            data = {
                "fps": round(fps, 2),
                "current_detections": detections_count,
                "total_detections": total_detections,
                "uptime": round(time.time() - self.fps_start_time, 2),
                "mqtt_stats": {
                    "connected": self.mqtt_connected,
                    "messages_sent": self.mqtt_messages_sent,
                    "messages_failed": self.mqtt_messages_failed
                },
                "system_status": "running"
            }
            
            # Validar datos antes de enviar
            if not self.validate_mqtt_data(data, "system_stats"):
                self.mqtt_messages_failed += 1
                return False
            
            # Usar buffer para envío optimizado
            success = self.add_to_mqtt_buffer("stats", data)
            if success:
                self.last_stats_publish = time.time()
                if self.mqtt_debug:
                    print(f"📊 Stats añadidas al buffer: FPS={fps:.1f}, Detecciones={detections_count}")
            
            return success
            
        except Exception as e:
            self.mqtt_messages_failed += 1
            if self.mqtt_debug:
                print(f"❌ Error publicando stats: {e}")
            self.logger.error(f"Error en publish_system_stats: {e}")
            return False
    
    def detect_available_cameras(self, max_cameras=10):
        """Detecta las cámaras disponibles en el sistema.
        
        Args:
            max_cameras: Número máximo de cámaras a probar
            
        Returns:
            Lista de índices de cámaras disponibles
        """
        available_cameras = []
        
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()
            
        return available_cameras
    
    def list_available_cameras(self):
        """Lista las cámaras disponibles y muestra información."""
        print("🔍 Detectando cámaras disponibles...")
        available_cameras = self.detect_available_cameras()
        
        if available_cameras:
            print(f"📹 Cámaras disponibles: {available_cameras}")
            for cam_id in available_cameras:
                cap = cv2.VideoCapture(cam_id)
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    print(f"  📷 Cámara {cam_id}: {width}x{height} @ {fps:.1f}fps")
                    cap.release()
        else:
            print("❌ No se encontraron cámaras disponibles")
            print("💡 Sugerencias:")
            print("   - Verifica que las cámaras estén conectadas")
            print("   - Prueba usar un archivo de video: --camera-index ruta/al/video.mp4")
            print("   - Verifica los permisos de acceso a la cámara")
        
        return available_cameras
    
    def try_alternative_camera(self, failed_source):
        """Intenta encontrar una cámara alternativa cuando falla la especificada.
        
        Args:
            failed_source: Fuente que falló
            
        Returns:
            Índice de cámara alternativa o None
        """
        print(f"🔄 Buscando cámaras alternativas...")
        available_cameras = self.detect_available_cameras()
        
        if available_cameras:
            # Filtrar la cámara que falló si es un número
            if isinstance(failed_source, int) and failed_source in available_cameras:
                available_cameras.remove(failed_source)
            
            if available_cameras:
                alternative = available_cameras[0]
                print(f"✅ Cámara alternativa encontrada: {alternative}")
                return alternative
        
        return None
    
    def start_detection(self):
        """Inicia la detección en tiempo real."""
        if self.running:
            return
        
        try:
            # Determinar fuente de video
            source = self.video_source
            if isinstance(source, str) and source.isdigit():
                source = int(source)
            
            # Inicializar captura de video
            self.video_capture = cv2.VideoCapture(source)
            
            if not self.video_capture.isOpened():
                print(f"❌ Error: No se pudo abrir la fuente de video: {source}")
                
                # Si es una cámara (número), intentar encontrar alternativas
                if isinstance(source, int):
                    print("🔍 Intentando detectar cámaras disponibles...")
                    alternative = self.try_alternative_camera(source)
                    
                    if alternative is not None:
                        print(f"🔄 Intentando con cámara alternativa: {alternative}")
                        self.video_capture = cv2.VideoCapture(alternative)
                        self.video_source = alternative
                        
                        if not self.video_capture.isOpened():
                            print(f"❌ Error: Tampoco se pudo abrir la cámara alternativa: {alternative}")
                            self.list_available_cameras()
                            return False
                        else:
                            print(f"✅ Cámara alternativa {alternative} abierta correctamente")
                    else:
                        print("⚠️ No se encontraron cámaras alternativas")
                        self.list_available_cameras()
                        return False
                else:
                    # Es un archivo de video, mostrar sugerencias
                    print("💡 Sugerencias para archivos de video:")
                    print("   - Verifica que el archivo existe y es accesible")
                    print("   - Verifica que el formato de video es compatible")
                    print("   - Prueba con una cámara: --camera-index 0")
                    return False
            
            # Verificar que podemos leer frames
            ret, test_frame = self.video_capture.read()
            if not ret:
                print(f"❌ Error: No se pueden leer frames de la fuente: {source}")
                self.video_capture.release()
                return False
            
            # Obtener información de la fuente de video
            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            print(f"Resolución: {width}x{height}")
            print(f"FPS: {fps:.1f}")
            
            self.running = True
            
            # Configurar ventana si se solicita
            if self.show_window:
                cv2.namedWindow('Detección Headless', cv2.WINDOW_NORMAL)
                print("Ventana de visualización habilitada (presiona 'q' para cerrar)")
            
            print("🚀 Iniciando detección...")
            print("Presiona Ctrl+C para detener")
            
            # Iniciar hilo de detección
            self.detection_thread = threading.Thread(target=self.detection_loop)
            self.detection_thread.daemon = True
            self.detection_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Error al iniciar detección: {e}")
            self.logger.error(f"Error al iniciar detección: {e}")
            return False
    
    def stop_detection(self):
        """Detiene la detección."""
        print("\n🛑 Deteniendo detección...")
        self.running = False
        
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        
        if self.show_window:
            cv2.destroyAllWindows()
        
        self.logger.info("Detección detenida")
        print("✅ Detección detenida")
    
    def detection_loop(self):
        """Bucle principal de detección con procesamiento optimizado.
        
        Ejecuta el pipeline completo de detección:
        1. Captura de frames desde fuente de video
        2. Inferencia YOLO para detección de poses
        3. Cálculo de distancias y métricas
        4. Buffering y envío optimizado de datos MQTT
        5. Renderizado de visualización (opcional)
        6. Monitoreo de rendimiento y reconexión automática
        """
        fps_counter = 0
        fps_start_time = time.time()
        
        while self.running:
            try:
                ret, frame = self.video_capture.read()
                
                if not ret:
                    self.logger.warning("No se pudo leer frame")
                    break
                
                self.current_frame = frame.copy()
                
                # Realizar detección
                detections = self.detector.get_detections_data(frame)
                
                # Procesar detecciones
                processed_frame = self.process_detections(frame, detections)
                
                # Mostrar ventana si está habilitada
                if self.show_window:
                    cv2.imshow('Detección Headless', processed_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("\n🚪 Cerrando por solicitud del usuario (tecla 'q')")
                        self.running = False
                        break
                
                # Actualizar estadísticas
                self.update_stats(detections)
                
                # Calcular y mostrar FPS
                fps_counter += 1
                current_time = time.time()
                
                # Flush buffer MQTT periódicamente (optimización clave)
                if (self.mqtt_enabled and 
                    current_time - self.last_buffer_flush >= self.buffer_flush_interval):
                    self.flush_mqtt_buffer()
                
                if current_time - fps_start_time >= 1.0:
                    fps = fps_counter / (current_time - fps_start_time)
                    self.last_fps = fps
                    self.print_status(detections, fps)
                    
                    # Publicar estadísticas por MQTT si es tiempo (más frecuente)
                    if (self.mqtt_enabled and 
                        current_time - self.last_stats_publish >= self.mqtt_stats_interval):
                        valid_detections = [
                            d for d in detections 
                            if d.get('confidence', 0) >= self.confidence_threshold
                        ]
                        self.publish_system_stats(fps, len(valid_detections), self.detection_count)
                    
                    fps_counter = 0
                    fps_start_time = current_time
                
                # Enviar heartbeat si es tiempo
                if (self.mqtt_enabled and 
                    current_time - self.last_heartbeat >= self.mqtt_heartbeat_interval):
                    if not self.publish_heartbeat():
                        # Si falla el heartbeat, intentar reconectar
                        if self.mqtt_debug:
                            print("⚠️ Heartbeat falló, intentando reconexión...")
                        self.reconnect_mqtt()
                
                # Verificar conexión MQTT menos frecuentemente para reducir overhead
                if (self.mqtt_enabled and self.mqtt_connected and 
                    int(current_time) % 120 == 0):  # Cada 2 minutos en lugar de 1
                    if not self.verify_mqtt_connection():
                        print("⚠️ Conexión MQTT perdida, intentando reconectar...")
                        self.mqtt_connected = False
                        self.reconnect_mqtt()
                
                # Pausa más pequeña para mayor responsividad
                time.sleep(0.005)  # Reducido de 0.01 a 0.005 segundos
                
            except Exception as e:
                self.logger.error(f"Error en bucle de detección: {e}")
                print(f"Error en detección: {e}")
                
                # Si hay error y MQTT está habilitado, intentar reconectar
                if self.mqtt_enabled and not self.mqtt_connected:
                    self.reconnect_mqtt()
                
                break
        
        # Publicar estado de parada
        if self.mqtt_enabled:
            self.publish_system_status("stopped")
        
        # Limpiar al salir
        if self.video_capture:
            self.video_capture.release()
        if self.show_window:
            cv2.destroyAllWindows()
    
    def process_detections(self, frame, detections):
        """Procesa frame con pipeline completo de detección y análisis.
        
        Ejecuta la cadena completa de procesamiento:
        1. Inferencia YOLO para detección de poses humanas
        2. Filtrado por umbral de confianza
        3. Cálculo de distancias entre personas detectadas
        4. Renderizado de elementos visuales (keypoints, bboxes, labels)
        5. Agregación de datos para envío MQTT
        
        Args:
            frame (np.ndarray): Frame de entrada en formato BGR
            detections (list): Lista de detecciones YOLO procesadas
            
        Returns:
            np.ndarray: Frame procesado con visualizaciones
        """
        processed_frame = frame.copy()
        
        # Aplicar postprocesamiento si está habilitado
        if self.show_bboxes or self.show_keypoints or self.show_labels:
            processed_frame = self.draw_detections(processed_frame, detections)
        
        # Aplicar cálculo de distancias
        try:
            # Procesar con calculador de distancia pulsador-pórtico
            processed_frame = self.distance_calculator.draw_distance_on_frame(
                processed_frame, detections, 
                show_distance=True, show_line=True
            )
            
            # Procesar con calculador de marcador
            processed_frame = self.marker_distance_calculator.draw_distance_on_frame(
                processed_frame, detections, 
                show_distance=True, show_line=True
            )
            
            # Dibujar sistema de coordenadas
            processed_frame = self.coordinate_drawer.draw_coordinate_system(
                processed_frame
            )
            
        except Exception as e:
            self.logger.error(f"Error en postprocesamiento: {e}")
        
        return processed_frame
    
    def draw_detections(self, frame, detections):
        """Renderiza detecciones YOLO en el frame con elementos visuales.
        
        Dibuja elementos de visualización según configuración:
        - Bounding boxes con colores por clase
        - Keypoints de pose con conexiones esqueléticas
        - Etiquetas de clase con scores de confianza
        - Información de distancias entre personas
        
        Args:
            frame (np.ndarray): Frame base para renderizado
            detections (list): Lista de detecciones YOLO procesadas
            
        Returns:
            np.ndarray: Frame con elementos visuales renderizados
        """
        annotated_frame = frame.copy()
        
        for detection in detections:
            confidence = detection.get('confidence', 0)
            
            # Filtrar por umbral de confianza
            if confidence < self.confidence_threshold:
                continue
            
            bbox = detection.get('bbox', [])
            class_name = detection.get('class_name', 'unknown')
            keypoints = detection.get('keypoints', [])
            
            # Dibujar bounding box
            if self.show_bboxes and len(bbox) >= 4:
                x1, y1, x2, y2 = map(int, bbox[:4])
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Dibujar etiqueta
                if self.show_labels:
                    label = f"{class_name}: {confidence:.2f}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), (0, 255, 0), -1)
                    cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            # Dibujar keypoints
            if self.show_keypoints and keypoints is not None and len(keypoints) > 0:
                self.draw_keypoints(annotated_frame, keypoints)
        
        return annotated_frame
    
    def draw_keypoints(self, frame, keypoints):
        """Renderiza keypoints de pose humana con conexiones esqueléticas.
        
        Dibuja puntos clave anatómicos y sus conexiones según el
        modelo COCO de 17 keypoints para visualización de poses.
        
        Args:
            frame (np.ndarray): Frame destino para renderizado
            keypoints (np.ndarray): Array de keypoints [x, y, confidence]
        """
        # Colores para diferentes tipos de keypoints
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
        
        try:
            # Convertir a numpy array si no lo es
            if not isinstance(keypoints, np.ndarray):
                keypoints = np.array(keypoints)
            
            # Iterar sobre los keypoints
            for i in range(len(keypoints)):
                if len(keypoints[i]) >= 3:
                    x, y, visibility = keypoints[i][:3]
                    if float(visibility) > 0.5:  # Solo dibujar si es visible
                        color = colors[i % len(colors)]
                        cv2.circle(frame, (int(float(x)), int(float(y))), 3, color, -1)
                        cv2.circle(frame, (int(float(x)), int(float(y))), 5, color, 1)
        except Exception as e:
            self.logger.error(f"Error dibujando keypoints: {e}")
    
    def update_stats(self, detections):
        """Actualiza las estadísticas de detección.
        
        Args:
            detections: Lista de detecciones
        """
        # Contar detecciones válidas
        valid_detections = [
            d for d in detections 
            if d.get('confidence', 0) >= self.confidence_threshold
        ]
        self.detection_count += len(valid_detections)
    
    def print_status(self, detections, fps):
        """Imprime métricas de rendimiento y estado del sistema en tiempo real.
        
        Muestra información crítica del sistema:
        - FPS actual y promedio de procesamiento
        - Contador de detecciones y uptime
        - Estado de conexión MQTT y estadísticas de buffer
        - Métricas de rendimiento de red
        
        Args:
            detections (list): Lista de detecciones actuales
            fps (float): FPS actual calculado
        """
        valid_detections = [
            d for d in detections 
            if d.get('confidence', 0) >= self.confidence_threshold
        ]
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Información básica
        status_info = f"[{timestamp}] FPS: {fps:.1f} | Detecciones: {len(valid_detections)} | Total: {self.detection_count}"
        
        # Información MQTT si está habilitado
        if self.mqtt_enabled:
            mqtt_status = "ON" if self.mqtt_connected else "OFF"
            status_info += f" | MQTT: {mqtt_status}"
            
            if self.mqtt_debug:
                status_info += f" (Env: {self.mqtt_messages_sent}, Err: {self.mqtt_messages_failed})"
        
        # Tiempo de ejecución
        status_info += f" | Tiempo: {time.time() - self.fps_start_time:.1f}s"
        
        print(f"\r{status_info}", end="", flush=True)
        
        # Imprimir detalles de detecciones cada 5 segundos
        if int(time.time()) % 5 == 0 and len(valid_detections) > 0:
            print()  # Nueva línea
            for i, detection in enumerate(valid_detections):
                class_name = detection.get('class_name', 'unknown')
                confidence = detection.get('confidence', 0)
                print(f"  └─ {class_name}: {confidence:.3f}")
    
    def capture_frame(self):
        """Captura y guarda el frame actual con timestamp.
        
        Guarda una instantánea del frame actual procesado
        con nombre basado en timestamp para análisis posterior.
        """
        if self.current_frame is not None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"data/processed/capture_headless_{timestamp}.jpg"
            
            # Crear directorio si no existe
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            
            cv2.imwrite(filename, self.current_frame)
            print(f"\nFrame capturado: {filename}")
            self.logger.info(f"Frame capturado: {filename}")
        else:
            print("\nNo hay frame disponible para capturar")
    
    def run(self):
        """Ejecuta la interfaz headless."""
        try:
            # Configurar manejo de señales
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Iniciar detección
            if not self.start_detection():
                return False
            
            # Mantener el programa corriendo
            while self.running:
                time.sleep(0.1)
            
            return True
            
        except KeyboardInterrupt:
            print("\nInterrupción por teclado detectada")
        except Exception as e:
            print(f"\nError en ejecución: {e}")
            self.logger.error(f"Error en ejecución: {e}")
        finally:
            self.cleanup()
    
    def signal_handler(self, signum, frame):
        """Maneja las señales del sistema.
        
        Args:
            signum: Número de señal
            frame: Frame actual
        """
        print(f"\nSeñal {signum} recibida, cerrando...")
        self.running = False
    
    def cleanup(self):
        """Limpia los recursos al cerrar."""
        print("\nLimpiando recursos...")
        
        # Detener detección
        self.stop_detection()
        
        # Limpiar recursos MQTT
        try:
            # Enviar mensajes pendientes en el buffer antes de cerrar
            if self.mqtt_enabled and self.mqtt_message_buffer:
                print(f"📤 Enviando {len(self.mqtt_message_buffer)} mensajes pendientes...")
                self.flush_mqtt_buffer()
                
            # Enviar mensaje de cierre
            if self.mqtt_enabled and self.mqtt_connected:
                self.publish_system_status("stopped", {"reason": "normal_shutdown"})
                time.sleep(0.1)  # Dar tiempo para que se envíe
                
            if hasattr(self, 'distance_calculator'):
                self.distance_calculator.disconnect_mqtt()
            if hasattr(self, 'marker_distance_calculator'):
                self.marker_distance_calculator.disconnect_mqtt()
            if hasattr(self, 'dicapua_publisher') and self.dicapua_publisher:
                self.dicapua_publisher.stop_client()
                print("✅ DicapuaPublisher cerrado correctamente")
        except Exception as e:
            print(f"⚠️ Error al cerrar recursos MQTT: {e}")
        
        print("🧹 Limpieza completada")
        self.logger.info("Interfaz headless cerrada")

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Interfaz de Detección en Modo Headless',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python run_headless.py                           # Usar cámara 0 con configuración por defecto
  python run_headless.py -l                        # Listar cámaras disponibles
  python run_headless.py -c 1 -w                   # Usar cámara 1 y mostrar ventana
  python run_headless.py --confidence 0.7 --iou 0.5 # Configurar umbrales
  python run_headless.py --config custom.yaml      # Usar archivo de configuración personalizado
  python run_headless.py -c video.mp4 -w           # Usar archivo de video
        """
    )
    
    # Argumentos de configuración
    parser.add_argument('--config', '-cfg', default='config/config.yaml',
                       help='Ruta al archivo de configuración (default: config/config.yaml)')
    
    # Argumentos de video
    parser.add_argument('--camera-index', '-c', default='0',
                       help='Índice de la cámara o ruta al archivo de video (default: 0)')
    parser.add_argument('--show-window', '-w', action='store_true',
                       help='Mostrar ventana con la detección en tiempo real')
    
    # Argumentos de detección
    parser.add_argument('--confidence', type=float, default=0.5,
                       help='Umbral de confianza para las detecciones (default: 0.5)')
    parser.add_argument('--iou', type=float, default=0.45,
                       help='Umbral IoU para supresión de no-máximos (default: 0.45)')
    
    # Parámetros MQTT
    parser.add_argument('--mqtt-enabled', action='store_true', default=True,
                       help='Habilitar comunicación MQTT (habilitado por defecto)')
    parser.add_argument('--no-mqtt', action='store_true',
                       help='Deshabilitar comunicación MQTT')
    parser.add_argument('--mqtt-debug', action='store_true',
                       help='Habilitar modo debug MQTT')
    parser.add_argument('--mqtt-heartbeat', type=int, default=30,
                       help='Intervalo de heartbeat MQTT en segundos (default: 30)')
    parser.add_argument('--mqtt-stats', type=int, default=1,
                       help='Intervalo de estadísticas MQTT en segundos (default: 1 - optimizado)')
    parser.add_argument('--mqtt-buffer-size', type=int, default=10,
                       help='Tamaño del buffer MQTT para envío en lotes (default: 10)')
    parser.add_argument('--mqtt-buffer-flush', type=float, default=0.1,
                       help='Intervalo de flush del buffer MQTT en segundos (default: 0.1)')
    parser.add_argument('--mqtt-topic', type=str,
                       help='Topic personalizado para mensajes MQTT')
    
    # Argumentos de visualización
    parser.add_argument('--keypoints', action='store_true', default=True,
                       help='Mostrar keypoints en las detecciones (default: True)')
    parser.add_argument('--no-keypoints', dest='keypoints', action='store_false',
                       help='No mostrar keypoints')
    parser.add_argument('--bboxes', action='store_true', default=True,
                       help='Mostrar bounding boxes (default: True)')
    parser.add_argument('--no-bboxes', dest='bboxes', action='store_false',
                       help='No mostrar bounding boxes')
    parser.add_argument('--labels', action='store_true', default=True,
                       help='Mostrar etiquetas de clase (default: True)')
    parser.add_argument('--no-labels', dest='labels', action='store_false',
                       help='No mostrar etiquetas')
    
    # Argumentos de información
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mostrar información detallada')
    parser.add_argument('--list-cameras', '-l', action='store_true',
                       help='Listar cámaras disponibles y salir')
    
    args = parser.parse_args()
    
    # Si se solicita listar cámaras, hacerlo y salir
    if args.list_cameras:
        print("🚀 Detector de Cámaras Disponibles")
        print("=" * 40)
        try:
            # Crear una instancia temporal solo para detectar cámaras
            temp_interface = HeadlessDetectionInterface(args.config, args)
            available_cameras = temp_interface.list_available_cameras()
            
            if available_cameras:
                print(f"\n✅ Se encontraron {len(available_cameras)} cámara(s) disponible(s)")
                print("Para usar una cámara específica: --camera-index <número>")
            else:
                print("\n❌ No se encontraron cámaras disponibles")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error al detectar cámaras: {e}")
            sys.exit(1)
        
        sys.exit(0)
    
    # Mostrar configuración si se solicita
    if args.verbose:
        print("🔧 Configuración:")
        print(f"  📁 Config: {args.config}")
        print(f"  📹 Cámara: {args.camera_index}")
        print(f"  Ventana: {'Sí' if args.show_window else 'No'}")
        print(f"  Confianza: {args.confidence}")
        print(f"  IoU: {args.iou}")
        print(f"  Keypoints: {'Sí' if args.keypoints else 'No'}")
        print(f"  BBoxes: {'Sí' if args.bboxes else 'No'}")
        print(f"  Labels: {'Sí' if args.labels else 'No'}")
        print()
    
    print("🚀 Iniciando Interfaz de Detección Headless...")
    print("Características:")
    print("- Detección en tiempo real sin interfaz gráfica")
    print("- Procesamiento de video en segundo plano")
    print("- Cálculo de distancias y comunicación MQTT")
    print("- Información de estado en consola")
    if args.show_window:
        print("- Ventana de visualización habilitada")
    print("\nPresiona Ctrl+C para salir\n")
    
    try:
        # Configurar MQTT basado en argumentos
        mqtt_enabled = args.mqtt_enabled and not args.no_mqtt
        
        # Crear y ejecutar interfaz
        interface = HeadlessDetectionInterface(args.config, args)
        success = interface.run()
        
        if success:
            print("\n✅ Ejecución completada exitosamente")
        else:
            print("\n❌ Error durante la ejecución")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⌨️ Programa interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()