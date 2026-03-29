# Hyperparamater Optimalizalas

## Gyors Attekintes

> A hyperparamater optimalizalas (Hyperparameter Tuning) a gepi tanulasi modellek teljesitmenyenek javitasara szolgalo folyamat, amelynek soran a modell tanulasi folytamatat befolyasolo -- de az adatokbol nem tanulhato -- parametereket hangoljuk. A fo celunk, hogy megtalaljuk az optimalis parameterkombinaciokat, amelyekkel a modell a legjobb altalanositasi kepesseget eri el anelkul, hogy overfittelne. A leggyakoribb modszerek a Grid Search (teljes racskereses), a Random Search (veletlen kereses), es a Bayesian optimalizacio (pl. Optuna framework).

---

## Kulcsfogalmak

- **Hyperparamater vs paramater**: A *parametereket* a modell a tanitas soran tanulja meg az adatokbol (pl. sulyok, bias). A *hyperparametereket* viszont mi allitjuk be a tanitas elott -- ezek szabalyozzak a tanulasi folyamat mukodeset (pl. learning rate, regularizacios ero, fakmelyseg).
- **Keresesi ter (Search Space)**: Azon hyperparamater-ertekek vagy tartomanyok osszessege, amelyeket az optimalizalas soran ki akarunk probalni. Lehet diszkret (pl. `[100, 200, 400]`) vagy folytonos (pl. `0.001`--`0.1`).
- **Cross-Validation (CV)**: Az adathalmazt tobbszor felosztjuk tanito es validacios halmazra, hogy megbizhatobban merjuk a modell teljesitmenyet. Az 5-fold CV az 5 kulonbozo felosztast jelenti.
- **MAPE (Mean Absolute Percentage Error)**: Az elorejzesi hibak atlagos szazalekos erteket mero metrika. Fontos: ha az Y-ertekek kozott nulla van, a MAPE nem szamolhato, ezert ilyenkor MinMaxScaler-rel (pl. 0.01--1 tartomanyra) skalazunk.
- **Overfitting**: Amikor a modell tul jol alkalmazkodik a tanito adatokhoz, es emiatt rosszul teljesit uj, ismeretlen adatokon. A hyperparamater hangolas egyik fo celja ennek elkerulese.
- **Brute Force vs. okos kereses**: A Grid Search minden kombinaciot kiprobalt (brute force), mig az Optuna intelligensen valogatja a kovetkezo kiserleteket, ezaltal gyorsabb.

---

## Optimalizalasi Modszerek

### Grid Search (GridSearchCV)

#### Mukodesi elv

A Grid Search a keresesi terben meghatarozott osszes lehetseges parameterkombinaciora letrehozza es kiertekeli a modellt cross-validation segitsegevel. Ez egy **brute force** megkozelites: mindent mindennel kiprobalt. Elonye, hogy garantaltan megtalaja a legjobb kombinaciot a megadott racs alapjan; hatranya, hogy nagyon lassu lehet, ha sok paramater vagy sok lehetseges ertek van.

Az `sklearn.model_selection.GridSearchCV` automatikusan elvegzi:
- a parameterkombenaciok generalasaat,
- a cross-validation felosztast,
- a kiertekeles es a legjobb eredmeny kivalasztasat.

#### Kod pelda -- Ridge regresszio

```python
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.linear_model import Ridge

# K-fold cross-validation beallitasa
kf = KFold(n_splits=5, shuffle=True, random_state=42)

# Paramater grid definalasa
param_grid = {
    'alpha': [0.001, 0.01, 0.1, 1, 10, 100],
    'tol': [1e-4, 1e-3, 1e-2],
    'solver': ['auto', 'svd', 'cholesky', 'lsqr', 'sparse_cg', 'sag', 'saga']
}

ridge = Ridge()

# GridSearchCV letrehozasa es futtatas
grid_search = GridSearchCV(
    estimator=ridge,
    param_grid=param_grid,
    cv=kf,
    scoring='neg_mean_absolute_percentage_error',
    verbose=1,
    n_jobs=-1  # osszes CPU mag hasznalata
)

grid_search.fit(X_train, y_train.ravel())

# Eredmenyek
best_params = grid_search.best_params_
best_score = -grid_search.best_score_ * 100  # Pozitiv MAPE ertekke alakitas
print(f"Legjobb parameterek: {best_params}")
print(f"Legjobb MAPE: {best_score:.2f}%")
# Eredmeny: ~71.01% MAPE, 126 kombinacio
```

#### Kod pelda -- SVM (SVR)

