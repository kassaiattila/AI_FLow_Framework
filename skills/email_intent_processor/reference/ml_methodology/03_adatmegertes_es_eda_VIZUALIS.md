> Vizualis verzio - kepekkel kiegeszitve | Eredeti: [03_adatmegertes_es_eda.md](03_adatmegertes_es_eda.md)

> Utolso frissites: 2026-03-09 | Forrasok: 5 transzkript + 1 Jupyter notebook + 1 PDF prezentacio

# Adatmegertesi es EDA (Exploratory Data Analysis)

## Gyors Attekintes

> Az adatmegertes es a felderto adatelemzes (EDA) a gepi tanulasi projektek legkritikusabb kezdeti fazisa. Az uzleti cel megertese utan az adatok alapos megismerese, vizualizacioja es minosegi ellenorzese elengedhetetlen ahhoz, hogy hatekony ML modelleket fejlesszunk. Az EDA soran felismerhetjuk a mintazatokat, trendeket, anomaliakat es korrelacciokat, amelyek megalapozzak az adatelokeszites es a modellezesi strategia dontest. Ez a folyamat kreaticitast, domenismeretet es szisztematikus ellenorzest igenyel egyszerre.

---

## Kulcsfogalmak

- **Adatmegertes (Data Understanding)**: Az adatok alapos megismerese, statisztikai jellemzoik felterkepeztese es minosegi vizsgalata a modellfeijlesztes elott
- **EDA (Exploratory Data Analysis)**: Felderto adatelemzes -- kreatv, vizualis es statisztikai modszerekkel felderitjuk az adatok szerkezetet, mintazatait es kapcsolatait
- **Adatminoseg (Data Quality)**: Az adatok pontossaga, teljessege, megbizhatatosaga es relevancija egy adott feladathoz
- **Korrelaciio**: Ket vagy tobb valtozo kozotti statisztikai kapcsolat merteke (-1 es +1 kozott)
- **Outlier (kiugroi ertek)**: Az adathalmaz tobbi elemeitol szignifikansan eltero adatpont
- **Feature (jellemzo)**: Az adathalmaz egy-egy oszlopa/valtozoja, amelyet a modell tanulasahoz hasznalunk
- **Target valtozo**: Az a valtozo, amelyet a modell prediikciojanak celja megjosolni
- **Domenismeret**: Az adott szakterulet (pl. orvostudomany, penzugy) melysegi ismerete, amely nelkul az adatok nem ertelmezhetoek
- **Univariate elemzes**: Egyetlen valtozo onallo vizsgalata (eloszlas, statisztikak)
- **Multivariate elemzes**: Tobb valtozo egyuttes vizsgalata, kapcsolataik felteerkepezese
- **Kategoriavaltozo**: Diszkret csoportokat jelolo valtozo (pl. szin, nem, osztalyy)
- **Folytonos valtozo**: Barmilyen numerikus erteket felveiheto valtozo egy intervallumon belul (pl. homerseklet, ar)
- **Ordinalis valtozo**: Olyan kategoriavaltozo, amelynel a kategoriak kozott rendezesi sorrend all fenn (pl. enyhe < kozepsulyos < sulyos)

---

## Adatmegertes

### Miert fontos?

Az adatmegertes a gepi tanulasi projekt elso erdemi munkalepese az uzleti cel megertese utan. Ahogy egy asztalos alaposan megvizsgalja a fat mielott dolgozni kezdene vele, ugy nekunk is alaposan meg kell ismerunk az adatainkat.

**A legnagyobb hiba**: rogtoon ML modelleket kezdeni epiteni az adatok megertese nelkul. Ez rengeteg idoipazarlashoz es csapdakhoz vezethet.

Az adatmegertes fontossaganak fo okai:

1. **Komplexitas egyszerusitese (Simplification of Complexity)**: A vizualizaciok az osszetett adatokat -- nagy adathalmazokat, tobbdimenzios informaciot -- grafikus formaba alakitjak, igy konnyebb megerteni a mintazatokat es trendeket
2. **Mintazatok felismerese (Pattern Recognition)**: Az agyunk vizualisan van behuzalozva a mintak felismeresere; a vizualizaciok segitenek gyorsan es pontosan eszrevenni a trendeket, kiugro ertekeket es anomaliakat
3. **Kontextus megertese (Contextual Understanding)**: A vizualizaciok kontextust adnak az adatokhoz, megmutatjak, hogyan kapcsolodnak es hatnak egymasra a kulonbozo adatpontok (pl. egy scatter plot ket valtozo kapcsolatat abrazolja)
4. **Osszehasonlitas es kontrasztolas (Comparison and Contrast)**: Olyan eszkozok, mint az oszlopdiagramok, kordiagramok es vonaldiagramok lehetove teszik a kulonbozo adatok egyertelmuu osszehasonlitasat, tamogatva a hatekony donteshozast
5. **Storytelling (tortenetmeseles)**: A vizualizaciok elmeselhetik az adatok tortenetet, logikus es lebilincselo modon rendezve az informaciot, ami megkonnyiti a kozonseg szamara a megeertest
6. **Minosegi problemaak es anomaliak felderitese (Detecting Quality Problems, Anomalies)**: A vizualis megjelenitesek megkonnyitik az elteeresek es kiugro ertekek felismereeset, ravilagitva a lehetseges hibakra vagy tovabbi vizsgalatot igenylo teruletekre
7. **Prediktiv insightok (Predictive Insights)**: A tortenelmi adatok es trendek vizualizalasa segit megerteni a jovobeli lehetosegeket, es pontosabb elorjelzeseket es becslieseket tesz lehetove
8. **Dontestamogatas (Decision Support)**: A vilagos, jol megtervezett vizualizaciok atfogo kepet adnak az adatokrol a donteshozok szamara, tamogatva a tenyeken alapulo, adatvezerelt donteseket
9. **Kommunikacio es egyuttmukodes (Communication and Collaboration)**: A vizualizaciok univerzalis adatnyelkent mukodnek, javitva a kommunikaciot es egyuttmukodest a kulonbozo adat-jartassagu csapattagok es erdekelt felek kozott

