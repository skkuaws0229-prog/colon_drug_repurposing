#!/usr/bin/env python3
"""
HGT (Heterogeneous Graph Transformer) - Simplified Bipartite Version
Drug-Gene bipartite graph에서 heterogeneous attention 학습
"""
import torch
import torch.nn as nn
import torch_geometric
from torch_geometric.nn import HeteroConv, GATConv, Linear
from torch_geometric.data import HeteroData
import numpy as np


class SimpleHGTModel(nn.Module):
    """
    Simple HGT for Drug-Gene Bipartite Graph

    노드 타입:
    - Drug: drug features (1127-dim)
    - Gene: gene features (4402-dim)

    엣지 타입:
    - (Drug, interacts_with, Gene): drug-gene interaction
    """

    def __init__(self, drug_dim=1127, gene_dim=4402, hidden_dim=128, n_layers=2, n_heads=4, dropout=0.3):
        super().__init__()

        self.drug_dim = drug_dim
        self.gene_dim = gene_dim
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers

        # Node feature projection
        self.drug_proj = Linear(drug_dim, hidden_dim)
        self.gene_proj = Linear(gene_dim, hidden_dim)

        # Heterogeneous graph convolutions
        self.convs = nn.ModuleList()
        for _ in range(n_layers):
            conv = HeteroConv({
                ('drug', 'interacts', 'gene'): GATConv(hidden_dim, hidden_dim, heads=n_heads, concat=False, dropout=dropout, add_self_loops=False),
                ('gene', 'rev_interacts', 'drug'): GATConv(hidden_dim, hidden_dim, heads=n_heads, concat=False, dropout=dropout, add_self_loops=False),
            }, aggr='mean')
            self.convs.append(conv)

        # Output MLP (drug node만 사용)
        self.output_mlp = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, data):
        """
        Forward pass

        Args:
            data: HeteroData with
                - data['drug'].x: [n_drugs, drug_dim]
                - data['gene'].x: [n_genes, gene_dim]
                - data['drug', 'interacts', 'gene'].edge_index
                - data['gene', 'rev_interacts', 'drug'].edge_index

        Returns:
            output: [n_drugs] IC50 predictions
        """
        # Node feature projection
        x_dict = {
            'drug': self.drug_proj(data['drug'].x),
            'gene': self.gene_proj(data['gene'].x)
        }

        # Graph convolutions
        for conv in self.convs:
            x_dict = conv(x_dict, data.edge_index_dict)
            # ReLU + residual (optional)
            for key in x_dict:
                x_dict[key] = torch.relu(x_dict[key])

        # Output (drug nodes만)
        drug_emb = x_dict['drug']  # [n_drugs, hidden_dim]
        output = self.output_mlp(drug_emb).squeeze()  # [n_drugs]

        return output


def create_drug_gene_bipartite_graph(x, drug_indices, gene_indices, top_k=50):
    """
    Drug-Gene bipartite graph 생성

    방법: 각 sample (drug-cell pair)를 하나의 drug node로 취급
    drug feature와 gene feature 간의 상관관계로 엣지 생성

    Args:
        x: [n_samples, n_features] - 전체 features
        drug_indices: drug feature indices
        gene_indices: gene feature indices
        top_k: 각 drug당 연결할 gene 수

    Returns:
        HeteroData
    """
    n_samples = x.shape[0]

    # Drug/Gene features 분리
    x_drug = x[:, drug_indices]  # [n_samples, n_drug_features]
    x_gene = x[:, gene_indices]  # [n_samples, n_gene_features]

    # Drug nodes: 각 sample이 하나의 drug
    # Gene nodes: gene features (n_gene_features개)

    n_drugs = n_samples
    n_genes = len(gene_indices)

    # 엣지 생성: drug i와 gene j의 상관계수로
    # 간단하게: 각 drug마다 값이 높은 top-k genes와 연결
    edge_index_drug_gene = []

    for i in range(n_drugs):  # 전체 샘플 사용
        gene_values = x_gene[i]  # [n_genes]
        top_genes = torch.topk(torch.from_numpy(gene_values), k=min(top_k, n_genes)).indices

        for gene_idx in top_genes:
            edge_index_drug_gene.append([i, gene_idx.item()])

    edge_index_drug_gene = torch.tensor(edge_index_drug_gene).t()  # [2, n_edges]

    # Reverse edges
    edge_index_gene_drug = edge_index_drug_gene.flip(0)

    # HeteroData 생성
    data = HeteroData()

    # Node features
    data['drug'].x = torch.from_numpy(x_drug).float()  # [n_drugs, drug_dim]
    # Gene features: 평균값 사용
    gene_features = x_gene.T  # [n_genes, n_samples]
    data['gene'].x = torch.from_numpy(gene_features).float()  # [n_genes, 1]

    # 실제로는 gene node feature를 적절히 설계해야 함
    # 여기서는 간단하게 identity embedding
    data['gene'].x = torch.eye(n_genes).float()  # [n_genes, n_genes]

    # Edges
    data['drug', 'interacts', 'gene'].edge_index = edge_index_drug_gene
    data['gene', 'rev_interacts', 'drug'].edge_index = edge_index_gene_drug

    return data


