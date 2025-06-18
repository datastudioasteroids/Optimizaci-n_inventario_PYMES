# backend/ml_utils.py

import pandas as pd
from rapidfuzz import process, fuzz
from nltk.corpus import wordnet as wn
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
import xgboost as xgb

STANDARD_COLUMNS = ["date", "region", "product", "quantity", "profit"]

def normalize_columns(df: pd.DataFrame, threshold: int = 80) -> pd.DataFrame:
    """
    Renombra columnas a STANDARD_COLUMNS usando:
      1) fuzzy matching (RapidFuzz)
      2) sinonimia semántica (WordNet)
    """
    orig = list(df.columns)
    mapping = {}
    for std in STANDARD_COLUMNS:
        # 1) fuzzy
        match, score, _ = process.extractOne(std, orig, scorer=fuzz.token_sort_ratio)
        if score >= threshold:
            mapping[match] = std
            continue
        # 2) sinonimia
        for col in orig:
            syns = wn.synsets(col, lang='eng') or wn.synsets(col)
            lemmas = {l.lower().replace('_',' ') for s in syns for l in s.lemma_names()}
            if std in lemmas:
                mapping[col] = std
                break
    return df.rename(columns=mapping)

def extract_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extrae year, month y year_month de df['date']."""
    ds = df["date"]
    return pd.DataFrame({
        "year":      ds.dt.year,
        "month":     ds.dt.month,
        "year_month": ds.dt.year.astype(str) + "_" + ds.dt.month.astype(str),
    })

def get_preprocessor() -> ColumnTransformer:
    """ColumnTransformer para date, region, product con OHE."""
    date_pipe = Pipeline([
        ("extract", FunctionTransformer(extract_date_features, validate=False)),
        ("ohe",     OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    cat_pipe  = Pipeline([("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    return ColumnTransformer([
        ("date",    date_pipe, ["date"]),
        ("region",  cat_pipe,  ["region"]),
        ("product", cat_pipe,  ["product"]),
    ], remainder="drop")

def build_xgb_pipeline(model_params: dict) -> Pipeline:
    """Pipeline completo: preproc → scale → XGBRegressor"""
    return Pipeline([
        ("preproc", get_preprocessor()),
        ("scale",   StandardScaler(with_mean=False)),
        ("model",   xgb.XGBRegressor(**model_params))
    ])