> **Fontos**: Az adatvizualiciaciora es megertesre forditott ido nem felesleges -- ez a befektetes megsokszorozza a kesoobbi modellezes hatekonysagat.

### CRISP-DM keretrendszer: Data Understanding fazis

A CRISP-DM (Cross-Industry Standard Process for Data Mining) keretrendszerben az adatmegertes a masodik fazis, amely kozvetlenul az uzleti cel megertese (Business Understanding) utan kovetkezik:

```
Business Understanding --> DATA UNDERSTANDING --> Data Preparation --> Modeling --> Evaluation --> Deployment
```

A Data Understanding fazis 4 fo feladatbol (Task) es 4 kimeneti dokumentumbol (Output) all:

| Feladat (Task) | Kimeneti dokumentum (Output) |
|---|---|
| **Collect Initial Data** -- Kezdeti adatok osszegyujtese | **Initial Data Collection Report** -- Adatgyujtesi jelentes |
| **Describe Data** -- Adatok leirasa | **Data Description Report** -- Adatleirasi jelentes |
| **Explore Data** -- Adatok felderitese (EDA) | **Data Exploration Report** -- Felderiito elemzesi jelentes |
| **Verify Data Quality** -- Adatminoseg ellenorzese | **Data Quality Report** -- Adatminosegi jelentes |

![CRISP-DM Data Understanding fazis es a pd.describe() kimenet](_kepek_cleaned/03_data_understanding/slide_03.png)
*1. abra: A CRISP-DM keretrendszer Data Understanding fazisa a 4 fo feladattal (Collect, Describe, Explore, Verify) es azok kimeneti dokumentumaival, valamint a `pd.describe()` fuggveny pelda kimenete, amely az alapveto statisztikai jellemzoket osszegzi.*

> **Megjegyzes**: A `pd.Series.describe()` / `DataFrame.describe()` fuggveny a "Describe Data" lepes fo eszkoze. Pelda: `s = pd.Series([2, 3, 4])` eseten a `s.describe()` kimenete: count=3.0, mean=3.0, std=1.0, min=2.0, 25%=2.5, 50%=3.0, 75%=3.5, max=4.0.

### Adatmegertesi lepesek

A tananyag alapjan az adatmegertes az alabbi strukturalt lepesekbol all:

#### 1. Kommunikacio a domen szakertokkel

- Kerdezzuk meg a szakterulet ismeroit az adatok jellegerol, kontextusarol
- Szerezzunk be domenismeretet -- ez nem szegyen, hanem a projekt sikeirenek kulcsa
- Az uzleti cel is csiszolodhat a beszellgetesek soran
- Ez nem egyszeri lepes: a projekt egesz ideje alatt erdemes konzultalni

#### 2. Kommunikacio az adatgyujto mernokokkel

- Hogyan lettek gyujtve az adatok?
- Milyen forrasokat hasznaltak?
- Vannak-e ismert korlatozasok vagy hibak?
- Eredmeny: **Data Collection Report**

#### 3. Alapveto statisztikai jellemzok megismerese

- Pandas `.describe()`, `.info()`, `.isnull()` hasznalata
- Elemszam, atlag, szoras, min/max, percentilisek feltarasa
- Eredmeny: **Data Description Report**

```python
import pandas as pd
import numpy as np

# Adatok betoltese
df = pd.read_csv("data/horse-colic.data", header=None, delim_whitespace=True)

# Hianyzo ertekek jelolesenek egysegesitese
df = df.replace('?', np.nan)

# Oszlopnevek beallitasa
list_column_names = ["V" + str(i) for i in range(1, 29)]
df.columns = list_column_names

# Alapveto informaciok
df.info()          # oszlopok, tipusok, nem-null ertekek szama
df.describe()      # statisztikai osszefoglalo (numerikus oszlopokra)
df.isnull().sum()  # hianyzo ertekek szama oszloponkent
```

#### 4. Exploratory Data Analysis (EDA)

- Kreatv, felfedezoi jellegu adatvizsgalat
- Kulonbozo vizualizaciok es osszehasonlitasok kiprobailasa
- Eredmeny: **Data Exploration Report** (PDF, HTML vagy Jupyter Notebook)

#### 5. Adatminoseg vizsgalata

- Szisztematikus ellenorzes az adatminosegi szempontok alapjan
- Eredmeny: **Data Quality Report**

### Adatminoseg dimenzioi

Az adatminoseg 12 dimenzioija, amelyeket erdemes szisztematikusan vizsgalni:

| Dimenzio | Angol megnevezes | Leiras | Angol definicio (prezentaciobol) |
|---|---|---|---|
| **Pontossag** | Accuracy | Mennyire fedik a meresek a valosagot? Rosszul mero eszkoz adatai nem hasznosiithatoak. | The extent to which it is close to reality. |
| **Elerhetoseg** | Availability | Hozza tudunk-e ferni az adatokhoz? Tanitas es production kozott is elerheto-e? | The degree to which users or systems can access data. |
| **Teljesseeg** | Completeness | Megvannak-e a szukseges oszlopok, rekordok, fajlok, meta-adatok? | The extent to which every data attribute, record, file, value, and metadata is present and accounted for. |
| **Megfeleleoseg** | Compliance | Megfelel-e az adat a jogi eloirasoknak (pl. GDPR)? | The degree to which data complies with applicable laws. |
| **Konzisztencia** | Consistency | A belso szabalyoknak megfelel-e (pl. telefonszam-formatumok)? | The extent to which data across multiple datasets or domains comply with specified rules. |
| **Integritas** | Integrity | Megbiizhato-e az adat? Volt-e manipulacio vagy illetektelen hozzaferes? | The measure of the absence of corruption, manipulation, loss, leakage, or unauthorized access in the dataset. |
| **Kesleltetes** | Latency | Milyen gyorsan valik elerhetove az adat? (Kritikus pl. ajanloorend szerenel) | The delay in the production and availability of data. |
| **Targyilagossag** | Objectivity | Mennyire elfogultatlan az adat? Nem tartalmaz-e szubjektiv velieményeket? | The degree to which data are produced and evaluated without bias (personal opinion, emotion, subjectivity). |
| **Plauzibilitas** | Plausibility | Valoszeru-e az adat? Kulonosen fontos szimulalt/generalt adatoknal. | The extent to which the dataset is relevant to real-world situations. |
| **Redundancia** | Redundancy | Vannak-e ismetlodo rekordok? (Torzithatjak az eredmenyt) | The presence of logically identical information in the data. |
| **Nyomonkovethetooseg** | Traceability | Ismerjuk-e az adatforrasit? Ismeretlen forras csapdakat rejthet. | The ability to verify the source of data. |
| **Volatilitas** | Volatility | Mennyire valtozekony az adat idovel? (Gazdasagi/politikai adatok gyakran valtoznak) | The extent to which the values in the dataset change over time. |

