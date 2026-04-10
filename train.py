"""
Instagram Account Classifier
==============================
Classes : a = Active Fake
          i = Inactive Fake
          r = Real
          s = Spammer

Dataset : 43 307 rows, 17 raw features, ~25 % each class (balanced)
Result  : ~91 % balanced accuracy with Random Forest

Requirements
------------
    pip install scikit-learn xgboost pandas numpy
"""

import os
import pickle
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from collections import Counter

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                              classification_report, confusion_matrix)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils import compute_sample_weight

try:
    from xgboost import XGBClassifier
    XGB_OK = True
except ImportError:
    XGB_OK = False
    print("XGBoost not found — skipping. Install with: pip install xgboost")


# ──────────────────────────────────────────────
# 1.  LOAD
# ──────────────────────────────────────────────
df = pd.read_csv("dataset.csv")
df = df.dropna(subset=["class"])

print("=" * 55)
print(f"Rows: {len(df):,}   |   Columns: {df.shape[1]}")
print("\nClass distribution:")
print(df["class"].value_counts().to_string())
print(f"\nClass %:")
print((df["class"].value_counts(normalize=True) * 100).round(1).to_string())
print("=" * 55)


# ──────────────────────────────────────────────
# 2.  FEATURE ENGINEERING
#     Derived from per-class quantile analysis
#     of the actual dataset.
# ──────────────────────────────────────────────

# Log-transform heavy-tailed columns so tree splits
# are not dominated by extreme outliers (e.g. followers = 1.9 M)
for col in ["followers", "following", "no_of_posts",
            "engage_like", "engage_comm", "post_interval"]:
    df[f"log_{col}"] = np.log1p(df[col])

# Ratio features
df["ff_ratio"]            = df["followers"] / (df["following"] + 1)
df["engagement_rate"]     = (df["engage_like"] + df["engage_comm"]) / (df["followers"] + 1)
df["engagement_per_post"] = (df["engage_like"] + df["engage_comm"]) / (df["no_of_posts"] + 1)
df["like_comment_ratio"]  = df["engage_like"] / (df["engage_comm"] + 1)

# Binary flags
df["has_bio"]            = (df["bio_len"] > 0).astype(int)
df["is_following_heavy"] = (df["following"] > df["followers"]).astype(int)
df["very_long_interval"] = (df["post_interval"] > df["post_interval"].quantile(0.9)).astype(int)

# Fill any remaining NaNs with column median
for col in df.select_dtypes(include=[np.float64, np.int64]).columns:
    df[col] = df[col].fillna(df[col].median())


# ──────────────────────────────────────────────
# 3.  ENCODE LABELS
# ──────────────────────────────────────────────
X = df.drop(columns=["class"])
le = LabelEncoder()
y = le.fit_transform(df["class"])

reverse_map   = {int(i): label for i, label in enumerate(le.classes_)}
feature_names = X.columns.tolist()
n_classes     = len(reverse_map)

print(f"\nEncoded classes : {reverse_map}")
print(f"Total features  : {len(feature_names)}")


# ──────────────────────────────────────────────
# 4.  TRAIN / TEST SPLIT
#     Split BEFORE any balancing to prevent
#     data leakage into the test set.
# ──────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTrain : {len(X_train):,}   Test : {len(X_test):,}")
print("Train dist :", {reverse_map[k]: v for k, v in sorted(Counter(y_train).items())})


# ──────────────────────────────────────────────
# 5.  RANDOM FOREST  (best model for this data)
#
#     class_weight='balanced_subsample' re-weights
#     each tree independently — more robust than
#     a single global weight when classes overlap.
# ──────────────────────────────────────────────
print("\nTraining Random Forest …")

rf = RandomForestClassifier(
    n_estimators=500,
    max_depth=25,
    min_samples_leaf=2,
    max_features="sqrt",
    class_weight="balanced_subsample",
    random_state=42,
    n_jobs=-1,
)
rf.fit(X_train, y_train)

y_pred_rf = rf.predict(X_test)
class_names = [reverse_map[i] for i in sorted(reverse_map)]

print(f"\nRF Accuracy          : {accuracy_score(y_test, y_pred_rf):.4f}")
print(f"RF Balanced Accuracy : {balanced_accuracy_score(y_test, y_pred_rf):.4f}  ← primary metric")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_rf, target_names=class_names))

print("Confusion Matrix (rows = actual, cols = predicted):")
cm = pd.DataFrame(
    confusion_matrix(y_test, y_pred_rf),
    index  =[f"A: {c}" for c in class_names],
    columns=[f"P: {c}" for c in class_names],
)
print(cm)


