> Vizualis verzio - kepekkel kiegeszitve | Eredeti: [04_adatelokeszites_es_feature_engineering.md](04_adatelokeszites_es_feature_engineering.md)

> Utolso frissites: 2026-03-09 | Forrasok: 6 transzkript + 1 PDF prezentacio

# Adatelokeszites es Feature Engineering

## Gyors Attekintes

> Az adatelokeszites a gepi tanulasi folyamat legidoigenesebb es egyben legfontosabb fazisa: az adatok
> importalasatol a hianyzó ertekek es outlierek kezelesen at a feature-ok letrehozasaig, enkodolasaig es
> skalazasaig terjed. A jol eloekszitett adatok kozvetlenul javitjak a modell pontossagat, tanulasi
> sebesseget es altalanositokepesseget. Ez a fejezet vegigvezet az osszes lenyeges lepesen, konkret
> sklearn kodpeldakkal.

---

## Kulcsfogalmak

| Fogalom | Rovid definicio |
|---|---|
| **Adatelokeszites (Data Preprocessing)** | Az adatok tisztitasa, atalakitasa es elokeszitese elemzesre vagy modell betanitasra |
| **Feature Engineering** | Uj jellemzok (feature-ok) letrehozasa, kivalasztasa es atalakitasa a modell szamara |
| **Imputalas** | Hianyzó adatok helyettesitese becsult vagy statisztikai ertekekkel |
| **Outlier** | Kiugro adatpont, amely jelentosen elter a tobbi adat ertektartomanyatol |
| **Encoding** | Kategorikus valtozok numerikus formara alakitasa |
| **Skalazas** | Az adatok atmeretezese egysemes tartomanyba a modell jobb teljesitmenyeert |
| **MCAR / MAR / MNAR** | A hianyzó adatok harom fo tipusa (teljesen veletlen / feltetelesen veletlen / nem veletlen) |
| **Pipeline** | Eloefeldolgozasi es modellezesi lepesek lancolt, reprodukalhato vegrehajtasa |

---

## Az Adatelokeszites Lepesei (attekintes)

### Az adatelokeszites helye a Data Science folyamatban

Az adatelokeszites (Data Preparation) a teljes Data Science / ML Engineering munkafolyamat **kozponti fazisa**.
A tipikus pipeline a kovetkezo nagyobb lepesekbol all:

```
Uzleti problema definialasa
    --> Adatgyujtes (Data Collection)
        --> Adattisztitas (Data Cleansing / Cleaning)
            --> Adatelokeszites (Data Preparation)
                --> Feature Engineering
                    --> Modellvalasztas es tanitas
                        --> Modell ertekeles
                            --> Uzembe helyezes (Deployment)
```

![A Data Science folyamat lepeseit bemutato diagram](_kepek_cleaned/04_data_preparation/slide_02.png)
*1. abra: A teljes Data Science munkafolyamat fazisai -- az uzleti problema megertésetol a deploymentig, visszacsatolasi hurkokkal. Az adatelokeszites es modellezesi lepesek kek szinnel, a projekt-definialas zolddel kiemelt.*

> **Forras:** A fenti pipeline a prezentacio (Gerzson Boros: "Data Preparation") altal hivatkozott
> Data Science Process modellen alapul.

Az adattisztitas es az adatelokeszites kozott szoros kapcsolat van: a **cleaning** az adatok hibainak
javitasat, a duplikaciok es inkonzisztenciak eltavolitasat jelenti, mig a **preparation** az adatok
atalakitasat, gazdagitasat es modellre kesziteset foglalja magaban. A gyakorlatban ez a ket lepes
gyakran egymasba fonodik.

![Az adatelokeszites fo fazisai ikonokkal](_kepek_cleaned/04_data_preparation/slide_03.png)
*2. abra: Az adatelokeszites hat fo fazisa: adatgyujtes (Gather), feltaras (Discover), tisztitas (Cleanse), transzformacio (Transform), gazdagitas (Enrich) es tarolas (Store).*

Az adatelokeszites **iterativ folyamat** -- az adat megertes (EDA) es az elokeszites gyakran tobb ciklusban
koveti egymast. A fo lepesek:

1. **Adatok importalasa** -- CSV, adatbazis, API stb.
2. **Adatok egyesitese (merge)** -- osszetartozo adatforrasok osszefuzese egy DataFrame-be
3. **Hianyzó ertekek kezelese** -- eltavolitas vagy potlas (imputalas)
4. **Adatvalidacio es verifikacio** -- minoseg ellenorzes, uzleti szabalyoknak megfeleles
5. **Duplikaciok eltavolitasa** -- ismetlodo sorok kiszurese
6. **Outlierek kezelese** -- kiugro ertekek detektalasa es kezelese
7. **Feature Engineering** -- uj feature-ok letrehozasa, kivalasztasa
8. **Encoding** -- kategorikus valtozok numerikussa alakitasa
9. **Skalazas** -- feature-ok egysemes tartomanyba hozasa
10. **Exportalas** -- eloekszitett adatok mentese

![Az adattisztitasi ciklus kordiagramja](_kepek_cleaned/04_data_preparation/slide_04.png)
*3. abra: A Data Cleansing Cycle -- az adattisztitas kokorosen ismetlodo lepeseit mutatja: hianyzó adatok ujraepitese, validacio, duplikaciok eltavolitasa, standardizalas/normalizalas, import/export es osszefuzes.*

> **Fontos:** Az adatelokeszites nemcsak a modellezes elott tortenik -- mar az adatgyujtes, az EDA es a
> tarolas soran is lehetnek elofeldolgozasi lepesek.

---

## Hianyzó Ertekek Kezelese

### A hianyzó adatok tipusai

| Tipus | Angol nev | Jellemzo | Pelda |
|---|---|---|---|
| **Teljesen veletlen** | MCAR (Missing Completely At Random) | Semmilyen valtozotol nem fugg | Szenzor veletlen kiesese |
| **Feltetelesen veletlen** | MAR (Missing At Random) | A megfigyelt valtozokkal osszefugg, de az ertekkel nem | Idosek kevesbe toltik ki az edzesre vonatkozo kerdest |
| **Nem veletlen** | MNAR (Missing Not At Random) | Az ertek maga befolyasolja a hianyzast | Magasabb jovedelmuek nem adjak meg a fizetessuket |

