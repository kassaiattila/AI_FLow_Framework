# Anomalia Detektio (Anomaly Detection)

## Gyors Attekintes

> Az **anomalia detektio** (anomaly detection) celjat az adathalmazban elofordulo szokatlan, vart mintatol eltero megfigylesek azonositasa jelenti. A modszer kulonosen fontos olyan teruleteken, ahol a ritka, de kritikus esemenyek felderitese lenyeges -- peldaul penzugyi csalasfelderites, halozati behatolaseszleles, ipari gephibak elojelzese vagy egeszsegugyi rendellenessegek szurese. A fejezet harom fo megkozelitest mutat be: felugyeletlen modszereket (**GMM**, **Isolation Forest**), **self-supervised learning** alapu detektiot, es a **semi-supervised bridge** strategiat, amely a felugyeletlen eredmenyeket szakertoi cimkekre epitett felugyelt tanulassa alakitja.

---

## Kulcsfogalmak

| Fogalom | Jelentes |
|---------|---------|
| **Anomalia** | Abnormalis, gyanus vagy vart mintatol eltero aktivitas a rendszerben; nem feltetlenul statisztikai kiugro ertek, hanem kontextusfuggo szokatlan viselkedes |
| **Outlier** | Statisztikai kiugro ertek az adatban; az adat eloszlasabol killo egyedi megfigyeles, amely nem feltetlenul gyanus |
| **Data Drift** | Az adat eloszlasanak valtozasa idovel; a modell betanitasakori es a produkcioban kapott adatok kozti elteres |
| **GMM (Gaussian Mixture Model)** | Valoszinusegi modell, amely az adatokat tobb Gauss-eloszlas keverekekent irja le; soft clustering es anomalia skor is szamolhato vele |
| **Isolation Forest** | Izolacion alapulo anomalia-detektalo algoritmus; az anomaliakat konnyebb izolalni, ezert rovid fa-utak jelzik oket |
| **Contamination** | Az Isolation Forest parametere; az adathalmaz feltetelezett anomalia-aranya (pl. 0.02 = 2%) |
| **score_samples** | A GMM metodusa, amely log-valoszinusegi erteket ad minden adatpontra; alacsony skor = valoszinu anomalia |
| **Quantile (kvantilis)** | Az adat eloszlasanak meghatarozott hanyada; a threshold dontes alapja (pl. 5%-os kvantilis) |
| **Z-score** | Standardizalt ertek, amely megmutatja, hany szorasnyira ter el egy ertek az atlagtol; |z| > 3 ritka esemeny (99.7% szabaly) |
| **Self-supervised learning** | Onfeluelyelt tanulas: egy feature-t targetkent kezelunk, a tobbivel prediktaljuk, es a nagy hibaju (residual) pontokat anomalianak tekintjuk |
| **Semi-supervised learning** | Felileg felugyelt tanulas: kis mennyisegu cimkezett adat es nagy mennyisegu cimkezetlen adat kombinacioja |
| **Residual (maradektag)** | A tenyleges es a prediktalt ertek kulonbsege; nagy residual anomaliat jelezhet |
| **Semi-supervised bridge** | Strategia, ahol a felugyeletlen modell eredmenyeit szakerto cimkezi, majd felugyelt modellt epitunk |
| **EM algoritmus** | Expectation-Maximization: a GMM illesztesenek iterativ algoritmusa (E-lepes: valoszinusegek, M-lepes: parameterek frissitese) |

---

## Anomalia vs Outlier vs Data Drift

Ez a harom fogalom gyakran keveredik, de fontos kulonbseg van kozottuk:

![Outlier scatter plot: normalis adatpontok es outlier pontok](_kepek_cleaned/04_data_preparation/slide_07.png)

*1. abra: Outlier detektalas scatter plot-on -- a kek pontok a normalis adatokat, a piros pontok az outliereket jelolik. Az anomalia detektio hasonlo vizualis mintazatokat keres automatizaltan.*

### Anomalia (Anomaly)

Az **anomalia** egy abnormalis, kontextusfuggo szokatlan viselkedes vagy aktivitas a rendszerben. Nem feltetlenul egyetlen szamertekrol van szo, hanem a rendszer allapotarol.