### Adattipusok

Az EDA soran kulonbozo adattipusokkal talalkozhattunk, es mindegyiket maskepp kell kezelni:

| Tipus | Leiras | Pelda | Tipikus vizualizacio |
|---|---|---|---|
| **Folytonos (numerikus)** | Barmilyen ertek egy intervallumon | Homerseklet, ar, suly | Hisztogram, boxplot, KDE |
| **Kategorikus (nominalis)** | Diszkret csoportok, sorrend nelkul | Szin, nem, faj | Count plot, bar chart |
| **Ordinalis** | Kategorikus, de sorrenddel | Sulyossagi fokozat (1-5) | Count plot, bar chart |
| **Datum/ido** | Idopontos adatok | Vasarlasi datum | Vonaldiagram (idosor) |

> **Tipp**: Az automatizalt EDA eszkozok (pl. YData Profiling) nem mindig talailjak el helyesen az oszlopok tipusat. Mindig erdemes kezzel ellenorizni es sajat listat kesziteni!

---

## EDA (Felderiito Adatelemzes)

Az EDA egy kreativ, strukturaltan nem kotott folyamat, amelynek celja az adatok alapos megismerese vizualizaciok es statisztikai modszerek segitsegevel. Ugyanakkor vannak bevalt technikak es best practice-ek.

### EDA Cheatsheet -- Strukturalt dontiesi fa

A prezentacio egy EDA cheatsheet-et mutat be, amely strukturalt dontiesi faként foglalja ossze a felderiito elemzes lepeseit:

```
EDA
 |
 +-- Non-graphical Analysis (Nem grafikus elemzes)
 |     df.info()
 |     df.describe()
 |     df.isnull()
 |
 +-- Univariate Analysis (Egyvaltozos elemzes)
 |     |
 |     +-- Numerical (Numerikus):     df[column].plot(kind="hist")
 |     +-- Categorical (Kategorikus): df[column].plot(kind="bar")
 |
 +-- Multivariate Analysis (Tobbvaltozos elemzes)
       |
       +-- Numerical vs. Numerical:     sns.pairplot() / sns.heatmap()
       +-- Categorical vs. Categorical: sns.countplot(hue=...)
       +-- Categorical vs. Numerical:   sns.boxplot() / sns.pairplot(hue=...)
```

![EDA Cheatsheet -- az elemzesi lepesek strukturalt attekintese](_kepek_cleaned/03_data_understanding/slide_05.png)
*2. abra: EDA Cheatsheet -- a felderto adatelemzes harom fo pillere (nem grafikus elemzes, egyvaltozos es tobbvaltozos elemzes) a hozzajuk tartozo Python fuggvenyekkel es vizualizacios tipusokkal.*

> **Forras**: https://www.visual-design.net/post/semi-automated-exploratory-data-analysis-process-in-python

### Univariate elemzes

Egyetlen valtozo onallo vizsgalata. Celja: megerteni egy-egy oszlop eloszlasat, jellemzoit.

**Folytonos valtozoknal:**
```python
import matplotlib.pyplot as plt
import seaborn as sns

# Hisztogram -- folytonos valtozo eloszlasa
plt.figure(figsize=(10, 6))
sns.histplot(df['V4'].dropna().astype(float), bins=30, kde=True)
plt.title('Homerseklet eloszlasa (V4)')
plt.xlabel('Homerseklet (Celsius)')
plt.ylabel('Gyakorisag')
plt.show()
```

**Kategorikus valtozoknal:**
```python
# Oszlopdiagram (bar plot) -- kategoriavaltozo gyakorisaga
plt.figure(figsize=(8, 5))
df['V1'].value_counts().plot(kind='bar')
plt.title('V1 valtozo eloszlasa (1=muteti, 2=nem muteti)')
plt.xlabel('Kategoria')
plt.ylabel('Darabszam')
plt.show()
```

**Pandas beepitett modszerek:**
```python
# Describe: statisztikai osszefoglalo
print(df['V4'].astype(float).describe())
# count    240.000000
# mean      38.167917
# std        0.732842
# min       35.400000
# 25%       37.800000
# 50%       38.200000
# 75%       38.500000
# max       40.800000

# Ertekeloszlas kategoriavaltozokra
print(df['V1'].value_counts())
```

### Bivariate elemzes

Ket valtozo kozotti kapcsolat vizsgalata. Mas technika kell a valtozotipusoktol fuggoen:

| Valtozotipusok | Ajanlott diagram |
|---|---|
| Folytonos vs. Folytonos | Scatter plot, pair plot |
| Kategorikus vs. Kategorikus | Count plot (hue-val), stacked bar |
| Kategorikus vs. Folytonos | Box plot, violin plot |

**Kategorikus vs. Kategorikus -- Count plot (Titanic pelda):**
```python
# Count plot ket kategoriavaltozo osszehasonlitasara
# Pelda: Titanic -- osztalyy vs. tuleles
import seaborn as sns

sns.countplot(x='Pclass', hue='Survived', data=titanic_df)
plt.title('Tuleles osztaly szerint')
plt.xlabel('Utazasi osztaly')
plt.ylabel('Darabszam')
plt.show()
```

