from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import io
from pathlib import Path

from model_utils import load_data, predict_from_dataframe, evaluate_model

# -------------------------------------------------------
# INSTANCIAMOS FastAPI Y CONFIGURAMOS CORS
# -------------------------------------------------------
app = FastAPI(
    title="Sales Forecasting API",
    description="API para predecir ventas con XGBoost y obtener métricas.",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# RUTAS Y ARCHIVOS BASE
# -------------------------------------------------------
BASE_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

# CSV principal con todas las columnas:
CSV1 = PROJECT_DIR / "stores_sales_forecasting.csv"

# Directorio del frontend:
FRONTEND_DIR = PROJECT_DIR / "frontend"
SRC_DIR      = FRONTEND_DIR / "src"
CSS_DIR      = FRONTEND_DIR / "css"
JS_DIR       = FRONTEND_DIR / "js"

# -------------------------------------------------------
# MONTAR ARCHIVOS ESTÁTICOS (Frontend)
# -------------------------------------------------------
app.mount("/static/css", StaticFiles(directory=str(CSS_DIR)), name="static_css")
app.mount("/static/js", StaticFiles(directory=str(JS_DIR)), name="static_js")

# -------------------------------------------------------
# SERVIR index.html CUANDO PIDAN "/"
# -------------------------------------------------------
@app.get("/")
def serve_frontend():
    index_path = SRC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html no encontrado en frontend/src/")
    return FileResponse(str(index_path))


# -------------------------------------------------------
# ENDPOINT: /metrics_xgb (Obtener métricas del XGBoost sobre el CSV completo)
# -------------------------------------------------------
@app.get("/metrics_xgb")
def metrics_xgb_endpoint():
    """
    Carga el CSV principal, luego utiliza evaluate_model() para calcular 
    R2, MAE, MSE y RMSE sobre todo el dataset, y devuelve esas métricas.
    """
    try:
        df = load_data(str(CSV1))
        metrics = evaluate_model(df)
        return JSONResponse(content={"metrics": metrics})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------
# ENDPOINT: /predict_csv (Predicción batch a partir de CSV subido)
# -------------------------------------------------------
@app.post("/predict_csv")
def predict_csv(file: UploadFile = File(...)):
    """
    Recibe un archivo CSV, lo lee en un DataFrame y retorna las predicciones 
    calculadas por predict_from_dataframe().
    """
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents), encoding="latin1")
        preds = predict_from_dataframe(df)
        return JSONResponse(content={"predictions": preds})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------
# ENDPOINT: /predict (Predicción a partir de JSON con una o varias filas)
# -------------------------------------------------------
@app.post("/predict")
def predict_json(data: list[dict]):
    """
    Recibe un JSON con lista de objetos, cada uno representando una fila con las columnas esperadas:
      - Region
      - Product ID
      - Category
      - Sub-Category
      - Product Name
      - Quantity
      - Discount
      - Profit
    Retorna: {"predictions": [valor_predicho, ...]}
    """
    try:
        df = pd.DataFrame(data)
        preds = predict_from_dataframe(df)
        return JSONResponse(content={"predictions": preds})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------
# ENDPOINT: /kpis (Obtener KPI de negocio con filtros opcionales)
# -------------------------------------------------------
@app.get("/kpis")
def get_kpis(
    month: str = Query(None, description="Filtrar por mes (YYYY-MM), opcional."),
    vendor: str = Query("Todos", description="Filtrar por Customer Name."),
    product: str = Query("Todos", description="Filtrar por Product Name.")
):
    """
    Calcula y devuelve los KPIs:
      - total_sales: suma de 'Sales'
      - avg_profit_pct: promedio de (Profit/Sales)
      - sale_count: número de filas
      - avg_sales: promedio de 'Sales'
    Aplica filtros opcionales: month, vendor, product.
    """
    # 1) Leer CSV principal
    df = pd.read_csv(str(CSV1), encoding="latin1")

    # 2) Convertir 'Order Date' a datetime si existe
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

    # 3) Aplicar filtros
    if month:
        df = df[df["Order Date"].dt.to_period("M") == pd.Period(month, freq="M")]
    if vendor and vendor != "Todos":
        df = df[df["Customer Name"] == vendor]
    if product and product != "Todos":
        df = df[df["Product Name"] == product]

    # 4) Verificar columnas necesarias
    required_cols = ["Sales", "Profit"]
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=500, detail=f"Columna '{col}' no encontrada para calcular KPIs.")

    total_sales    = df["Sales"].sum()
    avg_profit_pct = (df["Profit"] / df["Sales"]).mean() if total_sales != 0 else 0
    sale_count     = df.shape[0]
    avg_sales      = df["Sales"].mean() if sale_count > 0 else 0

    return {
        "total_sales": float(total_sales),
        "avg_profit_pct": float(avg_profit_pct),
        "sale_count": int(sale_count),
        "avg_sales": float(avg_sales)
    }


