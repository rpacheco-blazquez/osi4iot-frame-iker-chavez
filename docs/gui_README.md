# Carpeta `gui/` - Interfaz Gráfica de Usuario

## Descripción General

La carpeta `gui/` contiene la interfaz gráfica de usuario (GUI) del sistema de gemelo digital. Proporciona una interfaz interactiva construida con Tkinter que permite la configuración, monitoreo y control en tiempo real de todos los componentes del sistema.

## Arquitectura de la Interfaz

### Componente Principal: `InteractiveDetectionInterface`

La clase `InteractiveDetectionInterface` implementa una interfaz de usuario que integra:

- **Sistema de pestañas (Notebook)**: Organización modular de las distintas funcionalidades.
- **Internacionalización (i18n)**: Soporte multiidioma (español/inglés).
- **Visualización en tiempo real**: Streaming de video con overlays de detección.
- **Configuración dinámica**: Controles interactivos para el ajuste de los parámetros del sistema.
- **Monitoreo de estado**: Paneles informativos y estadísticas en tiempo real.

### Estructura de Pestañas

```
GUI Interface
├── Detección (Detection)
│   ├── Configuración de modelo YOLO
│   ├── Controles de visualización
│   └── Panel de video en tiempo real
├── Postprocesamiento (Postprocess)
│   ├── Cálculo de distancias
│   ├── Configuración MQTT
│   └── Filtros de movimiento
├── Posición Virtual (Virtual Position)
│   ├── Sistema de coordenadas
│   ├── Calibración espacial
│   └── Trayectorias
└── Datos (Data)
    ├── Estadísticas de detección
    ├── Historial de mediciones
    └── Gráficos de rendimiento
```

## Principios de Diseño de Interfaz

### 1. Patrón Model-View-Controller (MVC)

La interfaz implementa una separación clara de responsabilidades:

- **Model**: Componentes del sistema (detector, calculadores, publisher).
- **View**: Elementos gráficos de Tkinter.
- **Controller**: Lógica de eventos y actualización de estado.

### 2. Patrón Observer para Actualizaciones en Tiempo Real

La interfaz utiliza el patrón Observer para mantener sincronización:

```python
# Actualización automática de elementos visuales
def update_detection_display(self, frame, detections):
    # Procesar frame con overlays
    processed_frame = self.draw_detections(frame, detections)
    # Actualizar canvas de video
    self.update_video_canvas(processed_frame)
```

### 3. Sistema de Eventos Asíncronos

Implementa threading para operaciones no bloqueantes:

```python
self.detection_thread = threading.Thread(
    target=self.detection_loop,
    daemon=True
)
self.detection_thread.start()
```

## Funcionalidades Principales

### 1. Pestaña de Detección

#### Configuración de Modelo YOLO
- **Presets de configuración**:
  - Alta precisión: `confidence=0.8, iou=0.3`
  - Detección rápida: `confidence=0.3, iou=0.7`
  - Modo completo: Todas las visualizaciones activas
  - Solo keypoints: Visualización únicamente de los keypoints.

#### Controles de Umbral
- **Confidence Threshold**: Control deslizante para umbral de la confianza de la detección.
- **IoU Threshold**: Ajuste de supresión de no-máximos.

#### Opciones de Visualización
- Bounding boxes con colores por clase.
- Keypoints de pose.
- Etiquetas con confianza y clase.

### 2. Pestaña de Postprocesamiento

#### Cálculo de Distancias
Implementa dos algoritmos de cálculo:

**Distancia Euclidiana 2D:**

$$d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$


**Conversión Píxeles a Centímetros:**

$$d_{cm} = \frac{d_{pixels}}{pixels\_per\_cm}$$


#### Filtros de Movimiento
Implementa múltiples filtros para mejorar la precisión de las mediciones:

1. **Filtro de Distancia**: Elimina los cambios abruptos en las distancias medidas.
2. **Filtro de Velocidad**: Limita velocidades máximas, evitando así oscilaciones bruscas en las mediciones.
3. **Filtro de Estabilidad**: Reduce las oscilaciones en las mediciones, para así reducir transiciones bruscas en el gemelo digital.
4. **Filtro Relativo**: Considera posiciones relativas, mejorando la precisión en cálculos de trayectorias.

**Filtro de Media Móvil:**

$$\bar{x}_n = \frac{1}{w} \sum_{i=0}^{w-1} x_{n-i}$$

Donde `w` es el tamaño de la ventana temporal.

```python
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
```

