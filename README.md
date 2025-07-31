# 🏗️ Digital Twin del Pórtico - Gemelo Digital OSI4IoT

## 📋 Descripción del Proyecto

Este proyecto implementa un **gemelo digital avanzado** para un sistema de pórtico grúa, integrando visión por computador con YOLO v8, análisis físico en tiempo real, comunicación IoT bidireccional y visualización interactiva. El sistema permite monitorear, analizar y predecir el comportamiento de cargas aplicadas en un pórtico mediante técnicas de inteligencia artificial, detección de movimiento inteligente y comunicación con plataformas IoT externas.

## 🎯 Características Principales

### 🔍 Visión por Computador Avanzada
- **Detección de objetos** con YOLO v8 personalizado (modelo `best.pt`)
- **Detección de pose** con keypoints para cálculo preciso de distancias
- **Tracking en tiempo real** de múltiples objetos con filtros Kalman
- **Análisis de movimiento inteligente** con detección de patrones
- **Calibración automática** de píxeles a centímetros
- **Filtrado temporal** y corrección de errores geométricos

### 📡 Comunicación IoT Bidireccional
- **Protocolo MQTT** para transmisión de datos a DicapuaIoT
- **Comunicación directa** sin broker local (modo directo)
- **Integración OSI4IoT** para plataformas industriales
- **Validación de datos** antes del envío
- **Reconexión automática** y manejo de errores
- **Formato JSON** estándar con timestamps y metadatos

### 📊 Visualización e Interfaz Interactiva
- **Interfaz gráfica moderna** con Tkinter y controles avanzados
- **Gráficos en tiempo real** con matplotlib integrado
- **Dashboard multilingüe** (español/inglés)
- **Sistema de coordenadas** configurable y calibrable
- **Visualización de trayectorias** y historial de movimientos
- **Controles de filtros** y parámetros en tiempo real

## 🏗️ Arquitectura del Sistema

```
osi4iot-gantry-project/
├── 📁 config/                 # Configuración del proyecto
│   └── config.yaml           # Configuración principal (MQTT, visión, física)
├── 📁 data/                   # Almacenamiento de datos
│   ├── logs/                 # Logs del sistema con rotación automática
│   ├── raw/                  # Datos sin procesar
│   └── processed/            # Datos procesados y estadísticas
├── 📁 src/                    # Código fuente principal
│   ├── 📁 vision/            # Módulos de visión por computadora
│   │   ├── detector.py       # Detección YOLO v8 con pose
│   │   └── tracker.py        # Tracking multi-objeto
│   ├── 📁 mqtt/              # Comunicación IoT
│   │   ├── dicapua_publisher.py # Publicador DicapuaIoT
│   │   └── config/           # Configuraciones MQTT y credenciales
│   ├── 📁 postprocess/       # Procesamiento avanzado
│   │   ├── distance_calculator.py     # Cálculo de distancias pórtico-pulsador
│   │   ├── marker_distance_calculator.py # Cálculo de distancias marcador
│   │   ├── movement_detector.py       # Detección inteligente de movimiento
│   │   └── coordinate_axis_drawer.py  # Sistema de coordenadas
│   ├── 📁 gui/               # Interfaz gráfica
│   │   └── interactive_interface.py  # Interfaz principal interactiva
│   ├── 📁 visualization/     # Visualización
│   │   └── visualizer.py     # Renderizado 2D/3D en tiempo real
│   ├── 📁 utils/             # Utilidades
│   │   ├── helpers.py        # Funciones auxiliares
│   │   └── i18n.py          # Sistema de internacionalización
│   ├── main.py               # Sistema principal (detección básica)
│   └── run_pipeline.py       # Pipeline completo de procesamiento
├── 📁 ui/                     # Diseños de interfaz
│   └── interface.ui          # Diseño Qt para futuras extensiones
├── 📁 models/                 # Modelos entrenados
│   └── best.pt              # Modelo YOLO v8 personalizado
├── 📁 locales/               # Archivos de idioma
│   ├── en.json              # Traducciones en inglés
│   └── es.json              # Traducciones en español
├── requirements.txt          # Dependencias del proyecto
├── README.md                 # Este archivo
└── .gitignore               # Archivos excluidos del repositorio
```

