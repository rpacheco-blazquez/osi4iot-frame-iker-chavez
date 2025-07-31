"""Interfaz interactiva para configuración de detección y visualización en tiempo real."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import numpy as np
import threading
import time
from pathlib import Path
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import collections
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent.parent))

from vision.detector import YOLOPoseDetector
from utils.helpers import ConfigManager, Logger
from utils.i18n import get_i18n, t
from postprocess.distance_calculator import DistanceCalculator
from postprocess.marker_distance_calculator import MarkerDistanceCalculator
from postprocess.coordinate_axis_drawer import CoordinateAxisDrawer

class InteractiveDetectionInterface:
    """Interfaz interactiva para detección en tiempo real."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Inicializa la interfaz.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config_manager = ConfigManager(config_path)
        self.logger = Logger("InteractiveInterface")
        
        # Inicializar sistema de internacionalización
        self.i18n = get_i18n()
        
        # Componentes del sistema
        self.detector = YOLOPoseDetector(config_path)
        
        # Crear DicapuaPublisher para comunicación directa
        try:
            from mqtt.dicapua_publisher import DicapuaPublisher
            self.dicapua_publisher = DicapuaPublisher()
            # Iniciar en modo directo (sin MQTT local)
            self.dicapua_publisher.start_client_direct_mode()
            print("✅ DicapuaPublisher iniciado en modo directo")
        except Exception as e:
            print(f"⚠️ Error al inicializar DicapuaPublisher: {e}")
            self.dicapua_publisher = None
        
        # Crear calculadores con comunicación directa
        self.distance_calculator = DistanceCalculator(
            pixels_per_cm=10.0,
            enable_mqtt=True,  # Habilitar para comunicación directa
            dicapua_publisher=self.dicapua_publisher,  # Pasar referencia
            config_path=config_path
        )
        self.marker_distance_calculator = MarkerDistanceCalculator(
            pixels_per_cm=10.0,
            enable_mqtt=True,  # Habilitar para comunicación directa
            dicapua_publisher=self.dicapua_publisher,  # Pasar referencia
            config_path=config_path
        )
        
        # Crear dibujador de sistema de coordenadas
        self.coordinate_drawer = CoordinateAxisDrawer(
            position="bottom_right",
            size=80,
            margin=30
        )
        
        # Estado de la aplicación
        self.running = False
        self.postprocess_running = False
        self.video_capture = None
        self.postprocess_capture = None
        self.current_frame = None
        self.detection_thread = None
        self.postprocess_thread = None
        
        # Crear interfaz primero
        self.setup_gui()
        
        # Inicializar variable de idioma después de crear root
        self.current_language = tk.StringVar(value=self.i18n.get_language())
        
        # Configurar barra de menú después de inicializar current_language
        self.setup_menu_bar()
        
        # Configuración de detección (después de crear root)
        self.confidence_threshold = tk.DoubleVar(value=0.5)
        self.iou_threshold = tk.DoubleVar(value=0.45)
        self.show_keypoints = tk.BooleanVar(value=True)
        self.show_bboxes = tk.BooleanVar(value=True)
        self.show_labels = tk.BooleanVar(value=True)
        self.video_source = tk.StringVar(value="0")
        self.current_config = tk.StringVar(value="Por defecto")
        
        # Variables para postprocesamiento
        self.pixels_per_cm = tk.DoubleVar(value=10.0)
        self.show_distance = tk.BooleanVar(value=True)
        self.show_distance_line = tk.BooleanVar(value=True)
        self.postprocess_video_source = tk.StringVar(value="0")
        
        # Variables para calculador de marcador
        self.show_marker_distance = tk.BooleanVar(value=True)
        self.show_marker_distance_line = tk.BooleanVar(value=True)
        self.marker_pixels_per_cm = tk.DoubleVar(value=10.0)
        
        # Variables para sistema de coordenadas
        self.show_coordinate_system = tk.BooleanVar(value=True)
        self.coordinate_position = tk.StringVar(value="bottom_right")
        self.coordinate_size = tk.IntVar(value=80)
        
        # Variables para MQTT
        self.mqtt_enabled = tk.BooleanVar(value=True)
        self.mqtt_broker = tk.StringVar(value="localhost")
        self.mqtt_port = tk.StringVar(value="1883")
        self.mqtt_status = tk.StringVar(value="Desconectado")
        
        # Variables para filtros de movimiento
        self.filter_distance_enabled = tk.BooleanVar(value=True)
        self.filter_velocity_enabled = tk.BooleanVar(value=True)
        self.filter_stability_enabled = tk.BooleanVar(value=True)
        self.filter_relative_enabled = tk.BooleanVar(value=True)
        self.filter_temporal_enabled = tk.BooleanVar(value=True)
        
        # Parámetros de filtros
        self.distance_threshold = tk.DoubleVar(value=2.0)
        self.velocity_threshold = tk.DoubleVar(value=1.0)
        self.temporal_window = tk.IntVar(value=3)
        
        # Variables para datos y estadísticas
        self.distance_history = collections.deque(maxlen=100)
        self.detection_stats = {'marcador': 0, 'portico': 0, 'pulsador': 0}
        self.fps_history = collections.deque(maxlen=50)
        self.confidence_history = collections.deque(maxlen=100)
        
        # Variables para posición virtual
        self.virtual_position_history = collections.deque(maxlen=100)
        self.pulsador_position = {'x': 0, 'y': 0}
        self.portico_position = {'x': 0, 'y': 0}
        self.virtual_position_enabled = tk.BooleanVar(value=True)
        self.show_trajectory = tk.BooleanVar(value=True)
        self.coordinate_system_calibrated = tk.BooleanVar(value=False)
        self.virtual_position_running = False
        self.coordinate_origin = (320, 240)  # Origen por defecto
        self.coordinate_scale = 10.0  # Escala por defecto
        
        # Configurar controles después de crear variables
        self.setup_controls()
        
        # Cargar modelo
        self.detector.load_model()
        
        self.logger.info("Interfaz interactiva inicializada")
    
    def t(self, key, **kwargs):
        """Método de traducción que usa el sistema de internacionalización.
        
        Args:
            key: Clave de traducción
            **kwargs: Parámetros para la traducción
            
        Returns:
            Texto traducido
        """
        return self.i18n.t(key, **kwargs)
    
    def setup_gui(self):
        """Configura la interfaz gráfica básica."""
        self.root = tk.Tk()
        self.root.title(self.t('app_title'))
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Configurar estilo moderno y profesional
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores profesionales consistentes
        bg_color = '#f0f0f0'
        frame_color = '#ffffff'
        text_color = '#333333'
        button_color = '#e1e1e1'
        accent_color = '#0078d4'
        
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=frame_color, foreground=text_color)
        style.configure('TButton', background=button_color, foreground=text_color)
        style.configure('TNotebook', background=bg_color)
        style.configure('TNotebook.Tab', background=button_color, foreground=text_color)
        style.configure('TLabelFrame', background=frame_color, foreground=text_color)
        style.configure('TLabelFrame.Label', background=frame_color, foreground=text_color)
        
        # Crear notebook para pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Crear frames para cada pestaña
        self.detection_frame = ttk.Frame(self.notebook)
        self.postprocess_frame = ttk.Frame(self.notebook)
        self.virtual_position_frame = ttk.Frame(self.notebook)
        self.data_frame = ttk.Frame(self.notebook)
        
        # Agregar pestañas al notebook
        self.notebook.add(self.detection_frame, text=self.t("detection.title"))
        self.notebook.add(self.postprocess_frame, text=self.t("postprocess.title"))
        self.notebook.add(self.virtual_position_frame, text=self.t("virtual_position.title"))
        self.notebook.add(self.data_frame, text=self.t("data.title"))
        
        # Frame principal para compatibilidad (apunta al frame de detección)
        self.main_frame = self.detection_frame
    
    def setup_menu_bar(self):
        """Configura la barra de menú con selector de idioma."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú de idioma
        language_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.t('language'), menu=language_menu)
        
        # Opciones de idioma
        available_languages = self.i18n.get_available_languages()
        for lang_code, lang_name in available_languages.items():
            language_menu.add_radiobutton(
                label=lang_name,
                variable=self.current_language,
                value=lang_code,
                command=lambda code=lang_code: self.change_language(code)
            )
    
    def change_language(self, language_code: str):
        """Cambia el idioma de la interfaz.
        
        Args:
            language_code: Código del idioma ('es' o 'en')
        """
        self.i18n.set_language(language_code)
        self.current_language.set(language_code)
        self.update_interface_texts()
        self.logger.info(f"Idioma cambiado a: {language_code}")
    
    def update_interface_texts(self):
        """Actualiza todos los textos de la interfaz con el idioma actual."""
        # Actualizar título de la ventana
        self.root.title(self.t('app_title'))
        
        # Actualizar pestañas del notebook
        self.notebook.tab(0, text=self.t('detection.title'))
        self.notebook.tab(1, text=self.t('postprocess.title'))
        self.notebook.tab(2, text=self.t('virtual_position.title'))
        self.notebook.tab(3, text=self.t('data.title'))
        
        # Actualizar textos de la pestaña de detección
        self.update_detection_texts()
        
        # Actualizar textos de otras pestañas
        self.update_postprocess_texts()
        self.update_virtual_position_texts()
        self.update_data_texts()
    
    def update_detection_texts(self):
        """Actualiza los textos de la pestaña de detección."""
        # Actualizar frame de control de detección
        if hasattr(self, 'detection_control_frame'):
            self.detection_control_frame.config(text=self.t('detection.config_title'))
        
        # Actualizar etiquetas
        if hasattr(self, 'presets_label'):
            self.presets_label.config(text=self.t('detection.presets'))
        
        # Actualizar botones de presets
        if hasattr(self, 'high_precision_btn'):
            self.high_precision_btn.config(text=self.t('detection.high_precision'))
        if hasattr(self, 'fast_detection_btn'):
            self.fast_detection_btn.config(text=self.t('detection.fast_detection'))
        if hasattr(self, 'full_mode_btn'):
            self.full_mode_btn.config(text=self.t('detection.full_mode'))
        if hasattr(self, 'keypoints_only_btn'):
            self.keypoints_only_btn.config(text=self.t('detection.keypoints_only'))
        
        # Actualizar etiquetas de configuración
        if hasattr(self, 'video_source_label'):
            self.video_source_label.config(text=self.t('detection.video_source'))
        if hasattr(self, 'browse_btn'):
            self.browse_btn.config(text=self.t('detection.browse'))
        if hasattr(self, 'confidence_threshold_label'):
            self.confidence_threshold_label.config(text=self.t('detection.confidence_threshold'))
        if hasattr(self, 'iou_threshold_label'):
            self.iou_threshold_label.config(text=self.t('detection.iou_threshold'))
        
        # Actualizar etiquetas de valores
        if hasattr(self, 'conf_label'):
            self.conf_label.config(text=self.t('detection.confidence_label', value=self.confidence_threshold.get()))
        if hasattr(self, 'iou_label'):
            self.iou_label.config(text=self.t('detection.iou_label', value=self.iou_threshold.get()))
        
        # Actualizar opciones de visualización
        if hasattr(self, 'visualization_options_label'):
            self.visualization_options_label.config(text=self.t('detection.visualization_options'))
        if hasattr(self, 'show_bboxes_check'):
            self.show_bboxes_check.config(text=self.t('detection.show_bboxes'))
        if hasattr(self, 'show_keypoints_check'):
            self.show_keypoints_check.config(text=self.t('detection.show_keypoints'))
        if hasattr(self, 'show_labels_check'):
            self.show_labels_check.config(text=self.t('detection.show_labels'))
        
        # Actualizar botones de control
        if hasattr(self, 'start_button'):
            self.start_button.config(text=self.t('detection.start_detection'))
        if hasattr(self, 'stop_button'):
            self.stop_button.config(text=self.t('detection.stop'))
        if hasattr(self, 'capture_button'):
            self.capture_button.config(text=self.t('detection.capture'))
        
        # Actualizar panel de video
        if hasattr(self, 'video_frame'):
            self.video_frame.config(text=self.t('detection.video_realtime'))
        
        # Actualizar panel de información
        if hasattr(self, 'info_frame'):
            self.info_frame.config(text=self.t('detection.detection_info'))
        
        # Actualizar texto de estado si no está en ejecución
        if hasattr(self, 'status_text') and not self.running:
            self.status_text.set(self.t('detection.status_start'))
    
    def update_postprocess_texts(self):
        """Actualiza los textos de la pestaña de postprocesamiento."""
        # Actualizar frame de control de postprocesamiento
        if hasattr(self, 'postprocess_control_frame'):
            self.postprocess_control_frame.config(text=self.t('postprocess.config_title'))
        
        # Actualizar etiquetas de configuración de video
        if hasattr(self, 'postprocess_video_label'):
            self.postprocess_video_label.config(text=self.t('postprocess.video_source'))
        if hasattr(self, 'browse_postprocess_btn'):
            self.browse_postprocess_btn.config(text=self.t('postprocess.browse'))
        
        # Actualizar etiquetas de distancia pulsador-pórtico
        if hasattr(self, 'distance_button_gantry_label'):
            self.distance_button_gantry_label.config(text=self.t('postprocess.distance_button_gantry'))
        if hasattr(self, 'show_distance_button_gantry_check'):
            self.show_distance_button_gantry_check.config(text=self.t('postprocess.show_distance_button_gantry'))
        if hasattr(self, 'show_line_button_gantry_check'):
            self.show_line_button_gantry_check.config(text=self.t('postprocess.show_line_button_gantry'))
        
        # Actualizar etiquetas de marcador
        if hasattr(self, 'distance_marker_title_label'):
            self.distance_marker_title_label.config(text=self.t('postprocess.distance_marker_title'))
        if hasattr(self, 'show_marker_distance_check'):
            self.show_marker_distance_check.config(text=self.t('postprocess.show_marker_distance'))
        if hasattr(self, 'show_marker_line_check'):
            self.show_marker_line_check.config(text=self.t('postprocess.show_marker_line'))
        if hasattr(self, 'calibration_marker_pixels_cm_label'):
            self.calibration_marker_pixels_cm_label.config(text=self.t('postprocess.calibration_marker_pixels_cm'))
        
        # Actualizar configuración MQTT
        if hasattr(self, 'mqtt_config_label'):
            self.mqtt_config_label.config(text=self.t('postprocess.mqtt_config'))
        if hasattr(self, 'mqtt_enabled_check'):
            self.mqtt_enabled_check.config(text=self.t('postprocess.mqtt_enabled'))
        if hasattr(self, 'mqtt_broker_label'):
            self.mqtt_broker_label.config(text=self.t('postprocess.mqtt_broker'))
        if hasattr(self, 'mqtt_port_label'):
            self.mqtt_port_label.config(text=self.t('postprocess.mqtt_port'))
        
        # Actualizar filtros de movimiento
        if hasattr(self, 'movement_filters_label'):
            self.movement_filters_label.config(text=self.t('postprocess.movement_filters'))
        if hasattr(self, 'filter_distance_check'):
            self.filter_distance_check.config(text=self.t('postprocess.filter_distance'))
        if hasattr(self, 'filter_velocity_check'):
            self.filter_velocity_check.config(text=self.t('postprocess.filter_velocity'))
        if hasattr(self, 'filter_stability_check'):
            self.filter_stability_check.config(text=self.t('postprocess.filter_stability'))
        if hasattr(self, 'filter_relative_check'):
            self.filter_relative_check.config(text=self.t('postprocess.filter_relative'))
        if hasattr(self, 'filter_temporal_check'):
            self.filter_temporal_check.config(text=self.t('postprocess.filter_temporal'))
        
        # Actualizar etiquetas de parámetros
        if hasattr(self, 'distance_threshold_label_title'):
            self.distance_threshold_label_title.config(text=self.t('postprocess.distance_threshold'))
        if hasattr(self, 'velocity_threshold_label_title'):
            self.velocity_threshold_label_title.config(text=self.t('postprocess.velocity_threshold'))
        if hasattr(self, 'temporal_window_label_title'):
            self.temporal_window_label_title.config(text=self.t('postprocess.temporal_window'))
        
        # Actualizar botones de postprocesamiento
        if hasattr(self, 'start_postprocess_button'):
            self.start_postprocess_button.config(text=self.t('postprocess.start_postprocess'))
        if hasattr(self, 'stop_postprocess_button'):
            self.stop_postprocess_button.config(text=self.t('postprocess.stop_postprocess'))
        if hasattr(self, 'calibrate_button_gantry_btn'):
            self.calibrate_button_gantry_btn.config(text=self.t('postprocess.calibrate_button_gantry'))
        if hasattr(self, 'calibrate_marker_btn'):
            self.calibrate_marker_btn.config(text=self.t('postprocess.calibrate_marker'))
        
        # Actualizar frame de video de postprocesamiento
        if hasattr(self, 'postprocess_video_frame'):
            self.postprocess_video_frame.config(text=self.t('postprocess.video_analysis_title'))
        
        # Actualizar frame de información de distancias
        if hasattr(self, 'distance_info_frame'):
            self.distance_info_frame.config(text=self.t('postprocess.distance_info_title'))
        
        # Actualizar texto de estado de postprocesamiento si no está en ejecución
        if hasattr(self, 'postprocess_status_text') and not self.postprocess_running:
            self.postprocess_status_text.set(self.t('postprocess.postprocess_status_start'))
        
        # Actualizar etiquetas de calibración
        if hasattr(self, 'cal_label'):
            self.cal_label.config(text=self.t('postprocess.calibration_label', value=self.pixels_per_cm.get()))
        if hasattr(self, 'marker_cal_label'):
            self.marker_cal_label.config(text=self.t('postprocess.marker_calibration_label', value=self.marker_pixels_per_cm.get()))
        
        # Actualizar etiquetas de filtros
        if hasattr(self, 'dist_threshold_label'):
            self.dist_threshold_label.config(text=self.t('postprocess.distance_threshold_label', value=self.distance_threshold.get()))
        if hasattr(self, 'vel_threshold_label'):
            self.vel_threshold_label.config(text=self.t('postprocess.velocity_threshold_label', value=self.velocity_threshold.get()))
        if hasattr(self, 'temp_window_label'):
            self.temp_window_label.config(text=self.t('postprocess.temporal_window_label', value=self.temporal_window.get()))
    
    def update_virtual_position_texts(self):
        """Actualiza los textos de la pestaña de posición virtual."""
        # Actualizar frame de control de posición virtual
        if hasattr(self, 'virtual_position_control_frame'):
            self.virtual_position_control_frame.config(text=self.t('virtual_position.config_title'))
        
        # Actualizar etiquetas de configuración de video
        if hasattr(self, 'virtual_position_video_label'):
            self.virtual_position_video_label.config(text=self.t('virtual_position.video_source'))
        if hasattr(self, 'browse_virtual_position_btn'):
            self.browse_virtual_position_btn.config(text=self.t('virtual_position.browse'))
        
        # Actualizar opciones de visualización
        if hasattr(self, 'virtual_position_visualization_options_label'):
            self.virtual_position_visualization_options_label.config(text=self.t('virtual_position.visualization_options'))
        if hasattr(self, 'virtual_position_enabled_check'):
            self.virtual_position_enabled_check.config(text=self.t('virtual_position.enable_virtual_position'))
        if hasattr(self, 'show_trajectory_check'):
            self.show_trajectory_check.config(text=self.t('virtual_position.show_trajectory'))
        
        # Actualizar sistema de coordenadas
        if hasattr(self, 'coordinate_system_label'):
            self.coordinate_system_label.config(text=self.t('virtual_position.coordinate_system'))
        if hasattr(self, 'calibrate_system_button'):
            self.calibrate_system_button.config(text=self.t('virtual_position.calibrate_system'))
        
        # Actualizar estado de calibración
        if hasattr(self, 'coordinate_status_label'):
            if self.coordinate_system_calibrated:
                self.coordinate_status_label.config(text=self.t('virtual_position.calibrated'))
            else:
                self.coordinate_status_label.config(text=self.t('virtual_position.not_calibrated'))
        
        # Actualizar botones de posición virtual
        if hasattr(self, 'start_virtual_button'):
            self.start_virtual_button.config(text=self.t('virtual_position.start_virtual'))
        if hasattr(self, 'stop_virtual_button'):
            self.stop_virtual_button.config(text=self.t('virtual_position.stop_virtual'))
        
        # Actualizar etiquetas de posición
        if hasattr(self, 'current_position_label'):
            self.current_position_label.config(text=self.t('virtual_position.current_position'))
        
        # Actualizar título del gráfico de posición virtual
        if hasattr(self, 'virtual_ax'):
            self.virtual_ax.set_title(self.t('virtual_position.graph_title'))
            self.virtual_ax.set_xlabel(self.t('virtual_position.x_axis'))
            self.virtual_ax.set_ylabel(self.t('virtual_position.y_axis'))
            if hasattr(self, 'virtual_canvas'):
                self.virtual_canvas.draw()
    
    def update_data_texts(self):
        """Actualiza los textos de la pestaña de datos."""
        # Actualizar sub-pestañas de datos
        if hasattr(self, 'data_notebook'):
            # Actualizar nombres de las sub-pestañas
            try:
                self.data_notebook.tab(0, text=self.t('data.distances_tab'))
                self.data_notebook.tab(1, text=self.t('data.detections_tab'))
                self.data_notebook.tab(2, text=self.t('data.performance_tab'))
            except:
                pass
        
        # Actualizar frames de gráficos
        if hasattr(self, 'distance_frame_label'):
            self.distance_frame_label.config(text=self.t('data.distance_history'))
        if hasattr(self, 'distance_hist_frame_label'):
            self.distance_hist_frame_label.config(text=self.t('data.distance_distribution'))
        if hasattr(self, 'detection_stats_frame_label'):
            self.detection_stats_frame_label.config(text=self.t('data.detection_statistics'))
        
        # Actualizar títulos de gráficos
        if hasattr(self, 'distance_ax'):
            self.distance_ax.set_title(self.t('data.distance_time_graph'))
            self.distance_ax.set_xlabel(self.t('data.time_samples'))
            self.distance_ax.set_ylabel(self.t('data.distance_cm'))
            if hasattr(self, 'distance_canvas'):
                self.distance_canvas.draw()
        
        if hasattr(self, 'distance_hist_ax'):
            self.distance_hist_ax.set_title(self.t('data.distance_histogram'))
            self.distance_hist_ax.set_xlabel(self.t('data.distance_cm'))
            self.distance_hist_ax.set_ylabel(self.t('data.frequency'))
            if hasattr(self, 'distance_hist_canvas'):
                self.distance_hist_canvas.draw()
        
        if hasattr(self, 'detection_ax1'):
            self.detection_ax1.set_title(self.t('data.detection_count_graph'))
            self.detection_ax1.set_ylabel(self.t('data.detection_number'))
            if hasattr(self, 'detection_canvas'):
                self.detection_canvas.draw()
        
        if hasattr(self, 'detection_ax2'):
            self.detection_ax2.set_title(self.t('data.confidence_graph'))
            self.detection_ax2.set_ylabel(self.t('data.confidence'))
            if hasattr(self, 'detection_canvas'):
                self.detection_canvas.draw()
    
    def update_widget_text(self, widget):
        """Actualiza el texto de un widget específico.
        
        Args:
            widget: Widget de tkinter a actualizar
        """
        # Este método se puede expandir para actualizar widgets específicos
        # basándose en sus nombres o propiedades
        pass
    
    def setup_controls(self):
        """Configura los controles después de crear las variables tkinter."""
        # Configurar pestaña de detección
        self.setup_detection_tab()
        
        # Configurar pestaña de postprocesamiento
        self.setup_postprocess_tab()
        
        # Configurar pestaña de posición virtual
        self.setup_virtual_position_tab()
        
        # Configurar pestaña de datos
        self.setup_data_tab()
        
    def setup_detection_tab(self):
        """Configura la pestaña de detección."""
        # Panel de control (izquierda)
        self.setup_control_panel(self.detection_frame)
        
        # Panel de video (derecha)
        self.setup_video_panel(self.detection_frame)
        
        # Panel de información (abajo)
        self.setup_info_panel(self.detection_frame)
        
    def setup_postprocess_tab(self):
        """Configura la pestaña de postprocesamiento."""
        # Panel de control para postprocesamiento (izquierda)
        self.setup_postprocess_control_panel(self.postprocess_frame)
        
        # Panel de video para postprocesamiento (derecha)
        self.setup_postprocess_video_panel(self.postprocess_frame)
        
        # Panel de información para postprocesamiento (abajo)
        self.setup_postprocess_info_panel(self.postprocess_frame)
    
    def setup_control_panel(self, parent):
        """Configura el panel de control."""
        self.detection_control_frame = ttk.LabelFrame(parent, text=self.t('detection.config_title'), padding=10)
        self.detection_control_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Configuraciones predefinidas
        self.presets_label = ttk.Label(self.detection_control_frame, text=self.t('detection.presets'))
        self.presets_label.grid(row=0, column=0, sticky="w", pady=5)
        presets_frame = ttk.Frame(self.detection_control_frame)
        presets_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.high_precision_btn = ttk.Button(presets_frame, text=self.t('detection.high_precision'), command=self.config_high_precision)
        self.high_precision_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.fast_detection_btn = ttk.Button(presets_frame, text=self.t('detection.fast_detection'), command=self.config_fast_detection)
        self.fast_detection_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.full_mode_btn = ttk.Button(presets_frame, text=self.t('detection.full_mode'), command=self.config_full_mode)
        self.full_mode_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.keypoints_only_btn = ttk.Button(presets_frame, text=self.t('detection.keypoints_only'), command=self.config_keypoints_only)
        self.keypoints_only_btn.pack(side=tk.LEFT)
        
        # Información de configuración actual
        self.config_info = ttk.Label(self.detection_control_frame, textvariable=self.current_config, foreground="#0078d4")
        self.config_info.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Configuración de fuente de video
        self.video_source_label = ttk.Label(self.detection_control_frame, text=self.t('detection.video_source'))
        self.video_source_label.grid(row=3, column=0, sticky="w", pady=5)
        video_frame = ttk.Frame(self.detection_control_frame)
        video_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Entry(video_frame, textvariable=self.video_source, width=20).pack(side=tk.LEFT, padx=(0, 5))
        self.browse_btn = ttk.Button(video_frame, text=self.t('detection.browse'), command=self.browse_video)
        self.browse_btn.pack(side=tk.LEFT)
        
        # Umbral de confianza
        self.confidence_threshold_label = ttk.Label(self.detection_control_frame, text=self.t('detection.confidence_threshold'))
        self.confidence_threshold_label.grid(row=5, column=0, sticky="w", pady=5)
        conf_scale = ttk.Scale(self.detection_control_frame, from_=0.1, to=1.0, variable=self.confidence_threshold, 
                              orient=tk.HORIZONTAL, length=200)
        conf_scale.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.conf_label = ttk.Label(self.detection_control_frame, text=self.t('detection.confidence_label', value=self.confidence_threshold.get()))
        self.conf_label.grid(row=7, column=0, sticky="w")
        
        # Umbral de IoU
        self.iou_threshold_label = ttk.Label(self.detection_control_frame, text=self.t('detection.iou_threshold'))
        self.iou_threshold_label.grid(row=8, column=0, sticky="w", pady=5)
        iou_scale = ttk.Scale(self.detection_control_frame, from_=0.1, to=1.0, variable=self.iou_threshold, 
                             orient=tk.HORIZONTAL, length=200)
        iou_scale.grid(row=9, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.iou_label = ttk.Label(self.detection_control_frame, text=self.t('detection.iou_label', value=self.iou_threshold.get()))
        self.iou_label.grid(row=10, column=0, sticky="w")
        
        # Opciones de visualización
        self.visualization_options_label = ttk.Label(self.detection_control_frame, text=self.t('detection.visualization_options'))
        self.visualization_options_label.grid(row=11, column=0, sticky="w", pady=(20, 5))
        
        self.show_bboxes_check = ttk.Checkbutton(self.detection_control_frame, text=self.t('detection.show_bboxes'), 
                       variable=self.show_bboxes)
        self.show_bboxes_check.grid(row=12, column=0, sticky="w", pady=2)
        
        self.show_keypoints_check = ttk.Checkbutton(self.detection_control_frame, text=self.t('detection.show_keypoints'), 
                       variable=self.show_keypoints)
        self.show_keypoints_check.grid(row=13, column=0, sticky="w", pady=2)
        
        self.show_labels_check = ttk.Checkbutton(self.detection_control_frame, text=self.t('detection.show_labels'), 
                       variable=self.show_labels)
        self.show_labels_check.grid(row=14, column=0, sticky="w", pady=2)
        
        # Botones de control
        button_frame = ttk.Frame(self.detection_control_frame)
        button_frame.grid(row=15, column=0, columnspan=2, pady=(20, 0))
        
        self.start_button = ttk.Button(button_frame, text=self.t('detection.start_detection'), 
                                      command=self.start_detection)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text=self.t('detection.stop'), 
                                     command=self.stop_detection, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.capture_button = ttk.Button(button_frame, text=self.t('detection.capture'), 
                  command=self.capture_frame)
        self.capture_button.pack(side=tk.LEFT)
        
        # Configurar callbacks para actualizar etiquetas
        self.confidence_threshold.trace('w', self.update_conf_label)
        self.iou_threshold.trace('w', self.update_iou_label)
    
    def setup_video_panel(self, parent):
        """Configura el panel de video."""
        self.video_frame = ttk.LabelFrame(parent, text=self.t('detection.video_realtime'), padding=10)
        self.video_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Canvas para mostrar video
        self.video_canvas = tk.Canvas(self.video_frame, width=800, height=600, bg='black')
        self.video_canvas.pack(expand=True, fill=tk.BOTH)
        
        # Texto de estado
        self.status_text = tk.StringVar(value=self.t('detection.status_start'))
        self.status_label = ttk.Label(self.video_frame, textvariable=self.status_text)
        self.status_label.pack(pady=5)
        
        # Configurar redimensionamiento
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
    
    def setup_info_panel(self, parent):
        """Configura el panel de información."""
        self.info_frame = ttk.LabelFrame(parent, text=self.t('detection.detection_info'), padding=10)
        self.info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Información de detecciones
        self.detection_info = tk.Text(self.info_frame, height=8, width=80, 
                                     bg='#1e1e1e', fg='white', font=('Consolas', 9))
        self.detection_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar para el texto
        scrollbar = ttk.Scrollbar(self.info_frame, orient=tk.VERTICAL, command=self.detection_info.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.detection_info.config(yscrollcommand=scrollbar.set)
        
        parent.grid_rowconfigure(1, weight=0)
    
    def browse_video(self):
        """Abre diálogo para seleccionar archivo de video."""
        filename = filedialog.askopenfilename(
            title=self.t('messages.file_select'),
            filetypes=[(self.t('messages.video_files'), "*.mp4 *.avi *.mov *.mkv"), (self.t('messages.all_files'), "*.*")]
        )
        if filename:
            self.video_source.set(filename)
    
    def update_conf_label(self, *args):
        """Actualiza la etiqueta del umbral de confianza."""
        self.conf_label.config(text=self.t('detection.confidence_label', value=self.confidence_threshold.get()))
    
    def update_iou_label(self, *args):
        """Actualiza la etiqueta del umbral de IoU."""
        self.iou_label.config(text=self.t('detection.iou_label', value=self.iou_threshold.get()))
    
    def start_detection(self):
        """Inicia la detección en tiempo real."""
        if self.running:
            return
        
        try:
            # Determinar fuente de video
            source = self.video_source.get()
            if source.isdigit():
                source = int(source)
            
            # Inicializar captura de video
            self.video_capture = cv2.VideoCapture(source)
            
            if not self.video_capture.isOpened():
                messagebox.showerror(self.t('messages.error'), self.t('messages.video_error', source=source))
                return
            
            # Configurar captura
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.running = True
            
            # Iniciar hilo de detección
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            
            # Actualizar interfaz
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.status_text.set(self.t('detection.status_running'))
            
            self.logger.info(self.t('messages.detection_started', source=source))
            
        except Exception as e:
            messagebox.showerror(self.t('messages.error'), self.t('messages.detection_error', error=str(e)))
            self.logger.error(f"Error al iniciar detección: {e}")
    
    def stop_detection(self):
        """Detiene la detección."""
        self.running = False
        
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        
        # Actualizar interfaz
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_text.set(self.t('detection.status_stopped'))
        
        # Limpiar canvas
        self.video_canvas.delete("all")
        
        self.logger.info("Detección detenida")
    
    def detection_loop(self):
        """Bucle principal de detección."""
        fps_counter = 0
        fps_start_time = time.time()
        
        while self.running:
            try:
                ret, frame = self.video_capture.read()
                
                if not ret:
                    self.logger.warning("No se pudo leer frame")
                    break
                
                self.current_frame = frame.copy()
                
                # Realizar detección
                detections = self.detector.get_detections_data(frame)
                
                # Dibujar detecciones
                annotated_frame = self.draw_detections(frame, detections)
                
                # Mostrar frame en la interfaz
                self.display_frame(annotated_frame)
                
                # Actualizar información de detecciones
                self.update_detection_info(detections)
                
                # Calcular FPS
                fps_counter += 1
                if time.time() - fps_start_time >= 1.0:
                    fps = fps_counter / (time.time() - fps_start_time)
                    self.root.after(0, lambda: self.status_text.set(f"FPS: {fps:.1f} | Detecciones: {len(detections)}"))
                    fps_counter = 0
                    fps_start_time = time.time()
                
                time.sleep(0.01)  # Pequeña pausa para no saturar la CPU
                
            except Exception as e:
                self.logger.error(f"Error en bucle de detección: {e}")
                break
        
        # Limpiar al salir
        if self.video_capture:
            self.video_capture.release()
    
    def draw_detections(self, frame, detections):
        """Dibuja las detecciones en el frame.
        
        Args:
            frame: Frame de video
            detections: Lista de detecciones
            
        Returns:
            Frame con detecciones dibujadas
        """
        annotated_frame = frame.copy()
        
        for detection in detections:
            confidence = detection.get('confidence', 0)
            
            # Filtrar por umbral de confianza
            if confidence < self.confidence_threshold.get():
                continue
            
            bbox = detection.get('bbox', [])
            class_name = detection.get('class_name', 'unknown')
            keypoints = detection.get('keypoints', [])
            
            # Dibujar bounding box
            if self.show_bboxes.get() and len(bbox) >= 4:
                x1, y1, x2, y2 = map(int, bbox[:4])
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Dibujar etiqueta
                if self.show_labels.get():
                    label = f"{class_name}: {confidence:.2f}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), (0, 255, 0), -1)
                    cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            # Dibujar keypoints
            if self.show_keypoints.get() and keypoints is not None and len(keypoints) > 0:
                self.draw_keypoints(annotated_frame, keypoints)
        
        return annotated_frame
    
    def draw_keypoints(self, frame, keypoints):
        """Dibuja keypoints en el frame.
        
        Args:
            frame: Frame donde dibujar
            keypoints: Array numpy de keypoints
        """
        # Colores para diferentes tipos de keypoints
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
        
        try:
            # Convertir a numpy array si no lo es
            if not isinstance(keypoints, np.ndarray):
                keypoints = np.array(keypoints)
            
            # Iterar sobre los keypoints
            for i in range(len(keypoints)):
                if len(keypoints[i]) >= 3:
                    x, y, visibility = keypoints[i][:3]
                    if float(visibility) > 0.5:  # Solo dibujar si es visible
                        color = colors[i % len(colors)]
                        cv2.circle(frame, (int(float(x)), int(float(y))), 3, color, -1)
                        cv2.circle(frame, (int(float(x)), int(float(y))), 5, color, 1)
        except Exception as e:
            print(f"Error dibujando keypoints: {e}")
    
    def display_frame(self, frame):
        """Muestra el frame en el canvas.
        
        Args:
            frame: Frame a mostrar
        """
        # Redimensionar frame para ajustarse al canvas
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            frame_resized = cv2.resize(frame, (canvas_width, canvas_height))
        else:
            frame_resized = frame
        
        # Convertir de BGR a RGB
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        
        # Convertir a formato PIL
        image_pil = Image.fromarray(frame_rgb)
        image_tk = ImageTk.PhotoImage(image_pil)
        
        # Actualizar canvas en el hilo principal
        self.root.after(0, self._update_canvas, image_tk)
    
    def _update_canvas(self, image_tk):
        """Actualiza el canvas con la nueva imagen."""
        self.video_canvas.delete("all")
        self.video_canvas.create_image(0, 0, anchor=tk.NW, image=image_tk)
        self.video_canvas.image = image_tk  # Mantener referencia
    
    def update_detection_info(self, detections):
        """Actualiza la información de detecciones.
        
        Args:
            detections: Lista de detecciones
        """
        info_text = f"Timestamp: {time.strftime('%H:%M:%S')}\n"
        info_text += f"Detecciones encontradas: {len(detections)}\n\n"
        
        for i, detection in enumerate(detections):
            confidence = detection.get('confidence', 0)
            if confidence < self.confidence_threshold.get():
                continue
                
            class_name = detection.get('class_name', 'unknown')
            bbox = detection.get('bbox', [])
            
            info_text += f"Detección {i+1}:\n"
            info_text += f"  Clase: {class_name}\n"
            info_text += f"  Confianza: {confidence:.3f}\n"
            
            if len(bbox) >= 4:
                info_text += f"  BBox: ({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f})\n"
            
            keypoints = detection.get('keypoints', [])
            if keypoints is not None and len(keypoints) > 0:
                info_text += f"  Keypoints: {len(keypoints)} puntos\n"
            
            info_text += "\n"
        
        # Actualizar texto en el hilo principal
        self.root.after(0, self._update_info_text, info_text)
    
    def _update_info_text(self, text):
        """Actualiza el texto de información."""
        self.detection_info.delete(1.0, tk.END)
        self.detection_info.insert(1.0, text)
        self.detection_info.see(tk.END)
    
    def capture_frame(self):
        """Captura el frame actual."""
        if self.current_frame is not None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"data/processed/capture_{timestamp}.jpg"
            
            # Crear directorio si no existe
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            
            cv2.imwrite(filename, self.current_frame)
            messagebox.showinfo("Captura", f"Frame guardado como: {filename}")
            self.logger.info(f"Frame capturado: {filename}")
        else:
            messagebox.showwarning("Advertencia", "No hay frame disponible para capturar")
            
    # ===== MÉTODOS PARA POSTPROCESAMIENTO =====
    
    def setup_postprocess_control_panel(self, parent):
        """Configura el panel de control para postprocesamiento."""
        # Frame principal con scroll
        main_control_frame = ttk.LabelFrame(parent, text=self.t("postprocess.config_title"), padding=5)
        main_control_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Canvas y scrollbar para el contenido
        canvas = tk.Canvas(main_control_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_control_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configurar grid
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        main_control_frame.grid_rowconfigure(0, weight=1)
        main_control_frame.grid_columnconfigure(0, weight=1)
        
        # Usar scrollable_frame como control_frame
        control_frame = scrollable_frame
        
        # Configurar scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # Configuración de fuente de video
        self.postprocess_video_label = ttk.Label(control_frame, text=self.t("postprocess.video_source"))
        self.postprocess_video_label.grid(row=1, column=0, sticky="w", pady=5)
        video_frame = ttk.Frame(control_frame)
        video_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Entry(video_frame, textvariable=self.postprocess_video_source, width=20).pack(side=tk.LEFT, padx=(0, 5))
        self.browse_postprocess_btn = ttk.Button(video_frame, text=self.t("postprocess.browse"), command=self.browse_postprocess_video)
        self.browse_postprocess_btn.pack(side=tk.LEFT)
        
        # Factor de calibración píxeles/cm
        self.calibration_pixels_cm_label = ttk.Label(control_frame, text=self.t("postprocess.calibration_pixels_cm"))
        self.calibration_pixels_cm_label.grid(row=3, column=0, sticky="w", pady=5)
        cal_scale = ttk.Scale(control_frame, from_=1.0, to=50.0, variable=self.pixels_per_cm, 
                             orient=tk.HORIZONTAL, length=200)
        cal_scale.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.cal_label = ttk.Label(control_frame, text=self.t("postprocess.calibration_label", value=self.pixels_per_cm.get()))
        self.cal_label.grid(row=5, column=0, sticky="w")
        
        # Opciones de visualización - Distancia Pulsador-Pórtico
        self.distance_button_gantry_label = ttk.Label(control_frame, text=self.t("postprocess.distance_button_gantry"))
        self.distance_button_gantry_label.grid(row=6, column=0, sticky="w", pady=(20, 5))
        
        self.show_distance_button_gantry_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.show_distance_button_gantry"), 
                       variable=self.show_distance)
        self.show_distance_button_gantry_check.grid(row=7, column=0, sticky="w", pady=2)
        
        self.show_line_button_gantry_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.show_line_button_gantry"), 
                       variable=self.show_distance_line)
        self.show_line_button_gantry_check.grid(row=8, column=0, sticky="w", pady=2)
        
        # Opciones de visualización - Distancia Marcador
        self.distance_marker_title_label = ttk.Label(control_frame, text=self.t("postprocess.distance_marker_title"))
        self.distance_marker_title_label.grid(row=9, column=0, sticky="w", pady=(15, 5))
        
        self.show_marker_distance_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.show_marker_distance"), 
                       variable=self.show_marker_distance)
        self.show_marker_distance_check.grid(row=10, column=0, sticky="w", pady=2)
        
        self.show_marker_line_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.show_marker_line"), 
                       variable=self.show_marker_distance_line)
        self.show_marker_line_check.grid(row=11, column=0, sticky="w", pady=2)
        
        # Calibración para marcador
        self.calibration_marker_pixels_cm_label = ttk.Label(control_frame, text=self.t("postprocess.calibration_marker_pixels_cm"))
        self.calibration_marker_pixels_cm_label.grid(row=12, column=0, sticky="w", pady=(10, 2))
        marker_cal_scale = ttk.Scale(control_frame, from_=1.0, to=50.0, variable=self.marker_pixels_per_cm, 
                                   orient=tk.HORIZONTAL, length=200)
        marker_cal_scale.grid(row=13, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.marker_cal_label = ttk.Label(control_frame, text=self.t("postprocess.marker_calibration_label", value=self.marker_pixels_per_cm.get()))
        self.marker_cal_label.grid(row=14, column=0, sticky="w")
        
        # Configuración del Sistema de Coordenadas
        self.coordinate_system_label = ttk.Label(control_frame, text=self.t("postprocess.coordinate_system_title"))
        self.coordinate_system_label.grid(row=15, column=0, sticky="w", pady=(20, 5))
        
        self.show_coordinate_system_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.show_coordinate_system"), 
                       variable=self.show_coordinate_system)
        self.show_coordinate_system_check.grid(row=16, column=0, sticky="w", pady=2)
        
        # Posición del sistema de coordenadas
        position_frame = ttk.Frame(control_frame)
        position_frame.grid(row=17, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.coordinate_position_label = ttk.Label(position_frame, text=self.t("postprocess.coordinate_position"))
        self.coordinate_position_label.pack(side=tk.LEFT)
        
        position_combo = ttk.Combobox(position_frame, textvariable=self.coordinate_position, 
                                     values=["bottom_right", "bottom_left", "top_right", "top_left"],
                                     state="readonly", width=12)
        position_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Tamaño del sistema de coordenadas
        self.coordinate_size_label = ttk.Label(control_frame, text=self.t("postprocess.coordinate_size"))
        self.coordinate_size_label.grid(row=18, column=0, sticky="w", pady=(10, 2))
        coord_size_scale = ttk.Scale(control_frame, from_=40, to=150, variable=self.coordinate_size, 
                                   orient=tk.HORIZONTAL, length=200)
        coord_size_scale.grid(row=19, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.coord_size_label = ttk.Label(control_frame, text=f"Tamaño: {self.coordinate_size.get()} px")
        self.coord_size_label.grid(row=20, column=0, sticky="w")
        
        # Configuración MQTT
        self.mqtt_config_label = ttk.Label(control_frame, text=self.t("postprocess.mqtt_config"))
        self.mqtt_config_label.grid(row=21, column=0, sticky="w", pady=(20, 5))
        
        self.mqtt_enabled_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.mqtt_enabled"), 
                       variable=self.mqtt_enabled, command=self.toggle_mqtt)
        self.mqtt_enabled_check.grid(row=22, column=0, sticky="w", pady=2)
        
        # Broker MQTT
        mqtt_frame = ttk.Frame(control_frame)
        mqtt_frame.grid(row=23, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.mqtt_broker_label = ttk.Label(mqtt_frame, text=self.t("postprocess.mqtt_broker"))
        self.mqtt_broker_label.pack(side=tk.LEFT)
        ttk.Entry(mqtt_frame, textvariable=self.mqtt_broker, width=15).pack(side=tk.LEFT, padx=(5, 10))
        self.mqtt_port_label = ttk.Label(mqtt_frame, text=self.t("postprocess.mqtt_port"))
        self.mqtt_port_label.pack(side=tk.LEFT)
        ttk.Entry(mqtt_frame, textvariable=self.mqtt_port, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Estado MQTT
        self.mqtt_status_label = ttk.Label(control_frame, textvariable=self.mqtt_status, foreground="red")
        self.mqtt_status_label.grid(row=24, column=0, sticky="w", pady=2)
        
        # Configuración de Filtros de Movimiento
        self.movement_filters_label = ttk.Label(control_frame, text=self.t("postprocess.movement_filters"))
        self.movement_filters_label.grid(row=25, column=0, sticky="w", pady=(20, 5))
        
        # Filtros habilitados/deshabilitados
        self.filter_distance_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.filter_distance"), 
                       variable=self.filter_distance_enabled, command=self.update_movement_filters)
        self.filter_distance_check.grid(row=26, column=0, sticky="w", pady=2)
        
        self.filter_velocity_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.filter_velocity"), 
                       variable=self.filter_velocity_enabled, command=self.update_movement_filters)
        self.filter_velocity_check.grid(row=27, column=0, sticky="w", pady=2)
        
        self.filter_stability_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.filter_stability"), 
                       variable=self.filter_stability_enabled, command=self.update_movement_filters)
        self.filter_stability_check.grid(row=28, column=0, sticky="w", pady=2)
        
        self.filter_relative_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.filter_relative"), 
                       variable=self.filter_relative_enabled, command=self.update_movement_filters)
        self.filter_relative_check.grid(row=29, column=0, sticky="w", pady=2)
        
        self.filter_temporal_check = ttk.Checkbutton(control_frame, text=self.t("postprocess.filter_temporal"), 
                       variable=self.filter_temporal_enabled, command=self.update_movement_filters)
        self.filter_temporal_check.grid(row=30, column=0, sticky="w", pady=2)
        
        # Parámetros de filtros
        self.distance_threshold_label_title = ttk.Label(control_frame, text=self.t("postprocess.distance_threshold"))
        self.distance_threshold_label_title.grid(row=31, column=0, sticky="w", pady=(10, 2))
        dist_scale = ttk.Scale(control_frame, from_=0.5, to=10.0, variable=self.distance_threshold, 
                              orient=tk.HORIZONTAL, length=200)
        dist_scale.grid(row=32, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.dist_threshold_label = ttk.Label(control_frame, text=f"Distancia: {self.distance_threshold.get():.1f} cm")
        self.dist_threshold_label.grid(row=33, column=0, sticky="w")
        
        self.velocity_threshold_label_title = ttk.Label(control_frame, text=self.t("postprocess.velocity_threshold"))
        self.velocity_threshold_label_title.grid(row=34, column=0, sticky="w", pady=(10, 2))
        vel_scale = ttk.Scale(control_frame, from_=0.1, to=5.0, variable=self.velocity_threshold, 
                             orient=tk.HORIZONTAL, length=200)
        vel_scale.grid(row=35, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.vel_threshold_label = ttk.Label(control_frame, text=f"Velocidad: {self.velocity_threshold.get():.1f} cm/s")
        self.vel_threshold_label.grid(row=36, column=0, sticky="w")
        
        self.temporal_window_label_title = ttk.Label(control_frame, text=self.t("postprocess.temporal_window"))
        self.temporal_window_label_title.grid(row=37, column=0, sticky="w", pady=(10, 2))
        temp_scale = ttk.Scale(control_frame, from_=1, to=10, variable=self.temporal_window, 
                              orient=tk.HORIZONTAL, length=200)
        temp_scale.grid(row=38, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.temp_window_label = ttk.Label(control_frame, text=f"Ventana: {self.temporal_window.get()} frames")
        self.temp_window_label.grid(row=39, column=0, sticky="w")
        
        # Botones de control
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=40, column=0, columnspan=2, pady=(20, 0))
        
        self.start_postprocess_button = ttk.Button(button_frame, text=self.t("postprocess.start_postprocess"), 
                                                  command=self.start_postprocessing)
        self.start_postprocess_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_postprocess_button = ttk.Button(button_frame, text=self.t("postprocess.stop_postprocess"), 
                                                 command=self.stop_postprocessing, state="disabled")
        self.stop_postprocess_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.calibrate_button_gantry_btn = ttk.Button(button_frame, text=self.t("postprocess.calibrate_button_gantry"), 
                  command=self.calibrate_distance)
        self.calibrate_button_gantry_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.calibrate_marker_btn = ttk.Button(button_frame, text=self.t("postprocess.calibrate_marker"), 
                  command=self.calibrate_marker_distance)
        self.calibrate_marker_btn.pack(side=tk.LEFT)
        
        # Configurar callbacks para actualizar etiquetas
        self.pixels_per_cm.trace('w', self.update_cal_label)
        self.marker_pixels_per_cm.trace('w', self.update_marker_cal_label)
        self.distance_threshold.trace('w', self.update_dist_threshold_label)
        self.velocity_threshold.trace('w', self.update_vel_threshold_label)
        self.temporal_window.trace('w', self.update_temp_window_label)
        self.coordinate_size.trace('w', self.update_coord_size_label)
        
        # Actualizar estado MQTT inicial
        self.update_mqtt_status()
        
    def setup_postprocess_video_panel(self, parent):
        """Configura el panel de video para postprocesamiento."""
        self.postprocess_video_frame = ttk.LabelFrame(parent, text=self.t("postprocess.video_analysis_title"), padding=10)
        self.postprocess_video_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Canvas para mostrar video
        self.postprocess_canvas = tk.Canvas(self.postprocess_video_frame, width=800, height=600, bg='black')
        self.postprocess_canvas.pack(expand=True, fill=tk.BOTH)
        
        # Texto de estado
        self.postprocess_status_text = tk.StringVar(value=self.t("postprocess.postprocess_status_start"))
        status_label = ttk.Label(self.postprocess_video_frame, textvariable=self.postprocess_status_text)
        status_label.pack(pady=5)
        
        # Configurar redimensionamiento
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        
    def setup_postprocess_info_panel(self, parent):
        """Configura el panel de información para postprocesamiento."""
        self.distance_info_frame = ttk.LabelFrame(parent, text=self.t("postprocess.distance_info_title"), padding=10)
        self.distance_info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Información de distancias
        self.distance_info = tk.Text(self.distance_info_frame, height=8, width=80, 
                                   bg='#1e1e1e', fg='white', font=('Consolas', 9))
        self.distance_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar para el texto
        scrollbar2 = ttk.Scrollbar(self.distance_info_frame, orient=tk.VERTICAL, command=self.distance_info.yview)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        self.distance_info.config(yscrollcommand=scrollbar2.set)
        
        parent.grid_rowconfigure(1, weight=0)
        
    def setup_virtual_position_tab(self):
        """Configura la pestaña de posición virtual."""
        # Panel de control para posición virtual (izquierda)
        self.setup_virtual_position_control_panel(self.virtual_position_frame)
        
        # Panel de visualización para posición virtual (derecha)
        self.setup_virtual_position_display_panel(self.virtual_position_frame)
        
        # Panel de información para posición virtual (abajo)
        self.setup_virtual_position_info_panel(self.virtual_position_frame)
        
    def setup_virtual_position_control_panel(self, parent):
        """Configura el panel de control para posición virtual."""
        self.virtual_position_control_frame = ttk.LabelFrame(parent, text=self.t("virtual_position.config_title"), padding=10)
        self.virtual_position_control_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Configuración de fuente de video
        self.virtual_video_source_label = ttk.Label(self.virtual_position_control_frame, text=self.t("postprocess.video_source"))
        self.virtual_video_source_label.grid(row=0, column=0, sticky="w", pady=5)
        video_frame = ttk.Frame(self.virtual_position_control_frame)
        video_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.virtual_video_source = tk.StringVar(value="0")
        ttk.Entry(video_frame, textvariable=self.virtual_video_source, width=20).pack(side=tk.LEFT, padx=(0, 5))
        self.browse_virtual_btn = ttk.Button(video_frame, text=self.t("postprocess.browse"), command=self.browse_virtual_video)
        self.browse_virtual_btn.pack(side=tk.LEFT)
        
        # Opciones de visualización
        self.virtual_visualization_options_label = ttk.Label(self.virtual_position_control_frame, text=self.t("virtual_position.visualization_options"))
        self.virtual_visualization_options_label.grid(row=2, column=0, sticky="w", pady=(20, 5))
        
        self.enable_virtual_check = ttk.Checkbutton(self.virtual_position_control_frame, text=self.t("virtual_position.enable_virtual"), 
                       variable=self.virtual_position_enabled)
        self.enable_virtual_check.grid(row=3, column=0, sticky="w", pady=2)
        
        self.show_trajectory_check = ttk.Checkbutton(self.virtual_position_control_frame, text=self.t("virtual_position.show_trajectory"), 
                       variable=self.show_trajectory)
        self.show_trajectory_check.grid(row=4, column=0, sticky="w", pady=2)
        
        # Calibración del sistema de coordenadas
        self.coordinate_system_label = ttk.Label(self.virtual_position_control_frame, text=self.t("virtual_position.coordinate_system"))
        self.coordinate_system_label.grid(row=5, column=0, sticky="w", pady=(20, 5))
        
        self.calibrate_system_btn = ttk.Button(self.virtual_position_control_frame, text=self.t("virtual_position.calibrate_system"), 
                  command=self.calibrate_coordinate_system)
        self.calibrate_system_btn.grid(row=6, column=0, sticky="w", pady=5)
        
        self.coord_status_label = ttk.Label(self.virtual_position_control_frame, text="❌ " + self.t("virtual_position.not_calibrated"), foreground="red")
        self.coord_status_label.grid(row=7, column=0, sticky="w", pady=2)
        
        # Información de posición actual
        ttk.Label(self.virtual_position_control_frame, text=self.t("virtual_position.current_position")).grid(row=8, column=0, sticky="w", pady=(20, 5))
        
        self.pulsador_pos_label = ttk.Label(self.virtual_position_control_frame, text="Pulsador: (0, 0)")
        self.pulsador_pos_label.grid(row=9, column=0, sticky="w", pady=2)
        
        self.portico_pos_label = ttk.Label(self.virtual_position_control_frame, text="Pórtico: (0, 0)")
        self.portico_pos_label.grid(row=10, column=0, sticky="w", pady=2)
        
        self.distance_pos_label = ttk.Label(self.virtual_position_control_frame, text=self.t("virtual_position.distance_label"))
        self.distance_pos_label.grid(row=11, column=0, sticky="w", pady=2)
        
        # Botones de control
        button_frame = ttk.Frame(self.virtual_position_control_frame)
        button_frame.grid(row=12, column=0, columnspan=2, pady=(20, 0))
        
        self.start_virtual_button = ttk.Button(button_frame, text=self.t("virtual_position.start_visualization"), 
                                              command=self.start_virtual_position)
        self.start_virtual_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_virtual_button = ttk.Button(button_frame, text=self.t("virtual_position.stop"), 
                                             command=self.stop_virtual_position, state="disabled")
        self.stop_virtual_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text=self.t("virtual_position.clear_trajectory"), 
                  command=self.clear_trajectory).pack(side=tk.LEFT)
        
    def setup_virtual_position_display_panel(self, parent):
        """Configura el panel de visualización para posición virtual."""
        display_frame = ttk.LabelFrame(parent, text=self.t("virtual_position.visualization_title"), padding=10)
        display_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Crear figura para el gráfico 2D con estilo profesional
        self.virtual_fig = Figure(figsize=(10, 8), dpi=100, facecolor='white')
        self.virtual_ax = self.virtual_fig.add_subplot(111)
        
        # Configurar estilo profesional del gráfico
        self.virtual_ax.set_facecolor('#f8f9fa')
        self.virtual_ax.set_title(self.t('virtual_position.graph_title'), 
                                 fontsize=14, fontweight='bold', pad=20)
        self.virtual_ax.set_xlabel('Posición X (cm)', fontsize=12, fontweight='bold')
        self.virtual_ax.set_ylabel('Posición Y (cm)', fontsize=12, fontweight='bold')
        
        # Grid profesional
        self.virtual_ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        self.virtual_ax.set_aspect('equal')
        
        # Configurar límites iniciales
        self.virtual_ax.set_xlim(-50, 50)
        self.virtual_ax.set_ylim(-50, 50)
        
        # Añadir círculos concéntricos para referencia
        for radius in [10, 20, 30, 40]:
            circle = plt.Circle((0, 0), radius, fill=False, color='lightgray', 
                              alpha=0.5, linestyle='--', linewidth=1)
            self.virtual_ax.add_patch(circle)
        
        # Añadir ejes de referencia
        self.virtual_ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3, linewidth=1)
        self.virtual_ax.axvline(x=0, color='gray', linestyle='-', alpha=0.3, linewidth=1)
        
        self.virtual_canvas = FigureCanvasTkAgg(self.virtual_fig, display_frame)
        self.virtual_canvas.draw()
        self.virtual_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configurar redimensionamiento
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        
    def setup_virtual_position_info_panel(self, parent):
        """Configura el panel de información para posición virtual."""
        info_frame = ttk.LabelFrame(parent, text=self.t("virtual_position.info_title"), padding=10)
        info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Información de posición virtual
        self.virtual_info = tk.Text(info_frame, height=8, width=80, 
                                   bg='#1e1e1e', fg='white', font=('Consolas', 9))
        self.virtual_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar para el texto
        scrollbar3 = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.virtual_info.yview)
        scrollbar3.pack(side=tk.RIGHT, fill=tk.Y)
        self.virtual_info.config(yscrollcommand=scrollbar3.set)
        
        parent.grid_rowconfigure(1, weight=0)
        
    def browse_virtual_video(self):
        """Abre diálogo para seleccionar archivo de video para posición virtual."""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.virtual_video_source.set(filename)
            
    def calibrate_coordinate_system(self):
        """Abre diálogo para calibrar el sistema de coordenadas."""
        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("virtual_position.calibration_dialog_title"))
        dialog.geometry("500x400")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar el diálogo
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        ttk.Label(dialog, text=self.t("virtual_position.calibration_dialog_title"), 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        ttk.Label(dialog, text=self.t("virtual_position.instructions")).pack(pady=(10, 5))
        ttk.Label(dialog, text=self.t("virtual_position.calibration_step1")).pack()
        ttk.Label(dialog, text=self.t("virtual_position.calibration_step2")).pack()
        ttk.Label(dialog, text=self.t("virtual_position.calibration_step3")).pack(pady=(0, 10))
        
        # Frame para configuración
        config_frame = ttk.LabelFrame(dialog, text=self.t("virtual_position.configuration"), padding=10)
        config_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # Origen
        ttk.Label(config_frame, text=self.t("virtual_position.origin_x")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        origin_x_entry = ttk.Entry(config_frame, width=15)
        origin_x_entry.grid(row=0, column=1, padx=5, pady=2)
        origin_x_entry.insert(0, "320")
        
        ttk.Label(config_frame, text=self.t("virtual_position.origin_y")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        origin_y_entry = ttk.Entry(config_frame, width=15)
        origin_y_entry.grid(row=1, column=1, padx=5, pady=2)
        origin_y_entry.insert(0, "240")
        
        # Escala
        ttk.Label(config_frame, text=self.t("virtual_position.scale")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        scale_entry = ttk.Entry(config_frame, width=15)
        scale_entry.grid(row=2, column=1, padx=5, pady=2)
        scale_entry.insert(0, str(self.pixels_per_cm.get()))
        
        # Botones
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def apply_calibration():
            try:
                origin_x = float(origin_x_entry.get())
                origin_y = float(origin_y_entry.get())
                scale = float(scale_entry.get())
                
                if scale > 0:
                    # Guardar configuración de calibración
                    self.coordinate_origin = (origin_x, origin_y)
                    self.coordinate_scale = scale
                    self.coordinate_system_calibrated.set(True)
                    
                    # Actualizar interfaz
                    self.coord_status_label.config(text="✅ " + self.t("virtual_position.calibrated"), foreground="green")
                    
                    messagebox.showinfo("Calibración", "Sistema de coordenadas calibrado correctamente")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "La escala debe ser positiva")
            except ValueError:
                messagebox.showerror("Error", "Introduce valores numéricos válidos")
        
        ttk.Button(button_frame, text=self.t("virtual_position.apply"), command=apply_calibration).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.t("virtual_position.cancel"), command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
    def start_virtual_position(self):
        """Inicia la visualización de posición virtual con calibración automática."""
        # Calibración automática desde postprocesamiento
        if hasattr(self, 'pixels_per_cm') and self.pixels_per_cm.get() > 0:
            # Usar calibración del postprocesamiento automáticamente
            self.coordinate_scale = self.pixels_per_cm.get()
            self.coordinate_origin = (320, 240)  # Centro de imagen por defecto
            self.coordinate_system_calibrated.set(True)
            self.coord_status_label.config(text="✅ " + self.t("virtual_position.auto_calibrated"), foreground="green")
            
        elif not self.coordinate_system_calibrated.get():
            # Calibración automática básica si no hay calibración previa
            self.coordinate_scale = 10.0  # Escala por defecto
            self.coordinate_origin = (320, 240)  # Centro por defecto
            self.coordinate_system_calibrated.set(True)
            self.coord_status_label.config(text="✅ " + self.t("virtual_position.auto_calibrated_basic"), foreground="orange")
            messagebox.showinfo("Calibración Automática", 
                               "Sistema calibrado automáticamente.\n" +
                               "Escala: 10 px/cm (básica)\n" +
                               "Origen: Centro de imagen")
            
        # Usar la misma fuente de video que el postprocesamiento si está disponible
        if hasattr(self, 'postprocess_capture') and self.postprocess_capture and self.postprocess_capture.isOpened():
            self.virtual_position_running = True
            self.start_virtual_button.config(state="disabled")
            self.stop_virtual_button.config(state="normal")
            messagebox.showinfo("Posición Virtual", 
                               "Visualización iniciada con calibración automática\n" +
                               f"Escala: {self.coordinate_scale:.1f} px/cm")
        else:
            self.virtual_position_running = True
            self.start_virtual_button.config(state="disabled")
            self.stop_virtual_button.config(state="normal")
            messagebox.showinfo("Posición Virtual", 
                               "Visualización iniciada con calibración automática\n" +
                               "Nota: Inicia el postprocesamiento para datos en tiempo real")
            
    def stop_virtual_position(self):
        """Detiene la visualización de posición virtual."""
        self.virtual_position_running = False
        self.start_virtual_button.config(state="normal")
        self.stop_virtual_button.config(state="disabled")
        
    def clear_trajectory(self):
        """Limpia la trayectoria mostrada."""
        self.virtual_position_history.clear()
        self.update_virtual_position_display()
        
    def update_virtual_position_display(self):
        """Actualiza la visualización de posición virtual con línea horizontal de 30 cm con origen en el extremo izquierdo."""
        if not self.virtual_position_enabled.get():
            return
            
        # Limpiar el gráfico manteniendo el estilo
        self.virtual_ax.clear()
        
        # Reconfigurar estilo profesional
        self.virtual_ax.set_facecolor('#f8f9fa')
        self.virtual_ax.set_title(self.t('virtual_position.graph_title'), 
                                 fontsize=14, fontweight='bold', pad=20)
        self.virtual_ax.set_xlabel(self.t('virtual_position.position_x_label'), fontsize=12, fontweight='bold')
        self.virtual_ax.set_ylabel(self.t('virtual_position.position_y_label'), fontsize=12, fontweight='bold')
        self.virtual_ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        self.virtual_ax.set_aspect('equal')
        
        # Configurar límites para mostrar la línea de 0 a 30 cm con origen en el extremo izquierdo
        self.virtual_ax.set_xlim(-5, 35)
        self.virtual_ax.set_ylim(-10, 10)
        
        # Dibujar línea horizontal de 30 cm (de 0 a 30 cm)
        line_start = 0
        line_end = 30
        line_y = 0
        
        # Línea principal de 30 cm
        self.virtual_ax.plot([line_start, line_end], [line_y, line_y], 
                           color='#2c3e50', linewidth=8, alpha=0.8, 
                           label=self.t('virtual_position.reference_line'), zorder=2)
        
        # Marcas de medición cada 5 cm
        for x in range(line_start, line_end + 1, 5):
            self.virtual_ax.plot([x, x], [line_y - 0.5, line_y + 0.5], 
                               color='#34495e', linewidth=2, alpha=0.7)
            # Etiquetas de medición
            self.virtual_ax.text(x, line_y - 1.5, f'{x}', 
                               ha='center', va='top', fontsize=9, 
                               fontweight='bold', color='#2c3e50')
        
        # Marcar el origen (extremo izquierdo)
        self.virtual_ax.plot(0, line_y, 's', color='#d32f2f', markersize=12, 
                           markeredgecolor='darkred', markeredgewidth=2, 
                           label='Origen (0,0)', zorder=5)
        
        # Marcar la posición del pórtico (keypoint D) - asumiendo que está a 15 cm del origen
        portico_x = 15  # Posición del pórtico en el nuevo sistema de coordenadas
        self.virtual_ax.plot(portico_x, line_y, '^', color='#ff9800', markersize=12, 
                           markeredgecolor='darkorange', markeredgewidth=2, 
                           label='Pórtico (Keypoint D)', zorder=5)
        
        # Dibujar trayectoria del círculo si está habilitada
        if self.show_trajectory.get() and len(self.virtual_position_history) > 1:
            trajectory_x = [pos['x'] for pos in self.virtual_position_history]
            trajectory_y = [line_y + 2] * len(trajectory_x)  # Mantener altura constante
            
            # Crear gradiente de color para la trayectoria
            colors = plt.cm.viridis(np.linspace(0, 1, len(trajectory_x)))
            
            for i in range(len(trajectory_x) - 1):
                self.virtual_ax.plot([trajectory_x[i], trajectory_x[i+1]], 
                                   [trajectory_y[i], trajectory_y[i+1]], 
                                   color=colors[i], alpha=0.7, linewidth=3)
            
            # Marcar puntos de la trayectoria
            self.virtual_ax.scatter(trajectory_x[:-1], trajectory_y[:-1], 
                                  c=colors[:-1], s=30, alpha=0.6, zorder=3)
        
        # Dibujar círculo del pulsador encima de la línea
        if hasattr(self, 'pulsador_position'):
            # La distancia calculada es la posición directa del pulsador desde el keypoint D del pórtico
            # En nuestro sistema: pórtico está a 15 cm del origen, pulsador se mueve hacia la izquierda
            distance_from_portico = self.pulsador_position['x']
            
            # Calcular posición absoluta: pórtico a 15 cm - distancia del pulsador al pórtico
            px = portico_x - distance_from_portico  # El pulsador se mueve hacia el origen (izquierda)
            
            # Limitar la posición X del círculo a los límites de la línea
            circle_x = max(line_start, min(line_end, px))
            circle_y = line_y + 2  # 2 cm encima de la línea
            
            # Círculo del pulsador
            self.virtual_ax.plot(circle_x, circle_y, 'o', color='#1976d2', 
                               markersize=16, markeredgecolor='darkblue', 
                               markeredgewidth=3, label=self.t('virtual_position.button'), zorder=4)
            
            # Línea vertical conectando el círculo con la línea
            self.virtual_ax.plot([circle_x, circle_x], [line_y, circle_y], 
                               color='#4caf50', linestyle='--', 
                               alpha=0.8, linewidth=2, zorder=2)
            
            # Mostrar posición X del pulsador (absoluta desde el origen)
            self.virtual_ax.text(circle_x, circle_y + 1.5, f'{circle_x:.1f} cm', 
                               bbox=dict(boxstyle="round,pad=0.5", 
                                       facecolor="#fff3e0", 
                                       edgecolor="#ff9800", 
                                       alpha=0.9),
                               fontsize=11, fontweight='bold',
                               ha='center', va='bottom', zorder=6)
            
            # Mostrar distancia desde el origen
            distance_from_origin = circle_x
            if distance_from_origin > 0.1:  # Solo mostrar si hay distancia significativa
                mid_x = distance_from_origin / 2
                self.virtual_ax.text(mid_x, line_y - 2.5, f'{self.t("virtual_position.distance_label")}: {distance_from_origin:.1f} cm', 
                                   bbox=dict(boxstyle="round,pad=0.3", 
                                           facecolor="#e8f5e8", 
                                           edgecolor="#4caf50", 
                                           alpha=0.9),
                                   fontsize=10, fontweight='bold',
                                   ha='center', va='top', zorder=6)
        
        # Añadir etiquetas de los extremos de la línea
        self.virtual_ax.text(line_start, line_y + 4, '0 cm (Origen)', 
                           ha='center', va='bottom', fontsize=10, 
                           fontweight='bold', color='#2c3e50',
                           bbox=dict(boxstyle="round,pad=0.3", 
                                   facecolor="white", alpha=0.8))
        self.virtual_ax.text(line_end, line_y + 4, '30 cm', 
                           ha='center', va='bottom', fontsize=10, 
                           fontweight='bold', color='#2c3e50',
                           bbox=dict(boxstyle="round,pad=0.3", 
                                   facecolor="white", alpha=0.8))
        
        # Leyenda con estilo
        legend = self.virtual_ax.legend(loc='upper right', frameon=True, 
                                      fancybox=True, shadow=True)
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)
        
        self.virtual_canvas.draw()
         
    def update_virtual_position(self, detections):
        """Actualiza la posición virtual basada en la distancia calculada por distance_calculator."""
        try:
            # Usar la distancia calculada por el distance_calculator del postprocess
            distance_cm = self.distance_calculator.calculate_pulsador_portico_distance(detections)
            
            if distance_cm is not None:
                # La posición X del pulsador es la distancia calculada
                # La posición Y se mantiene en 0 ya que el movimiento es principalmente horizontal
                relative_x = distance_cm
                relative_y = 0.0
                
                # Actualizar posiciones
                self.pulsador_position = {'x': relative_x, 'y': relative_y}
                self.portico_position = {'x': 0, 'y': 0}  # El pórtico es el origen
                
                # Agregar a historial de trayectoria
                if self.show_trajectory.get():
                    self.virtual_position_history.append({
                        'x': relative_x, 
                        'y': relative_y,
                        'timestamp': time.time()
                    })
                
                # Actualizar etiquetas de posición
                self.root.after(0, self.update_position_labels)
                
                # Actualizar visualización
                self.root.after(0, self.update_virtual_position_display)
                
                # Actualizar información de posición virtual
                self.root.after(0, self.update_virtual_info, detections)
            else:
                # Si no se puede calcular la distancia, mantener la última posición conocida
                self.logger.debug("No se pudo calcular la distancia para la posición virtual")
                    
        except Exception as e:
            self.logger.error(f"Error actualizando posición virtual: {e}")
            
    def update_position_labels(self):
        """Actualiza las etiquetas de posición en la interfaz."""
        try:
            # Calcular la posición absoluta del pulsador en el nuevo sistema de coordenadas
            distance_from_portico = self.pulsador_position['x']  # Distancia calculada relativa al pórtico
            portico_x = 15  # Posición del pórtico en el nuevo sistema de coordenadas
            px_absolute = portico_x - distance_from_portico  # Posición absoluta desde el origen (pórtico - distancia)
            py = self.pulsador_position['y']
            
            # Distancia desde el origen (extremo izquierdo)
            distance_from_origin = px_absolute
            
            self.pulsador_pos_label.config(text=f"{self.t('virtual_position.pulsador_position')}: ({px_absolute:.2f}, {py:.2f}) cm")
            self.portico_pos_label.config(text=f"{self.t('virtual_position.portico_position')}: ({portico_x:.2f}, 0.00) cm")
            self.distance_pos_label.config(text=f"{self.t('virtual_position.distance_label')}: {distance_from_origin:.2f} cm desde origen")
            
        except Exception as e:
            self.logger.error(f"Error actualizando etiquetas de posición: {e}")
            
    def update_virtual_info(self, detections):
        """Actualiza la información de posición virtual."""
        try:
            info_text = f"Timestamp: {time.strftime('%H:%M:%S')}\n"
            info_text += f"Fuente de datos: Distance Calculator (Postprocess)\n"
            info_text += f"Calibración automática: {'✅ Activa' if self.distance_calculator.auto_calibrated else '❌ Inactiva'}\n"
            info_text += f"Píxeles por cm: {self.distance_calculator.pixels_per_cm:.2f}\n\n"
            
            # Calcular distancia usando el distance_calculator
            distance_cm = self.distance_calculator.calculate_pulsador_portico_distance(detections)
            
            if distance_cm is not None:
                # Convertir posiciones al nuevo sistema de coordenadas
                distance_from_portico = self.pulsador_position['x']  # Distancia relativa al pórtico
                portico_x = 15  # Posición del pórtico en el nuevo sistema
                px_absolute = portico_x - distance_from_portico  # Posición absoluta desde el origen (pórtico - distancia)
                py = self.pulsador_position['y']
                
                info_text += "=== POSICIÓN VIRTUAL (ORIGEN EN EXTREMO IZQUIERDO) ===\n"
                info_text += f"Pulsador (posición absoluta desde origen):\n"
                info_text += f"  X: {px_absolute:.3f} cm (desde extremo izquierdo)\n"
                info_text += f"  Y: {py:.3f} cm (fijo en línea horizontal)\n"
                info_text += f"  Distancia desde origen: {px_absolute:.3f} cm\n\n"
                
                info_text += f"Pórtico (Keypoint D):\n"
                info_text += f"  X: {portico_x:.3f} cm (desde extremo izquierdo)\n"
                info_text += f"  Y: 0.000 cm\n\n"
                
                info_text += f"Distancia pulsador-pórtico: {distance_cm:.3f} cm\n\n"
                
                # Información de trayectoria
                if self.show_trajectory.get():
                    info_text += f"Puntos en trayectoria: {len(self.virtual_position_history)}\n"
                    if len(self.virtual_position_history) > 1:
                        # Calcular velocidad aproximada
                        recent_points = list(self.virtual_position_history)[-5:]
                        if len(recent_points) >= 2:
                            dt = recent_points[-1]['timestamp'] - recent_points[0]['timestamp']
                            if dt > 0:
                                dx = recent_points[-1]['x'] - recent_points[0]['x']
                                velocity = abs(dx) / dt  # Velocidad en X (horizontal)
                                info_text += f"Velocidad horizontal: {velocity:.2f} cm/s\n"
                
                info_text += "\n=== INFORMACIÓN DEL DISTANCE CALCULATOR ===\n"
                info_text += f"Distancia de referencia: {self.distance_calculator.reference_distance_cm} cm\n"
                info_text += f"Historial de calibración: {len(self.distance_calculator.calibration_history)} muestras\n"
                info_text += f"Filtrado temporal: {len(self.distance_calculator.keypoint_history)} frames\n"
                
                # Información de detecciones
                info_text += "\n=== DETECCIONES ACTUALES ===\n"
                for detection in detections:
                    class_name = detection.get('class_name', 'unknown')
                    confidence = detection.get('confidence', 0)
                    info_text += f"{class_name}: {confidence:.3f}\n"
                    
            else:
                info_text += "⚠️ No se puede calcular la distancia\n"
                info_text += "Verificar:\n"
                info_text += "- Detección del pulsador\n"
                info_text += "- Detección del pórtico\n"
                info_text += "- Keypoints visibles\n"
                info_text += "- Calibración automática\n"
            
            # Actualizar texto
            self.virtual_info.delete(1.0, tk.END)
            self.virtual_info.insert(1.0, info_text)
            self.virtual_info.see(tk.END)
            
        except Exception as e:
            self.logger.error(f"Error actualizando información virtual: {e}")
         
    def browse_postprocess_video(self):
        """Abre diálogo para seleccionar archivo de video para postprocesamiento."""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.postprocess_video_source.set(filename)
            
    def update_cal_label(self, *args):
        """Actualiza la etiqueta de calibración."""
        self.cal_label.config(text=self.t('calibration_label', value=self.pixels_per_cm.get()))
        self.distance_calculator.set_calibration(self.pixels_per_cm.get())
        
    def update_marker_cal_label(self, *args):
        """Actualiza la etiqueta de calibración del marcador."""
        self.marker_cal_label.config(text=self.t('marker_calibration_label', value=self.marker_pixels_per_cm.get()))
        self.marker_distance_calculator.set_calibration(self.marker_pixels_per_cm.get())
        
    def update_dist_threshold_label(self, *args):
        """Actualiza la etiqueta del umbral de distancia."""
        self.dist_threshold_label.config(text=self.t('distance_threshold_label', value=self.distance_threshold.get()))
        self.update_movement_filters()
        
    def update_vel_threshold_label(self, *args):
        """Actualiza la etiqueta del umbral de velocidad."""
        self.vel_threshold_label.config(text=self.t('velocity_threshold_label', value=self.velocity_threshold.get()))
        self.update_movement_filters()
        
    def update_temp_window_label(self, *args):
        """Actualiza la etiqueta de la ventana temporal."""
        self.temp_window_label.config(text=self.t('temporal_window_label', value=self.temporal_window.get()))
        self.update_movement_filters()
        
    def update_coord_size_label(self, *args):
        """Actualiza la etiqueta del tamaño del sistema de coordenadas."""
        self.coord_size_label.config(text=f"Tamaño: {self.coordinate_size.get()} px")
        
    def update_movement_filters(self):
        """Actualiza la configuración de filtros de movimiento en el DistanceCalculator."""
        if hasattr(self.distance_calculator, 'movement_detector'):
            # Actualizar configuración de filtros
            filter_config = {
                'distance_threshold': {
                    'enabled': self.filter_distance_enabled.get(),
                    'min_distance_cm': self.distance_threshold.get()
                },
                'velocity_threshold': {
                    'enabled': self.filter_velocity_enabled.get(),
                    'min_velocity_cm_per_s': self.velocity_threshold.get()
                },
                'stability_threshold': {
                    'enabled': self.filter_stability_enabled.get()
                },
                'relative_movement': {
                    'enabled': self.filter_relative_enabled.get()
                },
                'temporal_filter': {
                    'enabled': self.filter_temporal_enabled.get(),
                    'window_size': self.temporal_window.get()
                }
            }
            
            # Aplicar configuración al detector de movimiento
            self.distance_calculator.movement_detector.update_config(filter_config)
            
            self.logger.info(f"Filtros de movimiento actualizados: {filter_config}")
        
    def start_postprocessing(self):
        """Inicia el postprocesamiento en tiempo real."""
        if self.postprocess_running:
            return
        
        try:
            # Determinar fuente de video
            source = self.postprocess_video_source.get()
            if source.isdigit():
                source = int(source)
            
            # Inicializar captura de video
            self.postprocess_capture = cv2.VideoCapture(source)
            
            if not self.postprocess_capture.isOpened():
                messagebox.showerror("Error", f"No se pudo abrir la fuente de video: {source}")
                return
            
            # Configurar captura
            self.postprocess_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.postprocess_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.postprocess_running = True
            
            # Iniciar hilo de postprocesamiento
            self.postprocess_thread = threading.Thread(target=self.postprocess_loop, daemon=True)
            self.postprocess_thread.start()
            
            # Actualizar interfaz
            self.start_postprocess_button.config(state="disabled")
            self.stop_postprocess_button.config(state="normal")
            self.postprocess_status_text.set("Postprocesamiento en curso...")
            
            self.logger.info(f"Postprocesamiento iniciado con fuente: {source}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar postprocesamiento: {str(e)}")
            self.logger.error(f"Error al iniciar postprocesamiento: {e}")
            
    def stop_postprocessing(self):
        """Detiene el postprocesamiento."""
        self.postprocess_running = False
        
        if self.postprocess_capture:
            self.postprocess_capture.release()
            self.postprocess_capture = None
        
        # Actualizar interfaz
        self.start_postprocess_button.config(state="normal")
        self.stop_postprocess_button.config(state="disabled")
        self.postprocess_status_text.set("Postprocesamiento detenido")
        
        # Limpiar canvas
        self.postprocess_canvas.delete("all")
        
        self.logger.info("Postprocesamiento detenido")
        
    def postprocess_loop(self):
        """Bucle principal de postprocesamiento."""
        fps_counter = 0
        fps_start_time = time.time()
        
        while self.postprocess_running:
            try:
                ret, frame = self.postprocess_capture.read()
                
                if not ret:
                    self.logger.warning("No se pudo leer frame en postprocesamiento")
                    break
                
                # Realizar detección
                detections = self.detector.get_detections_data(frame)
                
                # Procesar frame con distancias
                processed_frame = self.process_frame_with_options(frame, detections)
                
                # Mostrar frame en la interfaz
                self.display_postprocess_frame(processed_frame)
                
                # Actualizar información de distancias
                self.update_distance_info(detections)
                
                # Actualizar posición virtual si está habilitada
                if self.virtual_position_running and self.coordinate_system_calibrated.get():
                    self.update_virtual_position(detections)
                
                # Calcular FPS y actualizar estadísticas
                fps_counter += 1
                if time.time() - fps_start_time >= 1.0:
                    fps = fps_counter / (time.time() - fps_start_time)
                    distance_cm = self.distance_calculator.calculate_pulsador_portico_distance(detections)
                    marker_distance_cm = self.marker_distance_calculator.calculate_marker_distance(detections)
                    
                    distance_text = f"{distance_cm:.2f} cm" if distance_cm else "N/A"
                    marker_distance_text = f"{marker_distance_cm:.2f} cm" if marker_distance_cm else "N/A"
                    
                    # Actualizar estadísticas para gráficos
                    self.update_statistics(detections, distance_cm, fps)
                    
                    self.root.after(0, lambda: self.postprocess_status_text.set(
                        f"FPS: {fps:.1f} | Pulsador-Pórtico: {distance_text} | Marcador: {marker_distance_text}"))
                    fps_counter = 0
                    fps_start_time = time.time()
                
                time.sleep(0.01)  # Pequeña pausa para no saturar la CPU
                
            except Exception as e:
                self.logger.error(f"Error en bucle de postprocesamiento: {e}")
                break
        
        # Limpiar al salir
        if self.postprocess_capture:
            self.postprocess_capture.release()
            
    def display_postprocess_frame(self, frame):
        """Muestra el frame procesado en el canvas de postprocesamiento."""
        # Redimensionar frame para ajustarse al canvas
        canvas_width = self.postprocess_canvas.winfo_width()
        canvas_height = self.postprocess_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            frame_resized = cv2.resize(frame, (canvas_width, canvas_height))
        else:
            frame_resized = frame
        
        # Convertir de BGR a RGB
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        
        # Convertir a formato PIL
        image_pil = Image.fromarray(frame_rgb)
        image_tk = ImageTk.PhotoImage(image_pil)
        
        # Actualizar canvas en el hilo principal
        self.root.after(0, self._update_postprocess_canvas, image_tk)
        
    def _update_postprocess_canvas(self, image_tk):
        """Actualiza el canvas de postprocesamiento con la nueva imagen."""
        self.postprocess_canvas.delete("all")
        self.postprocess_canvas.create_image(0, 0, anchor=tk.NW, image=image_tk)
        self.postprocess_canvas.image = image_tk  # Mantener referencia
        
    def update_distance_info(self, detections):
        """Actualiza la información de distancias."""
        distance_info = self.distance_calculator.get_distance_info(detections)
        marker_distance_info = self.marker_distance_calculator.get_distance_info(detections)
        
        info_text = f"Timestamp: {time.strftime('%H:%M:%S')}\n"
        info_text += f"Factor calibración pulsador-pórtico: {self.pixels_per_cm.get():.1f} px/cm\n"
        info_text += f"Factor calibración marcador: {self.marker_pixels_per_cm.get():.1f} px/cm\n\n"
        
        # Información distancia pulsador-pórtico
        info_text += "=== DISTANCIA PULSADOR-PÓRTICO ===\n"
        if distance_info['distance_cm'] is not None:
            info_text += f"DISTANCIA: {distance_info['distance_cm']:.2f} cm\n"
            info_text += f"Distancia en píxeles: {distance_info['distance_pixels']:.1f} px\n"
            
            if distance_info['pulsador_midpoint']:
                px, py = distance_info['pulsador_midpoint']
                info_text += f"Punto medio del pulsador: ({px:.1f}, {py:.1f})\n"
                
            if distance_info['portico_keypoint_d']:
                dx, dy = distance_info['portico_keypoint_d']
                info_text += f"Keypoint D del pórtico: ({dx:.1f}, {dy:.1f})\n"
        else:
            info_text += "No se pueden detectar ambos objetos (pulsador y pórtico)\n"
        
        # Información distancia marcador
        info_text += "\n=== DISTANCIA MARCADOR ===\n"
        if marker_distance_info['distance_cm'] is not None:
            info_text += f"DISTANCIA: {marker_distance_info['distance_cm']:.2f} cm\n"
            info_text += f"Distancia en píxeles: {marker_distance_info['distance_pixels']:.1f} px\n"
            
            if marker_distance_info.get('bbox_midpoint'):
                bx, by = marker_distance_info['bbox_midpoint']
                info_text += f"Punto medio bbox superior: ({bx:.1f}, {by:.1f})\n"
                
            if marker_distance_info.get('keypoints_midpoint'):
                kx, ky = marker_distance_info['keypoints_midpoint']
                info_text += f"Punto medio keypoints: ({kx:.1f}, {ky:.1f})\n"
        else:
            info_text += "No se puede detectar el marcador\n"
        
        info_text += f"\nDetecciones totales: {len(detections)}\n"
        for detection in detections:
            class_name = detection.get('class_name', 'unknown')
            confidence = detection.get('confidence', 0)
            info_text += f"  - {class_name}: {confidence:.3f}\n"
        
        # Agregar estadísticas de filtros de movimiento
        if hasattr(self.distance_calculator, 'movement_detector'):
            try:
                filter_stats = self.distance_calculator.movement_detector.get_filter_statistics()
                movement_metrics = self.distance_calculator.movement_detector.get_movement_metrics()
                
                info_text += "\n=== ESTADÍSTICAS DE FILTROS ===\n"
                info_text += f"Total cálculos: {filter_stats['total_calculations']}\n"
                info_text += f"Distancias enviadas: {filter_stats['sent_distances']}\n"
                info_text += f"Filtradas: {filter_stats['total_filtered']} ({filter_stats['filter_rate_percent']:.1f}%)\n\n"
                
                info_text += "Filtros activos:\n"
                for filter_name, status in filter_stats['filter_status'].items():
                    status_text = "✓" if status else "✗"
                    info_text += f"  {status_text} {filter_name.replace('_', ' ').title()}\n"
                
                info_text += "\nContadores de filtrado:\n"
                for filter_name, data in filter_stats['filters'].items():
                    if data['count'] > 0:
                        info_text += f"  - {filter_name.replace('_', ' ').title()}: {data['count']} ({data['percentage']:.1f}%)\n"
                
                info_text += "\nMétricas de movimiento:\n"
                info_text += f"  - Velocidad pulsador: {movement_metrics['pulsador_velocity_px_s']:.1f} px/s\n"
                info_text += f"  - Velocidad pórtico: {movement_metrics['portico_velocity_px_s']:.1f} px/s\n"
                info_text += f"  - Velocidad distancia: {movement_metrics['distance_velocity_cm_s']:.2f} cm/s\n"
                info_text += f"  - Posición estable: {movement_metrics['stable_position_count']} frames\n"
                
            except Exception as e:
                info_text += f"\nError obteniendo estadísticas de filtros: {e}\n"
        
        # Actualizar texto en el hilo principal
        self.root.after(0, self._update_distance_text, info_text)
        
    def _update_distance_text(self, text):
        """Actualiza el texto de información de distancias."""
        self.distance_info.delete(1.0, tk.END)
        self.distance_info.insert(1.0, text)
        self.distance_info.see(tk.END)
        
    def calibrate_distance(self):
        """Abre diálogo para calibrar la distancia."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Calibración de Distancia")
        dialog.geometry("400x300")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar el diálogo
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        ttk.Label(dialog, text="Calibración de Factor Píxeles/Centímetros", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        ttk.Label(dialog, text="Instrucciones:").pack(pady=(10, 5))
        ttk.Label(dialog, text="1. Mide una distancia conocida en la imagen").pack()
        ttk.Label(dialog, text="2. Cuenta los píxeles correspondientes").pack()
        ttk.Label(dialog, text="3. Calcula: píxeles ÷ centímetros").pack(pady=(0, 10))
        
        # Frame para entrada
        entry_frame = ttk.Frame(dialog)
        entry_frame.pack(pady=10)
        
        ttk.Label(entry_frame, text="Nuevo factor (px/cm):").grid(row=0, column=0, padx=5)
        cal_entry = ttk.Entry(entry_frame, width=15)
        cal_entry.grid(row=0, column=1, padx=5)
        cal_entry.insert(0, str(self.pixels_per_cm.get()))
        
        # Botones
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def apply_calibration():
            try:
                new_factor = float(cal_entry.get())
                if new_factor > 0:
                    self.pixels_per_cm.set(new_factor)
                    messagebox.showinfo("Calibración", f"Factor actualizado: {new_factor:.2f} px/cm")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "El factor debe ser positivo")
            except ValueError:
                messagebox.showerror("Error", "Introduce un número válido")
        
        ttk.Button(button_frame, text="Aplicar", command=apply_calibration).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def calibrate_marker_distance(self):
        """Abre diálogo para calibrar la distancia del marcador."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Calibración de Distancia Marcador")
        dialog.geometry("400x300")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar el diálogo
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        ttk.Label(dialog, text="Calibración de Factor Píxeles/Centímetros - Marcador", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        ttk.Label(dialog, text="Instrucciones:").pack(pady=(10, 5))
        ttk.Label(dialog, text="1. Mide una distancia conocida en la imagen del marcador").pack()
        ttk.Label(dialog, text="2. Cuenta los píxeles correspondientes").pack()
        ttk.Label(dialog, text="3. Calcula: píxeles ÷ centímetros").pack(pady=(0, 10))
        
        # Frame para entrada
        entry_frame = ttk.Frame(dialog)
        entry_frame.pack(pady=10)
        
        ttk.Label(entry_frame, text="Nuevo factor (px/cm):").grid(row=0, column=0, padx=5)
        cal_entry = ttk.Entry(entry_frame, width=15)
        cal_entry.grid(row=0, column=1, padx=5)
        cal_entry.insert(0, str(self.marker_pixels_per_cm.get()))
        
        # Botones
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def apply_calibration():
            try:
                new_factor = float(cal_entry.get())
                if new_factor > 0:
                    self.marker_pixels_per_cm.set(new_factor)
                    messagebox.showinfo("Calibración", f"Factor marcador actualizado: {new_factor:.2f} px/cm")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "El factor debe ser positivo")
            except ValueError:
                messagebox.showerror("Error", "Introduce un número válido")
        
        ttk.Button(button_frame, text="Aplicar", command=apply_calibration).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def process_frame_with_options(self, frame, detections):
        """Procesa el frame aplicando las opciones de visualización seleccionadas."""
        processed_frame = frame.copy()
        
        # Aplicar opciones de visualización para distancia pulsador-pórtico
        if self.show_distance.get() or self.show_distance_line.get():
            processed_frame = self.distance_calculator.draw_distance_on_frame(
                processed_frame, detections, 
                show_distance=self.show_distance.get(),
                show_line=self.show_distance_line.get()
            )
        
        # Aplicar opciones de visualización para distancia marcador
        if self.show_marker_distance.get() or self.show_marker_distance_line.get():
            processed_frame = self.marker_distance_calculator.draw_distance_on_frame(
                processed_frame, detections, 
                show_distance=self.show_marker_distance.get(),
                show_line=self.show_marker_distance_line.get()
            )
        
        # Aplicar sistema de coordenadas si está habilitado
        if self.show_coordinate_system.get():
            # Actualizar configuración del dibujador si ha cambiado
            if (self.coordinate_drawer.position != self.coordinate_position.get() or 
                self.coordinate_drawer.size != self.coordinate_size.get()):
                self.coordinate_drawer.set_position(self.coordinate_position.get())
                self.coordinate_drawer.set_size(self.coordinate_size.get())
            
            processed_frame = self.coordinate_drawer.draw_coordinate_system(processed_frame)
        
        return processed_frame
    
    def update_statistics(self, detections, distance_cm, fps):
        """Actualiza las estadísticas para los gráficos."""
        # Actualizar historial de distancias
        if distance_cm is not None:
            self.distance_history.append(distance_cm)
        
        # Actualizar estadísticas de detección
        for detection in detections:
            class_name = detection.get('class_name', 'unknown')
            if class_name in self.detection_stats:
                self.detection_stats[class_name] += 1
        
        # Actualizar historial de FPS
        self.fps_history.append(fps)
        
        # Actualizar historial de confianza
        for detection in detections:
            confidence = detection.get('confidence', 0)
            self.confidence_history.append(confidence)
        
        # Actualizar gráficos en la pestaña de datos
        self.root.after(0, self.update_data_plots)
    
    def setup_data_tab(self):
        """Configura la pestaña de datos con gráficos."""
        # Crear notebook para sub-pestañas de datos
        data_notebook = ttk.Notebook(self.data_frame)
        data_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sub-pestaña de distancias
        distance_frame = ttk.Frame(data_notebook)
        data_notebook.add(distance_frame, text=self.t("data.distances_tab"))
        
        # Sub-pestaña de detecciones
        detection_frame = ttk.Frame(data_notebook)
        data_notebook.add(detection_frame, text=self.t("data.detections_tab"))
        
        # Sub-pestaña de rendimiento
        performance_frame = ttk.Frame(data_notebook)
        data_notebook.add(performance_frame, text=self.t("data.performance_tab"))
        
        # Configurar gráficos de distancias
        self.setup_distance_plots(distance_frame)
        
        # Configurar gráficos de detecciones
        self.setup_detection_plots(detection_frame)
        
        # Configurar gráficos de rendimiento
        self.setup_performance_plots(performance_frame)
    
    def setup_distance_plots(self, parent):
        """Configura los gráficos de distancias."""
        # Frame superior para historial de distancias
        top_frame = ttk.LabelFrame(parent, text=self.t("data.distance_history"), padding=10)
        top_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Crear figura para historial de distancias
        self.distance_fig = Figure(figsize=(12, 4), dpi=100)
        self.distance_ax = self.distance_fig.add_subplot(111)
        self.distance_ax.set_title(self.t("data.distance_realtime_title"))
        self.distance_ax.set_xlabel(self.t("data.time_samples"))
        self.distance_ax.set_ylabel(self.t("data.distance_cm"))
        self.distance_ax.grid(True, alpha=0.3)
        
        self.distance_canvas = FigureCanvasTkAgg(self.distance_fig, top_frame)
        self.distance_canvas.draw()
        self.distance_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Frame inferior para histograma de distancias
        bottom_frame = ttk.LabelFrame(parent, text=self.t("data.distance_distribution"), padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Crear figura para histograma
        self.distance_hist_fig = Figure(figsize=(12, 4), dpi=100)
        self.distance_hist_ax = self.distance_hist_fig.add_subplot(111)
        self.distance_hist_ax.set_title(self.t("data.distance_histogram"))
        self.distance_hist_ax.set_xlabel(self.t("data.distance_cm"))
        self.distance_hist_ax.set_ylabel(self.t("data.frequency"))
        self.distance_hist_ax.grid(True, alpha=0.3)
        
        self.distance_hist_canvas = FigureCanvasTkAgg(self.distance_hist_fig, bottom_frame)
        self.distance_hist_canvas.draw()
        self.distance_hist_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def setup_detection_plots(self, parent):
        """Configura los gráficos de detecciones."""
        # Frame para estadísticas de detección
        stats_frame = ttk.LabelFrame(parent, text=self.t("data.detection_stats"), padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Crear figura para estadísticas de detección
        self.detection_fig = Figure(figsize=(12, 6), dpi=100)
        
        # Gráfico de barras para conteo de detecciones
        self.detection_ax1 = self.detection_fig.add_subplot(121)
        self.detection_ax1.set_title(self.t("data.detection_count_title"))
        self.detection_ax1.set_ylabel(self.t("data.detection_number"))
        
        # Gráfico de confianza promedio
        self.detection_ax2 = self.detection_fig.add_subplot(122)
        self.detection_ax2.set_title(self.t("data.confidence_history"))
        self.detection_ax2.set_xlabel(self.t("data.time_samples"))
        self.detection_ax2.set_ylabel(self.t("data.confidence"))
        self.detection_ax2.grid(True, alpha=0.3)
        
        self.detection_canvas = FigureCanvasTkAgg(self.detection_fig, stats_frame)
        self.detection_canvas.draw()
        self.detection_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def setup_performance_plots(self, parent):
        """Configura los gráficos de rendimiento."""
        # Frame para métricas de rendimiento
        perf_frame = ttk.LabelFrame(parent, text=self.t("data.performance_metrics"), padding=10)
        perf_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Crear figura para rendimiento
        self.performance_fig = Figure(figsize=(12, 8), dpi=100)
        
        # Gráfico de FPS
        self.fps_ax = self.performance_fig.add_subplot(211)
        self.fps_ax.set_title(self.t("data.system_performance_fps"))
        self.fps_ax.set_ylabel(self.t("data.fps"))
        self.fps_ax.grid(True, alpha=0.3)
        
        # Gráfico de estadísticas en tiempo real
        self.stats_ax = self.performance_fig.add_subplot(212)
        self.stats_ax.set_title(self.t("data.realtime_stats"))
        self.stats_ax.set_xlabel(self.t("data.time"))
        self.stats_ax.set_ylabel(self.t("data.values"))
        self.stats_ax.grid(True, alpha=0.3)
        
        self.performance_canvas = FigureCanvasTkAgg(self.performance_fig, perf_frame)
        self.performance_canvas.draw()
        self.performance_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Panel de información en tiempo real
        info_frame = ttk.LabelFrame(parent, text=self.t("data.system_info"), padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.system_info = tk.Text(info_frame, height=6, width=80, 
                                  bg='#1e1e1e', fg='white', font=('Consolas', 9))
        self.system_info.pack(fill=tk.BOTH, expand=True)
    
    def update_data_plots(self):
        """Actualiza todos los gráficos de datos."""
        try:
            self.update_distance_plots()
            self.update_detection_plots()
            self.update_performance_plots()
        except Exception as e:
            print(f"Error actualizando gráficos: {e}")
    
    def update_distance_plots(self):
        """Actualiza los gráficos de distancias."""
        if len(self.distance_history) > 0:
            # Actualizar gráfico de historial
            self.distance_ax.clear()
            self.distance_ax.plot(list(self.distance_history), 'b-', linewidth=2)
            self.distance_ax.set_title(self.t("data.distance_realtime_title"))
            self.distance_ax.set_xlabel(self.t("data.time_samples"))
            self.distance_ax.set_ylabel(self.t("data.distance_cm"))
            self.distance_ax.grid(True, alpha=0.3)
            
            # Agregar líneas de referencia
            if len(self.distance_history) > 0:
                avg_distance = np.mean(self.distance_history)
                self.distance_ax.axhline(y=avg_distance, color='r', linestyle='--', 
                                       label=f'{self.t("data.average")}: {avg_distance:.2f} cm')
                self.distance_ax.legend()
            
            # Actualizar histograma
            self.distance_hist_ax.clear()
            self.distance_hist_ax.hist(list(self.distance_history), bins=20, 
                                     alpha=0.7, color='skyblue', edgecolor='black')
            self.distance_hist_ax.set_title(self.t("data.distance_distribution"))
            self.distance_hist_ax.set_xlabel(self.t("data.distance_cm"))
            self.distance_hist_ax.set_ylabel(self.t("data.frequency"))
            self.distance_hist_ax.grid(True, alpha=0.3)
            
            # Redibujar
            self.distance_canvas.draw()
            self.distance_hist_canvas.draw()
    
    def update_detection_plots(self):
        """Actualiza los gráficos de detecciones."""
        # Actualizar gráfico de barras
        self.detection_ax1.clear()
        classes = list(self.detection_stats.keys())
        counts = list(self.detection_stats.values())
        colors = ['red', 'green', 'blue']
        
        bars = self.detection_ax1.bar(classes, counts, color=colors)
        self.detection_ax1.set_title(self.t("data.detection_count_title"))
        self.detection_ax1.set_ylabel(self.t("data.detection_number"))
        
        # Agregar valores en las barras
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            self.detection_ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                  f'{count}', ha='center', va='bottom')
        
        # Actualizar gráfico de confianza
        if len(self.confidence_history) > 0:
            self.detection_ax2.clear()
            self.detection_ax2.plot(list(self.confidence_history), 'g-', alpha=0.7)
            self.detection_ax2.set_title(self.t("data.confidence_history"))
            self.detection_ax2.set_xlabel(self.t("data.time_samples"))
            self.detection_ax2.set_ylabel(self.t("data.confidence"))
            self.detection_ax2.grid(True, alpha=0.3)
            self.detection_ax2.set_ylim(0, 1)
        
        # Redibujar
        self.detection_canvas.draw()
    
    def update_performance_plots(self):
        """Actualiza los gráficos de rendimiento."""
        # Actualizar gráfico de FPS
        if len(self.fps_history) > 0:
            self.fps_ax.clear()
            self.fps_ax.plot(list(self.fps_history), 'r-', linewidth=2)
            self.fps_ax.set_title(self.t("data.system_performance_fps"))
            self.fps_ax.set_ylabel('FPS')
            self.fps_ax.grid(True, alpha=0.3)
            
            # Agregar línea de FPS promedio
            avg_fps = np.mean(self.fps_history)
            self.fps_ax.axhline(y=avg_fps, color='orange', linestyle='--', 
                              label=f'FPS Promedio: {avg_fps:.1f}')
            self.fps_ax.legend()
        
        # Actualizar información del sistema
        current_time = datetime.now().strftime("%H:%M:%S")
        info_text = f"Última actualización: {current_time}\n"
        info_text += f"Total de muestras de distancia: {len(self.distance_history)}\n"
        info_text += f"FPS promedio: {np.mean(self.fps_history):.2f}\n" if self.fps_history else "FPS promedio: N/A\n"
        info_text += f"Confianza promedio: {np.mean(self.confidence_history):.3f}\n" if self.confidence_history else "Confianza promedio: N/A\n"
        
        if len(self.distance_history) > 0:
            info_text += f"Distancia actual: {self.distance_history[-1]:.2f} cm\n"
            info_text += f"Distancia promedio: {np.mean(self.distance_history):.2f} cm\n"
            info_text += f"Distancia mínima: {np.min(self.distance_history):.2f} cm\n"
            info_text += f"Distancia máxima: {np.max(self.distance_history):.2f} cm\n"
        
        self.system_info.delete(1.0, tk.END)
        self.system_info.insert(1.0, info_text)
        
        # Redibujar
        self.performance_canvas.draw()
    
    def toggle_mqtt(self):
        """Habilita o deshabilita MQTT."""
        try:
            if self.mqtt_enabled.get():
                # Habilitar MQTT
                self.distance_calculator.set_mqtt_enabled(True)
            else:
                # Deshabilitar MQTT
                self.distance_calculator.set_mqtt_enabled(False)
            
            self.update_mqtt_status()
            
        except Exception as e:
            self.logger.error(f"Error al cambiar estado MQTT: {e}")
            messagebox.showerror("Error MQTT", f"Error al cambiar estado MQTT: {str(e)}")
    
    def update_mqtt_status(self):
        """Actualiza el estado visual de MQTT."""
        try:
            mqtt_status = self.distance_calculator.get_mqtt_status()
            
            if mqtt_status['enabled'] and mqtt_status['connected']:
                self.mqtt_status.set("✅ Conectado y publicando")
                self.mqtt_status_label.config(foreground="green")
            elif mqtt_status['enabled'] and not mqtt_status['connected']:
                self.mqtt_status.set("⚠️ Habilitado pero desconectado")
                self.mqtt_status_label.config(foreground="orange")
            else:
                self.mqtt_status.set("❌ Deshabilitado")
                self.mqtt_status_label.config(foreground="red")
                
            # Programar próxima actualización
            self.root.after(2000, self.update_mqtt_status)
            
        except Exception as e:
            self.mqtt_status.set("❌ Error")
            self.mqtt_status_label.config(foreground="red")
            self.logger.error(f"Error actualizando estado MQTT: {e}")
    
    def config_high_precision(self):
        """Configura alta precisión."""
        self.confidence_threshold.set(0.8)
        self.iou_threshold.set(0.5)
        self.show_bboxes.set(True)
        self.show_keypoints.set(True)
        self.show_labels.set(True)
        self.current_config.set("Alta Precisión")
    
    def config_fast_detection(self):
        """Configura detección rápida."""
        self.confidence_threshold.set(0.5)
        self.iou_threshold.set(0.7)
        self.show_bboxes.set(True)
        self.show_keypoints.set(False)
        self.show_labels.set(False)
        self.current_config.set("Detección Rápida")
    
    def config_full_mode(self):
        """Configura modo completo."""
        self.confidence_threshold.set(0.6)
        self.iou_threshold.set(0.6)
        self.show_bboxes.set(True)
        self.show_keypoints.set(True)
        self.show_labels.set(True)
        self.current_config.set("Modo Completo")
    
    def config_keypoints_only(self):
        """Configura solo keypoints."""
        self.confidence_threshold.set(0.7)
        self.iou_threshold.set(0.5)
        self.show_bboxes.set(False)
        self.show_keypoints.set(True)
        self.show_labels.set(False)
        self.current_config.set("Solo Keypoints")
    
    def run(self):
        """Ejecuta la interfaz."""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error en la interfaz: {e}")
    
    def on_closing(self):
        """Maneja el cierre de la aplicación."""
        if self.running:
            self.stop_detection()
        
        if self.postprocess_running:
            self.stop_postprocessing()
        
        # Limpiar recursos MQTT
        try:
            if hasattr(self, 'distance_calculator'):
                self.distance_calculator.disconnect_mqtt()
            if hasattr(self, 'marker_distance_calculator'):
                self.marker_distance_calculator.disconnect_mqtt()
            if hasattr(self, 'dicapua_publisher') and self.dicapua_publisher:
                self.dicapua_publisher.stop_client()
                print("✅ DicapuaPublisher cerrado correctamente")
        except Exception as e:
            print(f"⚠️ Error al cerrar recursos MQTT: {e}")
        
        self.root.destroy()
        self.logger.info("Interfaz cerrada")

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interfaz Interactiva de Detección')
    parser.add_argument('--config', '-c', default='config/config.yaml',
                       help='Ruta al archivo de configuración')
    
    args = parser.parse_args()
    
    # Crear y ejecutar interfaz
    interface = InteractiveDetectionInterface(args.config)
    interface.run()

if __name__ == "__main__":
    main()