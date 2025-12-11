import requests
import time
import pandas as pd
from Bio import Entrez

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================

Entrez.email = "+++++@uan.edu.co"  #deposita tu correo como identificador
SCOPUS_API_KEY = "91fd1cc44ec13a1c++++++"  #escribe tu API KEY en este espacio

SCOPUS_HEADERS = {
    "Accept": "application/json",
    "X-ELS-APIKey": SCOPUS_API_KEY
}

# ---- QUERIES ----
PUBMED_QUERY = (
    '"Helicobacter pylori" AND ("Drug Resistance" OR "Drug Resistance, Multiple, Bacterial" '
    'OR "susceptibility test" OR "Drug Resistance, Microbial" OR "Microbial Sensitivity Tests")')
PMC_QUERY = '"Helicobacter pylori" AND susceptibility test OR drug resistance '
SCOPUS_QUERY = '"Helicobacter pylori" AND ("susceptibility test" OR "drug resistance")'
START_YEAR = 2020
END_YEAR = 2025


# ======================================================
# PUBMED
# ======================================================

def extract_pubmed_article(article):
    try:
        med = article["MedlineCitation"]
        art = med["Article"]

        pmid = med.get("PMID", "")
        pmid = str(pmid)

        # DOI desde ArticleIdList
        doi = ""
        ids = art.get("ELocationID", [])
        for item in ids:
            if item.attributes.get("EIdType") == "doi":
                doi = str(item)

        # O buscar DOI en ArticleIdList (cuando existe)
        for id_item in med.get("ArticleIdList", []):
            if id_item.attributes.get("IdType") == "doi":
                doi = str(id_item)

        title = art.get("ArticleTitle", "")

        abstract = ""
        if art.get("Abstract"):
            for part in art["Abstract"]["AbstractText"]:
                abstract += str(part)

        journal = art["Journal"]["Title"]
        year = art["Journal"]["JournalIssue"]["PubDate"].get("Year", "")

        authors = []
        for a in art.get("AuthorList", []):
            if "ForeName" in a and "LastName" in a:
                authors.append(f"{a['ForeName']} {a['LastName']}")

        url = ""
        if pmid:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        elif doi:
            url = f"https://doi.org/{doi}"

        return {
            "id": pmid,
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "year": year,
            "authors": "; ".join(authors),
            "url_fulltext": url,
            "source": "PubMed"
        }

    except Exception as e:
        print("Error PubMed:", e)
        return None

# ======================================================
# EUROPE PMC
# ======================================================

def search_europe_pmc(query, start, end):
    print("Buscando en Europe PMC...")

    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    papers = []
    cursor = "*"

    while True:
        params = {
            "query": f"({query}) AND PUB_YEAR:[{start} TO {end}]",
            "format": "json",
            "pageSize": 1000,
            "cursorMark": cursor
        }

        r = requests.get(base_url, params=params)

        if r.status_code != 200:
            print(" Error Europe PMC:", r.text)
            break

        data = r.json()

        results = data.get("resultList", {}).get("result", [])
        if not results:
            break

        for r in results:
            pmcid = r.get("pmcid", "")
            doi = r.get("doi", "")

            if pmcid:
                url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
            elif doi:
                url = f"https://doi.org/{doi}"
            else:
                url = ""

            papers.append({
                "id": pmcid or doi or f"pmc_{len(papers)}",
                "pmcid": pmcid,
                "doi": doi,
                "title": r.get("title", ""),
                "abstract": r.get("abstractText", ""),
                "journal": r.get("journalTitle", ""),
                "year": r.get("pubYear", ""),
                "authors": r.get("authorString", ""),
                "url_fulltext": url,
                "source": "PMC"
            })

        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break

        cursor = next_cursor

    print(f"✔ PMC total: {len(papers)}")
    return papers



# ======================================================
# SCOPUS
# ======================================================