#### Configuración MQTT
- Habilitación/deshabilitación del protocolo de comunicación.
- Configuración del broker MQTT y puerto.
- Estado de conexión en tiempo real.

### 3. Pestaña de Posición Virtual

#### Sistema de Coordenadas
Implementa transformación de coordenadas de la imagen (píxeles) a coordenadas físicas (mundo real):

**Transformación Afín:**

$$
\begin{bmatrix}
X_{world} \\
Y_{world}
\end{bmatrix} = 
\begin{bmatrix}
a & b \\
c & d
\end{bmatrix}
\begin{bmatrix}
X_{image} - x_0 \\
Y_{image} - y_0
\end{bmatrix}
$$

Donde $(x_0, y_0)$ es el origen del sistema de coordenadas.

#### Calibración Espacial
- Definición de origen de coordenadas.
- Configuración de escala (píxeles por unidad).
- Validación de calibración.

```python
def auto_calibrate(self, detections: List[Dict]) -> bool:
        """
        Calibra automáticamente con validación geométrica y corrección de errores.
        """
        keypoint_c = self.get_portico_keypoint_c(detections)
        keypoint_b = self.get_portico_keypoint_b(detections)
        
        if keypoint_c is None or keypoint_b is None:
            return False
            
        # Calcular distancia en píxeles entre C y B
        distance_pixels_cb = self.calculate_euclidean_distance(keypoint_c, keypoint_b)
        
        if distance_pixels_cb > 0:
            # Calcular factor de calibración: píxeles / cm
            new_pixels_per_cm = distance_pixels_cb / self.reference_distance_cm
            self.calibration_history.append(new_pixels_per_cm)
            
            # Usar promedio ponderado (más peso a calibraciones recientes)
            weights = np.exp(np.linspace(-1, 0, len(self.calibration_history)))
            weights /= weights.sum()
            
            self.pixels_per_cm = np.average(list(self.calibration_history), weights=weights)
            self.auto_calibrated = True
            return True
            
        return False
```

#### Visualización de Trayectorias
- Historial de posiciones con buffer circular.
- Renderizado de trayectoria en tiempo real.
- Análisis de patrones de movimiento.

### 4. Pestaña de Datos

#### Estadísticas de Detección
- Contadores de detecciones por clase de objeto.
- Historial de confianza de detecciones.
- Métricas de rendimiento (FPS).

#### Visualización de Datos
Utiliza Matplotlib integrado con Tkinter:

```python
fig = Figure(figsize=(8, 6), dpi=100)
canvas = FigureCanvasTkAgg(fig, parent=self.data_frame)
```

#### Gráficos en Tiempo Real
- Histograma de distancias.
- Evolución temporal de métricas.
- Distribución de confianza.

## Internacionalización (i18n)

### Sistema de Traducción
Implementa un sistema de internacionalización:

```python
class I18n:
    def __init__(self):
        self.translations = self.load_translations()
        self.current_language = 'es'
    
    def t(self, key, **kwargs):
        """Traduce una clave con parámetros opcionales."""
        translation = self.get_translation(key)
        return translation.format(**kwargs) if kwargs else translation
```

### Archivos de Traducción
- `locales/es.json`: Traducciones en español
- `locales/en.json`: Traducciones en inglés

### Actualización Dinámica
La interfaz se actualiza automáticamente al cambiar idioma:

```python
def change_language(self, language_code):
    self.i18n.set_language(language_code)
    self.update_interface_texts()
```

## Integración con Componentes del Sistema

### 1. Detector YOLO
```python
self.detector = YOLOPoseDetector(config_path)
detections = self.detector.get_detections_data(frame)
```

### 2. Calculadores de Distancia
```python
self.distance_calculator = DistanceCalculator(
    pixels_per_cm=10.0,
    enable_mqtt=True,
    dicapua_publisher=self.dicapua_publisher
)
```

### 3. Publisher MQTT
```python
self.dicapua_publisher = DicapuaPublisher()
self.dicapua_publisher.start_client_direct_mode()
```

### 4. Sistema de Coordenadas
```python
self.coordinate_drawer = CoordinateAxisDrawer(
    position="bottom_right",
    size=80,
    margin=30
)
```

## Gestión de Estado y Concurrencia

### Variables de Estado
La interfaz tiene múltiples variables de estado:

