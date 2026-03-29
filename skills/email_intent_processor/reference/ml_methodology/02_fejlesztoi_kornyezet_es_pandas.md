# Fejlesztoi Kornyezet es Pandas

## Gyors Attekintes

> A gepi tanulas fejlesztesehez elengedhetetlen a megfelelo fejlesztoi kornyezet es eszkoztar ismerete. Ez a fejezet bemutatja a legfontosabb ML fejlesztesi eszkozoket (Jupyter Notebook, Google Colab, VS Code, PyCharm), a felhoalapu platformok elonyeit, valamint reszletesen targyalja a Pandas konyvtarat, amely az adatfeldolgozas es adatelemzes alapveto eszkoze a Python okoszisztemaban. A Pandas-ra szuksegunk lesz egesz gepi tanulas fejlesztoi karrierunk soran.

---

## Kulcsfogalmak

- **Pandas**: Nyilt forraskodu Python konyvtar adatmanipulaciora es elemzesre, kulonosen tablazatos adatok kezelesehez. Importalasi konvencio: `import pandas as pd`.
- **DataFrame**: Ket dimenzios, tablazatos adatstruktura a Pandasban, amely sorokbol es oszlopokbol all -- hasonlo egy Excel tablazathoz vagy SQL tablahoz.
- **Series**: Egy dimenzios adatstruktura a Pandasban, egyetlen adatoszlopot vagy adatsort reprezental.
- **MultiIndex**: Tobbszintu indexeles, amely hierarchikus indexek hasznalatat teszi lehetove DataFrame-ekben.
- **Jupyter Notebook**: Interaktiv kornyezet, ahol kod, szoveg es vizualizaciok egyutt kezelhetok -- kulonosen hasznos Data Science es ML fejleszteshez.
- **Google Colab**: A Google felhoalapu Jupyter notebook szolgaltatasa, beepitett GPU/TPU tamogatassal.
- **Runtime**: A Colab altal biztositott futtatokornyezet, amelyhez hardver eroforrasok (CPU, GPU, TPU, memoria) tartoznak.
- **MLOps**: A gepi tanulasi modellek fejlesztesenek, telepitesenek es uzemeltetesenek folyamata es eszkozei.
- **PKL (Pickle)**: Python pickle formatumu fajl, amelyben gyorsan es hatekonyan lehet Pandas adatokat tarolni es betolteni.
- **Scikit-Learn (SK-Learn)**: Bevalt Python konyvtar gepi tanulasi algoritmusok implementalasara es kiertekelere.
- **TensorFlow**: Google altal fejlesztett keretrendszer neuralishalo-fejleszteshez; a Keras magas szintu API-ja ra epul.
- **PyTorch**: Facebook altal fejlesztett Deep Learning keretrendszer, az utolso evekben ipari szabvanynya valt.
- **Docker**: Kontenerizacios platform, amely hordozhatova es konnyedden telepithetove teszi a rendszereket.

---

## ML Fejlesztesi Eszkozok es Kornyezetek

### Python csomagok es keretrendszerek

A Machine Learning fejlesztes soran a kovetkezo eszkozok a leggyakrabban hasznaltak:

| Eszkoz | Felhasznalasi terulet |
|--------|----------------------|
| **Pandas** | Adatelofeldolgozas, adatfeldrites, adattranszformacio |
| **NumPy** | Numerikus szamitasok, tombkezeles, adattranszformacio |
| **Scikit-Learn** | Klasszikus ML algoritmusok, modellkiertekeles |
| **TensorFlow + Keras** | Deep Learning, neuralis halok (uzleti alkalmazasok) |
| **PyTorch** | Deep Learning (kutatas es ipar -- mostanra ipari szabvany) |
| **NLTK** | Termeszetes nyelvfeldolgozas (NLP) |
| **Spark** | Big Data feldolgozas, elosztott szamitas |
| **MXNet** | Deep Learning fejlesztes |

**Fontos trend**: A PyTorch az utolso evekben valt ipari szabvannya, mert gyorsan alkalmazkodik az uj kutatasi eredmenyekhez. A TensorFlow tamogatottsaga csokkeno tendenciat mutat. A Keras mindket konyvtar folott magasabb absztrakciot biztosit.

### Low-code es no-code megoldasok