> **Bovebb ertelmezes (a prezentacio alapjan):**
>
> - **MCAR:** A hianyzas teljesen veletlen, semmilyen megfigyelt vagy nem megfigyelt valtozoval nem fugg ossze.
> - **MAR:** A hianyzas valoszinusege fugg egy **megfigyelt** valtozotol, de nem a hianyzó ertektol
>   magától. Peldaul egy egeszsegugyi kerdoivben az idosebbek kevesbe valaszolnak a fizikai
>   aktivitasra vonatkozo kerdesre -- a hianyzas az eletkorral (megfigyelt) fugg ossze, de nem
>   feltetlen a tényleges aktivitassal.
> - **MNAR:** A hianyzas kozvetlenul a **hianyzó ertek magaval** fugg ossze. Peldaul a magas
>   jovedelmuek kevesbe hajlandoak megadni a jovedelmemsuket -- a hianyzas a valos jovedelem ertektol fugg.

### Detektalas (isnull, missingno)

```python
import pandas as pd
import missingno as msno
import matplotlib.pyplot as plt

df = pd.read_csv("adatok.csv")

# Hianyzó ertekek szama oszloponkent
print(df.isnull().sum())

# Hianyzó ertekek aranya szazalekban
print((df.isnull().sum() / len(df) * 100).round(2))

# Vizualis megjelenites missingno-val
msno.matrix(df, figsize=(12, 6))
plt.title("Hianyzó ertekek matrixa")
plt.show()

# Hianyzó ertekek korrelaccios heatmap-je
msno.heatmap(df, figsize=(10, 6))
plt.show()
```

### Dontesi folyamat a hianyzó ertekek kezelesehez

A hianyzó ertekek kezelesere a kovetkezo dontesi logika javasolt (a prezentacio flowchart-ja alapjan):

```
Hianyzó ertek detektalva
    |
    +--> Az oszlop > 80%-a hianyzik?
    |       IGEN --> Oszlop torlese
    |       NEM  |
    |            +--> Csak kevés sor erintett (< 1-2%)?
    |            |       IGEN --> Sorok torlese (dropna)
    |            |       NEM  |
    |            |            +--> Numerikus valtozo?
    |            |            |       IGEN --> Normalis eloszlas? --> mean / median imputalas
    |            |            |               Ferde eloszlas?    --> median imputalas
    |            |            |               Feature-ok kozott osszefugges? --> KNN imputalas
    |            |            |       NEM  |
    |            |            |            +--> Kategorikus valtozo?
    |            |            |                    Keves hianyzó --> modusz (most_frequent)
    |            |            |                    Sok hianyzó   --> kulon "ismeretlen" kategoria
    |            |            +--> Idosoros adat?
    |            |                    IGEN --> interpolacio (linear / time)
```

![A hianyzó ertekek kezelesi strategiainak dontes-faja](_kepek_cleaned/04_data_preparation/slide_06.png)
*4. abra: A hianyzó ertekek kezelesi strategiainak dontes-faja: torles (listwise, pairwise, oszlop) vagy imputalas (idosor-alapu vagy altalanos, folytonos vagy kategorikus valtozokhoz kulonbozo modszerekkel).*

> **Forras:** A flowchart a prezentacio "Handling missing values" diajan alapul
> (hivatkozas: analyticsvidhya.com/blog/2021/10/guide-to-deal-with-missing-values/)

### Strategiak (torles, imputalas)

**1. Torles (dropna)**

Akkor erdemes, ha:
- egy oszlopban szinte minden ertek hianyzik --> teljes oszlop torlese
- nagyon kevés sor erintett (pl. 15 sor 10 000-bol) --> sorok torlese

```python
# Teljes oszlop torlese, ha >80% hianyzik
kuszob = 0.8
df_tisztitott = df.dropna(thresh=int((1 - kuszob) * len(df)), axis=1)

# Sorok torlese, ahol barmelyik ertek hianyzik
df_tisztitott = df.dropna(axis=0, how="any")

# Sorok torlese, ahol egy adott oszlopban hianyzik az ertek
df_tisztitott = df.dropna(subset=["fontos_oszlop"])
```

**2. Statisztikai imputalas (atlag, median, modusz)**

- **Folytonos valtozok:** atlag (mean), median, modusz (mode)
- **Kategorikus valtozok:** modusz, vagy kulon "hianyzó" kategoria

```python
# Egyszeru potlas medianal
df["kor"].fillna(df["kor"].median(), inplace=True)

# Kategorikus: kulon kategoria a hianyzóknak
df["varos"].fillna("ismeretlen", inplace=True)
```

> **Figyelmeztetes kategorikus valtozoknal:** Ha pl. 10 000 "macska" es 10 002 "kutya" van, es 20 000
> sor hianyzik, a modusszal ("kutya") valo potlas sulyosan eltorza az aranyokat. Ilyenkor erdemes
> kulon "hianyzó" kategoriat bevezetni.

### SimpleImputer, KNNImputer

```python
from sklearn.impute import SimpleImputer, KNNImputer

# --- SimpleImputer ---
# Folytonos valtozokhoz: median
imp_median = SimpleImputer(strategy="median")
df[["kor", "jovedelem"]] = imp_median.fit_transform(df[["kor", "jovedelem"]])

# Kategorikus valtozokhoz: leggyakoribb ertek
imp_mode = SimpleImputer(strategy="most_frequent")
df[["varos"]] = imp_mode.fit_transform(df[["varos"]])

# Konstans ertekkel valo potlas
imp_const = SimpleImputer(strategy="constant", fill_value="ismeretlen")
df[["megjegyzes"]] = imp_const.fit_transform(df[["megjegyzes"]])

# --- KNNImputer ---
# A legkozelebbi szomszedok alapjan becsul
knn_imp = KNNImputer(n_neighbors=5, weights="distance")
df_numerikus = pd.DataFrame(
    knn_imp.fit_transform(df.select_dtypes(include="number")),
    columns=df.select_dtypes(include="number").columns
)
```

### Idosoros adatok specialis kezelese

```python
# Linearis interpolacio (trendkoveto adatokhoz)
df["ertek"] = df["ertek"].interpolate(method="linear")

# Ido-alapu interpolacio (nem egyenletes idokozu adatokhoz)
df["ertek"] = df["ertek"].interpolate(method="time")
```

> Ha van **szezonalitas**, eloszor tavolitsd el a trendet es a szezonalitast, imputalj, majd add vissza.

### Mikor melyiket hasznald?

| Helyzet | Javasolt modszer |
|---|---|
| Nagyon kevés hianyzó sor (<1-2%) | `dropna()` torles |
| Oszlop >80%-a hianyzik | Teljes oszlop torlese |
| Folytonos, normalis eloszlas | `SimpleImputer(strategy="mean")` |
| Folytonos, ferde eloszlas / outlierek | `SimpleImputer(strategy="median")` |
| Kategorikus, keves kategoria | `SimpleImputer(strategy="most_frequent")` |
| Kategorikus, sok hianyzó | Kulon "ismeretlen" kategoria |
| Tobb feature kozott osszefugges van | `KNNImputer` |
| Idosoros, trenddel | Linearis interpolacio |
| Idosoros, trend + szezonalitas | Dekompozicio utan interpolacio |

