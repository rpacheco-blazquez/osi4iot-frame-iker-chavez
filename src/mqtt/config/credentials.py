"""Módulo de credenciales MQTT para DicapuaIoT"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class MQTTCredentials:
    """Clase para manejar credenciales MQTT de DicapuaIoT"""
    
    broker: str
    username: str
    password: str
    client_id: str
    connect_certs: bool = False
    ca_certs: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None
    
    @classmethod
    def from_file(cls, config_path: str) -> 'MQTTCredentials':
        """Carga credenciales desde un archivo JSON"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        return cls(
            broker=config.get('broker', 'localhost'),
            username=config.get('username', ''),
            password=config.get('password', ''),
            client_id=config.get('client_id', 'mqtt_client'),
            connect_certs=config.get('connectCerts', False),
            ca_certs=config.get('ca_certs'),
            certfile=config.get('certfile'),
            keyfile=config.get('keyfile')
        )
    
    @classmethod
    def from_env(cls) -> 'MQTTCredentials':
        """Carga credenciales desde variables de entorno"""
        return cls(
            broker=os.getenv('MQTT_BROKER', 'localhost'),
            username=os.getenv('MQTT_USERNAME', ''),
            password=os.getenv('MQTT_PASSWORD', ''),
            client_id=os.getenv('MQTT_CLIENT_ID', 'mqtt_client'),
            connect_certs=os.getenv('MQTT_USE_CERTS', 'false').lower() == 'true',
            ca_certs=os.getenv('MQTT_CA_CERTS'),
            certfile=os.getenv('MQTT_CERTFILE'),
            keyfile=os.getenv('MQTT_KEYFILE')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte las credenciales a diccionario"""
        return {
            'broker': self.broker,
            'username': self.username,
            'password': self.password,
            'client_id': self.client_id,
            'connect_certs': self.connect_certs,
            'ca_certs': self.ca_certs,
            'certfile': self.certfile,
            'keyfile': self.keyfile
        }
    
    def validate(self) -> bool:
        """Valida que las credenciales sean válidas"""
        if not self.broker:
            return False
            
        if self.connect_certs:
            # Si usa certificados, verificar que existan los archivos
            if not all([self.ca_certs, self.certfile, self.keyfile]):
                return False
            if not all([os.path.exists(f) for f in [self.ca_certs, self.certfile, self.keyfile] if f]):
                return False
        else:
            # Si no usa certificados, verificar usuario y contraseña
            if not self.username or not self.password:
                return False
                
        return True