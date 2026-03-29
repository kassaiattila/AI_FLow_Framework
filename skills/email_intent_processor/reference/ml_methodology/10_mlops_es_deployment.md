# MLOps es Deployment

## Gyors Attekintes

> Az **MLOps** (Machine Learning Operations) a **DevOps** elveit alkalmazza ML rendszerekre. Celja a modellezestol a production kornyezetig tarto teljes eletciklus automatizalasa, monitorozasa es karbantartasa. A kurzus gyakorlati peldajan keresztul (horse-colic dataset, XGBoost modell, Flask REST API) mutatjuk be a **train pipeline**, **inference pipeline** es **REST API deployment** megvalositasat.

---

## Kulcsfogalmak

| Fogalom | Jelentes |
|---------|---------|
| **DevOps** | Fejlesztes (Dev) es uzemeltetes (Ops) egyesitest celzo gyakorlatok osszessege |
| **MLOps** | A DevOps kiterjesztese ML rendszerekre: adat + modell + infrastruktura kezelese |
| **CI/CD** | **Continuous Integration** / **Continuous Deployment** -- folyamatos integracio es kitelepites |
| **Inference** | A betanitott modell hasznalata uj adatokon torteno elorejelzesre |
| **Batch Inference** | Nagy mennyisegu adat egyszerre torteno feldolgozasa (offline) |
| **Online Inference** | Valos ideju, egyedi keresenkenti elorejelzes (REST API-n keresztul) |
| **Technical Debt** | **Technikai adossag** -- rovid tavu megoldasok miatti hosszu tavu koltsegnovekedes |
| **Data Drift** | Az eles adatok eloszlasanak valtozasa a tanito adatokhoz kepest |
| **Concept Drift** | A cel-valtozo es a feature-ok kozotti kapcsolat megvaltozasa |
| **Artifact** | A pipeline soran letrehozott es mentett objektum (modell, scaler, encoder fajlok) |
| **Pipeline** | Egymast koveto adatfeldolgozasi es modellezesi lepesek lanca |
| **REST API** | **Representational State Transfer** -- webes interfesz a modell eleresere |
| **Model Serving** | A betanitott modell elerehetove tetele production kornyezetben |
| **Model Registry** | Modellverziok kozponti taroloja es nyilvantartasa |
| **Shadow Deployment** | Az uj modell production forgalmat kap, de valaszai nem jutnak el a felhasznalohoz |
| **Canary Deployment** | A forgalom kis reszet az uj modellre iranyitjak, fokozatosan novelve |
| **A/B Testing** | Ket modellverzio parhuzamos futtatasa teljesitmeny-osszehasonlitasra |
| **Blue-Green Deployment** | Ket azonos kornyezet kozotti azonnali atkapcsolas |
| **POC** | **Proof of Concept** -- koncepcionalis bizonyitas |
| **MVP** | **Minimum Viable Product** -- minimalis eletkepessegu termek |
| **Endpoint** | REST API vegpont, amelyen keresztul a modell elerheto |

---

## DevOps Alapok es Ciklus

A **DevOps** celja a szoftverfejlesztes es az uzemeltetes kozotti szakadek athidalasa. A folyamat egy koralapot (ciklust) kovet, amelynek minden fazisa visszacsatol az elozo lepesekre.

### DevOps korforgas

```
Plan --> Code --> Build --> Test --> Release --> Deploy --> Operate --> Monitor
  ^                                                                        |
  |________________________________________________________________________|
```

A fazisok reszletesen:

| Fazis | Cel | Tipikus eszkozok |
|-------|-----|-----------------|
| **Plan** | Kovetelmeny-gyujtes, feladattervezes | Jira, Trello, GitHub Issues |
| **Code** | Forrasfejlesztes, verziokontroll | Git, GitHub, GitLab |
| **Build** | Forditas, csomag keszites | Docker, Maven, pip |
| **Test** | Automatizalt tesztek futtatasa | pytest, unittest, Jenkins |
| **Release** | Verzio kiadjanak eloszkeszitese | CI/CD pipeline, GitHub Actions |
| **Deploy** | Telepites production kornyezetbe | Kubernetes, AWS, Azure |
| **Operate** | Futtatasi kornyezet uzemeltetese | Terraform, Ansible |
| **Monitor** | Teljesitmeny- es hibafigyeles | Prometheus, Grafana, ELK Stack |

### Miert fontos a DevOps?

- **Gyorsabb szallitas**: rovidebb ciklusok, gyakoribb kiadas
- **Kevesebb hiba**: automatizalt tesztek es deploy elfogjak a problemakat
- **Jobb egyuttmukodes**: a fejlesztok es az uzemeltetok kozos felelossege
- **Reprodukalhatosag**: minden lepes dokumentalt es automatizalt

---

## MLOps: Adat + Modell + DevOps

Az **MLOps** a DevOps harom pillerrel egesziti ki:

```
                    +------------------+
                    |      MLOps       |
                    +------------------+
                   /        |          \
          +-------+    +--------+    +-------+
          | Data  |    |   ML   |    | DevOps|
          | Eng.  |    | Model  |    |       |
          +-------+    +--------+    +-------+
```

### Harom piller

1. **Data Engineering**: adatgyujtes, tisztitas, tarolasa, verziozas
2. **ML Modelling**: feature engineering, modell tanitas, validacio, kiserletkezeles
3. **DevOps**: CI/CD, deployment, monitorozas, infrastruktura

### Miert kell az MLOps?

A hagyomanyos szoftverfejlesztes es az ML-rendszerek kozotti kulonbseg alapveto:

| Szempont | Hagyomanyos szoftver | ML rendszer |
|----------|---------------------|-------------|
| **Determinisztikus** | Igen | Nem -- a kimenet az adattol fugg |
| **Teszt** | Egyertelmu pass/fail | Metrika-alapu (accuracy, F1 stb.) |
| **Kod aranya** | A termek ~100%-a kod | **Az ML kod a rendszer 5-10%-a** |
| **Valtozas forrasa** | Kovetelmeny-valtozas | Adat-valtozas (drift) |
| **Karbantartas** | Kod-refaktoring | Modell-ujratanitas, adat-frissites |

> **Fontos felismeres**: Egy production ML rendszerben az ML modell kodja a teljes rendszer kis toredeke. Az infrastruktura, adatkezeles, monitorozas, teszteles, konfiguracio es a serving pipeline teszi ki a munka 90%-at.

```
+------------------------------------------------------------------+
|                    ML RENDSZER PRODUCTION-BEN                     |
|                                                                  |
|  +----+ +-------+ +--------+ +-----------+ +--------+ +------+  |
|  |Data| |Feature| |Config  | |Monitoring | |Serving | |Infra | |
|  |Pipe| |Store  | |Manage  | |& Alerting | |Pipeline| |      | |
|  +----+ +-------+ +--------+ +-----------+ +--------+ +------+  |
|                                                                  |
|                  +------------------+                             |
|                  |   ML Modell Kod  |  <-- EZ CSAK ~5-10%        |
|                  +------------------+                             |
|                                                                  |
|  +------+ +--------+ +--------+ +---------+ +-------+ +------+  |
|  |Data  | |Process | |Resource| |Analysis | |Testing| |Auto  | |
|  |Verif.| |Manage  | |Manage  | |Tools    | |       | |ML    | |
|  +------+ +--------+ +--------+ +---------+ +-------+ +------+  |
+------------------------------------------------------------------+
```

---

## Technikai Adossag es Fejlesztesi Fazisok

Az ML-projektek tipikus fejlodesi utja negy fokozaton megy at. Minden fazisnak mas celja, hatarideig es minosegi szintje van.

### POC --> Prototipus --> MVP --> Production

```
POC               Prototipus          MVP                Production
+----------+      +----------+       +----------+       +----------+
| "Mukodik?"|  --> | "Jol     |  -->  | "Hasznal-|  -->  | "Megbiz- |
|           |      |  mukodik?"|      |  hato?"  |       |  hato?"  |
+----------+      +----------+       +----------+       +----------+
 Napok-hetek       Hetek              Honapok            Folyamatos
 Jupyter NB        Script-ek          REST API           CI/CD + Mon.
 Nincs teszt       Alapszintu teszt   Unit + Int. teszt  Teljes pipeline
 Egy adat          Tobb adat          Valos adat         Eles adat
```

| Fazis | Cel | Tipikus kimenet | Teszteles |
|-------|-----|----------------|-----------|
| **POC** | Megvalosithatosag bizonyitasa | Jupyter notebook, gyors kiserlet | Nincs formalis teszt |
| **Prototipus** | Mukodo megoldas bemutatasa | Python scriptek, egyszerubb pipeline | Manualis ellenorzes |
| **MVP** | Felhasznaloknak kiadott elso verzio | REST API, egyszerusitett UI | Unit + integration tesztek |
| **Production** | Megbizhato, skalazodo rendszer | Teljes CI/CD, monitoring, alerting | Automatizalt teszt pipeline |

### Technikai adossag ML-ben

A **technikai adossag** kulonosen veszelyes ML rendszerekben, mert tobb dimenzioban halmozhato:

1. **Adat-adossag**: nincs adatverziozas, nincs validacio, az adatforras valtozik
2. **Modell-adossag**: nehezen reprodukalhato kislerletek, kezi hyperparameter hangglas
3. **Pipeline-adossag**: train es inference pipeline eltero logikaja
4. **Infrastruktura-adossag**: kezi deploy, nincs monitoring

> **Tipp**: A technikai adossag csokkentesere a legfontosabb lepes a **train es inference pipeline konzisztenciajanak biztositasa** -- ugyanazokat az elofeldolgozasi lepeseket kell alkalmazni mindket helyen.

---

## MLOps Ciklus Lepesrol Lepesre

