import streamlit as st
import pandas as pd
import pickle
import os

# Load dataset for features and overview
df = pd.read_csv('dataset.csv')
features = [col for col in df.columns if col != 'class']

# Load models
with open('random_forest_model.pkl', 'rb') as f:
    rf_model = pickle.load(f)

with open('model_metadata.pkl', 'rb') as f:
    meta = pickle.load(f)

xgb_available = os.path.exists('xgboost_model.pkl')
if xgb_available:
    with open('xgboost_model.pkl', 'rb') as f:
        xgb_model = pickle.load(f)

# Streamlit app
st.title("Instagram Fake Account Detection")

st.markdown("""
This app uses machine learning models to classify Instagram accounts as Real (r), Active Fake (a), Inactive Fake (i), or Spammer Fake (s).
""")

# Model selection
model_options = ["Random Forest"]
if xgb_available:
    model_options.append("XGBoost")
model_choice = st.selectbox("Choose Model", model_options)

# Input features
st.header("Input Account Features")
inputs = {}
col1, col2 = st.columns(2)

with col1:
    for i, feat in enumerate(features[:len(features)//2]):
        if feat in ['picture', 'link', 'promotion_key', 'follower_key']:
            inputs[feat] = st.selectbox(f"{feat} (0 or 1)", [0, 1], key=feat)
        else:
            inputs[feat] = st.number_input(feat, value=0.0, key=feat)

with col2:
    for i, feat in enumerate(features[len(features)//2:]):
        if feat in ['picture', 'link', 'promotion_key', 'follower_key']:
            inputs[feat] = st.selectbox(f"{feat} (0 or 1)", [0, 1], key=feat)
        else:
            inputs[feat] = st.number_input(feat, value=0.0, key=feat)

# Predict button
if st.button("Predict Account Type"):
    input_df = pd.DataFrame([inputs])
    if model_choice == "Random Forest":
        pred_encoded = rf_model.predict(input_df)[0]
    else:
        pred_encoded = xgb_model.predict(input_df)[0]
    
    pred_label = meta['reverse_map'][pred_encoded]
    st.success(f"Predicted Class: **{pred_label}**")
    
    # Meaning
    meanings = {
        'r': 'Real account',
        'a': 'Active fake',
        'i': 'Inactive fake',
        's': 'Spammer fake'
    }
    st.info(f"Meaning: {meanings.get(pred_label, 'Unknown')}")

# Data Overview
st.header("Dataset Overview")
st.write(f"Dataset contains {len(df)} accounts with {len(features)} features.")
st.write("Class distribution:")
st.bar_chart(df['class'].value_counts())

st.write("Feature statistics:")
st.dataframe(df.describe())

# Feature Importance (if available)
if 'feature_importance' in meta:
    st.header("Feature Importance")
    feat_imp = pd.DataFrame({
        'Feature': features,
        'Importance': meta['feature_importance']
    }).sort_values('Importance', ascending=False)
    st.bar_chart(feat_imp.set_index('Feature'))