- Gyors prototipizalasra es proof of concept (POC) keszitesre hasznalhatoak
- A PyCaret kiemelt low-code eszkoz: nehany sornyi koddal kiprobalhatok kulonbozo ML algoritmusok
- Nagy cegek (Amazon, Microsoft, Google) biztositanak no-code megoldasokat (altalaban fizetosek)
- **Fontos**: Ne kenyelmesedjunk el -- a megfelelo konfiguracio es a mukodes megertes elengedhetetlen

### MLOps eszkozok

- **MLflow**: Kiserletkovetes (experiment tracking) -- minden kiprobalt modellt, eredmenyt, hiperparametert elment
- **Flask / FastAPI**: REST API-k letrehozasa a kesz modell kitelepitesehez
- **Streamlit / Grafana**: Dashboardok es monitorizalas eles kornyezetben
- **Docker**: Kontenerizacio -- a teljes rendszer hordozhatova valik, OS-fuggetlen telepites

### Jupyter Notebook / JupyterLab

A Jupyter notebook a Data Science es ML fejlesztes egyik legfontosabb eszkoze:

- **Kod, kepek es abrak egyutt** -- kiemeledoen fontos adatexploracio es vizualizacio soran
- **Memoriaban tart adat** -- nem kell ujra betolteni nagy adatokat minden futtataskor
- **Exportalhato** HTML vagy PDF formatumba (prezentaciokhoz is kivalo)
- A cellak kozott **szoveges** (Markdown) es **kod** cellak valtakozhatnak
- A futtas eredmenyei elmentodnek a notebookba

### IDE-k (VS Code, PyCharm)

- **VS Code**: Microsoft altal fejlesztett, nepszeru, altalanosabb fejlesztoi kornyezet
  - Tamogatja a Jupyter notebookokat
  - Kimerithetetlenul bovitheto pluginokkal
- **PyCharm**: JetBrains altal fejlesztett, Python-specifikus IDE
  - Beepitett debugolas, refaktoralas
  - Szinten tamogatja a notebookokat
- A valasztas szemelyes preferencia kerdese -- mindketto kiemeledoen jo
- A **terminal** hasznalata is elengedhetetlen, kulonosen production kornyezetben

### Felhoplatformok

A harom fo cloud szolgaltato ML szempontbol:

| Platform | Notebook szolgaltatas | ML szolgaltatasok |
|----------|----------------------|-------------------|
| **Google Cloud** | Google Colab, Vertex AI | AutoML, Vertex AI |
| **Microsoft Azure** | Azure Notebooks | Azure ML Studio |
| **Amazon AWS** | SageMaker Notebooks | SageMaker |

**Mikor erdemes cloud-ot hasznalni?**
- Rugalmasan berelheto hardver -- idoszakos hasznalat eseten koltseghatekonyabb, mint sajat szerver
- Specialis hardver (GPU/TPU) szukseges Deep Learninghez
- Az adatbazisok is a cloudban lehetnek -- gyorsabb adateleres

**Mikor NE hasznaljunk cloud-ot (pl. Colab-ot)?**
- Erzekeny adatokkal valo napi munkara nem ajanlott
- Jogi megfeleleoseg (GDPR, AI Act) betartasa kotelezo
- On-premise megoldas lehet szukseges szabalyozott iparakban

---

## Google Colab Reszletes Utmutato

### Inditas es alapok

A Google Colab egy felhoalapu Jupyter notebook kornyezet, amely bongeszoboel hasznalhato:

1. Navigalj a [colab.research.google.com](https://colab.research.google.com) oldalra
2. Hozz letre uj notebook-ot, vagy nyiss meg egy meglevet Google Drive-rol

**Cellatipusok:**
- **Kod cella**: Python kod irasa es futtatasa (`+ Code` gomb)
- **Szoveg cella**: Markdown formatumban iras (`+ Text` gomb)
- Cellak mozgathatoak fel-le, torolhetok, tobbszoros kivalasztas is lehetseges

**Strukturalas:**
- `# Cim` (egy hastag) -- legmagasabb szintu cim, osszecsukva mindent elrejt alatta
- `## Alcim` (ket hastag) -- blokkot jelol, osszecsukva az adott blokk cellakit rejti el
- Ez lehetove teszi a notebook attekintheto strukturalasat

### GPU/TPU hasznalat

A runtime tipus beallitasa: **Runtime > Change Runtime Type**

| Hardver | Leiras |
|---------|--------|
| CPU | Alapertelmezett, kisebb feladatokhoz |
| T4 GPU | Joviszonyban aru GPU, altalanos Deep Learning feladatokhoz |
| V100 GPU | Erosebb GPU, nagyobb modellekhez |
| A100 GPU | Legdragabb, legerosebb GPU -- 40 GB GPU RAM |
| TPU v2 | Google altal fejlesztett specialis chip ML-hez |

- **High RAM** opcio: bekapcsolva akar 51-83 GB RAM is elerheto
- A GPU RAM (pl. A100: 40 GB) kulon a rendszermemoria mellett

### Fajlkezeles, Google Drive integracio

- Bal oldalon **mappa ikon** -- az aktualis session fajlrendszere latszik
- **Google Drive csatlakoztatasa**: a sajat fajlok kozvetlenul elerhetoek a Colab-bol
- **Secrets** tab: API kulcsok tarolasa (pl. Kaggle, OpenAI)
- Terminal is elerheto a Colab-ban

### Elofizeesi szintek

| Csomag | Ar | Szamitasi egyseg | Fo jellemzok |
|--------|-----|-------------------|--------------|
| **Ingyenes** | $0 | Korlatozott | Alap CPU/GPU, korlatozott RAM |
| **Pay As You Go** | $10/egyszeri | 100 egyseg | Nincs elofizetes, rugalmas |
| **Colab Pro** | $10/ho | 100 egyseg/ho | Gyorsabb GPU, tobb memoria, terminal, AI kod-tamogatas |
| **Colab Pro+** | $25/ho | 500 egyseg/ho | + hatterben futo szamitasok (24h), prioriatsos GPU |
| **Colab Enterprise** | Egyedi | Egyedi | Google Cloud integracio (BigQuery, Vertex AI) |

**Szamitasi egysegek fogyasztasa (pelda):**
- Alap notebook (CPU): ~0,07 egyseg/ora
- A100 GPU + High RAM: ~11,84 egyseg/ora
- **90 nap utan lejarnak** a fel nem hasznalt egysegek

**Hatterben futo szamitasok** (Pro+ es felette):
- A bongeszo bezarhato, a gep kikapcsolhato
- A szamitasok tovabb futnak max. 24 oran keresztul

---

## Pandas Alapok

### Telepites es importalas

```python
# Telepites (ha szukseges)
pip install pandas

# Importalas (standard konvencio)
import pandas as pd
```

### Series letrehozas

A Series egy dimenzios adatstruktura -- egyetlen oszlop adatot tartalmaz:

```python
# Egyszeru Series letrehozasa listabol
s = pd.Series([1, 3, 5])
# Eredmeny:
# 0    1
# 1    3
# 2    5
# dtype: int64
```

### DataFrame letrehozas

A DataFrame ket dimenzios, tablazatos adatstruktura. Tobb modon is letrehozhatjuk:

**1. mod: Dictionary-bol (kulcsok = oszlopnevek)**
```python
data_dict = {
    'A': [1, 2, 3],
    'B': [4, 5, 6],
    'C': [7, 8, 9]
}
df = pd.DataFrame(data_dict)
#    A  B  C
# 0  1  4  7
# 1  2  5  8
# 2  3  6  9
```

**2. mod: Dictionary-k listajabol (minden dict egy sor)**
```python
data_list = [
    {'A': 1, 'B': 4, 'C': 7},
    {'A': 2, 'B': 5, 'C': 8},
    {'A': 3, 'B': 6, 'C': 9}
]
df = pd.DataFrame(data_list)
```

**3. mod: Listak listajabol oszlopnevekkel**
```python
data = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
columns = ['A', 'B', 'C']
df = pd.DataFrame(data, columns=columns)
```

**4. mod: Ures DataFrame (kesobbi feltolteshez)**
```python
empty_df = pd.DataFrame(columns=['A', 'B', 'C'])
```

**5. mod: MultiIndex-szel (tobbszintu indexeles)**
```python
index = pd.MultiIndex.from_tuples(
    [('a', 1), ('a', 2), ('b', 1), ('b', 2)],
    names=['first', 'second']
)
df_multi = pd.DataFrame(
    {'A': [1, 2, 3, 4], 'B': [5, 6, 7, 8]},
    index=index
)
#               A  B
# first second
# a     1       1  5
#       2       2  6
# b     1       3  7
#       2       4  8
```

### Adatbeolvasas (CSV, Excel, JSON, Pickle)

```python
# CSV fajlbol
df = pd.read_csv('adatok.csv')

# Excel fajlbol
df = pd.read_excel('adatok.xlsx')

# JSON fajlbol
df = pd.read_json('adatok.json')

# Pickle (PKL) fajlbol -- leggyorsabb!
df = pd.read_pickle('adatok.pkl')
```

**Gyakorlati tipp**: Az adatokat elofeldolgozas utan erdemes PKL fajlba menteni (`df.to_pickle('adatok.pkl')`), mert a Pandas ezt a formatumot nagyon gyorsan tudja olvasni. Igy nem kell mindig ujra importalni es elofeldolgozni az adatokat.

### Alap muveletek (head, tail, info, describe, shape, columns)

A Titanic dataset peldajan (Seaborn konyvtarbol):

```python
import seaborn as sns
df = sns.load_dataset('titanic')

# Elerheto dataset-ek listazasa
sns.get_dataset_names()

# Oszlopnevek lekerdezese
df.columns
# Index(['survived', 'pclass', 'sex', 'age', 'sibsp', 'parch', 'fare',
#        'embarked', 'class', 'who', 'adult_male', 'deck', 'embark_town',
#        'alive', 'alone'], dtype='object')

# Elso 5 sor megtekintese (alapertek)
df.head()

# Elso N sor megtekintese
df.head(50)  # max 50 sort jelenit meg

# Utolso 5 sor
df.tail()

# Statisztikai osszefoglalas (csak numerikus oszlopok!)
df.describe()
# Visszaadja: count, mean, std, min, 25%, 50%, 75%, max
```

**`describe()` kimenet ertelmezese:**

| Metrika | Jelentes |
|---------|---------|
| count | Nem hianyzo ertekek szama |
| mean | Atlag |
| std | Szoras (standard deviation) |
| min | Minimum ertek |
| 25% | Elso kvartilis (25. percentilis) |
| 50% | Median (50. percentilis) |
| 75% | Harmadik kvartilis (75. percentilis) |
| max | Maximum ertek |

**Fontos**: A `describe()` csak a numerikus oszlopokat mutatja -- a nem numerikus oszlopokra (pl. "sex", "embarked") nem lehet ilyen szamitasokat vegezni.

### Egy oszlop kivalasztasa

```python
# Egyetlen oszlop (Series-t ad vissza)
df["sex"]

# Tobb oszlop (DataFrame-et ad vissza)
df_subset = df[['class', 'sex', 'age', 'fare']]
```

### Indexeles es szures (loc, iloc, boolean indexing)

**`iloc` -- pozicio (szam) alapu indexeles:**
```python
# Elso sor
df.iloc[0]

# Elso 10 sor
df.iloc[0:10]

# 10. sortol az osszes
df.iloc[10:]

# 50. sortol a 100.-ig
df.iloc[50:100]
```

**`loc` -- cimke vagy logikai feltetel alapu szures:**
```python
# Egyszeru szures: 30 evnel fiatalabbak
df.loc[df["age"] < 30]

# Tobb feltetel (zarojelezni kell!):
df.loc[(df["age"] < 30) & (df["class"] == "Third")]

# VAGY kapcsolat:
df.loc[(df["age"] < 30) | (df["class"] == "First")]
```

**Fontos**: Tobb feltetel eseten minden egyes felteltelt kulon zarojelbe kell tenni, es `&` (AND) vagy `|` (OR) operatorokat kell hasznalni (nem `and`/`or`).

### Oszlopok kezelese

```python
# Oszlop torlese
df.drop(columns=["age"])

# Sorok torlese index alapjan
df.drop(index=[0, 1])

# Uj oszlop letrehozasa
df["new_column"] = df["age"] * 2
```

### Alap statisztikai fuggvenyek

```python
print(df["age"].median())   # 28.0
print(df["age"].mean())     # 29.699
print(df["age"].min())      # 0.42
print(df["age"].max())      # 80.0
print(df["age"].sum())      # 21205.17
```

---

## Pandas Halado

### Rendezes (sort_values)

```python
# Rendezes eletkor szerint (novekvo)
df.sort_values("age").head(50)

# Csokkeno sorrend
df.sort_values("age", ascending=False)
```

### GroupBy muveletek

A `groupby` csoportositja az adatokat egy vagy tobb oszlop alapjan, majd aggregacios fuggvenyeket alkalmaz:

```python
# Osztalyonkenti atlagok
df.groupby(by="class").mean()
#         survived  pclass        age      fare
# First   0.629630     1.0  38.233441  84.154687
# Second  0.472826     2.0  29.877630  20.662183
# Third   0.242363     3.0  25.140620  13.675550
```

Ezt a tablazatbol leolvashatjuk, hogy az elso osztalyon utazoknak volt a legmagasabb a tulelesi arany (63%), a legmagasabb atlageletkor (38 ev) es a legmagasabb atlagos jegyar ($84).

### Merge, Join, Concat

**`concat` -- DataFrame-ek osszefuzese:**
```python
# Sorok menten (axis=0, alapertek)
pd.concat([df.iloc[100:], df.iloc[:100]])

# Oszlopok menten
pd.concat([df1, df2], axis=1)

# Index ujraszamozasa osszefuzes utan
pd.concat([df1, df2]).reset_index(drop=True)
```

A `reset_index(drop=True)` parameter biztositja, hogy az eredeti indexek ne keruljenek be uj oszlopkent.

**`merge` -- SQL-szeru JOIN:**
```python
# Ket DataFrame egyesitese kozos oszlop alapjan
result = pd.merge(df1, df2, on='key_column', how='inner')
# how parameterek: 'inner', 'outer', 'left', 'right'
```

### Pivot tablak es adataalakit

**Wide to Long (melt):**
```python
df_subset = df[['class', 'sex', 'age', 'fare']]
long_df = pd.melt(df_subset, id_vars=['class', 'sex'], value_vars=['age', 'fare'])
# Az 'age' es 'fare' oszlopok ertekei kulon sorokba kerulnek
```

**Long to Wide (pivot_table):**
```python
wide_df = long_df.pivot_table(
    index=['class', 'sex'],
    columns='variable',
    values='value',
    aggfunc='mean'
)
# Eredmeny:
#                        age        fare
# class  sex
# First  female  34.611765  106.125798
#        male    41.281386   67.226127
# Second female  28.722973   21.970121
#        male    30.740707   19.741782
# Third  female  21.750000   16.118810
#        male    26.507589   12.661633
```

**Transpose (sorok es oszlopok felcserelese):**
```python
transposed_df = df_subset.head().T
#            0        1       2       3      4
# class  Third    First   Third   First  Third
# sex     male   female  female  female   male
# age     22.0     38.0    26.0    35.0   35.0
# fare    7.25  71.2833   7.925    53.1   8.05
```

### Apply es Lambda fuggvenyek

```python
# Lambda fuggveny alkalmazasa egy oszlopra
df["age_group"] = df["age"].apply(lambda x: "fiatal" if x < 30 else "idosebb")

# Sajat fuggveny alkalmazasa
def kategorializal(ertek):
    if ertek < 18:
        return "gyerek"
    elif ertek < 60:
        return "felnott"
    else:
        return "idos"

df["korosztaly"] = df["age"].apply(kategorializal)
```

### Hianyzo ertekek kezelese (NaN)

A Titanic dataset-ben is vannak hianyzo ertekek (pl. az `age` es `deck` oszlopokban):

```python
# Hianyzo ertekeket tartalmazo sorok torlese
df_clean = df.dropna()

# Csak adott oszlopbol hianyzo sorok torlese
df_clean = df.dropna(subset=["age"])

# Hianyzo ertekek kitoltese
df["age"].fillna(df["age"].median(), inplace=True)  # mediannal
df["deck"].fillna("Unknown", inplace=True)           # fix ertekkel
```

### Datumkezeles

```python
# Idosor-eltolas (shift)
df["previous_value"] = df["value"].shift(1)   # 1 pozicioval eltolva
df["next_value"] = df["value"].shift(-1)      # 1 pozicioval elore
```

### Egyeb hasznos muveletek

```python
# Kategoria-elofordulas szamlalasa
df["class"].value_counts()

# Duplikaciok eltavolitasa
df.drop_duplicates()

# Oszlopok atnevezese
df.rename(columns={"age": "eletkor", "fare": "jegyar"})

# Ertekek csereje
df["sex"].replace({"male": "ferfi", "female": "no"})
```

---

## Adatvizualizacio Pandas-szal

A Pandas beepitett plotolasi lehetosegei meglepoen sokfeleek:

```python
# Hisztogram (eloszlas vizualizalasa)
df["age"].hist(bins=20)

# Alternativ szintaxis
df["age"].plot.hist(bins=20)

# Rendezett adat plotolasa
df.sort_values(by="age")["age"].reset_index(drop=True).plot()

# Elerheto plot tipusok:
# - area plot
# - hisztogram
# - box plot
# - scatter plot
# - torta diagram (pie chart)
# - vonaldiagram (line plot)

# Abra testreszabasa
df["age"].plot.hist(bins=20, title="Eletkor eloszlas", xlabel="Eletkor", ylabel="Gyakorisag")
```

**Tipp**: Erdemes hasznalni a Pandas beepitett plotolasi lehetosegeit gyors adatvizualizaciohoz -- nem kell mindig kulon Matplotlib-et vagy Seaborn-t importalni.

---

## Gyakorlati Utmutato

### Tipikus Pandas workflow

1. **Adat betoltese**: `pd.read_csv()`, `pd.read_excel()`, `pd.read_pickle()` vagy mas forrasbol
2. **Elso attekintes**: `df.head()`, `df.shape`, `df.info()`, `df.describe()`
3. **Oszlopok vizsgalata**: `df.columns`, `df.dtypes`, `df["oszlop"].value_counts()`
4. **Hianyzo ertekek kezelese**: `df.isnull().sum()`, `df.dropna()` vagy `df.fillna()`
5. **Szures es kivalasztas**: `df.loc[...]`, `df.iloc[...]`, boolean indexing
6. **Transzformacio**: `groupby()`, `merge()`, `pivot_table()`, `apply()`
7. **Vizualizacio**: `df.plot()`, `df.hist()`, `df["col"].plot.bar()`
8. **Mentes**: `df.to_pickle()`, `df.to_csv()`, `df.to_excel()`

### Teljes pelda: Titanic dataset elemzes

```python
import pandas as pd
import seaborn as sns

# 1. Adat betoltese
df = sns.load_dataset('titanic')

# 2. Elso attekintes
print(f"Merete: {df.shape}")          # (891, 15)
print(f"Oszlopok: {df.columns.tolist()}")
df.describe()

# 3. Hianyzo ertekek
print(df.isnull().sum())

# 4. Szures: 30 evnel fiatalabb, harmadosztaly
fiatal_3_osztalyu = df.loc[
    (df["age"] < 30) & (df["class"] == "Third")
]

# 5. Csoportositas: tulelesi arany osztalyonkent
tuleles = df.groupby("class")["survived"].mean()
print(tuleles)

# 6. Pivot tabla: atlag eletkor es jegyar osztalyonkent es nemenent
pivot = df.pivot_table(
    index=['class', 'sex'],
    values=['age', 'fare'],
    aggfunc='mean'
)
print(pivot)

# 7. Vizualizacio
df["age"].hist(bins=20)

# 8. Mentes
df.to_pickle('titanic_feldolgozott.pkl')
```

### Kod peldak

A reszletes, futtatthato kodpeldak elerhetek:
- Jupyter notebook: `Cubix_ML_Engineer_Pandas.ipynb` (Colab notebook a kurzusbol)
- Pandas Cheat Sheet: [https://pandas.pydata.org/Pandas_Cheat_Sheet.pdf](https://pandas.pydata.org/Pandas_Cheat_Sheet.pdf)

---

## Gyakori Hibak es Tippek

### Pandas gotchas (gyakori buktatok)

1. **Boolean szures zarojelezese**: Tobb feltetel eseten minden felteltelt kulon zarojelbe KELL tenni:
   ```python
   # HELYES:
   df.loc[(df["age"] < 30) & (df["class"] == "Third")]

   # HELYTELEN (hibat dob):
   df.loc[df["age"] < 30 & df["class"] == "Third"]
   ```

2. **`and`/`or` vs `&`/`|`**: DataFrame szuresben `&` es `|` operatorokat kell hasznalni, NEM `and`/`or`-t.

3. **`describe()` nem mutat mindent**: Csak numerikus oszlopokat jeleniti meg. Nem numerikus oszlopokhoz hasznalj `df.describe(include='all')`-t.

4. **Index kavarodas `concat` utan**: Osszefuzes utan az indexek megmaradnak az eredeti DataFrame-ekbol. Hasznalj `reset_index(drop=True)`-t.

5. **`head()` korlat**: A Pandas alapertelezetten legfeljebb kb. 50 sort jelenit meg -- nagyobb adathalmazoknal ez nem latszik teljesen.

6. **SettingWithCopyWarning**: Ha egy szelet (slice) DataFrame-en modositasz, hasznalj `.copy()`-t:
   ```python
   df_subset = df[df["age"] < 30].copy()
   df_subset["new_col"] = 1  # Igy nincs warning
   ```

### LIVE alkalom Q&A -- relevan kerdesek es valaszok

**K: Erdemes-e Colab-ot hasznalni napi munkara?**
V: Tanulasra es kiserletezsere kivalo, de erzekeny adatokkal valo napi munkara NEM javasolt. Uzleti kornyezetben erdemes Azure ML Studio-t, AWS SageMaker-t vagy sajat on-premise megoldast hasznalni, ahol a jogi megfeleleoseg (GDPR, AI Act) biztositott.

**K: Melyik Deep Learning keretrendszert erdemes tanulni?**
V: A PyTorch valt ipari szabvannya, mert gyorsan alkalmazkodik az uj kutatasi eredmenyekhez. A TensorFlow tamogatottsaga csokkeno. A Keras mindketto folott jol hasznalhato absztrakciot biztosit. Erdemes PyTorch-csal kezdeni.

**K: Mennyire fontos a kodiras az AI eszkozok koraban?**
V: A kodiras fontossaga csokken az AI eszkozok fejlodesevel (Cursor, Copilot stb.), de a **koncepciok megertese tovabbra is elengedhetetlen**. Az allasinterjukon egyre inkabb elvaras az AI eszkozok hatekonya hasznalata.

**K: Milyen AI eszkoozok ajanlattak fejleszteshez?**
V:
- **Cursor**: AI-tamogatott kodszerkeszto
- **Perplexity**: RAG-alapu kereso, minimalis hallucinacio
- **NotebookLM**: Podcastokat es prezentaciokat general szoveges anyagokbol
- **OpenAI / Google API-k**: Elotra betanitott modellek hasznalata es finomhangolasa

### Adat PKL formatumba mentese -- best practice

Az egyik legfontosabb gyakorlati tipp a kurzusbol:

> "Baramilyen forrasbol szarmazo adatbol Pandas DataFrame-et hozunk letre, majd PKL fajlba mentjuk. A PKL formatumot a Pandas gyorsan tudja olvasni a `read_pickle` metodussal, igy egyseeges es gyors adatkezelest tesz lehetove."

```python
# Adat mentese PKL formatumba
df.to_pickle('elofeldolgozott_adatok.pkl')

# Visszaolvasas -- szignifikansan gyorsabb, mint CSV
df = pd.read_pickle('elofeldolgozott_adatok.pkl')
```

---

## Kapcsolodo Temak

- [03_adatmegertes_es_eda.md](03_adatmegertes_es_eda.md) -- Adatmegertes es Explorativ Adatelemzes (EDA), ami szervesen epul a Pandas ismeretekre
- [01_ml_alapfogalmak_es_tipusok.md](01_ml_alapfogalmak_es_tipusok.md) -- ML alapfogalmak (supervised, unsupervised, semi-supervised, reinforcement learning)

---

## Forrasok

| Forras | Tipus | Idotartam |
|--------|-------|-----------|
| 02_06 -- ML fejlesztesi es uzemeltetesi eszkozok | Videolecke | 14:23 |
| 02_07 -- Colab hasznalata | Videolecke | 11:11 |
| 02_08 -- Pandas intro | Videolecke | 16:06 |
| 02_09 -- Pandas folytatas | Videolecke | 17:34 |
| Cubix_ML_Engineer_Pandas.ipynb | Jupyter notebook | -- |
| 02_13 -- LIVE alkalom (2026.02.11.) | Elo session | 1:13:28 |

## Tovabbi Forrasok

- **Pandas dokumentacio**: [https://pandas.pydata.org/docs/](https://pandas.pydata.org/docs/)
- **Pandas Cheat Sheet (PDF)**: [https://pandas.pydata.org/Pandas_Cheat_Sheet.pdf](https://pandas.pydata.org/Pandas_Cheat_Sheet.pdf)
- **Seaborn adathalmazok**: `import seaborn as sns; sns.get_dataset_names()` -- keszz adathalmazok gyakorlashoz
- **Google Colab**: [https://colab.research.google.com](https://colab.research.google.com)
- **Colab elofizetes**: [https://colab.research.google.com/signup](https://colab.research.google.com/signup)