Az MLOps eletciklus a DevOps ciklust az ML-specifikus lepesekkel boviti. A kor folyamatosan forog -- az eles rendszerbol visszacsatolas (feedback) erkezik.

![MLOps pipeline architektura: Backend, Docker, Frontend](_kepek_cleaned/02_tasks_of_ml/slide_21.png)

*1. abra: MLOps pipeline architektura -- Backend (AutoML, MLflow, FastAPI) -> Docker konterizacio -> Frontend (Streamlit). Ez a tipikus production ML rendszer felepitese.*

### Teljes MLOps eletciklus

```
+---> Adat gyujtes
|         |
|    Adat eloeszites
|         |
|    Feature Engineering
|         |
|    Modell tanitas
|         |
|    Modell validacio
|         |               +---> Modell jo?
|         |              /          |
|    Ertekelesi dont  --+     Nem --> Visszateres a Feature Eng. / Tanitas lepeshez
|                              |
|                         Igen |
|                              v
|    Deployment (staging --> production)
|         |
|    Monitoring (metrikak, drift, alertek)
|         |
|    Feedback loop
|         |
+----<----+  (Ujratanitas, ha a teljesitmeny romlik)
```

### A ciklus kulcselemei

| Lepes | Tevekenyseg | Eszkozok |
|-------|-------------|----------|
| **Adat gyujtes** | Forrasok bekotese, ETL/ELT | Airflow, Spark, SQL |
| **Adat eloeszites** | Tisztitas, imputalas, transformacio | pandas, scikit-learn |
| **Feature Engineering** | Uj feature-ok letrehozasa, kivalasztas | pandas, featuretools |
| **Modell tanitas** | Algoritmus kivalasztas, fitting | scikit-learn, XGBoost, TensorFlow |
| **Modell validacio** | Metrikak, cross-validation | scikit-learn metrics, MLflow |
| **Deployment** | Modell kitelepites API-ra | Flask, FastAPI, Docker |
| **Monitoring** | Teljesitmeny kovetese, drift detektalas | Evidently, Prometheus |
| **Feedback** | Ujratanitas, modell frissites | Automatizalt pipeline |

---

## Data Drift es Concept Drift

A production modell teljesitmenye idoben romolhat, meg akkor is, ha a kod valtozatlan. Ket fo ok:

### Data Drift

Az **adateloszlas valtozasa** a tanito es az eles adatok kozott.

**Pelda**: Egy lakasaras modellt 2020-ban tanitsz be. 2023-ban az ingatlanarak jelentosen megvaltoztak, a lakasmeretek es lokacio-eloszlas is mas. A modell bemeneti adatai mar nem hasonlitanak a tanito adatokra.

```
Tanito adat eloszlasa:          Eles adat eloszlasa (1 ev mulva):
    _____                           _____
   /     \                         /     \
  /       \                       /   ____\____
 /    u1   \                     /   /         \
/           \                   /   / u1'       \
-----|--------->               ----|-----|-------->
     u1                             u1   u1'

--> Az eloszlas eltolodott (shifted distribution)
```

### Concept Drift

A **cel-valtozo es a feature-ok kozotti kapcsolat valtozasa**.

**Pelda**: Egy hiteleszkozlesi modell a jovedelem alapjan donti el a hitelerzekelest. Gazdasagi valsag idejen azonos jovedelem mellett is megnott a hitelmulasztas aranya -- a kapcsolat megvaltozott.

| Tipus | Mi valtozik | Pelda |
|-------|-------------|-------|
| **Data Drift** | A bemeneti adatok eloszlasa | Uj felhasznaloi demografia |
| **Concept Drift** | A bemenet-kimenet kapcsolat | Ugyfelviselkedes-valtozas |

### Detektalas es kezeles

```python
# Data drift detektalas -- statisztikai tesztekkel
from scipy.stats import ks_2samp

# Kolmogorov-Smirnov teszt ket eloszlas osszehasonlitasara
stat, p_value = ks_2samp(train_distribution, prod_distribution)
if p_value < 0.05:
    print("ALERT: Szignifikans data drift detektalt!")
```

> **Tipp**: A drift monitorozasra szolgalo eszkozok (pl. **Evidently**, **Alibi Detect**) automatizalt riportokat es alerteket kepesek generalni. Production kornyezetben ezek hasznalata erosen javasolt.

---

## Teszteles ML Rendszerekben

Az ML rendszerek tesztelese tobb szinten tortenik, es tobb szempontot fed le, mint a hagyomanyos szoftverteszteles.

### Tesztelesi szintek

```
+--------------------------------------------------+
|           PRODUCTION ML TESZT PIRAMIS             |
+--------------------------------------------------+
|                                                  |
|            /\      System / E2E tesztek          |
|           /  \     (teljes pipeline)             |
|          /    \                                  |
|         /------\   Integration tesztek           |
|        / Model  \  (komponensek egyuttmukodese)  |
|       / Validacio\                               |
|      /------------\                              |
|     /   Data       \  Data Validation            |
|    /  Validation    \ (adat minoseg)             |
|   /------------------\                           |
|  /    Unit tesztek    \  Egyedi fuggvenyek       |
| /______________________\                         |
+--------------------------------------------------+
```

