# backend/train_xgb.py

import pandas as pd
import joblib
from pathlib import Path
from ml_utils import normalize_columns, build_xgb_pipeline

def train_and_save(data_path: str, out_dir: str, model_params: dict = None):
    out = Path(out_dir)
    out.mkdir(exist_ok=True, parents=True)

    # 1) Leer CSV parseando la fecha correcta
    df = pd.read_csv(
        data_path,
        encoding="latin1",
        parse_dates=["Order Date"],
        dayfirst=False  # o True si tus fechas son DD/MM/YYYY
    )

    # 2) Renombrar columnas “fáciles” antes de normalizar
    df = df.rename(columns={
        "Order Date":   "date",
        "Region":       "region",
        "Product Name": "product",
        "Quantity":     "quantity",
        "Profit":       "profit"
    }, errors="ignore")

    # 3) Ahora normalizamos cualquier variante
    df = normalize_columns(df)

    # 4) Asegurarnos que 'date' es datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # 5) Extraer X y y
    X = df[["date", "region", "product"]]
    y_q = df["quantity"]
    y_p = df["profit"]

    # 6) Parámetros por defecto
    default = {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": 8,
        "random_state": 42,
        "n_jobs": -1
    }
    params = model_params or default

    # 7) Construir y entrenar pipelines
    pipe_q = build_xgb_pipeline(params)
    pipe_p = build_xgb_pipeline(params)
    pipe_q.fit(X, y_q)
    pipe_p.fit(X, y_p)

    # 8) Serializar
    joblib.dump(pipe_q, out / "pipeline_quantity.pkl")
    joblib.dump(pipe_p, out / "pipeline_profit.pkl")

    print(f"✅ Pipelines entrenados y guardados en {out}")
