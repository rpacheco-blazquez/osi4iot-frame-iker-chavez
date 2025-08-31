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

## 4. Guía de Uso con Ejemplos Prácticos

### Preparación de Datos

Antes de usar el addon, se necesita tener el archivo JSON de la malla FEM:

```bash
# Convertir archivos GiD a JSON usando gid2json
cd gid2json

node index.js ../ruta/al/proyecto.gid --pre-read-results
```

Esto generará archivos como:
- `proyecto_mesh.json` (geometría de la malla).
- `proyecto_res.json` (resultados de la simulación de elemetons finitos).

### Uso Básico del Addon

#### Paso 1: Preparar la Escena
1. **Abrir Blender** con una escena nueva
2. **Eliminar objetos por defecto**:
   - Seleccionar cubo, luz, cámara
   - Presionar `Delete` o `X > Delete`

#### Paso 2: Importar Malla FEM
1. **Acceder al Importador**:
   - Ir a `Object > Load FEM meshes`
   - O usar el atajo del menú Add (`Shift + A > Object > Load FEM meshes`)

2. **Seleccionar Archivo**:
   - Se abrirá el navegador de archivos de Blender
   - Navegar a la ubicación de tu archivo `*_mesh.json`
   - Seleccionar el archivo y hacer clic en "Load FEM meshes"

#### Paso 3: Verificar Importación
Después de la importación exitosa:
- Se creará una nueva colección llamada "FEM simulation objects"
- Los objetos de malla aparecerán en el Outliner
- La geometría será visible en el 3D Viewport

### Ejemplo Práctico: Importar Pórtico Estructural

#### Escenario:
Importar un modelo de pórtico biempotrado para análisis visual.

```json
// Ejemplo de estructura de archivo JSON esperado
{
  "meshes": [
    {
      "name": "Triangles_mesh_1",
      "nodes": {
        "itemSize": 3,
        "array": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, ...]
      },
      "elements": {
        "itemSize": 3,
        "array": [1, 2, 3, 2, 4, 3, ...]
      }
    }
  ]
}
```

#### Pasos:
1. **Preparar archivo JSON** usando gid2json
2. **Importar en Blender**:
   - `Object > Load FEM meshes`
   - Seleccionar `portico_mesh.json`
3. **Resultado esperado**:
   - Colección "FEM simulation objects" creada
   - Objeto "Triangles_mesh_1" visible
   - Geometría triangular del pórtico

### Flujo de Trabajo Avanzado

#### 1. Importación Múltiple
```python
# Para importar múltiples archivos (script personalizado)
import bpy

files_to_import = [
    "modelo1_mesh.json",
    "modelo2_mesh.json",
    "modelo3_mesh.json"
]

for file in files_to_import:
    bpy.ops.object.load_fem_meshes('INVOKE_DEFAULT', filepath=file)
```

#### 2. Post-procesamiento
Después de importar:
1. **Aplicar Materiales**:
   ```python
   # Crear material para visualización FEM
   mat = bpy.data.materials.new(name="FEM_Material")
   mat.use_nodes = True
   mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.8, 0.2, 0.2, 1.0)
   
   # Aplicar a objetos FEM
   for obj in bpy.data.collections["FEM simulation objects"].objects:
       obj.data.materials.append(mat)
   ```

2. **Configurar Vista**:
   - Cambiar a modo Wireframe: `Z > 2`
   - Ajustar sombreado: `Z > 6` (Material Preview)
   - Configurar cámara para vista óptima

#### 3. Análisis Visual
- **Inspeccionar Conectividades**: Usar modo Edit (`Tab`) para verificar topología
- **Verificar Geometría**: Buscar elementos degenerados o mal conectados
- **Comparar Modelos**: Importar múltiples versiones para análisis comparativo

### Casos de Uso Específicos

#### Caso 1: Verificación de Malla
```python
# Script para verificar calidad de malla después de importación
import bmesh

for obj in bpy.data.collections["FEM simulation objects"].objects:
    if obj.type == 'MESH':
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        # Verificar elementos degenerados
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
        
        # Actualizar malla
        bm.to_mesh(obj.data)
        bm.free()
```

#### Caso 2: Exportación para Presentación
1. **Configurar Iluminación**:
   - Añadir luces HDRI para iluminación realista
   - Configurar world shader

2. **Renderizar**:
   - Configurar cámara
   - Ajustar parámetros de render
   - Generar imágenes de alta calidad

## 5. Capturas de Pantalla Ilustrativas

### Interfaz del Addon
```
[Captura de pantalla del menú Object mostrando "Load FEM meshes"]
Ubicación: Object > Load FEM meshes
```

### Navegador de Archivos
```
[Captura del file browser con archivos JSON seleccionados]
Formatos soportados: *.json
```

### Resultado de Importación
```
[Vista del 3D Viewport con malla FEM importada]
- Colección "FEM simulation objects" en Outliner
- Geometría triangular visible
- Propiedades del objeto mostrando type="femObject"
```

### Outliner con Objetos FEM
```
[Captura del Outliner mostrando la jerarquía]
├── Scene Collection
│   └── FEM simulation objects
│       ├── Triangles_mesh_1
│       ├── Triangles_mesh_2
│       └── ...
```



---

*Este addon es parte del ecosistema OSI4IoT y está diseñado específicamente para trabajar con datos de elementos finitos generados por el pipeline gid2json del proyecto.*
