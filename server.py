import pandas as pd
import numpy as np
import pickle
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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

# ✅ CORRECT FEATURE LIST
model_features = meta['feature_names']
reverse_map = meta['reverse_map']

meanings = {
    'r': '✅ Real Account',
    'a': '⚠️ Active Fake',
    'i': '👻 Inactive Fake',
    's': '🤖 Spammer Fake'
}

# =========================
# LOAD DATA FOR MEDIANS
# =========================
df = pd.read_csv('dataset.csv')

medians = {
    c: float(df[c].median())
    for c in df.columns if c != 'class'
}

# =========================
# APP SETUP
# =========================
app = FastAPI(title="Instagram Fake Account Detector")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.cache = {}  # fix cache bug

# =========================
# HOME
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

    # =========================
    # USER INPUTS
    # =========================
    no_of_posts = get_float('no_of_posts')
    following   = get_float('following')
    followers   = get_float('followers')
    bio_len     = get_float('bio_len')
    picture     = get_float('picture')
    link        = get_float('link')

        # =========================
    # FEATURE ENGINEERING
    # =========================
    follower_following_ratio = followers / (following + 1)
    followers_per_post       = followers / (no_of_posts + 1)
    following_heavy          = 1.0 if following > followers else 0.0

    # Simulated engagement (IMPORTANT FIX)
    engagement_total = followers * 0.05
    engagement_per_post = engagement_total / (no_of_posts + 1)

    has_bio = 1.0 if bio_len > 0 else 0.0
    has_profile_pic = picture
    has_link = link

    low_followers = 1.0 if followers < 50 else 0.0
    high_following = 1.0 if following > 1000 else 0.0

    # 🔥 IMPROVED FEATURES
    irregular_posts = 1.0 if no_of_posts < 5 else 0.0
    cosine_similarity = 0.8 if has_bio else 0.3

    # =========================
    # BUILD FEATURE VECTOR
    # =========================
    user_values = {
        'no_of_posts': no_of_posts,
        'following': following,
        'followers': followers,
        'bio_len': bio_len,
        'picture': picture,
        'link': link,
        'follower_following_ratio': follower_following_ratio,
        'followers_per_post': followers_per_post,
        'following_heavy': following_heavy,
        'engagement_total': engagement_total,
        'engagement_per_post': engagement_per_post,
        'has_bio': has_bio,
        'has_profile_pic': has_profile_pic,
        'has_link': has_link,
        'low_followers': low_followers,
        'high_following': high_following,
        'irregular_posts': irregular_posts
    }

    inputs = {}
    for feat in model_features:
        if feat in user_values:
            inputs[feat] = user_values[feat]
        else:
            inputs[feat] = medians.get(feat, 0.0)

    input_df = pd.DataFrame([inputs], columns=model_features)

    # =========================
    # MODEL SELECTION
    # =========================
    model_choice = form_data.get('model_choice', 'Random Forest')

    if model_choice == "XGBoost" and xgb_available:
        model = xgb_model
    else:
        model = rf_model

    # =========================
    # PREDICTION
    # =========================
    pred_encoded = int(model.predict(input_df)[0])
    probs = model.predict_proba(input_df)[0]

    pred_label = reverse_map[pred_encoded]
    confidence = round(float(max(probs) * 100), 2)

    # =========================
    # EXPLANATION
    # =========================
    if pred_label == 'i':
        explanation = "Low activity and weak engagement"
    elif pred_label == 'a':
        explanation = "Suspicious engagement behavior"
    elif pred_label == 's':
        explanation = "Spam-like activity detected"
    else:
        explanation = "Normal user behavior"

    return {
        "predicted_class": pred_label,
        "meaning": meanings.get(pred_label, "Unknown"),
        "confidence": confidence,
        "explanation": explanation,
        "model_used": model_choice
    }

# =========================
# RUN
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)