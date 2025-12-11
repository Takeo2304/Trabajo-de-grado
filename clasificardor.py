import re
import pandas as pd
import numpy as np
import logging
from tqdm.auto import tqdm
import torch
from transformers import pipeline
from geotext import GeoText
from sentence_transformers import SentenceTransformer, util

# --------------------------
# CONFIG & LOGGING
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hpylori_rev")

DEVICE = 0 if torch.cuda.is_available() else -1

#MODELO
ZS_MODEL = "facebook/bart-large-mnli"
NER_MODEL = "dslim/bert-base-NER"
EMBED_MODEL = "all-MiniLM-L6-v2"


# ==========================================================
#  LIMPIEZA BÁSICA
# ==========================================================
def limpiar(text):
    return "" if not isinstance(text, str) else re.sub(r"\s+", " ", text).strip().lower()


# ==========================================================
#  PALABRAS PROHIBIDAS
# ==========================================================
EXCLUSION_TERMS = [
    "review", "systematic review","revisión sistemática", "meta-analysis",
    "meta análisis", "niño", "child", "children", "adolescente"
]

def excluir_palabras(text):
    t = text.lower()
    return any(p in t for p in EXCLUSION_TERMS)


# ==========================================================
#  GELOCALIZACIÓN
# ==========================================================
GENTILICIOS_AMERICA = {
    "Argentina": ["argentinian", "argentinians", "argentino", "argentina", "argentinos"],
    "Bolivia": ["bolivian", "bolivians", "boliviano", "boliviana", "bolivianos"],
    "Brazil": ["brazilian", "brazilians", "brasilero", "brasilera", "brasileño", "brasileños"],
    "Chile": ["chilean", "chileans", "chileno", "chilena", "chilenos"],
    "Colombia": ["colombian", "colombians", "colombiano", "colombiana", "colombianos"],
    "Ecuador": ["ecuadorian", "ecuadorians", "ecuatoriano", "ecuatoriana", "ecuatorianos"],
    "Guyana": ["guyanese"],
    "Paraguay": ["paraguayan", "paraguayans", "paraguayo", "paraguaya", "paraguayos"],
    "Peru": ["peruvian", "peruvians", "peruano", "peruana", "peruanos"],
    "Suriname": ["surinamese"],
    "Uruguay": ["uruguayan", "uruguayans", "uruguayo", "uruguaya", "uruguayos"],
    "Venezuela": ["venezuelan", "venezuelans", "venezolano", "venezolana", "venezolanos"],

    "Mexico": ["mexican", "mexicans", "mexicano", "mexicana", "mexicanos"],
    "Guatemala": ["guatemalan", "guatemalans", "guatemalteco", "guatemalteca", "guatemaltecos"],
    "Honduras": ["honduran", "hondurans", "hondureño", "hondureña", "hondureños"],
    "El Salvador": ["salvadoran", "salvadorans", "salvadorean", "salvadorian",
                    "salvadoreño", "salvadoreña", "salvadoreños"],
    "Nicaragua": ["nicaraguan", "nicaraguans", "nicaragüense", "nicaraguenses"],
    "Costa Rica": ["costa rican", "costa ricans", "costarricense", "tico", "tica", "ticos"],
    "Panama": ["panamanian", "panamanians", "panameño", "panameña", "panameños"],
    "Belize": ["belizean", "belizeans"],

    "Cuba": ["cuban", "cubans", "cubano", "cubana", "cubanos"],
    "Dominican Republic": ["dominican", "dominicans", "dominicano", "dominicana", "dominicanos"],
    "Haiti": ["haitian", "haitians", "haitiano"],
    "Jamaica": ["jamaican", "jamaicans"],
    "Puerto Rico": ["puerto rican", "puerto ricans", "puertorriqueño", "boricua", "boricuas"],
    "Trinidad and Tobago": ["trinidadian", "tobagonian"],
    "Barbados": ["barbadian"],
    "Bahamas": ["bahamian"],
    "Grenada": ["grenadian"],
    "Saint Lucia": ["saint lucian"],
    "Saint Vincent and the Grenadines": ["vincentian"],
    "Antigua and Barbuda": ["antiguan", "barbudan"],
    "Dominica": ["dominicant (caribe)"],

    "United States": ["american", "americans", "estadounidense", "norteamericano"],
    "Canada": ["canadian", "canadians"],

    "French Guiana": ["french guianese"],
}
def extraer_pais(text):
    if not isinstance(text, str):
        return ""

    t = text.lower()

    # --- Opción 1: GeoText (si funciona)
    lugares = GeoText(text)
    if lugares.countries:
        return list(lugares.countries)[0]

    # --- Opción 2: país directo por nombre ---
    for country in GENTILICIOS_AMERICA:
        if country.lower() in t:
            return country

    # --- Opción 3: búsqueda por gentilicios ---
    for country, gentilicios in GENTILICIOS_AMERICA.items():
        for g in gentilicios:
            if g.lower() in t:
                return country

    # --- Opción 4: regiones generales ---
    REGIONES = {
        "latin america": "Latin America",
        "south america": "South America",
        "central america": "Central America",
        "north america": "North America",
        "caribbean": "Caribbean"
    }
    for r in REGIONES:
        if r in t:
            return REGIONES[r]

    return ""


