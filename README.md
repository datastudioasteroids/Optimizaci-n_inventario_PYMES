# 📦 Optimización de Inventario para PYMES

# Descripción
## Optimizacion_inventario_PYMES es una aplicación web full‑stack pensada para pequeñas y medianas empresas que buscan:

## 📈 Predecir ventas y utilidades (quantity & profit) por región, producto y periodo.

## 📊 Visualizar KPIs, tendencias y agrupaciones interactivas.

## 🔄 Entrenar y actualizar modelos XGBoost en caliente tras cargar nuevos datos CSV.

# 🚀 Tecnologías
# Backend
FastAPI: servidor ultra‑rápido para endpoints REST y ficheros estáticos.

Pandas: manipulación y filtrado de datos.

Joblib: serialización de pipelines XGBoost.

XGBoost: regresión de alta performance.

scikit‑learn: Pipeline, ColumnTransformer y OHE + escalado.

RapidFuzz + NLTK WordNet: normalización de columnas dinámicas con fuzzy‑matching y sinonimia.

NLTK: WordNet y Open Multilingual Wordnet para sinonimia de nombres de columnas.

Uvicorn + AnyIO: servidor asíncrono de producción.

# Frontend
HTML5 / CSS3: diseño “glassmorphism” con fondo espacial.

JavaScript (ES Modules): modularización (api.js, dashboard.js, charts/*.js).

Plotly.js: gráficos interactivos (líneas, barras, dispersiones).

PapaParse: parseo de CSV en cliente y eventos clientDataReady.

Fetch API: llamadas a endpoints (/kpis, /grouped, /sales_trend, /predict, /metadata/...).

DevOps & Deploy
Docker: contenedor reproducible.

Render.com: CI/CD y hosting automático desde GitHub.

GitHub Actions (opcional): tests + build + deploy.

requirements.txt / Pipenv: gestión de dependencias.

# 📈 Uso
Sube tu CSV de entrenamiento (/upload_csv).

Entrena el modelo (/train_xgb).

Explora: KPIs, filtros, dashboards, predicción manual.

Integra en tu PYME para optimizar pedidos y stock.
