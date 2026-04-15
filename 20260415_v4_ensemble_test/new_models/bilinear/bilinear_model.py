#!/usr/bin/env python3
"""
Bilinear Interaction Network
Drug와 Gene을 분리 인코딩 후 bilinear interaction으로 예측
"""
import torch
import torch.nn as nn
import numpy as np


class BilinearInteractionNet(nn.Module):
    """
    Bilinear Interaction Network

    핵심: Drug와 Gene 간의 multiplicative interaction을 bilinear layer로 학습
    concat 후 MLP를 사용하지 않음으로써 기존 모델과 차별화
    """

    def __init__(self, drug_dim=1127, gene_dim=4402, hidden_dim=256, emb_dim=128, dropout=0.3):
        super().__init__()

        self.drug_dim = drug_dim
        self.gene_dim = gene_dim
        self.hidden_dim = hidden_dim
        self.emb_dim = emb_dim

        # Drug Encoder
        self.drug_encoder = nn.Sequential(
            nn.Linear(drug_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, emb_dim),
            nn.ReLU()
        )

        # Gene Encoder
        self.gene_encoder = nn.Sequential(
            nn.Linear(gene_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, emb_dim),
            nn.ReLU()
        )

        # Bilinear Interaction Layer
        # out = drug_emb^T × W × gene_emb
        self.bilinear = nn.Bilinear(emb_dim, emb_dim, 1)

        # 추가 normalization (optional)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, drug_indices, gene_indices):
        """
        Forward pass

        Args:
            x: [batch, total_features]
            drug_indices: drug feature indices
            gene_indices: gene feature indices

        Returns:
            output: [batch] IC50 prediction
        """
        # Feature 분리
        x_drug = x[:, drug_indices]  # [batch, drug_dim]
        x_gene = x[:, gene_indices]  # [batch, gene_dim]

        # Encoding
        drug_emb = self.drug_encoder(x_drug)  # [batch, emb_dim]
        gene_emb = self.gene_encoder(x_gene)  # [batch, emb_dim]

        # Bilinear interaction
        # out = drug_emb^T × W × gene_emb
        output = self.bilinear(drug_emb, gene_emb)  # [batch, 1]
        output = output.squeeze()  # [batch]

        return output

    def get_embeddings(self, x, drug_indices, gene_indices):
        """Get drug and gene embeddings"""
        x_drug = x[:, drug_indices]
        x_gene = x[:, gene_indices]
        drug_emb = self.drug_encoder(x_drug)
        gene_emb = self.gene_encoder(x_gene)
        return drug_emb, gene_emb


def verify_bilinear_model():
    """모델 검증"""
    print("=" * 80)
    print("BilinearInteractionNet 검증")
    print("=" * 80)

    # 모델 생성
    model = BilinearInteractionNet(
        drug_dim=1127,
        gene_dim=4402,
        hidden_dim=256,
        emb_dim=128,
        dropout=0.3
    )

    print("\n[1] 모델 아키텍처")
    print("-" * 80)
    print(f"Drug dim: {model.drug_dim}")
    print(f"Gene dim: {model.gene_dim}")
    print(f"Hidden dim: {model.hidden_dim}")
    print(f"Embedding dim: {model.emb_dim}")

    print("\n[2] Named Parameters")
    print("-" * 80)
    for name, param in model.named_parameters():
        print(f"{name:50s}: {list(param.shape)}")

    # 핵심 레이어 확인
    has_drug_encoder = any('drug_encoder' in name for name, _ in model.named_parameters())
    has_gene_encoder = any('gene_encoder' in name for name, _ in model.named_parameters())
    has_bilinear = any('bilinear' in name for name, _ in model.named_parameters())

    print(f"\n✅ Drug Encoder: {has_drug_encoder}")
    print(f"✅ Gene Encoder: {has_gene_encoder}")
    print(f"✅ Bilinear Layer: {has_bilinear}")

    print("\n[3] Total Parameters")
    print("-" * 80)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total: {total_params:,}")

    print("\n[4] Forward Pass Test")
    print("-" * 80)
    batch_size = 32
    total_features = 5529

    x_dummy = torch.randn(batch_size, total_features)
    drug_indices = np.arange(1127)
    gene_indices = np.arange(1127, 5529)

    model.eval()
    with torch.no_grad():
        output = model(x_dummy, drug_indices, gene_indices)
        drug_emb, gene_emb = model.get_embeddings(x_dummy, drug_indices, gene_indices)

    print(f"Input shape:     {x_dummy.shape}")
    print(f"Drug emb shape:  {drug_emb.shape}")
    print(f"Gene emb shape:  {gene_emb.shape}")
    print(f"Output shape:    {output.shape}")

    print(f"\n✅ Forward pass successful!")

    print("\n[5] 차별화 요소")
    print("-" * 80)
    print("1. Drug와 Gene 분리 인코딩")
    print("2. Bilinear interaction (multiplicative)")
    print("3. Concat 후 MLP 없음 (기존 모델과 차이)")
    print("4. Drug-Gene interaction에 집중")

    print("\n검증 완료!")
    return model, total_params


if __name__ == "__main__":
    verify_bilinear_model()
