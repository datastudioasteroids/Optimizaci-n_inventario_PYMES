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
    Recibe un JSON con lista de objetos (una o varias filas) con las columnas esperadas:
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
        # Filtramos las filas cuyo Order Date esté en ese periodo YYYY-MM
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

    # FILTROS
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
# ENDPOINT: /sales_trend (Ventas por tiempo, mes o día, según filtros)
# -------------------------------------------------------
@app.get("/sales_trend")
def sales_trend(
    year: int = Query(2020, description="Año para el que se calculan las ventas (p.ej. 2020)"),
    month: str = Query(None, description="Filtrar por mes (YYYY-MM), opcional."),
    vendor: str = Query("Todos", description="Filtrar por Customer Name.")
):
    """
    Devuelve una serie de tiempo de ventas:
      • Si no hay `month`, agrupamos mes a mes dentro del año indicado:
        { "labels": ["2020-01", ... , "2020-12"], 
          "datasets": [
            { "vendor": "Joe Elijah", "values": [1234, 2345, ... , 3456] },
            ...
          ]
        }
      • Si se pasa `month="YYYY-MM"`, entonces filtramos ese mes
        y devolvemos la serie diaria (día 1,2,... hasta fin de mes) para cada cliente:
        { "labels": ["2020-06-01", "2020-06-02", ..., "2020-06-30"],
          "datasets": [
            { "vendor": "Joe Elijah", "values": [123, 234, ... , 456] },
            ...
          ]
        }
    """
    # 1) Leer el CSV principal
    df = pd.read_csv(str(CSV1), encoding="latin1")

    # 2) Convertir 'Order Date' a datetime
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    else:
        raise HTTPException(status_code=500, detail="La columna 'Order Date' no existe en el CSV.")

    # 3) Filtrar por año
    df = df[df["Order Date"].dt.year == year]

    # 4) Si se envió un mes específico, filtramos ese mes y agrupamos por día
    if month:
        try:
            # “month” viene en formato "YYYY-MM"
            periodo = pd.Period(month, freq="M")
        except:
            raise HTTPException(status_code=400, detail="Formato de month inválido. Debe ser 'YYYY-MM'.")
        df = df[df["Order Date"].dt.to_period("M") == periodo]

        # 5) Filtrar por cliente si no es "Todos"
        if vendor and vendor != "Todos":
            df = df[df["Customer Name"] == vendor]

        # 6) Agrupar por día dentro de ese mes
        df["Day"] = df["Order Date"].dt.day
        grouped = df.groupby(["Customer Name", "Day"], dropna=False)["Sales"].sum().reset_index()

        # 7) Determinar cuántos días tiene ese mes
        #    Por ejemplo, junio tiene 30, febrero puede tener 28/29, etc.
        total_dias = periodo.days_in_month
        todos_dias = list(range(1, total_dias + 1))

        # 8) Pivot para columnas por cliente y filas por día
        pivot = grouped.pivot(index="Day", columns="Customer Name", values="Sales").fillna(0)
        pivot = pivot.reindex(todos_dias, fill_value=0)

        # 9) Preparar labels en formato "YYYY-MM-DD"
        labels = [f"{month}-{dia:02d}" for dia in todos_dias]

        # 10) Construir JSON de salida
        response = {
            "labels": labels,
            "datasets": []
        }
        for cliente in pivot.columns:
            valores = pivot[cliente].tolist()
            response["datasets"].append({
                "vendor": cliente,
                "values": [float(v) for v in valores]
            })
        return response

    # — Si no hay month: agrupamos mes a mes dentro de todo el año —
    else:
        # 4bis) Si no enviamos mes, solo filtramos por cliente si no es “Todos”
        if vendor and vendor != "Todos":
            df = df[df["Customer Name"] == vendor]

        # 5) Verificar que existan las columnas necesarias
        if "Sales" not in df.columns or "Customer Name" not in df.columns:
            raise HTTPException(status_code=500, detail="El CSV no contiene 'Sales' o 'Customer Name'.")

        # 6) Crear columna YearMonth en formato "YYYY-MM"
        df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)

        # 7) Agrupar por [Customer Name, YearMonth]
        grouped = df.groupby(["Customer Name", "YearMonth"], dropna=False)["Sales"].sum().reset_index()

        # 8) Pivot para índices = meses (enero a diciembre) y columnas = cada cliente
        pivot = grouped.pivot(index="YearMonth", columns="Customer Name", values="Sales").fillna(0)

        # 9) Reindexar para asegurarse de tener todos los meses de 01 a 12
        todos_meses = [f"{year}-{mes:02d}" for mes in range(1, 13)]
        pivot = pivot.reindex(todos_meses, fill_value=0)

        # 10) Construir JSON de salida
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
