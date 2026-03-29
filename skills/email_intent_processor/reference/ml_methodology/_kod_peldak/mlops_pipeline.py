"""
MLOps Pipeline - Kod Peldak
============================

10. fejezet: MLOps es Deployment

Ez a fajl a Cubix ML Engineer kepzes 7. heti anyagat dolgozza fel:
- MLModel osztaly (preprocessing, train, inference, artifact management)
- Train Pipeline (adat betoltes --> eloeldolgozas --> tanitas --> mentes)
- Inference Pipeline (artifact betoltes --> eloeldolgozas --> predikio)
- Flask REST API (/train, /predict vegpontok)
- Teszteles (pytest-kompatibilis tesztek)

A pelda self-contained: sklearn.datasets.make_classification-t hasznal,
igy kulso CSV fajl nelkul is futtathato.

Futtatas:
    python mlops_pipeline.py

Tesztek futtatasa:
    pytest mlops_pipeline.py -v
"""

import os
import sys
import json
import time
import tempfile
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# Sklearn - adatgeneralas
from sklearn.datasets import make_classification

# Sklearn - eloeldolgozas
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split

# Sklearn - modell (fallback, ha XGBoost nem elerheto)
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

# Sklearn - metrikak
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)

# Sklearn - pipeline
from sklearn.pipeline import Pipeline

# Pickle a modell es artifact menteshez
import pickle

# XGBoost - opcionalis import
try:
    from xgboost import XGBClassifier
    XGBOOST_ELERHETO = True
except ImportError:
    XGBOOST_ELERHETO = False
    print("[INFO] xgboost csomag nem elerheto. Fallback: GradientBoostingClassifier")
    print("       Telepites: pip install xgboost")

# Flask - opcionalis import (REST API-hoz)
try:
    from flask import Flask, request, jsonify
    FLASK_ELERHETO = True
except ImportError:
    FLASK_ELERHETO = False
    print("[INFO] flask csomag nem elerheto. REST API demo kimarad.")
    print("       Telepites: pip install flask")

# flask-restx - opcionalis import (Swagger dokumentaciohoz)
try:
    from flask_restx import Api, Resource, Namespace
    FLASK_RESTX_ELERHETO = True
except ImportError:
    FLASK_RESTX_ELERHETO = False
    if FLASK_ELERHETO:
        print("[INFO] flask-restx nem elerheto. Egyszeru Flask API-t hasznalunk.")
        print("       Telepites: pip install flask-restx")


# =============================================================================
# 0. KONSTANSOK ES KONFIGURACIO
# =============================================================================

# Feature oszlopok definialasa (a kurzus constants.py mintajara)
# Az eredeti kurzus a horse-colic adatkeszletet hasznalja, de itt
# szintetikus adatokkal dolgozunk a fuggetlen futtathatosag erdekeben.

RANDOM_SEED = 42
TEST_SIZE = 0.2
N_SAMPLES = 1000
N_FEATURES = 15
N_INFORMATIVE = 10
N_CLASSES = 3

# Modell mentesi konyvtar
DEFAULT_MODEL_DIR = os.path.join(tempfile.gettempdir(), "mlops_pipeline_models")

# Szintetikus kategorikus feature nevek (a one-hot encoding demonstralasahoz)
CATEGORICAL_FEATURE_NAMES = ["surgery", "age_category", "temp_category"]
SURGERY_VALUES = ["yes", "no"]
AGE_VALUES = ["young", "adult", "old"]
TEMP_VALUES = ["cold", "cool", "normal", "warm", "hot"]


# =============================================================================
# 1. SZINTETIKUS ADAT GENERALAS
# =============================================================================

def szintetikus_adat_generalas(n_samples=N_SAMPLES, random_state=RANDOM_SEED):
    """
    Szintetikus adatkeszlet generalasa a pipeline demonstralasahoz.

    Az eredeti kurzus a horse-colic datasetet hasznalja, mi viszont
    sklearn make_classification-t hasznalunk, kiegeszitve veletlenszeru
    kategorikus feature-okel es hianyzo ertekekkel.

    Args:
        n_samples: generalt mintak szama
        random_state: reprodukalhatosagi seed

    Returns:
        pd.DataFrame: szintetikus adatkeszlet numerikus es kategorikus feature-okel
    """
    np.random.seed(random_state)

    # Numerikus feature-ok generalasa
    X, y = make_classification(
        n_samples=n_samples,
        n_features=N_FEATURES,
        n_informative=N_INFORMATIVE,
        n_redundant=2,
        n_classes=N_CLASSES,
        random_state=random_state,
    )

    # DataFrame letrehozasa
    feature_names = [f"feature_{i:02d}" for i in range(N_FEATURES)]
    df = pd.DataFrame(X, columns=feature_names)

    # Kategorikus feature-ok hozzaadasa
    df["surgery"] = np.random.choice(SURGERY_VALUES, size=n_samples)
    df["age_category"] = np.random.choice(AGE_VALUES, size=n_samples)
    df["temp_category"] = np.random.choice(TEMP_VALUES, size=n_samples)

    # Cel-valtozo
    df["target"] = y

    # Hianyzo ertekek bevitele (realisztikus korulmenyek szimulalasa)
    # ~5% hianyzo ertek a numerikus feature-okban
    mask = np.random.random(size=(n_samples, N_FEATURES)) < 0.05
    for i, col in enumerate(feature_names):
        df.loc[mask[:, i], col] = np.nan

    # ~3% hianyzo ertek a kategorikus feature-okban
    for col in CATEGORICAL_FEATURE_NAMES:
        mask_cat = np.random.random(size=n_samples) < 0.03
        df.loc[mask_cat, col] = np.nan

    # Neha '?' ertekek (ahogy a horse-colic adatban is elofordulnak)
    qmark_mask = np.random.random(size=n_samples) < 0.02
    df.loc[qmark_mask, "feature_00"] = "?"
    df.loc[qmark_mask, "feature_01"] = "?"

    print(f"[Adat] Szintetikus adatkeszlet generalva: {df.shape[0]} sor, {df.shape[1]} oszlop")
    print(f"  Hianyzo ertekek: {df.isna().sum().sum()} db")
    print(f"  '?' ertekek: {(df == '?').sum().sum()} db")
    print(f"  Target eloszlas: {dict(df['target'].value_counts())}")

    return df


# =============================================================================
# 2. FEATURE ENGINEERING (a kurzus utils.py mintajara)
# =============================================================================

