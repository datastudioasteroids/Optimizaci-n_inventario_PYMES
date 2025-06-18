import io
import sys
import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Al principio de main.py, justo tras los imports estándar:
import nltk

# Asegúrate de que Python encuentre tu paquete backend
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from ml_utils import normalize_columns
from train_xgb import train_and_save


# -------------------------------------------------------
# Configuración general
# -------------------------------------------------------
app = FastAPI(title="Sales Forecasting API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_DIR   = BASE_DIR.parent
MODELS_DIR    = BASE_DIR / "models"
TRAIN_CSV     = PROJECT_DIR / "stores_sales_forecasting.csv"
PIPE_QTY      = MODELS_DIR / "pipeline_quantity.pkl"
PIPE_PROF     = MODELS_DIR / "pipeline_profit.pkl"

pipe_q = pipe_p = None
uploaded_csv_path: Path | None = None

# Montar frontend estático
FRONTEND_DIR = PROJECT_DIR / "frontend"
app.mount("/static/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/static/js",  StaticFiles(directory=FRONTEND_DIR / "js"),  name="js")
app.mount("/static/img", StaticFiles(directory=FRONTEND_DIR / "static" / "img"), name="img")


@app.get("/")
def serve_index():
    idx = FRONTEND_DIR / "src" / "index.html"
    if not idx.exists():
        raise HTTPException(404, "index.html no encontrado")
    return FileResponse(str(idx))


# Al principio de main.py, justo tras los imports estándar:
import nltk

# -------------------------------------------------------
# Startup: descargar datos de NLTK y cargar pipelines
# -------------------------------------------------------
@app.on_event("startup")
def startup():
    # 1) Descarga silenciosa de WordNet y Open Multilingual Wordnet
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
    try:
        nltk.data.find('corpora/omw-1.4')
    except LookupError:
        nltk.download('omw-1.4')

    # 2) Ahora cargamos los pipelines si existen
    MODELS_DIR.mkdir(exist_ok=True)
    global pipe_q, pipe_p
    if PIPE_QTY.exists() and PIPE_PROF.exists():
        pipe_q = joblib.load(PIPE_QTY)
        pipe_p = joblib.load(PIPE_PROF)
        print("▶️ Pipelines cargados.")
    else:
        pipe_q = pipe_p = None
        print("⚠️ Pipelines no encontrados. Usa /upload_csv + /train_xgb.")


# -------------------------------------------------------
# Auxiliar: leer y normalizar DataFrame
# -------------------------------------------------------
def _get_df() -> pd.DataFrame:
    path = uploaded_csv_path or TRAIN_CSV
    if not path.exists():
        raise HTTPException(400, "No hay CSV disponible.")
    df = pd.read_csv(path, encoding="latin1")
    df = df.rename(columns={
        "Order Date":   "date",
        "Region":       "region",
        "Product Name": "product",
        "Quantity":     "quantity",
        "Profit":       "profit"
    }, errors="ignore")
    return normalize_columns(df)


# -------------------------------------------------------
# ENDPOINT: /upload_csv
# -------------------------------------------------------
@app.post("/upload_csv")
def upload_training_csv(file: UploadFile = File(...)):
    global uploaded_csv_path
    try:
        data = file.file.read()
        TRAIN_CSV.write_bytes(data)
        uploaded_csv_path = TRAIN_CSV
        return {"detail": f"CSV guardado como {TRAIN_CSV.name}"}
    except Exception as e:
        raise HTTPException(500, str(e))


# -------------------------------------------------------
# ENDPOINT: /train_xgb
# -------------------------------------------------------
@app.post("/train_xgb")
def retrain():
    csv_path = uploaded_csv_path or TRAIN_CSV
    if not csv_path.exists():
        raise HTTPException(400, "No hay CSV. Usa /upload_csv primero.")
    try:
        train_and_save(str(csv_path), str(MODELS_DIR))
        load_pipelines()
        return {"detail": "Retraining completado."}
    except Exception as e:
        raise HTTPException(500, str(e))


# -------------------------------------------------------
# ENDPOINT: /predict_csv  (batch)
# -------------------------------------------------------
@app.post("/predict")
def predict_json(payload: dict):
    # 1) Validar campos obligatorios
    for k in ("region", "product", "date"):
        if k not in payload:
            raise HTTPException(422, f"Falta '{k}' en el JSON.")
    period = payload.get("period", "day")
    # 2) Parsear fecha base
    try:
        dt = datetime.strptime(payload["date"], "%Y-%m-%d")
    except:
        raise HTTPException(422, "Formato de 'date' inválido. Debe ser YYYY-MM-DD.")
    # 3) Construir lista de meses según periodo
    year = dt.year
    if period == "day":
        months = [dt.month]
    elif period == "quarter":
        q = (dt.month - 1) // 3  # 0..3
        months = list(range(q*3 + 1, q*3 + 4))
    elif period == "semester":
        sem = 0 if dt.month <= 6 else 1
        months = list(range(sem*6 + 1, sem*6 + 7))
    elif period == "year":
        months = list(range(1, 13))
    else:
        raise HTTPException(422, f"Período desconocido '{period}'")
    # 4) Generar DataFrame de entrada para cada mes
    rows = []
    for m in months:
        rows.append({
            "date":    datetime(year, m, 1),  # día 1 de cada mes
            "region":  payload["region"],
            "product": payload["product"]
        })
    df_in = pd.DataFrame(rows)
    # 5) Normalizar columnas
    from ml_utils import normalize_columns
    df_in = normalize_columns(df_in)
    df_in["date"] = pd.to_datetime(df_in["date"], errors="coerce")
    # 6) Predecir y sumar
    qty_preds  = pipe_q.predict(df_in)
    prof_preds = pipe_p.predict(df_in)
    qty_sum  = float(qty_preds.sum())
    prof_sum = float(prof_preds.sum())
    # 7) Devolver totales y el periodo
    return {
        "period":   period,
        "quantity": qty_sum,
        "profit":   prof_sum
    }
# -------------------------------------------------------
# ENDPOINT: /predict  (JSON único)
# -------------------------------------------------------
@app.post("/predict")
def predict_json(payload: dict):
    if pipe_q is None or pipe_p is None:
        raise HTTPException(400, "Modelos no entrenados. Usa /upload_csv + /train_xgb.")
    # Validar campos
    for k in ("region", "product", "date"):
        if k not in payload:
            raise HTTPException(422, f"Falta '{k}' en el JSON.")
    try:
        dt = datetime.strptime(payload["date"], "%Y-%m-%d")
    except:
        raise HTTPException(422, "Formato de 'date' inválido. Debe ser YYYY-MM-DD.")
    df = pd.DataFrame([{
        "date":    dt,
        "region":  payload["region"],
        "product": payload["product"]
    }])
    df = normalize_columns(df)
    qty  = pipe_q.predict(df)[0]
    prof = pipe_p.predict(df)[0]
    return {"quantity": float(qty), "profit": float(prof)}


# -------------------------------------------------------
# ENDPOINT: /metrics_xgb
# -------------------------------------------------------
@app.get("/metrics_xgb")
def metrics_xgb_endpoint():
    try:
        from model_utils import evaluate_model
        df = _get_df()
        return JSONResponse({"metrics": evaluate_model(df)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# -------------------------------------------------------
# ENDPOINTS: metadata para dropdowns
# -------------------------------------------------------
@app.get("/metadata/regions")
def metadata_regions():
    df = _get_df()
    df = normalize_columns(df)
    if "region" not in df.columns:
        raise HTTPException(500, "No se encontró la columna 'region'")
    regions = sorted(df["region"].dropna().unique().tolist())
    return JSONResponse(regions)

@app.get("/metadata/vendors")
def metadata_vendors():
    df = _get_df()
    df = normalize_columns(df)
    if "customer_name" not in df.columns:
        raise HTTPException(500, "No se encontró la columna 'customer_name'")
    vendors = sorted(df["customer_name"].dropna().unique().tolist())
    return JSONResponse(vendors)

@app.get("/metadata/products")
def metadata_products():
    df = _get_df()
    df = normalize_columns(df)
    if "product" not in df.columns:
        raise HTTPException(500, "No se encontró la columna 'product'")
    products = sorted(df["product"].dropna().unique().tolist())
    return JSONResponse(products)

@app.get("/metadata/fields")
def metadata_fields():
    df = _get_df()
    # Opcionalmente puedes devolver sólo las normalizadas:
    norm = normalize_columns(df)
    fields = sorted(norm.columns.tolist())
    return JSONResponse(fields)


# -------------------------------------------------------
# ENDPOINT: /kpis
# -------------------------------------------------------
@app.get("/kpis")
def get_kpis(
    month:   str  = Query(None),
    vendor:  str  = Query("Todos"),
    product: str  = Query("Todos")
):
    df = _get_df()

    # 1) Detectar columna de fecha y parsear
    if "date" in df.columns:
        date_col = "date"
    elif "Order Date" in df.columns:
        date_col = "Order Date"
    else:
        raise HTTPException(500, "Falta columna de fecha ('date' o 'Order Date')")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # 2) Filtrar mes solo si month es válido
    if month and month.lower() not in ("null", "", "none"):
        try:
            period = pd.Period(month, "M")
        except Exception:
            raise HTTPException(400, f"Formato de month inválido: {month}")
        df = df[df[date_col].notna() & (df[date_col].dt.to_period("M") == period)]

    # 3) Filtrar vendor/product
    if vendor != "Todos":
        df = df[df.get("Customer Name", "") == vendor]
    if product != "Todos":
        df = df[df.get("Product Name", "") == product]

    # 4) Detectar columnas de ventas y utilidades
    if "Sales" in df.columns:
        sales_col = "Sales"
    elif "quantity" in df.columns:
        sales_col = "quantity"
    else:
        raise HTTPException(500, "Falta columna de ventas ('Sales' o 'quantity')")

    if "Profit" in df.columns:
        profit_col = "Profit"
    elif "profit" in df.columns:
        profit_col = "profit"
    else:
        raise HTTPException(500, "Falta columna de utilidades ('Profit' o 'profit')")

    # 5) Calcular KPIs
    total_sales    = df[sales_col].sum()
    sale_count     = len(df)
    avg_profit_pct = (df[profit_col] / df[sales_col]).mean() if total_sales else 0
    avg_sales      = df[sales_col].mean() if sale_count else 0

    return {
        "total_sales":    float(total_sales),
        "avg_profit_pct": float(avg_profit_pct),
        "sale_count":     int(sale_count),
        "avg_sales":      float(avg_sales)
    }


# -------------------------------------------------------
# ENDPOINT: /grouped
# -------------------------------------------------------
@app.get("/grouped")
def get_grouped_data(
    field:   str  = Query(..., description="Campo para agrupar"),
    month:   str  = Query(None),
    vendor:  str  = Query("Todos"),
    product: str  = Query("Todos")
):
    df = _get_df()
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    if month:
        df = df[df["Order Date"].dt.to_period("M") == pd.Period(month, "M")]
    if vendor != "Todos":
        df = df[df["Customer Name"] == vendor]
    if product != "Todos":
        df = df[df["Product Name"] == product]
    if field not in df.columns:
        raise HTTPException(400, f"'{field}' no existe")
    for c in ["Sales", "Quantity", "Discount", "Profit"]:
        if c not in df.columns:
            raise HTTPException(500, f"Falta '{c}'")
    grouped = (
        df.groupby(field, dropna=False)
          .agg(
            total_sales    = pd.NamedAgg("Sales","sum"),
            total_quantity = pd.NamedAgg("Quantity","sum"),
            avg_discount   = pd.NamedAgg("Discount","mean"),
            total_profit   = pd.NamedAgg("Profit","sum")
          )
          .reset_index()
          .rename(columns={field:"group"})
          .sort_values("total_sales", ascending=False)
    )
    return {"data": [
        {
          "group":           row["group"],
          "total_sales":     float(row["total_sales"]),
          "total_quantity":  int(row["total_quantity"]),
          "avg_discount":    float(row["avg_discount"]),
          "total_profit":    float(row["total_profit"])
        }
        for _, row in grouped.iterrows()
    ]}


# -------------------------------------------------------
# ENDPOINT: /sales_trend
# -------------------------------------------------------
@app.get("/sales_trend")
def sales_trend(
    year:   int  = Query(2020),
    month:  str  = Query(None),
    vendor: str  = Query("Todos")
):
    df = _get_df()
    if "Order Date" not in df.columns:
        raise HTTPException(500, "Falta 'Order Date'")
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df = df[df["Order Date"].dt.year == year]

    # Ventas diarias de un mes
    if month:
        try:
            periodo = pd.Period(month, "M")
        except:
            raise HTTPException(400, "Formato de month inválido")
        df = df[df["Order Date"].dt.to_period("M") == periodo]
        if vendor != "Todos":
            df = df[df["Customer Name"] == vendor]
        df["Day"] = df["Order Date"].dt.day
        pivot = (
          df.groupby(["Customer Name","Day"])["Sales"]
            .sum().unstack(fill_value=0)
            .reindex(range(1, periodo.days_in_month+1), fill_value=0)
        )
        labels = [f"{month}-{d:02d}" for d in pivot.index]
        return {"labels": labels, "datasets": [
            {"vendor": c, "values": pivot[c].tolist()}
            for c in pivot.columns
        ]}

    # Ventas mes a mes
    if vendor != "Todos":
        df = df[df["Customer Name"] == vendor]
    if "Sales" not in df.columns:
        raise HTTPException(500, "Falta 'Sales'")
    df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)
    pivot = ( 
      df.groupby(["Customer Name","YearMonth"])["Sales"]
        .sum().unstack(fill_value=0)
        .reindex([f"{year}-{m:02d}" for m in range(1,13)], fill_value=0)
    )
    return {"labels": pivot.index.tolist(), "datasets": [
        {"vendor": c, "values": pivot[c].tolist()}
        for c in pivot.columns
    ]}