def scopus_get_full_abstract(eid, api_key):
    """Fallback estable: obtiene abstract completo desde /abstract/eid/{eid}."""
    if not eid:
        return ""
    url = f"https://api.elsevier.com/content/abstract/eid/{eid}"
    headers = {"Accept": "application/json", "X-ELS-APIKey": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return ""
        data = r.json()
        abstract = (
            data.get("abstracts-retrieval-response", {})
                .get("coredata", {})
                .get("dc:description", "")
        )
        return clean_abstract(abstract)
    except Exception:
        return ""


def search_scopus(query, start_year, end_year, api_key, max_results=1000):
    print("🔷 Buscando en Scopus...")
    url = "https://api.elsevier.com/content/search/scopus"
    headers = {"Accept": "application/json", "X-ELS-APIKey": api_key}
    params = {
        "query": f'{query} AND PUBYEAR > {start_year} AND PUBYEAR < {end_year}',
        "count": 25,
        "start": 0,
        "view": "STANDARD"
    }

    all_results = []
    total_retrieved = 0
    page = 0

    while True:
        page += 1
        print(f"[Scopus] Página {page} (start={params['start']})...")
        r = safe_request_get(url, headers=headers, params=params, retries=4)
        if not r:
            print("[Scopus] Request falló (sin respuesta).")
            break

        # manejo explícito de status codes útiles
        if r.status_code in (401, 403):
            print(" Scopus: API key inválida o sin permisos. Status:", r.status_code)
            print(r.text[:400])
            return []
        if r.status_code == 429:
            print(" Scopus: límite de peticiones (429). Esperando 5s...")
            time.sleep(5)
            continue

        try:
            data = r.json()
        except Exception as e:
            print("[Scopus] Error parseando JSON:", e)
            print(r.text[:800])
            break

        entries = data.get("search-results", {}).get("entry", [])
        if not entries:
            # si no hay entries, terminamos
            print("[Scopus] Sin entries en esta página, terminando.")
            break

        for item in entries:
            try:
                eid = item.get("eid", "") or ""
                doi = item.get("prism:doi", "") or ""
                title = item.get("dc:title", "") or ""

                # Preferir dc:description; si está vacío usar fallback /abstract/eid/
                abstract = clean_abstract(item.get("dc:description", ""))
                if not abstract and eid:
                    abstract = scopus_get_full_abstract(eid, api_key)

                year = (item.get("prism:coverDate", "") or "")[:4]
                journal = item.get("prism:publicationName", "") or ""

                authors = []
                for a in item.get("author", []) or []:
                    name = a.get("authname") or a.get("surname") or ""
                    if name:
                        authors.append(name)
                authors_str = "; ".join([a for a in authors if a])

                all_results.append({
                    "id": eid or doi or f"scopus_{len(all_results)}",
                    "title": title,
                    "abstract": abstract,
                    "authors": authors_str,
                    "year": year,
                    "journal": journal,
                    "country": None,
                    "url_fulltext": f"https://doi.org/{doi}" if doi else f"https://www.scopus.com/record/display.uri?eid={eid}",
                    "database": "Scopus"
                })
                total_retrieved += 1
                if total_retrieved >= max_results:
                    print("[Scopus] max_results alcanzado.")
                    print(f"✔ Total Scopus: {len(all_results)}")
                    return all_results

            except Exception as e:
                print("[Scopus] Error procesando artículo:", e)

        # paginación segura usando opensearch fields
        start_index = int(data.get("search-results", {}).get("opensearch:startIndex", 0) or 0)
        per_page = int(data.get("search-results", {}).get("opensearch:itemsPerPage", 25) or 25)
        next_index = start_index + per_page

        # si no avanza, salimos
        if next_index == start_index:
            break

        params["start"] = next_index
        time.sleep(0.3)

    print(f"✔ Total Scopus: {len(all_results)}")
    return all_results

# ======================================================
# MAIN
# ======================================================

pubmed_ids = search_pubmed(PUBMED_QUERY, START_YEAR, END_YEAR)
pubmed_data = fetch_pubmed_details(pubmed_ids)
scopus_data = search_scopus(SCOPUS_QUERY, START_YEAR, END_YEAR, SCOPUS_API_KEY)

pmc_data = search_europe_pmc(PMC_QUERY, START_YEAR, END_YEAR)


# Unión total
all_papers = pubmed_data + pmc_data + scopus_data
df = pd.DataFrame(all_papers)

df.to_csv("busqueda resultados.csv", index=False)

print("\n Terminado. Archivo generado: archivo.csv")