**Pelda**: Egy bankszamlaron ejszaka 3-kor, kulfoldi IP-cimrol torteno nagy osszegu utalas -- a tranzakcio onmagaban normalis lehetne, de a korulmenyek szokatlanok.

```
Normalis minta:     [havi 2-3 utalas, atlag 50.000 Ft, munkaido]
Anomalia:           [ejjel 3:00, 5.000.000 Ft, uj eszkoz, kulfold]
                    --> kontextusfuggo, a rendszer viselkedes szintjen szokatlan
```

### Outlier (Kiugro Ertek)

Az **outlier** egy statisztikai kiugro ertek az adatban. Az adat eloszlasabol killo egyedi megfigyeles, amely nem feltetlenul gyanus vagy hibas.

**Pelda**: Egy jövedelemfelmeresben egy szemely havi 50 millio Ft jovedelemet jelent -- statisztikailag kiugro, de valoban letezhet.

```
Adat:               [200k, 250k, 300k, 280k, 350k, 50.000k]
                                                    ^^^^^^^
                    --> statisztikai kiugro, de nem feltetlenul hiba
```

### Data Drift (Adatvaltozas)

A **data drift** az adat eloszlasanak valtozasat jelenti idovel. Amikor egy modellt betanitunk egy bizonyos adateloszlasra, de a produktiv kornyezetben az adatok fokozatosan megvaltoznak, a modell teljesitmenye romlik.

**Pelda**: Egy online bolt vasarloi viselkedese a COVID elott es utan eltero -- a modellt ujra kell tanitani.

```
Betanitas (2019):   atlag rendelesi ertek = 15.000 Ft
Produkcios (2021):  atlag rendelesi ertek = 35.000 Ft
                    --> az eloszlas megvaltozott, a modell "nem erti" az uj adatokat
```

### Osszehasonlitas

| Tulajdonsag | Anomalia | Outlier | Data Drift |
|-------------|----------|---------|------------|
| **Szint** | Rendszer/viselkedes | Egyedi adatpont | Adateloszlas |
| **Kontextusfuggo?** | Igen, erosen | Nem feltetlenul | Ido-fuggo |
| **Mindig hiba?** | Nem (de gyanus) | Nem (lehet valos) | Nem (termeszetes valtozas) |
| **Mikor fontos?** | Real-time monitoring | Adat tisztitas | Modell karbantartas |
| **Tipikus megoldas** | Anomalia detektio | Statisztikai szures | Monitoring + ujratanitas |

---

## Alkalmazasi Teruletek

### Penzugyi Csalas Detektio

A penzugyi szektorban az anomalia detektio a tranzakciok valoszinusegenek ertekeleset jelenti. A normalis tranzakcios mintabol killo esemenyek (szokatlan osszeg, helyszin, idopont) automatikusan megjelolhetok.

- **Hitelkartyacsalas**: szokatlan vasarlasi minta felismerese (szokatlan osszeg, helyszin, idopont)
- **Penzmogas**: nagy osszegu, bonyolult tranzakciolancolatok, strukturalt tranzakciok
- **Biztositasi csalas**: rendellenes karesemenyek, tulzott gyakorisag
- **Szamlanyitas**: tobbszoros szamlanyitas gyanus mintazattal (azonos IP, hasonlo adatok)

> **Kulcsfontossagu**: A penzugyi csalas detektioban a **precision** (pontossag) kritikus -- egy hamis riasztas felretajekoztatja a vizsgalot es eroszt az elem bizalmat. Ezert a konzervativ threshold (pl. 1% kvantilis) es a consensus megkozelites (GMM + IF egyuttes jelzese) elonyos.

### Halozati Biztonsag

A **network intrusion detection** a halozati forgalom mintazatait elemzi, es az elterest jelzi:

- Szokatlanul nagy adatforgalom egy adott porton vagy protokollon
- Ismeretlen portokra torteno kapcsolodas vagy port scanning mintak
- Brute-force tamadasi mintak (sok sikertelen bejelentkezesi kiserlet)
- DDoS tamadas jelei (rendkivuli forgalomnovekedés rovid ido alatt)

### Egeszsegugy

Az egeszsegugyi alkalmazasok betegadatok mintazatainak monitoringjan alapulnak:

- Laborertekek rendellenessegei (pl. verertekek hirtelen valtozasa)
- Gyogyszerinterakciok felismerese (veszely kombinaciok automatikus szurese)
- Ritka betegsegek szurese populacios adatokbol
- Orvosi muszerek szenzor-adatainak monitoringja (pl. EKG anomaliak)

### Ipari Gepi Karbantartas

A **predictive maintenance** a szenzoradatok anomaliaira reagal a gephiba bekovetkezese elott:

- Szokatlan rezgesminta (motor, csapagy, kompresszor)
- Homerseklet-csucsok (tulhevules az elott, hogy meghibasodik)
- Energiafogyasztas elterese (a normal uzemi szinttol valo elmozdulas)
- Nyomas- es aramlasi ertekek rendellenessegei csovezetekrendszerekben

> **Ipari peldak**: A General Electric es a Siemens turbina-monitoringot hasznalnak, ahol a szenzoradatok anomaliai napokkal vagy hetekkel a meghibasodas elott figyelmezteto jelzest adnak. Ez a **predictive maintenance** megkozelites jelentos koltsegmegtakaritast jelent a **reactive maintenance** (meghibasodas utani javitas) modszerhez kepest.

---

## Felugyeletlen Modszerek (Unsupervised Anomaly Detection)

A felugyeletlen anomalia detektio elonye, hogy **nem igenyel cimkezett adatot** -- nem kell elozetesen tudnunk, melyek az anomaliak. Ez kulonosen fontos, mert a valos adathalmazokban az anomaliak tipikusan az adatpontok 1-5%-at teszik ki, es nehezen cimkezheto oket.

### GMM (Gaussian Mixture Model) Anomalia Detektio

A **Gaussian Mixture Model** az adatokat tobb (K db) Gauss-eloszlas keverekekent modellezi. Minden adatpont egyes Gauss-komponensekhez valo tartozasi valoszinuseget kap (**soft assignment**).

#### Az EM Algoritmus

A GMM illesztese az **Expectation-Maximization (EM)** iterativ algoritmussal tortenik:

1. **Inicializalas**: Kiindulo parameterek (atlagok, kovarianciamtrixok, sulyok) beallitasa
2. **E-lepes (Expectation)**: Kiszamitja minden adatpont valoszinusegi hozzarendeleset az egyes komponensekhez
3. **M-lepes (Maximization)**: Frissiti a parametereket (atlagok, kovarianciamtrixok, sulyok) a hozzarendelesek alapjan
4. **Iteracio**: Az E es M lepeseket ismetli konvergenciaig

#### score_samples es Threshold Valasztas

Az anomalia detektiohoz a GMM `score_samples()` metodusat hasznaljuk, amely **log-valoszinusegi erteket** (log-likelihood) ad minden adatpontra. Az alacsony skor azt jelenti, hogy az adott pont a modell szerint "valoszinuetlen" -- tehat potencialis anomalia.

A **threshold** (kuszobertek) megvalasztasa donti el, mi szamit anomalianak:

```python
from sklearn.mixture import GaussianMixture
import numpy as np

# GMM illesztes 5 Gauss-komponenssel
gm = GaussianMixture(n_components=5, random_state=42)
components = gm.fit_predict(scaled_data)

# Log-valoszinusegi skorok szamitasa
scores = gm.score_samples(scaled_data)

# Threshold: az 5%-os kvantilis alatti pontok anomaliak
threshold = np.quantile(scores, 0.05)

# Cimkezesek: -1 = anomalia, 1 = normalis
gm_result = [-1 if val <= threshold else 1 for val in scores]

print(f"Anomaliak szama: {gm_result.count(-1)}")
print(f"Normalis pontok: {gm_result.count(1)}")
```

#### Threshold valasztas strategiak

| Strategia | Kvantilis | Feltetelezett anomalia arany | Mikor hasznald |
|-----------|-----------|------------------------------|----------------|
| Konzervativ | 1% | Nagyon keves anomalia | Magas pontossag kell |
| Kiegyensulyozott | 5% | Mersekelt arany | Altalanos hasznalat |
| Szeles | 10% | Tobb anomalia | Recall fontosabb |

> **Fontos**: A kvantilis erteket a domen ismerete alapjan kell megvalasztani. Penzugyi csalasnal tipikusan 1-2%, ipari karbantartasnal 5-10% lehet realis.

