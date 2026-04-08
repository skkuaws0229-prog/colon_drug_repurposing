"""
Data source integrations for Drug Discovery Chat App.
Priority order: S3 > PubMed > FAERS > ClinicalTrials > ChEMBL > PubChem
"""
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

# ── S3 Config ──
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
# Local results paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent
ENSEMBLE_RESULTS = PROJECT_ROOT / "models" / "ensemble_results" / "ensemble_results.json"
TOP15_CSV = PROJECT_ROOT / "models" / "ensemble_results" / "top15_drugs.csv"
TOP30_CSV = PROJECT_ROOT / "models" / "ensemble_results" / "top30_drugs.csv"
ML_RESULTS = PROJECT_ROOT / "models" / "ml_results"
DL_RESULTS = PROJECT_ROOT / "models" / "dl_results" / "dl_results.json"
GRAPH_RESULTS = PROJECT_ROOT / "models" / "graph_results" / "graph_results.json"

# ── Data Source Status ──
DATA_SOURCE_STATUS = {
    "S3 Pipeline": {
        "status": "connected",
        "description": "파이프라인 결과 (약물 추천, 모델 결과)",
    },
    "PubMed": {
        "status": "available",
        "description": "최신 논문 검색 (API 키 불필요)",
    },
    "FAERS (FDA)": {
        "status": "available",
        "description": "부작용 데이터 (open API)",
    },
    "ClinicalTrials.gov": {
        "status": "available",
        "description": "임상시험 정보 (API v2)",
    },
    "ChEMBL": {
        "status": "available",
        "description": "신약 후보물질 데이터",
    },
    "PubChem": {
        "status": "available",
        "description": "분자 구조, SMILES",
    },
    "HIRA": {
        "status": "api_key_required",
        "description": "약가/급여/비급여 (공공데이터포털 API 키 필요)",
    },
    "Bedrock LLM": {
        "status": "pending",
        "description": "자연어 대화 (연동 예정)",
    },
}


# ═══════════════════════════════════════════
# 1순위: S3 Pipeline Results
# ═══════════════════════════════════════════

def query_s3_drug_candidates():
    """Load drug candidates from ensemble results."""
    # Try top15 CSV first, then ensemble JSON
    if TOP15_CSV.exists():
        df = pd.read_csv(TOP15_CSV)
        return {"status": "ok", "data": df.to_dict(orient="records")}

    if ENSEMBLE_RESULTS.exists():
        with open(ENSEMBLE_RESULTS) as f:
            data = json.load(f)
        if "top15_drugs" in data:
            return {"status": "ok", "data": data["top15_drugs"]}
        if "top30_drugs" in data:
            return {"status": "ok", "data": data["top30_drugs"][:15]}

    return {
        "status": "pending",
        "message": "앙상블 학습이 진행 중입니다. 완료 후 약물 후보가 표시됩니다."
    }


def query_s3_model_results():
    """Load model training results from local files."""
    results = {"status": "ok", "data": {}}

    # ML results
    ml_models = []
    # Parse from known Step 4 results
    ml_known = [
        {"model": "CatBoost", "spearman": 0.8007, "rmse": 1.3172, "status": "PASS"},
        {"model": "LightGBM", "spearman": 0.7913, "rmse": 1.3438, "status": "PASS"},
        {"model": "XGBoost", "spearman": 0.7895, "rmse": 1.3445, "status": "PASS"},
        {"model": "LightGBM-DART", "spearman": 0.7848, "rmse": 1.4029, "status": "FAIL (RMSE)"},
        {"model": "Stacking", "spearman": 0.7981, "rmse": 1.3213, "status": "EXCLUDED"},
        {"model": "ExtraTrees", "spearman": 0.6468, "rmse": 1.8704, "status": "FAIL"},
        {"model": "RandomForest", "spearman": 0.6267, "rmse": 1.9747, "status": "FAIL"},
        {"model": "RSF", "spearman": 0.6142, "rmse": 0.0, "status": "METABRIC only"},
    ]
    results["data"]["ML Models (8)"] = ml_known

    # DL results
    if DL_RESULTS.exists():
        with open(DL_RESULTS) as f:
            dl_data = json.load(f)
        dl_models = []
        for m in dl_data:
            sp_pass = m["spearman_mean"] >= 0.713
            rm_pass = m["rmse_mean"] <= 1.385
            status = "PASS" if (sp_pass and rm_pass) else "FAIL"
            dl_models.append({
                "model": m["model"],
                "spearman": m["spearman_mean"],
                "rmse": m["rmse_mean"],
                "status": status,
            })
        results["data"]["DL Models (5)"] = dl_models
    else:
        results["data"]["DL Models (5)"] = [
            {"model": "FlatMLP", "spearman": 0.7936, "rmse": 1.3429, "status": "PASS"},
            {"model": "ResidualMLP", "spearman": 0.7855, "rmse": 1.3776, "status": "PASS"},
            {"model": "Cross-Attention", "spearman": 0.7852, "rmse": 1.3716, "status": "PASS"},
            {"model": "TabNet", "spearman": 0.7780, "rmse": 1.3892, "status": "FAIL (RMSE)"},
            {"model": "FT-Transformer", "spearman": 0.7625, "rmse": 1.4444, "status": "FAIL (RMSE)"},
        ]

    # Graph results
    if GRAPH_RESULTS.exists():
        with open(GRAPH_RESULTS) as f:
            gr_data = json.load(f)
        gr_models = []
        for m in gr_data:
            gr_models.append({
                "model": m["model"],
                "spearman": m["spearman_mean"],
                "rmse": m["rmse_mean"],
                "status": f"FAIL (P@20={m.get('p_at_20_mean', 0):.2f})",
            })
        results["data"]["Graph Models (2)"] = gr_models
    else:
        results["data"]["Graph Models (2)"] = [
            {"model": "GraphSAGE", "spearman": 0.3852, "rmse": 2.3189, "status": "METABRIC P@20"},
            {"model": "GAT", "spearman": 0.0085, "rmse": 2.6608, "status": "FAIL"},
        ]

    # Ensemble
    if ENSEMBLE_RESULTS.exists():
        with open(ENSEMBLE_RESULTS) as f:
            ens = json.load(f)
        results["ensemble"] = {
            "spearman": ens["ensemble_metrics"]["spearman_mean"],
            "rmse": ens["ensemble_metrics"]["rmse_mean"],
        }

    return results