### 🔧 Componentes Principales

#### 🎯 Calculadores de Distancia
- **DistanceCalculator**: Mide distancias entre pórtico y pulsador
- **MarkerDistanceCalculator**: Calcula distancias del marcador
- **MovementDetector**: Detecta movimientos inteligentes y filtra ruido

#### 🌐 Comunicación IoT
- **DicapuaPublisher**: Envía datos a plataforma DicapuaIoT
- **Modo directo**: Comunicación sin broker MQTT local
- **Validación de datos**: Verifica integridad antes del envío

#### 🖥️ Interfaces de Usuario
- **InteractiveInterface**: Interfaz principal con controles en tiempo real
- **Sistema multilingüe**: Soporte para español e inglés
- **Configuración dinámica**: Ajustes sin reiniciar la aplicación

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.8 o superior
- Cámara web o archivo de video para análisis
- (Opcional) Conexión a plataforma DicapuaIoT para transmisión de datos
- Sistema operativo: Windows, Linux o macOS

### Instalación

1. **Clonar el repositorio**
```bash
git clone <url-del-repositorio>
cd osi4iot-gantry-project
```

2. **Crear entorno virtual**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar credenciales DicapuaIoT** (opcional)
```bash
# Editar src/mqtt/config/dicapuaiot/dicapuaiot.json
# Configurar broker, credenciales y topics según su instalación
```

5. **Configurar el sistema**
```bash
# Editar config/config.yaml según sus necesidades
# Configurar cámara, umbrales de detección, etc.
```

## 🎮 Uso del Sistema

### Ejecución Principal (Recomendado)

```bash
# Ejecutar el programa principal
python run_interface.py
```

**Características de la interfaz:**
- ✅ Calculadores de distancia integrados
- ✅ Comunicación directa con DicapuaIoT
- ✅ Controles en tiempo real
- ✅ Visualización de estadísticas
- ✅ Sistema multilingüe
- ✅ Calibración automática

### Interfaz Interactiva Avanzada

```bash
# Ejecutar la interfaz completa con calculadores de distancia
python src/gui/interactive_interface.py
```

**Características de la interfaz:**
- ✅ Calculadores de distancia integrados
- ✅ Comunicación directa con DicapuaIoT
- ✅ Controles en tiempo real
- ✅ Visualización de estadísticas
- ✅ Sistema multilingüe
- ✅ Calibración automática

### Sistema Principal (Detección Básica)

```bash
# Ejecutar solo detección y tracking básico
python src/main.py

# Con configuración personalizada
python src/main.py --config mi_config.yaml
```

### Pipeline Completo de Procesamiento

```bash
# Ejecutar pipeline completo con todas las funcionalidades
python src/run_pipeline.py
```

### Scripts de Demostración

```bash
# Demo del sistema de coordenadas
python run_coordinate_axis_demo.py

# Demo de detección de pose
python run_pose_detection.py

# Procesamiento con coordenadas
python run_postprocess_with_coordinates.py
```

### Parámetros de Configuración

El archivo <mcfile name="config.yaml" path="config/config.yaml"></mcfile> permite configurar:

```yaml
# Configuración de visión
vision:
  yolo_model_path: "models/best.pt"
  confidence_threshold: 0.3
  video_source: 0  # 0 para cámara, ruta para archivo

# Configuración de comunicación
communication:
  mqtt:
    broker: "tu-broker-dicapuaiot"
    port: 1883
    topics:
      distance: "gantry/distance"

# Configuración de interfaz
ui:
  language: "es"  # "es" o "en"
  theme: "dark"
```

## 📊 Datos y Formatos

### Datos de Entrada
- **Video**: Formatos MP4, AVI, MOV, webcam en tiempo real
- **Cámara**: USB, cámaras IP compatibles con OpenCV
- **Configuración**: YAML para configuración general, JSON para credenciales IoT

