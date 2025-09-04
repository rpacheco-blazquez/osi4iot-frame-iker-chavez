# Script `run_headless.py` - Detección Headless en Tiempo Real

## Descripción General

El script `run_headless.py` implementa un sistema de detección de objetos y poses en tiempo real sin interfaz gráfica (modo headless). Utiliza el modelo YOLO v8 para detección de poses, calculadores de distancia especializados y comunicación MQTT optimizada para transmisión de datos a la plataforma DicapuaIoT. 

## Arquitectura del Sistema Headless

### Componentes Principales

```mermaid
graph TD
    A[Entrada de Video/Cámara] --> B[YOLOPoseDetector]
    B --> C[Detecciones + Keypoints]
    C --> D[DistanceCalculator]
    C --> E[MarkerDistanceCalculator]
    D --> F[Buffer MQTT]
    E --> F
    F --> G[DicapuaPublisher]
    G --> H[DicapuaIoT Platform]
    
    I[Sistema de Logs] --> J[HeadlessInterface_YYYYMMDD.log]
    K[Estadísticas FPS] --> L[Consola/Terminal]
    
    subgraph "Detección"
        B
        C
    end
    
    subgraph "Procesamiento"
        D
        E
    end
    
    subgraph "Comunicación"
        F
        G
        H
    end
    
    subgraph "Monitoreo"
        I
        J
        K
        L
    end
```

### Flujo de Procesamiento

1. **Inicialización**: Carga del modelo YOLO y configuración MQTT
2. **Captura de Video**: Adquisición continua de frames desde cámara/video
3. **Detección**: Identificación de objetos y keypoints con YOLO
4. **Cálculo de Distancias**: Procesamiento de métricas espaciales
5. **Buffer MQTT**: Agrupación optimizada de mensajes
6. **Transmisión**: Envío de datos a DicapuaIoT
7. **Monitoreo**: Logging y estadísticas en tiempo real

## Requisitos del Sistema

### Dependencias de Software

```bash
# Dependencias principales
opencv-python>=4.8.0
numpy>=1.24.0
PyYAML>=6.0
paho-mqtt>=1.6.0
ultralytics>=8.0.0  # Para YOLO v8
```

### Sistemas Operativos Soportados

- ✅ Linux (Ubuntu 20.04+, CentOS 8+)
- ✅ Windows 10/11
- ✅ macOS 11+
- ✅ Docker containers

## Instalación y Configuración

### 1. Instalación de Dependencias

```bash
# Clonar repositorio
git clone <repository-url>
cd osi4iot-frame-iker-chavez

# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python headless/run_headless.py --help
```

### 2. Configuración MQTT

Crear archivo de configuración MQTT:

```json
# dicapuaiot/dicapuaiot.json
{
  "broker_host": "your-broker.dicapuaiot.com",
  "broker_port": 1883,
  "username": "your-username",
  "password": "your-password",
  "client_id": "headless-detector",
  "topics": {
    "data": "YOLOframe",
    "status": "system/status"
  }
}
```

### 3. Configuración del Modelo

Asegurar que el modelo YOLO esté disponible:

```bash
# Verificar modelo
ls models/best.pt
```

## Parámetros de Configuración

### Argumentos de Línea de Comandos

| Parámetro | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `--camera-index, -c` | int/str | 0 | Índice de cámara o ruta de video |
| `--config` | str | config/config.yaml | Archivo de configuración |
| `--show-window, -w` | flag | False | Mostrar ventana de detección |
| `--confidence` | float | 0.5 | Umbral de confianza (0.0-1.0) |
| `--iou` | float | 0.45 | Umbral IoU para NMS (0.0-1.0) |
| `--verbose, -v` | flag | False | Modo verbose |
| `--list-cameras, -l` | flag | False | Listar cámaras disponibles |

### Parámetros MQTT Optimizados

| Parámetro | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `--mqtt-enabled` | flag | True | Habilitar MQTT |
| `--no-mqtt` | flag | False | Deshabilitar MQTT |
| `--mqtt-debug` | flag | False | Modo debug MQTT |
| `--mqtt-heartbeat` | int | 30 | Intervalo heartbeat (segundos) |
| `--mqtt-stats` | int | 1 | Intervalo estadísticas (segundos) |
| `--mqtt-buffer-size` | int | 10 | Tamaño buffer MQTT |
| `--mqtt-buffer-flush` | float | 0.1 | Intervalo flush buffer (segundos) |
| `--mqtt-topic` | str | None | Topic personalizado |

### Parámetros de Visualización

| Parámetro | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `--keypoints` | flag | True | Mostrar keypoints |
| `--no-keypoints` | flag | False | Ocultar keypoints |
| `--bboxes` | flag | True | Mostrar bounding boxes |
| `--no-bboxes` | flag | False | Ocultar bounding boxes |
| `--labels` | flag | True | Mostrar etiquetas |
| `--no-labels` | flag | False | Ocultar etiquetas |

