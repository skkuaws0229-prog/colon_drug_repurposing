#!/usr/bin/env python3
"""
LLM Explanation Automation Template
═══════════════════════════════════════════════════════════════════════════
Top 30 drug별 자동 요약 생성 (Claude API 사용, 향후 Bedrock 전환)
항목: 주요 target gene / Hallmark pathway / LINCS reversal signal /
      OpenTargets disease relevance / 문헌 근거 (PubMed 키워드)
출력: JSON + Markdown
저장: results/llm_explanations_20260413/{drug_name}_explanation.md
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
import re
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent

# Top 30 reextract 결과 (작업 1 완료 후 사용 가능)
TOP30_PATH = PROJECT_ROOT / "results" / "top30_reextract_20260413" / "top30_reextract.csv"

# Data sources
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
DRUG_ANN_S3 = f"{S3_BASE}/data/gsdc/gdsc2_drug_annotation_master_20260406.parquet"
MSIGDB_S3 = f"{S3_BASE}/data/msigdb/msigdb_gene_set_membership_basic_20260406.parquet"
OT_ASSOC_S3 = f"{S3_BASE}/data/opentargets/opentargets_association_overall_direct_basic_20260406.parquet"
OT_TARGET_S3 = f"{S3_BASE}/data/opentargets/opentargets_target_basic_20260406.parquet"
OT_DISEASE_S3 = f"{S3_BASE}/data/opentargets/opentargets_disease_basic_20260406.parquet"

# Mechanism v2 features (LINCS 관련)
V2_PATH = PROJECT_ROOT / "mechanism" / "mechanism_features_v2_20260413.parquet"

# Drug target mapping
DRUG_TARGET_S3 = f"{S3_BASE}/data/drug_target_mapping_basic_20260406.parquet"

OUTPUT_DIR = PROJECT_ROOT / "results" / "llm_explanations_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Claude API (임시, 향후 Bedrock 전환)
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 2000


def load_context_data():
    """약물 설명에 필요한 전체 컨텍스트 데이터 로드."""
    print("  Loading context data from S3...")
    t0 = time.time()

    drug_ann = pd.read_parquet(DRUG_ANN_S3)
    msigdb = pd.read_parquet(MSIGDB_S3)
    ot_assoc = pd.read_parquet(OT_ASSOC_S3)
    ot_target = pd.read_parquet(OT_TARGET_S3)
    ot_disease = pd.read_parquet(OT_DISEASE_S3)

    # Drug target mapping
    try:
        drug_target = pd.read_parquet(DRUG_TARGET_S3)
    except Exception:
        drug_target = pd.DataFrame()

    # Mechanism v2 (LINCS scores)
    v2 = pd.read_parquet(V2_PATH) if V2_PATH.exists() else pd.DataFrame()

    # Hallmark pathways only
    hallmark = msigdb[msigdb["collection"].str.contains("hallmark", case=False, na=False)]

    dt = time.time() - t0
    print(f"    Drug annotations: {drug_ann.shape[0]} drugs")
    print(f"    MSigDB Hallmark: {hallmark['gene_set_name'].nunique()} pathways, "
          f"{hallmark['gene_symbol'].nunique()} genes")
    print(f"    OpenTargets associations: {ot_assoc.shape[0]}")
    print(f"    Mechanism v2 features: {v2.shape}")
    print(f"    ({dt:.1f}s)")

    return {
        "drug_ann": drug_ann,
        "hallmark": hallmark,
        "ot_assoc": ot_assoc,
        "ot_target": ot_target,
        "ot_disease": ot_disease,
        "drug_target": drug_target,
        "v2": v2,
    }


def gather_drug_context(drug_id, drug_name, target_str, pathway_str, ctx):
    """단일 약물에 대한 컨텍스트 정보 수집."""
    info = {
        "drug_id": int(drug_id),
        "drug_name": drug_name,
        "target_genes": [],
        "hallmark_pathways": [],
        "lincs_scores": {},
        "opentargets_relevance": [],
        "pubmed_keywords": [],
    }

    # 1. Target genes
    target_genes = [g.strip() for g in str(target_str).split(", ") if g.strip()]
    info["target_genes"] = target_genes
    info["putative_target"] = target_str
    info["pathway"] = pathway_str

    # 2. Hallmark pathways - target genes가 속한 경로 찾기
    hallmark = ctx["hallmark"]
    if len(target_genes) > 0:
        matched = hallmark[hallmark["gene_symbol"].isin(target_genes)]
        pathway_counts = matched.groupby("gene_set_name")["gene_symbol"].apply(list).to_dict()
        info["hallmark_pathways"] = [
            {"pathway": pw, "matched_genes": genes}
            for pw, genes in sorted(pathway_counts.items(), key=lambda x: -len(x[1]))
        ]

    # 3. LINCS reversal scores (from v2 features)
    v2 = ctx["v2"]
    if not v2.empty and "canonical_drug_id" in v2.columns:
        drug_v2 = v2[v2["canonical_drug_id"].astype(str) == str(drug_id)]
        if not drug_v2.empty:
            lincs_cols = [c for c in drug_v2.columns if "lincs" in c.lower()]
            for col in lincs_cols:
                vals = drug_v2[col].values
                info["lincs_scores"][col] = {
                    "mean": float(np.nanmean(vals)),
                    "std": float(np.nanstd(vals)),
                    "min": float(np.nanmin(vals)),
                    "max": float(np.nanmax(vals)),
                }

    # 4. OpenTargets disease relevance
    ot_assoc = ctx["ot_assoc"]
    ot_target_df = ctx["ot_target"]
    ot_disease = ctx["ot_disease"]

    # Find BRCA-related disease IDs
    brca_diseases = ot_disease[
        ot_disease["name"].str.contains("breast", case=False, na=False)
    ]["id"].values

    # Find target gene IDs
    for gene in target_genes:
        gene_matches = ot_target_df[
            ot_target_df["approvedSymbol"].str.upper() == gene.upper()
        ]
        if gene_matches.empty:
            continue

        target_id = gene_matches.iloc[0]["id"]

        # Find associations with BRCA
        gene_assoc = ot_assoc[
            (ot_assoc["targetId"] == target_id) &
            (ot_assoc["diseaseId"].isin(brca_diseases))
        ]

        if not gene_assoc.empty:
            best_score = float(gene_assoc["score"].max())
            disease_ids = gene_assoc.nlargest(3, "score")["diseaseId"].values
            disease_names = []
            for did in disease_ids:
                d = ot_disease[ot_disease["id"] == did]
                if not d.empty:
                    disease_names.append(d.iloc[0]["name"])

            info["opentargets_relevance"].append({
                "gene": gene,
                "best_association_score": best_score,
                "related_diseases": disease_names,
            })

    # 5. PubMed keywords
    info["pubmed_keywords"] = [
        f"{drug_name} breast cancer",
        f"{drug_name} BRCA",
        f"{' '.join(target_genes[:3])} breast cancer treatment",
        f"{drug_name} drug sensitivity IC50",
        f"{pathway_str} breast cancer therapy",
    ]

    return info


def build_prompt(drug_info):
    """Claude API에 보낼 프롬프트 구성."""
    prompt = f"""다음 약물의 유방암(BRCA) 재창출 가능성에 대해 간결하게 분석해 주세요.

