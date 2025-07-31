import json
import os
from pathlib import Path
from typing import Dict, Any

class I18nManager:
    """Gestor de internacionalización."""
    
    def __init__(self, default_language: str = 'es'):
        """Inicializa el gestor de i18n.
        
        Args:
            default_language: Idioma por defecto ('es' o 'en')
        """
        self.current_language = default_language
        self.translations = {}
        self.base_path = Path(__file__).parent.parent.parent / 'locales'
        self.load_translations()
    
    def load_translations(self):
        """Carga todas las traducciones disponibles."""
        try:
            # Cargar español
            es_path = self.base_path / 'es.json'
            if es_path.exists():
                with open(es_path, 'r', encoding='utf-8') as f:
                    self.translations['es'] = json.load(f)
            
            # Cargar inglés
            en_path = self.base_path / 'en.json'
            if en_path.exists():
                with open(en_path, 'r', encoding='utf-8') as f:
                    self.translations['en'] = json.load(f)
                    
        except Exception as e:
            print(f"Error cargando traducciones: {e}")
            # Fallback a traducciones básicas
            self.translations = {
                'es': {'app_title': 'Interfaz de Detección Interactiva - Pórtico Digital'},
                'en': {'app_title': 'Interactive Detection Interface - Digital Gantry'}
            }
    
    def set_language(self, language: str):
        """Cambia el idioma actual.
        
        Args:
            language: Código del idioma ('es' o 'en')
        """
        if language in self.translations:
            self.current_language = language
        else:
            print(f"Idioma no soportado: {language}")
    
    def get_language(self) -> str:
        """Obtiene el idioma actual.
        
        Returns:
            Código del idioma actual
        """
        return self.current_language
    
    def t(self, key: str, **kwargs) -> str:
        """Obtiene una traducción.
        
        Args:
            key: Clave de la traducción
            **kwargs: Parámetros para formatear la cadena
            
        Returns:
            Texto traducido
        """
        try:
            # Buscar en el idioma actual
            if self.current_language in self.translations:
                translation = self._get_nested_value(self.translations[self.current_language], key)
                if translation:
                    return translation.format(**kwargs) if kwargs else translation
            
            # Fallback al español si no se encuentra
            if 'es' in self.translations and self.current_language != 'es':
                translation = self._get_nested_value(self.translations['es'], key)
                if translation:
                    return translation.format(**kwargs) if kwargs else translation
            
            # Si no se encuentra, devolver la clave
            return key
            
        except Exception as e:
            print(f"Error obteniendo traducción para '{key}': {e}")
            return key
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> str:
        """Obtiene un valor anidado usando notación de punto.
        
        Args:
            data: Diccionario de datos
            key: Clave con notación de punto (ej: 'menu.file.open')
            
        Returns:
            Valor encontrado o None
        """
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_available_languages(self) -> Dict[str, str]:
        """Obtiene los idiomas disponibles.
        
        Returns:
            Diccionario con códigos y nombres de idiomas
        """
        return {
            'es': 'Español',
            'en': 'English (UK)'
        }

# Instancia global del gestor de i18n
_i18n_manager = I18nManager()

def get_i18n() -> I18nManager:
    """Obtiene la instancia global del gestor de i18n.
    
    Returns:
        Instancia del gestor de i18n
    """
    return _i18n_manager

def t(key: str, **kwargs) -> str:
    """Función de conveniencia para obtener traducciones.
    
    Args:
        key: Clave de la traducción
        **kwargs: Parámetros para formatear
        
    Returns:
        Texto traducido
    """
    return _i18n_manager.t(key, **kwargs)