# Guía de Instalación de Dependencias

Este proyecto incluye varios archivos de requirements para diferentes casos de uso:

## 📦 Archivos Disponibles

### `requirements.txt` (Recomendado)
- **Uso**: Instalación estándar para la mayoría de usuarios
- **Características**: Rangos de versiones compatibles
- **Ventajas**: Máxima compatibilidad entre sistemas
- **Instalación**: `pip install -r requirements.txt`

### `requirements-minimal.txt`
- **Uso**: Instalación mínima con solo dependencias esenciales
- **Características**: Solo paquetes principales necesarios
- **Ventajas**: Instalación más rápida, menos conflictos
- **Instalación**: `pip install -r requirements-minimal.txt`

### `requirements-exact.txt`
- **Uso**: Replicación exacta del entorno de desarrollo
- **Características**: Versiones exactas (pip freeze)
- **Ventajas**: Reproducibilidad total del entorno
- **Desventajas**: Puede no funcionar en otros sistemas
- **Instalación**: `pip install -r requirements-exact.txt`

## 🚀 Instalación Recomendada

```bash
# 1. Crear entorno virtual
python -m venv .venv

# 2. Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Actualizar pip
python -m pip install --upgrade pip

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Verificar instalación
pip check
```

## 🔧 Solución de Problemas

### Error de versiones incompatibles
Si encuentras errores como el mostrado en el terminal, usa:
```bash
pip install -r requirements-minimal.txt
```

### Error de compilación de paquetes
```bash
# Actualizar herramientas de construcción
pip install --upgrade setuptools wheel
pip install -r requirements.txt
```

### Conflictos de dependencias
```bash
# Limpiar caché de pip
pip cache purge
# Reinstalar desde cero
pip install --force-reinstall -r requirements.txt
```

## 📋 Verificación Post-Instalación

```bash
# Verificar que no hay conflictos
pip check

# Listar paquetes instalados
pip list

# Probar importaciones principales
python -c "import cv2, torch, ultralytics, PyQt5; print('✅ Todas las dependencias principales funcionan')"
```

## 🎯 Casos de Uso

- **Desarrollo**: `requirements.txt`
- **Producción**: `requirements.txt`
- **CI/CD**: `requirements-exact.txt`
- **Instalación rápida**: `requirements-minimal.txt`
- **Debugging**: `requirements-exact.txt`

## 📝 Notas Importantes

1. **Python 3.8+** requerido
2. **Windows**: Puede requerir Visual Studio Build Tools para algunos paquetes
3. **Linux**: Instalar `python3-tk` si es necesario: `sudo apt-get install python3-tk`
4. **macOS**: Instalar con Homebrew si es necesario: `brew install python-tk`

## 🔄 Actualización de Requirements

Para actualizar los archivos de requirements:
```bash
# Generar nuevo requirements-exact.txt
pip freeze > requirements-exact.txt

# Verificar compatibilidad
pip check
```