"""
DrugMPNN 학습 (5-Fold CV + Holdout)

학습 조건:
- seed=42
- 5-fold CV on 80% train
- 20% holdout
- OOF/Holdout predictions 저장
"""
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch_geometric.data import Data, Batch
from sklearn.model_selection import KFold
from scipy.stats import spearmanr
from pathlib import Path
import pickle
import json
import time

from mpnn_model import DrugMPNN

# Device
device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
print(f"Device: {device}")

class DrugGeneDataset(Dataset):
    def __init__(self, drug_ids, gene_features, targets, drug_graphs):
        """
        Args:
            drug_ids: List[str] - drug IDs
            gene_features: np.array [n_samples, n_gene_features]
            targets: np.array [n_samples]
            drug_graphs: dict - {drug_id: PyG Data}
        """
        self.drug_ids = drug_ids
        self.gene_features = torch.tensor(gene_features, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.float32).unsqueeze(1)
        self.drug_graphs = drug_graphs

    def __len__(self):
        return len(self.drug_ids)

    def __getitem__(self, idx):
        drug_id = self.drug_ids[idx]
        graph = self.drug_graphs[drug_id]
        gene_feat = self.gene_features[idx]
        target = self.targets[idx]

        return graph, gene_feat, target

def collate_fn(batch):
    """Custom collate for batching graphs"""
    graphs, gene_feats, targets = zip(*batch)

    # Batch graphs
    graph_batch = Batch.from_data_list(graphs)

    # Stack gene features and targets
    gene_batch = torch.stack(gene_feats)
    target_batch = torch.stack(targets)

    return graph_batch, gene_batch, target_batch

def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    all_preds = []
    all_targets = []

    for graph_batch, gene_batch, target_batch in loader:
        graph_batch = graph_batch.to(device)
        gene_batch = gene_batch.to(device)
        target_batch = target_batch.to(device)

        optimizer.zero_grad()
        preds = model(graph_batch, gene_batch)
        loss = criterion(preds, target_batch)

        loss.backward()
        optimizer.step()

        total_loss += loss.item() * len(target_batch)
        all_preds.append(preds.detach().cpu().numpy())
        all_targets.append(target_batch.cpu().numpy())

    avg_loss = total_loss / len(loader.dataset)
    all_preds = np.concatenate(all_preds)
    all_targets = np.concatenate(all_targets)

    return avg_loss, all_preds, all_targets

def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for graph_batch, gene_batch, target_batch in loader:
            graph_batch = graph_batch.to(device)
            gene_batch = gene_batch.to(device)
            target_batch = target_batch.to(device)

            preds = model(graph_batch, gene_batch)
            loss = criterion(preds, target_batch)

            total_loss += loss.item() * len(target_batch)
            all_preds.append(preds.cpu().numpy())
            all_targets.append(target_batch.cpu().numpy())

    avg_loss = total_loss / len(loader.dataset)
    all_preds = np.concatenate(all_preds)
    all_targets = np.concatenate(all_targets)

    return avg_loss, all_preds, all_targets