#### A GMM mint Anomalia Detektor -- Elonyok es Hatranyok

| Elony | Hatrany |
|-------|---------|
| Valoszinusegi framework: szkort ad, nem csak cimket | Az `n_components` valasztasa nem trivialis |
| Soft assignment: arnyalt eredmenyt ad | Gomb alaku klasztereket feltetelezett (kovarianciamtrixtol fugg) |
| Jol ertelmheto log-likelihood skor | Magas dimenzioban lassulhat |
| Kvantilis alapu threshold rugalmasan allithato | Kis mintanal instabil lehet |

### Isolation Forest

Az **Isolation Forest** egy faalapot anomalia-detektalo algoritmus, amely az **izolacio elvere** epul: az anomaliakat konnyebb izolalni, mint a normalis pontokat.

#### Mukodesi Elv

1. **Random fa epitese**: Veletlenszeruen valaszt egy feature-t, majd egy random vagasi pontot
2. **Rekurziv particiolas**: Az adathalmazt ismetlodoen kette osztja
3. **Izolacio**: Az anomaliak kevesebb vagassal (rovid agon) izoalhatoak, mert a tobbi ponttol tavol esnek
4. **Erdos megkozelites**: Tobb fat epit (ensemble), az anomalia skor az atlagos ut hosszabol szarmazik

```
Normalis pont:      Sok vagas kell az izolaciojához (hosszu ut)
Anomalia:           Keves vagas kell (rovid ut)

          [Root]
         /      \
       [.]      [Anomalia!]     <-- 1 vagas utan mar izolalt
      /   \
    [.]   [.]
   /  \
  [N] [N]                       <-- 4 vagas utan izolalt
```

#### Contamination Parameter

A `contamination` parameter az adathalmaz feltetelezett anomalia-aranyat hatarozza meg:

```python
from sklearn.ensemble import IsolationForest

# contamination=0.02: az adatok 2%-at tekintjuk anomalianak
iso_forest = IsolationForest(contamination=0.02, random_state=42)
anomalies = iso_forest.fit_predict(scaled_data)

# Eredmeny: 1 = normalis, -1 = anomalia
anomalia_szam = (anomalies == -1).sum()
print(f"Anomaliak szama: {anomalia_szam}")
print(f"Anomalia arany: {anomalia_szam / len(anomalies):.2%}")
```

#### Isolation Forest Parameterei

| Parameter | Jelentes | Tipikus ertek |
|-----------|---------|---------------|
| `n_estimators` | Fak szama az erdoben | 100 (alapertelmezett) |
| `contamination` | Feltetelezett anomalia arany | 0.01 - 0.10 |
| `max_samples` | Mintapontok szama fakent | "auto" vagy egesz szam |
| `random_state` | Reprodukalhatosag | 42 |
| `max_features` | Feature-ok szama fakent | 1.0 (az osszes) |

#### Isolation Forest -- Elonyok es Hatranyok

| Elony | Hatrany |
|-------|---------|
| Gyors betanitas es prediktalas | A contamination erteket elozetesen meg kell becsulni |
| Jo skalazhatosag nagy adathalmazokra | Nem ad valoszinusegi erteket (csak anomalia szkort) |
| Nem feltetelezi az adat eloszlasat | Nem jol kezeli a lokalis anomaliakat surun adat kozott |
| Kepes magas dimenzioban is mukodni | Az eredmeny fugg a random seed-tol |

### GMM es Isolation Forest Eredmenyeinek Osszehasonlitasa

A gyakorlatban erdemes **tobb modszert is futtatni** es az eredmenyeket osszehasonlitani. Ha mindket modszer anomaliakent jeloil meg egy pontot, az sokkal erosebb jelzes:

```python
import pandas as pd

# Eredmenyek osszegzese
df = pd.DataFrame({
    'Labels_GMM': gm_result,
    'Labels_IF': anomalies
})

# Mindketto altal anomaliakent jelolt pontok
both_minus_one = len(df[(df['Labels_GMM'] == -1) & (df['Labels_IF'] == -1)])
print(f"Mindketto anomalianak jelolte: {both_minus_one}")

# Csak GMM
only_gmm = len(df[(df['Labels_GMM'] == -1) & (df['Labels_IF'] == 1)])
print(f"Csak GMM anomalia: {only_gmm}")

# Csak IF
only_if = len(df[(df['Labels_GMM'] == 1) & (df['Labels_IF'] == -1)])
print(f"Csak IF anomalia: {only_if}")
```

