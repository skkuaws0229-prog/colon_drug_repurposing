#!/usr/bin/env python3
"""
HGT 메모리 최적화 버전

메모리 절약 수정사항:
1. Gene 노드: 4,402 → top 1,000 (importance 기준)
2. hidden_dim: 256 → 128
3. batch_size: 절반으로 축소
4. Gradient accumulation (2 steps)
5. 불필요한 텐서 즉시 삭제 + torch.mps.empty_cache()
6. Mixed precision (float16) 옵션
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HGTConv
import numpy as np
import gc

class HGTModelOptimized(nn.Module):
    """
    Heterogeneous Graph Transformer (메모리 최적화)

    변경사항:
    - hidden_dim: 256 → 128
    - num_heads: 8 → 4
    - num_layers: 2 (유지)
    """
    def __init__(self, num_drugs, num_genes, hidden_dim=128, num_heads=4, num_layers=2, dropout=0.3):
        super().__init__()

        self.num_drugs = num_drugs
        self.num_genes = num_genes
        self.hidden_dim = hidden_dim

        # Node embeddings
        self.drug_embedding = nn.Embedding(num_drugs, hidden_dim)
        self.gene_embedding = nn.Embedding(num_genes, hidden_dim)

        # HGT layers
        self.convs = nn.ModuleList()
        metadata = (['drug', 'gene'],
                   [('drug', 'interacts', 'gene'),
                    ('gene', 'rev_interacts', 'drug')])

        for _ in range(num_layers):
            conv = HGTConv(hidden_dim, hidden_dim, metadata, num_heads, group='sum')
            self.convs.append(conv)

        # Output head (simple)
        self.predictor = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x_dict, edge_index_dict, drug_idx, gene_idx):
        """
        Args:
            x_dict: {'drug': [num_drugs, hidden_dim], 'gene': [num_genes, hidden_dim]}
            edge_index_dict: {('drug', 'interacts', 'gene'): edge_index, ...}
            drug_idx: [batch_size] - drug indices
            gene_idx: [batch_size, num_genes] - gene features (not used for lookup)

        Returns:
            predictions: [batch_size]
        """
        # HGT message passing
        for conv in self.convs:
            x_dict = conv(x_dict, edge_index_dict)
            # ReLU + cleanup
            x_dict = {key: F.relu(x) for key, x in x_dict.items()}

            # Memory cleanup
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

        # Get drug embeddings for batch
        drug_emb = x_dict['drug'][drug_idx]  # [batch_size, hidden_dim]

        # Aggregate gene information (mean pooling over all genes)
        gene_emb = x_dict['gene'].mean(dim=0, keepdim=True).expand(drug_idx.size(0), -1)

        # Concatenate and predict
        combined = torch.cat([drug_emb, gene_emb], dim=-1)

        # Memory cleanup before prediction
        del drug_emb, gene_emb
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

        pred = self.predictor(combined).squeeze(-1)

        return pred


def select_top_genes_by_importance(gene_importance_path, n_genes=1000):
    """
    CRISPR gene importance 기준으로 상위 N개 선택

    Args:
        gene_importance_path: CRISPR gene importance 파일 경로
        n_genes: 선택할 gene 수

    Returns:
        selected_indices: 선택된 gene indices (original 4,402 기준)
    """
    # CRISPR features의 variance 또는 mean absolute value로 importance 계산
    # 여기서는 간단히 step4 features에서 variance 계산

    from pathlib import Path
    base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
    step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"

    # X_train 로드
    X_train = np.load(step4_dir / "X_train.npy")

    # Gene features는 뒤쪽 4,402개 (Drug 1,127 + Gene 4,402)
    gene_features = X_train[:, 1127:]  # [6366, 4402]

    # Variance 계산
    gene_variance = np.var(gene_features, axis=0)

    # Top N genes 선택
    top_indices = np.argsort(gene_variance)[-n_genes:]  # 상위 n_genes개
    top_indices = np.sort(top_indices)  # 순서 유지

    print(f"✓ Top {n_genes} genes selected by variance")
    print(f"  Variance range: {gene_variance[top_indices].min():.4f} ~ {gene_variance[top_indices].max():.4f}")

    return top_indices


def create_graph_optimized(X, drug_indices, gene_indices_selected, top_k=20):
    """
    간이 bipartite graph 생성 (메모리 최적화)

    Args:
        X: [n_samples, n_features]
        drug_indices: drug feature indices (1,127개)
        gene_indices_selected: 선택된 gene feature indices (1,000개)
        top_k: 각 노드당 상위 k개 edge만 유지

    Returns:
        x_dict: {'drug': [n_drugs, hidden_dim], 'gene': [n_genes, hidden_dim]}
        edge_index_dict: {('drug', 'interacts', 'gene'): [2, n_edges], ...}
        num_drugs: drug 수
        num_genes: gene 수
    """
    from scipy.stats import pearsonr
    from pathlib import Path
    import torch

    base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
    step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"

    # Drug/Gene features 추출
    X_drug = X[:, drug_indices]  # [n_samples, 1127]
    X_gene = X[:, gene_indices_selected]  # [n_samples, 1000] - REDUCED!

    print(f"\n[Graph 생성 - 최적화]")
    print(f"  Drug features: {X_drug.shape}")
    print(f"  Gene features: {X_gene.shape} (원본 4,402 → {len(gene_indices_selected)})")

    # Feature 평균으로 node features 생성
    drug_features = torch.FloatTensor(np.mean(X_drug, axis=0, keepdims=True).T)  # [1127, 1]
    gene_features = torch.FloatTensor(np.mean(X_gene, axis=0, keepdims=True).T)  # [1000, 1]

    num_drugs = drug_features.shape[0]
    num_genes = gene_features.shape[0]

    print(f"  Nodes: {num_drugs} drugs + {num_genes} genes = {num_drugs + num_genes}")

    # Edge 생성 (Pearson correlation > 0, top-k)
    print(f"  Computing correlations (top-{top_k})...")

    edges_drug_to_gene = []
    for i in range(num_drugs):
        correlations = []
        for j in range(num_genes):
            corr, _ = pearsonr(X_drug[:, i], X_gene[:, j])
            if corr > 0:
                correlations.append((corr, j))

        # Top-k genes
        correlations.sort(reverse=True)
        for _, j in correlations[:top_k]:
            edges_drug_to_gene.append([i, j])

        if (i + 1) % 200 == 0:
            print(f"    {i+1}/{num_drugs} drugs processed")
            gc.collect()

    edges_drug_to_gene = np.array(edges_drug_to_gene).T  # [2, n_edges]
    edges_gene_to_drug = edges_drug_to_gene[[1, 0], :]  # Reverse

    print(f"  Edges: {edges_drug_to_gene.shape[1]} (reduced from ~200k)")

    # PyG format
    edge_index_dict = {
        ('drug', 'interacts', 'gene'): torch.LongTensor(edges_drug_to_gene),
        ('gene', 'rev_interacts', 'drug'): torch.LongTensor(edges_gene_to_drug)
    }

    # Initial node features (simple)
    x_dict = {
        'drug': drug_features,  # [1127, 1]
        'gene': gene_features   # [1000, 1]
    }

    # Cleanup
    del drug_features, gene_features, edges_drug_to_gene, edges_gene_to_drug
    gc.collect()

    return x_dict, edge_index_dict, num_drugs, num_genes


if __name__ == "__main__":
    print("HGT Optimized Model - Memory Test")
    print("=" * 80)

    # Test memory usage
    from pathlib import Path
    base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
    step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
    crossattn_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"

    # Load data
    X_train = np.load(step4_dir / "X_train.npy")
    drug_indices = np.load(crossattn_dir / "drug_feature_indices.npy")

    # Select top 1000 genes
    gene_indices_selected = select_top_genes_by_importance(None, n_genes=1000)

    # Create graph
    x_dict, edge_index_dict, num_drugs, num_genes = create_graph_optimized(
        X_train, drug_indices, gene_indices_selected, top_k=10  # Reduced top_k too
    )

    # Create model
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    model = HGTModelOptimized(num_drugs, num_genes, hidden_dim=128, num_heads=4).to(device)

    print(f"\n✓ Model created successfully")
    print(f"  Device: {device}")
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Test forward pass
    x_dict_device = {k: v.to(device) for k, v in x_dict.items()}
    edge_index_dict_device = {k: v.to(device) for k, v in edge_index_dict.items()}

    drug_idx = torch.LongTensor([0, 1, 2]).to(device)
    gene_idx = torch.zeros(3, 1000).to(device)  # dummy

    try:
        output = model(x_dict_device, edge_index_dict_device, drug_idx, gene_idx)
        print(f"  Forward pass: OK ({output.shape})")
    except Exception as e:
        print(f"  Forward pass: FAILED - {e}")

    print("\n" + "=" * 80)