def main():
    print("=" * 100)
    print("DrugMPNN 학습 (5-Fold CV + Holdout)")
    print("=" * 100)

    # 경로
    step2_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260415_multimodal_pipeline/step2_mpnn")

    # [1] 데이터 로드
    print("\n[1] 데이터 로드")
    print("-" * 100)

    # Drug graphs
    with open(step2_dir / "drug_graphs.pkl", 'rb') as f:
        drug_graphs = pickle.load(f)
    print(f"✓ Drug graphs: {len(drug_graphs)}")

    # Chemprop input (for gene features and targets)
    df = pd.read_csv(step2_dir / "chemprop_input.csv")
    print(f"✓ Data shape: {df.shape}")

    # Drug IDs from features_slim
    v3_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3")
    df_features = pd.read_parquet(v3_dir / "features_slim.parquet")
    drug_ids = df_features['canonical_drug_id'].values  # str type
    print(f"✓ Drug IDs: {len(drug_ids)}")

    # Gene features (gene_0 ~ gene_4414)
    gene_cols = [col for col in df.columns if col.startswith('gene_')]
    gene_features = df[gene_cols].values
    print(f"✓ Gene features: {gene_features.shape}")

    # Targets
    targets = df['target'].values
    print(f"✓ Targets: {targets.shape}")

    # [2] Train/Holdout Split (80/20, seed=42)
    print("\n[2] Train/Holdout Split")
    print("-" * 100)

    np.random.seed(42)
    n_samples = len(df)
    indices = np.arange(n_samples)
    np.random.shuffle(indices)

    n_train = int(0.8 * n_samples)
    train_idx = indices[:n_train]
    holdout_idx = indices[n_train:]

    print(f"  - Train: {len(train_idx)}")
    print(f"  - Holdout: {len(holdout_idx)}")

    # [3] 5-Fold CV
    print("\n[3] 5-Fold Cross-Validation")
    print("-" * 100)

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_preds = np.zeros(len(train_idx))
    oof_targets = targets[train_idx]

    fold_metrics = []

    for fold_idx, (train_fold_idx, val_fold_idx) in enumerate(kf.split(train_idx), 1):
        print(f"\n--- Fold {fold_idx}/5 ---")

        # Fold 데이터
        fold_train_idx = train_idx[train_fold_idx]
        fold_val_idx = train_idx[val_fold_idx]

        # Dataset
        train_dataset = DrugGeneDataset(
            drug_ids[fold_train_idx],
            gene_features[fold_train_idx],
            targets[fold_train_idx],
            drug_graphs
        )

        val_dataset = DrugGeneDataset(
            drug_ids[fold_val_idx],
            gene_features[fold_val_idx],
            targets[fold_val_idx],
            drug_graphs
        )

        # DataLoader
        train_loader = DataLoader(
            train_dataset,
            batch_size=64,
            shuffle=True,
            collate_fn=collate_fn,
            num_workers=0  # macOS MPS issue
        )

        val_loader = DataLoader(
            val_dataset,
            batch_size=64,
            shuffle=False,
            collate_fn=collate_fn,
            num_workers=0
        )

        # Model
        model = DrugMPNN(
            node_feature_dim=30,
            edge_feature_dim=6,
            gene_feature_dim=gene_features.shape[1],
            hidden_dim=128,
            gnn_layers=3,
            dropout=0.1
        ).to(device)

        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)

        # Training
        print(f"  Train: {len(train_dataset)}, Val: {len(val_dataset)}")

        best_val_sp = -1
        best_val_preds = None
        patience = 10
        patience_counter = 0

        start_time = time.time()

        for epoch in range(1, 101):  # max 100 epochs
            train_loss, train_preds, train_targets = train_epoch(
                model, train_loader, criterion, optimizer, device
            )

            val_loss, val_preds, val_targets = evaluate(
                model, val_loader, criterion, device
            )

            # Metrics
            val_sp = spearmanr(val_targets, val_preds)[0]
            val_rmse = np.sqrt(np.mean((val_targets - val_preds) ** 2))

            if epoch % 10 == 0 or epoch == 1:
                print(f"    Epoch {epoch:3d}: Train Loss={train_loss:.4f}, Val Loss={val_loss:.4f}, Val Sp={val_sp:.4f}, Val RMSE={val_rmse:.4f}")

            # Early stopping
            if val_sp > best_val_sp:
                best_val_sp = val_sp
                best_val_preds = val_preds.copy()
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= patience:
                print(f"    Early stopping at epoch {epoch}")
                break

        training_time = time.time() - start_time

        # OOF 저장
        oof_preds[val_fold_idx] = best_val_preds.flatten()

        # Fold 평가
        fold_sp = spearmanr(targets[fold_val_idx], best_val_preds)[0]
        fold_rmse = np.sqrt(np.mean((targets[fold_val_idx] - best_val_preds) ** 2))

        print(f"  Best Val Spearman: {fold_sp:.4f}")
        print(f"  Best Val RMSE: {fold_rmse:.4f}")
        print(f"  Training time: {training_time:.1f}s")

        fold_metrics.append({
            'fold': fold_idx,
            'spearman': float(fold_sp),
            'rmse': float(fold_rmse),
            'training_time': training_time
        })

    # OOF 평가
    print(f"\n--- OOF 전체 평가 ---")
    oof_sp = spearmanr(oof_targets, oof_preds)[0]
    oof_rmse = np.sqrt(np.mean((oof_targets - oof_preds) ** 2))
    print(f"  OOF Spearman: {oof_sp:.4f}")
    print(f"  OOF RMSE: {oof_rmse:.4f}")

    # OOF 저장
    oof_save_path = step2_dir / "mpnn_oof.npy"
    np.save(oof_save_path, oof_preds)
    print(f"  ✓ OOF saved: {oof_save_path}")

    # [4] Final Model on Full Train
    print("\n[4] Final Model Training (Full Train)")
    print("-" * 100)

    # Full train dataset
    full_train_dataset = DrugGeneDataset(
        drug_ids[train_idx],
        gene_features[train_idx],
        targets[train_idx],
        drug_graphs
    )

    holdout_dataset = DrugGeneDataset(
        drug_ids[holdout_idx],
        gene_features[holdout_idx],
        targets[holdout_idx],
        drug_graphs
    )

    full_train_loader = DataLoader(
        full_train_dataset,
        batch_size=64,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0
    )

    holdout_loader = DataLoader(
        holdout_dataset,
        batch_size=64,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0
    )

    # Final model
    final_model = DrugMPNN(
        node_feature_dim=30,
        edge_feature_dim=6,
        gene_feature_dim=gene_features.shape[1],
        hidden_dim=128,
        gnn_layers=3,
        dropout=0.1
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = optim.Adam(final_model.parameters(), lr=1e-3, weight_decay=1e-5)

    print(f"  Training on {len(full_train_dataset)} samples...")

    best_train_loss = float('inf')
    patience = 10
    patience_counter = 0

    start_time = time.time()

    for epoch in range(1, 101):
        train_loss, train_preds, train_targets = train_epoch(
            final_model, full_train_loader, criterion, optimizer, device
        )

        if epoch % 10 == 0 or epoch == 1:
            print(f"    Epoch {epoch:3d}: Train Loss={train_loss:.4f}")

        # Early stopping based on train loss
        if train_loss < best_train_loss:
            best_train_loss = train_loss
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= patience:
            print(f"    Early stopping at epoch {epoch}")
            break

    final_training_time = time.time() - start_time
    print(f"  Training time: {final_training_time:.1f}s")

    # Holdout prediction
    print(f"\n  Predicting on holdout...")
    holdout_loss, holdout_preds, holdout_targets = evaluate(
        final_model, holdout_loader, criterion, device
    )

    holdout_sp = spearmanr(holdout_targets, holdout_preds)[0]
    holdout_rmse = np.sqrt(np.mean((holdout_targets - holdout_preds) ** 2))

    print(f"  Holdout Spearman: {holdout_sp:.4f}")
    print(f"  Holdout RMSE: {holdout_rmse:.4f}")

    # Holdout 저장
    holdout_save_path = step2_dir / "mpnn_holdout.npy"
    np.save(holdout_save_path, holdout_preds.flatten())
    print(f"  ✓ Holdout saved: {holdout_save_path}")

    # Model 저장
    model_save_path = step2_dir / "mpnn_final_model.pt"
    torch.save(final_model.state_dict(), model_save_path)
    print(f"  ✓ Model saved: {model_save_path}")

    # [5] 학습 로그 저장
    print("\n[5] 학습 로그 저장")
    print("-" * 100)

    log = {
        'experiment': {
            'date': time.strftime('%Y-%m-%d'),
            'model': 'DrugMPNN (PyG)',
            'n_samples_total': n_samples,
            'n_train': len(train_idx),
            'n_holdout': len(holdout_idx),
            'n_drugs': len(drug_graphs),
            'n_gene_features': gene_features.shape[1],
            'seed': 42,
            'device': str(device)
        },
        'model_config': {
            'node_feature_dim': 30,
            'edge_feature_dim': 6,
            'hidden_dim': 128,
            'gnn_layers': 3,
            'dropout': 0.1,
            'total_parameters': sum(p.numel() for p in final_model.parameters())
        },
        'training': {
            'batch_size': 64,
            'max_epochs': 100,
            'learning_rate': 1e-3,
            'weight_decay': 1e-5,
            'early_stopping_patience': 10
        },
        'cv': {
            'n_folds': 5,
            'fold_metrics': fold_metrics,
            'oof_spearman': float(oof_sp),
            'oof_rmse': float(oof_rmse),
            'mean_fold_spearman': float(np.mean([f['spearman'] for f in fold_metrics])),
            'std_fold_spearman': float(np.std([f['spearman'] for f in fold_metrics]))
        },
        'holdout': {
            'spearman': float(holdout_sp),
            'rmse': float(holdout_rmse)
        },
        'gap': {
            'train_oof_gap': None,  # Will compute later
            'holdout_oof_gap': float(holdout_sp - oof_sp)
        }
    }

    log_path = step2_dir / "mpnn_train_log.json"
    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2)
    print(f"✓ Log saved: {log_path}")

    print("\n" + "=" * 100)
    print("✅ DrugMPNN 학습 완료!")
    print("=" * 100)
    print(f"  - OOF Spearman: {oof_sp:.4f} ± {np.std([f['spearman'] for f in fold_metrics]):.4f}")
    print(f"  - Holdout Spearman: {holdout_sp:.4f}")
    print(f"  - Holdout RMSE: {holdout_rmse:.4f}")
    print(f"  - OOF saved: {oof_save_path}")
    print(f"  - Holdout saved: {holdout_save_path}")
    print(f"  - Model saved: {model_save_path}")

if __name__ == "__main__":
    main()
