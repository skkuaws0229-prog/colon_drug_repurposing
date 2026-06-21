from __future__ import annotations

import re


CANONICAL_DISEASES: tuple[str, ...] = (
    "BRCA",
    "COAD",
    "LUAD",
    "LIHC",
    "STAD",
    "PAAD",
    "HNSC",
    "PAH",
    "IPF",
    "RA",
    "PSORIASIS",
)

DISEASE_ALIASES: dict[str, tuple[str, ...]] = {
    "BRCA": (
        "BRCA",
        "BRAC",
        "BREAST",
        "Breast invasive carcinoma",
        "Breast cancer",
    ),
    "COAD": (
        "COAD",
        "COLON",
        "CRC",
        "COLORECTAL",
        "COLORECTAL CANCER",
        "COLON ADENOCARCINOMA",
    ),
    "LUAD": (
        "LUAD",
        "LUNG",
        "Lung adenocarcinoma",
    ),
    "LIHC": (
        "LIHC",
        "Liver",
        "HCC",
        "HEPATOCELLULAR",
        "Hepatocellular carcinoma",
    ),
    "STAD": (
        "STAD",
        "Gastric",
        "STOMACH",
        "Stomach adenocarcinoma",
    ),
    "PAAD": (
        "PAAD",
        "PDAC",
        "PANCREATIC",
        "Pancreatic adenocarcinoma",
    ),
    "HNSC": (
        "HNSC",
        "HEADNECK",
        "HEAD_AND_NECK",
        "Head and neck squamous cell carcinoma",
    ),
    "PAH": (
        "PAH",
        "Pulmonary arterial hypertension",
        "PULMONARY ARTERIAL HYPERTENSION",
    ),
    "IPF": (
        "IPF",
        "Idiopathic pulmonary fibrosis",
        "IDIOPATHIC PULMONARY FIBROSIS",
    ),
    "RA": (
        "RA",
        "Rheumatoid arthritis",
        "RHEUMATOID ARTHRITIS",
    ),
    "PSORIASIS": (
        "PSORIASIS",
        "Psoriasis",
    ),
}

DB_SOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "BRCA": ("BRAC",),
    "COAD": ("COLON", "CRC", "COLORECTAL"),
    "LUAD": ("LUNG",),
    "LIHC": ("LIVER",),
    "STAD": ("GASTRIC", "STOMACH"),
    "PAAD": ("PDAC",),
    "HNSC": (),
    "PAH": (),
    "IPF": (),
    "RA": (),
    "PSORIASIS": (),
}

_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")


def _normalize_key(value: str) -> str:
    cleaned = _NON_ALNUM_RE.sub(" ", value.upper()).strip()
    return " ".join(cleaned.split())


_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical in CANONICAL_DISEASES:
    _ALIAS_TO_CANONICAL[_normalize_key(canonical)] = canonical
    for alias in DISEASE_ALIASES.get(canonical, ()):
        _ALIAS_TO_CANONICAL[_normalize_key(alias)] = canonical
    for db_alias in DB_SOURCE_ALIASES.get(canonical, ()):
        _ALIAS_TO_CANONICAL[_normalize_key(db_alias)] = canonical


def normalize_disease_code(input_code: str) -> str:
    key = _normalize_key((input_code or "").strip())
    canonical = _ALIAS_TO_CANONICAL.get(key)
    if canonical:
        return canonical
    supported = ", ".join(CANONICAL_DISEASES)
    raise ValueError(f"Unsupported disease '{input_code}'. Supported values: {supported}")


def normalize_disease(input_code: str) -> str:
    return normalize_disease_code(input_code)


def get_disease_aliases(input_code: str) -> list[str]:
    canonical = normalize_disease_code(input_code)
    values = [canonical, *DISEASE_ALIASES.get(canonical, ()), *DB_SOURCE_ALIASES.get(canonical, ())]
    seen: set[str] = set()
    aliases: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            aliases.append(value)
    return aliases


def get_disease_query_values(input_code: str) -> list[str]:
    aliases = get_disease_aliases(input_code)
    upper_values = [v.upper() for v in aliases]
    return sorted(set(upper_values))


def list_supported_diseases() -> list[str]:
    return list(CANONICAL_DISEASES)