## Ejemplos de Uso

### Uso Básico

```bash
# Ejecutar con cámara por defecto
python headless/run_headless.py

# Listar cámaras disponibles
python headless/run_headless.py --list-cameras

# Usar cámara específica
python headless/run_headless.py --camera-index 1
```

### Configuración Avanzada

```bash
# Modo verbose con ventana de visualización
python headless/run_headless.py -c 0 -w -v

# Configurar umbrales de detección
python headless/run_headless.py --confidence 0.7 --iou 0.5
```

### Optimización MQTT

```bash
# Buffer MQTT optimizado para alta frecuencia
python headless/run_headless.py \
  --mqtt-stats 0.5 \
  --mqtt-buffer-size 20 \
  --mqtt-buffer-flush 0.05

# Modo debug MQTT
python headless/run_headless.py --mqtt-debug

# Deshabilitar MQTT para pruebas locales
python headless/run_headless.py --no-mqtt
```

### Configuración Optimizada

```bash
# Servidor de producción (sin ventana, optimizado)
python headless/run_headless.py \
  --camera-index 0 \
  --confidence 0.6 \
  --mqtt-stats 1 \
  --mqtt-buffer-size 15 \
  --no-keypoints \
  --verbose
```

## Optimizaciones de Rendimiento

### Sistema de Buffer MQTT

El script implementa un sistema de buffer optimizado que:

- **Agrupa mensajes**: Reduce overhead de red
- **Flush automático**: Envío cada 100ms por defecto
- **Control de tamaño**: Buffer configurable (10 mensajes por defecto)
- **Recuperación de errores**: Reconexión automática

### Métricas de Rendimiento

```python
# Ejemplo de salida en consola
[16:00:20] FPS: 9.6 | Detecciones: 2 | Total: 649 | MQTT: 🟢 | Tiempo: 29.9s
  └─ portico: 0.945
  └─ pulsador: 0.862
```

### Configuración de Intervalos

$$
\text{Latencia Total} = \text{Detección} + \text{Procesamiento} + \text{Buffer} + \text{Red}
$$

- **Detección**: ~50-100ms (dependiente de hardware)
- **Procesamiento**: ~10-20ms
- **Buffer**: 100ms (configurable)
- **Red**: Variable (dependiente de conexión)

## Monitoreo y Logging

### Sistema de Logs

Los logs se almacenan en:
```
headless/data/logs/HeadlessInterface_YYYYMMDD.log
```

**Ejemplo de log:**
```
2025-09-03 15:42:18,122 - HeadlessInterface - INFO - Interfaz headless inicializada
2025-09-03 15:42:58,059 - HeadlessInterface - INFO - Detección detenida
2025-09-03 15:42:58,476 - HeadlessInterface - INFO - Interfaz headless cerrada
```

### Estadísticas en Tiempo Real

- **FPS**: Frames por segundo procesados
- **Detecciones**: Objetos detectados por frame
- **Total**: Contador acumulativo
- **Estado MQTT**: 🟢 Conectado / 🔴 Desconectado
- **Tiempo**: Uptime del sistema

### Métricas MQTT

- **Mensajes enviados**: Contador de éxito
- **Mensajes fallidos**: Contador de errores
- **Intentos de conexión**: Reintentos automáticos
- **Tamaño de buffer**: Mensajes pendientes

## Manejo de Errores y Recuperación

### Reconexión Automática MQTT

```python
# Configuración de reintentos
max_retries = 5
retry_delay = 1  # segundos
max_delay = 5    # límite de delay exponencial
```

## Solución de Problemas

### Problemas Comunes

#### 1. Error de Cámara
```bash
❌ Error al abrir la fuente de video: 0
```
**Solución:**
- Verificar permisos de cámara
- Listar cámaras disponibles: `--list-cameras`
- Probar con índice diferente: `--camera-index 1`

#### 2. Error de Conexión MQTT
```bash
❌ Error MQTT (intento 1/5): Connection refused
```
**Solución:**
- Verificar configuración en `dicapuaiot/dicapuaiot.json`
- Comprobar conectividad de red
- Usar modo debug: `--mqtt-debug`

#### 3. Modelo YOLO No Encontrado
```bash
❌ Error al cargar el modelo YOLO
```
**Solución:**
- Verificar que existe `models/best.pt`
- Descargar modelo base si es necesario
- Comprobar permisos de lectura

### Comandos de Diagnóstico

```bash
# Verificar sistema
python headless/run_headless.py --list-cameras --verbose

# Prueba sin MQTT
python headless/run_headless.py --no-mqtt --show-window

# Debug completo
python headless/run_headless.py --mqtt-debug --verbose
```

## Desarrollo

### Estructura del Código

```
headless/
├── run_headless.py          # Script principal
├── data/
│   └── logs/               # Logs del sistema
└── README.md              
```


---