```python
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVR

param_grid_svm = {
    'C': [0.1, 1, 10, 100],
    'kernel': ['linear', 'poly', 'rbf', 'sigmoid'],
    'gamma': ['scale', 'auto'],
    'epsilon': [0.001, 0.01, 0.1]
}

svm_model = SVR()

grid_search_svm = GridSearchCV(
    estimator=svm_model,
    param_grid=param_grid_svm,
    cv=kf,
    scoring='neg_mean_absolute_percentage_error',
    verbose=1,
    n_jobs=-1
)

grid_search_svm.fit(X_train, y_train.ravel())

best_params_svm = grid_search_svm.best_params_
best_score_svm = -grid_search_svm.best_score_ * 100
print(f"Legjobb parameterek: {best_params_svm}")
print(f"Legjobb MAPE: {best_score_svm:.2f}%")
# Eredmeny: ~69.6% MAPE, 96 kombinacio
```

#### Kod pelda -- LightGBM

```python
from sklearn.model_selection import GridSearchCV
import lightgbm as lgb

param_grid_lgb = {
    'boosting_type': ["dart"],
    'n_estimators': [100, 200, 400],
    'learning_rate': [0.001, 0.01, 0.1],
    'num_leaves': [5, 10, 20],
    'max_depth': [5, 7, 10],
    'min_data_in_leaf': [5, 10, 20],
    'feature_fraction': [0.2, 0.5, 1.0],
    'force_col_wise=true': [True]
}

lgb_model = lgb.LGBMRegressor()

grid_search_lgb = GridSearchCV(
    estimator=lgb_model,
    param_grid=param_grid_lgb,
    cv=kf,
    scoring='neg_mean_absolute_percentage_error',
    verbose=1,
    n_jobs=-1
)

grid_search_lgb.fit(X_train, y_train.ravel())

best_params_lgb = grid_search_lgb.best_params_
best_score_lgb = -grid_search_lgb.best_score_ * 100
print(f"Legjobb parameterek: {best_params_lgb}")
print(f"Legjobb MAPE: {best_score_lgb:.2f}%")
# Eredmeny: ~54.85% MAPE, 729 kombinacio, ~5 perc futasi ido
```

#### Elonyok es Hatranyok

| Szempont | Ertekeles |
|---|---|
| **Elony** | Garantaltan megtalaja a legjobb kombinaciot a megadott racsban |
| **Elony** | Egyszeruen hasznalhato, jol dokumentalt |
| **Elony** | Reprodukalhato eredmenyek |
| **Hatrany** | Brute force: exponencialisan no a futasi ido a parameterek szamaval |
| **Hatrany** | 729 kombinacio mar ~5 percig futott (kis adathalmazon!) |
| **Hatrany** | Nem adaptiv: nem tanul a korabbi eredmenyekbol |

---

### Random Search (RandomizedSearchCV)

#### Mukodesi elv

A Random Search a keresesi terbol **veletlenszeruen valaszt** parameterkombinaciot egy megadott szamu kiserletben. Nem probaja ki az osszes kombinaciot, hanem `n_iter` szamu mintavetelezest vegez. Elonye, hogy nagy keresesi terben is gyorsabban talal jo megoldasokat, es folytonos eloszlasokbol is tud mintavetelezni.

#### Kod pelda

```python
from sklearn.model_selection import RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
from scipy.stats import randint, uniform

param_distributions = {
    'n_estimators': randint(50, 500),
    'max_depth': randint(3, 15),
    'min_samples_split': randint(2, 20),
    'min_samples_leaf': randint(1, 10),
    'max_features': uniform(0.1, 0.9)
}

rf_model = RandomForestRegressor(random_state=42)

random_search = RandomizedSearchCV(
    estimator=rf_model,
    param_distributions=param_distributions,
    n_iter=100,          # 100 veletlen kombinacio
    cv=kf,
    scoring='neg_mean_absolute_percentage_error',
    verbose=1,
    n_jobs=-1,
    random_state=42
)

random_search.fit(X_train, y_train.ravel())

best_params_rf = random_search.best_params_
best_score_rf = -random_search.best_score_ * 100
print(f"Legjobb parameterek: {best_params_rf}")
print(f"Legjobb MAPE: {best_score_rf:.2f}%")
```

#### Elonyok es Hatranyok

| Szempont | Ertekeles |
|---|---|
| **Elony** | Sokkal gyorsabb, mint a Grid Search nagy keresesi terben |
| **Elony** | Folytonos eloszlasokbol is tud mintavetelezni |
| **Elony** | A tapasztalat szerint 60 kiserlettel mar a legjobb 5%-ba kerulunk |
| **Hatrany** | Nem garantal optimalis megoldast |
| **Hatrany** | Nem tanul a korabbi probalkozasokbol |

---

### Bayesian Optimalizacio (Optuna)

#### Mukodesi elv