---

## Outlierek Kezelese

### Mi az outlier?

Az outlier olyan adatpont, amely **jelentosen elter** a tobbi adat ertektartomanyatol. Fontos:
az outlier es az **anomalia** nem ugyanaz -- az anomalia-detekcioval kulon tema foglalkozik.

> **Domen tudas szerepe:** Nem minden outliert kell eltavolitani! Bizonyos esetekben az outlier
> fontos informaciot hordoz. A dontes meghozatalához **szakteruleti ismeretre** van szukseg.

![Outlierek vizualizacioja scatter ploton](_kepek_cleaned/04_data_preparation/slide_07.png)
*5. abra: Outlierek detektalasa scatter ploton -- a kek pontok a normalis adatokat, a piros pontok a kiugro ertekeket (outliereket) jelzik, a regresszios egyenes szemlelteti a fo trendet.*

### Z-score modszer

A z-szkor megmutatja, hogy egy adatpont hany szorasnyira van az atlagtol:

**Keplet:** `z = (x - atlag) / szoras`

| z-szkor (abszolut) | p-ertek | Ertekelmes |
|---|---|---|
| > 2.0 | < 0.05 | Valoszinuleg outlier |
| > 2.58 | < 0.01 | Nagyon szignifikans outlier |
| > 3.0 | < 0.003 | Szinte biztosan outlier |

![Z-score keplet es szignifikancia szintek normalis eloszlason](_kepek_cleaned/04_data_preparation/slide_08.png)
*6. abra: A Z-score keplete es a szignifikancia szintek (p-ertekek) vizualizacioja a normalis eloszlas gorbéjen -- a szinezett teruletek a kulonbozo konfidencia szinteket jelzik.*

![Z-score alapu outlier zonak a haranggorbén](_kepek_cleaned/04_data_preparation/slide_09.png)
*7. abra: Outlier detektalas Z-score alapjan: a gorbe kozepen a "Not unusual" zona (|z| < 2), szelen a "Moderately unusual" (|z| 2-3), a szelseken az "Outliers" (|z| > 3).*

```python
import numpy as np
from scipy import stats

# Z-szkor szamitas
z_scores = np.abs(stats.zscore(df["feature_oszlop"]))

# Outlierek szurese (|z| > 3)
outlier_maszk = z_scores > 3
print(f"Outlierek szama: {outlier_maszk.sum()}")

# Outlierek eltavolitasa
df_tiszta = df[z_scores <= 3]
```

### IQR modszer

Az **Interquartile Range (IQR)** az adatok kozepso 50%-anak teredelme. Robusztusabb, mint a z-szkor,
mert nem feltetelezi a normalis eloszlast.

```python
Q1 = df["feature_oszlop"].quantile(0.25)
Q3 = df["feature_oszlop"].quantile(0.75)
IQR = Q3 - Q1

also_hatar = Q1 - 1.5 * IQR
felso_hatar = Q3 + 1.5 * IQR

# Outlierek azonositasa
outlier_maszk = (df["feature_oszlop"] < also_hatar) | (df["feature_oszlop"] > felso_hatar)
print(f"Outlierek szama: {outlier_maszk.sum()}")

# Outlierek eltavolitasa
df_tiszta = df[~outlier_maszk]
```

### Outlier detektalas vizualis es statisztikai eszkozokkel (attekintes)

A prezentacio harom fo megkozelitest emel ki az outlierek detektalasahoz:

| Modszer | Leiras | Vizualis eszkoz |
|---|---|---|
| **Z-score** | Megmutatja, hany szorasnyira van egy pont az atlagtol. \|z\| > 2-3 eseten outlier. | Z-score tablazat, normalis eloszlas gorbe |
| **IQR (Interquartile Range)** | A Q1 - 1.5*IQR es Q3 + 1.5*IQR hataron kivuli pontok outlierek. | Boxplot (az "IQR kerites" vizualisan jeloli az outliereket) |
| **Vizualis modszerek** | Boxplot, scatter plot, histogram vizualis attekintese. | Boxplot + scatter plot |

> **Forras (prezentacio hivatkozasok):**
> - Z-score formula es ertelmezese: z-table.com/z-score-formula.html
> - Z-score es p-ertek kapcsolata: pro.arcgis.com (Spatial Statistics)
> - IQR-alapu outlier szamolo: inchcalculator.com/outlier-calculator/

### Vizualis detektalas (boxplot)

```python
import matplotlib.pyplot as plt
import seaborn as sns

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Boxplot -- az IQR-en kivuli pontok az outlierek
sns.boxplot(data=df, y="feature_oszlop", ax=axes[0])
axes[0].set_title("Boxplot -- outlier detektalas")

# Scatter plot -- vizualis attekintes
axes[1].scatter(range(len(df)), df["feature_oszlop"], alpha=0.5)
axes[1].set_title("Scatter plot")

plt.tight_layout()
plt.show()
```

### Kezelesi strategiak

| Strategia | Mikor hasznald | Kod pelda |
|---|---|---|
| **Eltavolitas** | Ha biztosan hibas adat | `df = df[~outlier_maszk]` |
| **Capping (windsoizing)** | Ha meg akarod tartani a sort, de korlatozni az erteket | `df["x"] = df["x"].clip(also_hatar, felso_hatar)` |
| **Transzformacio** | Ha ferde eloszlasu adat | `df["x_log"] = np.log1p(df["x"])` |
| **Imputalas** | Ha az outliert hianyzó ertekkent kezeled | `df.loc[outlier_maszk, "x"] = np.nan` majd imputalas |
| **Kulon modell** | Ha prediktalini akarod az outlier helyet | ML modell betanitasa a tobbi feature alapjan |
| **Klaszterezes** | Ha csoportos outliereket kell azonositani | Klaszterezesi technikak (pl. DBSCAN) a csoport-outlierek kulon kezelesere |
| **ML-alapu kezeles** | Ha az algoritmus maga kezeli az outliereket | Egyes algoritmusok (pl. Random Forest) robusztusak az outlierekre, kulon beavatkozas nelkul |
| **Domen-alapu manualis kezeles** | Ha szakteruleti ertekelest igenyel | Szakerto donti el, hogy valos anomalia vagy hiba; a kontextus hatarozza meg a kezelest |
| **Megtartas** | Ha a domen tudas szerint fontos | Nem nyulunk hozza |

```python
# Capping pelda (windsorizing)
from scipy.stats import mstats

df["feature_capped"] = mstats.winsorize(df["feature_oszlop"], limits=[0.05, 0.05])

# Log transzformacio ferde eloszlashoz
df["feature_log"] = np.log1p(df["feature_oszlop"])
```