def create_new_features(df):
    """
    Domain-specifikus uj feature-ok letrehozasa.

    Az eredeti kurzusban ez a horse-colic adathalmazra vonatkozott
    (pl. test-pulse arany). Mi itt altalanos szintetikus feature-oket
    hozunk letre a pipeline demonstralasahoz.

    Args:
        df: bemeneti DataFrame

    Returns:
        df: bovitett DataFrame uj feature-okkel
    """
    df = df.copy()

    # Numerikus feature-ok listaja (target nelkul)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != "target"]

    # Uj feature: az elso ket numerikus feature aranya
    if "feature_00" in df.columns and "feature_01" in df.columns:
        # Nulla-osztodas elkerulese
        df["ratio_00_01"] = df["feature_00"].astype(float) / (
            df["feature_01"].astype(float).replace(0, np.nan)
        )

    # Uj feature: az elso harom feature atlaga
    first_three = [c for c in ["feature_00", "feature_01", "feature_02"] if c in df.columns]
    if len(first_three) == 3:
        df["mean_first_three"] = df[first_three].astype(float).mean(axis=1)

    # Uj feature: numerikus feature-ok szorasa (volatilitas indikator)
    if len(numeric_cols) >= 5:
        df["std_first_five"] = df[numeric_cols[:5]].astype(float).std(axis=1)

    return df


# =============================================================================
# 3. MLMODEL OSZTALY (a kurzus MLModel.py mintajara)
# =============================================================================

