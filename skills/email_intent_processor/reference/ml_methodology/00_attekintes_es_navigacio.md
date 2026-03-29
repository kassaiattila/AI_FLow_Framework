# Áttekintés és Navigáció

## Mi Ez Az Anyag?

Ez a gyűjtemény a **Cubix EDU ML Engineering kurzus** teljes anyagát dolgozza fel **témánkénti, praktikus útmutatók** formájában. A 101 videó-transzkript (78 + 23 hét 7-8), 5 PDF előadás és 6 Jupyter notebook tartalma **14 tematikus útmutatóba** és **12 futtatható kód példafájlba** lett konszolidálva.

Az anyag **nem előadás-sorrendben**, hanem **ML projekt-workflow szerint** van szervezve, így bármely feladatnál gyorsan megtalálható a releváns tudás.

---

## ML Projekt Workflow

Egy tipikus ML projekt az alábbi lépéseket követi. Minden lépéshez tartozik egy útmutató:

```
1. PROBLÉMA MEGÉRTÉSE          → 01_ml_alapfogalmak
   ├── Milyen típusú feladat? (osztályozás/regresszió/klaszterezés)
   ├── Felügyelt vagy nem felügyelt?
   └── Milyen adatok állnak rendelkezésre?

2. KÖRNYEZET FELÁLLÍTÁSA       → 02_fejlesztoi_kornyezet
   ├── Colab / lokális Jupyter / VS Code
   ├── Könyvtárak telepítése
   └── Adatok betöltése (Pandas)

3. ADATMEGÉRTÉS (EDA)          → 03_adatmegertes_es_eda
   ├── Adatok áttekintése (shape, info, describe)
   ├── Vizualizáció (hisztogram, boxplot, heatmap)
   ├── Korrelációs elemzés
   └── Adatminőség felmérése

4. ADATELŐKÉSZÍTÉS              → 04_adatelokeszites
   ├── Hiányzó értékek kezelése
   ├── Outlier kezelés
   ├── Encoding (kategorikus → numerikus)
   ├── Skálázás
   └── Feature Engineering

5. MODELLEZÉS                   → 05_felugyelt_tanulasi_algoritmusok
   ├── Algoritmus kiválasztása          08_dimenziocsokkentes
   ├── Modell tanítása                  09_klaszterezes
   └── Predikció

6. ÉRTÉKELÉS                    → 06_modell_validacio
   ├── Train/Val/Test split
   ├── Cross-validation
   ├── Metrikák (accuracy, F1, AUC, RMSE...)
   └── Bias-Variance elemzés

7. OPTIMALIZÁLÁS                → 07_hyperparameter_optimalizalas
   ├── GridSearch / RandomSearch
   ├── Optuna (Bayesian optimalizálás)
   └── Modell finomhangolás

8. DEPLOYMENT & MLOPS            → 10_mlops_es_deployment
   ├── Train pipeline felépítése
   ├── Inference pipeline
   ├── REST API (Flask)
   ├── Tesztelés (pytest)
   └── Monitoring (data drift, concept drift)

SPECIÁLIS FELADATOK:
├── Anomália detekció            → 11_anomalia_detektio
├── Ajánlórendszerek             → 12_ajanlorendszerek
└── Deep Learning alapok         → 13_deep_learning_alapok
```

---

## Útmutatók Áttekintése

