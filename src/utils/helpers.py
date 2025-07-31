"""Funciones auxiliares y utilidades para el proyecto de gemelo digital."""

import os
import json
import yaml
import csv
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import time
from pathlib import Path
import hashlib
import pickle
from dataclasses import dataclass, asdict
import math

@dataclass
class LogEntry:
    """Entrada de log estructurada."""
    timestamp: str
    level: str
    module: str
    message: str
    data: Optional[Dict] = None

class Logger:
    """Logger personalizado para el proyecto."""
    
    def __init__(self, name: str, log_dir: str = "data/logs"):
        """Inicializa el logger.
        
        Args:
            name: Nombre del logger
            log_dir: Directorio para archivos de log
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Handler para archivo
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str, data: Optional[Dict] = None):
        """Log de información."""
        self.logger.info(message)
        if data:
            self._save_structured_log('INFO', message, data)
    
    def warning(self, message: str, data: Optional[Dict] = None):
        """Log de advertencia."""
        self.logger.warning(message)
        if data:
            self._save_structured_log('WARNING', message, data)
    
    def error(self, message: str, data: Optional[Dict] = None):
        """Log de error."""
        self.logger.error(message)
        if data:
            self._save_structured_log('ERROR', message, data)
    
    def _save_structured_log(self, level: str, message: str, data: Dict):
        """Guarda log estructurado en JSON."""
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            module=self.name,
            message=message,
            data=data
        )
        
        json_file = self.log_dir / f"{self.name}_structured_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(json_file, 'a', encoding='utf-8') as f:
            json.dump(asdict(log_entry), f, ensure_ascii=False)
            f.write('\n')

class ConfigManager:
    """Gestor de configuración centralizado."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Inicializa el gestor de configuración.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.watchers = []
    
    def load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde archivo.
        
        Returns:
            Diccionario con la configuración
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                if self.config_path.suffix.lower() == '.yaml':
                    return yaml.safe_load(file)
                elif self.config_path.suffix.lower() == '.json':
                    return json.load(file)
                else:
                    raise ValueError(f"Formato de archivo no soportado: {self.config_path.suffix}")
        except FileNotFoundError:
            print(f"Archivo de configuración no encontrado: {self.config_path}")
            return {}
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            return {}
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración usando notación de punto.
        
        Args:
            key_path: Ruta de la clave (ej: 'vision.confidence_threshold')
            default: Valor por defecto si no se encuentra la clave
            
        Returns:
            Valor de configuración
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """Establece un valor de configuración.
        
        Args:
            key_path: Ruta de la clave
            value: Nuevo valor
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save_config(self):
        """Guarda la configuración actual al archivo."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                if self.config_path.suffix.lower() == '.yaml':
                    yaml.dump(self.config, file, default_flow_style=False, allow_unicode=True)
                elif self.config_path.suffix.lower() == '.json':
                    json.dump(self.config, file, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar configuración: {e}")

class DataManager:
    """Gestor de datos para guardar y cargar información."""
    
    def __init__(self, base_dir: str = "data"):
        """Inicializa el gestor de datos.
        
        Args:
            base_dir: Directorio base para datos
        """
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.logs_dir = self.base_dir / "logs"
        
        # Crear directorios si no existen
        for dir_path in [self.raw_dir, self.processed_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def save_json(self, data: Dict[str, Any], filename: str, 
                  subdir: str = "processed") -> bool:
        """Guarda datos en formato JSON.
        
        Args:
            data: Datos a guardar
            filename: Nombre del archivo
            subdir: Subdirectorio (raw, processed, logs)
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            target_dir = self.base_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = target_dir / f"{filename}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            return True
        except Exception as e:
            print(f"Error al guardar JSON: {e}")
            return False
    
    def load_json(self, filename: str, subdir: str = "processed") -> Optional[Dict[str, Any]]:
        """Carga datos desde archivo JSON.
        
        Args:
            filename: Nombre del archivo
            subdir: Subdirectorio
            
        Returns:
            Datos cargados o None si hay error
        """
        try:
            file_path = self.base_dir / subdir / f"{filename}.json"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al cargar JSON: {e}")
            return None
    
    def save_csv(self, data: List[Dict[str, Any]], filename: str, 
                 subdir: str = "processed") -> bool:
        """Guarda datos en formato CSV.
        
        Args:
            data: Lista de diccionarios con datos
            filename: Nombre del archivo
            subdir: Subdirectorio
            
        Returns:
            True si se guardó exitosamente
        """
        if not data:
            return False
        
        try:
            target_dir = self.base_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = target_dir / f"{filename}.csv"
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            
            return True
        except Exception as e:
            print(f"Error al guardar CSV: {e}")
            return False
    
    def save_pickle(self, data: Any, filename: str, subdir: str = "processed") -> bool:
        """Guarda datos en formato pickle.
        
        Args:
            data: Datos a guardar
            filename: Nombre del archivo
            subdir: Subdirectorio
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            target_dir = self.base_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = target_dir / f"{filename}.pkl"
            
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            
            return True
        except Exception as e:
            print(f"Error al guardar pickle: {e}")
            return False
    
    def load_pickle(self, filename: str, subdir: str = "processed") -> Any:
        """Carga datos desde archivo pickle.
        
        Args:
            filename: Nombre del archivo
            subdir: Subdirectorio
            
        Returns:
            Datos cargados o None si hay error
        """
        try:
            file_path = self.base_dir / subdir / f"{filename}.pkl"
            
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error al cargar pickle: {e}")
            return None

class MathUtils:
    """Utilidades matemáticas para cálculos del gemelo digital."""
    
    @staticmethod
    def distance_3d(p1: Tuple[float, float, float], 
                   p2: Tuple[float, float, float]) -> float:
        """Calcula la distancia euclidiana entre dos puntos 3D.
        
        Args:
            p1: Primer punto (x, y, z)
            p2: Segundo punto (x, y, z)
            
        Returns:
            Distancia euclidiana
        """
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
    
    @staticmethod
    def angle_between_vectors(v1: Tuple[float, float, float], 
                            v2: Tuple[float, float, float]) -> float:
        """Calcula el ángulo entre dos vectores 3D.
        
        Args:
            v1: Primer vector
            v2: Segundo vector
            
        Returns:
            Ángulo en radianes
        """
        v1_array = np.array(v1)
        v2_array = np.array(v2)
        
        cos_angle = np.dot(v1_array, v2_array) / (np.linalg.norm(v1_array) * np.linalg.norm(v2_array))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Evitar errores de precisión
        
        return math.acos(cos_angle)
    
    @staticmethod
    def interpolate_linear(p1: Tuple[float, float, float], 
                          p2: Tuple[float, float, float], 
                          t: float) -> Tuple[float, float, float]:
        """Interpolación lineal entre dos puntos 3D.
        
        Args:
            p1: Punto inicial
            p2: Punto final
            t: Factor de interpolación (0-1)
            
        Returns:
            Punto interpolado
        """
        t = max(0, min(1, t))  # Clamp t entre 0 y 1
        
        return (
            p1[0] + t * (p2[0] - p1[0]),
            p1[1] + t * (p2[1] - p1[1]),
            p1[2] + t * (p2[2] - p1[2])
        )
    
    @staticmethod
    def moving_average(data: List[float], window_size: int) -> List[float]:
        """Calcula la media móvil de una serie de datos.
        
        Args:
            data: Serie de datos
            window_size: Tamaño de la ventana
            
        Returns:
            Lista con la media móvil
        """
        if len(data) < window_size:
            return data
        
        result = []
        for i in range(len(data) - window_size + 1):
            window = data[i:i + window_size]
            result.append(sum(window) / window_size)
        
        return result
    
    @staticmethod
    def normalize_vector(vector: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Normaliza un vector 3D.
        
        Args:
            vector: Vector a normalizar
            
        Returns:
            Vector normalizado
        """
        magnitude = math.sqrt(sum(x**2 for x in vector))
        
        if magnitude == 0:
            return (0, 0, 0)
        
        return tuple(x / magnitude for x in vector)
    
    @staticmethod
    def low_pass_filter(data: List[float], alpha: float = 0.1) -> List[float]:
        """Aplica un filtro pasa-bajos simple.
        
        Args:
            data: Datos a filtrar
            alpha: Factor de suavizado (0-1)
            
        Returns:
            Datos filtrados
        """
        if not data:
            return []
        
        filtered = [data[0]]
        
        for i in range(1, len(data)):
            filtered_value = alpha * data[i] + (1 - alpha) * filtered[i-1]
            filtered.append(filtered_value)
        
        return filtered

class PerformanceMonitor:
    """Monitor de rendimiento para el sistema."""
    
    def __init__(self):
        """Inicializa el monitor de rendimiento."""
        self.start_times = {}
        self.execution_times = {}
        self.call_counts = {}
    
    def start_timer(self, operation: str):
        """Inicia un temporizador para una operación.
        
        Args:
            operation: Nombre de la operación
        """
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """Termina un temporizador y registra el tiempo.
        
        Args:
            operation: Nombre de la operación
            
        Returns:
            Tiempo de ejecución en segundos
        """
        if operation not in self.start_times:
            return 0.0
        
        execution_time = time.time() - self.start_times[operation]
        
        if operation not in self.execution_times:
            self.execution_times[operation] = []
            self.call_counts[operation] = 0
        
        self.execution_times[operation].append(execution_time)
        self.call_counts[operation] += 1
        
        del self.start_times[operation]
        
        return execution_time
    
    def get_statistics(self, operation: str) -> Dict[str, float]:
        """Obtiene estadísticas de rendimiento para una operación.
        
        Args:
            operation: Nombre de la operación
            
        Returns:
            Diccionario con estadísticas
        """
        if operation not in self.execution_times:
            return {}
        
        times = self.execution_times[operation]
        
        return {
            'count': self.call_counts[operation],
            'total_time': sum(times),
            'average_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'last_time': times[-1] if times else 0
        }
    
    def get_all_statistics(self) -> Dict[str, Dict[str, float]]:
        """Obtiene estadísticas de todas las operaciones.
        
        Returns:
            Diccionario con estadísticas de todas las operaciones
        """
        return {op: self.get_statistics(op) for op in self.execution_times.keys()}

def create_hash(data: str) -> str:
    """Crea un hash MD5 de una cadena.
    
    Args:
        data: Cadena a hashear
        
    Returns:
        Hash MD5 en hexadecimal
    """
    return hashlib.md5(data.encode()).hexdigest()

def ensure_directory(path: Union[str, Path]) -> Path:
    """Asegura que un directorio existe, creándolo si es necesario.
    
    Args:
        path: Ruta del directorio
        
    Returns:
        Path object del directorio
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """Formatea un timestamp para uso en nombres de archivo.
    
    Args:
        timestamp: Timestamp a formatear (usa datetime.now() si es None)
        
    Returns:
        Timestamp formateado
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    return timestamp.strftime("%Y%m%d_%H%M%S")

def validate_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """Valida que una configuración tenga las claves requeridas.
    
    Args:
        config: Configuración a validar
        required_keys: Lista de claves requeridas
        
    Returns:
        True si la configuración es válida
    """
    for key in required_keys:
        if key not in config:
            print(f"Clave requerida faltante en configuración: {key}")
            return False
    
    return True