A Bayesian optimalizacio az elozo kiserletek eredmenyeibol tanulva valasztja ki a kovetkezo kiprobando parameterkombinaciot. Igy **celzottan** a legigretesebb teruletek fele keres, ahelyett, hogy vakon probalgata. Az Optuna framework ezt kenyelmesen kezelheto modon valosita meg, es tobb kulonbozo sampling algoritmust tamogat.

#### Optuna framework

Az **Optuna** egy automatikus hyperparamater optimalizalo keretrendszer Python-ban. Fo jellemzoi:

- **Study**: Egy optimalizalasi feladat kerete, amely tartalazza az osszes trial-t es az eredmenyeket
- **Trial**: Egyetlen kiserlet egy adott parameterkombinacoval
- **Objective fuggveny**: A felhasznalo altal definialt fuggveny, amely a trial-nak megadott parametrekke epitkezo modell teljesitmenyet adja vissza
- **Sampler**: A parametervalasztas strategiaja

Az Optuna altal tamogatott sampling algoritmusok:

| Sampler | Leiras |
|---|---|
| `TPESampler` | Tree-structured Parzen Estimator -- az alapertelmezett, Bayesian megkozelites |
| `GridSampler` | Teljes racskereses (mint GridSearchCV) |
| `RandomSampler` | Veletlen kereses |
| `CmaEsSampler` | CMA-ES alapu evolucio strategia |
| `NSGAIISampler` | Genetikus algoritmus (NSGA-II) |
| `QMCSampler` | Quasi Monte Carlo mintavetelezas |
| `PartialFixedSampler` | Reszlegesen rogzitett parameterekkel |

#### Kod pelda Optuna-val (LightGBM)

```python
import optuna
import lightgbm as lgb
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_absolute_percentage_error
import os
import sys
from contextlib import contextmanager

# Figyelmezteto uzenetek elnemitasa (LightGBM sokat general)
@contextmanager
def suppress_stdout_stderr():
    """Stdout es stderr atiranyitasa devnull-ra."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def objective(trial, params_dict):
    """Optuna objective fuggveny LightGBM-hez."""
    with suppress_stdout_stderr():
        param = {
            'boosting_type': 'dart',
            'n_estimators': trial.suggest_categorical(
                'n_estimators', params_dict['n_estimators']),
            'learning_rate': trial.suggest_categorical(
                'learning_rate', params_dict['learning_rate']),
            'num_leaves': trial.suggest_categorical(
                'num_leaves', params_dict['num_leaves']),
            'max_depth': trial.suggest_categorical(
                'max_depth', params_dict['max_depth']),
            'min_data_in_leaf': trial.suggest_categorical(
                'min_data_in_leaf', params_dict['min_data_in_leaf']),
            'feature_fraction': trial.suggest_categorical(
                'feature_fraction', params_dict['feature_fraction']),
            'force_col_wise': True
        }

        lgbm = lgb.LGBMRegressor(**param)
        scores = cross_val_score(
            lgbm, X_train, y_train.ravel(),
            cv=kf, scoring='neg_mean_absolute_percentage_error'
        )
        mape_score = -scores.mean()

        return mape_score


# --- 1. lepes: Elozsetes kereses teg tartomannyoal ---
params_dict = {
    'n_estimators': [100, 200, 400],
    'learning_rate': [0.001, 0.01, 0.1],
    'num_leaves': [5, 10, 20],
    'max_depth': [5, 7, 10],
    'min_data_in_leaf': [5, 10, 20],
    'feature_fraction': [0.2, 0.5, 1.0]
}

# Alapertelmezett TPE Sampler-rel
study = optuna.create_study(direction='minimize')
study.optimize(
    lambda trial: objective(trial, params_dict),
    n_trials=100
)

print(f"Legjobb parameterek: {study.best_params}")
print(f"Legjobb MAPE: {study.best_value * 100:.2f}%")
# Eredmeny: ~55.08% MAPE, ~1 perc (vs Grid Search ~5 perc)


# --- 2. lepes: Genetikus algoritmussal ---
study_ga = optuna.create_study(
    direction='minimize',
    sampler=optuna.samplers.NSGAIISampler()
)
study_ga.optimize(
    lambda trial: objective(trial, params_dict),
    n_trials=100
)

print(f"GA - Legjobb MAPE: {study_ga.best_value * 100:.2f}%")


# --- 3. lepes: Finomhangolas -- szukitett tartomany ---
params_dict_fine = {
    'n_estimators': [150, 200, 250],
    'learning_rate': [0.007, 0.01, 0.02],
    'num_leaves': [7, 10, 13],
    'max_depth': [4, 7, 10],
    'min_data_in_leaf': [7, 10, 13],
    'feature_fraction': [0.8, 1.0]
}

study_fine = optuna.create_study(
    direction='minimize',
    sampler=optuna.samplers.NSGAIISampler()
)
study_fine.optimize(
    lambda trial: objective(trial, params_dict_fine),
    n_trials=100
)

print(f"Finomhangolt MAPE: {study_fine.best_value * 100:.2f}%")
# Eredmeny: ~54.36% -> tovabbi szukites utan ~54.15%


# --- 4. lepes: Meg szukebb tartomany ---
params_dict_finer = {
    'n_estimators': [230, 250, 270],
    'learning_rate': [0.009, 0.01, 0.015],
    'num_leaves': [9, 10, 11],
    'max_depth': [3, 4, 5],
    'min_data_in_leaf': [12, 13, 14],
    'feature_fraction': [0.9, 1.0]
}

study_finer = optuna.create_study(
    direction='minimize',
    sampler=optuna.samplers.NSGAIISampler()
)
study_finer.optimize(
    lambda trial: objective(trial, params_dict_finer),
    n_trials=100
)

print(f"Vegso finomhangolt MAPE: {study_finer.best_value * 100:.2f}%")
# Eredmeny: ~54.15%


# --- 5. lepes: Vegso ellenorzes a test halmazon ---
lgbm_final = lgb.LGBMRegressor(**study_finer.best_params)
lgbm_final.fit(X_train, y_train)
y_pred_test = lgbm_final.predict(X_test)
test_mape = mean_absolute_percentage_error(y_test, y_pred_test) * 100
print(f"Test MAPE: {test_mape:.2f}%")
# Eredmeny: ~54.75% (validation: 54.15% -- elfogadhato kulonbseg)
```