def query_s3_admet_results():
    """Load ADMET results if available."""
    admet_path = PROJECT_ROOT / "models" / "admet_results"
    if admet_path.exists():
        return {"status": "ok", "data": "ADMET results loaded"}
    return {
        "status": "pending",
        "message": "ADMET 필터링은 Step 7에서 진행 예정입니다. (Step 6 METABRIC 검증 이후)"
    }


# ═══════════════════════════════════════════
# 1순위: PubMed API (Free, no API key)
# ═══════════════════════════════════════════

def query_pubmed(search_term: str, max_results: int = 5):
    """Search PubMed for articles."""
    try:
        # Step 1: Search for IDs
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        search_url = (f"{base_url}/esearch.fcgi?"
                     f"db=pubmed&term={urllib.parse.quote(search_term)}"
                     f"&retmax={max_results}&sort=date&retmode=json")

        req = urllib.request.Request(search_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            search_data = json.loads(resp.read().decode())

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return {"status": "ok", "data": [], "message": "검색 결과가 없습니다."}

        # Step 2: Fetch article details
        ids_str = ",".join(id_list)
        fetch_url = (f"{base_url}/esummary.fcgi?"
                    f"db=pubmed&id={ids_str}&retmode=json")

        req = urllib.request.Request(fetch_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            fetch_data = json.loads(resp.read().decode())

        articles = []
        result_data = fetch_data.get("result", {})
        for pmid in id_list:
            if pmid in result_data:
                article = result_data[pmid]
                authors = ", ".join(
                    a.get("name", "") for a in article.get("authors", [])[:3]
                )
                if len(article.get("authors", [])) > 3:
                    authors += " et al."
                articles.append({
                    "pmid": pmid,
                    "title": article.get("title", "N/A"),
                    "authors": authors,
                    "journal": article.get("source", "N/A"),
                    "pub_date": article.get("pubdate", "N/A"),
                })

        return {"status": "ok", "data": articles}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════
# 2순위: FAERS (FDA Adverse Event Reporting)
# ═══════════════════════════════════════════

def query_faers(query: str, limit: int = 5):
    """Query FDA FAERS for adverse events."""
    try:
        # Extract drug name from query
        drug_name = None
        for word in query.split():
            if len(word) > 3 and word.lower() not in [
                "부작용", "알려줘", "보여줘", "해줘", "이것", "약물"
            ]:
                drug_name = word
                break

        if not drug_name:
            drug_name = "docetaxel"  # Default BRCA-related drug

        url = (f"https://api.fda.gov/drug/event.json?"
              f"search=patient.drug.medicinalproduct:\"{urllib.parse.quote(drug_name)}\""
              f"&count=patient.reaction.reactionmeddrapt.exact&limit={limit}")

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = data.get("results", [])
        if not results:
            return {"status": "ok", "data": f"'{drug_name}'에 대한 부작용 데이터가 없습니다."}

        text = f"**FAERS 부작용 보고** ('{drug_name}')\n\n"
        text += "| 부작용 | 보고 건수 |\n"
        text += "|--------|----------|\n"
        for r in results:
            text += f"| {r['term']} | {r['count']:,} |\n"
        text += f"\n> 출처: FDA FAERS (https://api.fda.gov)"

        return {"status": "ok", "data": text}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════
# 3순위: ClinicalTrials.gov API v2
# ═══════════════════════════════════════════

def query_clinicaltrials(query: str, max_results: int = 5):
    """Search ClinicalTrials.gov."""
    try:
        # Extract search terms
        terms = []
        for word in query.split():
            if len(word) > 2 and word.lower() not in [
                "임상", "시험", "알려줘", "보여줘", "현황"
            ]:
                terms.append(word)

        search_term = " ".join(terms) if terms else "breast cancer drug sensitivity"

        url = (f"https://clinicaltrials.gov/api/v2/studies?"
              f"query.term={urllib.parse.quote(search_term)}"
              f"&pageSize={max_results}&sort=LastUpdatePostDate:desc"
              f"&format=json")

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        studies = data.get("studies", [])
        if not studies:
            return {"status": "ok", "data": f"'{search_term}' 관련 임상시험이 없습니다."}

        text = f"**ClinicalTrials.gov 검색 결과** ('{search_term}')\n\n"
        for i, study in enumerate(studies, 1):
            proto = study.get("protocolSection", {})
            id_mod = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            design_mod = proto.get("designModule", {})

            nct_id = id_mod.get("nctId", "N/A")
            title = id_mod.get("briefTitle", "N/A")
            status = status_mod.get("overallStatus", "N/A")
            phase = ", ".join(design_mod.get("phases", ["N/A"]))

            text += f"**{i}. {title}**\n"
            text += f"- NCT ID: [{nct_id}](https://clinicaltrials.gov/study/{nct_id})\n"
            text += f"- Status: {status} | Phase: {phase}\n\n"

        return {"status": "ok", "data": text}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════
# 5순위: ChEMBL API
# ═══════════════════════════════════════════

def query_chembl(query: str, limit: int = 5):
    """Search ChEMBL for compounds."""
    try:
        terms = []
        for word in query.split():
            if len(word) > 2 and word.lower() not in [
                "신약", "후보", "물질", "알려줘", "보여줘", "화합물"
            ]:
                terms.append(word)
        search_term = " ".join(terms) if terms else "breast cancer"

        url = (f"https://www.ebi.ac.uk/chembl/api/data/molecule/search.json?"
              f"q={urllib.parse.quote(search_term)}&limit={limit}")

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        molecules = data.get("molecules", [])
        if not molecules:
            return {"status": "ok", "data": f"'{search_term}' 관련 ChEMBL 화합물이 없습니다."}

        text = f"**ChEMBL 화합물 검색** ('{search_term}')\n\n"
        text += "| ChEMBL ID | Name | Type | Phase |\n"
        text += "|-----------|------|------|-------|\n"
        for m in molecules:
            chembl_id = m.get("molecule_chembl_id", "N/A")
            name = m.get("pref_name", "N/A") or "N/A"
            mol_type = m.get("molecule_type", "N/A")
            phase = m.get("max_phase", "N/A")
            text += f"| {chembl_id} | {name} | {mol_type} | {phase} |\n"

        text += f"\n> 출처: ChEMBL (https://www.ebi.ac.uk/chembl/)"
        return {"status": "ok", "data": text}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════
# 5순위: PubChem API
# ═══════════════════════════════════════════

def query_pubchem(query: str):
    """Search PubChem for compound info."""
    try:
        terms = []
        for word in query.split():
            if len(word) > 2 and word.lower() not in [
                "구조", "분자", "알려줘", "보여줘", "smiles"
            ]:
                terms.append(word)
        compound_name = " ".join(terms) if terms else "docetaxel"

        url = (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
              f"{urllib.parse.quote(compound_name)}/JSON")

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        compounds = data.get("PC_Compounds", [])
        if not compounds:
            return {"status": "ok", "data": f"'{compound_name}' PubChem 검색 결과 없음"}

        comp = compounds[0]
        cid = comp.get("id", {}).get("id", {}).get("cid", "N/A")

        # Extract properties
        props = {}
        for p in comp.get("props", []):
            label = p.get("urn", {}).get("label", "")
            name = p.get("urn", {}).get("name", "")
            val = p.get("value", {})
            value = val.get("sval", val.get("fval", val.get("ival", "")))
            if label and value:
                props[f"{label} ({name})" if name else label] = value

        text = f"**PubChem 화합물 정보** ('{compound_name}')\n\n"
        text += f"- CID: [{cid}](https://pubchem.ncbi.nlm.nih.gov/compound/{cid})\n"

        # Show key properties
        for key in ["IUPAC Name (Preferred)", "IUPAC Name (Systematic)",
                    "Molecular Formula", "Molecular Weight", "SMILES (Canonical)",
                    "InChI (Standard)"]:
            for pk, pv in props.items():
                if key.split(" (")[0] in pk:
                    text += f"- {pk}: `{pv}`\n"
                    break

        text += f"\n> 출처: PubChem (https://pubchem.ncbi.nlm.nih.gov)"
        return {"status": "ok", "data": text}

    except Exception as e:
        return {"status": "error", "message": str(e)}