### Unit tesztek (pytest)

A **unit test** egyedi fuggvenyeket tesztel elkulonitetten.

```python
import pytest
import numpy as np

def test_feature_engineering():
    """Ellenorzi, hogy az uj feature-ok helyesen jonnek letre."""
    df = pd.DataFrame({
        'temp_c': [36.5, 38.0, 39.2],
        'pulse': [60, 80, 110]
    })
    result = create_new_features(df)
    assert 'temp_pulse_ratio' in result.columns
    assert len(result) == 3
    assert not result['temp_pulse_ratio'].isna().any()

def test_preprocessing_output_shape():
    """Ellenorzi, hogy az eloeldolgozas utani alak megfelelo."""
    X_train, X_test = preprocessing_pipeline(raw_data)
    assert X_train.shape[1] == X_test.shape[1]
    assert X_train.shape[0] > 0
```

### Data Validation

Az adatok minoseginek ellenorzese a pipeline elejen:

```python
def test_no_missing_values_in_target():
    """A cel-valtozo nem tartalmazhat hianyzo erteket."""
    assert not df['target'].isna().any(), "Hianyzo ertek a cel-valtozoban!"

def test_feature_ranges():
    """A feature-ok az elvart tartomanyban vannak."""
    assert df['age'].between(0, 120).all(), "Ervenytelen eletkor ertek!"
    assert df['temperature'].between(30, 45).all(), "Ervenytelen homerseklet!"

def test_no_duplicate_rows():
    """Nem lehetnek duplikalt sorok."""
    assert df.duplicated().sum() == 0, f"{df.duplicated().sum()} duplikalt sor!"
```

### Model Validation

A modell teljesitmenek ellenorzese minimalis kovetelmenyek alapjan:

```python
def test_model_accuracy_threshold():
    """A modell pontossaga meghaladja a minimalis kuszoberteket."""
    accuracy = model.get_accuracy()
    assert accuracy >= 0.70, f"Pontossag tul alacsony: {accuracy:.3f}"

def test_model_not_overfitting():
    """A train es test pontossag kozotti kulonbseg elfogadhato."""
    train_acc = model.get_accuracy_full()['train']
    test_acc = model.get_accuracy_full()['test']
    gap = train_acc - test_acc
    assert gap < 0.15, f"Overfitting gyanuja: gap={gap:.3f}"
```

### Train-Inference konzisztencia teszt

Ez az egyik **legkritikusabb** teszt ML rendszerekben -- biztositja, hogy a train pipeline es az inference pipeline ugyanazt az eloeldolgozast vegezze.

```python
def test_train_inference_consistency():
    """
    A train pipeline-bol kapott eredmeny megegyezik
    az inference pipeline-bol kapott eredmennyel
    ugyanarra az adatra.
    """
    # Train pipeline
    model = MLModel()
    df_train = pd.read_csv("train_data.csv")
    model.preprocessing_pipeline(df_train)
    train_accuracy = model.train_and_save_model(df_train)

    # Inference pipeline -- ugyanazzal a sorral
    sample_row = df_train.iloc[0:1].to_dict(orient='records')[0]
    prediction = model.predict(sample_row)

    # Az eloeldolgozas utani feature-ok szamanak egyeznie kell
    assert model.train_features_count == model.inference_features_count
```

> **Gyakori hiba**: A train pipeline mas feature engineering lepeseket alkalmaz, mint az inference pipeline. Ez az ugynevezett **training-serving skew**, az egyik leggyakoribb production ML hiba.

---

## Inference es Deployment Strategiak

### Batch vs Online Inference

| Szempont | **Batch Inference** | **Online Inference** |
|----------|--------------------|--------------------|
| **Mikor fut** | Utemezetten (naponta, orankent) | Valbs ideju keresre |
| **Bemenet** | Nagy adathalmaz (CSV, adatbazis) | Egyedi sor / JSON |
| **Latencia** | Nem kritikus (percek-orak) | Kritikus (ms-mp) |
| **Peldak** | Heti riport, batch scoring | Weboldali ajanlasok, fraud detektalas |
| **Infrastruktura** | ETL pipeline, cron job | REST API, gRPC, load balancer |
| **Skalazas** | Horizontalis (tobb adat, nem tobb user) | Vertikalis + horizontalis (tobb user) |

```python
# Batch inference pelda
def batch_predict(model, data_path):
    """Batch inference: egesz adathalmaz feldolgozasa."""
    df = pd.read_csv(data_path)
    predictions = []
    for _, row in df.iterrows():
        pred = model.predict(row.to_dict())
        predictions.append(pred)
    df['prediction'] = predictions
    df.to_csv("predictions_output.csv", index=False)
    return df

# Online inference pelda
@app.route('/model/predict', methods=['POST'])
def predict():
    """Online inference: egyetlen sor feldolgozasa."""
    inference_row = request.get_json()
    prediction = model.predict(inference_row)
    return jsonify({'prediction': int(prediction)})
```

