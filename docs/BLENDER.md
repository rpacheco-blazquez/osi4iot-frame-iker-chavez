# Addon Load_FEM_meshes para Blender

## 1. Descripción General del Addon

### Información Básica
- **Nombre**: Load_FEM_meshes
- **Autor**: Daniel Di Capua
- **Categoría**: Object
- **Licencia**: Proyecto OSI4IoT

### Funcionalidades Principales

El addon **`load_fem_meshes.py`** es una herramienta diseñada para importar y visualizar mallas de elementos finitos en **Blender**. Este addon permite:

#### Características Clave:

1. **Importación de Archivos JSON**: 
   - Carga archivos JSON que contienen datos de mallas FEM.
   - Compatible con el formato generado por el convertidor **gid2json**.

2. **Creación Automática de Colecciones**:
   - Organiza automáticamente los objetos FEM en colecciones específicas
   - Mantiene la estructura jerárquica del modelo

3. **Procesamiento de Geometría**:
   - Convierte datos de nodos y elementos en mallas de Blender
   - Soporta elementos triangulares
   - Preserva la topología original del modelo FEM

4. **Integración con la Interfaz**:
   - Se integra seamlessly en el menú Object de Blender
   - Utiliza el sistema nativo de selección de archivos
   - Interfaz intuitiva y familiar para usuarios de Blender

### Propósito en el Proyecto OSI4IoT

Este addon forma parte del pipeline de visualización del proyecto OSI4IoT, permitiendo:
- Visualización 3D de resultados de simulaciones estructurales
- Inspección visual de mallas de elementos finitos
- Verificación de geometría y conectividades
- Generación de renders de alta calidad para presentaciones

## 2. Requisitos del Sistema

### Versión de Blender Compatible
- **Versión Mínima**: Blender 2.93.7 o superior


### Requisitos del Sistema

#### Requisitos Mínimos:
- **Sistema Operativo**: Windows 10/11, macOS 10.15+, Linux Ubuntu 18.04+
- **RAM**: 4 GB mínimo (8 GB recomendado)
- **Espacio en Disco**: 50 MB para el addon + espacio para archivos JSON
- **Python**: Incluido con Blender (no requiere instalación separada)

#### Requisitos Recomendados:
- **RAM**: 16 GB o más para modelos grandes
- **GPU**: Tarjeta gráfica dedicada para mejor rendimiento de viewport
- **CPU**: Procesador multi-core para procesamiento eficiente

### Dependencias
- **Módulos Python**: json, os, pathlib (incluidos en Blender)
- **Módulos Blender**: bpy, bpy_extras (nativos de Blender)

## 3. Instrucciones de Instalación

### Instalación Manual 

#### Paso 1: Descargar el Addon
```bash
# Navegar a la carpeta blender_addons del directorio del proyecto
cd blender/blender_addons/

# El archivo load_fem_meshes.py está listo para usar
```

#### Paso 2: Instalar en Blender
1. **Abrir Blender**
2. **Ir a Preferences**:
   - Menú: `Edit > Preferences` (Windows/Linux)
   - Menú: `Blender > Preferences` (macOS)
3. **Navegar a Add-ons**:
   - Clic en la pestaña "Add-ons" en el panel izquierdo
4. **Instalar Addon**:
   - Clic en "Install..." en la parte superior derecha
   - Navegar a la ubicación del archivo `load_fem_meshes.py`
   - Seleccionar el archivo y hacer clic en "Install Add-on"
5. **Activar el Addon**:
   - Buscar "Load_FEM_meshes" en la lista de addons
   - Marcar la casilla para activarlo
   - El addon aparecerá en la categoría "Object"

#### Paso 3: Importar malla FEM a Blender
1. **Ir a `Object > Load FEM meshes`**
2. En la ventana **Blender File View** seleccionar el archivo `{nombre}_mesh.json` generado por el convertidor **gid2json**.
3. Hacer clic en **`Load FEM meshes`** para importar la malla.


---

*Este addon es parte del ecosistema OSI4IoT y está diseñado específicamente para trabajar con datos de elementos finitos generados por el pipeline gid2json del proyecto.*
