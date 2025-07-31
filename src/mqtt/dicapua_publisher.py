import datetime
import json
import time
import logging
import threading
from typing import Optional, Dict, Any
from paho.mqtt import client as mqtt_client
from .config.config import Config

class DicapuaPublisher:
    """Publicador MQTT principal que recibe datos locales y los envía a DicapuaIoT"""
    
    def __init__(self, config_path: str = "dicapuaiot/dicapuaiot.json"):
        self.logger = logging.getLogger(__name__)
        self.config = Config(config_path)
        
        # Cliente para DicapuaIoT (externo)
        self.dicapua_client = None
        self.dicapua_connected = False
        self.dicapuaiot_client = None  # Alias para compatibilidad
        self.dicapuaiot_connected = False  # Alias para compatibilidad
        self.dicapuaiot_topic = self.config.topic.publish["YOLOframe"]
        
        # Cliente para MQTT local (recibir datos de calculadores)
        self.local_client = None
        self.local_connected = False
        
        # Datos de distancia recibidos (formato nuevo)
        self.last_marker_data = None
        self.last_portico_data = None
        
        # Datos de distancia recibidos (formato legacy)
        self.marker_distance = None
        self.portico_distance = None
        self.last_marker_time = 0
        self.last_portico_time = 0
        
        self.last_publish_time = 0
        self.publish_threshold = 0.1  # Mínimo 100ms entre publicaciones
        
        # Configuración MQTT local
        self.local_broker = "localhost"
        self.local_port = 1883
        self.marker_topic = "distance/marcador"
        self.portico_topic = "distance/portico_pulsador"
        
        # Reconexión automática
        self.should_reconnect = True
        self.reconnect_delay = 1  # segundos inicial
        self.max_reconnect_delay = 60  # máximo delay
        self.reconnect_thread: Optional[threading.Thread] = None
        self.connection_lock = threading.Lock()
        
    def on_dicapua_message(self, client, userdata, msg):
        """Callback para mensajes recibidos de DicapuaIoT"""
        try:
            self.logger.debug(f"Mensaje DicapuaIoT recibido: {msg}")
            json_data = msg.payload.decode("utf-8")
            dict_data = json.loads(json_data)
            self.logger.info(f"Datos DicapuaIoT recibidos: {dict_data}")
        except Exception as e:
            self.logger.error(f"Error al procesar mensaje DicapuaIoT: {e}")
    
    def on_local_message(self, client, userdata, msg):
        """
        Callback para mensajes del broker local.
        Procesa datos de distancia de los calculadores locales.
        """
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            print(f"📨 Mensaje local recibido en {topic}: {payload}")
            
            # Procesar según el topic
            if topic == "distance/portico_pulsador":
                self.last_portico_data = {
                    'distance_cm': payload.get('distance_cm'),
                    'timestamp': payload.get('timestamp'),
                    'source': 'portico_calculator'
                }
                print(f"🏗️ Datos pórtico actualizados: {self.last_portico_data['distance_cm']:.2f}cm")
                
            elif topic == "distance/marcador":
                self.last_marker_data = {
                    'distance_cm': payload.get('distance_cm'),
                    'timestamp': payload.get('timestamp'),
                    'source': 'marker_calculator'
                }
                print(f"📏 Datos marcador actualizados: {self.last_marker_data['distance_cm']:.2f}cm")
            
            # Enviar datos combinados a DicapuaIoT si tenemos ambos
            self._send_combined_data_to_dicapuaiot()
            
        except Exception as e:
            print(f"❌ Error procesando mensaje local: {e}")
    
    def connect_dicapua_mqtt(self) -> mqtt_client.Client:
        """Conecta al broker DicapuaIoT externo"""
        def on_dicapua_connect(client, userdata, flags, rc):
            if rc == 0:
                self.dicapua_connected = True
                self.dicapuaiot_connected = True  # Alias para compatibilidad
                self.logger.info("✅ Conectado a DicapuaIoT MQTT Broker!")
            else:
                self.logger.error(f"❌ Error conectando a DicapuaIoT, código: {rc}")
                self.dicapua_connected = False
                self.dicapuaiot_connected = False
        
        def on_dicapua_disconnect(client, userdata, rc):
            self.dicapua_connected = False
            self.dicapuaiot_connected = False
            if rc != 0:
                disconnect_codes = {
                    1: "Versión de protocolo no aceptable",
                    2: "Identificador rechazado", 
                    3: "Servidor no disponible",
                    4: "Usuario/contraseña malformados",
                    5: "No autorizado",
                    7: "Error de red/conexión",
                    8: "Timeout de conexión"
                }
                reason = disconnect_codes.get(rc, f"Código desconocido: {rc}")
                self.logger.warning(f"⚠️ Desconexión inesperada de DicapuaIoT: {reason}")
                
                # Iniciar reconexión automática
                if self.should_reconnect:
                    self._schedule_reconnect()
            else:
                self.logger.info("🔌 Desconectado de DicapuaIoT MQTT Broker")
        
        # Crear cliente MQTT para DicapuaIoT con sesión persistente
        client = mqtt_client.Client(client_id=self.config.client_id + "_dicapua", clean_session=False)
        
        # Configurar SSL/TLS o autenticación básica
        if self.config.connectCerts:
            client.tls_set(
                ca_certs=self.config.certs["ca_certs"],
                certfile=self.config.certs["certfile"],
                keyfile=self.config.certs["keyfile"],
            )
            port = 8883
        else:
            client.username_pw_set(self.config.username, self.config.password)
            port = 1883
        
        # Configurar callbacks
        client.on_connect = on_dicapua_connect
        client.on_disconnect = on_dicapua_disconnect
        client.on_message = self.on_dicapua_message
        
        # Conectar al broker con keepalive largo
        try:
            client.connect(self.config.broker, port, 300)
            self.dicapua_client = client
            self.dicapuaiot_client = client  # Alias para compatibilidad
            return client
        except Exception as e:
            self.logger.error(f"Error al conectar a DicapuaIoT: {e}")
            return None
    
    def connect_local_mqtt(self) -> mqtt_client.Client:
        """Conecta al broker MQTT local para recibir datos de calculadores"""
        def on_local_connect(client, userdata, flags, rc):
            if rc == 0:
                self.local_connected = True
                self.logger.info("✅ Conectado a MQTT local!")
                # Suscribirse a los topics de distancia
                client.subscribe(self.marker_topic)
                client.subscribe(self.portico_topic)
                self.logger.info(f"📡 Suscrito a: {self.marker_topic}, {self.portico_topic}")
            else:
                self.logger.error(f"❌ Error conectando a MQTT local, código: {rc}")
                self.local_connected = False
        
        def on_local_disconnect(client, userdata, rc):
            self.local_connected = False
            if rc != 0:
                self.logger.warning(f"⚠️ Desconexión inesperada de MQTT local: {rc}")
            else:
                self.logger.info("🔌 Desconectado de MQTT local")
        
        # Crear cliente MQTT para broker local
        client = mqtt_client.Client(client_id=self.config.client_id + "_local", clean_session=True)
        
        # Configurar callbacks
        client.on_connect = on_local_connect
        client.on_disconnect = on_local_disconnect
        client.on_message = self.on_local_message
        
        # Conectar al broker local
        try:
            client.connect(self.local_broker, self.local_port)
            self.local_client = client
            return client
        except Exception as e:
            self.logger.error(f"Error al conectar a MQTT local: {e}")
            return None
    
    def _send_combined_data_to_dicapuaiot(self):
        """
        Envía datos combinados de marcador y pórtico a DicapuaIoT.
        Solo envía si hay ambos datos calculados.
        """
        if not self.dicapua_connected or not self.last_marker_data or not self.last_portico_data:
            return
            
        try:
            # Crear payload combinado según formato DicapuaIoT
            combined_payload = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "markerZ": self.last_marker_data['distance_cm'],  # Distancia vertical del marcador
                "buttonX": self.last_portico_data['distance_cm'],  # Distancia horizontal pórtico-pulsador
                "marker": self.last_marker_data['distance_cm']*0.91*10  
            }
            
            # Validar datos antes de enviar
            if self._validate_distance_data(combined_payload):
                # Enviar a DicapuaIoT con reintentos
                msg = json.dumps(combined_payload)
                success = self._publish_with_retry(self.config.topic.publish["YOLOframe"], msg, retries=3)
                
                if success:
                    print(f"✅ Datos combinados enviados a DicapuaIoT: markerZ={combined_payload['markerZ']:.2f}cm, buttonX={combined_payload['buttonX']:.2f}cm")
                    self.logger.info(f"📤 Payload combinado enviado: {combined_payload}")
                else:
                    print(f"⚠️ Error al enviar a DicapuaIoT después de reintentos")
                    self.logger.error(f"Error al publicar datos combinados después de reintentos")
            else:
                print("⚠️ Datos combinados no válidos, no se envían a DicapuaIoT")
                
        except Exception as e:
            print(f"❌ Error enviando datos combinados a DicapuaIoT: {e}")
            self.logger.error(f"Error enviando datos combinados: {e}")
    
    def _validate_distance_data(self, payload: Dict[str, Any]) -> bool:
        """
        Valida que los datos de distancia estén en rangos válidos.
        
        Args:
            payload: Diccionario con los datos a validar
            
        Returns:
            True si los datos son válidos, False en caso contrario
        """
        try:
            marker_z = payload.get('markerZ')
            button_x = payload.get('buttonX')
            
            # Validar que ambos valores existan y sean numéricos
            if marker_z is None or button_x is None:
                print(f"⚠️ Datos faltantes: markerZ={marker_z}, buttonX={button_x}")
                return False
            
            # Validar que sean números válidos
            if not isinstance(marker_z, (int, float)) or not isinstance(button_x, (int, float)):
                print(f"⚠️ Tipos de datos inválidos: markerZ={type(marker_z)}, buttonX={type(button_x)}")
                return False
                
            # Validar rangos: ambos deben ser positivos (los calculadores convierten negativos a 0)
            if not (0 <= marker_z < 1000):
                print(f"⚠️ markerZ fuera de rango: {marker_z} (debe estar entre 0 y 1000)")
                return False
                
            if not (0 <= button_x < 1000):
                print(f"⚠️ buttonX fuera de rango: {button_x} (debe estar entre 0 y 1000)")
                return False
            
            # Diagnóstico adicional para valores sospechosos
            if marker_z == 0 and button_x == 0:
                print(f"⚠️ Ambos valores son 0: markerZ={marker_z}, buttonX={button_x} - posible problema de detección")
                return False
                
            print(f"✅ Datos válidos: markerZ={marker_z:.2f}cm, buttonX={button_x:.2f}cm")
            return True
            
        except Exception as e:
            print(f"⚠️ Error validando datos: {e}")
            return False
    
    def publish_distance(self, distancia: float, marker_value: Optional[float] = None) -> bool:
        """Método de compatibilidad para publicar distancia directamente
        
        Args:
            distancia: Distancia a enviar en buttonX
            marker_value: Valor opcional para el campo marker
        """
        if not self.dicapua_connected or not self.dicapua_client:
            self.logger.warning("No conectado al broker DicapuaIoT")
            return False
        
        # Control de umbral para evitar spam
        current_time = time.time()
        if current_time - self.last_publish_time < self.publish_threshold:
            return False
        
        try:
            # Generar timestamp en formato UTC con microsegundos
            now_utc = datetime.datetime.now()
            mlsec = repr(now_utc).split(",")[-1][-7:-1].replace(" ", "0")
            timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%S.{}Z".format(mlsec))
            
            # Usar la distancia como valor por defecto si marker_value es None
            marker_val = marker_value if marker_value is not None else distancia
        
            payload = {
                "timestamp": timestamp,
                "markerZ": marker_val,
                "buttonX": distancia,
                "marker": marker_val*0.91*10,
            }
            
            # Convertir a JSON
            msg = json.dumps(payload)
            self.logger.info(f"📤 Payload directo enviado: {payload}")
            
            # Publicar en el topic YOLOframe
            result = self.dicapua_client.publish(self.config.topic.publish["YOLOframe"], msg)
            
            if result.rc == mqtt_client.MQTT_ERR_SUCCESS:
                self.last_publish_time = current_time
                self.logger.debug(f"Distancia publicada exitosamente: {distancia:.2f} cm")
                return True
            else:
                self.logger.error(f"Error al publicar: {result.rc}")
                return False
                
        except Exception as e:
            # Manejo de errores siguiendo el formato original
            now_utc = datetime.datetime.now()
            mlsec = repr(now_utc).split(",")[-1][-7:-1].replace(" ", "0")
            timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%S.{}Z".format(mlsec))
            self.logger.error(f"{timestamp} | Error sending data: {e}")
            time.sleep(0.1)
            return False
    
    def start_client(self) -> bool:
        """Inicia ambos clientes MQTT (DicapuaIoT y local)"""
        success = True
        
        # Conectar a DicapuaIoT
        dicapua_client = self.connect_dicapua_mqtt()
        if dicapua_client:
            dicapua_client.loop_start()
            self.logger.info("🚀 Cliente DicapuaIoT iniciado")
        else:
            success = False
            self.logger.error("❌ Error iniciando cliente DicapuaIoT")
        
        # Conectar a MQTT local
        local_client = self.connect_local_mqtt()
        if local_client:
            local_client.loop_start()
            self.logger.info("🚀 Cliente MQTT local iniciado")
        else:
            success = False
            self.logger.error("❌ Error iniciando cliente MQTT local")
        
        return success
    
    def stop_client(self) -> None:
        """Detiene ambos clientes MQTT"""
        # Detener reconexión automática
        self.should_reconnect = False
        
        if self.dicapua_client:
            self.dicapua_client.loop_stop()
            self.dicapua_client.disconnect()
            self.dicapua_connected = False
            self.logger.info("🔌 Cliente DicapuaIoT detenido")
        
        if self.local_client:
            self.local_client.loop_stop()
            self.local_client.disconnect()
            self.local_connected = False
            self.logger.info("🔌 Cliente MQTT local detenido")
        
        # Esperar a que termine el hilo de reconexión
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=2)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Retorna el estado de ambas conexiones"""
        return {
            'dicapua_connected': self.dicapua_connected,
            'local_connected': self.local_connected,
            'dicapua_broker': self.config.broker,
            'local_broker': self.local_broker,
            'client_id': self.config.client_id,
            'use_certs': self.config.connectCerts,
            'marker_distance': self.marker_distance,
            'portico_distance': self.portico_distance,
            'last_marker_time': self.last_marker_time,
            'last_portico_time': self.last_portico_time
        }
    
    @property
    def is_connected(self) -> bool:
        """Propiedad de compatibilidad para verificar conexión DicapuaIoT"""
        return self.dicapua_connected
    
    def set_publish_threshold(self, threshold_seconds: float) -> None:
        """Establece el umbral mínimo entre publicaciones"""
        self.publish_threshold = max(0.01, threshold_seconds)
    
    def validate_distance(self, distancia: float) -> bool:
        """Valida que la distancia esté en rango válido"""
        return 0 < distancia < 1000
    
    def get_latest_distances(self) -> Dict[str, Any]:
        """Obtiene las últimas distancias recibidas"""
        current_time = time.time()
        return {
            'marker_distance': self.marker_distance,
            'portico_distance': self.portico_distance,
            'marker_age_seconds': current_time - self.last_marker_time if self.last_marker_time > 0 else None,
            'portico_age_seconds': current_time - self.last_portico_time if self.last_portico_time > 0 else None,
            'marker_recent': (current_time - self.last_marker_time) < 5.0 if self.last_marker_time > 0 else False,
            'portico_recent': (current_time - self.last_portico_time) < 5.0 if self.last_portico_time > 0 else False
        }
    
    def receive_distance_data(self, source, distance_cm):
        """Recibe datos de distancia directamente (sin MQTT local)"""
        try:
            import datetime
            timestamp = datetime.datetime.now().isoformat() + "Z"
            
            if source == "marcador":
                self.last_marker_data = {
                    'distance_cm': distance_cm,
                    'timestamp': timestamp,
                    'source': 'marker_calculator'
                }
                print(f"📏 Datos marcador recibidos directamente: {distance_cm:.2f}cm")
                
            elif source == "portico":
                self.last_portico_data = {
                    'distance_cm': distance_cm,
                    'timestamp': timestamp,
                    'source': 'portico_calculator'
                }
                print(f"🏗️ Datos pórtico recibidos directamente: {distance_cm:.2f}cm")
            
            # Enviar datos combinados si tenemos ambos
            self._send_combined_data_to_dicapuaiot()
            
        except Exception as e:
            print(f"❌ Error recibiendo datos directos: {e}")
    
    def send_distance_data(self, payload):
        """Recibe datos de distancia del pórtico-pulsador"""
        try:
            distance_cm = payload.get('distance_cm')
            if distance_cm is not None:
                self.last_portico_data = {
                    'distance_cm': distance_cm,
                    'timestamp': payload.get('timestamp'),
                    'source': 'portico_calculator'
                }
                print(f"🏗️ Datos pórtico recibidos: {distance_cm:.2f}cm")
                self._send_combined_data_to_dicapuaiot()
                return True
            return False
        except Exception as e:
            print(f"❌ Error procesando datos pórtico: {e}")
            return False
    
    def send_marker_distance(self, payload):
        """Recibe datos de distancia del marcador"""
        try:
            distance_cm = payload.get('distance_cm')
            if distance_cm is not None:
                self.last_marker_data = {
                    'distance_cm': distance_cm,
                    'timestamp': payload.get('timestamp'),
                    'source': 'marker_calculator'
                }
                print(f"📏 Datos marcador recibidos: {distance_cm:.2f}cm")
                self._send_combined_data_to_dicapuaiot()
                return True
            return False
        except Exception as e:
            print(f"❌ Error procesando datos marcador: {e}")
            return False
    
    def _publish_with_retry(self, topic: str, payload: str, retries: int = 3) -> bool:
        """Publica un mensaje con reintentos automáticos"""
        for attempt in range(retries):
            if self.dicapua_connected and self.dicapua_client:
                try:
                    result = self.dicapua_client.publish(topic, payload)
                    if result.rc == 0:
                        self.logger.debug(f"📤 Mensaje publicado exitosamente (intento {attempt + 1})")
                        return True
                    else:
                        self.logger.warning(f"⚠️ Error publicando (intento {attempt + 1}): código {result.rc}")
                except Exception as e:
                    self.logger.error(f"❌ Excepción publicando (intento {attempt + 1}): {e}")
            else:
                self.logger.warning(f"⚠️ No conectado para publicar (intento {attempt + 1})")
            
            # Esperar antes del siguiente intento
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Backoff exponencial
                self.logger.info(f"⏳ Esperando {wait_time}s antes del siguiente intento...")
                time.sleep(wait_time)
        
        return False
    
    def _schedule_reconnect(self):
        """Programa una reconexión automática con backoff exponencial"""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
            
        def reconnect_worker():
            delay = self.reconnect_delay
            while self.should_reconnect and not self.dicapua_connected:
                self.logger.info(f"🔄 Intentando reconectar en {delay} segundos...")
                time.sleep(delay)
                
                with self.connection_lock:
                    if not self.dicapua_connected and self.should_reconnect:
                        try:
                            if self.dicapua_client:
                                self.dicapua_client.reconnect()
                                self.logger.info("✅ Reconexión exitosa")
                                self.reconnect_delay = 1  # Reset delay
                                break
                        except Exception as e:
                            self.logger.error(f"❌ Error en reconexión: {e}")
                            delay = min(delay * 2, self.max_reconnect_delay)
        
        self.reconnect_thread = threading.Thread(target=reconnect_worker, daemon=True)
        self.reconnect_thread.start()
    
    def start_client_direct_mode(self):
        """Inicia solo el cliente DicapuaIoT (sin MQTT local)"""
        print("🔄 Iniciando en modo directo (sin MQTT local)")
        client = self.connect_dicapua_mqtt()
        if client:
            client.loop_start()
            print("✅ Cliente DicapuaIoT iniciado en modo directo")
            return True
        return False