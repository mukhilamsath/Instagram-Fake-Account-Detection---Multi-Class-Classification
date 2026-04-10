
# Instagram Fake Account Detection (Multi-Class Classification)

A comprehensive machine learning project designed to detect and classify Instagram accounts into four distinct categories: Real, Active Fake, Inactive Fake, and Spammer Fake. This project features a robust training pipeline and a high-performance web interface.

## 👥 Team Members
* **Mukhil Amsath P K**
* **Harisree T**

## 🚀 Features
* **Multi-Class Classification:** Classifies accounts into four specific types:
    * `r`: ✅ **Real Account** — Genuine user with organic activity.
    * `a`: ⚠️ **Active Fake** — Bots that mimic activity to bypass detection.
    * `i`: 👻 **Inactive Fake** — Dormant accounts with minimal activity.
    * `s`: 🤖 **Spammer Fake** — Accounts exhibiting aggressive spam behavior.
* **Dual Deployment Options:**
    * **Streamlit App:** For data visualization, dataset statistics, and feature importance analysis.
    * **FastAPI Web Server:** A sleek, high-performance UI ("FakeGuard AI") for real-time account scanning.
* **Advanced Feature Engineering:** Utilizes 20+ metrics including follower/following ratios, engagement rates, bio length, and log-transformed distributions to handle outliers.

## 🛠️ Tech Stack
* **Machine Learning:** Python, Scikit-learn (Random Forest), XGBoost.
* **Data Processing:** Pandas, NumPy.
* **Web Frameworks:** Streamlit, FastAPI, Uvicorn.
* **Frontend:** HTML5, CSS3 (Modern UI with Glassmorphism), Jinja2 templates, JavaScript.

## 📂 Project Structure
* `train.py`: The machine learning pipeline including feature engineering and model training.
* `server.py`: FastAPI backend logic for the "FakeGuard AI" web interface.
* `app.py`: Streamlit application for model exploration and data overview.
* `static/` & `templates/`: Frontend assets for the web UI.
* `dataset.csv`: Training data containing over 43,000 account samples.

## ⚙️ Setup & Installation
1. **Clone the Repository:**
   ```bash
   git clone [repository-url]
   cd instagram-fake-account-detection
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Train the Model:**
   ```bash
   python train.py
   ```
4. **Run the FastAPI Web UI:**
   ```bash
   python server.py
   ```
   *Access at `http://localhost:8000`*
5. **(Optional) Run Streamlit Dashboard:**
   ```bash
   streamlit run app.py
   ```

## 📊 Model Performance
The models are trained on a balanced dataset of **43,307** accounts. The Random Forest classifier, optimized with balanced subsampling, achieves approximately **91% balanced accuracy**.
