"""
SMILES → PyG Graph 변환

RDKit으로 분자 그래프 생성:
- Node features: 원자 종류, 전하, 방향족, 수소 개수 등
- Edge features: 결합 종류 (single/double/triple/aromatic)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import torch
from torch_geometric.data import Data
from rdkit import Chem
from rdkit.Chem import AllChem
import pickle

def get_atom_features(atom):
    """원자 특징 벡터 생성 (44차원)"""
    # 원자 종류 (C, N, O, S, F, Cl, Br, I, P, other) - 10 one-hot
    atom_type = ['C', 'N', 'O', 'S', 'F', 'Cl', 'Br', 'I', 'P']
    atom_symbol = atom.GetSymbol()
    atom_type_enc = [1 if atom_symbol == t else 0 for t in atom_type]
    atom_type_enc.append(1 if atom_symbol not in atom_type else 0)  # other

    # 차수 (degree) - 6 one-hot (0-5)
    degree = min(atom.GetDegree(), 5)
    degree_enc = [1 if degree == i else 0 for i in range(6)]

    # 수소 개수 - 5 one-hot (0-4)
    num_h = min(atom.GetTotalNumHs(), 4)
    num_h_enc = [1 if num_h == i else 0 for i in range(5)]

    # Implicit valence - 6 one-hot (0-5)
    implicit_val = min(atom.GetImplicitValence(), 5)
    implicit_val_enc = [1 if implicit_val == i else 0 for i in range(6)]

    # 추가 특징 (11개)
    features = (
        atom_type_enc +           # 10
        degree_enc +              # 6
        num_h_enc +               # 5
        implicit_val_enc +        # 6
        [atom.GetFormalCharge(),  # 1
         int(atom.GetIsAromatic()), # 1
         atom.GetMass() / 100.0]   # 1 (normalized)
    )

    return features

def get_bond_features(bond):
    """결합 특징 벡터 생성 (6차원)"""
    bond_type = bond.GetBondType()
    bond_type_enc = [
        1 if bond_type == Chem.rdchem.BondType.SINGLE else 0,
        1 if bond_type == Chem.rdchem.BondType.DOUBLE else 0,
        1 if bond_type == Chem.rdchem.BondType.TRIPLE else 0,
        1 if bond_type == Chem.rdchem.BondType.AROMATIC else 0,
    ]

    features = (
        bond_type_enc +           # 4
        [int(bond.GetIsConjugated()),  # 1
         int(bond.IsInRing())]         # 1
    )

    return features

def smiles_to_graph(smiles):
    """SMILES 문자열을 PyG Data 객체로 변환"""
    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        return None

    # 노드 특징
    atom_features = []
    for atom in mol.GetAtoms():
        atom_features.append(get_atom_features(atom))

    x = torch.tensor(atom_features, dtype=torch.float)

    # 엣지 (양방향)
    edge_indices = []
    edge_features = []

    for bond in mol.GetBonds():
        i = bond.GetBeginAtomIdx()
        j = bond.GetEndAtomIdx()

        bond_feat = get_bond_features(bond)

        # 양방향 추가
        edge_indices.append([i, j])
        edge_features.append(bond_feat)
        edge_indices.append([j, i])
        edge_features.append(bond_feat)

    if len(edge_indices) == 0:
        # 단일 원자 분자 (엣지 없음)
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 6), dtype=torch.float)
    else:
        edge_index = torch.tensor(edge_indices, dtype=torch.long).t().contiguous()
        edge_attr = torch.tensor(edge_features, dtype=torch.float)

    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)

    return data

def main():
    print("=" * 100)
    print("SMILES → Graph 변환")
    print("=" * 100)

    # 경로
    step2_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260415_multimodal_pipeline/step2_mpnn")

    # [1] SMILES 로드
    print("\n[1] SMILES 로드")
    print("-" * 100)
    df_smiles = pd.read_csv(step2_dir / "trainable_drugs_with_smiles.csv")
    print(f"✓ 약물 수: {len(df_smiles)}")

    # [2] Graph 변환
    print("\n[2] Graph 변환")
    print("-" * 100)

    drug_graphs = {}
    failed_drugs = []

    for idx, row in df_smiles.iterrows():
        drug_id = str(row['DRUG_ID'])
        smiles = row['SMILES']

        graph = smiles_to_graph(smiles)

        if graph is None:
            failed_drugs.append((drug_id, row['DRUG_NAME']))
            print(f"  ⚠️  Failed: {drug_id} ({row['DRUG_NAME']})")
        else:
            drug_graphs[drug_id] = graph

        if (idx + 1) % 50 == 0:
            print(f"  Processed: {idx + 1}/{len(df_smiles)}")

    print(f"\n✓ 성공: {len(drug_graphs)} / {len(df_smiles)}")
    print(f"✓ 실패: {len(failed_drugs)}")

    if failed_drugs:
        print(f"\n실패 약물 목록:")
        for drug_id, drug_name in failed_drugs:
            print(f"  - {drug_id}: {drug_name}")

    # [3] 통계
    print("\n[3] Graph 통계")
    print("-" * 100)

    num_nodes = [data.x.shape[0] for data in drug_graphs.values()]
    num_edges = [data.edge_index.shape[1] for data in drug_graphs.values()]

    print(f"  - 노드 수 (원자): min={min(num_nodes)}, max={max(num_nodes)}, mean={np.mean(num_nodes):.1f}")
    print(f"  - 엣지 수 (결합×2): min={min(num_edges)}, max={max(num_edges)}, mean={np.mean(num_edges):.1f}")
    print(f"  - 노드 특징 차원: {drug_graphs[list(drug_graphs.keys())[0]].x.shape[1]}")
    print(f"  - 엣지 특징 차원: {drug_graphs[list(drug_graphs.keys())[0]].edge_attr.shape[1] if drug_graphs[list(drug_graphs.keys())[0]].edge_attr.shape[0] > 0 else 6}")

    # [4] 저장
    print("\n[4] 저장")
    print("-" * 100)

    output_path = step2_dir / "drug_graphs.pkl"
    with open(output_path, 'wb') as f:
        pickle.dump(drug_graphs, f)

    print(f"✓ 저장: {output_path}")
    print(f"  - 크기: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

    # 메타데이터 저장
    metadata = {
        'n_drugs': len(drug_graphs),
        'n_failed': len(failed_drugs),
        'node_feature_dim': 40,  # atom features
        'edge_feature_dim': 6,   # bond features
        'failed_drugs': failed_drugs,
        'stats': {
            'num_nodes': {'min': int(min(num_nodes)), 'max': int(max(num_nodes)), 'mean': float(np.mean(num_nodes))},
            'num_edges': {'min': int(min(num_edges)), 'max': int(max(num_edges)), 'mean': float(np.mean(num_edges))}
        }
    }

    import json
    metadata_path = step2_dir / "drug_graphs_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ 메타데이터: {metadata_path}")

    print("\n" + "=" * 100)
    print("✅ Graph 변환 완료!")
    print("=" * 100)

if __name__ == "__main__":
    main()