#### Elonyok es Hatranyok

| Szempont | Ertekeles |
|---|---|
| **Elony** | Sokkal gyorsabb mint Grid Search (1 perc vs 5 perc, hasonlo eredmeny) |
| **Elony** | Adaptiv: tanul a korabbi eredmenyekbol |
| **Elony** | Tobb sampling algoritmus tamogatasa |
| **Elony** | Konnyedne szukitheto a keresesi ter az eredmenyek alapjan |
| **Hatrany** | Nem garantalja a globalis optimumot |
| **Hatrany** | A kategorikus parametereknel korlatozott a Bayesian elon |

---

## Algoritmus-Specifikus Hyperparamater Utmutato

### Linear Regression / Ridge / Lasso

A sima linearis regresszionak **nincsenek hangolhato hyperparameterei** -- ezert kozvetlenul nem optimalizalhato. A Ridge es Lasso regresszio viszont regularizaciot alkalmaznak, ami mar hangolhato.

| Hyperparamater | Leiras | Tipikus range | Hatas az overfittingre |
|---|---|---|---|
| `alpha` | Regularizacios ero (Ridge/Lasso) | `[0.001, 0.01, 0.1, 1, 10, 100]` | Magasabb alpha = kevesebb overfit |
| `tol` | Tolerancia -- leallasi kriterium | `[1e-4, 1e-3, 1e-2]` | Nagyobb tol = hamarabb leall = kevesebb overfit |
| `solver` | Megoldo algoritmus | `['auto', 'svd', 'cholesky', 'lsqr', 'sparse_cg', 'sag', 'saga']` | Nem kozvetlen hatas, de egyes solverek mas adattipusokra jobbak |

**Megjegyzesek:**
- Az `alpha` a legfontosabb paramater: magas alpha erosebb regularizaciot jelent, ami kisebb, altalanositottabb modellt eredmenyez
- A `solver` valasztasa az adathalmaz meretetol es jellemetol fugg (nagy adatnal `sag`/`saga` gyorsabb)
- A kurzusban a legjobb eredmeny: **71.01% MAPE** (126 kombinacioval, GridSearchCV)

#### Kod pelda -- Manualis Ridge kereses

```python
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import KFold

kf = KFold(n_splits=5, shuffle=True, random_state=42)
alpha_values = [0.001, 0.01, 0.1, 1, 10, 100]

alpha_mape = {alpha: [] for alpha in alpha_values}

for alpha in alpha_values:
    for train_index, cv_index in kf.split(X_train):
        ridge_model = Ridge(alpha=alpha)
        ridge_model.fit(X_train.iloc[train_index], y_train[train_index])
        y_cv_pred = ridge_model.predict(X_train.iloc[cv_index])
        cv_mape = mean_absolute_percentage_error(
            y_train[cv_index], y_cv_pred) * 100
        alpha_mape[alpha].append(cv_mape)

# Atlagos MAPE alpha ertekenkent
mean_cv_mape = {
    alpha: sum(mapes)/len(mapes)
    for alpha, mapes in alpha_mape.items()
}
print(mean_cv_mape)
# Legjobb: alpha=0.001 -> 71.03% MAPE
```

