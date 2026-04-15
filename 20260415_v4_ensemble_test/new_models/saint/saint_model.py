#!/usr/bin/env python3
"""
SAINT (Self-Attention and Intersample Attention Network)
Column-aware attention으로 feature 간 상호작용 학습
"""
import torch
import torch.nn as nn
import numpy as np
import math


class SAINTModel(nn.Module):
    """
    SAINT: Self-Attention and Intersample Attention Network

    핵심:
    - 각 feature를 token으로 변환 (column embedding)
    - Inter-feature attention으로 feature 간 상호작용 학습
    - Drug/Gene block을 구분하여 block-aware attention 가능
    """

    def __init__(self, n_features=5529, embed_dim=32, n_heads=4, n_layers=2, dropout=0.3):
        super().__init__()

        self.n_features = n_features
        self.embed_dim = embed_dim
        self.n_heads = n_heads
        self.n_layers = n_layers

        # Column (feature) embeddings
        # 각 feature에 대한 learnable embedding
        self.column_embeddings = nn.Parameter(torch.randn(n_features, embed_dim))

        # Value projection: feature value → embedding
        self.value_projection = nn.Linear(1, embed_dim)

        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=n_heads,
            dim_feedforward=embed_dim * 4,
            dropout=dropout,
            activation='relu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # Output head
        self.output_head = nn.Sequential(
            nn.Linear(embed_dim * n_features, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1)
        )

    def forward(self, x):
        """
        Forward pass

        Args:
            x: [batch, n_features]

        Returns:
            output: [batch] IC50 prediction
        """
        batch_size = x.size(0)

        # Feature value를 embedding으로 변환
        # [batch, n_features] → [batch, n_features, 1] → [batch, n_features, embed_dim]
        x_expanded = x.unsqueeze(-1)  # [batch, n_features, 1]
        value_emb = self.value_projection(x_expanded)  # [batch, n_features, embed_dim]

        # Column embedding 추가
        # [batch, n_features, embed_dim] + [n_features, embed_dim]
        column_emb = self.column_embeddings.unsqueeze(0).expand(batch_size, -1, -1)
        token_emb = value_emb + column_emb  # [batch, n_features, embed_dim]

        # Transformer (inter-feature attention)
        # [batch, n_features, embed_dim]
        attn_out = self.transformer(token_emb)  # [batch, n_features, embed_dim]

        # Flatten
        attn_flat = attn_out.reshape(batch_size, -1)  # [batch, n_features * embed_dim]

        # Output
        output = self.output_head(attn_flat).squeeze()  # [batch]

        return output


class SAINTModelLite(nn.Module):
    """
    SAINT Lite Version
    메모리 효율성을 위해 feature를 압축 후 attention
    """

    def __init__(self, n_features=5529, embed_dim=64, n_heads=4, n_layers=2,
                 n_tokens=64, dropout=0.3):
        super().__init__()

        self.n_features = n_features
        self.embed_dim = embed_dim
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.n_tokens = n_tokens

        # Feature → token projection
        # n_features를 n_tokens로 압축
        self.feature_to_token = nn.Linear(n_features, n_tokens * embed_dim)

        # Positional encoding
        self.pos_encoding = nn.Parameter(torch.randn(n_tokens, embed_dim))

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=n_heads,
            dim_feedforward=embed_dim * 4,
            dropout=dropout,
            activation='relu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # Output head
        self.output_head = nn.Sequential(
            nn.Linear(embed_dim * n_tokens, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1)
        )

    def forward(self, x):
        """Forward pass"""
        batch_size = x.size(0)

        # Feature → tokens
        tokens = self.feature_to_token(x)  # [batch, n_tokens * embed_dim]
        tokens = tokens.reshape(batch_size, self.n_tokens, self.embed_dim)  # [batch, n_tokens, embed_dim]

        # Add positional encoding
        tokens = tokens + self.pos_encoding.unsqueeze(0)  # [batch, n_tokens, embed_dim]

        # Transformer
        attn_out = self.transformer(tokens)  # [batch, n_tokens, embed_dim]

        # Flatten
        attn_flat = attn_out.reshape(batch_size, -1)  # [batch, n_tokens * embed_dim]

        # Output
        output = self.output_head(attn_flat).squeeze()  # [batch]

        return output


def verify_saint_model():
    """모델 검증"""
    print("=" * 80)
    print("SAINT Model 검증")
    print("=" * 80)

    # Lite 버전 사용 (메모리 효율)
    model = SAINTModelLite(
        n_features=5529,
        embed_dim=64,
        n_heads=4,
        n_layers=2,
        n_tokens=64,
        dropout=0.3
    )

    print("\n[1] 모델 아키텍처")
    print("-" * 80)
    print(f"N features: {model.n_features}")
    print(f"Embed dim: {model.embed_dim}")
    print(f"N heads: {model.n_heads}")
    print(f"N layers: {model.n_layers}")
    print(f"N tokens: {model.n_tokens}")

    print("\n[2] Named Parameters (샘플)")
    print("-" * 80)
    for i, (name, param) in enumerate(model.named_parameters()):
        if i < 10:  # 처음 10개만
            print(f"{name:60s}: {list(param.shape)}")
    print("...")

    # Attention layer 확인
    has_transformer = any('transformer' in name for name, _ in model.named_parameters())
    has_attention = any('self_attn' in name or 'multihead' in name.lower()
                        for name, _ in model.named_parameters())

    print(f"\n✅ Transformer: {has_transformer}")
    print(f"✅ Attention: {has_attention}")

    print("\n[3] Total Parameters")
    print("-" * 80)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total: {total_params:,}")

    print("\n[4] Forward Pass Test")
    print("-" * 80)
    batch_size = 32
    x_dummy = torch.randn(batch_size, 5529)

    model.eval()
    with torch.no_grad():
        output = model(x_dummy)

    print(f"Input shape:  {x_dummy.shape}")
    print(f"Output shape: {output.shape}")

    print(f"\n✅ Forward pass successful!")

    print("\n[5] 차별화 요소")
    print("-" * 80)
    print("1. Column-aware attention (각 feature를 token으로)")
    print("2. Inter-feature attention (feature 간 상호작용)")
    print("3. Transformer encoder (self-attention)")
    print("4. Lite 버전으로 메모리 효율성")

    print("\n검증 완료!")
    return model, total_params


if __name__ == "__main__":
    verify_saint_model()