# ==========================================================
#  CLASIFICACIÓN DE TEMA (Zero-shot rápido)
# ==========================================================
def classify_topic(df):
    temas = [
        "antibiotic resistance surveillance",
        "antimicrobial susceptibility",
        "molecular mechanism of resistance",
        "genomic resistance",
        "clinical outcome",
        "treatment failure",
        "hpylori prevalence",
        "culture and isolation methods",
        "review",
        "systematic review",
        "revisión sistemática",
        "meta-analysis",
        "meta análisis"
    ]

    zs = pipeline("zero-shot-classification", model=ZS_MODEL, device=DEVICE)

    textos = (df["title_clean"] + " " + df["abstract_clean"]).tolist()

    logger.info("Ejecutando zero-shot optimizado...")

    # ⚡ batch pequeño = más rápido y estable
    results = zs(textos, temas, truncation=True, batch_size=4)

    df["topic"] = [r["labels"][0] for r in results]
    return df


# ==========================================================
#  TAMAÑO MUESTRAL
# ==========================================================
SAMPLE_RE = re.compile(
    r"\b(n\s*=?\s*\d{1,5}|\d{1,5}\s+patients|\d{1,5}\s+samples|\d{1,5}\s+isolates)\b",
    re.I
)

def extract_sample_size(text):
    if not isinstance(text, str):
        return ""
    return "; ".join(SAMPLE_RE.findall(text))


# ==========================================================
#  MÉTODOS DE LABORATORIO
# ==========================================================
METHOD_KEYWORDS = {
    "E-test": ["e-test", "etest"],
    "agar dilution": ["agar dilution"],
    "agar diffusion": ["disk diffusion", "kirby-bauer", "agar diffusion"],
    "broth microdilution": ["broth microdilution", "microdilution"],
    "PCR": ["PCR", "polymerase chain reaction"],
    "culture": ["culture", "cultivation"]
}

def extract_method(text):
    if not isinstance(text, str):
        return ""
    low = text.lower()
    return "; ".join([m for m, kws in METHOD_KEYWORDS.items() if any(k.lower() in low for k in kws)])


# ==========================================================
#  EXTRACCIÓN MIC, % Y ANTIBIÓTICOS
# ==========================================================
PCT_RE = re.compile(r"(\d{1,3}\s?%)")
MIC_RE = re.compile(r"mic\s?\d+(\.\d+)?", re.I)
ANTIBIOTICOS = [
    "clarithromycin", "amoxicillin", "metronidazole",
    "levofloxacin", "tetracycline", "rifabutin"
]

def extract_data(df):
    df["pct_values"] = df["abstract_clean"].str.findall(PCT_RE)
    df["mic_values"] = df["abstract_clean"].str.findall(MIC_RE)
    df["antibiotics"] = df["abstract_clean"].apply(
        lambda x: [ab for ab in ANTIBIOTICOS if ab in x.lower()]
    )
    return df


# ==========================================================
#  PIPELINE PRINCIPAL
# ==========================================================
def main(path_csv):

    df["title_clean"] = df["title"].apply(limpiar)
    df["abstract_clean"] = df["abstract"].apply(limpiar)

    df["texto_total"] = df["title_clean"] + " " + df["abstract_clean"]

# 1. Excluir artículos con palabras no deseadas
    df = df[~df["texto_total"].apply(excluir_palabras)].reset_index(drop=True)

# 2. ELIMINACIÓN DE DUPLICADOS POR TÍTULO EXACTO
    df = df.drop_duplicates(subset=["title_clean"], keep="first").reset_index(drop=True)

# 3. Continuar con el pipeline
    df["country"] = df["texto_total"].apply(extraer_pais)
    df = classify_topic(df)
    df["sample_size"] = df["texto_total"].apply(extract_sample_size)
    df["method_used"] = df["texto_total"].apply(extract_method)
    df = extract_data(df)

    # --------------------------------------
    # Guardado con nombre solicitado
    # --------------------------------------
    output_path = "clasificacion_automatizada.csv"
    df.to_csv(output_path, index=False)

    logger.info(f"Pipeline terminado. Archivo generado: {output_path}")

    return df


# --------------------------
# EJECUCIÓN
# --------------------------
if __name__ == "__main__":
    df_final = main("/content/mineria_con_pmc.csv")
    df_final.head()