![Countplot -- Titanic tuleles osztaly szerint](_kepek/03_data_understanding/slide_06.png)
*3. abra: Titanic countplot pelda -- az X tengelyen a harom utazasi osztaly (First, Second, Third), az Y tengelyen a darabszam lathato. A kek oszlopok a nem tulelok, a narancs oszlopok a tulelok szamat mutatjak. Jol latszik, hogy a 3. osztalyban kiugroan magas a halalozas.*

> **A prezentacio pelda-abraja (Titanic countplot)**: Az X tengelyen a harom utazasi osztaly (First, Second, Third), az Y tengelyen a darabszam (count) lathato. Mindegyik osztalynal ket oszlop: survived=0 (kek, nem elte tul) es survived=1 (narancs, tulelte). A diagram jol mutatja, hogy a 3. osztalyban kiugro merteku a halalozas (~370 fo nem elte tul vs. ~120 tulelo), mig az 1. osztalyban tobben eltek tul (~136), mint ahany meghalt (~80). Ez tipikus pelda arra, hogyan tarja fel a countplot ket kategoriavaltozo kapcsolatat.

**Kategorikus vs. Folytonos -- Box plot (Titanic pelda):**
```python
# Box plot: kategorikus es folytonos valtozo
# Pelda: Titanic -- osztaly vs. kor, szinezve a tuleles altal
sns.boxplot(x='Pclass', y='Age', hue='Survived', data=titanic_df)
plt.title('Kor eloszlasa osztaly es tuleles szerint')
plt.xlabel('Utazasi osztaly')
plt.ylabel('Kor')
plt.show()
```

![Boxplot -- Titanic kor eloszlasa osztaly es tuleles szerint](_kepek/03_data_understanding/slide_07.png)
*4. abra: Titanic boxplot pelda -- az osztaly (First, Second, Third) es a tuleles (alive: no/yes) szerint szinezett boxplotok mutatjak az eletkor eloszlasat. Latszik, hogy az 1. osztalyban az idosebbek kisebb esellyel eltek tul, mig a 3. osztalyban mindket csoport fiatalabb.*

> **A prezentacio pelda-abraja (Titanic boxplot)**: Az X tengelyen a harom utazasi osztaly (First, Second, Third), az Y tengelyen az eletkor (age, 0-80) lathato. Mindegyik osztalynal ket boxplot: alive=no (kek) es alive=yes (narancs). Fo megfigylesek: (1) Az 1. osztalyban a nem tulelok medianja magasabb (~45 ev) mint a tuleloke (~35 ev), ami arra utal, hogy az idosebbek kisebb esellyel eltek tul. (2) A 3. osztalyban mindket csoport fiatalabb (median ~25 ev). (3) Tobb outlier pont lathato (pl. 80 eves tulelo az 1. osztalyban). Ez a diagram pelda arra, hogyan vizsgalhatjuk egyidoben egy kategorikus (osztaly), egy kategorikus (tuleles) es egy folytonos (kor) valtozo kapcsolatat.

A box plot ertelmezese:
- **Doboz**: az elso kvartilis (Q1, 25%) es harmadik kvartilis (Q3, 75%) kozott
- **Vonal a dobozban**: median (50%)
- **Bajuszok**: min es max (az outliereket kive)
- **Pontok a bajuszokon tulra**: outlierek

### Multivariate elemzes

Tobb valtozo egyuttes vizsgalata, osszetettebb kapcsolatok feltarasa.

**Pair plot:**
```python
# Pair plot -- tobb folytonos valtozo osszehasonlitasa
# Az atlon hisztogramok (vagy KDE) lathatoak
# Az atlon kivul scatter plotok
sns.pairplot(df[['V4', 'V5', 'V6', 'V19']].dropna().astype(float))
plt.suptitle('Pair plot a valasztott valtozokra', y=1.02)
plt.show()

# Pair plot hue-val (target valtozo szerinti szinezes)
sns.pairplot(df[['V4', 'V5', 'V6', 'V24']].dropna().astype(float),
             hue='V24')
plt.show()
```

![Pairplot -- Palmer Penguins adathalmaz, sziget szerinti szinezessel](_kepek_cleaned/03_data_understanding/slide_08.png)
*5. abra: Pairplot pelda a Palmer Penguins adathalmazbol -- 4 numerikus valtozo (csorrhossz, csormelyseg, uszonyhossz, testtomeg) paronkenti osszehasonlitasa, szinezve a 3 sziget szerint. Az atlon KDE eloszlasgorbek, az atlon kivul scatter plotok mutatjak a csoportok elkuulonuleset.*

> **A prezentacio pelda-abraja (Palmer Penguins pairplot)**: A prezentacio egy pairplot peldat mutat a Palmer Penguins adathalmazbol, amelyben 4 numerikus valtozo (culmen_length_mm, culmen_depth_mm, flipper_length_mm, body_mass_g) paronkenti osszehasonlitasa lathato, szinezve a 3 sziget (island: Torgersen=kek, Biscoe=narancs, Dream=zold) szerint. Az atlon KDE eloszlasgorbek mutatjak az egyes csoportok eloszlasat, mig az atlon kivuli scatter plotok a paronkenti kapcsolatokat. A diagram jol mutatja, hogyan kulonulnek el a kulonbozo szigetekrol szarmazo pingvinek -- peldaul a Biscoe sziget pingvinjei altalaban nagyobb testtomeggel es uszonyahosszal rendelkeznek. Forras: https://towardsdatascience.com/5-advanced-visualisation-for-exploratory-data-analysis-eda-c8eafeb0b8cb

### Korrelaccios elemzes

A korrelacio megmutatja, hogy az egyes valtozok hogyan mozognak egyutt.

```python
# Numerikus oszlopok kivalasztasa es tipuskonverzio
numeric_cols = ['V4', 'V5', 'V6', 'V19', 'V20', 'V24']
df_numeric = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

# Pearson korrelacios matrix
corr_matrix = df_numeric.corr()
print(corr_matrix)

# Spearman korrelacios matrix (ordinalis valtozokhoz jobb)
spearman_corr = df_numeric.corr(method='spearman')
print(spearman_corr)
```

