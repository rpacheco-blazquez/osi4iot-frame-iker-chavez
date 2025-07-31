"""Módulo de visualización para el gemelo digital del pórtico."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Dict, Tuple, Optional
import yaml
from datetime import datetime, timedelta
from collections import deque
import threading
import time

# Configurar matplotlib para modo interactivo
plt.ion()

class GantryVisualizer:
    """Visualizador principal para el sistema de pórtico."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Inicializa el visualizador.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config = self._load_config(config_path)
        self.viz_config = self.config['visualization']
        
        # Configuración de visualización
        self.update_frequency = self.viz_config['update_frequency']
        self.enable_3d = self.viz_config['3d_enabled']
        self.real_time_plots = self.viz_config['real_time_plots']
        
        # Datos para visualización
        self.force_history = deque(maxlen=1000)
        self.position_history = deque(maxlen=1000)
        self.time_history = deque(maxlen=1000)
        
        # Figuras de matplotlib
        self.fig_2d = None
        self.fig_3d = None
        self.fig_forces = None
        self.axes = {}
        
        # Animaciones
        self.animations = []
        self.running = False
        
        # Thread para actualización en tiempo real
        self.update_thread = None
        
    def _load_config(self, config_path: str) -> dict:
        """Carga la configuración desde archivo YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Archivo de configuración no encontrado: {config_path}")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Configuración por defecto."""
        return {
            'visualization': {
                'update_frequency': 30,
                '3d_enabled': True,
                'real_time_plots': True
            }
        }
    
    def setup_2d_view(self, figsize: Tuple[int, int] = (12, 8)):
        """Configura la vista 2D del pórtico.
        
        Args:
            figsize: Tamaño de la figura
        """
        self.fig_2d, axes = plt.subplots(2, 2, figsize=figsize)
        self.fig_2d.suptitle('Vista 2D del Sistema de Pórtico', fontsize=16)
        
        # Vista frontal (XZ)
        self.axes['front'] = axes[0, 0]
        self.axes['front'].set_title('Vista Frontal (XZ)')
        self.axes['front'].set_xlabel('X (m)')
        self.axes['front'].set_ylabel('Z (m)')
        self.axes['front'].grid(True)
        self.axes['front'].set_aspect('equal')
        
        # Vista lateral (YZ)
        self.axes['side'] = axes[0, 1]
        self.axes['side'].set_title('Vista Lateral (YZ)')
        self.axes['side'].set_xlabel('Y (m)')
        self.axes['side'].set_ylabel('Z (m)')
        self.axes['side'].grid(True)
        self.axes['side'].set_aspect('equal')
        
        # Vista superior (XY)
        self.axes['top'] = axes[1, 0]
        self.axes['top'].set_title('Vista Superior (XY)')
        self.axes['top'].set_xlabel('X (m)')
        self.axes['top'].set_ylabel('Y (m)')
        self.axes['top'].grid(True)
        self.axes['top'].set_aspect('equal')
        
        # Gráfico de trayectoria
        self.axes['trajectory'] = axes[1, 1]
        self.axes['trajectory'].set_title('Trayectoria de la Carga')
        self.axes['trajectory'].set_xlabel('Tiempo (s)')
        self.axes['trajectory'].set_ylabel('Posición (m)')
        self.axes['trajectory'].grid(True)
        
        plt.tight_layout()
    
    def setup_3d_view(self, figsize: Tuple[int, int] = (10, 8)):
        """Configura la vista 3D del pórtico.
        
        Args:
            figsize: Tamaño de la figura
        """
        if not self.enable_3d:
            return
        
        self.fig_3d = plt.figure(figsize=figsize)
        self.axes['3d'] = self.fig_3d.add_subplot(111, projection='3d')
        
        self.axes['3d'].set_title('Vista 3D del Sistema de Pórtico')
        self.axes['3d'].set_xlabel('X (m)')
        self.axes['3d'].set_ylabel('Y (m)')
        self.axes['3d'].set_zlabel('Z (m)')
        
        # Configurar límites iniciales
        self.axes['3d'].set_xlim([-5, 5])
        self.axes['3d'].set_ylim([-5, 5])
        self.axes['3d'].set_zlim([0, 10])
    
    def setup_force_plots(self, figsize: Tuple[int, int] = (12, 10)):
        """Configura los gráficos de fuerzas.
        
        Args:
            figsize: Tamaño de la figura
        """
        self.fig_forces, axes = plt.subplots(3, 2, figsize=figsize)
        self.fig_forces.suptitle('Análisis de Fuerzas en Tiempo Real', fontsize=16)
        
        # Fuerzas por componente
        self.axes['force_x'] = axes[0, 0]
        self.axes['force_x'].set_title('Fuerza X vs Tiempo')
        self.axes['force_x'].set_ylabel('Fuerza X (N)')
        self.axes['force_x'].grid(True)
        
        self.axes['force_y'] = axes[0, 1]
        self.axes['force_y'].set_title('Fuerza Y vs Tiempo')
        self.axes['force_y'].set_ylabel('Fuerza Y (N)')
        self.axes['force_y'].grid(True)
        
        self.axes['force_z'] = axes[1, 0]
        self.axes['force_z'].set_title('Fuerza Z vs Tiempo')
        self.axes['force_z'].set_ylabel('Fuerza Z (N)')
        self.axes['force_z'].grid(True)
        
        # Magnitud de fuerza total
        self.axes['force_magnitude'] = axes[1, 1]
        self.axes['force_magnitude'].set_title('Magnitud de Fuerza Total')
        self.axes['force_magnitude'].set_ylabel('|F| (N)')
        self.axes['force_magnitude'].grid(True)
        
        # Distribución de fuerzas
        self.axes['force_distribution'] = axes[2, 0]
        self.axes['force_distribution'].set_title('Distribución de Fuerzas')
        self.axes['force_distribution'].set_xlabel('Componente')
        self.axes['force_distribution'].set_ylabel('Fuerza (N)')
        
        # Espectro de frecuencias
        self.axes['force_spectrum'] = axes[2, 1]
        self.axes['force_spectrum'].set_title('Espectro de Frecuencias')
        self.axes['force_spectrum'].set_xlabel('Frecuencia (Hz)')
        self.axes['force_spectrum'].set_ylabel('Amplitud')
        self.axes['force_spectrum'].grid(True)
        
        plt.tight_layout()
    
    def draw_gantry_structure(self, ax, dimensions: Dict[str, float]):
        """Dibuja la estructura del pórtico.
        
        Args:
            ax: Eje de matplotlib donde dibujar
            dimensions: Dimensiones del pórtico
        """
        length = dimensions.get('length', 10.0)
        width = dimensions.get('width', 8.0)
        height = dimensions.get('height', 6.0)
        beam_width = dimensions.get('beam_width', 0.3)
        
        if ax.name == '3d':
            # Dibujar estructura 3D
            # Vigas horizontales superiores
            ax.plot([0, length], [0, 0], [height, height], 'b-', linewidth=3, label='Viga principal')
            ax.plot([0, length], [width, width], [height, height], 'b-', linewidth=3)
            ax.plot([0, 0], [0, width], [height, height], 'b-', linewidth=3)
            ax.plot([length, length], [0, width], [height, height], 'b-', linewidth=3)
            
            # Soportes verticales
            ax.plot([0, 0], [0, 0], [0, height], 'r-', linewidth=2, label='Soporte')
            ax.plot([length, length], [0, 0], [0, height], 'r-', linewidth=2)
            ax.plot([0, 0], [width, width], [0, height], 'r-', linewidth=2)
            ax.plot([length, length], [width, width], [0, height], 'r-', linewidth=2)
            
        else:
            # Dibujar estructura 2D según la vista
            if 'front' in ax.get_title().lower():
                # Vista frontal (XZ)
                ax.plot([0, length], [height, height], 'b-', linewidth=3, label='Viga')
                ax.plot([0, 0], [0, height], 'r-', linewidth=2, label='Soporte')
                ax.plot([length, length], [0, height], 'r-', linewidth=2)
                
            elif 'side' in ax.get_title().lower():
                # Vista lateral (YZ)
                ax.plot([0, width], [height, height], 'b-', linewidth=3, label='Viga')
                ax.plot([0, 0], [0, height], 'r-', linewidth=2, label='Soporte')
                ax.plot([width, width], [0, height], 'r-', linewidth=2)
                
            elif 'top' in ax.get_title().lower():
                # Vista superior (XY)
                rect = Rectangle((0, 0), length, width, linewidth=2, 
                               edgecolor='b', facecolor='none', label='Estructura')
                ax.add_patch(rect)
    
    def update_load_position(self, position: Tuple[float, float, float], 
                           load_mass: float = 1.0):
        """Actualiza la posición de la carga.
        
        Args:
            position: Posición de la carga (x, y, z)
            load_mass: Masa de la carga en kg
        """
        x, y, z = position
        timestamp = datetime.now()
        
        # Agregar a historial
        self.position_history.append(position)
        self.time_history.append(timestamp)
        
        # Actualizar visualización si está configurada
        if self.fig_2d and self.axes:
            self._update_2d_load_position(x, y, z)
        
        if self.fig_3d and self.axes.get('3d'):
            self._update_3d_load_position(x, y, z, load_mass)
    
    def _update_2d_load_position(self, x: float, y: float, z: float):
        """Actualiza la posición de la carga en vistas 2D."""
        # Limpiar posiciones anteriores de la carga
        for ax_name in ['front', 'side', 'top']:
            if ax_name in self.axes:
                # Remover marcadores anteriores de carga
                for artist in self.axes[ax_name].get_children():
                    if hasattr(artist, 'get_label') and 'Carga' in str(artist.get_label()):
                        artist.remove()
        
        # Dibujar nueva posición
        if 'front' in self.axes:
            self.axes['front'].plot(x, z, 'ro', markersize=8, label='Carga')
        
        if 'side' in self.axes:
            self.axes['side'].plot(y, z, 'ro', markersize=8, label='Carga')
        
        if 'top' in self.axes:
            self.axes['top'].plot(x, y, 'ro', markersize=8, label='Carga')
    
    def _update_3d_load_position(self, x: float, y: float, z: float, mass: float):
        """Actualiza la posición de la carga en vista 3D."""
        ax = self.axes['3d']
        
        # Limpiar carga anterior
        for artist in ax.get_children():
            if hasattr(artist, 'get_label') and 'Carga' in str(artist.get_label()):
                artist.remove()
        
        # Dibujar nueva carga
        ax.scatter([x], [y], [z], c='red', s=100*mass, alpha=0.8, label='Carga')
        
        # Dibujar cable (línea desde la viga hasta la carga)
        ax.plot([x, x], [y, y], [6, z], 'k--', linewidth=1, alpha=0.6, label='Cable')
    
    def update_forces(self, forces: Dict[str, Tuple[float, float, float]]):
        """Actualiza la visualización de fuerzas.
        
        Args:
            forces: Diccionario con fuerzas por componente
        """
        timestamp = datetime.now()
        
        # Agregar fuerzas al historial
        self.force_history.append(forces)
        
        if self.fig_forces and self.real_time_plots:
            self._update_force_plots()
    
    def _update_force_plots(self):
        """Actualiza los gráficos de fuerzas en tiempo real."""
        if not self.force_history or not self.time_history:
            return
        
        # Preparar datos para gráficos
        times = list(self.time_history)
        forces_x = []
        forces_y = []
        forces_z = []
        magnitudes = []
        
        for force_data in self.force_history:
            if 'load_weight' in force_data:
                fx, fy, fz = force_data['load_weight']
                forces_x.append(fx)
                forces_y.append(fy)
                forces_z.append(fz)
                magnitudes.append(np.sqrt(fx**2 + fy**2 + fz**2))
        
        # Actualizar gráficos de componentes
        if len(times) == len(forces_x):
            if 'force_x' in self.axes:
                self.axes['force_x'].clear()
                self.axes['force_x'].plot(times, forces_x, 'r-')
                self.axes['force_x'].set_title('Fuerza X vs Tiempo')
                self.axes['force_x'].set_ylabel('Fuerza X (N)')
                self.axes['force_x'].grid(True)
            
            if 'force_y' in self.axes:
                self.axes['force_y'].clear()
                self.axes['force_y'].plot(times, forces_y, 'g-')
                self.axes['force_y'].set_title('Fuerza Y vs Tiempo')
                self.axes['force_y'].set_ylabel('Fuerza Y (N)')
                self.axes['force_y'].grid(True)
            
            if 'force_z' in self.axes:
                self.axes['force_z'].clear()
                self.axes['force_z'].plot(times, forces_z, 'b-')
                self.axes['force_z'].set_title('Fuerza Z vs Tiempo')
                self.axes['force_z'].set_ylabel('Fuerza Z (N)')
                self.axes['force_z'].grid(True)
            
            if 'force_magnitude' in self.axes:
                self.axes['force_magnitude'].clear()
                self.axes['force_magnitude'].plot(times, magnitudes, 'k-', linewidth=2)
                self.axes['force_magnitude'].set_title('Magnitud de Fuerza Total')
                self.axes['force_magnitude'].set_ylabel('|F| (N)')
                self.axes['force_magnitude'].grid(True)
    
    def create_animation(self, interval: int = 50) -> animation.FuncAnimation:
        """Crea animación en tiempo real.
        
        Args:
            interval: Intervalo de actualización en ms
            
        Returns:
            Objeto de animación de matplotlib
        """
        def animate(frame):
            if self.real_time_plots:
                self._update_force_plots()
            return []
        
        if self.fig_forces:
            anim = animation.FuncAnimation(self.fig_forces, animate, 
                                         interval=interval, blit=False)
            self.animations.append(anim)
            return anim
        
        return None
    
    def start_real_time_update(self):
        """Inicia actualización en tiempo real en hilo separado."""
        if not self.running:
            self.running = True
            self.update_thread = threading.Thread(target=self._update_worker)
            self.update_thread.daemon = True
            self.update_thread.start()
    
    def stop_real_time_update(self):
        """Detiene la actualización en tiempo real."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
    
    def _update_worker(self):
        """Worker thread para actualización en tiempo real."""
        update_interval = 1.0 / self.update_frequency
        
        while self.running:
            try:
                if self.real_time_plots:
                    self._update_force_plots()
                    
                    # Actualizar figuras
                    if self.fig_forces:
                        self.fig_forces.canvas.draw_idle()
                        self.fig_forces.canvas.flush_events()
                    if self.fig_2d:
                        self.fig_2d.canvas.draw_idle()
                        self.fig_2d.canvas.flush_events()
                    if self.fig_3d:
                        self.fig_3d.canvas.draw_idle()
                        self.fig_3d.canvas.flush_events()
                
                time.sleep(update_interval)
                
            except Exception as e:
                print(f"Error en actualización de visualización: {e}")
                time.sleep(1)
    
    def save_plots(self, output_dir: str = "data/processed"):
        """Guarda las gráficas actuales.
        
        Args:
            output_dir: Directorio de salida
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.fig_2d:
            self.fig_2d.savefig(f"{output_dir}/gantry_2d_{timestamp}.png", 
                               dpi=300, bbox_inches='tight')
        
        if self.fig_3d:
            self.fig_3d.savefig(f"{output_dir}/gantry_3d_{timestamp}.png", 
                               dpi=300, bbox_inches='tight')
        
        if self.fig_forces:
            self.fig_forces.savefig(f"{output_dir}/forces_{timestamp}.png", 
                                   dpi=300, bbox_inches='tight')
    
    def show_all(self):
        """Muestra todas las ventanas de visualización."""
        # Mostrar todas las figuras de forma no bloqueante
        if self.fig_2d:
            self.fig_2d.show()
        if self.fig_3d:
            self.fig_3d.show()
        if self.fig_forces:
            self.fig_forces.show()
        
        # Forzar actualización de la interfaz
        plt.pause(0.001)
    
    def close_all(self):
        """Cierra todas las ventanas y detiene animaciones."""
        self.stop_real_time_update()
        
        for anim in self.animations:
            anim.event_source.stop()
        
        plt.close('all')