| # | Útmutató | Tartalom | Sorok | Kód példa |
|---|----------|----------|-------|-----------|
| 01 | [ML Alapfogalmak és Típusok](01_ml_alapfogalmak_es_tipusok.md) | ML/DL fogalmak, tanulási paradigmák, algoritmus-típusok taxonómiája, CRISP-DM | 378 | - |
| 02 | [Fejlesztői Környezet és Pandas](02_fejlesztoi_kornyezet_es_pandas.md) | Colab, IDE-k, Pandas adatkezelés, DataFrame műveletek | 704 | [pandas_alapok.py](_kod_peldak/pandas_alapok.py) |
| 03 | [Adatmegértés és EDA](03_adatmegertes_es_eda.md) | Adatminőség, EDA technikák, vizualizáció, korrelációs elemzés | 652 | [eda_peldak.py](_kod_peldak/eda_peldak.py) |
| 04 | [Adatelőkészítés és Feature Engineering](04_adatelokeszites_es_feature_engineering.md) | Hiányzó értékek, outlierek, encoding, skálázás, Pipeline | 810 | [adat_elokeszites.py](_kod_peldak/adat_elokeszites.py) |
| 05 | [Felügyelt Tanulási Algoritmusok](05_felugyelt_tanulasi_algoritmusok.md) | KNN, lineáris modellek, SVM, döntési fa, ensemble, boosting | 876 | [supervised_ml.py](_kod_peldak/supervised_ml.py) |
| 06 | [Modell Validáció és Metrikák](06_modell_validacio_es_metrikak.md) | Cross-validation, confusion matrix, ROC-AUC, PR-AUC, regressziós metrikák | 933 | [validacio_metrikak.py](_kod_peldak/validacio_metrikak.py) |
| 07 | [Hyperparaméter Optimalizálás](07_hyperparameter_optimalizalas.md) | Grid/Random/Bayes search, Optuna, algoritmus-specifikus HP-k | 801 | [hyperparameter_optuna.py](_kod_peldak/hyperparameter_optuna.py) |
| 08 | [Dimenziócsökkentés](08_dimenziocsokkentes.md) | PCA, SVD, LDA, Kernel PCA, MDS, Isomap, LLE, t-SNE, UMAP | 764 | [dimenziocsokkentes.py](_kod_peldak/dimenziocsokkentes.py) |
| 09 | [Klaszterezés](09_klaszterezes.md) | K-Means, hierarchikus, spectral, GMM, DBSCAN, HDBSCAN | 825 | [klaszterezes.py](_kod_peldak/klaszterezes.py) |
| 10 | [MLOps és Deployment](10_mlops_es_deployment.md) | DevOps, MLOps, CI/CD, train/inference pipeline, REST API, tesztelés | 978 | [mlops_pipeline.py](_kod_peldak/mlops_pipeline.py) |
| 11 | [Anomália Detekció](11_anomalia_detektio.md) | GMM, Isolation Forest, self-supervised learning, anomália vs outlier | 606 | [anomalia_detektio.py](_kod_peldak/anomalia_detektio.py) |
| 12 | [Ajánlórendszerek](12_ajanlorendszerek.md) | Content-based, collaborative filtering, cosine similarity, association rules | 874 | [ajanlorendszerek.py](_kod_peldak/ajanlorendszerek.py) |
| 13 | [Deep Learning Alapok](13_deep_learning_alapok.md) | Perceptron, ANN, aktivációs függvények, multi-label classification, DL architektúrák | 687 | [deep_learning_alapok.py](_kod_peldak/deep_learning_alapok.py) |

**Összesen**: ~12,888 sor útmutató + 12 futtatható Python fájl

---

## Mikor Melyik Útmutatót Használd?

### Feladat szerint

| Kérdés | Útmutató |
|--------|----------|
| "Mi az a gépi tanulás?" | [01 - Alapfogalmak](01_ml_alapfogalmak_es_tipusok.md) |
| "Hogyan állítsam be a környezetet?" | [02 - Fejlesztői környezet](02_fejlesztoi_kornyezet_es_pandas.md) |
| "Hogyan töltsem be és nézzem meg az adatokat?" | [02 - Pandas](02_fejlesztoi_kornyezet_es_pandas.md) + [03 - EDA](03_adatmegertes_es_eda.md) |
| "Hogyan tisztítsam meg az adatokat?" | [04 - Adatelőkészítés](04_adatelokeszites_es_feature_engineering.md) |
| "Melyik algoritmust válasszam?" | [05 - Algoritmusok](05_felugyelt_tanulasi_algoritmusok.md) (összehasonlító táblázat) |
| "Hogyan értékeljem a modellemet?" | [06 - Validáció](06_modell_validacio_es_metrikak.md) |
| "Hogyan javítsam a modell teljesítményét?" | [07 - HP Optimalizálás](07_hyperparameter_optimalizalas.md) |
| "Túl sok feature-öm van, mit tegyek?" | [08 - Dimenziócsökkentés](08_dimenziocsokkentes.md) |
| "Csoportokat szeretnék találni az adatokban" | [09 - Klaszterezés](09_klaszterezes.md) |
| "Hogyan vigyem production-be a modellemet?" | [10 - MLOps](10_mlops_es_deployment.md) |
| "Hogyan detektáljak anomáliákat?" | [11 - Anomália Detekció](11_anomalia_detektio.md) |
| "Ajánlórendszert szeretnék építeni" | [12 - Ajánlórendszerek](12_ajanlorendszerek.md) |
| "Mi az a deep learning / neurális hálózat?" | [13 - Deep Learning](13_deep_learning_alapok.md) |