**Ertelmezesi szabaly**:
- **Mindketto -1**: Erosen valoszinu anomalia --> azonnal vizsgalni
- **Csak az egyik -1**: Gyanus, de nem bizonytott --> szakertoi felulvizsgalat
- **Mindketto 1**: Normalis pont

---

## Self-Supervised Learning Megkozelites

A **self-supervised learning** (onfelugyelt tanulas) egy kreativ megkozelites az anomalia detektiohoz, ahol a modell sajat maga generalja a tanulasi jelat, cimkezett adat nelkul.

### Az Alapotlet

Az elv a kovetkezo: ha egy feature-t kiveszunk es a tobbi feature-bol megprobaljuk prediktalni, akkor a normalis adatpontokon a predikcios hiba kicsi lesz, mig az anomaliakon nagy.

```
Normalis adatpont:  A feature-ok koherensek, jol prediktalhatok egymasbol
Anomalia:           A feature-ok szokatlan kombinacioja, nagy predikcios hiba
```

![Z-score keplet es normalis eloszlas gorbe](_kepek_cleaned/04_data_preparation/slide_08.png)

*2. abra: A Z-score keplete es a normalis eloszlas gorbeje -- az anomalia detektioban a Z-score > 3 erteku adatpontokat tekintjuk anomalianak (99.7%-os szabaly).*

![Z-score outlier zonak: Not unusual, Moderately unusual, Outliers](_kepek_cleaned/04_data_preparation/slide_09.png)

*3. abra: Z-score alapu zonak -- az adatpontok a standard deviacio alapjan kategorizalhatok: normalis (|z| < 2), mersekelten szokatlan (2 < |z| < 3), es outlier/anomalia (|z| > 3).*

### Implementacio: Random Forest Regressor + Z-score

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from scipy.stats import zscore
import numpy as np

# 1. Egy feature-t target-kent kezelunk
target_column = "CASH_ADVANCE"
features = scaled_data.drop(target_column, axis=1)

# 2. Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    features, scaled_data[target_column],
    test_size=0.2, random_state=42
)

# 3. Regresszios modell betanitasa
regressor = RandomForestRegressor(random_state=42)
regressor.fit(X_train, y_train)

# 4. Predikcio es residualok szamitasa
predictions = regressor.predict(X_test)
residuals = y_test - predictions

# 5. Z-score szamitas a residualokra
z_scores = zscore(residuals)

# 6. Threshold alkalmazas (|z| > 3 --> 99.7% szabaly)
threshold = 3
anomalies = np.where(np.abs(z_scores) > threshold)
anomaly_data = X_test.iloc[anomalies]

print(f"Osszes teszt pont: {len(X_test)}")
print(f"Anomaliak (|z| > {threshold}): {len(anomaly_data)}")
print(f"Anomalia arany: {len(anomaly_data) / len(X_test):.2%}")
```

### A Z-score Alapu Threshold Ertelmezese

A **Z-score** megmutatja, hany szorasnyira ter el egy residual az atlagtol:

| Z-score tartomany | Valoszinuseg | Jelentes |
|-------------------|-------------|---------|
| |z| < 1 | ~68% | Normalis |
| 1 < |z| < 2 | ~27% | Enyhen szokatlan |
| 2 < |z| < 3 | ~4.3% | Gyanus |
| |z| > 3 | ~0.3% | Valoszinu anomalia |

> **Fontos**: A Z-score normalis eloszlast feltetelezett. Ha a residualok eloszlasa erosen ferde, erdemes robusztusabb modszert hasznalni (pl. MAD -- Median Absolute Deviation).

### Target Feature Valasztas

A self-supervised megkozelitesnel kulcsfontossagu, hogy **melyik feature-t valasztjuk target-nek**:

- Valasszuk azt a feature-t, amely a domain szempontjabol **legreleansabb** az anomaliara nezve
- Probaljunk meg **tobb target feature-t** is, es nezzuk meg, hogy konzisztens-e az eredmeny
- A target feature idealis esetben **jo korrelacioval** rendelkezik a tobbi feature-rel (kulonben a predikcios hiba mindig nagy lesz)

---

## Semi-Supervised Bridge (Felugyelet Hid)

A **semi-supervised bridge** egy strategia, amely athidalja a felugyeletlen es a felugyelt tanulas kozti rest. Az otlet a kovetkezo:

### A Folyamat

```
1. FELUGYELETLEN FAZIS
   ├── GMM + Isolation Forest futtatasa
   ├── Anomalia-jeloltek azonositasa
   └── Eredmenyek exportalasa