## 약물 정보
- **약물명**: {drug_info['drug_name']}
- **주요 타겟**: {drug_info['putative_target']}
- **경로**: {drug_info['pathway']}
- **타겟 유전자**: {', '.join(drug_info['target_genes'])}

## Hallmark Pathways 연관
"""
    if drug_info["hallmark_pathways"]:
        for pw in drug_info["hallmark_pathways"][:5]:
            prompt += f"- {pw['pathway']}: {', '.join(pw['matched_genes'])}\n"
    else:
        prompt += "- 직접 매칭된 Hallmark pathway 없음\n"

    prompt += "\n## LINCS Reversal Signal\n"
    if drug_info["lincs_scores"]:
        for col, stats in drug_info["lincs_scores"].items():
            prompt += f"- {col}: mean={stats['mean']:.4f}, range=[{stats['min']:.4f}, {stats['max']:.4f}]\n"
    else:
        prompt += "- LINCS 데이터 없음\n"

    prompt += "\n## OpenTargets Disease Relevance\n"
    if drug_info["opentargets_relevance"]:
        for rel in drug_info["opentargets_relevance"]:
            prompt += (f"- {rel['gene']}: score={rel['best_association_score']:.3f}, "
                       f"diseases={', '.join(rel['related_diseases'][:3])}\n")
    else:
        prompt += "- OpenTargets 연관 없음\n"

    prompt += f"""
## 요청 분석 항목 (한글로 작성)
1. **작용 기전 요약** (2-3문장): 이 약물이 어떻게 암세포에 작용하는지
2. **유방암 특이적 근거** (2-3문장): 유방암에서 이 타겟/경로가 왜 중요한지
3. **LINCS 신호 해석** (1-2문장): 유전자 발현 역전 가능성
4. **재창출 가능성 평가**: 높음/중간/낮음 + 근거 1문장
5. **PubMed 검색 키워드**: 추가 문헌 조사를 위한 키워드 3개

간결하게 작성해 주세요. 각 항목은 핵심만 포함합니다.
"""
    return prompt


def call_claude_api(prompt, drug_name):
    """Claude API 호출 (anthropic SDK 사용)."""
    try:
        import anthropic
    except ImportError:
        print(f"    [WARN] anthropic SDK 없음 → {drug_name} 건너뜀 (pip install anthropic)")
        return None

    try:
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"    [ERROR] API call failed for {drug_name}: {str(e)[:100]}")
        return None


def save_explanation(drug_info, explanation_text):
    """약물별 Markdown + JSON 저장."""
    drug_name = drug_info["drug_name"]
    safe_name = re.sub(r'[^\w\-]', '_', drug_name)

    # Markdown
    md_content = f"""# {drug_name} - 유방암 재창출 분석

