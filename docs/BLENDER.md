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

## 6. Solución de Problemas Comunes

### Problema 1: Addon No Aparece en el Menú

**Síntomas**:
- El addon está instalado pero no aparece en Object menu
- Error en la consola de Blender

**Soluciones**:
1. **Verificar Activación**:
   - Ir a Preferences > Add-ons
   - Buscar "Load_FEM_meshes"
   - Asegurar que esté marcado

2. **Reiniciar Blender**:
   - Cerrar completamente Blender
   - Abrir nuevamente

3. **Verificar Versión de Blender**:
   ```python
   import bpy
   print(bpy.app.version)  # Debe ser >= (2, 93, 7)
   ```

### Problema 2: Error al Cargar Archivo JSON

**Síntomas**:
```
Traceback (most recent call last):
  File "load_fem_meshes.py", line 23, in execute
    meshData = json.load(json_file)
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Soluciones**:
1. **Verificar Formato JSON**:
   ```bash
   # Validar JSON
   python -m json.tool archivo_mesh.json
   ```

2. **Verificar Estructura Esperada**:
   ```json
   {
     "meshes": [
       {
         "name": "string",
         "nodes": {
           "itemSize": number,
           "array": [numbers...]
         },
         "elements": {
           "itemSize": number,
           "array": [numbers...]
         }
       }
     ]
   }
   ```

3. **Regenerar Archivo JSON**:
   ```bash
   # Usar gid2json para regenerar
   node gid2json/index.js proyecto.gid --pre-read-results
   ```

### Problema 3: Geometría No Visible

**Síntomas**:
- El addon ejecuta sin errores
- Los objetos aparecen en Outliner
- No hay geometría visible en viewport

**Soluciones**:
1. **Verificar Escala**:
   - Presionar `Numpad .` para enfocar objetos seleccionados
   - Verificar que la geometría no esté muy pequeña o grande

2. **Verificar Capas/Colecciones**:
   - Asegurar que la colección "FEM simulation objects" esté visible
   - Verificar iconos de ojo en Outliner

3. **Verificar Datos de Nodos**:
   ```python
   # Verificar en consola de Python
   obj = bpy.context.selected_objects[0]
   print(f"Vertices: {len(obj.data.vertices)}")
   print(f"Faces: {len(obj.data.polygons)}")
   ```

### Problema 4: Rendimiento Lento

**Síntomas**:
- Importación muy lenta
- Blender se congela durante la importación
- Viewport lag después de importación

**Soluciones**:
1. **Optimizar Archivo JSON**:
   - Reducir precisión de coordenadas si es posible
   - Usar gid2json con filtros específicos

2. **Configurar Viewport**:
   ```python
   # Reducir calidad de viewport para modelos grandes
   for area in bpy.context.screen.areas:
       if area.type == 'VIEW_3D':
           for space in area.spaces:
               if space.type == 'VIEW_3D':
                   space.shading.type = 'WIREFRAME'
   ```

3. **Procesar en Lotes**:
   - Dividir modelos grandes en múltiples archivos
   - Importar secciones por separado

### Problema 5: Errores de Memoria

**Síntomas**:
```
MemoryError: Unable to allocate array
```

**Soluciones**:
1. **Aumentar RAM Disponible**:
   - Cerrar otras aplicaciones
   - Usar máquina con más RAM

2. **Optimizar Datos**:
   ```bash
   # Usar filtros en gid2json
   node index.js proyecto.gid --results-of-interest "Displacements"
   ```

3. **Procesamiento Incremental**:
   - Dividir el modelo en partes más pequeñas
   - Procesar elementos por grupos

## 7. Información de Contacto para Soporte

### Desarrollador Principal
- **Nombre**: Daniel Di Capua
- **Proyecto**: OSI4IoT Frame
- **Institución**: CIMNE (Centro Internacional de Métodos Numéricos en Ingeniería)

### Canales de Soporte

#### Soporte Técnico del Proyecto
- **Repositorio**: Proyecto OSI4IoT-Frame
- **Ubicación**: `/c:/Users/ikerc/Documents/CIMNE/osi4iot-frame-iker-chavez/`
- **Documentación**: Carpeta `docs/` del proyecto

#### Recursos Adicionales

1. **Documentación Relacionada**:
   - `GID2JSON.md`: Información sobre el convertidor de archivos
   - `POSTPROCESS.md`: Documentación de post-procesamiento
   - `VISION.md`: Información sobre el sistema de visión

2. **Archivos de Ejemplo**:
   - `blender/Portico_biempotrado_YOLO.glb`: Modelo de ejemplo
   - `gid2json/projects/`: Directorio para proyectos de prueba

3. **Logs y Debugging**:
   - Consola de Blender: `Window > Toggle System Console`
   - Logs del proyecto: `data/logs/`

#### Reportar Problemas

Cuando reportes un problema, incluye:

1. **Información del Sistema**:
   ```python
   import bpy
   import sys
   print(f"Blender: {bpy.app.version_string}")
   print(f"Python: {sys.version}")
   print(f"Platform: {sys.platform}")
   ```

2. **Información del Archivo**:
   - Tamaño del archivo JSON
   - Número de nodos y elementos
   - Origen del archivo (qué software generó el .gid)

3. **Mensaje de Error Completo**:
   - Copiar el traceback completo de la consola
   - Incluir pasos para reproducir el error

4. **Archivos de Prueba**:
   - Si es posible, proporcionar un archivo JSON pequeño que reproduzca el problema
   - Incluir el archivo .gid original si está disponible

### Contribuciones y Mejoras

Para contribuir al desarrollo del addon:

1. **Código Fuente**: Ubicado en `blender/blender_addons/load_fem_meshes.py`
2. **Estilo de Código**: Seguir PEP 8 para Python
3. **Testing**: Probar con diferentes tipos de archivos JSON
4. **Documentación**: Actualizar esta documentación con nuevas funcionalidades

---

**Última Actualización**: Diciembre 2024  
**Versión del Documento**: 1.0  
**Compatibilidad**: Blender 2.93.7+

*Este addon es parte del ecosistema OSI4IoT y está diseñado específicamente para trabajar con datos de elementos finitos generados por el pipeline gid2json del proyecto.*