### ML feladattípus szerint

| Feladattípus | Elsődleges útmutató | Kiegészítő |
|--------------|---------------------|------------|
| **Bináris osztályozás** | [05](05_felugyelt_tanulasi_algoritmusok.md) | [06](06_modell_validacio_es_metrikak.md) (ROC-AUC, F1) |
| **Többosztályos osztályozás** | [05](05_felugyelt_tanulasi_algoritmusok.md) | [06](06_modell_validacio_es_metrikak.md) (macro/micro avg) |
| **Regresszió** | [05](05_felugyelt_tanulasi_algoritmusok.md) | [06](06_modell_validacio_es_metrikak.md) (RMSE, R2) |
| **Klaszterezés** | [09](09_klaszterezes.md) | [08](08_dimenziocsokkentes.md) (vizualizáció) |
| **Dimenziócsökkentés** | [08](08_dimenziocsokkentes.md) | [09](09_klaszterezes.md) (utána klaszterezés) |
| **Imbalanced adathalmaz** | [06](06_modell_validacio_es_metrikak.md) | [04](04_adatelokeszites_es_feature_engineering.md) |
| **Anomália detekció** | [11](11_anomalia_detektio.md) | [09](09_klaszterezes.md) (GMM) |
| **Ajánlórendszer** | [12](12_ajanlorendszerek.md) | [05](05_felugyelt_tanulasi_algoritmusok.md) |
| **Multi-label osztályozás** | [13](13_deep_learning_alapok.md) | [05](05_felugyelt_tanulasi_algoritmusok.md) |
| **MLOps / Deployment** | [10](10_mlops_es_deployment.md) | [06](06_modell_validacio_es_metrikak.md) (tesztelés) |

---

## ML Projekt Checklist

### Adatmegértés fázis
- [ ] Adatok betöltése és első áttekintés (`shape`, `info`, `describe`)
- [ ] Adattípusok ellenőrzése
- [ ] Hiányzó értékek felmérése
- [ ] Target változó eloszlásának vizsgálata
- [ ] EDA: univariáte + bivariáte elemzés
- [ ] Korrelációs mátrix vizsgálata
- [ ] Outlierek azonosítása

### Adatelőkészítés fázis
- [ ] Hiányzó értékek kezelése (imputálás stratégia kiválasztása)
- [ ] Outlierek kezelése (eltávolítás / clipping / transzformáció)
- [ ] Kategorikus változók encoding-ja
- [ ] Numerikus változók skálázása
- [ ] Feature Engineering (új feature-ök, interakciók)
- [ ] Train/Test split (stratified, ha osztályozás)
- [ ] Pipeline összeállítása (ColumnTransformer)

### Modellezés fázis
- [ ] Baseline modell (egyszerű algoritmus, default HP-k)
- [ ] Több algoritmus összehasonlítása (cross-validation)
- [ ] Legjobb 2-3 modell kiválasztása
- [ ] Hyperparaméter optimalizálás (Optuna)
- [ ] Végleges modell értékelése test halmazon
- [ ] Overfitting ellenőrzés (train vs test metrikák)
- [ ] Eredmények dokumentálása

---

## Kód Példák Használata

A `_kod_peldak/` mappában 12 futtatható Python fájl található:

```bash
# Futtatás (bármelyik fájl)
python _kod_peldak/pandas_alapok.py
python _kod_peldak/eda_peldak.py
python _kod_peldak/adat_elokeszites.py
python _kod_peldak/supervised_ml.py
python _kod_peldak/validacio_metrikak.py
python _kod_peldak/hyperparameter_optuna.py
python _kod_peldak/dimenziocsokkentes.py
python _kod_peldak/klaszterezes.py
python _kod_peldak/mlops_pipeline.py
python _kod_peldak/anomalia_detektio.py
python _kod_peldak/ajanlorendszerek.py
python _kod_peldak/deep_learning_alapok.py
```