A korrelacio ertelmezese:
- **+1**: tokeletes pozitiv korrelaciio (egyutt noveksznek)
- **-1**: tokeletes negativ korrelaciio (ellentetesen mozognak)
- **0**: nincs linearis kapcsolat
- **|r| > 0.5**: eros korrelaciio
- **0.3 < |r| < 0.5**: kozeperes korrelaciio
- **|r| < 0.3**: gyenge korrelaciio

> **A peldabol**: A lo kolika adathalmazban a V24 (prediiktalt: sebeszeti lezio) erosen korrelal a V1-gyel (0.596) es a V18-cal (0.574).

---

## Vizualizacios Technikak

### A legfontosabb vizualizacios tipusok attekintese

![Data Visualization attekinto mezoony -- 11 alapveto diagramtipus](_kepek_cleaned/03_data_understanding/slide_09.png)
*6. abra: Az adatvizualizacio 11 leggyakrabban hasznalt diagramtipusa mezosonyben: Pie Chart, Scatter Chart, Line Chart, Area Plot, Bar Charts, Hexbin Plots, Box Plot, Histogram, Pair Plot, KDE Charts es Heat Map.*

### Hisztogram

Az eloszylas megjelenitesere szolgal folytonos valtozok eseteben. Megmutatja, hogyan oszlanak el az ertekek.

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Alap hisztogram matplotlib-tel
plt.figure(figsize=(10, 6))
plt.hist(df['V4'].dropna().astype(float), bins=30, edgecolor='black', alpha=0.7)
plt.title('Homerseklet eloszlasa')
plt.xlabel('Homerseklet (Celsius)')
plt.ylabel('Gyakorisag')
plt.show()

# Hisztogram KDE gorbeevel (seaborn)
plt.figure(figsize=(10, 6))
sns.histplot(df['V4'].dropna().astype(float), bins=30, kde=True, color='steelblue')
plt.title('Homerseklet eloszlasa KDE gorbeevel')
plt.xlabel('Homerseklet (Celsius)')
plt.ylabel('Gyakorisag')
plt.show()
```

**Mikor hasznald**: Folytonos valtozok eloszlasanak gyors attekintesere (pl. eletkort, homerseklet, ar).

### Boxplot

Az eloszlas osszefoglalo statisztikaait (median, kvartilisek, outlierek) jeleniti meg.

```python
# Egyszeruu boxplot
plt.figure(figsize=(8, 6))
sns.boxplot(y=df['V4'].dropna().astype(float))
plt.title('Homerseklet boxplot')
plt.ylabel('Homerseklet (Celsius)')
plt.show()

# Csoportositott boxplot (kategorikus valtozo szerint)
plt.figure(figsize=(10, 6))
sns.boxplot(x='V1', y=df['V4'].astype(float), data=df)
plt.title('Homerseklet eloszlasa a V1 (muteti/nem muteti) szerint')
plt.xlabel('V1 (1=muteti, 2=nem muteti)')
plt.ylabel('Homerseklet (Celsius)')
plt.show()
```

**Mikor hasznald**: Outlierek azonositasara, csoportok osszehasonlitasara, eloszlas gyors attekintesere.

### Scatter plot

Ket folytonos valtozo kozotti kapcsolat vizualizalasa.

```python
plt.figure(figsize=(10, 6))
df_plot = df[['V4', 'V5']].dropna().astype(float)
plt.scatter(df_plot['V4'], df_plot['V5'], alpha=0.5, edgecolors='black')
plt.title('Homerseklet vs. Pulzus')
plt.xlabel('Homerseklet (V4)')
plt.ylabel('Pulzus (V5)')
plt.show()

# Scatter plot szinezessel (target valtozo szerint)
plt.figure(figsize=(10, 6))
df_scatter = df[['V4', 'V5', 'V24']].dropna()
df_scatter = df_scatter.astype(float)
scatter = plt.scatter(df_scatter['V4'], df_scatter['V5'],
                      c=df_scatter['V24'], cmap='viridis', alpha=0.6)
plt.colorbar(scatter, label='V24 (target)')
plt.title('Homerseklet vs. Pulzus (szinezve a target szerint)')
plt.xlabel('Homerseklet (V4)')
plt.ylabel('Pulzus (V5)')
plt.show()
```

**Mikor hasznald**: Ket folytonos valtozo kozotti kapcsolat, klaszterek, trendek felismeresere.

### Heatmap (korrelacios matrix)

Szines matrix, amely vizualisan jeleniti meg az osszes valtozupar kozotti korrelaciiot.

```python
# Korrelacios matrix heatmap
plt.figure(figsize=(14, 10))
numeric_df = df.apply(pd.to_numeric, errors='coerce')
corr = numeric_df.corr()

sns.heatmap(corr,
            annot=True,          # szamertekek megjelenitese
            fmt='.2f',           # ket tizedes jegy
            cmap='coolwarm',     # szinpaletta
            center=0,            # 0 legyen a kozepponti ertek
            square=True,
            linewidths=0.5)
plt.title('Korrelacios matrix heatmap')
plt.tight_layout()
plt.show()
```

**Mikor hasznald**: Osszes valtozpar korrelaiociojanak egyidobeni attekintesere. Segit azonositani az erosen osszeifuggo valtozopaarokat es a target-tel legjobban korrelaalo feature-oket.

### Pairplot

Matrix formajaban megjelenitii az osszes valtozpar scatter plotjait es az egyes valtozok eloszlasat.

```python
# Alap pairplot
selected_cols = ['V4', 'V5', 'V6', 'V19', 'V20']
df_pair = df[selected_cols].apply(pd.to_numeric, errors='coerce').dropna()

sns.pairplot(df_pair, diag_kind='kde')  # atlon KDE hisztogram
plt.suptitle('Pairplot a valasztott valtozokra', y=1.02)
plt.show()

# Pairplot target valtozo szinezessel
selected_cols_with_target = ['V4', 'V5', 'V6', 'V24']
df_pair2 = df[selected_cols_with_target].apply(pd.to_numeric, errors='coerce').dropna()
df_pair2['V24'] = df_pair2['V24'].astype(int).astype(str)