class MLModel:
    """
    ML modell osztaly: eloeldolgozas, tanitas, inference, artifact kezeles.

    Ez az osztaly a kurzusban bemutatott MLModel.py adaptacioja,
    szintetikus adatokra es sklearn-alapu modellre alkalmazva.

    Fobb metodusok:
        - preprocessing_pipeline(df): teljes train eloeldolgozas
        - preprocessing_pipeline_inference(sample_data): inference eloeldolgozas
        - train_and_save_model(df): modell tanitas es mentes
        - predict(inference_row): end-to-end predikio
        - save_model / load_model: artifact I/O
    """

    def __init__(self, model_dir=None):
        """
        Inicializalas: ha letezo artifact-ek vannak, betoltjuk oket.

        Args:
            model_dir: artifact-ek (encoder, scaler, model) mentesi konyvtar
        """
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.model = None
        self.encoder = None
        self.scaler = None
        self.imputer_numeric = None
        self.imputer_categorical = None
        self.label_encoders = {}
        self.train_columns = None
        self.target_col = "target"
        self.categorical_cols = []
        self.numeric_cols = []

        # Metrika tarolasa
        self._train_accuracy = None
        self._test_accuracy = None
        self._train_f1 = None
        self._test_f1 = None

        # Ha leteznek mentett artifact-ek, betoltjuk
        if os.path.exists(os.path.join(self.model_dir, "model.pkl")):
            self._load_artifacts()
            print(f"[MLModel] Betoltott artifact-ek: {self.model_dir}")

    # -----------------------------------------------------------------
    # TRAIN PIPELINE
    # -----------------------------------------------------------------

    def preprocessing_pipeline(self, df):
        """
        Teljes train eloeldolgozasi pipeline.

        Lepesek:
        1. '?' ertekek csere NaN-ra
        2. Oszlopnevek tisztitasa
        3. Feature engineering (uj feature-ok)
        4. Numerikus es kategorikus oszlopok azonositasa
        5. Hianyzo ertekek kezeles (imputer fit_transform)
        6. Outlier kezeles (Z-score)
        7. OneHot encoding (encoder fit_transform)
        8. MinMaxScaler (scaler fit_transform)
        9. Artifact-ek mentese

        Args:
            df: nyers bemeneti DataFrame (target oszloppal)

        Returns:
            pd.DataFrame: eloeldolgozott DataFrame
        """
        df = df.copy()
        print("\n[Train Pipeline] Eloeldolgozas inditasa...")

        # 1. '?' ertekek csere NaN-ra (horse-colic adatban gyakori)
        df = df.replace("?", np.nan)
        print(f"  1. '?' --> NaN csere kesz. Hianyzo ertekek: {df.isna().sum().sum()}")

        # 2. Oszlopnevek tisztitasa (szokozok, specialis karakterek)
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
        print(f"  2. Oszlopnevek tisztitva: {len(df.columns)} oszlop")

        # 3. Feature engineering
        df = create_new_features(df)
        print(f"  3. Feature engineering kesz. Oszlopok szama: {len(df.columns)}")

        # 4. Oszlopok tipizalasa
        # A target-et kulon kezeljuk
        target = df[self.target_col].copy() if self.target_col in df.columns else None

        feature_cols = [c for c in df.columns if c != self.target_col]

        # Kategorikus: object tipusu oszlopok
        self.categorical_cols = df[feature_cols].select_dtypes(
            include=["object", "category"]
        ).columns.tolist()

        # Numerikus: nem object tipusu oszlopok
        self.numeric_cols = df[feature_cols].select_dtypes(
            include=[np.number]
        ).columns.tolist()

        print(f"  4. Tipizalas: {len(self.numeric_cols)} numerikus, "
              f"{len(self.categorical_cols)} kategorikus")

        # 5. Hianyzo ertekek kezeles -- IMPUTER FIT_TRANSFORM
        # Numerikus: median strategia
        if self.numeric_cols:
            # Biztositsuk, hogy numerikus tipusra konvertalunk
            for col in self.numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            self.imputer_numeric = SimpleImputer(strategy="median")
            df[self.numeric_cols] = self.imputer_numeric.fit_transform(
                df[self.numeric_cols]
            )

        # Kategorikus: most_frequent (modusz) strategia
        if self.categorical_cols:
            self.imputer_categorical = SimpleImputer(strategy="most_frequent")
            df[self.categorical_cols] = self.imputer_categorical.fit_transform(
                df[self.categorical_cols]
            )

        remaining_na = df[feature_cols].isna().sum().sum()
        print(f"  5. Hianyzo ertekek kezelve. Maradek NaN: {remaining_na}")

        # 6. Outlier kezeles -- Z-score (|z| > 3 --> median)
        outlier_count = 0
        for col in self.numeric_cols:
            col_std = df[col].std()
            if col_std > 0:
                z_scores = np.abs((df[col] - df[col].mean()) / col_std)
                mask = z_scores > 3
                outlier_count += mask.sum()
                df.loc[mask, col] = df[col].median()

        print(f"  6. Outlier kezeles (Z-score > 3): {outlier_count} ertek cserelve")

        # 7. OneHot encoding -- ENCODER FIT_TRANSFORM
        if self.categorical_cols:
            self.encoder = OneHotEncoder(
                sparse_output=False,
                handle_unknown="ignore",
                drop=None,
            )
            encoded_array = self.encoder.fit_transform(df[self.categorical_cols])
            encoded_cols = self.encoder.get_feature_names_out(self.categorical_cols)
            encoded_df = pd.DataFrame(
                encoded_array,
                columns=encoded_cols,
                index=df.index,
            )
            df = df.drop(columns=self.categorical_cols)
            df = pd.concat([df, encoded_df], axis=1)
            print(f"  7. OneHot encoding kesz. Uj oszlopok: {len(encoded_cols)}")
        else:
            print("  7. OneHot encoding: nincs kategorikus oszlop")

        # 8. MinMaxScaler -- SCALER FIT_TRANSFORM
        feature_cols_final = [c for c in df.columns if c != self.target_col]
        numeric_final = df[feature_cols_final].select_dtypes(
            include=[np.number]
        ).columns.tolist()

        if numeric_final:
            self.scaler = MinMaxScaler()
            df[numeric_final] = self.scaler.fit_transform(df[numeric_final])
            print(f"  8. MinMaxScaler alkalmazva {len(numeric_final)} oszlopra")

        # A train oszlopok mentese (inference-hez kell)
        self.train_columns = [c for c in df.columns if c != self.target_col]

        # Target visszarakasa
        if target is not None:
            df[self.target_col] = target.values

        # 9. Artifact-ek mentese
        self._save_artifacts()
        print(f"  9. Artifact-ek mentve: {self.model_dir}")

        print(f"[Train Pipeline] Kesz. Vegso alak: {df.shape}")
        return df

    # -----------------------------------------------------------------
    # INFERENCE PIPELINE
    # -----------------------------------------------------------------

    def preprocessing_pipeline_inference(self, sample_data):
        """
        Inference eloeldolgozas egyetlen adatsorra.

        FONTOS: A mentett artifact-eket hasznalja (transform, NEM fit_transform)!
        Ezzel biztositjuk a train-inference konzisztenciat.

        Args:
            sample_data: dict -- egyetlen adatsor kulcs-ertek parokkal

        Returns:
            pd.DataFrame: eloeldolgozott egyetlen sor
        """
        # Dict --> DataFrame (egyetlen sor)
        df = pd.DataFrame([sample_data])

        # 1. '?' --> NaN
        df = df.replace("?", np.nan)

        # 2. Oszlopnevek tisztitasa (UGYANUGY, mint train-nel)
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]

        # Target eltavolitasa, ha van
        if self.target_col in df.columns:
            df = df.drop(columns=[self.target_col])

        # 3. Feature engineering (UGYANAZ a fuggveny)
        df = create_new_features(df)

        # 4. Kategorikus es numerikus oszlopok
        cat_cols = [c for c in self.categorical_cols if c in df.columns]
        num_cols = [c for c in self.numeric_cols if c in df.columns]

        # 5. Hianyzo ertekek -- MENTETT IMPUTER TRANSFORM
        if num_cols and self.imputer_numeric is not None:
            for col in num_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df[num_cols] = self.imputer_numeric.transform(df[num_cols])

        if cat_cols and self.imputer_categorical is not None:
            df[cat_cols] = self.imputer_categorical.transform(df[cat_cols])

        # 6. Outlier kezeles -- inference eseten nem csinalkunk
        # (az outlier thresholdokat a train adatbol szamoltuk)

        # 7. OneHot encoding -- MENTETT ENCODER TRANSFORM
        if cat_cols and self.encoder is not None:
            encoded_array = self.encoder.transform(df[cat_cols])
            encoded_cols = self.encoder.get_feature_names_out(self.categorical_cols)
            encoded_df = pd.DataFrame(
                encoded_array,
                columns=encoded_cols,
                index=df.index,
            )
            df = df.drop(columns=cat_cols)
            df = pd.concat([df, encoded_df], axis=1)

        # 8. MinMaxScaler -- MENTETT SCALER TRANSFORM
        if self.scaler is not None:
            numeric_final = df.select_dtypes(include=[np.number]).columns.tolist()
            # Csak azokra alkalmazzuk, amiket a scaler ismer
            valid_cols = [c for c in numeric_final if c in self.train_columns]
            if valid_cols:
                # A scaler a train feature-ok sorrendjeben varja az adatot
                scaler_cols = [c for c in self.train_columns
                               if c in df.columns and c in valid_cols]
                if scaler_cols:
                    df[scaler_cols] = self.scaler.transform(df[scaler_cols])

        # Biztositsuk, hogy a train-nel letezo oszlopok mind megvannak
        for col in self.train_columns:
            if col not in df.columns:
                df[col] = 0  # Hianyzo oszlop default erteke

        # Oszlop-sorrend illesztese a train adatokhoz
        df = df[self.train_columns]

        return df

    # -----------------------------------------------------------------
    # MODELL TANITAS
    # -----------------------------------------------------------------

    def train_and_save_model(self, df, target_col=None):
        """
        Modell tanitas es mentes.

        Args:
            df: eloeldolgozott DataFrame (target oszloppal)
            target_col: cel-valtozo neve (alapertek: self.target_col)

        Returns:
            float: test accuracy
        """
        target_col = target_col or self.target_col

        if target_col not in df.columns:
            raise ValueError(f"A target oszlop '{target_col}' nem talalhato a DataFrame-ben!")

        X = df.drop(columns=[target_col])
        y = df[target_col]

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=y
        )

        print(f"\n[Train] Modell tanitas inditasa...")
        print(f"  Train meret: {X_train.shape[0]}, Test meret: {X_test.shape[0]}")
        print(f"  Feature-ok szama: {X_train.shape[1]}")

        # Modell valasztas
        if XGBOOST_ELERHETO:
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=RANDOM_SEED,
                use_label_encoder=False,
                eval_metric="mlogloss",
            )
            model_name = "XGBClassifier"
        else:
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=RANDOM_SEED,
            )
            model_name = "GradientBoostingClassifier"

        # Tanitas
        start_time = time.time()
        self.model.fit(X_train, y_train)
        train_time = time.time() - start_time

        # Ertekelees
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        self._train_accuracy = accuracy_score(y_train, y_pred_train)
        self._test_accuracy = accuracy_score(y_test, y_pred_test)
        self._train_f1 = f1_score(y_train, y_pred_train, average="weighted")
        self._test_f1 = f1_score(y_test, y_pred_test, average="weighted")

        print(f"\n[Train] Eredmenyek ({model_name}):")
        print(f"  Train Accuracy: {self._train_accuracy:.4f}")
        print(f"  Test Accuracy:  {self._test_accuracy:.4f}")
        print(f"  Train F1:       {self._train_f1:.4f}")
        print(f"  Test F1:        {self._test_f1:.4f}")
        print(f"  Tanitasi ido:   {train_time:.2f}s")

        # Reszletes riport
        print(f"\n  Classification Report (test):")
        report = classification_report(y_test, y_pred_test, zero_division=0)
        for line in report.split("\n"):
            print(f"    {line}")

        # Modell mentese
        self.save_model(self.model, os.path.join(self.model_dir, "model.pkl"))
        self._save_artifacts()

        # Tanulasi naplo mentese
        self._write_training_log(model_name, train_time)

        return self._test_accuracy

    # -----------------------------------------------------------------
    # PREDIKIO
    # -----------------------------------------------------------------

    def predict(self, inference_row):
        """
        End-to-end predikio: eloeldolgozas + modell prediction.

        Args:
            inference_row: dict -- egyetlen adatsor

        Returns:
            int/float: predikalt osztaly
        """
        if self.model is None:
            raise RuntimeError("Nincs betanitott modell! Hivd meg eloszor a "
                               "train_and_save_model() metodust.")

        processed = self.preprocessing_pipeline_inference(inference_row)
        prediction = self.model.predict(processed)
        return prediction[0]

    def predict_proba(self, inference_row):
        """
        Predikio valoszinusegekkel.

        Args:
            inference_row: dict -- egyetlen adatsor

        Returns:
            np.ndarray: osztaly-valoszinusegek
        """
        if self.model is None:
            raise RuntimeError("Nincs betanitott modell!")

        processed = self.preprocessing_pipeline_inference(inference_row)

        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(processed)[0]
        else:
            # Ha a modell nem tamogatja a predict_proba-t
            pred = self.model.predict(processed)[0]
            return np.array([1.0 if i == pred else 0.0
                            for i in range(N_CLASSES)])

    # -----------------------------------------------------------------
    # ACCURACY LEKERDEZESEK
    # -----------------------------------------------------------------

    def get_accuracy(self):
        """Test accuracy lekerdezese."""
        return self._test_accuracy

    def get_accuracy_full(self):
        """Train es test metrikak reszletes lekerdezese."""
        return {
            "train_accuracy": self._train_accuracy,
            "test_accuracy": self._test_accuracy,
            "train_f1": self._train_f1,
            "test_f1": self._test_f1,
        }

    # -----------------------------------------------------------------
    # ARTIFACT I/O
    # -----------------------------------------------------------------

    @staticmethod
    def save_model(model, filepath):
        """Modell mentese pickle fajlba."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(model, f)
        print(f"  [Save] {filepath}")

    @staticmethod
    def load_model(filepath):
        """Modell betoltese pickle fajlbol."""
        with open(filepath, "rb") as f:
            return pickle.load(f)

    def _save_artifacts(self):
        """Osszes artifact (encoder, scaler, imputer, metadata) mentese."""
        os.makedirs(self.model_dir, exist_ok=True)

        artifacts = {
            "encoder.pkl": self.encoder,
            "scaler.pkl": self.scaler,
            "imputer_numeric.pkl": self.imputer_numeric,
            "imputer_categorical.pkl": self.imputer_categorical,
        }

        for filename, obj in artifacts.items():
            if obj is not None:
                filepath = os.path.join(self.model_dir, filename)
                with open(filepath, "wb") as f:
                    pickle.dump(obj, f)

        # Metadata mentese JSON-ben (train_columns, col tipusok)
        metadata = {
            "train_columns": self.train_columns,
            "categorical_cols": self.categorical_cols,
            "numeric_cols": self.numeric_cols,
            "target_col": self.target_col,
            "saved_at": datetime.now().isoformat(),
        }
        meta_path = os.path.join(self.model_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _load_artifacts(self):
        """Osszes artifact betoltese a model_dir-bol."""
        artifacts = {
            "model.pkl": "model",
            "encoder.pkl": "encoder",
            "scaler.pkl": "scaler",
            "imputer_numeric.pkl": "imputer_numeric",
            "imputer_categorical.pkl": "imputer_categorical",
        }

        for filename, attr in artifacts.items():
            filepath = os.path.join(self.model_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    setattr(self, attr, pickle.load(f))

        # Metadata betoltese
        meta_path = os.path.join(self.model_dir, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            self.train_columns = metadata.get("train_columns")
            self.categorical_cols = metadata.get("categorical_cols", [])
            self.numeric_cols = metadata.get("numeric_cols", [])
            self.target_col = metadata.get("target_col", "target")

    @staticmethod
    def create_new_folder(path):
        """Uj mappa letrehozasa, ha nem letezik."""
        os.makedirs(path, exist_ok=True)
        return path

    # -----------------------------------------------------------------
    # TANULASI NAPLO
    # -----------------------------------------------------------------

    def _write_training_log(self, model_name, train_time):
        """Tanulasi naplo fajl irasa."""
        log_path = os.path.join(self.model_dir, "training_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Tanitas ideje: {datetime.now().isoformat()}\n")
            f.write(f"Modell: {model_name}\n")
            f.write(f"Train Accuracy: {self._train_accuracy:.4f}\n")
            f.write(f"Test Accuracy:  {self._test_accuracy:.4f}\n")
            f.write(f"Train F1:       {self._train_f1:.4f}\n")
            f.write(f"Test F1:        {self._test_f1:.4f}\n")
            f.write(f"Tanitasi ido:   {train_time:.2f}s\n")
            f.write(f"Feature-ok:     {len(self.train_columns)}\n")
            f.write(f"Artifact dir:   {self.model_dir}\n")
        print(f"  [Log] Tanulasi naplo: {log_path}")


# =============================================================================
# 4. BATCH INFERENCE
# =============================================================================

def batch_inference(model, df):
    """
    Batch inference: tobb sor egyszerrekszukseges feldolgozasa.

    A batch inference tipikusan utemezve (cron, Airflow) fut,
    es nagy adatmennyiseget dolgoz fel egyszerre.

    Args:
        model: betanitott MLModel objektum
        df: bemeneti DataFrame (target nelkul vagy target-tel)

    Returns:
        pd.DataFrame: az eredeti adatok + prediction oszlop
    """
    print(f"\n[Batch Inference] {len(df)} sor feldolgozasa...")
    start_time = time.time()

    predictions = []
    probabilities = []
    errors = []

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        # Target eltavolitasa, ha van
        row_dict.pop("target", None)

        try:
            pred = model.predict(row_dict)
            proba = model.predict_proba(row_dict)
            predictions.append(pred)
            probabilities.append(max(proba))
            errors.append(None)
        except Exception as e:
            predictions.append(None)
            probabilities.append(None)
            errors.append(str(e))

    result_df = df.copy()
    result_df["prediction"] = predictions
    result_df["confidence"] = probabilities
    result_df["error"] = errors

    elapsed = time.time() - start_time
    success_count = sum(1 for e in errors if e is None)
    error_count = sum(1 for e in errors if e is not None)

    print(f"[Batch Inference] Kesz.")
    print(f"  Sikeres: {success_count}, Hibas: {error_count}")
    print(f"  Ido: {elapsed:.2f}s ({elapsed/len(df)*1000:.1f}ms/sor)")

    return result_df


# =============================================================================
# 5. FLASK REST API (a kurzus app.py mintajara)
# =============================================================================

def create_flask_app(model):
    """
    Flask REST API letrehozasa /train es /predict vegpontokkal.

    A kurzus flask_restx + Swagger dokumentaciot hasznal.
    Ha a flask_restx nem elerheto, egyszeru Flask route-okat hasznalunk.

    Args:
        model: MLModel objektum

    Returns:
        Flask app objektum
    """
    if not FLASK_ELERHETO:
        print("[REST API] Flask nem elerheto. API letrehozas kihagyva.")
        return None

    app = Flask(__name__)

    if FLASK_RESTX_ELERHETO:
        # flask-restx valtozat: Swagger dokumentacioval
        api = Api(
            app,
            title="ML Model API",
            version="1.0",
            description="MLOps Pipeline - Train es Predict vegpontok",
        )
        model_ns = Namespace("model", description="Model muveletek")
        api.add_namespace(model_ns)

        @model_ns.route("/train")
        class TrainResource(Resource):
            def post(self):
                """
                Modell tanitas CSV fajlbol.

                POST /model/train
                Content-Type: multipart/form-data
                Body: file = <CSV fajl>

                Visszateresi ertek: JSON {'status', 'accuracy', 'message'}
                """
                try:
                    if "file" not in request.files:
                        return {"status": "error", "message": "Nincs 'file' mezo!"}, 400

                    file = request.files["file"]
                    df = pd.read_csv(file)

                    # Eloeldolgozas (train pipeline)
                    processed_df = model.preprocessing_pipeline(df)

                    # Modell tanitas
                    accuracy = model.train_and_save_model(processed_df)

                    return {
                        "status": "success",
                        "accuracy": float(accuracy),
                        "metrics": model.get_accuracy_full(),
                        "message": f"Modell betanitva. Test accuracy: {accuracy:.4f}",
                    }, 200

                except Exception as e:
                    return {"status": "error", "message": str(e)}, 500

        @model_ns.route("/predict")
        class PredictResource(Resource):
            def post(self):
                """
                Predikio egyetlen adatsorra.

                POST /model/predict
                Content-Type: application/json
                Body: {"feature_00": 1.2, "feature_01": -0.5, ...}

                Visszateresi ertek: JSON {'status', 'prediction', 'confidence'}
                """
                try:
                    inference_row = request.get_json()
                    if inference_row is None:
                        return {"status": "error", "message": "Ures JSON body!"}, 400

                    prediction = model.predict(inference_row)
                    proba = model.predict_proba(inference_row)

                    return {
                        "status": "success",
                        "prediction": int(prediction),
                        "confidence": float(max(proba)),
                        "probabilities": {
                            f"class_{i}": float(p) for i, p in enumerate(proba)
                        },
                    }, 200

                except Exception as e:
                    return {"status": "error", "message": str(e)}, 500

        @model_ns.route("/health")
        class HealthResource(Resource):
            def get(self):
                """Health check vegpont."""
                has_model = model.model is not None
                return {
                    "status": "ok" if has_model else "no_model",
                    "model_loaded": has_model,
                    "metrics": model.get_accuracy_full() if has_model else None,
                }, 200

    else:
        # Egyszeru Flask valtozat (flask-restx nelkul)

        @app.route("/model/train", methods=["POST"])
        def train_endpoint():
            try:
                file = request.files["file"]
                df = pd.read_csv(file)
                processed_df = model.preprocessing_pipeline(df)
                accuracy = model.train_and_save_model(processed_df)
                return jsonify({
                    "status": "success",
                    "accuracy": float(accuracy),
                })
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/model/predict", methods=["POST"])
        def predict_endpoint():
            try:
                inference_row = request.get_json()
                prediction = model.predict(inference_row)
                return jsonify({
                    "status": "success",
                    "prediction": int(prediction),
                })
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/model/health", methods=["GET"])
        def health_endpoint():
            return jsonify({
                "status": "ok" if model.model is not None else "no_model",
            })

    return app


# =============================================================================
# 6. SKLEARN PIPELINE ALTERNATIVA
# =============================================================================

def sklearn_pipeline_demo():
    """
    Sklearn Pipeline hasznalata a train-inference konzisztencia biztositasara.

    Az sklearn Pipeline garantalja, hogy a train es inference soran
    pontosan ugyanazok az eloeldolgozasi lepesek futnak le.
    Ez az egyik legjobb modszer a training-serving skew elkerulese.
    """
    print("\n" + "=" * 60)
    print("  SKLEARN PIPELINE DEMO")
    print("=" * 60)

    # Adatgeneralas (csak numerikus, az egyszeru demokert)
    X, y = make_classification(
        n_samples=500,
        n_features=10,
        n_informative=7,
        n_classes=2,
        random_state=RANDOM_SEED,
    )

    # Hianyzo ertekek bevitele
    mask = np.random.random(X.shape) < 0.05
    X[mask] = np.nan

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED
    )

    # Pipeline definialasa
    if XGBOOST_ELERHETO:
        classifier = XGBClassifier(
            n_estimators=50, max_depth=3, random_state=RANDOM_SEED,
            use_label_encoder=False, eval_metric="logloss",
        )
        model_name = "XGBClassifier"
    else:
        classifier = GradientBoostingClassifier(
            n_estimators=50, max_depth=3, random_state=RANDOM_SEED,
        )
        model_name = "GradientBoostingClassifier"

    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", MinMaxScaler()),
        ("model", classifier),
    ])

    # Train -- a pipeline fit() egyetlen hivassal vegigfut
    print(f"\n[Pipeline] Tanitas {model_name}-rel...")
    pipeline.fit(X_train, y_train)

    # Inference -- a pipeline predict() GARANTALTAN ugyanazt
    # az eloeldolgozast vegzi, mint a fit() soran
    y_pred_train = pipeline.predict(X_train)
    y_pred_test = pipeline.predict(X_test)

    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)

    print(f"  Train Accuracy: {train_acc:.4f}")
    print(f"  Test Accuracy:  {test_acc:.4f}")

    # Pipeline mentese egyetlen pickle fajlba
    pipeline_path = os.path.join(DEFAULT_MODEL_DIR, "sklearn_pipeline.pkl")
    os.makedirs(os.path.dirname(pipeline_path), exist_ok=True)
    with open(pipeline_path, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"  Pipeline mentve: {pipeline_path}")

    # Pipeline betoltese es hasznalata
    with open(pipeline_path, "rb") as f:
        loaded_pipeline = pickle.load(f)
    y_pred_loaded = loaded_pipeline.predict(X_test)
    loaded_acc = accuracy_score(y_test, y_pred_loaded)
    print(f"  Betoltott pipeline accuracy: {loaded_acc:.4f}")
    assert loaded_acc == test_acc, "Pipeline konzisztencia hiba!"
    print("  [OK] Pipeline konzisztencia ellenorzes sikeres")

    return pipeline


# =============================================================================
# 7. DATA DRIFT DETEKTALAS DEMO
# =============================================================================

def data_drift_demo():
    """
    Egyszeru data drift detektalas statisztikai teszttel.

    A Kolmogorov-Smirnov (KS) teszt ket eloszlast hasonlit ossze.
    Ha a p-ertek alacsony (< 0.05), az eloszlasok szignifikansan elternek,
    ami data driftre utal.
    """
    from scipy.stats import ks_2samp

    print("\n" + "=" * 60)
    print("  DATA DRIFT DETEKTALAS DEMO")
    print("=" * 60)

    np.random.seed(RANDOM_SEED)

    # Szimulalt train es production adatok
    train_data = np.random.normal(loc=0.0, scale=1.0, size=500)

    # 1. eset: nincs drift (hasonlo eloszlas)
    prod_data_no_drift = np.random.normal(loc=0.0, scale=1.0, size=500)

    # 2. eset: kicsi drift (kis eltolodas)
    prod_data_small_drift = np.random.normal(loc=0.3, scale=1.0, size=500)

    # 3. eset: nagy drift (jelentos eltolodas)
    prod_data_large_drift = np.random.normal(loc=1.5, scale=2.0, size=500)

    scenarios = [
        ("Nincs drift", prod_data_no_drift),
        ("Kicsi drift", prod_data_small_drift),
        ("Nagy drift", prod_data_large_drift),
    ]

    print(f"\n  {'Szcenario':<20} {'KS Statistic':>14} {'p-value':>12} {'Drift?':>10}")
    print("  " + "-" * 58)

    for name, prod_data in scenarios:
        stat, p_value = ks_2samp(train_data, prod_data)
        drift_detected = "IGEN" if p_value < 0.05 else "nem"
        print(f"  {name:<20} {stat:>14.4f} {p_value:>12.6f} {drift_detected:>10}")

    print("\n  [INFO] Ha p-value < 0.05 --> szignifikans kulonbseg --> data drift")
    print("  [INFO] Production-ben ezt minden feature-re rendszeresen futtatni kell")


# =============================================================================
# 8. PYTEST-KOMPATIBILIS TESZTEK
# =============================================================================

# A teszteket pytest-tel is futtathatjuk: pytest mlops_pipeline.py -v

def _get_trained_model():
    """Segedfuggveny: betanitott modell letrehozasa tesztekhez."""
    model = MLModel(model_dir=os.path.join(DEFAULT_MODEL_DIR, "test_model"))
    df = szintetikus_adat_generalas(n_samples=200, random_state=42)
    processed_df = model.preprocessing_pipeline(df)
    model.train_and_save_model(processed_df)
    return model, df


def test_szintetikus_adat_generalas():
    """Ellenorzi, hogy a szintetikus adat generalas megfelelo."""
    df = szintetikus_adat_generalas(n_samples=100)
    assert len(df) == 100, f"Elv: 100 sor, kapott: {len(df)}"
    assert "target" in df.columns, "Hianyzo target oszlop"
    assert "surgery" in df.columns, "Hianyzo kategorikus oszlop"
    assert df["target"].nunique() == N_CLASSES, "Hibas osztaly szam"
    print("[TESZT OK] szintetikus_adat_generalas")


def test_create_new_features():
    """Ellenorzi, hogy az uj feature-ok letrejottek."""
    df = szintetikus_adat_generalas(n_samples=50)
    df_new = create_new_features(df)
    assert "ratio_00_01" in df_new.columns, "Hianyzo ratio feature"
    assert "mean_first_three" in df_new.columns, "Hianyzo mean feature"
    assert "std_first_five" in df_new.columns, "Hianyzo std feature"
    assert len(df_new) == len(df), "Sorszam megvaltozott"
    print("[TESZT OK] create_new_features")


def test_preprocessing_pipeline():
    """Ellenorzi a teljes train pipeline-t."""
    model = MLModel(model_dir=os.path.join(DEFAULT_MODEL_DIR, "test_preprocess"))
    df = szintetikus_adat_generalas(n_samples=100)
    processed = model.preprocessing_pipeline(df)

    # Nincs hianyzo ertek (a target-et leszamitva)
    feature_cols = [c for c in processed.columns if c != "target"]
    assert processed[feature_cols].isna().sum().sum() == 0, "Maradek NaN ertek!"

    # Az artifact-ek mentve lettek
    assert os.path.exists(os.path.join(model.model_dir, "scaler.pkl"))
    assert os.path.exists(os.path.join(model.model_dir, "metadata.json"))

    print("[TESZT OK] preprocessing_pipeline")


def test_train_and_save_model():
    """Ellenorzi a modell tanitas es mentes folyamatot."""
    model = MLModel(model_dir=os.path.join(DEFAULT_MODEL_DIR, "test_train"))
    df = szintetikus_adat_generalas(n_samples=200)
    processed = model.preprocessing_pipeline(df)
    accuracy = model.train_and_save_model(processed)

    assert accuracy > 0.3, f"Pontossag tul alacsony: {accuracy:.4f}"
    assert os.path.exists(os.path.join(model.model_dir, "model.pkl"))

    metrics = model.get_accuracy_full()
    assert metrics["train_accuracy"] is not None
    assert metrics["test_accuracy"] is not None

    print(f"[TESZT OK] train_and_save_model (accuracy: {accuracy:.4f})")


def test_predict():
    """Ellenorzi az end-to-end predikiot."""
    model, df = _get_trained_model()

    # Egy sor kivalasztasa (target nelkul)
    sample = df.iloc[0].to_dict()
    sample.pop("target", None)

    prediction = model.predict(sample)
    assert prediction in range(N_CLASSES), f"Ervenytelen predikio: {prediction}"

    # Valoszinusegek ellenorzese
    proba = model.predict_proba(sample)
    assert len(proba) == N_CLASSES, "Hibas valoszinuseg vektor hossz"
    assert abs(sum(proba) - 1.0) < 0.01, "Valoszinusegek nem adnak ki 1-et"

    print(f"[TESZT OK] predict (prediction: {prediction}, "
          f"confidence: {max(proba):.4f})")


def test_train_inference_konzisztencia():
    """
    KRITIKUS TESZT: a train es inference pipeline konzisztenciaja.

    Ez a legfontosabb teszt ML rendszerekben. Biztositja, hogy a
    train pipeline es az inference pipeline ugyanazt az eloeldolgozast
    vegezze, elkerulve a training-serving skew-t.
    """
    model, df = _get_trained_model()

    # Train eredmenyek
    train_accuracy = model.get_accuracy()
    assert train_accuracy is not None, "Nincs train accuracy"
    assert train_accuracy > 0.3, f"Train accuracy tul alacsony: {train_accuracy}"

    # Inference -- az elso train sorral
    sample = df.iloc[0].to_dict()
    sample.pop("target", None)
    prediction = model.predict(sample)

    assert prediction in range(N_CLASSES), f"Ervenytelen prediction: {prediction}"

    # Feature szam ellenorzese: a train es inference oszlopszamnak
    # egyeznie kell
    processed_inference = model.preprocessing_pipeline_inference(sample)
    assert len(processed_inference.columns) == len(model.train_columns), \
        (f"Feature szam elteres! Train: {len(model.train_columns)}, "
         f"Inference: {len(processed_inference.columns)}")

    print(f"[TESZT OK] train_inference_konzisztencia "
          f"(accuracy: {train_accuracy:.4f}, pred: {prediction})")


def test_artifact_save_load():
    """Ellenorzi az artifact-ek menteset es betoltest."""
    # Elso modell: tanitas es mentes
    model_dir = os.path.join(DEFAULT_MODEL_DIR, "test_saveload")
    model1 = MLModel(model_dir=model_dir)
    df = szintetikus_adat_generalas(n_samples=200)
    processed = model1.preprocessing_pipeline(df)
    accuracy1 = model1.train_and_save_model(processed)

    # Masodik modell: betoltes az elozo artifact-ekbol
    model2 = MLModel(model_dir=model_dir)

    # Ugyanaz a predikio kell mindkettobol
    sample = df.iloc[5].to_dict()
    sample.pop("target", None)
    pred1 = model1.predict(sample)
    pred2 = model2.predict(sample)

    assert pred1 == pred2, f"Artifact I/O hiba! Pred1: {pred1}, Pred2: {pred2}"
    print(f"[TESZT OK] artifact_save_load (pred1=pred2={pred1})")


def test_batch_inference():
    """Ellenorzi a batch inference mukodeset."""
    model, df = _get_trained_model()

    # 10 soros batch
    batch_df = df.head(10).copy()
    result = batch_inference(model, batch_df)

    assert "prediction" in result.columns, "Hianyzo prediction oszlop"
    assert "confidence" in result.columns, "Hianyzo confidence oszlop"
    assert result["prediction"].notna().all(), "Van NaN predikio"
    assert (result["error"].isna()).all(), "Van hibas sor"

    print(f"[TESZT OK] batch_inference ({len(result)} sor feldolgozva)")


def test_model_not_overfitting():
    """
    Ellenorzi, hogy a modell nem overfitting-el.
    A train es test accuracy kozotti kulonbseg ne legyen tul nagy.
    """
    model, _ = _get_trained_model()
    metrics = model.get_accuracy_full()

    gap = metrics["train_accuracy"] - metrics["test_accuracy"]
    assert gap < 0.25, (
        f"Overfitting gyanuja! Train: {metrics['train_accuracy']:.4f}, "
        f"Test: {metrics['test_accuracy']:.4f}, Gap: {gap:.4f}"
    )
    print(f"[TESZT OK] model_not_overfitting "
          f"(gap: {gap:.4f}, max: 0.25)")


# =============================================================================
# 9. DEPLOYMENT STRATEGIA SZIMULACIO
# =============================================================================

def deployment_strategia_demo():
    """
    Deployment strategiak szimulalasa szintetikus forgalommal.

    Bemutatja a canary, A/B es blue-green deployment logikajat.
    """
    print("\n" + "=" * 60)
    print("  DEPLOYMENT STRATEGIA SZIMULACIO")
    print("=" * 60)

    np.random.seed(RANDOM_SEED)

    # Ket "modell" szimulalasa (kulonbozo pontossaggal)
    model_v1_accuracy = 0.82  # regi modell
    model_v2_accuracy = 0.88  # uj modell

    n_requests = 1000

    def simulate_model(accuracy, n=1):
        """Modell predikciot szimulal adott accuracy-vel."""
        return np.random.random(n) < accuracy

    # -----------------------------------------------------------------
    # CANARY DEPLOYMENT
    # -----------------------------------------------------------------
    print("\n--- Canary Deployment ---")
    canary_phases = [
        ("Phase 1", 0.05),  # 5% canary
        ("Phase 2", 0.25),  # 25% canary
        ("Phase 3", 0.50),  # 50% canary
        ("Phase 4", 1.00),  # 100% (full rollout)
    ]

    print(f"  {'Fazis':<12} {'V2 %':>6} {'V1 acc':>10} {'V2 acc':>10} {'Overall':>10}")
    print("  " + "-" * 50)

    for phase_name, v2_ratio in canary_phases:
        n_v2 = int(n_requests * v2_ratio)
        n_v1 = n_requests - n_v2

        v1_correct = simulate_model(model_v1_accuracy, n_v1).sum() if n_v1 > 0 else 0
        v2_correct = simulate_model(model_v2_accuracy, n_v2).sum() if n_v2 > 0 else 0

        v1_acc = v1_correct / n_v1 if n_v1 > 0 else 0
        v2_acc = v2_correct / n_v2 if n_v2 > 0 else 0
        overall = (v1_correct + v2_correct) / n_requests

        print(f"  {phase_name:<12} {v2_ratio*100:>5.0f}% "
              f"{v1_acc:>9.4f} {v2_acc:>9.4f} {overall:>9.4f}")

    # -----------------------------------------------------------------
    # A/B TESTING
    # -----------------------------------------------------------------
    print("\n--- A/B Testing ---")
    n_ab = 500  # mintameret csoportonkent
    v1_results = simulate_model(model_v1_accuracy, n_ab)
    v2_results = simulate_model(model_v2_accuracy, n_ab)

    v1_success_rate = v1_results.mean()
    v2_success_rate = v2_results.mean()

    # Egyszeru statisztikai teszt (z-teszt)
    p1, p2 = v1_success_rate, v2_success_rate
    n1, n2 = n_ab, n_ab
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    z_stat = (p2 - p1) / se if se > 0 else 0

    print(f"  V1 (control): {v1_success_rate:.4f} ({n_ab} keres)")
    print(f"  V2 (variant): {v2_success_rate:.4f} ({n_ab} keres)")
    print(f"  Z-statistic:  {z_stat:.4f}")
    print(f"  Szignifikans (|z| > 1.96)? {'IGEN' if abs(z_stat) > 1.96 else 'NEM'}")

    # -----------------------------------------------------------------
    # BLUE-GREEN DEPLOYMENT
    # -----------------------------------------------------------------
    print("\n--- Blue-Green Deployment ---")
    print("  1. Blue (V1) aktiv, Green (V2) keszenleti")
    print(f"     Blue acc: {model_v1_accuracy:.2f}")
    print("  2. Atkapcsolas: Load Balancer --> Green")
    print(f"     Green acc: {model_v2_accuracy:.2f}")
    print("  3. Ha problema van: azonnali rollback Blue-ra")
    print(f"     Rollback ido: < 1 masodperc")


# =============================================================================
# FO PROGRAM
# =============================================================================

if __name__ == "__main__":

    print("=" * 70)
    print("  MLOPS PIPELINE - TELJES DEMONSTRACIO")
    print("  10. fejezet: MLOps es Deployment")
    print("=" * 70)

    warnings.filterwarnings("ignore")

    # -----------------------------------------------------------------
    # 1. Adatgeneralas
    # -----------------------------------------------------------------
    print("\n--- 1. Szintetikus adat generalas ---")
    df = szintetikus_adat_generalas()

    # -----------------------------------------------------------------
    # 2. MLModel letrehozasa es train pipeline
    # -----------------------------------------------------------------
    print("\n--- 2. Train Pipeline ---")
    model = MLModel(model_dir=os.path.join(DEFAULT_MODEL_DIR, "demo_model"))
    processed_df = model.preprocessing_pipeline(df)

    # -----------------------------------------------------------------
    # 3. Modell tanitas
    # -----------------------------------------------------------------
    print("\n--- 3. Modell tanitas ---")
    test_accuracy = model.train_and_save_model(processed_df)

    # -----------------------------------------------------------------
    # 4. Online inference (egyetlen sor)
    # -----------------------------------------------------------------
    print("\n--- 4. Online Inference ---")
    sample = df.iloc[0].to_dict()
    sample_target = sample.pop("target", None)

    prediction = model.predict(sample)
    proba = model.predict_proba(sample)

    print(f"  Bemeneti adatsor (elso 5 feature):")
    for i, (k, v) in enumerate(sample.items()):
        if i >= 5:
            break
        print(f"    {k}: {v}")
    print(f"  ...")
    print(f"  Predikio: {prediction} (valos: {sample_target})")
    print(f"  Valoszinusegek: {', '.join(f'class_{i}={p:.4f}' for i, p in enumerate(proba))}")

    # -----------------------------------------------------------------
    # 5. Batch inference
    # -----------------------------------------------------------------
    print("\n--- 5. Batch Inference ---")
    batch_df = df.sample(20, random_state=RANDOM_SEED)
    result_df = batch_inference(model, batch_df)
    print(f"  Elso 5 eredmeny:")
    for _, row in result_df.head(5).iterrows():
        print(f"    Pred: {row['prediction']}, Conf: {row['confidence']:.4f}, "
              f"Valos: {row.get('target', 'N/A')}")

    # -----------------------------------------------------------------
    # 6. Artifact betoltes teszt
    # -----------------------------------------------------------------
    print("\n--- 6. Artifact I/O teszt ---")
    loaded_model = MLModel(model_dir=model.model_dir)
    loaded_pred = loaded_model.predict(sample)
    print(f"  Eredeti modell predikcioja:  {prediction}")
    print(f"  Betoltott modell predikcioja: {loaded_pred}")
    assert prediction == loaded_pred, "Artifact I/O hiba!"
    print("  [OK] Az artifact I/O konzisztens")

    # -----------------------------------------------------------------
    # 7. Tesztek futtatasa
    # -----------------------------------------------------------------
    print("\n--- 7. Tesztek futtatasa ---")
    print()
    test_szintetikus_adat_generalas()
    test_create_new_features()
    test_preprocessing_pipeline()
    test_train_and_save_model()
    test_predict()
    test_train_inference_konzisztencia()
    test_artifact_save_load()
    test_batch_inference()
    test_model_not_overfitting()
    print(f"\n  Osszes teszt SIKERES (9/9)")

    # -----------------------------------------------------------------
    # 8. Sklearn Pipeline demo
    # -----------------------------------------------------------------
    sklearn_pipeline_demo()

    # -----------------------------------------------------------------
    # 9. Data Drift demo
    # -----------------------------------------------------------------
    data_drift_demo()

    # -----------------------------------------------------------------
    # 10. Deployment strategia szimulacio
    # -----------------------------------------------------------------
    deployment_strategia_demo()

    # -----------------------------------------------------------------
    # 11. REST API informacio
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  REST API")
    print("=" * 70)
    if FLASK_ELERHETO:
        print("\n  A REST API inditasahoz futtasd:")
        print("    python -c \"from mlops_pipeline import *; "
              "app = create_flask_app(MLModel()); app.run(debug=True)\"")
        print()
        print("  Vegpontok:")
        print("    POST /model/train   -- CSV feltoltes, modell tanitas")
        print("    POST /model/predict -- JSON body, predikio")
        print("    GET  /model/health  -- Health check")
        print()
        print("  Pelda (curl):")
        print('    curl -X POST http://localhost:5000/model/predict \\')
        print('      -H "Content-Type: application/json" \\')
        print('      -d \'{"feature_00": 1.2, "feature_01": -0.5, '
              '"surgery": "yes"}\'')
    else:
        print("\n  Flask nem telepitett. REST API nem elerheto.")
        print("  Telepites: pip install flask flask-restx")

    # -----------------------------------------------------------------
    # Osszefoglalas
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  OSSZEFOGLALAS")
    print("=" * 70)
    print(f"""
  Bemutatott komponensek:
    1. Szintetikus adatgeneralas (sklearn make_classification)
    2. MLModel osztaly (train + inference pipeline)
    3. Eloeldolgozas (imputer, encoder, scaler, feature engineering)
    4. Modell tanitas es mentes (XGBoost / GradientBoosting)
    5. Online inference (egyetlen sor)
    6. Batch inference (tobb sor)
    7. Artifact I/O (pickle save/load)
    8. pytest-kompatibilis tesztek (9 db)
    9. Sklearn Pipeline alternativa
   10. Data drift detektalas (KS-teszt)
   11. Deployment strategia szimulacio (canary, A/B, blue-green)
   12. Flask REST API (opcionalis)

  Fajlok:
    Artifact-ek: {model.model_dir}
    Training log: {os.path.join(model.model_dir, 'training_log.txt')}

  Tesztek futtatasa:
    pytest mlops_pipeline.py -v
    """)