### Deployment strategiak

Mikor keszult egy uj modellverzio, a kitelepitesi strategia donti el, hogyan kerul a felhasznalokhoz.

#### Shadow Deployment

```
Felhasznaloi keres --> Production modell (V1) --> Valas a felhasznalonak
                   \
                    +-> Shadow modell (V2) --> Csak naplozas (nem valaszol)
```

- Az uj modell **mindent lat**, de a valasz nem jut el a felhasznalohoz
- Cel: az uj modell teljesitmenye osszehasonlithato a regivel kockazat nelkul

#### Canary Deployment

```
Felhasznaloi keresek (100%)
       |
  +----+----+
  |         |
  v         v
 95%       5%
  |         |
  V1        V2 (canary)
  |         |
  +----+----+
       |
   Monitoring: V2 metrikak rendben?
   Igen --> fokozatosan noveljuk V2 aranyt (10%, 25%, 50%, 100%)
   Nem  --> visszaallitjuk V1-re
```

#### A/B Testing

```
Felhasznaloi keresek
       |
  +----+----+
  |         |
  50%      50%
  |         |
  V1        V2
  |         |
  Metrika A  Metrika B
  |         |
  Statisztikai teszt --> melyik a jobb?
```

- **Strukturalt kiserlet**: a forgalom feloszlasa elore meghatarozptt
- **Cel**: statisztikailag szignifikans kulonbseget merni ket modell kozott
- A/B tesztelesnel fontos a **mintameret** es a **szignifikancia-szint**

#### Blue-Green Deployment

```
        +----------+
        | Load     |
        | Balancer |
        +----+-----+
             |
     +-------+-------+
     |               |
  +--+--+         +--+--+
  | Blue|         |Green|
  | (V1)|         | (V2)|
  +-----+         +-----+
  AKTIV           KESZENLETI

  Atkapcsolas: Load Balancer atiranyitja a forgalmat Green-re
  Rollback:    Visszakapcsolas Blue-ra (azonnal)
```

### Deployment strategiak osszehasonlitasa

| Strategia | Kockazat | Rollback | Mikor hasznald |
|-----------|----------|----------|---------------|
| **Shadow** | Nulla | Nem kell | Elso eles teszt, baseline kialakulatlan |
| **Canary** | Alacsony | Gyors (% visszavesz) | Production modellcsere, fokozatos |
| **A/B Testing** | Kozepes | Kozepes | Ket verzio statisztikai osszehasonlitasa |
| **Blue-Green** | Alacsony | Azonnali | Teljes verziovaltag, instant rollback kell |

---

## Gyakorlati Utmutato

### Train Pipeline Felepitese

A train pipeline celja: nyers adatbol betanitott es mentett modell + artifact-ek letrehozasa.

```
1. ADAT BETOLTES
   |
   v
2. ELOELDOLGOZAS
   |- Hianyzo ertekek kezeles ('?' --> NaN --> median/mod)
   |- Oszlopok atnevezese (szokoz eltavolitas)
   |- Feature engineering (uj feature-ok letrehozasa)
   |
   v
3. FEATURE ENGINEERING
   |- create_new_features() -- domainspecifikus uj oszlopok
   |- NaN imputalas (median: folytonos, modusz: kategorikus)
   |- Outlier kezeles (Z-score, |z| > 3 --> median)
   |
   v
4. ENCODING + SKALAZAS
   |- OneHotEncoder kategorikus feature-okre
   |- MinMaxScaler numerikus feature-okre
   |- Encoder es scaler MENTES pickle fajlba
   |
   v
5. MODELL TANITAS
   |- XGBClassifier (vagy mas algoritmus)
   |- train_test_split (80/20)
   |- model.fit(X_train, y_train)
   |
   v
6. ERTEKELEES + MENTES
   |- accuracy_score, classification_report
   |- Modell MENTES pickle fajlba
   |- Osszes artifact egy mappastruktaraba
```

#### Kod: Train Pipeline (MLModel osztalybol)

