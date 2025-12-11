# Trabajo-de-grado
Codigo utilizado para la busqueda 
# Sistema Automatizado de Minería de Artículos Científicos

### Resistencia antimicrobiana de Helicobacter pylori (PubMed, PMC y Scopus)

Este proyecto implementa un pipeline automatizado para buscar, descargar
y consolidar artículos científicos relacionados con Helicobacter pylori
y su resistencia antimicrobiana, utilizando tres fuentes principales:

-   PubMed (Entrez API)
-   Europe PMC
-   Scopus (Elsevier API)

El resultado final es un archivo consolidado `resultados_finales.csv`
con metadatos clave: título, autores, DOI, resumen, año, revista y
enlace a texto completo.

------------------------------------------------------------------------

## Características principales

-   Búsqueda automática por rango de años\
-   Extracción de metadatos completos\
-   Limpieza y unificación de resultados\
-   Descarga de abstracts faltantes en Scopus mediante fallback\
-   Manejo robusto de errores\
-   Exportación final lista para análisis, curation y NER

------------------------------------------------------------------------

## Estructura del Proyecto

    project/
    │
    ├── script.py
    ├── resultados_finales.csv
    ├── README.md
    └── requirements.txt

------------------------------------------------------------------------

## Tecnologías utilizadas

-   Python 3.10+
-   Requests
-   Pandas
-   BioPython (Entrez)
-   Europe PMC REST API
-   Scopus Search API + Abstract API

------------------------------------------------------------------------

## Instalación

### Crear entorno virtual

``` bash
python -m venv env
source env/bin/activate   # Linux/macOS
env\Scripts\activate      # Windows
```

### Instalar dependencias

``` bash
pip install requests pandas biopython
```

------------------------------------------------------------------------

## Configuración obligatoria

### Correo para Entrez

``` python
Entrez.email = "TU_EMAIL"
```

### API Key de Scopus

``` python
SCOPUS_API_KEY = "TU_API_KEY"
```

------------------------------------------------------------------------

## Modo de uso

Ejecutar:

``` bash
python script.py
```

------------------------------------------------------------------------

## Flujo del Código

### 1. PubMed

-   Obtiene PMIDs
-   Descarga metadatos
-   Extrae DOI, título, abstract, journal, autores

### 2. Europe PMC

-   Búsqueda con cursor pagination
-   Extrae PMCID, DOI, título, abstract, autores

### 3. Scopus

-   Manejo de errores (401, 403, 429)
-   Descarga abstracts completos vía `/content/abstract/eid/`

### 4. Consolidación

``` python
df = pd.DataFrame(all_papers)
df.to_csv("resultados_finales.csv", index=False)
```

------------------------------------------------------------------------

## Salida esperada

  -----------------------------------------------------------------------------------------------------
  id               title   abstract   journal   year   authors      url_fulltext    source
  ---------------- ------- ---------- --------- ------ ------------ --------------- -------------------
  PMID/PMCID/EID   ...     ...        ...       2023   autores...   enlace          PubMed/PMC/Scopus

  -----------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## Limitaciones conocidas

-   Scopus tiene límites de uso por minuto\
-   Algunos abstracts pueden venir incompletos\
-   PubMed a veces no retorna DOI

------------------------------------------------------------------------

## Contacto

Sebastián Roa\
sroa30@uan.edu.co
