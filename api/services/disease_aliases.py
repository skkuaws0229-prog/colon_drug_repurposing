from __future__ import annotations


CANONICAL_DISEASES = ("BRCA", "COAD", "LUAD", "LIHC", "STAD", "PAAD", "HNSC", "PAH", "IPF", "RA", "PSORIASIS")

DISEASE_ALIASES = {
    "BRCA": [
        "BRCA",
        "brca",
        "BRAC",
        "brac",
        "Breast cancer",
        "breast cancer",
        "Breast invasive carcinoma",
    ],
    "COAD": [
        "COAD",
        "coad",
        "Colon",
        "COLON",
        "Colon adenocarcinoma",
        "CRC",
        "Colorectal",
        "colorectal cancer",
    ],
    "LUAD": [
        "LUAD",
        "luad",
        "LUNG",
        "lung",
        "Lung adenocarcinoma",
        "lung adenocarcinoma",
        "lung cancer",
    ],
    "LIHC": [
        "LIHC",
        "lihc",
        "LIVER",
        "liver",
        "Liver hepatocellular carcinoma",
        "hepatocellular carcinoma",
        "liver cancer",
    ],
    "STAD": [
        "STAD",
        "stad",
        "Stomach adenocarcinoma",
        "gastric cancer",
        "stomach cancer",
    ],
    "PAAD": [
        "PAAD",
        "paad",
        "PDAC",
        "pdac",
        "Pancreatic adenocarcinoma",
        "pancreatic cancer",
    ],
    "HNSC": [
        "HNSC",
        "hnsc",
        "Head and neck squamous cell carcinoma",
        "head and neck cancer",
    ],
    "PAH": [
        "PAH",
        "pah",
        "Pulmonary arterial hypertension",
        "pulmonary arterial hypertension",
    ],
    "IPF": [
        "IPF",
        "ipf",
        "Idiopathic pulmonary fibrosis",
        "idiopathic pulmonary fibrosis",
    ],
    "RA": [
        "RA",
        "ra",
        "Rheumatoid arthritis",
        "rheumatoid arthritis",
    ],
    "PSORIASIS": [
        "PSORIASIS",
        "psoriasis",
    ],
}


def normalize_disease_code(disease: str) -> str:
    raw = (disease or "").strip()
    if not raw:
        raise ValueError(f"Unsupported disease '{disease}'. Use one of: {', '.join(CANONICAL_DISEASES)}")
    upper = raw.upper()
    if upper in CANONICAL_DISEASES:
        return upper
    lower = raw.lower()
    for canonical, aliases in DISEASE_ALIASES.items():
        if lower in {a.lower() for a in aliases}:
            return canonical
    raise ValueError(f"Unsupported disease '{disease}'. Use one of: {', '.join(CANONICAL_DISEASES)}")


def list_supported_diseases() -> list[str]:
    return list(CANONICAL_DISEASES)


def get_disease_aliases(disease: str) -> list[str]:
    canonical = normalize_disease_code(disease)
    aliases = [canonical, *DISEASE_ALIASES.get(canonical, [])]
    seen = set()
    result = []
    for value in aliases:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def get_disease_db_codes(disease: str) -> list[str]:
    canonical = normalize_disease_code(disease)
    if canonical == "BRCA":
        return ["BRCA", "BRAC"]
    if canonical == "LUAD":
        return ["LUAD", "LUNG"]
    if canonical == "LIHC":
        return ["LIHC", "LIVER"]
    if canonical == "PAAD":
        return ["PAAD", "PDAC"]
    return [canonical]