2. SZAKERTOI CIMKEZES
   ├── Domen szakerto megvizsgalja a jelolteket
   ├── Valos anomaliakat megerositi
   ├── Hamis riasztasokat elutasitja
   └── Cimkezett adathalmaz letrehozasa

3. FELUGYELT FAZIS
   ├── Cimkezett adaton klasszifikacio (pl. XGBoost, Random Forest)
   ├── Cross-validation
   ├── Precision/Recall optimalizalas
   └── Produkcios modell deploy
```

### Miert Jo Ez a Megkozelites?

| Elony | Magyarazat |
|-------|-----------|
| Nincs szukseg teljes cimkezesre | Csak a gyanusakat kell megvizsgalni |
| Domaintudas beepitese | A szakerto szuri a hamis riasztasokat |
| Fokozatos javitas | A felugyelt modell egyre pontosabb |
| Skalazhatosag | A felugyeletlen resz nagy adatra is fut |

### Gyakorlati Megvalositas

```python
import pandas as pd

# 1. Felugyeletlen eredmenyek osszegyujtese
candidates = pd.DataFrame({
    'GMM_label': gm_result,
    'IF_label': anomalies,
    'GMM_score': scores
})

# 2. Magas konfidenciau jeloltek kivalasztasa
# Mindketto anomalianak jelolte --> szakerto ele kerul
high_confidence = candidates[
    (candidates['GMM_label'] == -1) &
    (candidates['IF_label'] == -1)
]

# 3. Exportalas szakertoi felulvizsgalatra
high_confidence.to_csv("anomalia_jeloltek_review.csv", index=True)
print(f"Szakertoi felulvizsgalatra varok: {len(high_confidence)} pont")

# 4. A szakerto cimkezi: True/False anomalia
# ... manualisan ...

# 5. Cimkezett adattal felugyelt modell epitese
# from sklearn.ensemble import GradientBoostingClassifier
# clf = GradientBoostingClassifier()
# clf.fit(X_labeled, y_expert_labels)
```

---

## Osszehasonlito Tablazat

| Jellemzo | GMM | Isolation Forest | Self-Supervised | Semi-Supervised Bridge |
|----------|-----|-----------------|----------------|----------------------|
| **Tipus** | Valoszinusegi | Faalapot | Regresszio + Z-score | Felugyeletlen --> felugyelt |
| **Cimke szukseges?** | Nem | Nem | Nem | Reszben (szakerto) |
| **Kimenet** | Log-likelihood skor | Anomalia skor (-1/1) | Residual Z-score | Klasszifikacios cimke |
| **Threshold** | Kvantilis (pl. 5%) | Contamination (pl. 2%) | Z-score (pl. 3) | Klasszifikacios hatar |
| **Eloszlas feltetelzes** | Gauss keverek | Nincs | Normalis residualok | Fugg a clf. modelltol |
| **Ertelmezhetoseg** | Jo (valoszinuseg) | Mersekelt | Jo (residual + Z) | Jo (feature importance) |
| **Skalazhatosag** | Jo | Kiválo | Korrekt | Jo |
| **Felhasznalasi terv** | Altalanos anomalia skor | Gyors felugyeletlen detektio | Feature koherencia | Produkcios rendszer |

---

## Gyakorlati Utmutato

### Anomalia Detekcios Workflow

```
1. ADATELOESZITES
   ├── Hianyzo ertekek potlasa (SimpleImputer, median)
   ├── Log-transzformacio (log1p) a ferde eloszlasokra
   ├── Skalazas (MinMaxScaler)
   └── (Opcionalis) Dimenziocsokkenttes (PCA, t-SNE vizualizaciohoz)