---

### SVM (Support Vector Machine / SVR)

| Hyperparamater | Leiras | Tipikus range | Hatas az overfittingre |
|---|---|---|---|
| `C` | Regularizacios paramater -- hibabutetes erejet szabalyozza | `[0.1, 1, 10, 100]` | Kisebb C = kevesebb overfit |
| `kernel` | Kernelfuggveny tipusa | `['linear', 'poly', 'rbf', 'sigmoid']` | `linear` egyszerubb modell, `rbf` osszetettebb |
| `gamma` | Kernel koefficiens -- adatpontok hatokore | `['scale', 'auto']` vagy `[0.001, 0.01, 0.1]` | Kisebb gamma = simabb dontesi hatar = kevesebb overfit |
| `epsilon` | Epsilon-cso merete (SVR) -- megengedett hibahatart | `[0.001, 0.01, 0.1]` | Nagyobb epsilon = nagyobb turelemboveszeg = kevesebb overfit |

**Megjegyzesek:**
- A `gamma` csak bizonyos kerneleknel allithato be (`rbf`, `poly`, `sigmoid`)
- A paramaterek beallitasanal erdemes logaritmikus leptkeket hasznalni (pl. 0.1, 1, 10, 100)
- A kurzusban a legjobb eredmeny: **69.6% MAPE** (96 kombinacioval, GridSearchCV)

#### Kod pelda

```python
from sklearn.svm import SVR
from sklearn.model_selection import GridSearchCV

param_grid_svm = {
    'C': [0.1, 1, 10, 100],
    'kernel': ['linear', 'poly', 'rbf', 'sigmoid'],
    'gamma': ['scale', 'auto'],
    'epsilon': [0.001, 0.01, 0.1]
}

svm_model = SVR()

grid_search_svm = GridSearchCV(
    estimator=svm_model,
    param_grid=param_grid_svm,
    cv=kf,
    scoring='neg_mean_absolute_percentage_error',
    verbose=1,
    n_jobs=-1
)

grid_search_svm.fit(X_train, y_train.ravel())

print(f"Legjobb parameterek: {grid_search_svm.best_params_}")
print(f"Legjobb MAPE: {-grid_search_svm.best_score_ * 100:.2f}%")
```

---

### LightGBM

| Hyperparamater | Leiras | Tipikus range | Hatas az overfittingre |
|---|---|---|---|
| `n_estimators` | Boosting iteraciok (fak) szama | `[100, 200, 400]` | Tobb fa = jobb tanitas, de tobb overfit kockazat |
| `learning_rate` | Tanulasi rata -- milyen gyorsan tanul | `[0.001, 0.01, 0.1]` | Kisebb = lassabb tanulas, pontosabb, de tobb iteracio kell |
| `num_leaves` | Levelek maximalis szama a faban | `[5, 10, 20]` | Tobb level = osszetettebb modell = tobb overfit |
| `max_depth` | Fa maximalis melysege | `[5, 7, 10]` vagy `[-1]` (korlatlan) | Melyebb fa = tobb overfit |
| `min_data_in_leaf` | Minimalis adatpont szam levlenkent | `[5, 10, 20]` | Magasabb ertek = kevesebb overfit |
| `feature_fraction` | Feature-ok hanyada iteracionkent | `[0.2, 0.5, 1.0]` | Kisebb hanyad = kevesebb overfit (veletlenszeru feature valasztas) |
| `boosting_type` | Boosting strategia | `['gbdt', 'dart', 'rf']` | `dart` dropouttal regularizal |
| `force_col_wise` | Oszlopenkenti histogram epites kenyszeritese | `[True]` | Nem hat az overfittingre, de gyorsithat |

**Finomhangolasi strategia** (az Optuna pelda alapjan):

1. Teg tartomany: `n_estimators=[100,200,400]`, `learning_rate=[0.001,0.01,0.1]` stb.
2. Elso szukites: `n_estimators=[150,200,250]`, `learning_rate=[0.007,0.01,0.02]` stb.
3. Masodik szukites: `n_estimators=[230,250,270]`, `learning_rate=[0.009,0.01,0.015]` stb.

A kurzusban elert eredmenyek:
- Grid Search: **54.85%** MAPE (729 kombinacio, ~5 perc)
- Optuna (100 trial): **55.08%** MAPE (~1 perc)
- Optuna finomhangolva: **54.15%** MAPE (iterativ szukitessel)
- Test halmazon: **54.75%** MAPE

#### Kod pelda -- GridSearchCV vizualizacioval