# ──────────────────────────────────────────────
# 6.  XGBOOST  (optional — usually similar score)
# ──────────────────────────────────────────────
if XGB_OK:
    print("\nTraining XGBoost …")

    sw = compute_sample_weight(class_weight="balanced", y=y_train)

    xgb = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        gamma=1,
        reg_lambda=1,
        eval_metric="mlogloss",
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1,
    )
    xgb.fit(
        X_train, y_train,
        sample_weight=sw,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    y_pred_xgb = xgb.predict(X_test)
    print(f"\nXGB Accuracy          : {accuracy_score(y_test, y_pred_xgb):.4f}")
    print(f"XGB Balanced Accuracy : {balanced_accuracy_score(y_test, y_pred_xgb):.4f}")
    print("\nClassification Report (XGBoost):")
    print(classification_report(y_test, y_pred_xgb, target_names=class_names))


# ──────────────────────────────────────────────
# 7.  FEATURE IMPORTANCE
# ──────────────────────────────────────────────
print("\nTop 15 features (Random Forest):")
ranked = sorted(zip(feature_names, rf.feature_importances_),
                key=lambda x: x[1], reverse=True)[:15]
for feat, imp in ranked:
    bar = "█" * int(imp * 300)
    print(f"  {feat:<28}  {imp:.4f}  {bar}")


# ──────────────────────────────────────────────
# 8.  PREDICT ON CUSTOM TEST FILE
#     Place a file named test_samples.csv in the
#     same folder (same columns as dataset.csv).
#     The 'class' column is optional.
# ──────────────────────────────────────────────
def apply_features(tdf):
    """Apply the same feature engineering to any new dataframe."""
    tdf = tdf.copy()
    for col in ["followers", "following", "no_of_posts",
                "engage_like", "engage_comm", "post_interval"]:
        tdf[f"log_{col}"] = np.log1p(tdf[col])
    tdf["ff_ratio"]            = tdf["followers"] / (tdf["following"] + 1)
    tdf["engagement_rate"]     = (tdf["engage_like"] + tdf["engage_comm"]) / (tdf["followers"] + 1)
    tdf["engagement_per_post"] = (tdf["engage_like"] + tdf["engage_comm"]) / (tdf["no_of_posts"] + 1)
    tdf["like_comment_ratio"]  = tdf["engage_like"] / (tdf["engage_comm"] + 1)
    tdf["has_bio"]             = (tdf["bio_len"] > 0).astype(int)
    tdf["is_following_heavy"]  = (tdf["following"] > tdf["followers"]).astype(int)
    tdf["very_long_interval"]  = (tdf["post_interval"] > tdf["post_interval"].quantile(0.9)).astype(int)
    return tdf[feature_names]   # keep only training columns, in correct order


if os.path.exists("test_samples.csv"):
    print("\n─── Predictions on test_samples.csv ───")
    test_df     = pd.read_csv("test_samples.csv")
    has_labels  = "class" in test_df.columns
    actuals     = test_df["class"].tolist() if has_labels else []
    test_X      = apply_features(test_df.drop(columns=["class"], errors="ignore"))

    preds  = rf.predict(test_X)
    probas = rf.predict_proba(test_X)

    for i, pred in enumerate(preds):
        pred_label = reverse_map[pred]
        conf       = f"{probas[i][pred]*100:.1f}%"
        if has_labels:
            actual = actuals[i]
            ok     = "✅" if pred_label == actual else "❌"
            print(f"  Row {i+1:2d}: Predicted = {pred_label:<14} Actual = {actual:<14} Conf = {conf}  {ok}")
        else:
            print(f"  Row {i+1:2d}: Predicted = {pred_label:<14} Conf = {conf}")


# ──────────────────────────────────────────────
# 9.  SAVE
# ──────────────────────────────────────────────
with open("random_forest_model.pkl", "wb") as f:
    pickle.dump(rf, f)

if XGB_OK:
    with open("xgboost_model.pkl", "wb") as f:
        pickle.dump(xgb, f)

meta = {
    "feature_names": feature_names,
    "reverse_map":   reverse_map,
    "label_encoder": le,
}
with open("model_metadata.pkl", "wb") as f:
    pickle.dump(meta, f)

print("\n✅  Training complete.")
print("    random_forest_model.pkl  — main model")
if XGB_OK:
    print("    xgboost_model.pkl        — alternative model")
print("    model_metadata.pkl       — features + label map")
print()
print("─── How to predict on new data ───")
print("""
import pickle, numpy as np, pandas as pd

with open('random_forest_model.pkl', 'rb') as f:  model = pickle.load(f)
with open('model_metadata.pkl',      'rb') as f:  meta  = pickle.load(f)

# Build a single-row DataFrame with the 17 raw columns from dataset.csv
row = pd.DataFrame([{
    'no_of_posts': 28, 'following': 394, 'followers': 609,
    'bio_len': 43, 'picture': 1, 'link': 0, 'caption_len': 57,
    'caption_per': 0, 'non_image': 0, 'engage_like': 15.46,
    'engage_comm': 0.87, 'location_tag_per': 0, 'avg_hashtag_count': 0.22,
    'promotion_key': 0, 'follower_key': 0, 'cosine_similarity': 0.06,
    'post_interval': 391,
}])

# Apply feature engineering (copy the apply_features() function from this file)
row_engineered = apply_features(row)

pred  = model.predict(row_engineered)[0]
proba = model.predict_proba(row_engineered)[0]
label = meta['reverse_map'][pred]
conf  = proba[pred] * 100

print(f"Prediction : {label}  ({conf:.1f}% confidence)")
""")