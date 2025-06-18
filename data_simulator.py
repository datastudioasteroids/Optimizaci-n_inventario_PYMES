import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import (
    SimpleImputer,
    IterativeImputer,
    KNNImputer
)
from faker import Faker
import random
import argparse

class DataSimulator:
    def __init__(self, df_or_path, encoding='utf-8'):
        if isinstance(df_or_path, str):
            print(f"[INFO] Cargando dataset desde: {df_or_path} con encoding={encoding}")
            try:
                self.df = pd.read_csv(df_or_path, encoding=encoding)
            except UnicodeDecodeError:
                alt = 'latin1' if encoding!='latin1' else 'utf-8'
                print(f"[WARN] Decodificación {encoding} fallida, reintentando con {alt}")
                self.df = pd.read_csv(df_or_path, encoding=alt)
        else:
            self.df = df_or_path.copy()
        self.fake = Faker()
        self._infer_types()
        self.logs = []
        self.default_strategy = {
            'numeric':'median', 'categorical':'mode', 'boolean':'mode', 'text':'mode'
        }

    def _infer_types(self):
        self.types = {}
        for col in self.df.columns:
            s = self.df[col]
            if s.dropna().isin([0,1,True,False]).all():
                self.types[col]='boolean'
            elif pd.api.types.is_numeric_dtype(s):
                self.types[col]='numeric'
            elif pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.infer_dtype(s)=='datetime':
                self.types[col]='datetime'
            else:
                n = s.nunique(dropna=True)
                self.types[col]='categorical' if n/len(s)<0.05 or n<50 else 'text'
        return self.types

    def fill_missing(self, col, strategy=None, random_weights=None, end_date=None, freq='D', **kwargs):
        col_type = self.types[col]
        s = self.df[col]
        options = {
            'numeric':['mean','median','mode','constant','iterative','knn','random_uniform'],
            'categorical':['mode','constant'],
            'boolean':['mode','constant'],
            'text':['mode','constant'],
            'datetime':['ffill','bfill','interpolate','generate_range']
        }[col_type]
        strat = (random.choices(options, weights=[random_weights.get(o,1) for o in options])[0]
                 if random_weights else strategy or ( 'generate_range' if col_type=='datetime' and strategy=='generate_range' else self.default_strategy.get(col_type)))
        self.logs.append(f"[STRATEGY] {col} ({col_type})->{strat}")

        if col_type=='datetime' and strat=='generate_range':
            self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
            last = self.df[col].max()
            ed = pd.to_datetime(end_date) if end_date else pd.Timestamp.today()
            rng = pd.date_range(last+pd.Timedelta(1,freq), ed, freq=freq)
            rows = []
            for date in rng:
                row = {col:date}
                for c,t in self.types.items():
                    if c==col: continue
                    if t=='numeric': row[c] = self.df[c].dropna().sample(1).iloc[0]
                    elif t in('categorical','boolean','text'):
                        probs = self.df[c].value_counts(normalize=True)
                        row[c] = np.random.choice(probs.index, p=probs.values)
                    elif t=='datetime':
                        row[c] = self.df[c].dropna().sample(1).iloc[0]
                rows.append(row)
            self.df = pd.concat([self.df, pd.DataFrame(rows)], ignore_index=True)
            return self.df[col]

        if col_type=='numeric':
            if strat=='random_uniform':
                mi,ma = s.min(), s.max()
                filled = s.fillna(pd.Series(np.random.uniform(mi,ma,s.isna().sum()), index=s[s.isna()].index))
            else:
                if strat=='mean': imp = SimpleImputer(strategy='mean')
                elif strat=='median': imp = SimpleImputer(strategy='median')
                elif strat=='mode': imp = SimpleImputer(strategy='most_frequent')
                elif strat=='constant': imp = SimpleImputer(strategy='constant', fill_value=kwargs.get('fill_value',0))
                elif strat=='iterative': imp = IterativeImputer()
                elif strat=='knn': imp = KNNImputer(n_neighbors=kwargs.get('n_neighbors',5))
                filled = imp.fit_transform(s.values.reshape(-1,1)).ravel()
            self.df[col] = filled
            return self.df[col]

        if col_type in ('categorical','boolean','text'):
            if strat=='mode': imp = SimpleImputer(strategy='most_frequent')
            else: imp = SimpleImputer(strategy='constant', fill_value=kwargs.get('fill_value','missing'))
            filled = imp.fit_transform(s.values.reshape(-1,1)).ravel()
            self.df[col] = filled
            return self.df[col]

        if col_type=='datetime':
            if strat=='ffill': self.df[col] = s.ffill()
            elif strat=='bfill': self.df[col] = s.bfill()
            elif strat=='interpolate': self.df[col] = s.interpolate()
            return self.df[col]

        raise ValueError(f"No soportado {strat} para tipo {col_type}")

    def auto_impute_all(self, skip=None, random_weights=None, **kwargs):
        for c in list(self.df.columns):
            if skip and c in skip: continue
            self.fill_missing(c, random_weights=random_weights, **kwargs)
        return self.df

if __name__=='__main__':
    p = argparse.ArgumentParser("DataSimulator imputación y generación")
    p.add_argument('-i','--input', required=True, help='CSV de entrada')
    p.add_argument('-o','--output', required=True, help='CSV de salida')
    p.add_argument('-d','--date-column', help='Columna de fecha para extender')
    p.add_argument('--end-date', help='Fecha límite (YYYY-MM-DD)')
    args = p.parse_args()

    # Inicializar simulador
    sim = DataSimulator(args.input)
    # Si se indica columna fecha, convertirla y actualizar tipo
    if args.date_column:
        # Convertir a datetime
        sim.df[args.date_column] = pd.to_datetime(sim.df[args.date_column], errors='coerce')
        # Actualizar tipo en el mapeo
        sim.types[args.date_column] = 'datetime'
        # Generar filas hasta end_date sin afectar existentes
        sim.fill_missing(
            args.date_column,
            strategy='generate_range',
            end_date=args.end_date,
            freq='D'
        )
        # Imputar resto, sin tocar la columna de fecha
        df = sim.auto_impute_all(skip=[args.date_column])
    else:
        # Solo imputación general
        df = sim.auto_impute_all()

    # Guardar resultado
    df.to_csv(args.output, index=False)
    print(f"[INFO] CSV completo guardado en: {args.output}")
    # Mostrar log de estrategias
    for log in sim.logs:
        print(log)