```python
from sklearn.model_selection import GridSearchCV
import lightgbm as lgb
import matplotlib.pyplot as plt

# n_estimators hatas vizualizalasa
param_grid_lgb = {
    'n_estimators': list(range(10, 210, 10))  # 10-tol 200-ig tizesevel
}

lgb_model = lgb.LGBMRegressor()

grid_search_lgb = GridSearchCV(
    estimator=lgb_model,
    param_grid=param_grid_lgb,
    cv=kf,
    scoring='neg_mean_absolute_percentage_error',
    verbose=1,
    n_jobs=-1,
    return_train_score=True  # Train score is visszaadjuk
)

grid_search_lgb.fit(X_train, y_train.ravel())

# Eredmenyek vizualizalasa
mean_test_scores = -grid_search_lgb.cv_results_['mean_test_score'] * 100
mean_train_scores = -grid_search_lgb.cv_results_['mean_train_score'] * 100
n_estimators_range = param_grid_lgb['n_estimators']

plt.figure(figsize=(10, 6))
plt.plot(n_estimators_range, mean_test_scores,
         label='Validation MAPE', marker='o')
plt.plot(n_estimators_range, mean_train_scores,
         label='Train MAPE', marker='x')
plt.xlabel('Estimatorok szama (n_estimators)')
plt.ylabel('MAPE (%)')
plt.title('Train es Validation MAPE vs Estimatorok szama')
plt.legend()
plt.grid(True)
plt.show()
# A train hiba folyamatosan csokken, a validation minimum ~30 estimatornal van
```

#### Kod pelda -- Optuna-val (reszletes)

Lasd a fenti [Bayesian Optimalizacio / Optuna szekcioot](#kod-pelda-optuna-val-lightgbm) a teljes Optuna workflow-ert LightGBM-mel.

---

### Random Forest

| Hyperparamater | Leiras | Tipikus range | Hatas az overfittingre |
|---|---|---|---|
| `n_estimators` | Fak szama az erdoben | `[50, 100, 200, 500]` | Tobb fa altalaban jobb, de csokeno hatarhaszon |
| `max_depth` | Fa maximalis melysege | `[3, 5, 7, 10, 15, None]` | Melyebb fa = tobb overfit |
| `min_samples_split` | Minimalis mintaszam felosztashoz | `[2, 5, 10, 20]` | Magasabb = kevesebb overfit |
| `min_samples_leaf` | Minimalis mintaszam levelenkent | `[1, 2, 5, 10]` | Magasabb = kevesebb overfit |
| `max_features` | Feature-ok hanyada felosztaskor | `['sqrt', 'log2', 0.5, 0.8]` | Kisebb hanyad = kevesebb overfit + gyorsabb |
| `bootstrap` | Bootstrap mintavetelezas hasznalata | `[True, False]` | `True` segit a regularizacioban |

#### Kod pelda

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import randint, uniform

param_distributions = {
    'n_estimators': randint(50, 500),
    'max_depth': randint(3, 15),
    'min_samples_split': randint(2, 20),
    'min_samples_leaf': randint(1, 10),
    'max_features': uniform(0.1, 0.9)
}

rf = RandomForestRegressor(random_state=42)

search = RandomizedSearchCV(
    rf, param_distributions,
    n_iter=100, cv=5,
    scoring='neg_mean_absolute_percentage_error',
    n_jobs=-1, random_state=42
)

search.fit(X_train, y_train.ravel())
print(f"Legjobb parameterek: {search.best_params_}")
print(f"Legjobb MAPE: {-search.best_score_ * 100:.2f}%")
```

---

### XGBoost

| Hyperparamater | Leiras | Tipikus range | Hatas az overfittingre |
|---|---|---|---|
| `n_estimators` | Boosting iteraciok szama | `[100, 200, 500, 1000]` | Tobb = tobb overfit kockazat (early stopping javasolt) |
| `learning_rate` (`eta`) | Tanulasi rata | `[0.01, 0.05, 0.1, 0.3]` | Kisebb = lassabb, de pontosabb tanulas |
| `max_depth` | Fa maximalis melysege | `[3, 5, 7, 10]` | Melyebb = tobb overfit |
| `min_child_weight` | Minimalis sulycsoport levelben | `[1, 3, 5, 7]` | Magasabb = kevesebb overfit |
| `subsample` | Adatok hanyada iteracionkent | `[0.6, 0.8, 1.0]` | Kisebb = kevesebb overfit |
| `colsample_bytree` | Feature-ok hanyada fankent | `[0.6, 0.8, 1.0]` | Kisebb = kevesebb overfit |
| `reg_alpha` | L1 regularizacio | `[0, 0.01, 0.1, 1]` | Magasabb = erosebb regularizacio |
| `reg_lambda` | L2 regularizacio | `[0, 0.01, 0.1, 1]` | Magasabb = erosebb regularizacio |
| `gamma` | Minimalis loss csokkenes felosztashoz | `[0, 0.1, 0.5, 1]` | Magasabb = kevesebb felosztast enged |

#### Kod pelda -- Optuna-val

```python
import optuna
import xgboost as xgb
from sklearn.model_selection import cross_val_score

def xgb_objective(trial):
    param = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 7),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-4, 1.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-4, 1.0, log=True),
    }

    model = xgb.XGBRegressor(**param, random_state=42)
    scores = cross_val_score(
        model, X_train, y_train.ravel(),
        cv=5, scoring='neg_mean_absolute_percentage_error'
    )
    return -scores.mean()