# -------------------------------------------------------
# ENDPOINT: /grouped (Agrupar datos según un campo + filtros)
# -------------------------------------------------------
@app.get("/grouped")
def get_grouped_data(
    field: str = Query(
        ...,
        description=(
            "Columna por la que agrupar. Puede ser: "
            "'State', 'Postal Code', 'Region', 'Product ID', 'Category', "
            "'Sub-Category', 'Product Name', 'Customer Name'."
        )
    ),
    month: str = Query(None, description="Filtrar por mes (YYYY-MM), opcional."),
    vendor: str = Query("Todos", description="Filtrar por Customer Name."),
    product: str = Query("Todos", description="Filtrar por Product Name.")
):
    """
    Agrupa el CSV por `field`, calculando:
      - total_sales: suma de 'Sales'
      - total_quantity: suma de 'Quantity'
      - avg_discount: promedio de 'Discount'
      - total_profit: suma de 'Profit'
    Aplica los filtros opcionales: month, vendor, product.
    Retorna JSON con lista ordenada por total_sales descendente.
    """
    df = pd.read_csv(str(CSV1), encoding="latin1")
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

    if month:
        df = df[df["Order Date"].dt.to_period("M") == pd.Period(month, freq="M")]
    if vendor and vendor != "Todos":
        df = df[df["Customer Name"] == vendor]
    if product and product != "Todos":
        df = df[df["Product Name"] == product]

    if field not in df.columns:
        raise HTTPException(status_code=400, detail=f"El campo '{field}' no existe en el CSV.")

    required_cols = ["Sales", "Quantity", "Discount", "Profit"]
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=500, detail=f"Falta columna '{col}'.")

    grouped = (
        df.groupby(field, dropna=False)
          .agg(
              total_sales=pd.NamedAgg(column="Sales", aggfunc="sum"),
              total_quantity=pd.NamedAgg(column="Quantity", aggfunc="sum"),
              avg_discount=pd.NamedAgg(column="Discount", aggfunc="mean"),
              total_profit=pd.NamedAgg(column="Profit", aggfunc="sum")
          )
          .reset_index()
          .rename(columns={field: "group"})
          .sort_values("total_sales", ascending=False)
    )

    result = []
    for _, row in grouped.iterrows():
        result.append({
            "group": row["group"],
            "total_sales": float(row["total_sales"]),
            "total_quantity": int(row["total_quantity"]),
            "avg_discount": float(row["avg_discount"]),
            "total_profit": float(row["total_profit"])
        })

    return {"data": result}


# -------------------------------------------------------
# ENDPOINT: /sales_trend (Ventas mensuales por Cliente para un año dado)
# -------------------------------------------------------
@app.get("/sales_trend")
def sales_trend(
    year: int = Query(2020, description="Año para el que se calculan las ventas (p.ej. 2020)"),
    vendor: str = Query("Todos", description="Filtrar por Customer Name.")
):
    """
    Devuelve, para cada mes de `year`, la suma de 'Sales' agrupada por 'Customer Name'.
    Si `vendor != "Todos"`, solo se consideran filas de ese cliente.
    Retorna JSON con:
      {
        "labels": ["2020-01", ..., "2020-12"],
        "datasets": [
          { "vendor": "Ana López",   "values": [12000, ..., 9000] },
          { "vendor": "Carlos Pérez","values": [ 8000, ..., 3000] },
          …
        ]
      }
    """
    df = pd.read_csv(str(CSV1), encoding="latin1")
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df = df[df["Order Date"].dt.year == year]
    if vendor and vendor != "Todos":
        df = df[df["Customer Name"] == vendor]

    if "Sales" not in df.columns or "Customer Name" not in df.columns:
        raise HTTPException(status_code=500, detail="El CSV no contiene 'Sales' o 'Customer Name'.")

    df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)
    grouped = df.groupby(["Customer Name", "YearMonth"], dropna=False)["Sales"].sum().reset_index()

    pivot = grouped.pivot(index="YearMonth", columns="Customer Name", values="Sales").fillna(0)
    todos_meses = [f"{year}-{mes:02d}" for mes in range(1, 13)]
    pivot = pivot.reindex(todos_meses, fill_value=0)

    response = {
        "labels": todos_meses,
        "datasets": []
    }
    for cliente in pivot.columns:
        valores = pivot[cliente].tolist()
        response["datasets"].append({
            "vendor": cliente,
            "values": [float(v) for v in valores]
        })

    return response

