# BISO Knowledge Graph API 명세서

작성일: 2026-04-09
버전: 1.0.0
Base URL: `http://localhost:8000`

---

## 서버 실행 방법

```bash
cd 20260409_scaleup_biso
conda activate drug4-kg
uvicorn chat.api_server:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

## Neo4j 연결

루트 디렉토리 `.env` 파일에 아래 설정 필요:

```
NEO4J_URI=neo4j+s://108928fe.databases.neo4j.io
NEO4J_USERNAME=108928fe
NEO4J_DATABASE=108928fe
NEO4J_PASSWORD=(별도 전달)
```

## 공통 응답 형식

```json
{
  "status": "success",
  "data": { ... },
  "source": "neo4j | pubmed | ncis",
  "timestamp": "2026-04-09T09:05:33.231629+00:00"
}
```

## KG 현황 (2026-04-09 기준)

| 노드 | 수 | 엣지 | 수 |
|------|------|------|------|
| Drug | 19,844 | TESTED_IN | 89,470 |
| Target | 8,880 | INTERACTS_WITH | 46,882 |
| CellLine | 969 | IN_PATHWAY | 729 |
| Pathway | 686 | HAS_SIDE_EFFECT | 109 |
| Hospital | 97 | TREATS_DISEASE | 97 |
| SideEffect | 46 | ASSOCIATED_WITH | 50 |
| Trial | 35 | TARGETS | 41 |
| Disease | 1 | IN_TRIAL | 39 |
| | | FOR_DISEASE | 35 |
| | | TREATS | 13 |
| **총 노드** | **30,558** | **총 엣지** | **137,465** |

---

## 엔드포인트 목록

### 1. 전체 약물 목록

```
GET /api/drugs
```

**파라미터:**

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `pipeline` | bool | false | `true`: 파이프라인 15개 약물만 |
| `status` | string | - | `BRCA_CURRENT` / `BRCA_RESEARCH` / `BRCA_CANDIDATE` |
| `limit` | int | 100 | 최대 반환 수 (max 20000) |

**요청 예시:**
```
GET /api/drugs?pipeline=true
GET /api/drugs?status=BRCA_CURRENT
GET /api/drugs?pipeline=true&status=BRCA_RESEARCH
```

**응답 예시:**
```json
{
  "status": "success",
  "data": [
    {
      "name": "Vinblastine",
      "brca_status": "BRCA_CURRENT",
      "overall_score": 13.3,
      "safety_score": 7.8,
      "ic50": -2.722,
      "max_phase": "4.0",
      "target": "Microtubule destabiliser",
      "rank": 3
    },
    {
      "name": "Docetaxel",
      "brca_status": "BRCA_CURRENT",
      "overall_score": 12.8,
      "safety_score": 6.8,
      "ic50": -2.811,
      "max_phase": "4.0",
      "target": "Microtubule stabiliser",
      "rank": 5
    }
  ]
}
```

---

### 2. 약물 상세 정보

```
GET /api/drug/{drug_name}
```

**경로 파라미터:**

| 이름 | 설명 |
|------|------|
| `drug_name` | 약물 영문명 (예: `Docetaxel`) |

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 약물명 |
| `ic50` | float | GDSC IC50 (log) |
| `target` | string | 작용 타겟 |
| `brca_status` | string | BRCA_CURRENT / BRCA_RESEARCH / BRCA_CANDIDATE |
| `dili_flag` | bool | 약물유발 간손상 위험 |
| `ames_flag` | bool | Ames 변이원성 |
| `safety_score` | float | 안전성 점수 (0-10) |
| `overall_score` | float | 종합 재창출 점수 |
| `repurposing_evidence` | string | 재창출 근거 |
| `smiles` | string | SMILES 구조식 |
| `molecular_weight` | string | 분자량 |
| `molecular_formula` | string | 분자식 |
| `max_phase` | string | 최대 임상 단계 |
| `ensemble_spearman` | float | 앙상블 모델 Spearman 상관 |
| `pipeline_date` | string | 파이프라인 실행일 |
| `drugbank_id` | string | DrugBank ID |
| `chembl_id` | string | ChEMBL ID |
| `pubchem_cid` | int | PubChem CID |
| `gdsc_id` | int | GDSC ID |
| `rank` | int | 파이프라인 순위 |
| `drug_type` | string | small molecule 등 |
| `oral` | bool | 경구 투여 가능 여부 |
| `insurance_type` | string | 보험 유형 |
| `alogp` | string | ALogP (지질친화도) |
| `disease_code` | string | 질환 코드 |

**응답 예시:**
```json
{
  "status": "success",
  "data": {
    "name": "Docetaxel",
    "ic50": -2.811,
    "target": "Microtubule stabiliser",
    "brca_status": "BRCA_CURRENT",
    "dili_flag": true,
    "ames_flag": false,
    "safety_score": 6.8,
    "overall_score": 12.8,
    "repurposing_evidence": "FDA 유방암 적응증 승인 (보조/전이성). NCCN 표준요법",
    "smiles": "CC(=O)O[C@@]12CO[C@@H]1C...",
    "molecular_weight": "807.8792",
    "molecular_formula": "C43H53NO14",
    "max_phase": "4.0",
    "ensemble_spearman": 0.8055,
    "pipeline_date": "2026-04-08",
    "drugbank_id": "DB01248",
    "chembl_id": "CHEMBL3545252",
    "pubchem_cid": 148124,
    "gdsc_id": 1007,
    "rank": 5,
    "drug_type": "small molecule",
    "oral": false,
    "insurance_type": "해당없음"
  }
}
```

**에러:**
- `404`: Drug not found

---

### 3. 약물 타겟

```
GET /api/drug/{drug_name}/targets
```

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `gene_symbol` | string | 유전자 심볼 |
| `protein_name` | string | 단백질명 |
| `uniprot_id` | string | UniProt ID |
| `function` | string | 기능 설명 |

**응답 예시:**
```json
{
  "status": "success",
  "data": [
    {
      "gene_symbol": "NR1I2",
      "protein_name": null,
      "uniprot_id": "O75469",
      "function": null
    },
    {
      "gene_symbol": "TUBB1",
      "protein_name": null,
      "uniprot_id": "Q9H4B7",
      "function": null
    },
    {
      "gene_symbol": "BCL2",
      "protein_name": null,
      "uniprot_id": "P10415",
      "function": null
    }
  ]
}
```

---

### 4. 약물 부작용

```
GET /api/drug/{drug_name}/side_effects
```

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 부작용명 |
| `meddra_term` | string | MedDRA 표준 용어 |

**응답 예시:**
```json
{
  "status": "success",
  "data": [
    { "name": "NEUTROPENIA", "meddra_term": "NEUTROPENIA" },
    { "name": "NAUSEA", "meddra_term": "NAUSEA" },
    { "name": "ALOPECIA", "meddra_term": "ALOPECIA" },
    { "name": "MADAROSIS", "meddra_term": "MADAROSIS" },
    { "name": "DIARRHOEA", "meddra_term": "DIARRHOEA" },
    { "name": "ANXIETY", "meddra_term": "ANXIETY" }
  ]
}
```

---

### 5. 약물 임상시험

```
GET /api/drug/{drug_name}/trials
```

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `nct_id` | string | ClinicalTrials.gov 등록번호 |
| `title` | string | 임상시험 제목 |
| `phase` | string | PHASE1 / PHASE2 / PHASE3 / PHASE4 |
| `status` | string | RECRUITING / ACTIVE_NOT_RECRUITING / COMPLETED 등 |
| `sponsor` | string | 후원기관 |
| `start_date` | string | 시작일 |
| `completion_date` | string | 종료 예정일 |

**응답 예시:**
```json
{
  "status": "success",
  "data": [
    {
      "nct_id": "NCT06445400",
      "title": "A Study of BL-M07D1, BL-M07D1+Pertuzumab and BL-M07D1+Pertuzumab+Docetaxel in Patients With Unresectable Locally Advanced or Metastatic HER2-positive Breast Cancer",
      "phase": "PHASE2",
      "status": "RECRUITING",
      "sponsor": "Sichuan Baili Pharmaceutical Co., Ltd.",
      "start_date": "2024-06-19",
      "completion_date": "2026-06"
    }
  ]
}
```

---

### 6. 약물 Pathway

```
GET /api/drug/{drug_name}/pathways
```

**경로:** Drug → TARGETS → Target → IN_PATHWAY → Pathway

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `pathway_id` | string | Reactome Pathway ID |
| `name` | string | Pathway 이름 |
| `collection` | string | 컬렉션 분류 |

**응답 예시:**
```json
{
  "status": "success",
  "data": [
    {
      "pathway_id": "R-HSA-109582",
      "name": "Hemostasis",
      "collection": "Reactome"
    }
  ]
}
```

---

### 7. 병원 목록

```
GET /api/hospitals
```

**파라미터:**

| 이름 | 타입 | 설명 |
|------|------|------|
| `region` | string | 지역 필터 (`서울`, `부산`, `인천` 등) |
| `specialty` | string | 전문 분류 필터 (`상급종합병원` 등) |

**요청 예시:**
```
GET /api/hospitals?region=서울
GET /api/hospitals?specialty=상급종합병원
GET /api/hospitals?region=서울&specialty=상급종합병원
```

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 병원명 |
| `address` | string | 주소 |
| `phone` | string | 전화번호 |
| `url` | string | 웹사이트 |
| `region` | string | 지역 (시/도) |
| `specialty` | string | 전문 분류 |
| `category` | string | 의료기관 유형 |
| `district` | string | 구/군 |

**응답 예시:**
```json
{
  "status": "success",
  "data": [
    {
      "name": "가톨릭대학교 여의도성모병원",
      "address": "서울특별시 영등포구 63로 10, 여의도성모병원 (여의도동)",
      "phone": "1661-7575",
      "url": "http://www.cmcujb.or.kr/",
      "region": "서울",
      "specialty": "상급종합병원",
      "category": "종합병원",
      "district": "영등포구"
    }
  ]
}
```

---

### 8. 질환 정보

```
GET /api/disease/{disease_code}
```

**경로 파라미터:**

| 이름 | 설명 |
|------|------|
| `disease_code` | 질환 코드 (예: `BRCA`) |

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `code` | string | 질환 코드 |
| `name` | string | 질환명 |
| `ensemble_spearman` | float | 앙상블 모델 Spearman 상관 |
| `ensemble_rmse` | float | 앙상블 모델 RMSE |
| `pipeline_date` | string | 파이프라인 실행일 |
| `efo_ids` | list | EFO/HPO ID 목록 |

**응답 예시:**
```json
{
  "status": "success",
  "data": {
    "code": "BRCA",
    "name": "Breast Cancer",
    "ensemble_spearman": 0.8055,
    "ensemble_rmse": 1.3008,
    "pipeline_date": "2026-04-08",
    "efo_ids": ["HP_0000769", "HP_0003187", "HP_0006625", "HP_0010311", "HP_0010313"]
  }
}
```

**에러:**
- `404`: Disease not found

---

### 9. PubMed 실시간 검색

```
GET /api/pubmed
```

**파라미터:**

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `query` | string | (필수) | 검색어 |
| `max_results` | int | 5 | 최대 결과 수 (max 20) |

**요청 예시:**
```
GET /api/pubmed?query=breast+cancer+docetaxel&max_results=5
```

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `pmid` | string | PubMed ID |
| `title` | string | 논문 제목 |
| `authors` | list | 저자 (최대 5명) |
| `journal` | string | 저널명 |
| `pub_date` | string | 출판일 |

**응답 예시:**
```json
{
  "status": "success",
  "data": [
    {
      "pmid": "12868802",
      "title": "Neoadjuvant docetaxel in locally advanced breast cancer.",
      "authors": ["Hutcheon AW", "Heys SD", "Sarkar TK", "Aberdeen Breast Group"],
      "journal": "Breast cancer research and treatment",
      "pub_date": "2003"
    }
  ],
  "source": "pubmed"
}
```

**에러:**
- `502`: PubMed API 호출 실패

---

### 10. 국립암센터 유방암 정보

```
GET /api/ncis/{category}
```

**경로 파라미터:**

| 이름 | 설명 |
|------|------|
| `category` | `brca` / `prevention` / `guide` / `term` |

**쿼리 파라미터:**

| 이름 | 타입 | 설명 |
|------|------|------|
| `term` | string | 용어 검색어 (category=`term` 일 때만, 기본값: `유방암`) |

**카테고리 설명:**

| category | 소스 | 설명 |
|----------|------|------|
| `brca` | cancer.go.kr/api/cancer.do | 유방암 상세 정보 (정의/증상/진단/치료) |
| `prevention` | cancer.go.kr/api/prevention.do | 암 예방/검진 정보 |
| `guide` | cancer.go.kr/api/data.do | 암환자 생활백서 |
| `term` | cancer.go.kr/api/dictionaryworks.do | 의학용어 사전 |

**요청 예시:**
```
GET /api/ncis/brca
GET /api/ncis/prevention
GET /api/ncis/term?term=HER2
```

**응답 예시 (brca):**
```json
{
  "status": "success",
  "data": {
    "발생부위": "일반적으로 암은 인간의 신체 중 어느 부위에서든지 발생할 수 있습니다...",
    "진단방법": "암에 대한 검사는 목적에 따라 암이 의심되지 않을 때 하는 검진과 같은 선별검사가..."
  },
  "source": "ncis"
}
```

**에러:**
- `400`: Invalid category

---

### 11. KG 현황

```
GET /api/stats
```

**파라미터:** 없음

**응답 예시:**
```json
{
  "status": "success",
  "data": {
    "nodes": {
      "Drug": 19844,
      "Target": 8880,
      "CellLine": 969,
      "Pathway": 686,
      "Hospital": 97,
      "SideEffect": 46,
      "Trial": 35,
      "Disease": 1
    },
    "edges": {
      "TESTED_IN": 89470,
      "INTERACTS_WITH": 46882,
      "IN_PATHWAY": 729,
      "HAS_SIDE_EFFECT": 109,
      "TREATS_DISEASE": 97,
      "ASSOCIATED_WITH": 50,
      "TARGETS": 41,
      "IN_TRIAL": 39,
      "FOR_DISEASE": 35,
      "TREATS": 13
    },
    "total_nodes": 30558,
    "total_edges": 137465
  }
}
```

---

### 12. 채팅 질의

```
POST /api/chat
```

**요청 Body:**

```json
{
  "query": "Docetaxel 부작용 알려줘",
  "user_type": "patient"
}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `query` | string | (필수) | 자연어 질의 |
| `user_type` | string | `patient` | `patient` / `researcher` |

