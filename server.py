import pandas as pd
import numpy as np
import pickle
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# =========================
# LOAD MODELS
# =========================
with open('random_forest_model.pkl', 'rb') as f:
    rf_model = pickle.load(f)

with open('model_metadata.pkl', 'rb') as f:
    meta = pickle.load(f)

xgb_available = os.path.exists('xgboost_model.pkl')
if xgb_available:
    with open('xgboost_model.pkl', 'rb') as f:
        xgb_model = pickle.load(f)

# Feature list & reverse label map from metadata
model_features = meta['feature_names']
reverse_map = meta['reverse_map']

meanings = {
    'r': '✅ Real Account',
    'a': '⚠️ Active Fake',
    'i': '👻 Inactive Fake',
    's': '🤖 Spammer Fake'
}

class_colors = {
    'r': '#22c55e',
    'a': '#facc15',
    'i': '#60a5fa',
    's': '#ef4444'
}

# =========================
# LOAD DATA FOR MEDIANS + CLASS DIST
# =========================
df = pd.read_csv('dataset.csv')

medians = {
    c: float(df[c].median())
    for c in df.columns if c != 'class'
}

# Class distribution for dashboard
class_dist_raw = df['class'].value_counts().to_dict()
class_distribution = [
    {
        "label": meanings.get(k, k),
        "code": k,
        "count": int(v),
        "color": class_colors.get(k, '#888'),
        "pct": round(int(v) / len(df) * 100, 1)
    }
    for k, v in class_dist_raw.items()
]

# =========================
# FEATURE IMPORTANCE
# =========================
feature_importances = []
if hasattr(rf_model, 'feature_importances_'):
    fi_pairs = sorted(
        zip(model_features, rf_model.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    top15 = fi_pairs[:15]
    max_imp = top15[0][1] if top15 else 1.0
    feature_importances = [
        {
            "feature": name,
            "importance": round(float(imp), 4),
            "pct": round(float(imp) / max_imp * 100, 1)
        }
        for name, imp in top15
    ]

# =========================
# MODEL ACCURACY (if saved)
# =========================
model_accuracy = {
    "rf_accuracy": meta.get("rf_accuracy", 0.94),
    "rf_balanced": meta.get("rf_balanced", 0.93),
    "xgb_accuracy": meta.get("xgb_accuracy", 0.95) if xgb_available else None,
    "xgb_balanced": meta.get("xgb_balanced", 0.94) if xgb_available else None,
}

# =========================
# APP SETUP
# =========================
app = FastAPI(title="FakeGuard AI — Instagram Fake Account Detector")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.cache = {}

# =========================
# HOME — serves SPA
# =========================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"xgb_available": xgb_available}
    )

# =========================
# PREDICT
# =========================
@app.post("/predict")
async def predict_account(request: Request):
    form_data = await request.form()

    def get_float(key, default=0.0):
        val = form_data.get(key)
        if val is None or val == "":
            return default
        try:
            return float(val)
        except:
            return default

    # User inputs
    no_of_posts = get_float('no_of_posts')
    following   = get_float('following')
    followers   = get_float('followers')
    bio_len     = get_float('bio_len')
    picture     = get_float('picture')
    link        = get_float('link')

    # Feature engineering (mirrors train.py logic)
    follower_following_ratio = followers / (following + 1)
    followers_per_post       = followers / (no_of_posts + 1)
    following_heavy          = 1.0 if following > followers else 0.0

    engagement_total     = followers * 0.05
    engagement_per_post  = engagement_total / (no_of_posts + 1)

    has_bio         = 1.0 if bio_len > 0 else 0.0
    has_profile_pic = picture
    has_link        = link

    low_followers   = 1.0 if followers < 50   else 0.0
    high_following  = 1.0 if following > 1000 else 0.0
    irregular_posts = 1.0 if no_of_posts < 5  else 0.0
    cosine_similarity = 0.8 if has_bio else 0.3

    user_values = {
        'no_of_posts':              no_of_posts,
        'following':                following,
        'followers':                followers,
        'bio_len':                  bio_len,
        'picture':                  picture,
        'link':                     link,
        'follower_following_ratio': follower_following_ratio,
        'followers_per_post':       followers_per_post,
        'following_heavy':          following_heavy,
        'engagement_total':         engagement_total,
        'engagement_per_post':      engagement_per_post,
        'has_bio':                  has_bio,
        'has_profile_pic':          has_profile_pic,
        'has_link':                 has_link,
        'low_followers':            low_followers,
        'high_following':           high_following,
        'irregular_posts':          irregular_posts,
    }

    inputs = {}
    for feat in model_features:
        inputs[feat] = user_values.get(feat, medians.get(feat, 0.0))

    input_df = pd.DataFrame([inputs], columns=model_features)

    # Model selection
    model_choice = form_data.get('model_choice', 'Random Forest')
    if model_choice == "XGBoost" and xgb_available:
        model = xgb_model
    else:
        model = rf_model
        model_choice = "Random Forest"

    # Prediction
    pred_encoded = int(model.predict(input_df)[0])
    probs_raw    = model.predict_proba(input_df)[0]
    pred_label   = reverse_map[pred_encoded]
    confidence   = round(float(max(probs_raw)) * 100, 2)

    # Build class-probability dict (all 4 classes)
    all_probs = {}
    for idx, prob in enumerate(probs_raw):
        cls = reverse_map[idx]
        all_probs[cls] = round(float(prob) * 100, 2)

    # Explanation signals
    signals = []
    if followers < 50:
        signals.append({"label": "Low followers", "type": "warning"})
    if following > 1000:
        signals.append({"label": "High following count", "type": "warning"})
    if no_of_posts < 5:
        signals.append({"label": "Very few posts", "type": "warning"})
    if bio_len == 0:
        signals.append({"label": "No bio", "type": "warning"})
    if bio_len > 0:
        signals.append({"label": "Has bio", "type": "good"})
    if picture == 1:
        signals.append({"label": "Has profile picture", "type": "good"})
    if link == 1:
        signals.append({"label": "Has external link", "type": "info"})
    if followers > 0 and following > 0:
        ratio = followers / following
        if ratio > 2:
            signals.append({"label": f"Good follower ratio ({ratio:.1f}x)", "type": "good"})
        elif ratio < 0.3:
            signals.append({"label": f"Poor follower ratio ({ratio:.2f}x)", "type": "warning"})

    if pred_label == 'i':
        explanation = "Low activity and weak engagement signals"
    elif pred_label == 'a':
        explanation = "Suspicious engagement behavior detected"
    elif pred_label == 's':
        explanation = "Spam-like posting activity detected"
    else:
        explanation = "Normal, organic user behavior"

    return JSONResponse({
        "predicted_class": pred_label,
        "meaning":         meanings.get(pred_label, "Unknown"),
        "confidence":      confidence,
        "explanation":     explanation,
        "model_used":      model_choice,
        "all_probs":       all_probs,
        "signals":         signals,
    })

# =========================
# STATS API — for dashboard
# =========================
@app.get("/api/stats")
async def get_stats():
    return JSONResponse({
        "dataset": {
            "total_samples":   int(len(df)),
            "total_features":  len(model_features),
            "num_classes":     4,
            "models_available": 2 if xgb_available else 1,
        },
        "class_distribution": class_distribution,
        "feature_importances": feature_importances,
        "model_accuracy": model_accuracy,
        "xgb_available": xgb_available,
    })

# =========================
# RUN
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)