## 기본 정보
- **약물 ID**: {drug_info['drug_id']}
- **주요 타겟**: {drug_info['putative_target']}
- **경로**: {drug_info['pathway']}
- **타겟 유전자**: {', '.join(drug_info['target_genes'])}

## Hallmark Pathways
"""
    if drug_info["hallmark_pathways"]:
        for pw in drug_info["hallmark_pathways"][:5]:
            md_content += f"- **{pw['pathway']}**: {', '.join(pw['matched_genes'])}\n"
    else:
        md_content += "- 직접 매칭 없음\n"

    md_content += "\n## OpenTargets 연관성\n"
    if drug_info["opentargets_relevance"]:
        for rel in drug_info["opentargets_relevance"]:
            md_content += (f"- **{rel['gene']}**: score={rel['best_association_score']:.3f} "
                           f"({', '.join(rel['related_diseases'][:3])})\n")
    else:
        md_content += "- 연관 없음\n"

    md_content += "\n## LINCS Reversal Signal\n"
    if drug_info["lincs_scores"]:
        for col, stats in drug_info["lincs_scores"].items():
            md_content += f"- **{col}**: mean={stats['mean']:.4f}\n"
    else:
        md_content += "- 데이터 없음\n"

    md_content += "\n## PubMed 검색 키워드\n"
    for kw in drug_info["pubmed_keywords"]:
        md_content += f"- `{kw}`\n"

    if explanation_text:
        md_content += f"\n---\n\n## LLM 분석 결과\n\n{explanation_text}\n"
    else:
        md_content += "\n---\n\n## LLM 분석 결과\n\n*API 호출 실패 또는 SDK 미설치*\n"

    md_content += f"\n---\n*생성일: 2026-04-13 | Claude API ({CLAUDE_MODEL})*\n"

    md_path = OUTPUT_DIR / f"{safe_name}_explanation.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return md_path


def main():
    t0 = time.time()
    print("=" * 70)
    print("  LLM Explanation Template - Top 30 Drug Analysis")
    print("=" * 70)

    # Top 30 로드
    if not TOP30_PATH.exists():
        raise FileNotFoundError(
            f"Top 30 파일 없음: {TOP30_PATH}\n"
            "먼저 run_top30_reextract_20260413.py 를 실행하세요."
        )

    top30 = pd.read_csv(TOP30_PATH)
    print(f"\n  Top 30 drugs loaded: {len(top30)} drugs")

    # 컨텍스트 데이터 로드
    ctx = load_context_data()

    # 각 약물별 처리
    all_results = []
    api_success = 0
    api_fail = 0

    print(f"\n{'─'*70}")
    print(f"  Processing {len(top30)} drugs...")
    print(f"{'─'*70}")

    for idx, row in top30.iterrows():
        drug_id = row["canonical_drug_id"]
        drug_name = str(row.get("drug_name", f"Drug_{drug_id}"))
        target_str = str(row.get("target", "N/A"))
        pathway_str = str(row.get("pathway", "N/A"))

        print(f"\n  [{idx+1}/{len(top30)}] {drug_name} (ID: {drug_id})")

        # 1. 컨텍스트 수집
        drug_info = gather_drug_context(drug_id, drug_name, target_str, pathway_str, ctx)

        # 2. 프롬프트 생성
        prompt = build_prompt(drug_info)

        # 3. Claude API 호출
        explanation = call_claude_api(prompt, drug_name)
        if explanation:
            api_success += 1
            print(f"    API response: {len(explanation)} chars")
        else:
            api_fail += 1

        # 4. 저장
        md_path = save_explanation(drug_info, explanation)
        print(f"    Saved: {md_path.name}")

        # 5. 결과 수집
        result = {
            "drug_id": int(drug_id),
            "drug_name": drug_name,
            "target": target_str,
            "pathway": pathway_str,
            "n_hallmark_pathways": len(drug_info["hallmark_pathways"]),
            "n_ot_associations": len(drug_info["opentargets_relevance"]),
            "has_lincs": bool(drug_info["lincs_scores"]),
            "api_success": explanation is not None,
            "md_file": md_path.name,
        }
        all_results.append(result)

    # 전체 결과 JSON 저장
    summary_path = OUTPUT_DIR / "explanation_summary.json"
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64, np.bool_)):
            return int(obj)
        return obj

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "description": "LLM Explanation Summary for Top 30 Drugs",
            "model": CLAUDE_MODEL,
            "api_success": api_success,
            "api_fail": api_fail,
            "total_drugs": len(top30),
            "results": all_results,
        }, f, indent=2, default=convert, ensure_ascii=False)

    dt = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  LLM Explanation 완료")
    print(f"  API 성공: {api_success}/{len(top30)}, 실패: {api_fail}/{len(top30)}")
    print(f"  결과 저장: {OUTPUT_DIR}")
    print(f"  소요시간: {dt/60:.1f} min")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
