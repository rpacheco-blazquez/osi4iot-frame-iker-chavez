# Carpeta `gid2json/` - Convertidor de Archivos GiD a JSON

## Propósito Principal

La carpeta `gid2json/` contiene un **convertidor** desarrollado en **Node.js** que transforma archivos de resultados de simulaciones de elementos finitos (formato GiD) al formato JSON. Este módulo permite que los resultados de simulaciones de elementos finitos puedan ser visualizados en navegadores web.

## Estructura de Archivos

```
gid2json/
├── .gitignore              
├── index.js                # Archivo principal del convertidor 
├── package.json            # Configuración del proyecto Node.js
├── package-lock.json       
├── yarn.lock              
└── projects/               # Directorio para proyectos de simulación
    └── .gitignore          # Ignora todos los archivos del directorio
```

## Funcionalidades Principales

### 1. Conversión de Archivos GiD

El convertidor procesa dos tipos de archivos generados por GiD:
- **`.post.msh`**: Archivos de malla de elementos finitos (geometría, nodos, elementos)
- **`.post.res`**: Archivos de resultados de simulación (desplazamientos, tensiones, etc.)

### 2. Tipos de Resultados Soportados

El sistema puede manejar múltiples tipos de resultados de simulaciones de elementos finitos:

| Tipo de Resultado | Componentes | Descripción |
|-------------------|-------------|-------------|
| `Displacements` | 3 | Desplazamientos en X, Y, Z |
| `Shells//Stresses_Top` | 6 | Tensiones en la cara superior |
| `Shells//Stresses_Bottom` | 6 | Tensiones en la cara inferior |
| `Shells//Equivalent_stresses//Von_Mises` | 1 | Tensiones equivalentes de Von Mises |
| `Shells//Main_stresses` | 1 | Tensiones principales (Si, Sii, Siii) |
| `Axial_Force` | 4 | Fuerzas axiales |
| `Temperature` | 1 | Campo de temperaturas |

### 3. Modo Interactivo

El convertidor incluye un modo interactivo (`--pre-read-results`) que:
- Escanea automáticamente todos los resultados disponibles en el archivo **`.post.res`**.
- Presenta un menú interactivo para seleccionar qué resultados se quieren convertir.
- Guarda la configuración seleccionada en *`{nombre}_res.json`*.

### 4. Procesamiento de Mallas

El sistema procesa la geometría de la malla de elementos finitos:
- Convierte elementos triangulares de la malla.
- Organiza nodos y sus coordenadas espaciales.
- Gestiona las conectividades entre elementos de la malla.


## Dependencias Técnicas

El proyecto utiliza las siguientes dependencias de Node.js:

```json
{
  "n-readlines": "^1.0.1",    // Lectura eficiente de archivos grandes línea por línea
  "merge-files": "^0.1.2",    // Fusión de múltiples archivos
  "process": "^0.11.10",      // Manejo de procesos del sistema
  "three": "^0.136.0"         // Biblioteca 3D para visualización web
}
```

## Uso del Convertidor

### Sintaxis Básica
```bash
node index.js ruta/al/proyecto.gid [opciones]
```

### Opciones Disponibles

- `--pre-read-results`: Activa el modo interactivo para seleccionar los resultados a convertir.
- `--results-of-interest [lista]`: Especifica los resultados específicos a convertir.
- `--reverse-field [campos]`: Invierte la dirección de campos específicos.
- `--min-threshold-field [campo] [valor]`: Aplica umbral mínimo.
- `--max-threshold-field [campo] [valor]`: Aplica umbral máximo.

### Ejemplo de Uso
```bash
# Modo interactivo
node index.js ./mi_proyecto.gid --pre-read-results

# Conversión directa con resultados específicos
node index.js ./mi_proyecto.gid --results-of-interest "Displacements,Stresses_Top"
```

## Archivos de Salida

El convertidor genera tres tipos de archivos JSON:

### 1. `{nombre}_mesh.json`
Contiene la geometría de la malla:
```json
{
  "meshes": [
    {
      "name": "Triangles_mesh_1",
      "nodes": {
        "itemSize": 3,
        "array": [x1, y1, z1, x2, y2, z2, ...]
      },
      "elements": {
        "itemSize": 3,
        "array": [n1, n2, n3, n4, n5, n6, ...]
      }
    }
  ]
}
```

### 2. `{nombre}_res.json`
Contiene los resultados de simulación organizados por modos:
```json
{
  "meshResults": [
    {
      "resultFields": {
        "Displacements": {
          "modalValues": {
            "Mode_1": {
              "itemSize": 3,
              "array": [dx1, dy1, dz1, dx2, dy2, dz2, ...]
            }
          }
        }
      }
    }
  ]
}
```

### 3. `{nombre}_config.json`
Guarda la configuración utilizada:
```json
{
  "resultsOfInterest": ["Displacements", "Stresses_Top"],
  "dictCompOfInterest": {
    "Displacements": 3,
    "Stresses_Top": 6
  },
  "generatedAt": "2024-01-15T10:30:00.000Z"
}
```

## Integración en el Proyecto OSI4IoT

### Rol en el Pipeline de Visualización




---