sns.pairplot(df_pair2, hue='V24', diag_kind='kde')
plt.suptitle('Pairplot target (V24) szerinti szinezessel', y=1.02)
plt.show()
```

**Mikor hasznald**: Tobb folytonos valtozo kozotti kapcsolatok attekintesere, csoportok elkuulonuulesenek vizualizalasara.

### Tovabbi hasznos diagramtipusok

| Diagram | Leiras | Jellemzo hasznalat |
|---|---|---|
| **KDE plot** | Simittott hisztogram (surrusegbecsles) | Folytonos valtozok osszehasonlitasa |
| **Vonaldiagram** | Idosorok megjelenites | Idofuggo adatok trendjei |
| **Count plot** | Kategoriak gyakorisaga | Kategorikus valtozok eloszlasa |
| **Violin plot** | Boxplot + KDE kombinacio | Reszletesebb eloszlas-attekintes |
| **Area plot** | Kitoltott teruleti diagram | Resz-egesz aranyok idosorban |
| **Hexbin plot** | Hexagonis surrusegteerkep | Sok adatpont scatter-je helyett |
| **Pie chart (kordiagram)** | Resz-egesz aranyok vizualis megjelenitese | Kategorikus valtozok aranyainak osszehasonlitasa |

### Kiegeszito vizualizacios tipusok (halado)

A prezentacio utolso diaja egy bovitett vizualizacios katologust mutat be, amely a szabvanyos EDA diagramokon tulmenoen is hasznos lehet speciailisabb feladatokhoz:

![Bovitett vizualizacios katalogus -- 15 halado diagramtipus](_kepek_cleaned/03_data_understanding/slide_10.png)
*7. abra: Bovitett vizualizacios katalogus 15 halado diagramtipussal: Dot Plot, Radar Diagram, Waterfall Chart, Population Pyramid, Sociogram, Multi-level Donut Chart, Angular Gauge, Phase Diagram, Cycle Diagram, 3D Stream Graph, Boxplot, Semi Circle Donut Chart es Topographic Map.*

| Diagram | Leiras | Jellemzo hasznalat |
|---|---|---|
| **Dot Plot (pontdiagram)** | Diszkret ertekek osszehasonlitasa pontokkal | Kis adathalmaz kategorikus osszehasonlitasa |
| **Radar Diagram (pokhalo-diagram)** | Tobb dimenzio egyidobeni osszehasonlitasa | Tobbdimenzios profilok vizualizalasa |
| **Waterfall Chart (vizeses diagram)** | Kumulativ hatas lepesenkenti megjelenitese | Penzugyi elemzesek, valtozasok kovetese |
| **Population Pyramid (korfadiagram)** | Ket iranyban szimmetrikus oszlopdiagram | Demografiai eloszlasok, korosztaly-elemzes |
| **Sociogram** | Halozati graf, pontok es elek | Kapcsolati halok, halozatelemzes |
| **Cycle Diagram (ciklus-diagram)** | Korkorosffolyamatabrazolas | Ismeetlodo folyamatok, eletciklusok |
| **Multi-level Donut Chart** | Egymasba agyazott kordiagramok | Hierarchikus resz-egesz aranyok |
| **Topographic Map (topografiai terkep)** | Szintvonalak 2D feluleten | Surruseg- vagy magassag-eloszlas |
| **Angular Gauge (oralap-diagram)** | Mutatos merooeszkooz jelleguu abra | KPI-k, egyetlen metrika vizualis kijelzese |
| **3D Stream Graph** | Haromdimenzios teruleti diagram | Osszetett idosori osszehasonlitasok |

> **Forras**: https://devopedia.org/exploratory-data-analysis

---

## Gyakorlati Utmutato

### EDA Checklist

- [ ] Kommunikacio a domen szakertokkel (az adatok es a szakterulet megertese)
- [ ] Kommunikacio az adatgyujto mernokokkel (hogyan, honnan, mikor gyujtottek)
- [ ] Adatok betoltese es elso beleintezet (`df.head()`, `df.shape`)
- [ ] Adattuipusok ellenorzese (`df.info()`, `df.dtypes`)
- [ ] Alapveto statisztikak (`df.describe()`)
- [ ] Hianyzo ertekek felmerese (`df.isnull().sum()`)
- [ ] Duplikalt sorok ellenorzese (`df.duplicated().sum()`)
- [ ] Kategorikus valtozok ertekeloszlasa (`df['col'].value_counts()`)
- [ ] Univariate vizualizaciok (hisztogramok, count plotok)
- [ ] Bivariate vizualizaciok (scatter plotok, box plotok)
- [ ] Korrelacios matrix es heatmap
- [ ] Multivariate elemzes (pair plot)
- [ ] Outlierek azonositasa
- [ ] Adatminosegi szempontok vegigvezetese (12 dimenzio)
- [ ] Automatizalt EDA report generalas (YData Profiling, Sweetviz)
- [ ] Riport keszitese a donteshozok szamara
- [ ] Domenszakertokkeli konzultaciio az eredmenyekrol

### Lepesrol lepesre

#### 1. lepes: Adatok betoltese es elso attekintes

```python
import pandas as pd
import numpy as np

# Adat betoltese
df = pd.read_csv("data/horse-colic.data", header=None, delim_whitespace=True)

# Elso beleintes
print(f"Adathalmaz merete: {df.shape[0]} sor, {df.shape[1]} oszlop")
print(f"\nElso 5 sor:")
df.head()
```

#### 2. lepes: Adattisztitas es elokeszites

```python
# Hianyzo ertekek jelolese egyseges formara
df = df.replace('?', np.nan)

# Oszlopnevek beallitasa a dokumentacio szerint
list_column_names = ["V" + str(i) for i in range(1, 29)]
df.columns = list_column_names

# Adattipusok ellenorzese
print(df.dtypes)
print(f"\nHianyzo ertekek szama oszloponkent:")
print(df.isnull().sum())
print(f"\nHianyzo ertekek aranya: {df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100:.1f}%")
```

#### 3. lepes: Statisztikai osszefoglalo

```python
# Numerikus oszlopok statisztikaja
print(df.describe())

