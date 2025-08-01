
# Ejemplo de DicapuaPublisher robusto con reconexión automática
import time
import threading
import paho.mqtt.client as mqtt
from typing import Optional

class RobustDicapuaPublisher:
    def __init__(self, config):
        self.config = config
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.reconnect_thread = None
        self.should_reconnect = True
        self.reconnect_delay = 1  # Inicial
        self.max_reconnect_delay = 60
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.reconnect_delay = 1  # Reset delay
            print("✅ Conectado a DicapuaIoT")
        else:
            print(f"❌ Error conexión: {rc}")
            
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            print(f"⚠️ Desconexión inesperada: {rc}")
            if self.should_reconnect:
                self._schedule_reconnect()
                
    def _schedule_reconnect(self):
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
            
        def reconnect_worker():
            while self.should_reconnect and not self.connected:
                try:
                    print(f"🔄 Reintentando conexión en {self.reconnect_delay}s...")
                    time.sleep(self.reconnect_delay)
                    
                    if self.client:
                        self.client.reconnect()
                        
                    # Exponential backoff
                    self.reconnect_delay = min(
                        self.reconnect_delay * 2, 
                        self.max_reconnect_delay
                    )
                    
                except Exception as e:
                    print(f"❌ Error en reconexión: {e}")
                    
        self.reconnect_thread = threading.Thread(target=reconnect_worker)
        self.reconnect_thread.daemon = True
        self.reconnect_thread.start()
        
    def connect(self):
        self.client = mqtt.Client(
            client_id=self.config.client_id + "_robust",
            clean_session=False  # Sesión persistente
        )
        
        # Configurar SSL
        self.client.tls_set(
            ca_certs=self.config.certs["ca_certs"],
            certfile=self.config.certs["certfile"],
            keyfile=self.config.certs["keyfile"]
        )
        
        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        # Conectar con keepalive largo
        self.client.connect(self.config.broker, 8883, 300)
        self.client.loop_start()
        
    def publish_with_retry(self, topic, payload, retries=3):
        for attempt in range(retries):
            if self.connected:
                try:
                    result = self.client.publish(topic, payload)
                    if result.rc == 0:
                        return True
                except Exception as e:
                    print(f"❌ Error publicando (intento {attempt+1}): {e}")
            
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Backoff
                
        return False
        
    def stop(self):
        self.should_reconnect = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
