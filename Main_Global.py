import io, os, pickle, logging
from typing import Dict, Tuple
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use('Agg')
MODEL_STORAGE_PATH = "dimension_model.pkl"

class RegressionModel:
    def __init__(self):
        self.coefficients = {}
        self.is_trained = False

    def train(self, initial_df, final_df):
        merged = pd.merge(initial_df, final_df, on=['Cavity', 'Shot'], suffixes=('_init', '_final'))
        cols = [c.replace('_init', '') for c in merged.columns if '_init' in c]
        for dim in cols:
            X = pd.to_numeric(merged[f"{dim}_init"], errors='coerce').values
            Y = pd.to_numeric(merged[f"{dim}_final"], errors='coerce').values
            mask = ~np.isnan(X) & ~np.isnan(Y)
            if len(X[mask]) < 2: continue
            slope, intercept = np.polyfit(X[mask], Y[mask], 1)
            self.coefficients[dim] = {"slope": slope, "intercept": intercept}
        self.is_trained = True
        self.save_state()

    def predict(self, val, dim):
        if dim not in self.coefficients: return val
        p = self.coefficients[dim]
        return (p["slope"] * val) + p["intercept"]

    def save_state(self):
        with open(MODEL_STORAGE_PATH, 'wb') as f:
            pickle.dump({'coeffs': self.coefficients, 'is_trained': self.is_trained}, f)

    def load_state(self):
        if os.path.exists(MODEL_STORAGE_PATH):
            with open(MODEL_STORAGE_PATH, 'rb') as f:
                d = pickle.load(f)
                self.coefficients, self.is_trained = d['coeffs'], d['is_trained']

predictor = RegressionModel()
predictor.load_state()

def parse_excel(file_content):
    # 'openpyxl' is required here for .xlsx files
    df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
    # Clean headers: remove anything in brackets like [mm]
    df.columns = [str(c).split('[')[0].strip() for c in df.columns]
    return df.dropna(subset=['Cavity', 'Shot'])

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/train")
async def train_endpoint(initial_file: UploadFile = File(...), final_file: UploadFile = File(...)):
    try:
        df_init = parse_excel(await initial_file.read())
        df_final = parse_excel(await final_file.read())
        predictor.train(df_init, df_final)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/predict")
async def predict_endpoint(startup_file: UploadFile = File(...)):
    if not predictor.is_trained: return {"status": "error", "detail": "Model not trained"}
    try:
        df = parse_excel(await startup_file.read())
        results = {}
        for dim in [c for c in df.columns if c not in ["Cavity", "Shot"]]:
            avg = df[dim].mean()
            results[dim] = {"predicted": round(float(predictor.predict(avg, dim)), 4)}
        return {"status": "ok", "predictions": results}
    except Exception as e:
        return {"status": "error", "detail": str(e)}