```python
import pandas as pd
import numpy as np
import pickle
import os
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

class MLModel:
    def __init__(self, model_dir="models/"):
        self.model_dir = model_dir
        self.model = None
        self.encoder = None
        self.scaler = None
        self.columns = None

    def preprocessing_pipeline(self, df):
        """
        Teljes train eloeldolgozasi pipeline.
        Minden lepest elvegez es az artifact-eket menti.
        """
        # 1. '?' ertekek csere NaN-ra
        df = df.replace('?', np.nan)

        # 2. Oszlopnevek tisztitasa
        df.columns = [col.strip().replace(' ', '_') for col in df.columns]

        # 3. Feature engineering -- domain-specifikus uj feature-ok
        df = self.create_new_features(df)

        # 4. Hianyzo ertekek kezelese
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col].fillna(df[col].median(), inplace=True)
        for col in df.select_dtypes(include=['object']).columns:
            df[col].fillna(df[col].mode()[0], inplace=True)

        # 5. Outlier kezeles Z-score-ral
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
            df.loc[z_scores > 3, col] = df[col].median()

        # 6. OneHot encoding
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        if categorical_cols:
            self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
            encoded = self.encoder.fit_transform(df[categorical_cols])
            encoded_df = pd.DataFrame(encoded,
                                      columns=self.encoder.get_feature_names_out())
            df = df.drop(columns=categorical_cols)
            df = pd.concat([df.reset_index(drop=True),
                           encoded_df.reset_index(drop=True)], axis=1)

        # 7. MinMaxScaler
        self.scaler = MinMaxScaler()
        numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()
        df[numeric_features] = self.scaler.fit_transform(df[numeric_features])

        # 8. Artifact-ek mentese
        self._save_artifacts()

        self.columns = df.columns.tolist()
        return df

    def _save_artifacts(self):
        """Encoder, scaler es egyeb artifact-ek mentese pickle-be."""
        os.makedirs(self.model_dir, exist_ok=True)
        if self.encoder is not None:
            with open(os.path.join(self.model_dir, 'encoder.pkl'), 'wb') as f:
                pickle.dump(self.encoder, f)
        if self.scaler is not None:
            with open(os.path.join(self.model_dir, 'scaler.pkl'), 'wb') as f:
                pickle.dump(self.scaler, f)
```

### Inference Pipeline Felepitese

Az inference pipeline a betanitott modell es a mentett artifact-ek hasznalataval dolgozik. **Kritikus**, hogy pontosan ugyanazokat az eloeldolgozasi lepeseket vegezze, mint a train pipeline.

```
1. BEMENET (egyedi sor -- JSON vagy dict)
   |
   v
2. ARTIFACT-EK BETOLTESE
   |- encoder.pkl --> OneHotEncoder
   |- scaler.pkl --> MinMaxScaler
   |- model.pkl --> XGBClassifier
   |
   v
3. ELOELDOLGOZAS (UGYANAZ, mint train-nel!)
   |- Oszlopnevek tisztitasa
   |- Feature engineering (create_new_features)
   |- Hianyzo ertekek kezeles
   |- OneHot encoding (MENTETT encoder.transform())
   |- Skalazas (MENTETT scaler.transform())
   |
   v
4. PREDIKCI0
   |- model.predict(processed_row)
   |- Eredmeny visszaadasa
```

> **Fontos kulonbseg a train es inference pipeline kozott**:
> - Train: `encoder.fit_transform()`, `scaler.fit_transform()` -- tanulja es alkalmazza
> - Inference: `encoder.transform()`, `scaler.transform()` -- csak alkalmazza a mar megtanultat

```python
def preprocessing_pipeline_inference(self, sample_data):
    """
    Inference eloeldolgozas egyetlen adatsorra.
    A mentett artifact-eket hasznalja (encoder, scaler).
    """
    # Dict --> DataFrame
    df = pd.DataFrame([sample_data])

    # Oszlopnevek tisztitasa (UGYANUGY, mint train-nel)
    df.columns = [col.strip().replace(' ', '_') for col in df.columns]

    # Feature engineering (UGYANAZ a fuggveny)
    df = self.create_new_features(df)

    # OneHot encoding a MENTETT encoderrel
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    if categorical_cols and self.encoder is not None:
        encoded = self.encoder.transform(df[categorical_cols])
        encoded_df = pd.DataFrame(encoded,
                                  columns=self.encoder.get_feature_names_out())
        df = df.drop(columns=categorical_cols)
        df = pd.concat([df.reset_index(drop=True),
                       encoded_df.reset_index(drop=True)], axis=1)

    # Skalazas a MENTETT scalerrel
    numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()
    if self.scaler is not None:
        df[numeric_features] = self.scaler.transform(df[numeric_features])

    return df

def predict(self, inference_row):
    """End-to-end predikio: eloeldolgozas + modell prediction."""
    processed = self.preprocessing_pipeline_inference(inference_row)
    prediction = self.model.predict(processed)
    return prediction[0]
```

### REST API Letrehozasa (Flask + flask-restx)

A Flask REST API ket vegpontot biztosit: egyet a modell tanitasara es egyet az inferenciere.

```
REST API Architektura
=====================

  Kliens (browser, curl, Python)
       |
       | HTTP POST
       v
  +------------------+
  | Flask App        |
  | (app.py)         |
  +------------------+
  | /model/train     | <-- CSV feltoltes --> modell tanitas --> accuracy
  | /model/predict   | <-- JSON sor --> predikio --> eredmeny
  +------------------+
       |
       v
  +------------------+
  | MLModel          |
  | (MLModel.py)     |
  +------------------+
  | preprocessing    |
  | train_and_save   |
  | predict          |
  +------------------+
       |
       v
  +------------------+
  | Artifact-ek      |
  | (models/)        |
  +------------------+
  | encoder.pkl      |
  | scaler.pkl       |
  | model.pkl        |
  +------------------+
```

