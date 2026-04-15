#!/usr/bin/env python3
"""
Bilinear Interaction Network v2 (디버깅 버전)

수정사항:
- learning rate: 1e-3 → 1e-4
- epochs: 100 → 200
- BatchNorm 추가 (각 encoder 출력에)
- gradient clipping: max_norm=1.0
- Drug/Gene block 각각 StandardScaler 적용
"""
import torch
import torch.nn as nn
import numpy as np


class BilinearInteractionNetV2(nn.Module):
    """
    Bilinear Interaction Network v2

    개선사항:
    - BatchNorm 추가로 학습 안정화
    - Gradient clipping으로 exploding gradient 방지
    """

    def __init__(self, drug_dim=1127, gene_dim=4402, hidden_dim=256, emb_dim=128, dropout=0.3):
        super().__init__()

        self.drug_dim = drug_dim
        self.gene_dim = gene_dim
        self.hidden_dim = hidden_dim
        self.emb_dim = emb_dim

        # Drug Encoder (with BatchNorm)
        self.drug_encoder = nn.Sequential(
            nn.Linear(drug_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, emb_dim),
            nn.BatchNorm1d(emb_dim),
            nn.ReLU()
        )

        # Gene Encoder (with BatchNorm)
        self.gene_encoder = nn.Sequential(
            nn.Linear(gene_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, emb_dim),
            nn.BatchNorm1d(emb_dim),
            nn.ReLU()
        )

        # Bilinear Interaction Layer
        self.bilinear = nn.Bilinear(emb_dim, emb_dim, 1)

        # Dropout
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


def verify_bilinear_v2():
    """모델 검증"""
    print("=" * 80)
    print("BilinearInteractionNetV2 검증")
    print("=" * 80)

    # 모델 생성
    model = BilinearInteractionNetV2(
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

    # BatchNorm 확인
    has_batchnorm = any('BatchNorm' in str(type(m)) for m in model.modules())
    print(f"\n✅ BatchNorm: {has_batchnorm}")

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

    print("\n[5] 개선사항")
    print("-" * 80)
    print("1. BatchNorm 추가 (학습 안정화)")
    print("2. Gradient clipping 적용 (학습 코드에서)")
    print("3. StandardScaler 적용 (학습 코드에서)")
    print("4. Learning rate 감소 (1e-3 → 1e-4)")
    print("5. Epochs 증가 (100 → 200)")

    print("\n검증 완료!")
    return model, total_params


if __name__ == "__main__":
    verify_bilinear_v2()