**의도 분류:**

| intent | 트리거 키워드 | 데이터 소스 |
|--------|-------------|------------|
| `side_effects` | 부작용, side effect, 독성, toxicity | Neo4j HAS_SIDE_EFFECT |
| `trials` | 임상, trial, clinical, nct | Neo4j IN_TRIAL |
| `targets` | 타겟, target, 표적, 작용기전 | Neo4j TARGETS |
| `pathways` | pathway, 경로, 신호전달 | Neo4j IN_PATHWAY |
| `hospitals` | 병원, hospital, 의료기관 | Neo4j Hospital |
| `disease_stats` | 통계, 환자수, 발생률, 유병률 | Neo4j Disease |
| `prevention` | 예방, 검진, screening | NCIS cancer.go.kr |
| `term` | 용어, 사전, 뜻, 정의 | NCIS 의학용어사전 |
| `drug_info` | (기본) 약물명 매칭 시 | Neo4j Drug |

**응답 예시:**
```json
{
  "status": "success",
  "data": {
    "answer": "Docetaxel의 주요 부작용: NEUTROPENIA, NAUSEA, ALOPECIA, MADAROSIS, HAIR TEXTURE ABNORMAL",
    "detail": {
      "drug": "Docetaxel",
      "side_effects": [
        { "name": "NEUTROPENIA", "meddra_term": "NEUTROPENIA" },
        { "name": "NAUSEA", "meddra_term": "NAUSEA" },
        { "name": "ALOPECIA", "meddra_term": "ALOPECIA" }
      ]
    },
    "intent": "side_effects",
    "drug": "Docetaxel"
  }
}
```