# Kategorikus oszlopok ertekeloszlasa
for col in df.columns:
    if df[col].nunique() < 10:
        print(f"\n{col} ertekeloszlasa:")
        print(df[col].value_counts())
```

#### 4. lepes: Vizualizaciok keszitese

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Hisztogramok az osszes numerikus valtozora
numeric_df = df.apply(pd.to_numeric, errors='coerce')
numeric_df.hist(bins=20, figsize=(16, 12), edgecolor='black')
plt.suptitle('Osszes numerikus valtozo eloszlasa', fontsize=16)
plt.tight_layout()
plt.show()

# Korrelacios matrix
plt.figure(figsize=(14, 10))
corr = numeric_df.corr()
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0)
plt.title('Korrelacios matrix')
plt.tight_layout()
plt.show()

# Hianyzo ertekek vizualizacioja
plt.figure(figsize=(14, 6))
df.isnull().sum().plot(kind='bar', color='coral')
plt.title('Hianyzo ertekek szama oszloponkent')
plt.xlabel('Oszlop')
plt.ylabel('Hianyzo ertekek szama')
plt.tight_layout()
plt.show()
```

#### 5. lepes: Automatizalt EDA riportok

```python
# YData Profiling (korabban pandas-profiling)
# pip install ydata-profiling
from ydata_profiling import ProfileReport

report = ProfileReport(df, title='Lo Kolika Adathalmaz - EDA Riport')
report.to_file("EDA_report/ydata_report.html")

# Sweetviz
# pip install sweetviz
import sweetviz as sv

report_sv = sv.analyze(df)
report_sv.show_html('EDA_report/sweetviz_report.html')
```

#### 6. lepes: Target valtozo kapcsolatainak vizsgalata

```python
# A prediktalando valtozo (V24) korrelacioja a tobbi valtozoval
target_corr = numeric_df.corr()['V24'].sort_values(ascending=False)
print("Korrelaciok a V24 (target) valtozoval:")
print(target_corr)

# A legerosebb korrelaaciok vizualizalasa
plt.figure(figsize=(10, 6))
target_corr.drop('V24').plot(kind='barh', color='steelblue')
plt.title('Oszlopok korrelacioja a V24 (target) valtozoval')
plt.xlabel('Pearson korrelacios egyutthato')
plt.tight_layout()
plt.show()
```

> A reszletes kod peldak megtalaalhatoak: [_kod_peldak/eda_peldak.py](_kod_peldak/eda_peldak.py)

---

## Osszehasonlito Tablazat

| Vizualizacio | Mikor hasznald | Adat tipus | Seaborn/Matplotlib fuggveny |
|---|---|---|---|
| **Hisztogram** | Egyetlen folytonos valtozo eloszlasa | Folytonos | `sns.histplot()` / `plt.hist()` |
| **KDE plot** | Simittott eloszlas-becsles | Folytonos | `sns.kdeplot()` |
| **Count plot** | Kategorikus valtozo gyakorisaga | Kategorikus | `sns.countplot()` |
| **Bar chart** | Kategoriak osszehasonlitasa | Kategorikus | `df.plot(kind='bar')` / `sns.barplot()` |
| **Box plot** | Eloszlas, kvartilisek, outlierek | Folytonos (+ kategorikus csoportositas) | `sns.boxplot()` |
| **Violin plot** | Reszletes eloszlas + boxplot | Folytonos (+ kategorikus csoportositas) | `sns.violinplot()` |
| **Scatter plot** | Ket folytonos valtozo kapcsolata | Folytonos vs. Folytonos | `plt.scatter()` / `sns.scatterplot()` |
| **Pair plot** | Tobb valtozo paroonkenti osszehasonlitasa | Folytonos (+ hue kategorikus) | `sns.pairplot()` |
| **Heatmap** | Korrelaciios matrix vizualizalasa | Numerikus | `sns.heatmap()` |
| **Vonaldiagram** | Idosorok, trendek | Idofuggo | `plt.plot()` / `sns.lineplot()` |
| **Hexbin plot** | Nagy adathalmaz suuruuseg-abraja | Folytonos vs. Folytonos | `plt.hexbin()` |
| **Pie chart** | Resz-egesz aranyok | Kategorikus | `df.plot.pie()` / `plt.pie()` |
| **Area plot** | Resz-egesz aranyok idosorban | Idofuggo + kategorikus | `df.plot.area()` |

---

## Gyakori Hibak es Tippek

### Hibak, amiket kerulj el

1. **Rogtoon modellezni kezdesz az adatok megertese nelkul**
   - Mindig szanj idot az EDA-ra, meg ha surget is a projekt
   - "Az adat a nyers anyag" -- alaposan meg kell vizsgalni

2. **Nem kommunikalsz a domen szakertokkel**
   - A legertekesebb insightok gyakran a domenismeretbol szarmaznak
   - Ne legyel szegyenlos: kerdezz, tanulj toluk

3. **Automatizalt EDA riportokra tamaszkodsz kizarolag**
   - Az YData Profiling es Sweetviz jo kiindulasi pont, de nem elegseges
   - Keszits sajat elemzeseket, vizualizaciokat is
   - Az automatizalt eszkozok nem mindig talalljak el az oszlopok tipusat

4. **Nem ellenorzod az adattipusokat**
   - Kategoriavaltozo es folytonos valtozo kezelese alapvetoen kulonbozik
   - Keszits sajat listat az oszlopok tipusarol

5. **Figyelmen kivul hagyod a hianyzoi ertekeket**
   - Mindig vizsgald meg, hol es mennyire hianyoznak adatok
   - Ez befolyasolja a modellezesi strategiat

6. **Nem figyelsz a production kornyezetre**
   - Availability: ami tanultaskor elerheto, production-ben lehet, hogy nem lesz az
   - Latency: predikcios idoben az adat-elerheteoseg kritikus lehet

### Hasznos tippek

