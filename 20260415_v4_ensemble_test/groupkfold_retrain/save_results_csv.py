"""
GroupKFold 재학습 결과를 CSV로 저장
"""
import pandas as pd
from pathlib import Path

output_dir = Path(__file__).parent

# 결과 데이터
data = [
    {
        'Model': 'CatBoost-Full',
        'GroupKFold_Spearman': 0.5189,
        'Std': 0.0619,
        'RMSE': 2.2787,
        'vs_v3': 0.0279
    },
    {
        'Model': 'CatBoost-Drug',
        'GroupKFold_Spearman': 0.5210,
        'Std': 0.0600,
        'RMSE': 2.2646,
        'vs_v3': 0.0300
    },
    {
        'Model': 'Bilinear-v2',
        'GroupKFold_Spearman': 0.4074,
        'Std': 0.1264,
        'RMSE': 2.8968,
        'vs_v3': -0.0836
    },
    {
        'Model': 'Drug+Bilinear',
        'GroupKFold_Spearman': 0.5145,
        'Std': 0.0,
        'RMSE': 2.3412,
        'vs_v3': 0.0235
    }
]

summary_df = pd.DataFrame(data)

csv_path = output_dir / "groupkfold_retrain_comparison.csv"
summary_df.to_csv(csv_path, index=False)

print(f"✓ CSV saved to: {csv_path}")
print(f"\n{summary_df.to_string(index=False)}")