study = optuna.create_study(direction='minimize')
study.optimize(xgb_objective, n_trials=100)

print(f"Legjobb parameterek: {study.best_params}")
print(f"Legjobb MAPE: {study.best_value * 100:.2f}%")
```

---

## Gyakorlati Utmutato

### Hyperparamater optimalizalas workflow

Az alabbi lepessor javasolt barmely modellhez:

```
1. Adat elokeiszites
   - Train/Validation/Test felosztasa
   - Skalazas (pl. MinMaxScaler(0.01, 1) MAPE-hez)
   - K-Fold CV beallitasa (tipikusan 5 split)
       |
       v
2. Baseline modell
   - Alapbeallitasokkal futatas
   - Baseline MAPE rogzitese
       |
       v
3. Elso kereses -- tag tartomany
   - Grid Search VAGY Optuna 100 trial
   - Logaritmikus lepteku parameterek (0.001, 0.01, 0.1, 1, 10)
   - Eredmenyek elemzese
       |
       v
4. Iterativ finomhangolas
   - A legjobb parameterek kornyezetenek szukitese
   - Ujabb Optuna futas a szukitett terben
   - Ismetelni amig javul az eredmeny
       |
       v
5. Vegso ellenorzes
   - Legjobb parameterekkel tanthatsatas az egesz train halmazon
   - Ertekeles a TEST halmazon (NEM a validation-on!)
   - Elfogadhato-e a kulonbseg validation es test kozott?
       |
       v
6. Vegso modell
```

### Tipikus hibak

1. **Data leakage a cross-validationben**: Ha a skalazast vagy feature engineeringet a teljes adathalmazon vegezzuk el a CV felosztasa elott, az informaciot szivarogtat a validacios halmazba. Megoldas: `Pipeline` hasznalata.

2. **Tul nagy keresesi ter**: Ha minden parametert minden lehetseges erteknel kiprobalnankk, a kombinaciok szama robbanasszeruen no. Megoldas: eloszor teg racsot hasznalj, majd szukits.

3. **Validation-on valo tuloptimalizalas**: Ha tul sokszor szukitjuk a parameterteret a validation eredmenyek alapjan, implicit modon raoptimalizalunk a validation halmazra. Ezert fontos a vegso teszt kulon test halmazon.

4. **Rossz metrika valasztasa**: A `scoring` parameter helyes beallitasa kritikus. Az sklearn-ben a MAPE negativ ertekke alakithato: `'neg_mean_absolute_percentage_error'`.

5. **Y-ertekek nulla-erteke MAPE-nel**: MAPE nem szamolhato, ha Y-ban nulla van. Megoldas: MinMaxScaler `feature_range=(0.01, 1)`.

### Early stopping

Az early stopping megakadalyozza a felesleges iteraciokat a boosting algoritmusoknal:

```python
import lightgbm as lgb

lgb_model = lgb.LGBMRegressor(
    n_estimators=1000,  # magas szam -- az early stopping leallitja
    learning_rate=0.01
)

lgb_model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=10)
    ]
)

