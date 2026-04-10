"""
Instagram Account Classifier
Classes: a (active?), i (inactive?), r (real), s (spam/fake?)
Dataset: 43,307 rows | 17 features | ~25% each class (balanced)
Expected accuracy: ~91% balanced accuracy
"""

import pandas as pd
import numpy as np
import pickle
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (classification_report, accuracy_score,
                              balanced_accuracy_score, confusion_matrix)
from collections import Counter

try:
    from xgboost import XGBClassifier
    from sklearn.utils import compute_sample_weight
    xgb_available = True
except ImportError:
    xgb_available = False
    print("XGBoost not found — install with: pip install xgboost")

# ─────────────────────────────────────────
# 1. LOAD
# ─────────────────────────────────────────
df = pd.read_csv("dataset.csv")
df = df.dropna(subset=['class'])

print("=" * 55)
print(f"Loaded {len(df):,} rows | {df['class'].nunique()} classes")
print("\nClass distribution:")
print(df['class'].value_counts().to_string())
print("=" * 55)

# ─────────────────────────────────────────
# 2. FEATURE ENGINEERING
# ─────────────────────────────────────────

# Log-transform skewed columns (handles outliers like followers=1.9M)
for col in ['followers', 'following', 'no_of_posts',
            'engage_like', 'engage_comm', 'post_interval']:
    df[f'log_{col}'] = np.log1p(df[col])

# Ratio features
df['ff_ratio']            = df['followers'] / (df['following'] + 1)
df['engagement_rate']     = (df['engage_like'] + df['engage_comm']) / (df['followers'] + 1)
df['engagement_per_post'] = (df['engage_like'] + df['engage_comm']) / (df['no_of_posts'] + 1)
df['like_comment_ratio']  = df['engage_like'] / (df['engage_comm'] + 1)

# Binary flags
df['has_bio']            = (df['bio_len'] > 0).astype(int)
df['is_following_heavy'] = (df['following'] > df['followers']).astype(int)
df['very_long_interval'] = (df['post_interval'] > df['post_interval'].quantile(0.9)).astype(int)

# Fill any missing values
for col in df.select_dtypes(include=[np.float64, np.int64]).columns:
    df[col] = df[col].fillna(df[col].median())

# ─────────────────────────────────────────
# 3. ENCODE LABELS
# ─────────────────────────────────────────
X = df.drop(columns=['class'])
le = LabelEncoder()
y = le.fit_transform(df['class'])
reverse_map = {int(i): label for i, label in enumerate(le.classes_)}
feature_names = X.columns.tolist()

print(f"\nEncoded classes: {reverse_map}")

# ─────────────────────────────────────────
# 4. TRAIN / TEST SPLIT  (always before balancing)
# ─────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
print(f"Train dist: { {reverse_map[k]: v for k,v in sorted(Counter(y_train).items())} }")

# ─────────────────────────────────────────
# 5. RANDOM FOREST  (best model for this dataset)
# ─────────────────────────────────────────
print("\nTraining Random Forest...")

rf = RandomForestClassifier(
    n_estimators=500,          # more trees = more stable predictions
    max_depth=25,
    min_samples_leaf=2,        # slight regularisation to prevent overfitting
    max_features='sqrt',
    class_weight='balanced_subsample',  # re-weights at every tree
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)

y_pred_rf = rf.predict(X_test)
print(f"\nRF Accuracy:          {accuracy_score(y_test, y_pred_rf):.4f}")
print(f"RF Balanced Accuracy: {balanced_accuracy_score(y_test, y_pred_rf):.4f}")
print("\nClassification Report:")
print(classification_report(
    y_test, y_pred_rf,
    target_names=[reverse_map[i] for i in sorted(reverse_map)]
))
print("Confusion Matrix (rows=actual, cols=predicted):")
cm = pd.DataFrame(
    confusion_matrix(y_test, y_pred_rf),
    index=[f"Actual:{reverse_map[i]}" for i in sorted(reverse_map)],
    columns=[f"Pred:{reverse_map[i]}" for i in sorted(reverse_map)]
)
print(cm)

