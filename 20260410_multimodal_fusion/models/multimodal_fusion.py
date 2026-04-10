#!/usr/bin/env python3
"""
Multimodal Fusion Network for Drug Repurposing Pipeline

Encoder 정의는 modal_interface.py로 이동.
이 파일은 Cross-Attention Fusion 네트워크와 데이터 설정만 담당.
"""

import torch
import torch.nn as nn

from modal_interface import (
    CRISPREncoder, MorganFPEncoder, LINCSEncoder,
    TargetEncoder, DrugDescEncoder, registry,
)


# ── Cross-Attention Fusion Network ───────────────────────────────

class MultiModalFusionNet(nn.Module):
    """
    Cross-Attention Fusion: Sample modality attends to Drug modalities.

    Architecture:
      1. 5 Encoders → modality embeddings
      2. Cross-Attention: Q=CRISPR(sample), K/V=stack(Morgan,LINCS,Target,DrugDesc)
      3. FFN: [attn_out ∥ crispr_out] → IC50 prediction

    Forward signature:
      forward(crispr, morgan, lincs, target, drugdesc) → (B,)
    """

    def __init__(self, d_model: int = 128, nhead: int = 4, dropout: float = 0.2):
        super().__init__()

        # 1. Modality encoders
        self.crispr_enc = CRISPREncoder(input_dim=18310, output_dim=128, dropout=dropout)
        self.morgan_enc = MorganFPEncoder(input_dim=2048, output_dim=128, dropout=dropout)
        self.lincs_enc = LINCSEncoder(input_dim=5, output_dim=64, dropout=dropout)
        self.target_enc = TargetEncoder(input_dim=10, output_dim=64, dropout=dropout)
        self.drugdesc_enc = DrugDescEncoder(input_dim=9, output_dim=64, dropout=dropout)

        # 2. Projection layers: 64-d → 128-d for drug modalities
        self.lincs_proj = nn.Linear(64, d_model)
        self.target_proj = nn.Linear(64, d_model)
        self.drugdesc_proj = nn.Linear(64, d_model)

        # 3. Cross-Attention: Q=sample, K/V=drug tokens
        self.cross_attn = nn.MultiheadAttention(
            embed_dim=d_model, num_heads=nhead, dropout=dropout, batch_first=True,
        )

        # 4. Final prediction head: [attn_out(128) || crispr_out(128)] → 1
        self.head = nn.Sequential(
            nn.LayerNorm(d_model * 2),
            nn.Linear(d_model * 2, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, 1),
        )

    def forward(
        self,
        crispr: torch.Tensor,    # (B, 18310)
        morgan: torch.Tensor,    # (B, 2048)
        lincs: torch.Tensor,     # (B, 5)
        target: torch.Tensor,    # (B, 10)
        drugdesc: torch.Tensor,  # (B, 9)
    ) -> torch.Tensor:

        # ── 1. Encode each modality ──
        crispr_out = self.crispr_enc(crispr)      # (B, 128)
        morgan_out = self.morgan_enc(morgan)       # (B, 128)
        lincs_out = self.lincs_enc(lincs)          # (B, 64)
        target_out = self.target_enc(target)       # (B, 64)
        drugdesc_out = self.drugdesc_enc(drugdesc) # (B, 64)

        # ── 2. Project drug modalities to d_model=128, then stack ──
        morgan_tok = morgan_out.unsqueeze(1)                      # (B, 1, 128)
        lincs_tok = self.lincs_proj(lincs_out).unsqueeze(1)       # (B, 1, 128)
        target_tok = self.target_proj(target_out).unsqueeze(1)    # (B, 1, 128)
        drugdesc_tok = self.drugdesc_proj(drugdesc_out).unsqueeze(1)  # (B, 1, 128)

        drug_tokens = torch.cat(
            [morgan_tok, lincs_tok, target_tok, drugdesc_tok], dim=1,
        )  # (B, 4, 128)  ← Key, Value

        # Query = CRISPR (sample modality)
        query = crispr_out.unsqueeze(1)  # (B, 1, 128)

        # ── 3. Cross-Attention ──
        attn_out, _ = self.cross_attn(query, drug_tokens, drug_tokens)  # (B, 1, 128)
        attn_out = attn_out.squeeze(1)   # (B, 128)

        # ── 4. Predict IC50 ──
        combined = torch.cat([attn_out, crispr_out], dim=1)  # (B, 256)
        return self.head(combined).squeeze(-1)                # (B,)


# ── Data paths (S3 reference, no local copy) ────────────────────

S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
DATA_PATHS = {
    "features": f"{S3_BASE}/fe_output/20260408_fe_v1/features/features.parquet",
    "pair_features": f"{S3_BASE}/fe_output/20260408_fe_v1/pair_features/pair_features_newfe_v2.parquet",
    "labels": f"{S3_BASE}/fe_output/20260408_fe_v1/features/labels.parquet",
}

# Column slicing spec for each modality
MODALITY_COLUMNS = {
    "crispr": {"prefix": "sample__crispr__", "count": 18310},
    "morgan_fp": {"prefix": "drug_morgan_", "count": 2048},
    "lincs": {"prefix": "lincs_", "count": 5},
    "target": {"prefix": "target_", "count": 10},
    "drug_desc": {"prefix": "drug_desc_", "count": 9},
}


if __name__ == "__main__":
    batch = 4
    print(f"Registry: {registry}")
    print(f"Registered modals: {[m['name'] for m in registry.list_modals()]}\n")

    # MultiModalFusionNet end-to-end test
    print("MultiModalFusionNet smoke test:")
    model = MultiModalFusionNet()
    out = model(
        crispr=torch.randn(batch, 18310),
        morgan=torch.randn(batch, 2048),
        lincs=torch.randn(batch, 5),
        target=torch.randn(batch, 10),
        drugdesc=torch.randn(batch, 9),
    )
    print(f"  Output shape: {tuple(out.shape)}  (expected: ({batch},))")
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Total params: {n_params:,}")
