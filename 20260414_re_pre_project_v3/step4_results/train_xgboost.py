import numpy as np
import json
from sklearn.model_selection import KFold, train_test_split
from sklearn.metrics import mean_squared_error
from scipy.stats import spearmanr
import xgboost as xgb
import time
import warnings
warnings.filterwarnings("ignore")

print("="*80)
print("Model 3/15: XGBoost (CPU)")
print("="*80)

X = np.load("X_train.npy")
y = np.load("y_train.npy")
X_train, X_holdout, y_train, y_holdout = train_test_split(X, y, test_size=0.2, random_state=42)

kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_predictions = np.zeros(len(y_train))

for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X_train), 1):
    X_tr, X_val = X_train[train_idx], X_train[val_idx]
    y_tr, y_val = y_train[train_idx], y_train[val_idx]
    
    model = xgb.XGBRegressor(random_state=42, verbosity=0)
    t0 = time.time()
    model.fit(X_tr, y_tr)
    
    y_val_pred = model.predict(X_val)
    oof_predictions[val_idx] = y_val_pred
    
    val_sp, _ = spearmanr(y_val, y_val_pred)
    val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
    print(f"Fold {fold_idx}/5: Sp={val_sp:.4f}, RMSE={val_rmse:.4f}, Time={time.time()-t0:.1f}s")

oof_sp, _ = spearmanr(y_train, oof_predictions)
oof_rmse = np.sqrt(mean_squared_error(y_train, oof_predictions))

model_final = xgb.XGBRegressor(random_state=42, verbosity=0)
model_final.fit(X_train, y_train)
y_holdout_pred = model_final.predict(X_holdout)
holdout_sp, _ = spearmanr(y_holdout, y_holdout_pred)
holdout_rmse = np.sqrt(mean_squared_error(y_holdout, y_holdout_pred))

ensemble_pass = (oof_sp >= 0.713) and (oof_rmse <= 1.385)
print(f"OOF: Sp={oof_sp:.4f}, RMSE={oof_rmse:.4f}")
print(f"Holdout: Sp={holdout_sp:.4f}, RMSE={holdout_rmse:.4f}")
print(f"Ensemble: {'✓ PASS' if ensemble_pass else '✗ FAIL'}")

with open("model_03_xgboost.json", "w") as f:
    json.dump({"model": "XGBoost", "oof_spearman": float(oof_sp), "oof_rmse": float(oof_rmse),
               "holdout_spearman": float(holdout_sp), "holdout_rmse": float(holdout_rmse),
               "ensemble_pass": bool(ensemble_pass)}, f, indent=2)
print("✓ XGBoost 완료")
