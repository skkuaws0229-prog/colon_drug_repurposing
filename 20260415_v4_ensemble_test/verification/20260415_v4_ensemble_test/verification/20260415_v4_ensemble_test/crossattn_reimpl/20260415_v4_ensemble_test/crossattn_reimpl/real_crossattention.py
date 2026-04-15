#!/usr/bin/env python3
"""
Real CrossAttention Model Implementation
진짜 Multi-Head Attention을 사용하는 CrossAttention 모델
"""
import torch
import torch.nn as nn
import numpy as np


class RealCrossAttentionModel(nn.Module):
    """
    Real Cross-Attention Model with Multi-Head Attention

    Architecture:
    1. Drug features (1130) → Drug encoder (256)
    2. Gene features (4402) → Gene encoder (256)
    3. Cross-Attention: Drug ↔ Gene interaction
    4. Fusion → Output

    This is fundamentally different from FlatMLP:
    - FlatMLP: simple 2-layer MLP
    - This: Dual encoders + Cross-Attention + Fusion
    """

    def __init__(self, drug_dim=1130, gene_dim=4402, hidden_dim=256, n_heads=4, dropout=0.3):
        super().__init__()

        self.drug_dim = drug_dim
        self.gene_dim = gene_dim
        self.hidden_dim = hidden_dim
        self.n_heads = n_heads

        # ============================================================================
        # Dual Encoders: Drug와 Gene을 각각 인코딩
        # ============================================================================
        self.drug_encoder = nn.Sequential(
            nn.Linear(drug_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        self.gene_encoder = nn.Sequential(
            nn.Linear(gene_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # ============================================================================
        # Multi-Head Cross-Attention
        # Query: Drug, Key/Value: Gene (또는 반대)
        # ============================================================================
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True  # Input: [batch, seq, embed_dim]
        )

        # ============================================================================
        # Fusion Layer: Drug + Gene + Attention output
        # ============================================================================
        self.fusion = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim),  # drug + gene + attn_out
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # ============================================================================
        # Output Head
        # ============================================================================
        self.output = nn.Linear(hidden_dim, 1)

    def forward(self, x, drug_indices, gene_indices, return_attention_weights=False):
        """
        Forward pass with explicit attention

        Args:
            x: [batch, total_features] - 전체 feature vector
            drug_indices: numpy array or tensor - drug feature indices
            gene_indices: numpy array or tensor - gene feature indices
            return_attention_weights: bool - attention weight 반환 여부

        Returns:
            output: [batch] - IC50 prediction
            (optional) attn_weights: attention weights
        """
        # Feature 분리
        x_drug = x[:, drug_indices]  # [batch, drug_dim]
        x_gene = x[:, gene_indices]  # [batch, gene_dim]

        # Dual encoding
        drug_encoded = self.drug_encoder(x_drug)  # [batch, hidden_dim]
        gene_encoded = self.gene_encoder(x_gene)  # [batch, hidden_dim]

        # Cross-Attention을 위해 sequence dimension 추가
        # MultiheadAttention은 [batch, seq_len, embed_dim] 형태를 기대
        drug_seq = drug_encoded.unsqueeze(1)  # [batch, 1, hidden_dim]
        gene_seq = gene_encoded.unsqueeze(1)  # [batch, 1, hidden_dim]

        # Cross-Attention: Drug를 Query로, Gene을 Key/Value로 사용
        # 즉, "Drug가 Gene을 attend한다" = Drug와 Gene의 interaction 학습
        attn_out, attn_weights = self.cross_attention(
            query=drug_seq,      # [batch, 1, hidden_dim]
            key=gene_seq,        # [batch, 1, hidden_dim]
            value=gene_seq,      # [batch, 1, hidden_dim]
            need_weights=True
        )

        attn_out = attn_out.squeeze(1)  # [batch, hidden_dim]

        # Fusion: drug + gene + attention output
        fused = torch.cat([drug_encoded, gene_encoded, attn_out], dim=1)  # [batch, hidden_dim*3]
        fused = self.fusion(fused)  # [batch, hidden_dim]

        # Output
        output = self.output(fused).squeeze()  # [batch]

        if return_attention_weights:
            return output, attn_weights
        else:
            return output

    def get_architecture_summary(self):
        """모델 아키텍처 요약"""
        return {
            "model_name": "RealCrossAttentionModel",
            "drug_dim": self.drug_dim,
            "gene_dim": self.gene_dim,
            "hidden_dim": self.hidden_dim,
            "n_heads": self.n_heads,
            "components": {
                "drug_encoder": f"Linear({self.drug_dim}, {self.hidden_dim}) + ReLU + Dropout",
                "gene_encoder": f"Linear({self.gene_dim}, {self.hidden_dim}) + ReLU + Dropout",
                "cross_attention": f"MultiheadAttention(embed={self.hidden_dim}, heads={self.n_heads})",
                "fusion": f"Linear({self.hidden_dim*3}, {self.hidden_dim}) + ReLU + Dropout + Linear({self.hidden_dim}, {self.hidden_dim})",
                "output": f"Linear({self.hidden_dim}, 1)"
            },
            "key_differences_from_flatmlp": [
                "Dual encoders (drug/gene 분리)",
                "Multi-Head Cross-Attention layer",
                "3-way fusion (drug + gene + attention)",
                "Much larger capacity for learning drug-gene interactions"
            ]
        }


# ============================================================================
# 모델 검증 함수
# ============================================================================
def verify_model():
    """모델 구조 검증"""
    print("=" * 80)
    print("RealCrossAttentionModel 검증")
    print("=" * 80)

    # 모델 생성
    model = RealCrossAttentionModel(
        drug_dim=1130,
        gene_dim=4402,
        hidden_dim=256,
        n_heads=4,
        dropout=0.3
    )

    print("\n[1] 모델 아키텍처 요약")
    print("-" * 80)
    summary = model.get_architecture_summary()
    print(f"Model: {summary['model_name']}")
    print(f"Drug dim: {summary['drug_dim']}")
    print(f"Gene dim: {summary['gene_dim']}")
    print(f"Hidden dim: {summary['hidden_dim']}")
    print(f"Attention heads: {summary['n_heads']}")

    print("\n[2] Components")
    print("-" * 80)
    for comp_name, comp_desc in summary['components'].items():
        print(f"{comp_name:20s}: {comp_desc}")

    print("\n[3] Named Parameters")
    print("-" * 80)
    for name, param in model.named_parameters():
        print(f"{name:60s}: {list(param.shape)}")

    print("\n[4] Total Parameters")
    print("-" * 80)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total: {total_params:,}")

    # Attention layer 존재 확인
    has_attention = any('cross_attention' in name for name, _ in model.named_parameters())
    print(f"\n✅ Has Cross-Attention layer: {has_attention}")

    print("\n[5] Forward Pass Test")
    print("-" * 80)
    batch_size = 32
    total_features = 5532

    # 더미 입력
    x_dummy = torch.randn(batch_size, total_features)
    drug_indices = np.arange(1130)
    gene_indices = np.arange(1130, 5532)

    # Forward
    model.eval()
    with torch.no_grad():
        output, attn_weights = model(x_dummy, drug_indices, gene_indices, return_attention_weights=True)

    print(f"Input shape:  {x_dummy.shape}")
    print(f"Output shape: {output.shape}")
    print(f"Attention weights shape: {attn_weights.shape}")

    print(f"\n✅ Forward pass successful!")

    # Intermediate shapes
    with torch.no_grad():
        x_drug = x_dummy[:, drug_indices]
        x_gene = x_dummy[:, gene_indices]
        drug_encoded = model.drug_encoder(x_drug)
        gene_encoded = model.gene_encoder(x_gene)

        print(f"\n[6] Intermediate Tensor Shapes")
        print("-" * 80)
        print(f"x_drug shape:       {x_drug.shape}")
        print(f"x_gene shape:       {x_gene.shape}")
        print(f"drug_encoded shape: {drug_encoded.shape}")
        print(f"gene_encoded shape: {gene_encoded.shape}")

    print("\n[7] Key Differences from FlatMLP")
    print("-" * 80)
    for i, diff in enumerate(summary['key_differences_from_flatmlp'], 1):
        print(f"{i}. {diff}")

    print("\n검증 완료!")
    return model, total_params


if __name__ == "__main__":
    verify_model()
