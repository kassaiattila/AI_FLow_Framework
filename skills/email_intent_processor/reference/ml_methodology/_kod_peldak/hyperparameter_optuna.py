"""
Hyperparaméter optimalizálás - Teljes kódpélda
================================================

Tartalom:
  1. GridSearchCV (sklearn) - SVM példa
  2. RandomizedSearchCV (sklearn) - Random Forest példa
  3. Optuna alapok (study, trial, objective)
  4. Optuna + LightGBM teljes példa
  5. Optuna + XGBoost példa
  6. Optuna vizualizáció (optimization_history, param_importances)
  7. Early stopping callback
  8. Eredmények összefoglalása és best params

Forrás: Cubix EDU - ML Engineering, 5. hét
        Hyperparaméter optimalizálás és Optuna előadás
"""

import os
import sys
import warnings
from contextlib import contextmanager

import numpy as np
import pandas as pd
from sklearn.datasets import make_classification, make_regression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_percentage_error,
    mean_squared_error,
)
from sklearn.model_selection import (
    GridSearchCV,
    KFold,
    RandomizedSearchCV,
    cross_val_score,
    train_test_split,
)
from sklearn.svm import SVC

# --- Optuna importálása try/except-tel ---
# Az optuna nem része az alap sklearn csomagnak, ezért
# külön kell telepíteni: pip install optuna
try:
    import optuna
    from optuna.samplers import TPESampler

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print(
        "[FIGYELMEZTETÉS] Az optuna csomag nem elérhető. "
        "Telepítés: pip install optuna"
    )

# --- LightGBM és XGBoost importálása ---
try:
    import lightgbm as lgb

    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print(
        "[FIGYELMEZTETÉS] A lightgbm csomag nem elérhető. "
        "Telepítés: pip install lightgbm"
    )

try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print(
        "[FIGYELMEZTETÉS] Az xgboost csomag nem elérhető. "
        "Telepítés: pip install xgboost"
    )

# Matplotlib vizualizációhoz
try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print(
        "[FIGYELMEZTETÉS] A matplotlib csomag nem elérhető. "
        "Vizualizáció ki lesz hagyva."
    )


# ============================================================================
# Segédfüggvények
# ============================================================================