#### /model/train vegpont

```python
from flask import Flask, request, jsonify
from flask_restx import Api, Resource, Namespace

app = Flask(__name__)
api = Api(app, title='ML Model API',
          description='Train es Predict vegpontok')

model_ns = Namespace('model', description='Model muveletek')
api.add_namespace(model_ns)

ml_model = MLModel()

@model_ns.route('/train')
class TrainResource(Resource):
    def post(self):
        """
        Modell tanitas CSV fajlbol.
        POST /model/train -- multipart/form-data, fajl mezo: 'file'
        """
        try:
            file = request.files['file']
            df = pd.read_csv(file)

            # Eloeldolgozas (train pipeline)
            processed_df = ml_model.preprocessing_pipeline(df)

            # Modell tanitas
            accuracy = ml_model.train_and_save_model(processed_df)

            return {
                'status': 'success',
                'accuracy': float(accuracy),
                'message': f'Modell betanitva. Pontossag: {accuracy:.4f}'
            }, 200

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }, 500
```

#### /model/predict vegpont

```python
@model_ns.route('/predict')
class PredictResource(Resource):
    def post(self):
        """
        Predikio egyetlen adatsorra.
        POST /model/predict -- JSON body
        """
        try:
            inference_row = request.get_json()

            prediction = ml_model.predict(inference_row)

            return {
                'status': 'success',
                'prediction': int(prediction),
                'message': 'Predikio sikeres'
            }, 200

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }, 500
```

#### API hasznalat peldak (curl)

```bash
# Modell tanitas CSV fajlbol
curl -X POST http://localhost:5000/model/train \
  -F "file=@train_data.csv"

# Predikio egyetlen sorra
curl -X POST http://localhost:5000/model/predict \
  -H "Content-Type: application/json" \
  -d '{"surgery": "yes", "age": "adult", "temp_of_extremities": "warm"}'
```

### Tesztek irasa (pytest)

A kurzus peldaja egy **train-inference konzisztencia tesztet** mutat be:

```python
# test_train_inference.py

import pytest
import pandas as pd
from MLModel import MLModel

def test_train_inference_consistency():
    """
    Ellenorzi, hogy a train pipeline-bol es az inference pipeline-bol
    ugyanarra az adatra ugyanaz az eredmeny jon-e ki.

    Ez a teszt a training-serving skew detektalasara szolgal.
    """
    model = MLModel()

    # 1. Train pipeline
    df = pd.read_csv("horse.csv")
    model.preprocessing_pipeline(df)
    train_accuracy = model.train_and_save_model(df)

    # 2. Inference pipeline -- az elso train sor hasznalata
    sample = df.iloc[0].to_dict()
    prediction = model.predict(sample)

    # 3. Ellenorzes
    assert train_accuracy > 0.6, \
        f"Train accuracy tul alacsony: {train_accuracy}"
    assert prediction in [0, 1, 2], \
        f"Ervenytelen prediction: {prediction}"
    print(f"Train accuracy: {train_accuracy:.4f}")
    print(f"Prediction for first row: {prediction}")
```

Futtatas:

```bash
# Osszes teszt futtatasa
pytest test_train_inference.py -v

# Csak egy specifikus teszt
pytest test_train_inference.py::test_train_inference_consistency -v
```

---

## Osszehasonlito Tablazat

### Deployment strategiak

| Strategia | Forgalom-felosztasi | Kockazat | Rollback ido | Hasznalati eset |
|-----------|-------------------|----------|--------------|----------------|
| **Shadow** | 100% V1 + 100% V2 (csak log) | Nulla | N/A | Uj modell elso eles tesztje |
| **Canary** | 95/5 --> 50/50 --> 0/100 | Alacsony | Masodpercek | Fokozatos kitelepites |
| **A/B** | 50/50 (fix) | Kozepes | Percek | Statisztikai osszehasonlitas |
| **Blue-Green** | 100/0 <--> 0/100 | Alacsony | Azonnali | Teljes verziovaltag |

### MLOps Maturity Levels

| Szint | Nev | Jellemzok |
|-------|-----|-----------|
| **0** | Nincs MLOps | Manualis kiserletek, Jupyter notebook, kezi deploy |
| **1** | DevOps, nincs MLOps | CI/CD a kodra, de a modell manualis, nincs monitoring |
| **2** | Automatizalt tanitas | Automatikus pipeline a tanitasra, de manualis deploy |
| **3** | Automatizalt deploy | CI/CD a modellre is, A/B tesztek, canary deploy |
| **4** | Teljes MLOps | Automatikus ujratanitas drift detektaas alapjan, teljes monitoring |

### Inference tipusok

| Szempont | **Batch** | **Online (Real-time)** | **Streaming** |
|----------|----------|----------------------|---------------|
| Latencia | Percek-orak | Milliszekundumok | Masodpercek |
| Atbocsatas | Magas (nagy adat) | Alacsony-kozepes | Kozepes |
| Infrastruktura | Cron/scheduler + storage | REST API + load balancer | Kafka/Flink + API |
| Pelda | Ejszakai scoring | Webes ajanlasok | Fraud detektalas streamen |