---

## Feature Engineering

A Feature Engineering a Data Scientist egyik legfontosabb feladata. A **feature-ok** az adathalmaz
oszlopai (jellemzoi), amelyeket a modell bemenetkent hasznal.

![A Feature Engineering hat fo teruletenek attekintese](_kepek_cleaned/04_data_preparation/slide_11.png)
*8. abra: A Feature Engineering hat fo teruletenek attekintese hexagon diagramon: Feature Learning, Feature Improvements, Feature Construction, Feature Extraction, Feature Selection es Feature Transformations.*

### A Feature Engineering fo lepsei (reszletes leiras)

A prezentacio (forras: datasciencecentral.com/feature-engineering-at-a-glance/) hat fo lepest kulonboztet meg:

1. **Feature Learning** -- Gepi tanulasi algoritmusok segitsegevel **automatikusan** tanulja meg a
   feature-oket az adatokbol. A modell donti el, melyek a legfontosabb feature-ok. Jellemzoen
   mely tanulasi (deep learning) technikakkal, peldaul konvolucios neuralis halozatokkal (CNN) tortenik.

2. **Feature Improvement** -- A meglevo feature-ok **minosegenek javitasa**, peldaul adatnormalizalassal
   vagy hianyzó ertekek kezeleesvel. A cel, hogy a feature-ok jobban ertelmezhetoek es hasznalhatobbak
   legyenek a modellek szamara.

3. **Feature Construction** -- **Uj feature-ok letrehozasa** meglevo adatokbol. Peldaul mozgoatlag
   szamitasa tozsdeadatokbol, haztartasi osszbevétel szamitasa egyeni fizetesekbol.

4. **Feature Extraction** -- **Lenyeges informaciok kinyerese** meglevo adatokbol, az adatok
   dimenzionalitasanak csokkentesevel. Peldak: TF-IDF letrehozasa szovegbol, idosor dekompozicio,
   PCA (fokomponens-elemzes), word embedding.

5. **Feature Selection** -- A feladathoz **legrelevansabb feature-ok kivalasztasa**. Az irrelevans
   vagy redundans feature-ok eltavolitasaval a modellek hatekonyabba es pontosabba valnak.

6. **Feature Transformation** -- A meglevo feature-ok **matematikai atalakitasa**, peldaul
   label encoding, one-hot encoding.

### Uj feature-ok letrehozasa (Feature Construction)

```python
import pandas as pd

# --- Peldak uj feature-ok letrehozasara ---

# Haztartasi osszbevétel (tobb szemely fizetesenek osszege)
df["haztartas_bevetel"] = df["fizetes_1"] + df["fizetes_2"]

# Arany (ratio) feature
df["szoba_per_terulet"] = df["szobak_szama"] / df["lakas_terulet"]

# Mozgo atlag (tozsde, idosorok)
df["mozgo_atlag_7"] = df["arfolyam"].rolling(window=7).mean()

# Binning -- folytonos valtozo kategorizalasa
df["kor_csoport"] = pd.cut(df["kor"], bins=[0, 18, 35, 55, 100],
                           labels=["gyerek", "fiatal", "kozepkoru", "idos"])
```

### Feature kivalasztas (Feature Selection)

A feature selection celja, hogy **csak a lenyeges** feature-oket tartsuk meg. Elonyei:
- gyorsabb tanulas es predikció
- konnyebb karbantartas
- jobb altalanositokeépesseg (kevesebb overfitting)

```python
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif

X = df.drop("target", axis=1)
y = df["target"]

# --- Univariate Feature Selection ---
selector = SelectKBest(score_func=f_classif, k=10)
X_selected = selector.fit_transform(X, y)

# Kivalasztott feature-ok nevei
kivalasztott = X.columns[selector.get_support()]
print("Kivalasztott feature-ok:", list(kivalasztott))

# --- Feature Importance (fa alapu modellel) ---
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X, y)

# Fontossagi sorrend
importances = pd.Series(rf.feature_importances_, index=X.columns)
print(importances.sort_values(ascending=False).head(10))
```

### Polinomialis feature-ok

```python
from sklearn.preprocessing import PolynomialFeatures

poly = PolynomialFeatures(degree=2, include_bias=False, interaction_only=False)
X_poly = poly.fit_transform(X[["feature_1", "feature_2"]])

# Uj feature nevek
print(poly.get_feature_names_out(["feature_1", "feature_2"]))
# Eredmeny: ['feature_1', 'feature_2', 'feature_1^2', 'feature_1 feature_2', 'feature_2^2']
```

### Interakcios feature-ok

```python
# Csak az interakciokat tartjuk meg (negyzetes tagok nelkul)
poly_inter = PolynomialFeatures(degree=2, include_bias=False, interaction_only=True)
X_inter = poly_inter.fit_transform(X[["feature_1", "feature_2", "feature_3"]])

print(poly_inter.get_feature_names_out(["feature_1", "feature_2", "feature_3"]))
# ['feature_1', 'feature_2', 'feature_3',
#  'feature_1 feature_2', 'feature_1 feature_3', 'feature_2 feature_3']
```

### Datum alapu feature-ok

```python
# Datum oszlopbol uj feature-ok
df["datum"] = pd.to_datetime(df["datum"])

df["ev"] = df["datum"].dt.year
df["honap"] = df["datum"].dt.month
df["het_napja"] = df["datum"].dt.dayofweek       # 0=hetfo, 6=vasarnap
df["hetvege"] = (df["het_napja"] >= 5).astype(int)
df["negyedev"] = df["datum"].dt.quarter
df["ev_napja"] = df["datum"].dt.dayofyear

# Ciklikus kodolas (pl. honapokhoz)
df["honap_sin"] = np.sin(2 * np.pi * df["honap"] / 12)
df["honap_cos"] = np.cos(2 * np.pi * df["honap"] / 12)
```

### Feature Extraction peldak

| Technika | Alkalmazas | sklearn / konyvtar |
|---|---|---|
| **PCA** | Dimenziocsokkentes | `sklearn.decomposition.PCA` |
| **TF-IDF** | Szoveges adatok | `sklearn.feature_extraction.text.TfidfVectorizer` |
| **Word Embedding** | Szemantikus szovegreprezentacio | `gensim`, `transformers` |
| **Idosor dekompozicio** | Szezonalitas es trend szétvalasztas | `statsmodels.tsa.seasonal_decompose` |

```python
from sklearn.decomposition import PCA

pca = PCA(n_components=0.95)  # 95% variancia megtartasa
X_pca = pca.fit_transform(X_scaled)
print(f"Eredeti feature-ok: {X_scaled.shape[1]}, PCA utan: {X_pca.shape[1]}")
```