def verify_hgt_model():
    """모델 검증"""
    print("=" * 80)
    print("SimpleHGTModel 검증")
    print("=" * 80)

    # 모델 생성
    model = SimpleHGTModel(
        drug_dim=1127,
        gene_dim=4402,
        hidden_dim=128,
        n_layers=2,
        n_heads=4,
        dropout=0.3
    )

    print("\n[1] 모델 아키텍처")
    print("-" * 80)
    print(f"Drug dim: {model.drug_dim}")
    print(f"Gene dim: {model.gene_dim}")
    print(f"Hidden dim: {model.hidden_dim}")
    print(f"N layers: {model.n_layers}")

    print("\n[2] Named Parameters (샘플)")
    print("-" * 80)
    for i, (name, param) in enumerate(model.named_parameters()):
        if i < 15:
            print(f"{name:60s}: {list(param.shape)}")
    print("...")

    # HeteroConv 확인
    has_hetero = any('convs' in name for name, _ in model.named_parameters())
    has_gat = any('gat' in name.lower() or 'att' in name.lower() for name, _ in model.named_parameters())

    print(f"\n✅ HeteroConv: {has_hetero}")
    print(f"✅ GAT/Attention: {has_gat}")

    print("\n[3] Total Parameters")
    print("-" * 80)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total: {total_params:,}")

    print("\n[4] Graph 구조 테스트")
    print("-" * 80)

    # 더미 데이터로 graph 생성
    n_samples = 100
    x_dummy = np.random.randn(n_samples, 5529)
    drug_indices = np.arange(1127)
    gene_indices = np.arange(1127, 5529)

    print("Creating drug-gene bipartite graph...")
    data = create_drug_gene_bipartite_graph(x_dummy, drug_indices, gene_indices, top_k=10)

    print(f"\nGraph statistics:")
    print(f"  Drug nodes: {data['drug'].x.shape[0]}")
    print(f"  Gene nodes: {data['gene'].x.shape[0]}")
    print(f"  Drug-Gene edges: {data['drug', 'interacts', 'gene'].edge_index.shape[1]}")
    print(f"  Gene-Drug edges: {data['gene', 'rev_interacts', 'drug'].edge_index.shape[1]}")

    print("\n[5] Forward Pass Test")
    print("-" * 80)

    model.eval()
    with torch.no_grad():
        output = model(data)

    print(f"Output shape: {output.shape}")
    print(f"✅ Forward pass successful!")

    print("\n[6] 차별화 요소")
    print("-" * 80)
    print("1. Heterogeneous graph (Drug/Gene 노드 타입 분리)")
    print("2. Graph attention (GAT)")
    print("3. Drug-Gene interaction을 graph 구조로 모델링")
    print("4. Bipartite graph 구조")

    print("\n검증 완료!")
    print("\n⚠️  참고: 실제 학습 시 graph 구성 전략 조정 필요")
    print("   - 현재는 간단한 top-k 방식")
    print("   - Neo4j KG 사용 시 더 풍부한 구조 가능")

    return model, total_params


if __name__ == "__main__":
    verify_hgt_model()