---

## Gyakori Hibak es Tippek

### Hibak

1. **Training-Serving Skew**: A train es inference pipeline elter. Peldaul a train pipeline `fit_transform()`-ot hasznal, az inference is -- ilyenkor az inference a sajat adatara tanul, nem a train adatokra.

2. **Artifact-ek nem mentese**: A modell train utan a scaler, encoder es egyeb transformaciok nem kerulnek mentesre. Az inference pipeline nem tudja reprodukalni az eloeldolgozast.

3. **Hardcodolt utvonalak**: A fajlutvonalak (model path, data path) hardcodolva vannak a kodban. Kornyezet-valtas (dev --> staging --> prod) soran hibat okoznak.

4. **Nincs modell-verziozas**: Uj modell tanitas felulirja a regit. Ha az uj modell rosszabb, nincs rollback lehetoseg.

5. **Monitoring hianya**: A modell deploy utan nem monitorozzak. Hetek-honapok mulva a teljesitmeny csoendesen leromlik (data drift), de senki nem veszi eszre.

6. **Test-kovezes hianya**: Nincs teszt a pipeline-ban, igy a hibak csak production-ben derulnek ki.

7. **Feature Store hianya**: A feature engineering logika meg van duplikava a train es inference kodban, ahelyett, hogy egy kozos Feature Store-bol szarmazna.

### Tippek

1. **Mindig mentsd az artifact-eket**: Minden encoder, scaler, imputer es a modell maga is pickle fajlba (vagy joblib-be) keruljon, verziozott mappastrukturaban.

2. **Hasznalj pipeline objektumot**: Az sklearn `Pipeline` osztaly biztositja, hogy a train es inference eloeldolgozas konzisztens legyen:

```python
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', MinMaxScaler()),
    ('model', XGBClassifier())
])

# Train
pipeline.fit(X_train, y_train)

# Inference -- garantaltan ugyanaz az eloeldolgozas
pipeline.predict(X_new)
```

3. **Irj train-inference konzisztencia tesztet**: Ahogy a kurzus peldajaban latjuk, ez a legfontosabb teszt ML rendszerekben.

4. **Verziozd a modelleket**: Hasznalj mappastruktturat vagy **MLflow Model Registry**-t a modellverziok nyilvantartasara.

5. **Allits be monitoring alerteket**: Data drift, accuracy csakkenes, latencia-novekedes esetere.

6. **Hasznalj canary deploy-t**: Soha ne csereld le egyszerre a teljes production modellt. A canary deploy minimalizalja a kockazatot.

7. **Dokumentald a pipeline-t**: Minden lepes, parametervalasztas es doontesi pont legyen dokumentalva. A "mi tortent 3 honapja?" kerdesre legyen valasz.

8. **Hasznalj environment valtozokat**: Fajlutvonalak, API kulcsok, konfiguracio ne legyen hardcodolva:

```python
import os

MODEL_DIR = os.environ.get('MODEL_DIR', 'models/')
API_PORT = int(os.environ.get('API_PORT', 5000))
```

---

## Kapcsolodo Temak

- [04_adatelokeszites_es_feature_engineering.md](04_adatelokeszites_es_feature_engineering.md) -- Pipeline es feature engineering alapok, amelyek az MLOps train pipeline reszet kepezik
- [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- Modell tanitasi algoritmusok (XGBoost, Random Forest stb.), amelyeket a pipeline-ba epitunk
- [06_modell_validacio_es_metrikak.md](06_modell_validacio_es_metrikak.md) -- Validacios metrikak (accuracy, F1, AUC), amelyek a model validation lepes alapjat kepezik
- [07_hyperparameter_optimalizalas.md](07_hyperparameter_optimalizalas.md) -- Hyperparameter finomhangolas, amely a train pipeline reszekent automatizalhato

---

## Tovabbi Forrasok

- **MLOps alapok**: [ml-ops.org](https://ml-ops.org/) -- kozossegi referenciaoldal
- **Google MLOps iranyelvek**: [Google Cloud MLOps](https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- **MLflow**: [mlflow.org](https://mlflow.org/) -- kiserletkeoves, modell registry, deployment
- **Evidently AI**: [evidentlyai.com](https://www.evidentlyai.com/) -- data drift es modell-monitoring eszkoz
- **Flask REST API**: [flask-restx dokumentacio](https://flask-restx.readthedocs.io/)
- **XGBoost**: [xgboost.readthedocs.io](https://xgboost.readthedocs.io/)
- **pytest**: [docs.pytest.org](https://docs.pytest.org/)
- **Scikit-learn Pipeline**: [sklearn.pipeline.Pipeline](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html)
- **Hidden Technical Debt in ML Systems (Google, 2015)**: [NeurIPS cikk](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html)