---

## Encoding (Kategorikus valtozok atalakitasa)

A gepi tanulasi algoritmusok **szamokkal** dolgoznak, ezert a kategorikus valtozokat numerikus
formara kell alakitani.

![Label Encoding, One-Hot Encoding es Dummy Encoding osszehasonlitasa](_kepek_cleaned/04_data_preparation/slide_13.png)
*9. abra: A harom fo encoding technika gyakorlati osszehasonlitasa pelda-tablazatokkal. Balra: Label Encoding (sorszamok hozzarendelese) es One-Hot Encoding (binaris oszlopok). Jobbra: One-Hot Encoding vs. Dummy Encoding kulonbsege -- a Dummy Encoding egy oszloppal kevesebbet hasznal.*

### Label Encoding

Minden kategorihoz egy egyedi **egesz szamot** rendel.

```python
from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()
df["szin_encoded"] = le.fit_transform(df["szin"])

# Visszaalakitas
df["szin_eredeti"] = le.inverse_transform(df["szin_encoded"])
```

> **Figyelmeztetes:** A Label Encoding **hamis sorrendet** sugall az algoritmusnak. Pl. ha
> alma=1, csirke=2, citrom=100, az algoritmus ugy "gondolja", hogy az alma es a csirke hasonloak,
> a citrom pedig nagyon tavolvan. Ezert **csak ordinalis valtozokhoz** hasznald (ahol van termeszetes
> sorrend, pl. kicsi < kozepes < nagy).

### One-Hot Encoding

Minden kategorihoz egy **kulon binaris oszlopot** hoz letre (0 vagy 1).

```python
from sklearn.preprocessing import OneHotEncoder

ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
X_encoded = ohe.fit_transform(df[["szin", "varos"]])

# Feature nevek lekerdezese
print(ohe.get_feature_names_out(["szin", "varos"]))

# Pandas get_dummies alternatíva (dummy encoding, egy oszloppal kevesebb)
df_encoded = pd.get_dummies(df, columns=["szin"], drop_first=True)
```

> A `drop_first=True` a **dummy encoding** variáns: egy oszloppal kevesebbet hoz letre,
> mert az elhagyott kategoria a tobbibol kiolvasható (ha mindenhol 0, akkor az a referencia kategoria).

### Ordinal Encoding

Olyan kategorikus valtozokhoz, ahol **van termeszetes sorrend**.

```python
from sklearn.preprocessing import OrdinalEncoder

oe = OrdinalEncoder(categories=[["kicsi", "kozepes", "nagy"]])
df["meret_encoded"] = oe.fit_transform(df[["meret"]])
# kicsi -> 0, kozepes -> 1, nagy -> 2
```

### Target Encoding

A kategoriat a **celvaltozo atlagaval** helyettesiti az adott kategoriaban.

```python
# Egyszeru target encoding (figyelj a data leakage-re!)
target_means = df.groupby("varos")["ar"].mean()
df["varos_target_enc"] = df["varos"].map(target_means)

# Sklearn TargetEncoder (sklearn >= 1.3, beepitett cross-fitting a leakage ellen)
from sklearn.preprocessing import TargetEncoder

te = TargetEncoder(smooth="auto")
df["varos_target_enc"] = te.fit_transform(df[["varos"]], df["ar"])
```

### Mikor melyiket? (osszehasonlito tablazat)

| Encoding tipus | Mikor hasznald | Elony | Hatrany |
|---|---|---|---|
| **Label Encoding** | Ordinalis valtozok (van sorrend) | Egyszeru, 1 oszlop marad | Hamis tavolsagokat sugall |
| **One-Hot Encoding** | Nominalis valtozok, kevés kategoria | Nem sugall sorrendet | Sok oszlop (magas kardinalitas eseten) |
| **Dummy Encoding** | Mint One-Hot, de linearisan fuggetlen | 1 oszloppal kevesebb | Nehezebb ertelmezni |
| **Ordinal Encoding** | Ordinalis valtozok | Megorzi a sorrendet | Csak ha van valos sorrend |
| **Target Encoding** | Magas kardinalitasu kategoriak | Kevés uj oszlop | Data leakage veszelye |

---

## Skalazas (Feature Scaling)

A skalazas celja, hogy a feature-ok **egyseges tartomanyba** keruljenek, igy egyetlen feature sem
dominalja a tanulasi folyamatot pusztan azert, mert nagyobb ertekei vannak.

![A skalazas vizualis bemutatasa hisztogramokkal](_kepek_cleaned/04_data_preparation/slide_14.png)
*10. abra: A skalazas vizualis bemutatasa: a nyers feature (x) eloszlasa, majd az egyszeru skalazas (x' = x/2) es a skalazas + eltolas (x' = (x-7)/2) hatasa az eloszlasra.*

### A skalazas elonyei (reszletes)

A prezentacio hat fo elonyt emelt ki:

1. **Javitott tanulasi pontossag (Enhanced Learning Accuracy)**
   - A skalazas normalizalja a feature-ok merteket, biztositva, hogy egyetlen feature sem dominalja a tanulasi folyamatot.
   - Megelozi az elfogultsagot a nagyobb skalan mero feature-ok fele, javitva a modell igazsagossagat es pontossagat.

2. **Gyorsabb konvergencia (Faster Convergence)**
   - A skalazott adatok segitik az algoritmusokat, hogy gyorsabban konvergaljanak a megoldashoz.
   - Csokkenti a szamitasi koltsegeket es gyorsitja a tanitasi folyamatot.

3. **Jobb Gradient Descent teljesitmeny (Better Gradient Descent Performance)**
   - Gradiens csokkentesen alapulo algoritmusoknál a skalazas simabb hiba-gradienst biztosit.
   - A megoldashoz vezeto ut simabb es kozvettlenebb, igy az algoritmus gyorsabban es konyebben talalja meg a legjobb megoldast.

4. **Alapveto tavolsag-alapu algoritmusokhoz (Essential for Distance-Based Algorithms)**
   - Az olyan algoritmusok, mint a K-Nearest Neighbors (KNN) es a K-Means, tavolsagszamitasra epitennek.
   - A skalazas biztositja, hogy ezeket a tavolsagokat ne torzitsak el a feature-ok kulonbozo skálai.

5. **Javitott regularizacio (Improved Regularization)**
   - A regularizacios technikak, mint a Lasso es a Ridge, erzekenyeek az adatok skalajara.
   - A skalazas egyenletes buntetés-elosztast biztosit a feature-ok kozott, novelve a regularizacio hatekonysagat.

