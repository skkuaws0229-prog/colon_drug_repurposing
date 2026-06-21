from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests


PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPE_PMC_FULLTEXT_XML_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower())
    return cleaned.strip("_") or "unknown_drug"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _norm_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _extract_year(pub_date_node: ET.Element | None) -> str:
    if pub_date_node is None:
        return ""
    year = _norm_text(pub_date_node.findtext("Year"))
    if year:
        return year
    medline_date = _norm_text(pub_date_node.findtext("MedlineDate"))
    if medline_date:
        m = re.search(r"(19|20)\d{2}", medline_date)
        if m:
            return m.group(0)
    return ""


def _parse_pubmed_xml(xml_text: str, query: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    out: list[dict[str, Any]] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _norm_text(article.findtext(".//MedlineCitation/PMID"))
        title = _norm_text(article.findtext(".//Article/ArticleTitle"))
        journal = _norm_text(article.findtext(".//Article/Journal/Title"))
        year = _extract_year(article.find(".//Article/Journal/JournalIssue/PubDate"))

        abstract_parts = []
        for abs_node in article.findall(".//Article/Abstract/AbstractText"):
            label = _norm_text(abs_node.attrib.get("Label"))
            content = _norm_text("".join(abs_node.itertext()))
            if not content:
                continue
            if label:
                abstract_parts.append(f"{label}: {content}")
            else:
                abstract_parts.append(content)
        abstract = _norm_text(" ".join(abstract_parts))

        doi = ""
        for id_node in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if _norm_text(id_node.attrib.get("IdType")).lower() == "doi":
                doi = _norm_text(id_node.text)
                break

        out.append(
            {
                "source": "PubMed",
                "query": query,
                "pmid": pmid,
                "pmcid": "",
                "title": title,
                "abstract": abstract,
                "full_text": "",
                "journal": journal,
                "year": year,
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                "is_open_access": False,
            }
        )
    return out


def search_pubmed(
    query: str,
    *,
    retmax: int = 30,
    timeout_sec: int = 30,
    email: str | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(retmax),
        "retmode": "json",
        "sort": "relevance",
    }
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key

    r = requests.get(PUBMED_ESEARCH_URL, params=params, timeout=timeout_sec)
    r.raise_for_status()
    data = r.json()
    id_list = data.get("esearchresult", {}).get("idlist", []) or []
    if not id_list:
        return []

    fetch_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"}
    if email:
        fetch_params["email"] = email
    if api_key:
        fetch_params["api_key"] = api_key
    rf = requests.get(PUBMED_EFETCH_URL, params=fetch_params, timeout=timeout_sec)
    rf.raise_for_status()
    return _parse_pubmed_xml(rf.text, query)


def _extract_full_text_from_xml(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    body = root.find(".//body")
    if body is None:
        return ""
    return _norm_text(" ".join(body.itertext()))


def search_europepmc(
    query: str,
    *,
    page_size: int = 30,
    timeout_sec: int = 30,
    include_open_access_fulltext: bool = True,
) -> list[dict[str, Any]]:
    params = {
        "query": query,
        "format": "json",
        "pageSize": str(page_size),
        "resultType": "core",
    }
    r = requests.get(EUROPE_PMC_SEARCH_URL, params=params, timeout=timeout_sec)
    r.raise_for_status()
    data = r.json()
    results = data.get("resultList", {}).get("result", []) or []

    out: list[dict[str, Any]] = []
    for item in results:
        pmid = _norm_text(item.get("pmid"))
        pmcid = _norm_text(item.get("pmcid"))
        title = _norm_text(item.get("title"))
        abstract = _norm_text(item.get("abstractText"))
        journal = _norm_text(item.get("journalTitle"))
        year = _norm_text(item.get("pubYear"))
        doi = _norm_text(item.get("doi"))
        source_db = _norm_text(item.get("source")) or "EPMC"
        identifier = _norm_text(item.get("id"))
        is_oa = str(item.get("isOpenAccess", "")).upper() == "Y"
        has_text = str(item.get("hasText", "")).upper() == "Y"

        full_text = ""
        if include_open_access_fulltext and is_oa and has_text and pmcid:
            try:
                url = EUROPE_PMC_FULLTEXT_XML_URL.format(pmcid=pmcid)
                fr = requests.get(url, timeout=timeout_sec)
                if fr.status_code == 200:
                    full_text = _extract_full_text_from_xml(fr.text)
                # polite throttle for repeated full text calls
                time.sleep(0.08)
            except requests.RequestException:
                full_text = ""

        article_url = ""
        if source_db and identifier:
            article_url = f"https://europepmc.org/article/{source_db}/{identifier}"
        elif pmid:
            article_url = f"https://europepmc.org/article/MED/{pmid}"

        out.append(
            {
                "source": "EuropePMC",
                "query": query,
                "pmid": pmid,
                "pmcid": pmcid,
                "title": title,
                "abstract": abstract,
                "full_text": full_text,
                "journal": journal,
                "year": year,
                "doi": doi,
                "url": article_url,
                "is_open_access": is_oa,
            }
        )
    return out


def search_clinicaltrials_stub(query: str) -> list[dict[str, Any]]:
    # Optional future extension point: intentionally disabled by default.
    _ = query
    return []


def dedupe_documents(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        pmid = _norm_text(row.get("pmid"))
        doi = _norm_text(row.get("doi")).lower()
        title = _norm_text(row.get("title")).lower()
        key = pmid or doi or title
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def build_search_queries(
    drug_name: str,
    disease_aliases: list[str],
    driver_genes: list[str],
    pathways: list[str] | None = None,
) -> list[str]:
    queries: list[str] = []
    for alias in disease_aliases:
        queries.append(f"\"{drug_name}\" AND \"{alias}\"")
    for gene in driver_genes:
        queries.append(f"\"{drug_name}\" AND \"{gene}\"")
    for pathway in pathways or []:
        if pathway.strip():
            queries.append(f"\"{drug_name}\" AND \"{pathway.strip()}\"")
    queries.extend(
        [
            f"\"{drug_name}\" AND \"IC50\"",
            f"\"{drug_name}\" AND \"drug repurposing\"",
            f"\"{drug_name}\" AND \"cancer\"",
        ]
    )
    return sorted(set(queries))


def run_literature_collection_for_drug(
    *,
    disease: str,
    drug_name: str,
    disease_aliases: list[str],
    driver_genes: list[str],
    pathways: list[str] | None,
    out_root: Path,
    pubmed_retmax: int = 25,
    europepmc_page_size: int = 25,
) -> dict[str, Any]:
    drug_slug = slugify(drug_name)
    raw_dir = out_root / "raw" / disease / drug_slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    pubmed_path = raw_dir / "pubmed_results.jsonl"
    epmc_path = raw_dir / "europepmc_results.jsonl"
    status_path = raw_dir / "collection_status.json"

    pubmed_all: list[dict[str, Any]] = []
    epmc_all: list[dict[str, Any]] = []

    queries = build_search_queries(drug_name, disease_aliases, driver_genes, pathways)
    for query in queries:
        try:
            pubmed_all.extend(search_pubmed(query, retmax=pubmed_retmax))
        except requests.RequestException:
            # Keep collection resilient; record only successful calls.
            pass
        except ET.ParseError:
            pass
        try:
            epmc_all.extend(search_europepmc(query, page_size=europepmc_page_size))
        except requests.RequestException:
            pass

    pubmed_unique = dedupe_documents(pubmed_all)
    epmc_unique = dedupe_documents(epmc_all)

    write_jsonl(pubmed_path, pubmed_unique)
    write_jsonl(epmc_path, epmc_unique)

    total_hits = len(pubmed_unique) + len(epmc_unique)
    status = {
        "disease": disease,
        "drug_name": drug_name,
        "drug_slug": drug_slug,
        "queries": queries,
        "pubmed_count": len(pubmed_unique),
        "europepmc_count": len(epmc_unique),
        "total_count": total_hits,
        "no_evidence": total_hits == 0,
        "source_only": "external_literature",
    }
    ensure_parent(status_path)
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status