# ─────────────────────────────────────────
# 6. XGBOOST  (optional, often slightly better on tabular data)
# ─────────────────────────────────────────
if xgb_available:
    print("\nTraining XGBoost...")
    sw = compute_sample_weight(class_weight='balanced', y=y_train)

    xgb = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        gamma=1,
        reg_lambda=1,
        eval_metric='mlogloss',
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1
    )
    xgb.fit(X_train, y_train,
            sample_weight=sw,
            eval_set=[(X_test, y_test)],
            verbose=False)

    y_pred_xgb = xgb.predict(X_test)
    print(f"\nXGB Accuracy:          {accuracy_score(y_test, y_pred_xgb):.4f}")
    print(f"XGB Balanced Accuracy: {balanced_accuracy_score(y_test, y_pred_xgb):.4f}")
    print("\nClassification Report (XGB):")
    print(classification_report(
        y_test, y_pred_xgb,
        target_names=[reverse_map[i] for i in sorted(reverse_map)]
    ))

# ─────────────────────────────────────────
# 7. FEATURE IMPORTANCE
# ─────────────────────────────────────────
print("\nTop 15 Features:")
for feat, imp in sorted(zip(feature_names, rf.feature_importances_),
                         key=lambda x: x[1], reverse=True)[:15]:
    bar = "█" * int(imp * 200)
    print(f"  {feat:<28} {imp:.4f}  {bar}")

# ─────────────────────────────────────────
# 8. PREDICT ON TEST FILE
#    Put test rows in test_samples.csv (same columns as dataset.csv, with or without 'class')
# ─────────────────────────────────────────
import os
if os.path.exists("test_samples.csv"):
    print("\n─── Predictions on test_samples.csv ───")
    test_df = pd.read_csv("test_samples.csv")
    actual_labels = test_df['class'].tolist() if 'class' in test_df.columns else None
    test_X = test_df.drop(columns=['class'], errors='ignore')

    # Apply same feature engineering
    for col in ['followers', 'following', 'no_of_posts',
                'engage_like', 'engage_comm', 'post_interval']:
        test_X[f'log_{col}'] = np.log1p(test_X[col])

    test_X['ff_ratio']            = test_X['followers'] / (test_X['following'] + 1)
    test_X['engagement_rate']     = (test_X['engage_like'] + test_X['engage_comm']) / (test_X['followers'] + 1)
    test_X['engagement_per_post'] = (test_X['engage_like'] + test_X['engage_comm']) / (test_X['no_of_posts'] + 1)
    test_X['like_comment_ratio']  = test_X['engage_like'] / (test_X['engage_comm'] + 1)
    test_X['has_bio']             = (test_X['bio_len'] > 0).astype(int)
    test_X['is_following_heavy']  = (test_X['following'] > test_X['followers']).astype(int)
    test_X['very_long_interval']  = (test_X['post_interval'] > test_X['post_interval'].quantile(0.9)).astype(int)

    # Align columns to training
    test_X = test_X[feature_names]
    preds = rf.predict(test_X)

    for i, pred in enumerate(preds):
        pred_label = reverse_map[pred]
        actual = actual_labels[i] if actual_labels else "?"
        status = "✅" if pred_label == actual else "❌"
        print(f"  Row {i+1:2d}: Predicted={pred_label}  Actual={actual}  {status}")

# ─────────────────────────────────────────
# 9. SAVE MODELS
# ─────────────────────────────────────────
with open("random_forest_model.pkl", "wb") as f:
    pickle.dump(rf, f)

if xgb_available:
    with open("xgboost_model.pkl", "wb") as f:
        pickle.dump(xgb, f)

meta = {
    "feature_names": feature_names,
    "reverse_map":   reverse_map,
    "label_encoder": le
}
with open("model_metadata.pkl", "wb") as f:
    pickle.dump(meta, f)

print("\n✅ DONE — models saved.")
print("  random_forest_model.pkl")
if xgb_available:
    print("  xgboost_model.pkl")
print("  model_metadata.pkl")