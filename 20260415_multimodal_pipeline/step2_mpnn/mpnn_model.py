"""
DrugMPNN 모델

구조:
- SMILES graph → GNN layers → drug_embedding (128dim)
- Gene features → Gene encoder → gene_embedding (128dim)
- drug_embedding + gene_embedding → prediction head → IC50
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool, global_max_pool

class DrugMPNN(nn.Module):
    def __init__(
        self,
        node_feature_dim=30,
        edge_feature_dim=6,
        gene_feature_dim=4415,
        hidden_dim=128,
        gnn_layers=3,
        dropout=0.1
    ):
        super(DrugMPNN, self).__init__()

        self.node_feature_dim = node_feature_dim
        self.edge_feature_dim = edge_feature_dim
        self.gene_feature_dim = gene_feature_dim
        self.hidden_dim = hidden_dim
        self.gnn_layers = gnn_layers
        self.dropout = dropout

        # === Drug GNN (SMILES → drug_embedding) ===

        # Initial node embedding
        self.node_embedding = nn.Linear(node_feature_dim, hidden_dim)

        # GNN layers (GCNConv)
        self.gnn_convs = nn.ModuleList()
        self.gnn_bns = nn.ModuleList()

        for i in range(gnn_layers):
            self.gnn_convs.append(GCNConv(hidden_dim, hidden_dim))
            self.gnn_bns.append(nn.BatchNorm1d(hidden_dim))

        # Graph readout: mean + max pooling
        # Output: 2 * hidden_dim
        self.drug_projection = nn.Sequential(
            nn.Linear(2 * hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim)  # Final drug_embedding: 128dim
        )

        # === Gene Encoder (gene features → gene_embedding) ===

        self.gene_encoder = nn.Sequential(
            nn.Linear(gene_feature_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, hidden_dim),  # gene_embedding: 128dim
            nn.ReLU()
        )

        # === Prediction Head (drug + gene → IC50) ===

        self.prediction_head = nn.Sequential(
            nn.Linear(2 * hidden_dim, hidden_dim),  # 256 → 128
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)  # IC50 prediction
        )

    def forward(self, graph_batch, gene_features):
        """
        Args:
            graph_batch: PyG Batch object (drug graphs)
            gene_features: Tensor [batch_size, gene_feature_dim]

        Returns:
            predictions: Tensor [batch_size, 1]
        """
        # === Drug GNN ===

        # Node embedding
        x = self.node_embedding(graph_batch.x)  # [num_nodes, hidden_dim]
        x = F.relu(x)

        # GNN layers
        for i in range(self.gnn_layers):
            x_new = self.gnn_convs[i](x, graph_batch.edge_index)
            x_new = self.gnn_bns[i](x_new)
            x_new = F.relu(x_new)
            x_new = F.dropout(x_new, p=self.dropout, training=self.training)

            # Residual connection
            if i > 0:
                x = x + x_new
            else:
                x = x_new

        # Global pooling (mean + max)
        mean_pool = global_mean_pool(x, graph_batch.batch)  # [batch_size, hidden_dim]
        max_pool = global_max_pool(x, graph_batch.batch)    # [batch_size, hidden_dim]
        graph_repr = torch.cat([mean_pool, max_pool], dim=1)  # [batch_size, 2*hidden_dim]

        # Drug embedding
        drug_embedding = self.drug_projection(graph_repr)  # [batch_size, hidden_dim]

        # === Gene Encoder ===

        gene_embedding = self.gene_encoder(gene_features)  # [batch_size, hidden_dim]

        # === Fusion ===

        combined = torch.cat([drug_embedding, gene_embedding], dim=1)  # [batch_size, 2*hidden_dim]

        # === Prediction ===

        predictions = self.prediction_head(combined)  # [batch_size, 1]

        return predictions

    def get_embeddings(self, graph_batch, gene_features):
        """
        Get drug and gene embeddings (for analysis)

        Returns:
            drug_embedding: [batch_size, hidden_dim]
            gene_embedding: [batch_size, hidden_dim]
        """
        with torch.no_grad():
            # Drug GNN
            x = self.node_embedding(graph_batch.x)
            x = F.relu(x)

            for i in range(self.gnn_layers):
                x_new = self.gnn_convs[i](x, graph_batch.edge_index)
                x_new = self.gnn_bns[i](x_new)
                x_new = F.relu(x_new)

                if i > 0:
                    x = x + x_new
                else:
                    x = x_new

            mean_pool = global_mean_pool(x, graph_batch.batch)
            max_pool = global_max_pool(x, graph_batch.batch)
            graph_repr = torch.cat([mean_pool, max_pool], dim=1)

            drug_embedding = self.drug_projection(graph_repr)

            # Gene encoder
            gene_embedding = self.gene_encoder(gene_features)

        return drug_embedding, gene_embedding


if __name__ == "__main__":
    # 모델 테스트
    print("=" * 100)
    print("DrugMPNN 모델 테스트")
    print("=" * 100)

    model = DrugMPNN(
        node_feature_dim=30,
        edge_feature_dim=6,
        gene_feature_dim=4415,
        hidden_dim=128,
        gnn_layers=3,
        dropout=0.1
    )

    print(f"\n모델 구조:")
    print(model)

    print(f"\n파라미터 수:")
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  - Total: {total_params:,}")
    print(f"  - Trainable: {trainable_params:,}")

    # 각 모듈별 파라미터
    print(f"\n모듈별 파라미터:")
    for name, module in model.named_children():
        n_params = sum(p.numel() for p in module.parameters())
        print(f"  - {name}: {n_params:,}")

    print("\n✅ 모델 테스트 완료!")
