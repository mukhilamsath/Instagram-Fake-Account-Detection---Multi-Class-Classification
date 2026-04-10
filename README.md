# Instagram Fake Account Detection UI

This Streamlit app provides a user interface for the Instagram Fake Account Detection project.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the app:
   ```
   streamlit run app.py
   ```

## Features

- Predict account type using Random Forest or XGBoost models
- View dataset overview and statistics
- Feature importance visualization (if available)

## Models

The app loads pre-trained models from the notebook. Ensure the following files are present:
- `random_forest_model.pkl`
- `xgboost_model.pkl` (optional)
- `model_metadata.pkl`
- `dataset.csv`

## Project Overview

This project classifies Instagram accounts into four categories:
- `r`: Real account
- `a`: Active fake
- `i`: Inactive fake
- `s`: Spammer fake

Using features like number of posts, followers, engagement rates, etc.