6. **Kompatibilitas specifikus technikakkal (Compatibility with Particular Techniques)**
   - Szamos gepi tanulasi technika feltetelezi, hogy az adatok centraltak es skalazottak.
   - Biztositja a kompatibilitast es az optimalis teljesitmenyt olyan technikakkal, mint a Principal Component Analysis (PCA).

### Normalizalas vs. Sztenderdizalas -- a ket fo megkozelites

A prezentacio kiemelten foglalkozik a **normalizalas (Normalization)** es a **sztenderdizalas (Standardization)**
kulonbsegevel, mert ez az egyik leggyakoribb felreertés:

| | Normalizalas (MinMaxScaler) | Sztenderdizalas (StandardScaler) |
|---|---|---|
| **Keplet** | `x' = (x - x_min) / (x_max - x_min)` | `z = (x - atlag) / szoras` |
| **Eredmeny tartomany** | [0, 1] (vagy tetszoleges [a, b]) | Nincs fix hatar; atlag = 0, szoras = 1 |
| **Eloszlas** | **Nem** alakit normalis eloszlassa | **Nem** alakit normalis eloszlassa |
| **Outlier-erzekenyseeg** | Nagyon erzekeny (az outlier "osszenyomja" a tobbi adatot) | Erzekeny, de kevesbe drasztikusan |
| **Hasznalat** | Neuralis halok, kepfeldolgozas, fix tartomany | Gradiens alapu modellerk, PCA, regularizacio |

![A Feature Scaling ket fo agat bemutato fa-diagram](_kepek_cleaned/04_data_preparation/slide_20.png)
*11. abra: A Feature Scaling ket fo megkozelitese: Normalizalas (MinMax) es Sztenderdizalas, mindkettohoz a pontos matematikai kepletekkel.*

> **Fontos:** Sem a normalizalas, sem a sztenderdizalas **nem alakitja** az adatokat normalis eloszlassuva!
> Mindketto csak **atmeretezi** az adatokat, de az eloszlas alakja valtozatlan marad.
> (Forras: python.plainenglish.io -- "Do Standardization and Normalization Transform the Data into Normal Distribution?")

### StandardScaler (Z-score normalizacio / Sztenderdizalas)

**Keplet:** `z = (x - atlag) / szoras`

Az atlagot **0**-ra, a szorast **1**-re allitja. **Nem** korlatozza a min/max ertekeket.

![A sztenderdizalas keplete es hatasa](_kepek_cleaned/04_data_preparation/slide_18.png)
*12. abra: A sztenderdizalas (standardization) keplete es eredmenye: az atlag 0-ra, a szoras 1-re allitodik, amit a haranggorbe szemleltet.*

![A normalis eloszlas es a standard normalis eloszlas osszehasonlitasa](_kepek_cleaned/04_data_preparation/slide_19.png)
*13. abra: A sztenderdizalas hatasa: egy normalis eloszlasu adatsor (balra, pl. atlag 1010) atalakulasa standard normalis eloszlassa (jobbra, atlag 0, szoras 1).*

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Visszaalakitas
X_eredeti = scaler.inverse_transform(X_scaled)
```

> **Elvaras:** A StandardScaler a legjobban Gauss-eloszlasu (haranggorbe alaku) adatokon mukodik.
> Ha az eloszlas erosen ferde, az eredmeny kevésbe megbizhato.

![A standardizacio peldaja hisztogrammal es kepletekkel](_kepek_cleaned/04_data_preparation/slide_17.png)
*14. abra: Standardizacio peldaja: a nyers feature eloszlasa (hisztogram) es a ket skalazasi keplet -- min-max normalizacio es standardizacio -- osszehasonlitasa.*

### MinMaxScaler

**Keplet:** `x_norm = (x - x_min) / (x_max - x_min)`

Az adatokat **0 es 1 koze** skalazza.

![A normalizalas (MinMax) peldaja hisztogramokkal](_kepek_cleaned/04_data_preparation/slide_16.png)
*15. abra: A normalizalas (min-max) vizualis bemutatasa: a nyers feature eloszlasa es a min-max keplet alkalmazasanak hatasa -- az adatok [0, 1] tartomanyba kerulnek.*

```python
from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()  # alapertelmezett: (0, 1)
X_scaled = scaler.fit_transform(X)

# Egyedi tartomany megadasa
scaler_custom = MinMaxScaler(feature_range=(-1, 1))
X_scaled_custom = scaler_custom.fit_transform(X)
```

> **Hatrany:** Outlierek eseten az adatok szuk tartomanyba zsufoldnak, mert az outlierek
> "elfoglaljak" a 0 es 1 szelseit. **Eloszor kezeld az outliereket!**

### RobustScaler

A **mediant** es az **IQR-t** hasznalja az atlag es a szoras helyett, igy **robusztus az outlierekre**.

```python
from sklearn.preprocessing import RobustScaler

scaler = RobustScaler()
X_scaled = scaler.fit_transform(X)
```

### Mikor melyiket? (osszehasonlito tablazat)

| Scaler | Keplet | Mikor hasznald | Outlier-erzekeny? |
|---|---|---|---|
| **StandardScaler** | `(x - atlag) / szoras` | Gauss-eloszlasu adatokhoz; gradiens alapu modellekhez | Igen |
| **MinMaxScaler** | `(x - min) / (max - min)` | Ha fix [0,1] tartomany kell; neuralis halozatokhoz | Nagyon erzekeny |
| **RobustScaler** | `(x - median) / IQR` | Ha vannak outlierek es nem akarod elozetesen eltavolitani | **Nem** (robusztus) |

![A normalizalas es sztenderdizalas vizualis osszehasonlitasa](_kepek_cleaned/04_data_preparation/slide_21.png)
*16. abra: A normalizalas es sztenderdizalas vizualis osszehasonlitasa: a haranggorbe (Bell Curve) es a ket technika kulonbozo eredmenye -- a normalizalas [0, 1] tartomanyra, a sztenderdizalas mu=0, sigma=1 parameterekre skalaz.*

### Mely algoritmusoknál kell skalazas?

| Kell skalazas | Indoklas | Nem kell skalazas |
|---|---|---|
| K-Nearest Neighbors (KNN) | Tavolsagszamitasra epit (pl. euklideszi) -- minden feature-nak egyenlo mertekben kell hozzajarulnia | Dontesi fa (Decision Tree) |
| K-means klaszterezes | Szinten euklideszi tavolsag-alapu | Random Forest |
| Logisztikus regresszio | Gradiens alapu optimalizacio -- kulonben egyes sulyok sokkal gyorsabban frissulnek, mint masok | Gradient Boosting (XGBoost, LightGBM) |
| Linearis regresszio | Gradiens alapu optimalizacio | Naive Bayes |
| SVM (Support Vector Machine) | Gradiens alapu optimalizacio | |
| Perceptron | Gradiens alapu optimalizacio | |
| Neuralis halozatok | Gradiens alapu optimalizacio | |
| PCA (fokomponens-elemzes) | A maximalis variancia iranyat keresi -- nagyobb skalaju valtozok dominalnanak | |
| Kernel PCA | Ugyanaz, mint PCA | |
| LDA (Linear Discriminant Analysis) | A maximalis variancia iranyat keresi ortogonalis kenyszerek mellett | |
| Lasso / Ridge regularizacieo | A buntetés erosen fugg a feature-ok skalajatol | |

> **Forras (prezentacio, 22. dia):** A skalazas kulonosen akkor kritikus, ha az algoritmus
> **tavolsagszamitasra** (KNN, K-means) vagy **gradiens alapu optimalizacioora** (logisztikus regresszio,
> SVM, neuralis halozatok) epit, illetve ha **variancia-maximalizalast** vegez (PCA, LDA).

---

## Teljes Eloekszitesi Pipeline

### sklearn Pipeline

A `Pipeline` biztositja, hogy az eloefeldolgozasi lepesek **reprodukalhatoak** legyenek,
es elkeruljuk a **data leakage**-et (a `fit` mindig csak a train adatokon tortenik).

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

# Egyseges pipeline: imputalas -> skalazas -> modell
pipe = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("model", LogisticRegression(max_iter=1000))
])

pipe.fit(X_train, y_train)
y_pred = pipe.predict(X_test)
```