**Szükséges csomagok**:
```bash
pip install numpy pandas scikit-learn matplotlib seaborn scipy
# Opcionális (boosting könyvtárak):
pip install xgboost lightgbm catboost
# Opcionális (hyperparaméter optimalizálás):
pip install optuna
# Opcionális (dimenziócsökkentés):
pip install umap-learn
# Opcionális (klaszterezés):
pip install hdbscan
# Opcionális (MLOps REST API):
pip install flask flask-restx
```

---

## Gyors Algoritmus-Választó

```
Feladat típusa?
│
├── Van CÍMKE (target) az adatokban? → FELÜGYELT TANULÁS [05]
│   ├── Target kategorikus? → OSZTÁLYOZÁS
│   │   ├── Kevés adat (<1000)? → KNN, SVM, Logistic Regression
│   │   ├── Értelmezhetőség fontos? → Döntési Fa, Logistic Regression
│   │   ├── Maximális pontosság kell? → Random Forest, XGBoost, LightGBM
│   │   └── Sok feature, kevés adat? → SVM (RBF), Ridge Classifier
│   │
│   └── Target folytonos? → REGRESSZIÓ
│       ├── Lineáris kapcsolat? → Linear/Ridge/Lasso Regression
│       ├── Nemlineáris kapcsolat? → Random Forest, XGBoost, SVR
│       └── Sok feature? → Lasso (feature selection), ElasticNet
│
├── NINCS CÍMKE → NEM FELÜGYELT TANULÁS
│   ├── Csoportokat keresek? → KLASZTEREZÉS [09]
│   │   ├── K ismert? → K-Means
│   │   ├── K ismeretlen, outlierek vannak? → DBSCAN, HDBSCAN
│   │   ├── Hierarchiát szeretnék? → Agglomerative Clustering
│   │   └── Soft klaszterek kellenek? → GMM
│   │
│   └── Dimenziókat csökkenteném? → DIMENZIÓCSÖKKENTÉS [08]
│       ├── Lineáris struktúra? → PCA
│       ├── Vizualizáció céljára? → t-SNE, UMAP
│       ├── Felügyelt DR? → LDA
│       └── Nemlineáris manifold? → Isomap, LLE, Kernel PCA
│
├── Modell javítása kell? → OPTIMALIZÁLÁS [06, 07]
│   ├── Overfit? → Regularizáció, több adat, feature selection
│   ├── Underfit? → Komplexebb modell, több feature
│   └── HP hangolás? → Optuna (Bayesian), GridSearchCV
│
├── ANOMÁLIA DETEKCIÓ kell? → [11]
│   ├── Felügyeletlen? → GMM, Isolation Forest
│   └── Self-supervised? → RF Regressor + Z-score
│
├── AJÁNLÓRENDSZER kell? → [12]
│   ├── Item tulajdonságok alapján? → Content-Based Filtering
│   ├── Felhasználói viselkedés alapján? → Collaborative Filtering
│   │   ├── Item-based CF → corrwith, cosine similarity
│   │   └── User-based CF → pairwise_distances
│   └── Kosárelemzés? → Association Rules (Support, Confidence, Lift)
│
├── DEEP LEARNING kell? → [13]
│   ├── Képek? → CNN
│   ├── Szöveg/szekvencia? → RNN, Transformer
│   ├── Generálás? → GAN, Autoencoder
│   └── Egyszerű start? → sklearn MLPClassifier
│
└── PRODUCTION DEPLOYMENT kell? → [10]
    ├── Train pipeline → MLModel osztály, artifact management
    ├── Inference pipeline → Konzisztens előfeldolgozás
    ├── REST API → Flask + flask-restx
    └── Monitoring → Data drift, concept drift
```

---

## Forrás-Hozzárendelés

Az alábbi táblázat mutatja, hogy melyik eredeti Cubix EDU anyag melyik útmutatóba került:

| Eredeti fájl | Útmutató |
|-------------|----------|
| `00_01` (Felület használat) | Bevezető - nem került külön útmutatóba |
| `01_01` (Kick-off LIVE) | [01](01_ml_alapfogalmak_es_tipusok.md) - Q&A |
| `01_02` (Alapfogalmak) | [01](01_ml_alapfogalmak_es_tipusok.md) |
| `01_03` - `01_07` | [01](01_ml_alapfogalmak_es_tipusok.md) |
| `01_08` (ML feladatai) | [01](01_ml_alapfogalmak_es_tipusok.md) |
| `01_12` (LIVE) | [01](01_ml_alapfogalmak_es_tipusok.md) - Q&A |
| `02_01` - `02_05` (ML típusok) | [01](01_ml_alapfogalmak_es_tipusok.md) |
| `02_06` - `02_07` (Eszközök, Colab) | [02](02_fejlesztoi_kornyezet_es_pandas.md) |
| `02_08` - `02_09` (Pandas) | [02](02_fejlesztoi_kornyezet_es_pandas.md) |
| `02_13` (LIVE) | [02](02_fejlesztoi_kornyezet_es_pandas.md) - Q&A |
| `03_01` - `03_03`, `03_10` - `03_11` (EDA) | [03](03_adatmegertes_es_eda.md) |
| `03_04` - `03_09` (Előkészítés) | [04](04_adatelokeszites_es_feature_engineering.md) |
| `04_01` - `04_15` (Algoritmusok) | [05](05_felugyelt_tanulasi_algoritmusok.md) |
| `04_17` (LIVE) | [05](05_felugyelt_tanulasi_algoritmusok.md) - Q&A |
| `05_01` - `05_11` (Validáció) | [06](06_modell_validacio_es_metrikak.md) |
| `05_12` - `05_14` (HP optimalizálás) | [07](07_hyperparameter_optimalizalas.md) |
| `05_17` (LIVE) | [06](06_modell_validacio_es_metrikak.md) - Q&A |
| `06_01` - `06_10` (DR) | [08](08_dimenziocsokkentes.md) |
| `06_11` - `06_17` (Klaszterezés) | [09](09_klaszterezes.md) |
| `07_01` - `07_12` (MLOps, DevOps, CI/CD, REST API) | [10](10_mlops_es_deployment.md) |
| `07_16` (LIVE - Bias/Variance, MLOps) | [10](10_mlops_es_deployment.md) - Q&A |
| `08_01` (Anomália detekció) | [11](11_anomalia_detektio.md) |
| `08_02` - `08_08` (Ajánlórendszerek) | [12](12_ajanlorendszerek.md) |
| `08_09` - `08_10` (Deep Learning, Perceptron) | [13](13_deep_learning_alapok.md) |

### Jupyter Notebookok
| Notebook | Útmutató |
|----------|----------|
| `Cubix_ML_Engineer_Pandas.ipynb` | [02](02_fejlesztoi_kornyezet_es_pandas.md) |
| `Cubix_ML_Engineer_Data_Understanding.ipynb` | [03](03_adatmegertes_es_eda.md) |
| `Cubix_ML_Engineer_ML_algorithms.ipynb` | [05](05_felugyelt_tanulasi_algoritmusok.md) |
| `5_week_Cubix_ML_Engineer_Evaluation_Optimization.ipynb` | [06](06_modell_validacio_es_metrikak.md), [07](07_hyperparameter_optimalizalas.md) |
| `Cubix_ML_Engineer_Unsupervised_Learning.ipynb` | [08](08_dimenziocsokkentes.md), [09](09_klaszterezes.md) |
| `Cubix_ML_Engineer_AnomalyDetection_RecommenderSystems.ipynb` | [11](11_anomalia_detektio.md), [12](12_ajanlorendszerek.md) |

### 7. hét Forráskód
| Fájl | Útmutató |
|------|----------|
| `MLModel.py`, `app.py`, `constants.py`, `utils.py` | [10](10_mlops_es_deployment.md) |
| `train_pipeline.ipynb`, `inference_pipeline.ipynb` | [10](10_mlops_es_deployment.md) |
| `rest_api_client.ipynb`, `test_train_inference.py` | [10](10_mlops_es_deployment.md) |

---

## További Források

Lásd: [_forrasok/hasznos_linkek.md](_forrasok/hasznos_linkek.md) - sklearn dokumentáció, Kaggle, Papers with Code, Optuna, és más hasznos linkek gyűjteménye.