```python
# Variables de configuración
self.confidence_threshold = tk.DoubleVar(value=0.5)
self.iou_threshold = tk.DoubleVar(value=0.45)
self.show_keypoints = tk.BooleanVar(value=True)

# Variables de postprocesamiento
self.pixels_per_cm = tk.DoubleVar(value=10.0)
self.show_distance = tk.BooleanVar(value=True)

# Variables MQTT
self.mqtt_enabled = tk.BooleanVar(value=True)
self.mqtt_status = tk.StringVar(value="Desconectado")
```

### Threading para Operaciones Asíncronas

#### Hilo de Detección
```python
def detection_loop(self):
    """Bucle principal de detección en hilo separado."""
    while self.running:
        ret, frame = self.video_capture.read()
        if ret:
            detections = self.detector.detect(frame)
            self.update_display(frame, detections)
        time.sleep(1/30)  # 30 FPS
```

#### Hilo de Postprocesamiento
```python
def postprocess_loop(self):
    """Bucle de postprocesamiento en hilo separado."""
    while self.postprocess_running:
        # Procesar frame con cálculos de distancia
        self.process_distances()
        time.sleep(1/30)
```

## Manejo de Eventos y Callbacks

### Eventos de Configuración
```python
def on_confidence_change(self, value):
    """Callback para cambio de umbral de confianza."""
    self.detector.set_confidence_threshold(float(value))
    self.conf_label.config(text=f"Confianza: {float(value):.2f}")
```

### Eventos de Control
```python
def start_detection(self):
    """Inicia el proceso de detección."""
    if not self.running:
        self.initialize_video_capture()
        self.running = True
        self.start_detection_thread()
```

## Visualización y Renderizado

### Canvas de Video
Se utiliza PIL (Python Imaging Library) y ImageTk para mostrar video en tiempo real:

```python
def update_video_canvas(self, frame):
    """Actualiza el canvas de video con el frame procesado."""
    # Convertir de BGR a RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Crear imagen PIL
    pil_image = Image.fromarray(frame_rgb)
    # Convertir a PhotoImage
    photo = ImageTk.PhotoImage(pil_image)
    # Actualizar canvas
    self.video_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
```

### Overlays de Detección
```python
def draw_detections(self, frame, detections):
    """Dibuja overlays de detección en el frame."""
    for detection in detections:
        if self.show_bboxes.get():
            self.draw_bounding_box(frame, detection)
        if self.show_keypoints.get():
            self.draw_keypoints(frame, detection)
        if self.show_labels.get():
            self.draw_labels(frame, detection)
    return frame
```

## Configuración

### Gestión de Configuración
La interfaz se integra con el `ConfigManager` para persistir configuraciones:

```python
def save_current_config(self):
    """Guarda la configuración actual."""
    config = {
        'confidence_threshold': self.confidence_threshold.get(),
        'iou_threshold': self.iou_threshold.get(),
        'show_keypoints': self.show_keypoints.get(),
        'pixels_per_cm': self.pixels_per_cm.get()
    }
    self.config_manager.update_config(config)
```

### Presets de Configuración
```python
def apply_high_precision_preset(self):
    """Aplica preset de alta precisión."""
    self.confidence_threshold.set(0.8)
    self.iou_threshold.set(0.3)
    self.show_keypoints.set(True)
    self.show_bboxes.set(True)
```

## Análisis de Rendimiento

### Métricas de Interfaz
- **FPS de visualización**: Frames mostrados por segundo.
- **Latencia de respuesta**: Tiempo entre evento y actualización.
- **Uso de memoria**: Monitoreo de buffers de imagen.
- **Tiempo de renderizado**: Duración de operaciones de dibujo.

### Optimizaciones Implementadas
1. **Buffer circular** para historial de datos.
2. **Redimensionado inteligente** de imágenes.
3. **Threading no bloqueante** para operaciones pesadas.
4. **Caché de traducciones** para i18n.
5. **Actualización selectiva** de elementos GUI.

## Modularidad

### Arquitectura Modular
La interfaz está diseñada para fácil extensión:

```python
class CustomTab(ttk.Frame):
    """Clase base para pestañas personalizadas."""
    def __init__(self, parent, interface):
        super().__init__(parent)
        self.interface = interface
        self.setup_controls()
    
    def setup_controls(self):
        """Implementar en subclases."""
        raise NotImplementedError
```

## Dependencias Técnicas

- **Tkinter**: Framework GUI nativo de Python.
- **PIL/Pillow**: Procesamiento y visualización de imágenes.
- **OpenCV**: Captura y procesamiento de video.
- **Matplotlib**: Gráficos y visualizaciones científicas.
- **Threading**: Concurrencia y operaciones asíncronas.
- **JSON**: Persistencia de configuración y traducciones.