2. FELUGYELETLEN ANOMALIA DETEKTIO
   ├── GMM illesztes
   │   ├── n_components valasztas (BIC/AIC vagy domentuds)
   │   ├── score_samples() -- log-likelihood szkrok
   │   └── Kvantilis-alapu threshold (pl. 5%)
   ├── Isolation Forest
   │   ├── contamination parameter beallitasa
   │   └── fit_predict() -- anomalia cimkek
   └── Eredmenyek osszehasonlitasa (mindketto -1 = eros jelzes)

3. SELF-SUPERVISED VALIDACIO (opcionalis)
   ├── Target feature kivalasztasa
   ├── Regresszios modell (RandomForestRegressor)
   ├── Residualok szamitasa
   ├── Z-score + threshold (|z| > 3)
   └── Konzisztencia-ellenorzes a felugyeletlen eredmenyekkel

4. SZAKERTOI FELULVIZSGALAT (semi-supervised bridge)
   ├── Magas konfidenciau jeloltek exportalasa
   ├── Domen szakerto cimkezese
   └── Hamis riasztasok kiszurese

5. (OPCIONALIS) FELUGYELT MODELL
   ├── Cimkezett adaton klasszifikacio
   ├── Cross-validation + metrikak
   └── Produkcios deploy
```

### Kod peldak

Teljes anomalia detekcios pipeline: lasd `_kod_peldak/anomalia_detektio.py`

#### Gyors GMM + Isolation Forest Osszehasonlitas

```python
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from sklearn.impute import SimpleImputer

# --- 1. Adateloeszites ---
data = pd.read_csv("CC GENERAL.csv")
data.set_index('CUST_ID', inplace=True)
data = pd.DataFrame(
    SimpleImputer(strategy='median').fit_transform(data),
    columns=data.columns
)
data = pd.DataFrame(np.log1p(data))
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

# --- 2. GMM ---
gm = GaussianMixture(n_components=5, random_state=42)
gm.fit(scaled_data)
scores = gm.score_samples(scaled_data)
threshold = np.quantile(scores, 0.05)
gm_result = [-1 if val <= threshold else 1 for val in scores]

# --- 3. Isolation Forest ---
iso_forest = IsolationForest(contamination=0.02, random_state=42)
if_result = iso_forest.fit_predict(scaled_data)

# --- 4. Osszehasonlitas ---
df_result = pd.DataFrame({'GMM': gm_result, 'IF': if_result})
both = len(df_result[(df_result['GMM'] == -1) & (df_result['IF'] == -1)])
only_gmm = len(df_result[(df_result['GMM'] == -1) & (df_result['IF'] == 1)])
only_if = len(df_result[(df_result['GMM'] == 1) & (df_result['IF'] == -1)])
print(f"Mindketto anomalia: {both}")
print(f"Csak GMM anomalia:  {only_gmm}")
print(f"Csak IF anomalia:   {only_if}")
```

#### Self-Supervised Anomalia Detektio

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from scipy.stats import zscore
import numpy as np

# Target feature kivalasztasa
target_column = "CASH_ADVANCE"
features = scaled_data.drop(target_column, axis=1)

# Modell tanitas
X_train, X_test, y_train, y_test = train_test_split(
    features, scaled_data[target_column],
    test_size=0.2, random_state=42
)
regressor = RandomForestRegressor(random_state=42)
regressor.fit(X_train, y_train)

# Anomaliak azonositasa Z-score alapjan
predictions = regressor.predict(X_test)
residuals = y_test - predictions
z_scores = zscore(residuals)
anomaly_mask = np.abs(z_scores) > 3
print(f"Anomaliak: {anomaly_mask.sum()} / {len(X_test)}")
```

---

## Gyakori Hibak es Tippek

### Hibak

1. **Rossz contamination ertek**: Az Isolation Forest `contamination` parameterenek tul magas erteke sok hamis riasztast eredmenyez, tul alacsony erteke pedig kihagy valos anomaliakat. Mindig a domen ismereten alapuljon a beallitas.

2. **Skalazas elmulasztasa**: A GMM es az Isolation Forest is erzekeny a feature-ok skalajara. MinMaxScaler vagy StandardScaler nelkul a nagy mertekegysegu feature-ok dominaljak az eredmenyt.

