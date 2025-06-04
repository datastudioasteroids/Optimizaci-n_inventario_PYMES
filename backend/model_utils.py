import pandas as pd
import joblib
import os
from pathlib import Path
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# -------------------------------------------------------------------
# 1) Rutas absolutas al modelo XGBoost y a los feature names
# -------------------------------------------------------------------
MODEL_PATH    = Path(r"D:\Repositorios\Proyecto Sales forecasting\best_xgb_model.pkl")
FEATURES_PATH = Path(r"D:\Repositorios\Proyecto Sales forecasting\feature_names.pkl")


def load_data(path: str) -> pd.DataFrame:
    """
    Carga el CSV con encoding latin1 y devuelve un DataFrame.
    Verifica si el archivo existe.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No encontré el archivo CSV en la ruta: {path}")
    return pd.read_csv(path, encoding="latin1")


def load_model():
    """
    Carga el modelo XGBoost serializado desde disco (best_xgb_model.pkl).
    Si no existe, lanza FileNotFoundError.
    """
    if MODEL_PATH.is_file():
        return joblib.load(str(MODEL_PATH))
    else:
        raise FileNotFoundError(f"El modelo no fue encontrado en: {MODEL_PATH}")


def load_feature_names():
    """
    Carga la lista de nombres de columnas (features) desde disco
    (feature_names.pkl).
    """
    if FEATURES_PATH.is_file():
        return joblib.load(str(FEATURES_PATH))
    else:
        raise FileNotFoundError(f"No encontré el archivo de features en: {FEATURES_PATH}")


def predict_from_dataframe(df: pd.DataFrame):
    """
    Genera predicciones para un DataFrame df:
      1) Elimina 'Sales' si está presente.
      2) Crea dummies de las columnas categóricas (mismo procedimiento que durante entrenamiento).
      3) Alinea columnas con las que se usaron para entrenar (cargadas desde feature_names.pkl).
      4) Retorna la lista de predicciones.
    """
    # 1) Cargar modelo XGBoost
    model = load_model()

    # 2) Quitar columna objetivo si viene en el DataFrame
    X_raw = df.drop(["Sales"], axis=1, errors="ignore")

    # 3) Crear variables dummy (one-hot) exactamente igual que en el entrenamiento
    X_encoded = pd.get_dummies(X_raw, drop_first=True)

    # 4) Cargar lista de features usadas durante el entrenamiento
    trained_features = load_feature_names()

    # 5) Reindex para alinear columnas:
    #    - Crea todas las columnas que faltan con 0
    #    - Descarta cualquier columna extra
    X_aligned = X_encoded.reindex(columns=trained_features, fill_value=0)

    # 6) Realizar predicción y devolver como lista
    preds = model.predict(X_aligned)
    return preds.tolist()


def evaluate_model(df: pd.DataFrame):
    """
    Dado un DataFrame `df` que incluya "Sales", calcula métricas R2, MAE, MSE, RMSE
    usando el modelo XGBoost precargado.
    """
    # 1) Verificar que exista "Sales"
    if "Sales" not in df.columns:
        raise KeyError("El DataFrame debe contener la columna 'Sales' para evaluar.")

    y_true = df["Sales"]
    X_raw = df.drop(["Sales"], axis=1, errors="ignore")

    # 2) Crear dummies y alinear con los features entrenados
    X_encoded = pd.get_dummies(X_raw, drop_first=True)
    trained_features = load_feature_names()
    X_aligned = X_encoded.reindex(columns=trained_features, fill_value=0)

    # 3) Cargar modelo y obtener predicciones
    model = load_model()
    y_pred = model.predict(X_aligned)

    # 4) Calcular métricas
    r2   = r2_score(y_true, y_pred)
    mae  = mean_absolute_error(y_true, y_pred)
    mse  = mean_squared_error(y_true, y_pred)
    rmse = mse ** 0.5

    return {
        "r2": float(r2),
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse)
    }
