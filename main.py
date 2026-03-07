import io, os, pickle
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Global Dimension Predictor")

# Enable CORS for the Cloudflare Worker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = "dimension_model.pkl"

# ==================== HELPERS ====================

def clean_header(col_name):
    """Removes [mm] and extra spaces from Excel headers."""
    return str(col_name).split('[')[0].strip()

def parse_excel_smarter(contents):
    """Skips info rows (Name, Project) and finds the measurement table."""
    xl = pd.ExcelFile(io.BytesIO(contents), engine='openpyxl')
    
    # Priority 1: A sheet named 'Data'. Priority 2: The first sheet.
    sheet_name = next((s for s in xl.sheet_names if 'data' in s.lower()), xl.sheet_names[0])
    df = xl.parse(sheet_name)
    
    print(f"\n--- [DEBUG] Reading Sheet: {sheet_name} ---")

    # SEARCH FOR DATA START: Look for the row containing 'Cavity'
    header_idx = 0
    for i, row in df.iterrows():
        row_str = [str(val).lower() for val in row.values]
        if any('cavity' in s or 'shot' in s for s in row_str):
            header_idx = i + 1
            print(f"--- [DEBUG] Found Data Table at Row: {header_idx} ---")
            # Re-read the file starting from the data row
            df = xl.parse(sheet_name, skiprows=header_idx)
            df.columns = [str(c).strip() for c in row.values]
            break

    # Standardize 'Cavity' and 'Shot' names
    rename_map = {}
    for col in df.columns:
        low_col = col.lower()
        if 'cavity' in low_col: rename_map[col] = 'Cavity'
        if 'shot' in low_col: rename_map[col] = 'Shot'
    
    df = df.rename(columns=rename_map)
    df.columns = [clean_header(c) for c in df.columns]
    
    # --- VISUAL CHECK IN TERMINAL ---
    print("--- [DEBUG] First 3 Rows of Data found: ---")
    print(df.head(3))
    
    if 'Cavity' not in df.columns or 'Shot' not in df.columns:
        raise ValueError(f"Could not find 'Cavity' or 'Shot' columns. Found: {list(df.columns)}")
    
    return df.dropna(subset=['Cavity', 'Shot'])

# ==================== MODEL LOGIC ====================

class DimensionModel:
    def __init__(self):
        self.coefficients = {}
        self.is_trained = False
        self.load_state()

    def train(self, df_init, df_final):
        # Match data by Cavity and Shot
        merged = pd.merge(df_init, df_final, on=['Cavity', 'Shot'], suffixes=('_init', '_final'))
        
        # Identify dimensions (exclude index columns)
        dims = [c.replace('_init', '') for c in merged.columns if '_init' in c]
        
        for d in dims:
            # Force numeric and filter out 0s/NaNs to keep calculation accurate
            X = pd.to_numeric(merged[f"{d}_init"], errors='coerce')
            Y = pd.to_numeric(merged[f"{d}_final"], errors='coerce')
            
            # SAFE FILTER: Ignore values < 1mm (likely empty cells or noise)
            mask = (X > 1.0) & (Y > 1.0)
            X_clean, Y_clean = X[mask].values, Y[mask].values
            
            if len(X_clean) >= 2:
                slope, intercept = np.polyfit(X_clean, Y_clean, 1)
                self.coefficients[d] = {"slope": float(slope), "intercept": float(intercept)}
        
        self.is_trained = True
        self.save_state()

    def save_state(self):
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({"coeff": self.coefficients, "trained": True}, f)

    def load_state(self):
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                data = pickle.load(f)
                self.coefficients = data.get("coeff", {})
                self.is_trained = data.get("trained", False)

model = DimensionModel()

# ==================== ENDPOINTS ====================

@app.get("/check-dimension")
def health():
    return {"status": "online", "model_trained": model.is_trained}

@app.post("/check-dimension/train")
async def train(initial_file: UploadFile = File(...), final_file: UploadFile = File(...)):
    try:
        df_init = parse_excel_smarter(await initial_file.read())
        df_final = parse_excel_smarter(await final_file.read())
        model.train(df_init, df_final)
        return {"status": "ok", "message": "Calibration Complete"}
    except Exception as e:
        print(f"Error during training: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)

@app.post("/check-dimension/predict")
async def predict(startup_file: UploadFile = File(...)):
    if not model.is_trained:
        return JSONResponse({"status": "error", "detail": "Model not calibrated."}, status_code=400)
    
    try:
        df = parse_excel_smarter(await startup_file.read())
        results = []
        
        for dim, coeffs in model.coefficients.items():
            if dim in df.columns:
                # SAFE AVERAGE: Filter out 0s/empty cells to avoid 27 vs 31 error
                vals = pd.to_numeric(df[dim], errors='coerce')
                valid_vals = vals[vals > 1.0] 
                
                if not valid_vals.empty:
                    avg_val = valid_vals.mean()
                    # Apply Formula: Y = mX + b
                    predicted_val = (avg_val * coeffs['slope']) + coeffs['intercept']
                    
                    results.append({
                        "dimension": dim,
                        "current": round(float(avg_val), 4),
                        "predicted": round(float(predicted_val), 4)
                    })
        
        return {"status": "ok", "predictions": results}
    except Exception as e:
        print(f"Error during prediction: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)

if __name__ == "__main__":
    print("Starting Global API on Port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