3. **Egyetlen modszerre hagyatkozas**: Ha csak GMM-et vagy csak Isolation Forest-et hasznalunk, az eredmeny nem megbizhato. A ket modszer **kulonbozo elvek** alapjan mukodik, ezert az egyuttesuk erosebb jelzest ad.

4. **Z-score alkalmazasa nem normalis eloszlasra**: A self-supervised megkozelites Z-score thresholdja normalis eloszlast feltetelezett. Erosen ferde residualoknal ez felremutato lehet -- hasznaljunk MAD-ot (Median Absolute Deviation).

5. **A threshold "tunelasa" a vart eredmenyre**: Ha a threshold-ot addig allitgatjuk, amig a "jo" eredmenyt kapjuk, az overfitting -- a threshold-ot domen tudas vagy cross-validation alapjan kell megvalasztani.

6. **Dimenzioatkok figyelmen kivul hagyasa**: Magas dimenzioban az euklideszi tavolsagok kiegyenlitodnek, ami a GMM es az IF ertekeit is torzitja. Erdemes PCA-val cskkenteni a dimenzioszamot.

### Tippek

1. **Tobb modszer kombinalasa**: Futtass GMM-et es Isolation Forest-et parhuzamosan. Ha mindketto anomaliakent jelol egy pontot, az eros jelzes.

2. **Vizualizalas t-SNE-vel**: A 2D t-SNE projekcion szemrevételezhetoek az anomaliak. Jelold szinnel a kulonbozo modszerek eredmenyeit.

3. **Kvantilis kiserletezés**: Probálj meg tobb kvantilis erteket (1%, 5%, 10%) es vizsgald meg, hogyan valtozik az anomalia szam es minoseg.

4. **Semi-supervised bridge alkalmazasa**: Ha van lehetoseged domen szakertot bevonni, az anomalia-jeloltek cimkezese dontoen javitja a modell minoseg hosszu tavon.

5. **Self-supervised: tobb target feature**: Ne csak egy feature-rel probalkozz. Futtasd tobb target feature-re es nézd meg, konzisztensek-e az eredmenyek.

6. **Idosoros adatnal**: Ha az adatban idosoros jelleg van, erdemes az anomalia detektiot idoablakokra bontani, es a **data drift** jelenseget kulon monitorizalni.

7. **Produkcios monitoring**: Az anomalia detektios rendszert produkcios kornyezetben folyamatosan kell monitorizalni, mert a data drift miatt a thresholdok elregedhetnek.

---

## Kapcsolodo Temak

- [09_klaszterezes.md](09_klaszterezes.md) -- A **GMM** klaszterezesi alkalmazasa (soft clustering), amely itt anomalia detektorra modosul a `score_samples` es kvantilis threshold hasznalataval
- [04_adatelokeszites_es_feature_engineering.md](04_adatelokeszites_es_feature_engineering.md) -- **Outlier** kezeles hagyomanyos statisztikai modszerekkel (IQR, Z-score), amelyek az anomalia detektio elokeszito lepeset jelentik
- [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- A **semi-supervised bridge** felugyelt fazisahoz szukseges klasszifikacios modszerek (Random Forest, XGBoost)
- [08_dimenziocsokkentes.md](08_dimenziocsokkentes.md) -- **PCA** es **t-SNE** az anomalia detektio elokeszitesehez es vizualizalasahoz

---

## Tovabbi Forrasok

- **scikit-learn dokumentacio -- Novelty and Outlier Detection**: https://scikit-learn.org/stable/modules/outlier_detection.html
- **Isolation Forest eredeti cikk (Liu et al., 2008)**: https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf
- **Gaussian Mixture Model (sklearn)**: https://scikit-learn.org/stable/modules/mixture.html
- **Self-supervised anomaly detection overview**: https://arxiv.org/abs/2007.02500
- **PyOD -- Python Outlier Detection konyvtar**: https://pyod.readthedocs.io/
- **Credit Card Dataset (Kaggle)**: https://www.kaggle.com/datasets/arjunbhasin2013/ccdata
- **Anomaly Detection Tutorial (Google)**: https://developers.google.com/machine-learning/problem-framing/anomaly-detection