- **Mindig ellenorizd a licenszt** publikus adathalmaz hasznalatanal
- **Keszits riportokat** a felfedezesek dokumentalasahoz (Data Collection Report, Data Description Report, Data Exploration Report, Data Quality Report)
- **Hasznald a `value_counts()` fuggvenyt** kategorikus valtozok gyors attekintesere
- **A `describe()` nem az osszes oszlopra fut**: ha string tipusu az oszlop, nem jelenik meg -- konvertalj elobb numerikusra
- **Pair plotnal figyelj** a sziinek eltakarasara suru adathalmaznal
- **Tartsd szem elott az uzleti celt** az elemzes soran: mely oszlopok lehetnek a legfontosabbak a predikciohoz
- **Oszlopnevek**: Ha az eredeti adatban nincsenek oszlopnevek, rendeld hozza a dokumentacio alapjan, hogy kovethetoo legyen az elemzes

```python
# Pelda: oszlopnevek hozzarendelese
list_column_names = ["V" + str(i) for i in range(1, 29)]
df.columns = list_column_names
```

---

## Kapcsolodo Temak

- [04_adatelokeszites_es_feature_engineering.md](04_adatelokeszites_es_feature_engineering.md) -- Az adatmegertes utan kovetkezo lepes: adattisztitas, feature-ok letrehozasa
- [02_fejlesztoi_kornyezet_es_pandas.md](02_fejlesztoi_kornyezet_es_pandas.md) -- A Python/Pandas kornyezet, amely az EDA alapeszkoze

---

## Tovabbi Forrasok

### Hasznalt Python csomagok
- **pandas**: Adatkezeles es alapveto statisztikak (`pip install pandas`)
- **numpy**: Numerikus muveletek (`pip install numpy`)
- **matplotlib**: Alapveto vizualizaciok (`pip install matplotlib`)
- **seaborn**: Statisztikai vizualizaciok (`pip install seaborn`)
- **ydata-profiling**: Automatizalt EDA riportok (`pip install ydata-profiling`)
- **sweetviz**: Automatizalt EDA riportok (`pip install sweetviz`)

### Pelda adathalmaz
- **Horse Colic Dataset**: [https://archive.ics.uci.edu/dataset/47/horse+colic](https://archive.ics.uci.edu/dataset/47/horse+colic)
  - 368 sor, 28 attributum
  - Osztaályozasi feladat (target: V24 -- sebeszeti lezio szuksegessege)
  - ~30% hianyzo adat
  - Biologia / allatgyogyaszat domen

### Ajanlott olvasmannyok
- Pandas dokumentaciio: [https://pandas.pydata.org/docs/](https://pandas.pydata.org/docs/)
- Seaborn tutorial: [https://seaborn.pydata.org/tutorial.html](https://seaborn.pydata.org/tutorial.html)
- Matplotlib tutorial: [https://matplotlib.org/stable/tutorials/](https://matplotlib.org/stable/tutorials/)

### Hivatkozasok a PDF prezentaciobol
- 11 Essential Plots That Data Scientists Use 95% of the Time: [https://ai.plainenglish.io/11-essential-plots-that-data-scientists-use-95-of-the-time-bfc967e76791](https://ai.plainenglish.io/11-essential-plots-that-data-scientists-use-95-of-the-time-bfc967e76791)
- CRISP-DM Phase 2 - Data Understanding: [https://medium.com/analytics-vidhya/crisp-dm-phase-2-data-understanding-b4d627ba6b45](https://medium.com/analytics-vidhya/crisp-dm-phase-2-data-understanding-b4d627ba6b45)
- Semi-Automated EDA Process in Python: [https://www.visual-design.net/post/semi-automated-exploratory-data-analysis-process-in-python](https://www.visual-design.net/post/semi-automated-exploratory-data-analysis-process-in-python)
- 5 Advanced Visualisation for EDA: [https://towardsdatascience.com/5-advanced-visualisation-for-exploratory-data-analysis-eda-c8eafeb0b8cb](https://towardsdatascience.com/5-advanced-visualisation-for-exploratory-data-analysis-eda-c8eafeb0b8cb)
- Exploratory Data Analysis (Devopedia): [https://devopedia.org/exploratory-data-analysis](https://devopedia.org/exploratory-data-analysis)
- Seaborn Countplot: [https://seaborn.pydata.org/generated/seaborn.countplot.html](https://seaborn.pydata.org/generated/seaborn.countplot.html)
- Seaborn Boxplot: [https://seaborn.pydata.org/generated/seaborn.boxplot.html](https://seaborn.pydata.org/generated/seaborn.boxplot.html)

---

## Kepjegyzek

| Abra | Leiras | Forras dia |
|---|---|---|
| 1. abra | CRISP-DM Data Understanding fazis a 4 fo feladattal es a `pd.describe()` pelda kimenettel | slide_03.png |
| 2. abra | EDA Cheatsheet -- a felderto elemzes harom fo pillere (nem grafikus, egyvaltozos, tobbvaltozos elemzes) a Python fuggvenyekkel | slide_05.png |
| 3. abra | Titanic countplot -- utazasi osztaly vs. tuleles kategorikus osszehasonlitasa oszlopdiagramon | slide_06.png |
| 4. abra | Titanic boxplot -- eletkor eloszlasa utazasi osztaly es tuleles szerinti bontasban, outlierekkel | slide_07.png |
| 5. abra | Palmer Penguins pairplot -- 4 numerikus valtozo paronkenti osszehasonlitasa sziget szerinti szinezessel | slide_08.png |
| 6. abra | Data Visualization attekintes -- a 11 leggyakrabban hasznalt diagramtipus vizualis mezosonye | slide_09.png |
| 7. abra | Bovitett vizualizacios katalogus -- 15 halado diagramtipus (Dot Plot, Radar, Waterfall, stb.) | slide_10.png |

---

*Forras: Cubix EDU ML Engineering kurzus -- 3. het: Adatmegertes es EDA (03_01, 03_02, 03_03, 03_10, 03_11 videok, Jupyter notebook es "2 Data understanding.pdf" prezentacio)*