### ColumnTransformer

Kulonbozo eloefeldolgozas a **numerikus** es a **kategorikus** oszlopokra:

```python
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier

# Oszloptipusok meghatarozasa
numerikus_oszlopok = ["kor", "jovedelem", "tapasztalat_ev"]
kategorikus_oszlopok = ["nem", "varos", "vegzettseg"]

# Numerikus eloefeldolgozas
numerikus_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

# Kategorikus eloefeldolgozas
kategorikus_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
])

# ColumnTransformer -- mindent egyutt kezel
preprocessor = ColumnTransformer([
    ("num", numerikus_pipeline, numerikus_oszlopok),
    ("cat", kategorikus_pipeline, kategorikus_oszlopok)
])

# Teljes pipeline: eloefeldolgozas + modell
teljes_pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", RandomForestClassifier(n_estimators=100, random_state=42))
])

# Hasznalat
teljes_pipeline.fit(X_train, y_train)
pontossag = teljes_pipeline.score(X_test, y_test)
print(f"Pontossag: {pontossag:.4f}")
```

### Kod sablon -- teljes munkafolyamat

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# 1. Adatok betoltese
df = pd.read_csv("adatok.csv")

# 2. Celvaltozo es feature-ok szétvalasztas
X = df.drop("target", axis=1)
y = df["target"]

# 3. Train-test split (ELOSZOR, mielott barmit fit-elenk!)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 4. Oszlopok tipusainak azonositasa
num_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

# 5. Pipeline felepitese
num_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

cat_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
])

preprocessor = ColumnTransformer([
    ("num", num_pipeline, num_cols),
    ("cat", cat_pipeline, cat_cols)
])

full_pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", RandomForestClassifier(n_estimators=200, random_state=42))
])

# 6. Tanitas es ertekeles
full_pipeline.fit(X_train, y_train)

