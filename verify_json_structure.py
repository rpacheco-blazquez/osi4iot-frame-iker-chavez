#!/usr/bin/env python3
"""
Script para verificar que los archivos de idiomas tienen la misma estructura JSON.
"""

import json
import sys
from pathlib import Path

def get_all_keys(data, prefix=""):
    """Obtiene todas las claves de un diccionario anidado."""
    keys = set()
    
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            
            if isinstance(value, dict):
                keys.update(get_all_keys(value, full_key))
    
    return keys

def compare_json_structures(file1_path, file2_path):
    """Compara la estructura de dos archivos JSON."""
    
    # Cargar archivos
    try:
        with open(file1_path, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        
        with open(file2_path, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
    except Exception as e:
        print(f"❌ Error cargando archivos: {e}")
        return False
    
    # Obtener todas las claves
    keys1 = get_all_keys(data1)
    keys2 = get_all_keys(data2)
    
    # Comparar
    missing_in_file2 = keys1 - keys2
    missing_in_file1 = keys2 - keys1
    
    print(f"🔍 Comparando estructuras JSON:")
    print(f"   📁 Archivo 1: {file1_path}")
    print(f"   📁 Archivo 2: {file2_path}")
    print()
    
    print(f"📊 Estadísticas:")
    print(f"   🔑 Claves en archivo 1: {len(keys1)}")
    print(f"   🔑 Claves en archivo 2: {len(keys2)}")
    print(f"   🤝 Claves comunes: {len(keys1 & keys2)}")
    print()
    
    if missing_in_file2:
        print(f"❌ Claves que faltan en {file2_path.name}:")
        for key in sorted(missing_in_file2):
            print(f"   - {key}")
        print()
    
    if missing_in_file1:
        print(f"❌ Claves que faltan en {file1_path.name}:")
        for key in sorted(missing_in_file1):
            print(f"   - {key}")
        print()
    
    if not missing_in_file1 and not missing_in_file2:
        print("✅ ¡Perfecto! Ambos archivos tienen exactamente la misma estructura JSON.")
        return True
    else:
        print("⚠️ Los archivos tienen estructuras diferentes.")
        return False

def main():
    """Función principal."""
    
    # Rutas de los archivos
    base_path = Path(__file__).parent / "locales"
    es_file = base_path / "es.json"
    en_file = base_path / "en.json"
    
    print("🌐 Verificador de Estructura JSON - Sistema de Idiomas")
    print("=" * 60)
    print()
    
    # Verificar que los archivos existen
    if not es_file.exists():
        print(f"❌ No se encontró: {es_file}")
        return False
    
    if not en_file.exists():
        print(f"❌ No se encontró: {en_file}")
        return False
    
    # Comparar estructuras
    result = compare_json_structures(es_file, en_file)
    
    print()
    print("=" * 60)
    
    if result:
        print("🎉 ¡Verificación completada exitosamente!")
        print("   Los archivos de idiomas están perfectamente sincronizados.")
    else:
        print("🔧 Se requiere sincronización de los archivos de idiomas.")
    
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)