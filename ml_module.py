import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import pickle
import os
from db import execute_query

MODEL_PATH = 'worker_suitability_model.pkl'

def train_model():
    """
    Trains a Random Forest model on historical booking and rating data.
    SRS FR-ML-01 to FR-ML-05
    """
    # Fetch historical data
    query = """
    SELECT 
        wp.daily_wage, 
        wp.experience_years, 
        wp.avg_rating, 
        wp.total_jobs,
        r.score as target_score
    FROM ratings r
    JOIN worker_profiles wp ON r.worker_id = wp.worker_id
    """
    data = execute_query(query)
    
    if not data or len(data) < 10:  # Minimum data for training
        print("Insufficient data for ML training. Cold-start handling active.")
        return False

    df = pd.DataFrame(data)
    X = df[['daily_wage', 'experience_years', 'avg_rating', 'total_jobs']]
    y = df['target_score']

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    
    print("ML Model trained and saved successfully.")
    return True

def predict_suitability(worker_profile):
    """
    Predicts worker suitability score using the trained ML model.
    Falls back to a heuristic if model isn't available.
    """
    if not os.path.exists(MODEL_PATH):
        # Fallback heuristic (Rule-based)
        score = (float(worker_profile['avg_rating']) * 20) + (min(worker_profile['total_jobs'], 50))
        return min(score, 100)

    try:
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        
        # Prepare input features
        features = [[
            float(worker_profile.get('daily_wage', 0)),
            int(worker_profile.get('experience_years', 0)),
            float(worker_profile.get('avg_rating', 0)),
            int(worker_profile.get('total_jobs', 0))
        ]]
        
        prediction = model.predict(features)[0]
        # Normalize to 0-100
        return min(max(prediction * 20, 0), 100)
    except Exception as e:
        print(f"ML Prediction Error: {e}")
        return 0