### Datos de Salida
- **Logs**: Archivos de texto con timestamps y rotación automática
- **Datos procesados**: JSON con metadatos, CSV para análisis estadístico
- **Visualizaciones**: Gráficos en tiempo real con matplotlib
- **Comunicación IoT**: Mensajes JSON a DicapuaIoT con validación

### Estructura de Datos DicapuaIoT

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "deviceId": "gantry_system_001",
  "data": {
    "markerZ": {
      "distance_cm": 15.7,
      "confidence": 0.95,
      "source": "marker_calculator"
    },
    "buttonX": {
      "distance_cm": 23.4,
      "confidence": 0.92,
      "source": "portico_calculator"
    },
    "movement_detected": true,
    "calibration_status": "auto_calibrated"
  }
}
```

### Métricas de Rendimiento

```json
{
  "fps": 28.5,
  "detection_accuracy": 0.94,
  "processing_latency_ms": 35,
  "mqtt_connection_status": "connected",
  "total_detections": 1247,
  "movement_events": 23
}
```

## 🔧 Desarrollo y Extensión

### Estructura de Clases Principales

- **YOLOPoseDetector**: Detección de objetos con keypoints de pose
- **DistanceCalculator**: Cálculo de distancias pórtico-pulsador con filtros Kalman
- **MarkerDistanceCalculator**: Medición de distancias del marcador
- **MovementDetector**: Detección inteligente de movimientos con filtros
- **DicapuaPublisher**: Comunicación bidireccional con plataforma IoT
- **InteractiveInterface**: Interfaz gráfica con controles en tiempo real
- **CoordinateAxisDrawer**: Sistema de coordenadas calibrable

### Nuevas Funcionalidades Implementadas

#### 🎯 Detección Inteligente de Movimiento
- Filtros de distancia, velocidad y estabilidad temporal
- Reducción de ruido y falsos positivos
- Configuración dinámica de umbrales

#### 🌐 Comunicación IoT Avanzada
- Modo directo sin broker MQTT local
- Validación de datos antes del envío
- Reconexión automática con backoff exponencial
- Manejo de errores y logging detallado

#### 🖥️ Interfaz Multilingüe
- Soporte para español e inglés
- Cambio de idioma en tiempo real
- Configuración persistente

### Agregar Nuevas Funcionalidades

1. **Nuevos calculadores**: Heredar de las clases base en `postprocess/`
2. **Filtros de movimiento**: Extender `MovementDetector`
3. **Protocolos de comunicación**: Implementar en `mqtt/`
4. **Idiomas**: Agregar archivos JSON en `locales/`

### Testing y Validación

```bash
# Scripts de prueba disponibles
python test_calculators_integration.py    # Prueba calculadores
python test_dicapua_connection.py        # Prueba conexión IoT
python verify_data_transmission.py       # Verifica transmisión
python monitor_dicapua_connection.py     # Monitoreo continuo
```

## 📈 Monitoreo y Métricas

### Métricas del Sistema
- **FPS**: Frames por segundo procesados (objetivo: >25 FPS)
- **Latencia**: Tiempo de procesamiento por frame (<50ms)
- **Precisión**: Accuracy de detección YOLO (>90%)
- **Conectividad IoT**: Estado de conexión DicapuaIoT
- **Memoria**: Uso de RAM y GPU optimizado

### Logs y Debugging

```bash
# Ver logs en tiempo real
tail -f data/logs/InteractiveInterface_$(date +%Y%m%d).log