@contextmanager
def suppress_stdout_stderr():
    """
    Kontextuskezelő, amely elnémítja a stdout és stderr kimeneteket.
    Hasznos pl. LightGBM figyelmeztetések elrejtéséhez.
    """
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def print_section(title: str) -> None:
    """Szekció fejléc kiírása a konzolra."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  {title}")
    print(f"{separator}\n")


# ============================================================================
# Adathalmaz generálás
# ============================================================================


def create_classification_data():
    """
    Szintetikus klasszifikációs adathalmaz létrehozása.
    Visszaadja a train/test splitelt adatot és a KFold objektumot.
    """
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=12,
        n_redundant=4,
        n_classes=2,
        random_state=42,
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    return X_train, X_test, y_train, y_test, kf


def create_regression_data():
    """
    Szintetikus regressziós adathalmaz létrehozása.
    Visszaadja a train/test splitelt adatot és a KFold objektumot.
    """
    X, y = make_regression(
        n_samples=1000,
        n_features=20,
        n_informative=12,
        noise=10.0,
        random_state=42,
    )
    # Az y értékek pozitívvá tétele a MAPE számításhoz
    # (MAPE nem definiált nulla közeli értékekre)
    y = np.abs(y) + 100
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    return X_train, X_test, y_train, y_test, kf


# ============================================================================
# 1. SZEKCIÓ: GridSearchCV - SVM példa
# ============================================================================


def demo_gridsearch_svm():
    """
    GridSearchCV bemutató SVM (Support Vector Machine) modellel.

    A GridSearchCV brute force módszer: MINDEN paraméterkombinációt kipróbál.
    Előnye: biztosan megtalálja a legjobb kombinációt a megadott rácsban.
    Hátránya: nagyon lassú lehet sok paraméter esetén.

    Példa: 4 * 3 * 2 * 3 = 72 kombináció, 5-fold CV = 360 illesztés.
    """
    print_section("1. GridSearchCV - SVM klasszifikáció")

    X_train, X_test, y_train, y_test, kf = create_classification_data()

    # --- Paraméterrács definiálása ---
    # Minden paraméterhez megadott értékek ÖSSZES kombinációját kipróbálja.
    param_grid_svm = {
        "C": [0.1, 1, 10, 100],  # Regularizáció erőssége
        "kernel": ["linear", "rbf", "poly"],  # Kernel típusa
        "gamma": ["scale", "auto"],  # Kernel együttható
        "degree": [2, 3, 4],  # Polinom kernel foka (csak poly kernelhez)
    }

    # Összes kombináció száma
    n_combinations = 1
    for values in param_grid_svm.values():
        n_combinations *= len(values)
    print(f"Paraméter-kombinációk száma: {n_combinations}")
    print(f"Cross-validation foldok száma: {kf.n_splits}")
    print(f"Összes illesztés: {n_combinations * kf.n_splits}")

    # --- GridSearchCV futtatása ---
    svm_model = SVC()
    grid_search = GridSearchCV(
        estimator=svm_model,
        param_grid=param_grid_svm,
        cv=kf,
        scoring="accuracy",  # Klasszifikációnál accuracy
        verbose=0,  # 0: csend, 1: folyamat, 2: részletes
        n_jobs=-1,  # Összes CPU mag használata
        return_train_score=True,  # Train score is legyen elérhető
    )

    print("GridSearchCV futtatása...")
    grid_search.fit(X_train, y_train)

    # --- Eredmények ---
    print(f"\nLegjobb paraméterek: {grid_search.best_params_}")
    print(f"Legjobb CV accuracy: {grid_search.best_score_:.4f}")

    # Tesztelés a legjobb modellel
    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_test)
    test_accuracy = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {test_accuracy:.4f}")

    # --- CV eredmények DataFrame-ként ---
    results_df = pd.DataFrame(grid_search.cv_results_)
    top5 = results_df.nsmallest(5, "rank_test_score")[
        ["params", "mean_test_score", "std_test_score", "mean_train_score", "rank_test_score"]
    ]
    print("\nTop 5 paraméterkombináció:")
    print(top5.to_string(index=False))

    return grid_search


# ============================================================================
# 2. SZEKCIÓ: RandomizedSearchCV - Random Forest példa
# ============================================================================


def demo_randomizedsearch_rf():
    """
    RandomizedSearchCV bemutató Random Forest modellel.

    A RandomizedSearchCV véletlenszerűen választ n_iter számú kombinációt
    a megadott eloszlásokból/értékekből.
    Előnye: sokkal gyorsabb, mint a GridSearchCV nagy keresési térnél.
    Hátránya: nem garantálja az optimális kombináció megtalálását.

    A keresési tér lehet:
    - lista (diszkrét értékek)
    - scipy eloszlás (folytonos értékek)
    """
    print_section("2. RandomizedSearchCV - Random Forest klasszifikáció")

    X_train, X_test, y_train, y_test, kf = create_classification_data()

    # --- Paraméter-eloszlások definiálása ---
    from scipy.stats import randint

    param_distributions = {
        "n_estimators": randint(50, 500),  # Egyenletes eloszlás 50-500 között
        "max_depth": [3, 5, 7, 10, 15, None],  # Diszkrét értékek
        "min_samples_split": randint(2, 20),  # Egyenletes eloszlás 2-20 között
        "min_samples_leaf": randint(1, 10),  # Egyenletes eloszlás 1-10 között
        "max_features": ["sqrt", "log2", None],  # Diszkrét értékek
        "bootstrap": [True, False],  # Boolean értékek
    }

    # --- RandomizedSearchCV futtatása ---
    rf_model = RandomForestClassifier(random_state=42)
    n_iter = 50  # Csak 50 véletlenszerű kombináció a teljes tér helyett

    random_search = RandomizedSearchCV(
        estimator=rf_model,
        param_distributions=param_distributions,
        n_iter=n_iter,  # Kipróbálandó kombinációk száma
        cv=kf,
        scoring="accuracy",
        verbose=0,
        n_jobs=-1,
        random_state=42,
        return_train_score=True,
    )

    print(f"RandomizedSearchCV futtatása ({n_iter} iteráció)...")
    random_search.fit(X_train, y_train)

    # --- Eredmények ---
    print(f"\nLegjobb paraméterek: {random_search.best_params_}")
    print(f"Legjobb CV accuracy: {random_search.best_score_:.4f}")

    # Tesztelés
    best_model = random_search.best_estimator_
    y_pred = best_model.predict(X_test)
    test_accuracy = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {test_accuracy:.4f}")

    # --- Overfitting ellenőrzés ---
    results_df = pd.DataFrame(random_search.cv_results_)
    best_idx = random_search.best_index_
    train_score = results_df.loc[best_idx, "mean_train_score"]
    test_score = results_df.loc[best_idx, "mean_test_score"]
    print("\nOverfitting ellenőrzés (legjobb modell):")
    print(f"  Train CV score: {train_score:.4f}")
    print(f"  Valid CV score: {test_score:.4f}")
    print(f"  Különbség:      {train_score - test_score:.4f}")

    return random_search


# ============================================================================
# 3. SZEKCIÓ: Optuna alapok (study, trial, objective)
# ============================================================================


def demo_optuna_basics():
    """
    Optuna alapok bemutatása.

    Az Optuna egy modern hyperparaméter optimalizáló keretrendszer.
    Főbb fogalmak:
    - Study: egy optimalizálási munkamenet (több trial-ból áll)
    - Trial: egyetlen paraméterkombináció kipróbálása
    - Objective: a célfüggvény, amit minimalizálni/maximalizálni akarunk

    Optuna sampling algoritmusok:
    - TPESampler: Tree-structured Parzen Estimator (alapértelmezett)
    - NSGAIISampler: genetikus algoritmus (NSGA-II)
    - RandomSampler: véletlenszerű mintavételezés
    - CmaEsSampler: CMA-ES evolúciós stratégia
    - GridSampler: hagyományos grid search
    - QMCSampler: kvázi Monte Carlo módszer

    Paraméter javaslat típusok (trial.suggest_*):
    - suggest_int: egész szám adott tartományból
    - suggest_float: lebegőpontos szám adott tartományból
    - suggest_categorical: kategória lista elemeiből
    """
    if not OPTUNA_AVAILABLE:
        print("[KIHAGYVA] Optuna nem elérhető.")
        return None

    print_section("3. Optuna alapok - Study, Trial, Objective")

    X_train, X_test, y_train, y_test, kf = create_classification_data()

    # --- Objective függvény definiálása ---
    # Az Optuna ezt a függvényt hívja meg minden trial-nál.
    # A trial objektumból kérjük a paraméterértékeket.
    def objective(trial):
        """
        Célfüggvény: Random Forest accuracy maximalizálása.
        A trial.suggest_* metódusokkal definiáljuk a keresési teret.
        """
        # Paraméterek definiálása a trial-on keresztül
        n_estimators = trial.suggest_int("n_estimators", 50, 300, step=50)
        max_depth = trial.suggest_int("max_depth", 3, 15)
        min_samples_split = trial.suggest_int("min_samples_split", 2, 20)
        min_samples_leaf = trial.suggest_int("min_samples_leaf", 1, 10)
        max_features = trial.suggest_categorical("max_features", ["sqrt", "log2"])

        # Modell létrehozása az adott paraméterekkel
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            random_state=42,
            n_jobs=-1,
        )

        # Cross-validation futtatása
        scores = cross_val_score(model, X_train, y_train, cv=kf, scoring="accuracy")

        # Az átlagos CV score-t adjuk vissza
        return scores.mean()

    # --- Study létrehozása és futtatása ---
    # direction='maximize' mert az accuracy-t maximalizáljuk
    # (ha hibát minimalizálnánk, pl. MAPE, akkor 'minimize')
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=42),  # Reprodukálhatóság érdekében seed
        study_name="rf_basic_demo",
    )

    print("Optuna Study futtatása (50 trial)...")
    study.optimize(objective, n_trials=50, show_progress_bar=False)

    # --- Eredmények ---
    print(f"\nLegjobb trial száma: {study.best_trial.number}")
    print(f"Legjobb CV accuracy: {study.best_value:.4f}")
    print("Legjobb paraméterek:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")

    # Összes trial statisztika
    print(f"\nÖsszes trial: {len(study.trials)}")
    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    print(f"Befejezett trialok: {len(completed)}")

    # A legjobb modell tesztelése
    best_model = RandomForestClassifier(**study.best_params, random_state=42, n_jobs=-1)
    best_model.fit(X_train, y_train)
    y_pred = best_model.predict(X_test)
    print(f"Test accuracy (legjobb paraméterekkel): {accuracy_score(y_test, y_pred):.4f}")

    return study


# ============================================================================
# 4. SZEKCIÓ: Optuna + LightGBM teljes példa
# ============================================================================


def demo_optuna_lightgbm():
    """
    Optuna + LightGBM regresszió teljes példa.

    A kurzusanyag alapján:
    - Először GridSearchCV-vel próbáljuk (brute force, lassú)
    - Utána Optuna-val (okos keresés, sokkal gyorsabb)
    - Iteratívan szűkítjük a keresési teret a legjobb eredmény felé

    LightGBM fontos hyperparaméterek:
    - n_estimators: boosting iterációk száma (fák száma)
    - learning_rate: tanulási ráta (alacsonyabb = lassabb de pontosabb)
    - num_leaves: fa levelek maximális száma
    - max_depth: fa maximális mélysége
    - min_data_in_leaf: minimum adat levelenként (overfitting ellen)
    - feature_fraction: feature-ök hányada iterációnként
    """
    if not OPTUNA_AVAILABLE or not LIGHTGBM_AVAILABLE:
        print("[KIHAGYVA] Optuna és/vagy LightGBM nem elérhető.")
        return None

    print_section("4. Optuna + LightGBM regresszió")

    X_train, X_test, y_train, y_test, kf = create_regression_data()

    # --- 4a) GridSearchCV brute force (összehasonlításként) ---
    print("--- 4a) GridSearchCV (brute force, referenciaként) ---\n")

    param_grid_lgb = {
        "n_estimators": [100, 200, 400],
        "learning_rate": [0.001, 0.01, 0.1],
        "num_leaves": [5, 10, 20],
    }

    n_combinations = 1
    for v in param_grid_lgb.values():
        n_combinations *= len(v)
    print(f"Kombinációk száma: {n_combinations} (brute force)")

    lgb_model = lgb.LGBMRegressor(verbosity=-1, force_col_wise=True)

    grid_search = GridSearchCV(
        estimator=lgb_model,
        param_grid=param_grid_lgb,
        cv=kf,
        scoring="neg_mean_absolute_percentage_error",
        verbose=0,
        n_jobs=-1,
    )

    import time

    start = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        grid_search.fit(X_train, y_train)
    grid_time = time.time() - start

    grid_best_mape = -grid_search.best_score_ * 100
    print(f"GridSearchCV legjobb MAPE: {grid_best_mape:.2f}%")
    print(f"GridSearchCV futási idő:   {grid_time:.1f} mp")
    print(f"GridSearchCV legjobb params: {grid_search.best_params_}")

    # --- 4b) Optuna optimalizálás (hatékonyabb) ---
    print("\n--- 4b) Optuna optimalizálás ---\n")

    def lgb_objective(trial):
        """
        LightGBM objective függvény Optuna-hoz.
        A suggest_* metódusokkal definiáljuk a keresési teret.
        Fontos: suggest_float log=True hasznos a learning_rate-hez,
        mert logaritmikus skálán egyenletesebben szór.
        """
        with suppress_stdout_stderr():
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.001, 0.3, log=True
                ),
                "num_leaves": trial.suggest_int("num_leaves", 5, 50),
                "max_depth": trial.suggest_int("max_depth", 3, 15),
                "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 5, 50),
                "feature_fraction": trial.suggest_float("feature_fraction", 0.2, 1.0),
                "verbosity": -1,
                "force_col_wise": True,
            }

            model = lgb.LGBMRegressor(**params)
            scores = cross_val_score(
                model,
                X_train,
                y_train,
                cv=kf,
                scoring="neg_mean_absolute_percentage_error",
            )
            mape = -scores.mean()
            return mape

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    # 1. kör: széles keresés
    study = optuna.create_study(
        direction="minimize",  # MAPE-t minimalizáljuk
        sampler=TPESampler(seed=42),
        study_name="lgbm_round1",
    )

    start = time.time()
    study.optimize(lgb_objective, n_trials=100, show_progress_bar=False)
    optuna_time = time.time() - start

    print(f"Optuna legjobb MAPE: {study.best_value * 100:.2f}%")
    print(f"Optuna futási idő:   {optuna_time:.1f} mp")
    print("Legjobb paraméterek:")
    for key, value in study.best_params.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")

    # --- 4c) Iteratív finomhangolás (a kurzus anyag alapján) ---
    print("\n--- 4c) Iteratív finomhangolás ---")
    print("A legjobb paraméterek környezetében szűkítjük a keresési teret.\n")

    best = study.best_params

    def lgb_objective_refined(trial):
        """Finomhangolt objective: a korábbi legjobb eredmény közelébe szűkítjük."""
        with suppress_stdout_stderr():
            # A keresési teret a legjobb értékek +/- 30%-ára szűkítjük
            n_est_best = best["n_estimators"]
            params = {
                "n_estimators": trial.suggest_int(
                    "n_estimators",
                    max(50, n_est_best - 100),
                    n_est_best + 100,
                    step=25,
                ),
                "learning_rate": trial.suggest_float(
                    "learning_rate",
                    max(0.001, best["learning_rate"] * 0.5),
                    best["learning_rate"] * 2.0,
                    log=True,
                ),
                "num_leaves": trial.suggest_int(
                    "num_leaves",
                    max(3, best["num_leaves"] - 5),
                    best["num_leaves"] + 5,
                ),
                "max_depth": trial.suggest_int(
                    "max_depth",
                    max(2, best["max_depth"] - 3),
                    best["max_depth"] + 3,
                ),
                "min_data_in_leaf": trial.suggest_int(
                    "min_data_in_leaf",
                    max(1, best["min_data_in_leaf"] - 5),
                    best["min_data_in_leaf"] + 5,
                ),
                "feature_fraction": trial.suggest_float(
                    "feature_fraction",
                    max(0.1, best["feature_fraction"] - 0.2),
                    min(1.0, best["feature_fraction"] + 0.2),
                ),
                "verbosity": -1,
                "force_col_wise": True,
            }

            model = lgb.LGBMRegressor(**params)
            scores = cross_val_score(
                model,
                X_train,
                y_train,
                cv=kf,
                scoring="neg_mean_absolute_percentage_error",
            )
            return -scores.mean()

    study_refined = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=42),
        study_name="lgbm_refined",
    )
    study_refined.optimize(lgb_objective_refined, n_trials=100, show_progress_bar=False)

    print(f"Finomhangolt MAPE:    {study_refined.best_value * 100:.2f}%")
    print(f"Korábbi legjobb MAPE: {study.best_value * 100:.2f}%")
    improvement = (study.best_value - study_refined.best_value) * 100
    print(f"Javulás:              {improvement:.2f} százalékpont")

    # --- 4d) Végső értékelés a teszthalmazon ---
    print("\n--- 4d) Végső értékelés a teszthalmazon ---\n")
    print(
        "FONTOS: A validation adathalmazon implicit módon optimalizálunk,\n"
        "ezért a teszthalmazon kapott eredmény a valós teljesítmény."
    )

    # A finomhangolt paraméterekkel
    final_params = study_refined.best_params.copy()
    final_params["verbosity"] = -1
    final_params["force_col_wise"] = True

    final_model = lgb.LGBMRegressor(**final_params)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        final_model.fit(X_train, y_train)
    y_pred_test = final_model.predict(X_test)
    test_mape = mean_absolute_percentage_error(y_test, y_pred_test) * 100

    print(f"Validation MAPE (CV): {study_refined.best_value * 100:.2f}%")
    print(f"Test MAPE:            {test_mape:.2f}%")
    print(f"Különbség:            {abs(test_mape - study_refined.best_value * 100):.2f} százalékpont")

    return study, study_refined


# ============================================================================
# 5. SZEKCIÓ: Optuna + XGBoost példa
# ============================================================================


def demo_optuna_xgboost():
    """
    Optuna + XGBoost regresszió példa.

    Az XGBoost hasonló a LightGBM-hez, de más hyperparaméterneveket használ.
    Fontos XGBoost paraméterek:
    - n_estimators: boosting körök száma
    - learning_rate (eta): tanulási ráta
    - max_depth: fa maximális mélysége
    - min_child_weight: minimum súly gyermek csomópontonként
    - subsample: sorok mintavételezési aránya
    - colsample_bytree: oszlopok mintavételezési aránya
    - gamma: minimális veszteségcsökkentés a továbbosztáshoz
    - reg_alpha: L1 regularizáció
    - reg_lambda: L2 regularizáció
    """
    if not OPTUNA_AVAILABLE or not XGBOOST_AVAILABLE:
        print("[KIHAGYVA] Optuna és/vagy XGBoost nem elérhető.")
        return None

    print_section("5. Optuna + XGBoost regresszió")

    X_train, X_test, y_train, y_test, kf = create_regression_data()

    def xgb_objective(trial):
        """XGBoost objective függvény Optuna-hoz."""
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.3, 1.0),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "verbosity": 0,
        }

        model = xgb.XGBRegressor(**params, random_state=42)
        scores = cross_val_score(
            model,
            X_train,
            y_train,
            cv=kf,
            scoring="neg_mean_absolute_percentage_error",
        )
        return -scores.mean()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=42),
        study_name="xgboost_demo",
    )

    print("Optuna + XGBoost optimalizálás (80 trial)...")
    study.optimize(xgb_objective, n_trials=80, show_progress_bar=False)

    # --- Eredmények ---
    print(f"\nLegjobb MAPE: {study.best_value * 100:.2f}%")
    print("Legjobb paraméterek:")
    for key, value in study.best_params.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")

    # Test értékelés
    final_params = study.best_params.copy()
    final_params["verbosity"] = 0
    final_model = xgb.XGBRegressor(**final_params, random_state=42)
    final_model.fit(X_train, y_train)
    y_pred = final_model.predict(X_test)
    test_mape = mean_absolute_percentage_error(y_test, y_pred) * 100
    print(f"\nTest MAPE: {test_mape:.2f}%")

    return study


# ============================================================================
# 6. SZEKCIÓ: Optuna vizualizáció
# ============================================================================


def demo_optuna_visualization(study, study_name: str = "Study"):
    """
    Optuna beépített vizualizációs eszközei.

    Elérhető ábrák:
    - optimization_history: a célfüggvény értéke trialról trialra
    - param_importances: melyik paraméter mennyire fontos
    - slice: egy-egy paraméter hatása a célfüggvényre
    - contour: két paraméter közötti interakció hőtérképe
    - parallel_coordinate: párhuzamos koordináta ábra
    """
    if not OPTUNA_AVAILABLE:
        print("[KIHAGYVA] Optuna nem elérhető.")
        return

    if not MATPLOTLIB_AVAILABLE:
        print("[KIHAGYVA] Matplotlib nem elérhető a vizualizációhoz.")
        return

    if study is None:
        print("[KIHAGYVA] Nincs study objektum a vizualizációhoz.")
        return

    print_section(f"6. Optuna vizualizáció - {study_name}")

    try:
        from optuna.visualization.matplotlib import (
            plot_optimization_history,
            plot_param_importances,
            plot_slice,
        )
    except ImportError:
        print(
            "[FIGYELMEZTETÉS] Az optuna matplotlib vizualizáció nem elérhető.\n"
            "Telepítés: pip install optuna[visualization]"
        )
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))

    # --- Optimization history ---
    # Az optimalizálás történetét mutatja: hogyan javult az eredmény trialról trialra.
    plt.sca(axes[0])
    plot_optimization_history(study)
    axes[0].set_title(f"{study_name} - Optimalizálás története")

    # --- Param importances ---
    # Megmutatja, melyik hyperparaméter milyen mértékben befolyásolja az eredményt.
    # Ez segít eldönteni, melyik paraméterrel érdemes tovább foglalkozni.
    plt.sca(axes[1])
    try:
        plot_param_importances(study)
        axes[1].set_title(f"{study_name} - Paraméter fontosság")
    except Exception as e:
        axes[1].text(
            0.5, 0.5,
            f"Nem sikerült kiszámolni\na paraméter fontosságot:\n{e}",
            ha="center", va="center", transform=axes[1].transAxes,
        )

    plt.tight_layout()
    plt.savefig("optuna_visualization.png", dpi=150, bbox_inches="tight")
    print("Vizualizáció elmentve: optuna_visualization.png")
    plt.show()

    # --- Slice plot (külön ábra) ---
    try:
        plt.figure(figsize=(14, 8))
        plot_slice(study)
        plt.suptitle(f"{study_name} - Paraméter szelet ábrák", fontsize=14)
        plt.tight_layout()
        plt.savefig("optuna_slice_plot.png", dpi=150, bbox_inches="tight")
        print("Slice plot elmentve: optuna_slice_plot.png")
        plt.show()
    except Exception as e:
        print(f"Slice plot hiba: {e}")


# ============================================================================
# 7. SZEKCIÓ: Early stopping callback
# ============================================================================


def demo_early_stopping():
    """
    Optuna early stopping callback-ek bemutatása.

    Az early stopping lehetővé teszi, hogy leállítsuk az optimalizálást,
    ha már nem várható javulás. Ez időt takarít meg.

    Beépített callback-ek:
    - EarlyStopping: ha N egymást követő trial nem javít, leáll
    - MaxTrialsCallback: adott számú trial után leáll (alternatíva n_trials-hoz)

    Egyéni callback: bármilyen logikát implementálhatunk.
    """
    if not OPTUNA_AVAILABLE:
        print("[KIHAGYVA] Optuna nem elérhető.")
        return None

    print_section("7. Early stopping callback")

    X_train, X_test, y_train, y_test, kf = create_classification_data()

    def objective(trial):
        """Egyszerű RF objective early stopping demonstrációhoz."""
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 10, 300, step=10),
            "max_depth": trial.suggest_int("max_depth", 2, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 30),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 15),
        }
        model = RandomForestClassifier(**params, random_state=42, n_jobs=-1)
        scores = cross_val_score(model, X_train, y_train, cv=kf, scoring="accuracy")
        return scores.mean()

    # --- 7a) Egyéni early stopping callback ---
    print("--- 7a) Egyéni early stopping callback ---\n")

    class EarlyStoppingCallback:
        """
        Egyéni callback: leállítja az optimalizálást, ha N egymást követő
        trial nem javít a legjobb eredményen.
        """

        def __init__(self, patience: int = 15):
            self.patience = patience
            self.best_value = None
            self.no_improvement_count = 0

        def __call__(self, study: optuna.Study, trial: optuna.trial.FrozenTrial):
            current_value = trial.value
            if current_value is None:
                return

            if self.best_value is None:
                self.best_value = current_value
                return

            # Ellenőrizzük, hogy van-e javulás
            if study.direction == optuna.study.StudyDirection.MAXIMIZE:
                improved = current_value > self.best_value
            else:
                improved = current_value < self.best_value

            if improved:
                self.best_value = current_value
                self.no_improvement_count = 0
            else:
                self.no_improvement_count += 1

            # Ha elértük a türelmi határ, leállítjuk
            if self.no_improvement_count >= self.patience:
                print(
                    f"\n  [Early Stop] {self.patience} egymást követő trial "
                    f"nem javított. Leállítás a {trial.number}. trial után."
                )
                study.stop()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=42),
    )

    early_stop = EarlyStoppingCallback(patience=15)

    print("Optimalizálás early stopping-gal (max 200 trial, patience=15)...")
    study.optimize(
        objective,
        n_trials=200,
        callbacks=[early_stop],
        show_progress_bar=False,
    )

    print(f"\nTényleges trialok száma: {len(study.trials)}")
    print(f"Legjobb accuracy: {study.best_value:.4f}")
    print(f"Legjobb paraméterek: {study.best_params}")

    # --- 7b) Beépített Optuna early stopping (ha elérhető) ---
    print("\n--- 7b) Időkorlát (timeout) ---\n")

    study2 = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=123),
    )

    # Az Optuna beépített timeout paramétere (másodpercben)
    # Ez 10 másodperc után leállítja az optimalizálást, függetlenül a trialok számától.
    print("Optimalizálás 10 másodperces időkorláttal...")
    study2.optimize(
        objective,
        n_trials=1000,  # Magas felső határ, a timeout fogja leállítani
        timeout=10,  # 10 mp után leáll
        show_progress_bar=False,
    )

    print(f"Trialok a 10 mp alatt: {len(study2.trials)}")
    print(f"Legjobb accuracy: {study2.best_value:.4f}")

    return study


# ============================================================================
# 8. SZEKCIÓ: Eredmények összefoglalása és best params
# ============================================================================


def demo_results_summary():
    """
    Eredmények összefoglalása és a legjobb paraméterek exportálása.

    Bemutatja:
    - Hogyan mentsük el az Optuna study-t SQLite adatbázisba
    - Hogyan töltsük vissza egy korábbi study-t
    - Hogyan exportáljuk az eredményeket DataFrame-ként
    - Hogyan használjuk a legjobb paramétereket a végső modellhez
    """
    if not OPTUNA_AVAILABLE or not LIGHTGBM_AVAILABLE:
        print("[KIHAGYVA] Optuna és/vagy LightGBM nem elérhető.")
        return

    print_section("8. Eredmények összefoglalása és best params")

    X_train, X_test, y_train, y_test, kf = create_regression_data()

    # --- 8a) Study mentése SQLite adatbázisba ---
    print("--- 8a) Study persistálása SQLite-ba ---\n")

    db_path = "sqlite:///optuna_study.db"

    def lgb_objective(trial):
        with suppress_stdout_stderr():
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 400, step=50),
                "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.2, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 5, 40),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 5, 30),
                "verbosity": -1,
                "force_col_wise": True,
            }
            model = lgb.LGBMRegressor(**params)
            scores = cross_val_score(
                model, X_train, y_train, cv=kf,
                scoring="neg_mean_absolute_percentage_error",
            )
            return -scores.mean()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    # A study SQLite-ba mentődik, így később folytatható
    study = optuna.create_study(
        direction="minimize",
        storage=db_path,
        study_name="lgbm_persistent",
        load_if_exists=True,  # Ha létezik, folytatjuk
        sampler=TPESampler(seed=42),
    )

    print("Study futtatása és mentése SQLite-ba (50 trial)...")
    study.optimize(lgb_objective, n_trials=50, show_progress_bar=False)
    print(f"Study mentve: {db_path}")

    # --- 8b) Study visszatöltése ---
    print("\n--- 8b) Study visszatöltése ---\n")

    loaded_study = optuna.load_study(
        study_name="lgbm_persistent",
        storage=db_path,
    )
    print(f"Visszatöltött trialok száma: {len(loaded_study.trials)}")
    print(f"Legjobb MAPE: {loaded_study.best_value * 100:.2f}%")

    # --- 8c) Eredmények exportálása ---
    print("\n--- 8c) Eredmények exportálása ---\n")

    trials_df = study.trials_dataframe()
    print(f"Trials DataFrame alakja: {trials_df.shape}")
    print(f"Oszlopok: {list(trials_df.columns)[:8]}...")

    # Top 5 trial
    top5 = trials_df.nsmallest(5, "value")[
        ["number", "value", "duration"]
        + [c for c in trials_df.columns if c.startswith("params_")]
    ]
    print("\nTop 5 trial:")
    print(top5.to_string(index=False))

    # CSV exportálás
    csv_path = "optuna_results.csv"
    trials_df.to_csv(csv_path, index=False)
    print(f"\nEredmények exportálva: {csv_path}")

    # --- 8d) Végső modell a legjobb paraméterekkel ---
    print("\n--- 8d) Végső modell ---\n")

    best_params = study.best_params.copy()
    best_params["verbosity"] = -1
    best_params["force_col_wise"] = True

    print("Legjobb paraméterek:")
    for key, value in best_params.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")

    # Végső modell betanítása
    final_model = lgb.LGBMRegressor(**best_params)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        final_model.fit(X_train, y_train)

    # Értékelés
    y_pred_train = final_model.predict(X_train)
    y_pred_test = final_model.predict(X_test)

    train_mape = mean_absolute_percentage_error(y_train, y_pred_train) * 100
    test_mape = mean_absolute_percentage_error(y_test, y_pred_test) * 100
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

    print("\nVégső modell értékelése:")
    print(f"  Train MAPE: {train_mape:.2f}%")
    print(f"  Test MAPE:  {test_mape:.2f}%")
    print(f"  Test RMSE:  {test_rmse:.2f}")
    print(f"  Overfitting (train-test MAPE különbség): {abs(train_mape - test_mape):.2f} pp")

    # Takarítás: SQLite fájl törlése a demó után
    import pathlib

    db_file = pathlib.Path("optuna_study.db")
    if db_file.exists():
        db_file.unlink()
        print(f"\nDemó adatbázis törölve: {db_file}")

    return study


# ============================================================================
# Fő belépési pont
# ============================================================================


if __name__ == "__main__":
    print(
        """