# A modell automatikusan leall, ha 50 iteracion at nem javul
```

A kurzusban latott pelda szerint az `n_estimators` vs MAPE gorbe is ezt mutatja: a train hiba folyamatosan csokken, de a validation MAPE ~30 estimatornal el a minimumot, utana no. Az early stopping automatikusan megtalaja ezt a pontot.

### Kod peldak hivatkozasa

A fenti kod peldak onallo Python scriptbe osszesitett valtozata:
`_kod_peldak/hyperparameter_optuna.py`

---

## Osszehasonlito Tablazat

| Modszer | Sebessg | Hatekonysag | Mikor hasznald |
|---|---|---|---|
| **Grid Search** | Lassu (exponencialis) | Maximalis (a racs legjobbja) | Kis keresesi ter, keves paramater, reprodukalhato eredmeny kell |
| **Random Search** | Kozepes | Jo (statisztikailag haterekony) | Nagy keresesi ter, folytonos paramaterek, elso felterkepezeshez |
| **Optuna (TPE)** | Gyors | Nagyon jo | Legtobb esetre javasolt, foleg sok paramaterel |
| **Optuna (NSGA-II)** | Gyors | Jo | Tobbcelunk optimalizalas, genetikus megkozelites kellenel |
| **Manualis kereses** | Valtozo | Gyenge | Nagyon keves paramater eseten (pl. egyetlen alpha) |

**Gyakorlati osszehasonlitas a kurzusbol** (LightGBM, diabetes adathalmaz):

| Modszer | Eredmeny (MAPE) | Futasi ido | Kombinaciok/Trialok |
|---|---|---|---|
| Grid Search CV | 54.85% | ~5 perc | 729 |
| Optuna (100 trial) | 55.08% | ~1 perc | 100 |
| Optuna (50 trial) | 55.13% | ~19 mp | 50 |
| Optuna (20 trial) | 55.40% | ~12 mp | 20 |
| Optuna finomhangolva | 54.15% | ~1 perc | 100 (szuk ter) |
| Vegso (test halmazon) | 54.75% | -- | -- |

---

## Gyakori Hibak es Tippek

### Hibak

- **Data leakage a CV-ben**: Mindig a CV fold-okon belul skalazz es transformalj, ne eloette! Hasznalj `Pipeline`-t az sklearn-bol.
- **Tul nagy keresesi ter**: Ne tedd be az osszes lehetseges erteket egyszeree. Kezdj logaritmikus leptekkel (0.001, 0.01, 0.1, 1, 10), es szukits.
- **Validation vs test osszekeveres**: A hyperparamater optimalizalas a **validation** halmazra tortenijk. A vegso ellenorzes a **test** halmazon. Ha a validation es test MAPE kozott nagy a kulonbseg, az tul-optimalizalasra utal.
- **n_jobs beallitas elfelejtese**: Az `n_jobs=-1` beallitas nelkul a Grid Search csak egy processzormagot hasznal -- ez dramatikusan lassabb.
- **MAPE ertek ertelmezese sklearn-ben**: Az sklearn `neg_mean_absolute_percentage_error` negativ erteket ad, szoroznai kell -1-gyel es 100-zal a szazalekos MAPE-hoz.

### Tippek

- **Logaritmikus leptlekek**: Paramatereknel (pl. `C`, `alpha`, `learning_rate`) hasznalj 10-es szorzast: `[0.001, 0.01, 0.1, 1, 10, 100]`
- **Iterativ szukites**: Az Optuna legjobb eredmenye kore szukitsd a tartomanyt, es futtass ujra. Pelda: ha a legjobb `n_estimators=200`, probalj `[150, 200, 250]`-et.
- **Verbose beallitas**: Allitsd be `verbose=1`-re vagy magasabbra, hogy lasd a folyamat allapotaat.
- **Kevesebb trial is eleg lehet**: Az Optuna 50 trial-lal is kozel annyit er el, mint 100-zal, de felannyi ido alatt.
- **LightGBM figyelmeztetesek elnemitasa**: Hasznald a `suppress_stdout_stderr()` context managert.
- **ravel() hasznalata**: Az `y_train.ravel()` szukseges, hogy az y egydimenziossaa valjon -- kulonben figyelmeztetes jelenik meg.

---

## Kapcsolodo Temak

- [06_modell_validacio_es_metrikak.md](06_modell_validacio_es_metrikak.md) -- Cross-validation, MAPE es mas metrikak reszletesesen
- [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- A hangolando algoritmusok (Ridge, SVM, LightGBM, Random Forest) elmeleti hattere
- [13_deep_learning_alapok.md](13_deep_learning_alapok.md) -- Deep Learning hyperparameter tuning: retegszam, neuronszam, learning rate, epoch

---

## Tovabbi Forrasok

- **Optuna dokumentacio**: [https://optuna.readthedocs.io/](https://optuna.readthedocs.io/)
- **sklearn Hyperparameter Tuning utmutato**: [https://scikit-learn.org/stable/modules/grid_search.html](https://scikit-learn.org/stable/modules/grid_search.html)
- **LightGBM paramater hangolasi utmutato**: [https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html](https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html)
- **XGBoost paramaterek**: [https://xgboost.readthedocs.io/en/latest/parameter.html](https://xgboost.readthedocs.io/en/latest/parameter.html)

---

> **Forras**: Cubix EDU ML Engineering kurzus -- 5. het, 12-14. lecke (Hyperparamater optimalizalas - Linear Regression/Ridge, SVM, Optuna/LightGBM) + Jupyter notebook (`5_week_Cubix_ML_Engineer_Evaluation_Optimization.ipynb`, cellak 106-134).