# Logs por nivel
grep "ERROR" data/logs/*.log
grep "WARNING" data/logs/*.log

# Monitoreo de conexión DicapuaIoT
python monitor_dicapua_connection.py
```

## 🚨 Solución de Problemas

### Problemas Comunes

1. **"Invalid combined data" en DicapuaPublisher**
   - **Causa**: Los calculadores de distancia no están inicializados
   - **Solución**: Usar `interactive_interface.py` en lugar de `main.py`
   - **Verificación**: Buscar mensajes "DistanceCalculator inicializado"

2. **Cámara no detectada**
   - Verificar permisos de cámara en el sistema
   - Probar diferentes índices (0, 1, 2...) en `video_source`
   - Verificar drivers de cámara actualizados

3. **Modelo YOLO no carga**
   - Verificar que existe `models/best.pt`
   - Comprobar versión de ultralytics compatible
   - Revisar logs de inicialización

4. **Conexión DicapuaIoT falla**
   - Verificar credenciales en `src/mqtt/config/dicapuaiot/`
   - Comprobar conectividad de red
   - Revisar configuración del broker

5. **Rendimiento lento**
   - Reducir `confidence_threshold` en configuración
   - Usar resolución de video menor
   - Optimizar configuración de filtros de movimiento

### Logs de Debug

```python
# Habilitar logs detallados en el código
import logging
logging.basicConfig(level=logging.DEBUG)

# O modificar config/config.yaml
data:
  log_level: "DEBUG"
```

## 🤝 Contribución

### Proceso de Contribución

1. Fork del proyecto
2. Crear rama para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Implementar cambios siguiendo estándares
4. Agregar tests si es necesario
5. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
6. Push a la rama (`git push origin feature/nueva-funcionalidad`)
7. Crear Pull Request con descripción detallada

### Estándares de Código

- **Formato**: Black para Python, líneas máximo 100 caracteres
- **Linting**: Flake8 para verificación de estilo
- **Documentación**: Docstrings en español con formato Google
- **Tests**: Scripts de prueba para nuevas funcionalidades
- **Commits**: Mensajes descriptivos en español

### Áreas de Contribución

- 🔍 Mejoras en algoritmos de detección
- 🌐 Nuevos protocolos de comunicación IoT
- 🖥️ Extensiones de interfaz de usuario
- 📊 Nuevas métricas y visualizaciones
- 🌍 Traducciones a otros idiomas

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👥 Autores y Reconocimientos

- **Equipo de Desarrollo**: Proyecto OSI4IoT Gantry
- **Institución**: CIMNE - Centro Internacional de Métodos Numéricos en Ingeniería
- **Proyecto**: Sistema de Gemelo Digital para Pórtico Grúa
- **Tecnologías**: YOLO v8, OpenCV, MQTT, DicapuaIoT, Python

### Agradecimientos Especiales

- Comunidad YOLO por el modelo de detección de pose
- Proyecto OSI4IoT por la plataforma de comunicación
- CIMNE por el soporte institucional y recursos

## 📞 Soporte y Contacto

- **Issues**: Reportar problemas en el repositorio GitHub
- **Documentación**: README y comentarios en código
- **Email**: Contacto institucional CIMNE
- **Wiki**: Documentación técnica detallada

## 🔄 Changelog

### v2.0.0 (2024-01-15) - Versión Actual
- ✅ **Interfaz interactiva completa** con controles en tiempo real
- ✅ **Calculadores de distancia avanzados** con filtros Kalman
- ✅ **Comunicación directa DicapuaIoT** sin broker local
- ✅ **Detección inteligente de movimiento** con múltiples filtros
- ✅ **Sistema multilingüe** (español/inglés)
- ✅ **Calibración automática** píxeles-centímetros
- ✅ **Validación de datos** antes de transmisión IoT
- ✅ **Manejo robusto de errores** y reconexión automática
- ✅ **Sistema de coordenadas** configurable
- ✅ **Logging avanzado** con rotación automática

### v1.0.0 (2023-10-01) - Versión Base
- ✅ Implementación inicial del sistema
- ✅ Detección YOLO básica integrada
- ✅ Cálculos físicos fundamentales
- ✅ Comunicación MQTT básica
- ✅ Visualización 2D/3D inicial
- ✅ Pipeline de procesamiento base

### Próximas Versiones (Roadmap)
- 🔄 **v2.1.0**: Integración con bases de datos para históricos
- 🔄 **v2.2.0**: API REST completa para integración externa
- 🔄 **v3.0.0**: Machine Learning para predicción de movimientos
- 🔄 **v3.1.0**: Interfaz web responsive
- 🔄 **v4.0.0**: Deployment con Docker y Kubernetes

---

**¡Gracias por usar el Digital Twin del Pórtico OSI4IoT!** 🚀

*Sistema desarrollado con ❤️ para la industria 4.0 y el Internet de las Cosas Industrial*