**에러:**
- `400`: query is empty

---

## 파이프라인 15개 약물 목록

| # | 약물명 | brca_status |
|---|--------|-------------|
| 1 | Romidepsin | - |
| 2 | Sepantronium bromide | - |
| 3 | Dactinomycin | BRCA_RESEARCH |
| 4 | Staurosporine | BRCA_CANDIDATE |
| 5 | Vinblastine | BRCA_CURRENT |
| 6 | Bortezomib | BRCA_RESEARCH |
| 7 | SN-38 | BRCA_CURRENT |
| 8 | Docetaxel | BRCA_CURRENT |
| 9 | Vinorelbine | BRCA_CURRENT |
| 10 | Dinaciclib | BRCA_RESEARCH |
| 11 | Paclitaxel | BRCA_CURRENT |
| 12 | Rapamycin | BRCA_RESEARCH |
| 13 | Camptothecin | BRCA_RESEARCH |
| 14 | Luminespib | BRCA_CANDIDATE |
| 15 | Epirubicin | BRCA_CURRENT |

## 그래프 스키마

```
(Drug)-[:TARGETS]->(Target)
(Drug)-[:IN_TRIAL]->(Trial)
(Drug)-[:HAS_SIDE_EFFECT]->(SideEffect)
(Drug)-[:TESTED_IN]->(CellLine)
(Drug)-[:ASSOCIATED_WITH]->(Disease)
(Target)-[:IN_PATHWAY]->(Pathway)
(Target)-[:INTERACTS_WITH]->(Target)
(Hospital)-[:TREATS_DISEASE]->(Disease)
(Trial)-[:FOR_DISEASE]->(Disease)
(Hospital)-[:TREATS]->(Disease)
```