# Cross-validation
cv_scores = cross_val_score(full_pipeline, X_train, y_train, cv=5, scoring="accuracy")
print(f"CV Pontossag: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# Teszt halmazon
y_pred = full_pipeline.predict(X_test)
print(classification_report(y_test, y_pred))
```

---

## Gyakorlati Utmutato

### Checklist

- [ ] **Adatok betoltese** es elso attekintes (`df.head()`, `df.info()`, `df.describe()`)
- [ ] **Train-test split elvegzese** -- MIELOTT barmit fit-elenk az adatokon!
- [ ] **Hianyzó ertekek** vizsgalata (`df.isnull().sum()`, `missingno`)
- [ ] **Hianyzó ertekek kezelese** -- torles vagy imputalas (SimpleImputer / KNNImputer)
- [ ] **Duplikaciok** ellenorzese es eltavolitasa (`df.duplicated().sum()`)
- [ ] **Outlierek** vizsgalata (boxplot, z-szkor, IQR)
- [ ] **Outlierek kezelese** -- eltavolitas, capping, transzformacio
- [ ] **Feature Engineering** -- uj feature-ok letrehozasa (aranyok, datum feature-ok, binning)
- [ ] **Feature Selection** -- felesleges feature-ok eltavolitasa
- [ ] **Encoding** -- kategorikus valtozok atalakitasa (OneHot / Label / Ordinal)
- [ ] **Skalazas** -- StandardScaler / MinMaxScaler / RobustScaler
- [ ] **Pipeline osszeallitasa** -- ColumnTransformer + Pipeline
- [ ] **Cross-validation** -- a teljes pipeline-on
- [ ] **Data leakage ellenorzes** -- minden `fit` csak a train adatokon tortent?

### Kod peldak

A reszletes, futtathato kod peldak kulon fajlban erhetoek el:

> Lasd: [_kod_peldak/adat_elokeszites.py](_kod_peldak/adat_elokeszites.py)

---

## Gyakori Hibak es Tippek

### Data leakage elkerulese

A **data leakage** (adatszivargas) a leggyakoribb es legsuyosabb hiba az adatelokeszitesben.
Akkor tortenik, amikor a **teszt adatok informacioja belefolyik a tanulasi folyamatba**.

**Hibas megkozelites:**
```python
# HIBA! A scaler az OSSZES adaton fit-el (train + test egyutt)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # <-- teljes adathalmaz!
X_train, X_test = train_test_split(X_scaled, ...)
```

**Helyes megkozelites:**
```python
# HELYES: eloszor split, aztan CSAK a train-en fit
X_train, X_test, y_train, y_test = train_test_split(X, y, ...)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)   # fit + transform a train-en
X_test_scaled = scaler.transform(X_test)          # CSAK transform a test-en!
```

**Legjobb megkozelites -- Pipeline hasznalata:**
```python
# A Pipeline automatikusan kezeli: fit csak train-en, transform mindketton
pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression())
])
pipe.fit(X_train, y_train)       # fit_transform belul, csak train-en
pipe.predict(X_test)              # transform belul, csak a test-en
```

### fit vs fit_transform vs transform

| Metodus | Mit csinal | Mikor hasznald |
|---|---|---|
| `fit(X_train)` | Megtanulja a parametreket (atlag, szoras stb.) | Csak egyszer, a train adatokon |
| `transform(X)` | Alkalmazza a megtanult parametreket | Test / uj adatokon |
| `fit_transform(X_train)` | `fit` + `transform` egyben | Train adatokon (gyorsabb) |

> **Aranyszabaly:** `fit_transform` **csak a train adatokon**, `transform` **a test es uj adatokon**.

### Tovabbi gyakori hibak

- **Skalazas fa-alapu modelleknel** -- felesleges, nem javit (Decision Tree, Random Forest, XGBoost)
- **Label Encoding nominalis valtozokra** -- hamis tavolsagokat vezet be; hasznalj One-Hot-ot
- **Outlierek vakon torlese** -- mindig kerdezd meg a domen szakertot; nem minden outlier hibas
- **MinMaxScaler outlierekkel** -- az adatokat szuk savba nyomja; hasznalj RobustScaler-t, vagy
  eloszor kezeld az outliereket
- **Kategorikus hianyzó ertekek modusszal potlasa** -- ha sok a hianyzó, inkabb kulon kategoria
- **Sztenderdizalas + normalizalas egyutt** -- felesleges, az eredmeny megegyezik a sima normalizalassal

---

## Kapcsolodo Temak

- [03_adatmegertes_es_eda.md](03_adatmegertes_es_eda.md) -- Exploratory Data Analysis, vizualizacio, eloszlas-vizsgalat
- [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- Regresszio, klasszifikacio, regularizacio (Lasso, Ridge)

---

## Tovabbi Forrasok

### Dokumentacio es konyvtarak

- **scikit-learn dokumentacio -- Preprocessing:** https://scikit-learn.org/stable/modules/preprocessing.html
- **scikit-learn dokumentacio -- Impute:** https://scikit-learn.org/stable/modules/impute.html
- **scikit-learn dokumentacio -- Pipeline:** https://scikit-learn.org/stable/modules/compose.html
- **scikit-learn dokumentacio -- Feature Selection:** https://scikit-learn.org/stable/modules/feature_selection.html
- **missingno konyvtar:** https://github.com/ResidentMario/missingno
- **Pandas dokumentacio:** https://pandas.pydata.org/docs/
- **Feature Engineering konyv (Alice Zheng & Amanda Casari):** *Feature Engineering for Machine Learning* (O'Reilly)

### A PDF prezentacioban hivatkozott forrasok (Gerzson Boros: "Data Preparation")

**Data Science folyamat:**
- Data Science Process: https://medium.com/@DataScienceKen/the-data-science-process-part-2-defining-the-project-4cbb75464965
- Data Preparation pipeline: https://addepto.com/blog/data-preparation-for-machine-learning-projects/
- CRM Data Cleansing: https://www.trujay.com/blog/crm-data-cleansing-and-how-to-clean-it-up

**Hianyzó ertekek:**
- Hianyzó ertekek kezelesi utmutato: https://www.analyticsvidhya.com/blog/2021/10/guide-to-deal-with-missing-values/

**Outlier detektalas:**
- Outlier kalkulator (IQR-alapu): https://www.inchcalculator.com/outlier-calculator/
- Z-score es p-ertek ertelmezese: https://pro.arcgis.com/en/pro-app/3.1/tool-reference/spatial-statistics/what-is-a-z-score-what-is-a-p-value.htm
- Z-score keplet: https://www.z-table.com/z-score-formula.html
- Outlier detektalas es kezeles: https://www.analyticsvidhya.com/blog/2021/05/detecting-and-treating-outliers-treating-the-odd-one-out/

**Feature Engineering:**
- Feature Engineering attekintes: https://www.datasciencecentral.com/feature-engineering-at-a-glance/
- Encoding peldak (Kaggle): https://www.kaggle.com/discussions/getting-started/187540

**Skalazas (Normalizalas vs. Sztenderdizalas):**
- Skalazas video: https://www.youtube.com/watch?v=sxEqtjLC0aM
- Standardization tutorial: https://365datascience.com/tutorials/statistics-tutorials/standardization/
- Standardization vs Normalization: https://cafecotech.hashnode.dev/standardization-or-normalization-ck97uo4eg01m7f3s1tip0btlc
- Normalis eloszlassa alakit-e?: https://python.plainenglish.io/do-standardization-and-normalization-transform-the-data-into-normal-distribution-cb5857ab9c63
- Normalization vs Standardization osszehasonlitas: https://www.simplilearn.com/normalization-vs-standardization-article
- Standardization and Normalization: https://algodaily.com/lessons/standardization-and-normalization
- Scaling vs Normalizing: https://towardsai.net/p/data-science/scaling-vs-normalizing-data-5c3514887a84
- Mikor kell skalazni?: https://www.quora.com/Machine-Learning-When-should-I-apply-data-normalization-standardization

---

## Kepjegyzek

| Abra | Dia | Leiras |
|---|---|---|
| 1. abra | slide_02 | A teljes Data Science munkafolyamat fazisai -- az uzleti problema megertésetol a deploymentig, visszacsatolasi hurkokkal |
| 2. abra | slide_03 | Az adatelokeszites hat fo fazisa: Gather, Discover, Cleanse, Transform, Enrich, Store |
| 3. abra | slide_04 | A Data Cleansing Cycle -- az adattisztitas kokorosen ismetlodo lepései |
| 4. abra | slide_06 | A hianyzó ertekek kezelesi strategiainak dontes-faja (torles vs. imputalas) |
| 5. abra | slide_07 | Outlierek detektalasa scatter ploton -- normalis adatpontok es kiugro ertekek |
| 6. abra | slide_08 | A Z-score keplete es a szignifikancia szintek vizualizacioja normalis eloszlason |
| 7. abra | slide_09 | Outlier detektalas Z-score alapjan -- az eloszlasi zonak (Not unusual, Moderately unusual, Outliers) |
| 8. abra | slide_11 | A Feature Engineering hat fo teruletenek hexagon diagramja |
| 9. abra | slide_13 | Label Encoding, One-Hot Encoding es Dummy Encoding osszehasonlitasa pelda-tablazatokkal |
| 10. abra | slide_14 | A skalazas vizualis bemutatasa hisztogramokkal es kepletekkel |
| 11. abra | slide_20 | A Feature Scaling ket fo agat bemutato fa-diagram (Normalizalas vs. Sztenderdizalas) |
| 12. abra | slide_18 | A sztenderdizalas keplete es hatasa haranggorbével (mu=0, sigma=1) |
| 13. abra | slide_19 | A normalis es standard normalis eloszlas osszehasonlitasa |
| 14. abra | slide_17 | Standardizacio peldaja hisztogrammal es ket skalazasi keplettel |
| 15. abra | slide_16 | A normalizalas (MinMax) vizualis bemutatasa hisztogramokkal es keplettel |
| 16. abra | slide_21 | A normalizalas es sztenderdizalas vizualis osszehasonlitasa haranggorbékkel |
