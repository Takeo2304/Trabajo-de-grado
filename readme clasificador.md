# Pipeline de Categorización, Limpieza y Enriquecimiento de Artículos Científicos

### Análisis de resistencia antimicrobiana en *Helicobacter pylori*

Este proyecto implementa un flujo completo para la curación,
clasificación temática y extracción de información estructurada a partir
de artículos científicos previamente recolectados. Se basa en modelos
NLP modernos para zero-shot classification, NER, extracción automática
de métodos, tamaños muestrales, antibióticos, y geolocalización por
gentilicios.

El resultado final se exporta en **clasificacion_automatizada.csv**,
listo para análisis estadístico, NER avanzado, minería de texto o
generación de mapas geoespaciales.

------------------------------------------------------------------------

## Características Principales

-   Limpieza y normalización del texto (título y resumen).
-   Eliminación de estudios no deseados (reviews, meta-análisis,
    estudios pediátricos, etc.).
-   **Eliminación automática de duplicados por título limpio
    (`title_clean`).**
-   Detección de país vía gentilicios y GeoText.
-   Clasificación temática Zero-Shot con modelo
    `facebook/bart-large-mnli`.
-   Extracción automática:
    -   Tamaño muestral (n, patients, isolates).
    -   Métodos de laboratorio (E-test, agar dilution, PCR, etc.).
    -   Valores MIC, porcentajes y antibióticos comunes.
-   Embeddings con `all-MiniLM-L6-v2` para posteriores análisis o
    clustering.

------------------------------------------------------------------------

## Estructura del Proyecto

    project/
    │
    ├── script.py
    ├── mineria_con_pmc.csv
    ├── clasificacion_automatizada.csv
    └── README.md

------------------------------------------------------------------------

## Requisitos

### Dependencias principales

-   pandas\
-   numpy\
-   tqdm\
-   torch\
-   transformers\
-   geotext\
-   sentence-transformers

### Instalación

``` bash
pip install pandas numpy tqdm torch transformers geotext sentence-transformers
```

------------------------------------------------------------------------

## Configuración del Código

### Modelos utilizados

-   `facebook/bart-large-mnli` --- Zero-shot classification
-   `dslim/bert-base-NER` --- Named Entity Recognition
-   `all-MiniLM-L6-v2` --- Embeddings para comparaciones futuras

------------------------------------------------------------------------

## Flujo del Pipeline

El flujo del script es el siguiente:

### **1. Cargar archivo**

Lectura del CSV consolidado obtenido previamente del proceso de minería.

### **2. Limpieza básica**

Normaliza texto, elimina caracteres duplicados, convierte todo a
minúsculas.

### **3. Exclusión de estudios no relevantes**

Filtra: - Reviews\
- Meta-análisis\
- Estudios pediátricos\
- Estudios no clínicos

### **4. Eliminación de duplicados por título**

Se añade esta línea dentro del pipeline:

``` python
df = df.drop_duplicates(subset=["title_clean"], keep="first")
```

Esto garantiza que artículos con títulos idénticos o equivalentes no se
repitan.

### **5. Geolocalización**

Detecta países a partir de: - Gentilicios - GeoText - Regiones (South
America, Caribbean, etc.)

### **6. Clasificación temática Zero-shot**

Predice el tema predominante del artículo basado en el título/resumen.

### **7. Extracciones específicas**

-   Tamaño muestral (expresiones regulares)
-   Métodos de laboratorio
-   MICs y porcentajes
-   Antibióticos reportados

### **8. Guardado del archivo final**

``` python
df.to_csv("clasificacion_automatizada.csv", index=False)
```

------------------------------------------------------------------------

## Ejecución

``` bash
python script.py
```

------------------------------------------------------------------------

## Salida esperada

  --------------------------------------------------------------------------------------------------------------------
  title_clean   abstract_clean   country    topic            sample_size   method_used   pct_values   antibiotics
  ------------- ---------------- ---------- ---------------- ------------- ------------- ------------ ----------------
  normalized    normalized       Colombia   antimicrobial    n=100         E-test        \[45%\]      clarithromycin
  title         abstract                    susceptibility                                            

  --------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## Nuevas Funcionalidades Incluidas

-   Eliminación de duplicados por título limpio.
-   Estandarización de texto para minería posterior.
-   Extracción robusta para análisis clínico y epidemiológico.

------------------------------------------------------------------------

## Contacto

Para soporte o ampliación del pipeline:

Sebastián Roa\
sroa30@uan.edu.co