╔══════════════════════════════════════════════════════════════════════╗
║        Hyperparaméter optimalizálás - Teljes kódpélda              ║
║                                                                    ║
║  Cubix EDU - ML Engineering, 5. hét                                ║
║  Témakörök: GridSearchCV, RandomizedSearchCV, Optuna               ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    )

    # Figyelmeztetések elnémítása a cleaner kimenetért
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

    # --- 1. GridSearchCV - SVM ---
    grid_result = demo_gridsearch_svm()

    # --- 2. RandomizedSearchCV - Random Forest ---
    random_result = demo_randomizedsearch_rf()

    # --- 3. Optuna alapok ---
    optuna_basic_study = demo_optuna_basics()

    # --- 4. Optuna + LightGBM ---
    lgbm_result = demo_optuna_lightgbm()

    # --- 5. Optuna + XGBoost ---
    xgb_study = demo_optuna_xgboost()

    # --- 6. Optuna vizualizáció ---
    # Az LightGBM study-t használjuk vizualizációhoz, ha elérhető
    if lgbm_result is not None:
        _, refined_study = lgbm_result
        demo_optuna_visualization(refined_study, "LightGBM finomhangolt")
    elif xgb_study is not None:
        demo_optuna_visualization(xgb_study, "XGBoost")

    # --- 7. Early stopping ---
    demo_early_stopping()

    # --- 8. Eredmények összefoglalása ---
    demo_results_summary()

    # --- Záró összefoglaló ---
    print_section("Összefoglaló")
    print(
        """A hyperparaméter optimalizálás kulcsfontosságú lépés a modellezésben.

Módszerek összehasonlítása:
┌─────────────────────┬──────────────┬──────────────┬──────────────────────┐
│ Módszer             │ Sebesség     │ Pontosság    │ Mikor használjuk     │
├─────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ GridSearchCV        │ Lassú        │ Teljes       │ Kevés paraméter,     │
│                     │              │              │ kis keresési tér     │
├─────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ RandomizedSearchCV  │ Közepes      │ Jó           │ Nagyobb keresési     │
│                     │              │              │ tér, gyors modell    │
├─────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ Optuna (TPE)        │ Gyors        │ Nagyon jó    │ Nagy keresési tér,   │
│                     │              │              │ drága modell         │
├─────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ Optuna (NSGA-II)    │ Gyors        │ Nagyon jó    │ Többcélú             │
│                     │              │              │ optimalizálás        │
└─────────────────────┴──────────────┴──────────────┴──────────────────────┘

Fontos tanulságok a kurzusból:
  1. A brute force (GridSearchCV) sok paraméternél nagyon lassú
  2. Az Optuna akár 5x gyorsabb azonos eredményért
  3. Iteratív finomhangolás: a legjobb paraméterek környékén szűkítjük a teret
  4. Mindig teszthalmazon ellenőrizzük a végső modellt (nem validation-ön!)
  5. A validation-ön kapott eredmény mindig optimistább, mert arra optimalizáltunk
"""
    )
