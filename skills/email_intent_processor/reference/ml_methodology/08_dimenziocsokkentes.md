# Dimenziocsokkentes (Dimensionality Reduction)

## Gyors Attekintes

> A dimenziocsokkentes a gepi tanulas egyik alapveto elofeldolgozo lepese, amelynek celja a jellemzok (feature-ok) szamanak csokkentese ugy, hogy a lenyeges informacio megmaradjon. A felugyeletlen tanulas reszteruletekent fontos szerepet jatszik az adatok egyszerusiteseben, a szamitasi koltseg csokkenteseben, az overfitting elkerüleseben es az adatok vizualizaciojaban. A kurzus soran linearis (PCA, SVD, LDA, MDS) es nemlinearis (Kernel PCA, Isomap, LLE, t-SNE) modszereket ismerhetunk meg, mindegyiknek megvan a maga alkalmazasi terulete es erossege.

---

## Kulcsfogalmak

- **Atok a dimenzioe (Curse of Dimensionality)**: Ahogy no a feature-ok szama, az adatpontok egyre ritkabban helyezkednek el a terben. Ez megneheziti a mintazatok felismereset, es az algoritmusok teljesitmenye romlik. Pelda: 10.000 oszlop es csak 300 sor eseten a modell nem tud ertelmes mintazatokat talalni.
- **Feature extraction vs Feature selection**: Ket kulonbozo megkozelites a dimenziocsokkentesre:
  - **Feature selection**: A meglevo feature-ok kozul valasztjuk ki a legfontosabbakat (pl. korrelacio, mutual information alapjan), a tobbit eldobjuk.
  - **Feature extraction**: Az osszes feature-bol uj, kisebb szamu jellemzoket hozunk letre (pl. PCA, t-SNE). Az eredeti feature-ok linearis vagy nemlinearis kombinacioit kapjuk.
- **Variancia (Variance)**: Az adatok szorodasanak merteke. A PCA es hasonlo modszerek azt az iranyt keresik, amelyben a variancia maximalis.
- **Explained Variance Ratio**: Megmutatja, hogy egy adott fokomponens az osszes variancia hany szazalekat magyarazza. Segit eldonteni, hany komponens elegendo.
- **Geodeziai tavolsag**: Ket pont kozotti legrövidebb ut az adathalmaz sokaságan (manifoldon) belul, nem az egyenes vonal (euklideszi) tavolsag. Az Isomap ezt hasznalja.
- **Kernel-trukk**: Matematikai technika, amely lehetove teszi, hogy linearis algoritmusokat nemlinearissa alakitsunk egy magasabb dimenzios terben torteno implicit lekepezessel.

---

## Miert Csökkentsunk Dimenziot?

### Az "atok" problemaja

Gyakran elofordul, hogy az adataink nagyon komplexek: nagyon sok feature (oszlop) van bennuk, mikozben viszonylag keves adatpontunk (sorunk) van. Pelda: 10.000 oszlop es 300 sor. Ilyenkor:
- A modell "elveszik a reszletekben" -- minden apro, irrelevans dologra ratagul
- A szamitasi igenyek exponencialisan nonek
- Az adatpontok oly messze kerulnek egymastol a magas dimenzios terben, hogy a tavolsagalapú modszerek ertelmuket vesztik

### Elonyok

1. **Redundans/irrelevans jellemzok eltavolitasa**: Eltavolitjuk azokat a feature-oket, amelyek nem hordoznak hasznos informaciot vagy duplikaljak mas feature-ok informaciojat.
2. **Overfitting csokkentese**: Megovjuk az algoritmust attol, hogy minden csekelyegre, minden irrelevans dologra ratanuljon. Kevesebb feature = egyszerubb modell = jobb altalanositokepesseg.
3. **Szamitasi koltseg csokkentese**: Akar a tizedere vagy szazadara is csokkenthetjuk a szamitasi kapacitasi igenyt a pontossag csokkentese nelkul. Egy 429 oszlopos adathalmaz 1-10 komponensre csokkentve nagyságrendekkel gyorsabban fut.
4. **Adatvizualizacio**: Ketdimenzioban vagy haromdimenzioban megjelenithetjuk az adatokat, igy betekintest nyerunk a teljes feature setunkbe. Lathato, hogy mennyire konnyen szeparalhatoak az osztalyok.
5. **Zaj csokkentese**: A kisebb dimenzios terben kevesebb a zaj, igy a modell a lenyeges mintazatokra tud koncentralni.

---

## Linearis Modszerek

### PCA (Principal Component Analysis)

A PCA a legismertebb es legszelessebb korben hasznalt dimenziocsokkento technika.

#### Mukodesi elv

A PCA olyan uj koordinata-rendszert keres, amelyben az adatok varianciaja maximalis:
- Az elso fokomponens (PC1) az az irany, amelyik a **legnagyobb varianciat** biztositja
- A masodik fokomponens (PC2) meroleges az elsore, es a maradek varianciabol a leheto legtobbet magyarazza
- A harmadik meg kevesebbet, es igy tovabb
- Kozben a **rezidualasokat** (maradványokat) minimalizalja

A PCA tehat ugy csokkenti az adatok dimenzioját, hogy megortja amennyire lehet az adatok eredeti tulajdonsagait.

**Fontos**: A PCA a **folytonos (continuous) valtozokat** szereti. Kategorikus valtozokra nem idealis kozvetlenul -- erdemes kulon kezelni oket.

#### Explained Variance Ratio

Az `explained_variance_ratio_` attributum megmutatja, hogy az egyes fokomponensek a teljes variancia hany szazalekat magyarazzak. Ha peldaul 95%-os variancia-magyarazatot szeretnenk elerni:

```python
from sklearn.decomposition import PCA

# Automatikus komponensszam: legalabb 95% variancia
pca = PCA(n_components=0.95)
X_pca = pca.fit_transform(X_scaled)

print(f"Kivalasztott komponensek szama: {pca.n_components_}")
print(f"Magyarazott variancia: {pca.explained_variance_ratio_}")
print(f"Osszes magyarazott variancia: {sum(pca.explained_variance_ratio_):.4f}")
```

> A kurzus peldajaban a PCA 9 oszlopot vont ki, amelyekkel elerte a 95%-os varianciamagyarazatot az eredeti adatbol.

#### Komponensek szamanak megvalasztasa

Tobb strategia letezik:
1. **Variancia kuszob**: `PCA(n_components=0.95)` -- annyi komponenst valaszt, amennyi a variancia 95%-at magyarazza
2. **Scree plot / konyok-modszer**: Abrazoljuk a komponensek altal magyarazott varianciat, es ott vagjuk el, ahol a gorbe "megtörik"
3. **Cross-validation-nel kiertekeles**: Probaljunk kulonbozo komponensszamokat, es nezzuk, melyiknel a legjobb a CV pontossag

A kurzusban 2-tol 40-ig probalkoztak, es megfigyelheto volt, hogy 2 es 10 komponens kozott alapvetoen novekszik a pontossag, de utana mar nem egyertelmu a javulas.

#### Kod pelda

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split, KFold

# ---------- Alap PCA az osszes feature-on ----------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

cv_accuracies = []
max_n_components = 40

for n_components in range(2, max_n_components):
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_train)

    X_train_pca = pd.DataFrame(X_pca).reset_index(drop=True)
    y_train = y_train.reset_index(drop=True)

    accuracies = []
    kf = KFold(n_splits=5)
    for train_index, cv_index in kf.split(X_train_pca):
        clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
        clf.fit(X_train_pca.iloc[train_index], y_train.iloc[train_index])
        y_cv_pred = clf.predict(X_train_pca.iloc[cv_index])
        cv_accuracy = accuracy_score(y_train[cv_index], y_cv_pred)
        accuracies.append(cv_accuracy)

    cv_accuracies.append(np.mean(accuracies))

# Eredmenyek kirajzolasa
plt.plot(range(2, max_n_components), cv_accuracies, marker='o', linestyle='-')
plt.title('CV Pontossag vs. Komponensek szama (PCA)')
plt.xlabel('Komponensek szama')
plt.ylabel('Atlagos CV pontossag')
plt.grid(True)
plt.show()

# ---------- PCA csak folytonos oszlopokon + konkatenal ----------
continuous_columns = ['V4', 'V16', 'V19', 'V20', 'V22']

pca = PCA(n_components=2)
X_continuous_pca = pca.fit_transform(X[continuous_columns])
pca_feature_names = [f'PCA_{i}' for i in range(2)]

X_pca_df = pd.DataFrame(X_continuous_pca, index=X.index, columns=pca_feature_names)
X_other = X.drop(columns=continuous_columns)
X_combined = pd.concat([X_pca_df, X_other], axis=1)

# ---------- PCA vizualizacio ----------
plt.figure(figsize=(8, 6))
plt.scatter(X_continuous_pca[:, 0], X_continuous_pca[:, 1],
            c=y, cmap='viridis', edgecolor='k', s=40)
plt.title('2D PCA Vizualizacio')
plt.xlabel('PCA 1')
plt.ylabel('PCA 2')
plt.colorbar(label='Osztaly')
plt.show()
```

**Kurzus eredmenyek**:
- PCA nelkul (429 feature): CV pontossag = **0.87**
- PCA 2 komponenssel (osszes feature-on): **0.84**
- PCA 2 komponens (csak continuous) + tobbi oszlop: **0.86**

---

### SVD (Singular Value Decomposition)

#### Mukodesi elv

A Truncated SVD (csonkolt szingularis ertek felbontas) hasonlo celokat szolgal, mint a PCA: dimenziot csokkent a fo varianciak mentén. A legfontosabb kulonbseg:

- **Ritka matrixokkal is kepes dolgozni** (sparse matrices), ami a PCA-nak nem erossege
- Kulonosen hasznos **NLP** (termeszetes nyelvfeldolgozas) es **ajanlorendszerek** teruleten, ahol a term-document vagy user-item matrixok jellemzoen nagyon ritkak
- Az sklearn-ben `TruncatedSVD` neven erheto el

#### Kapcsolat a PCA-val

A PCA belsőleg is SVD-t hasznal! A fo kulonbseg az, hogy a PCA eloszor centralizalja (atlagot kivon) az adatokat, mig a TruncatedSVD ezt nem teszi, ezert kepes ritka matrixokkal is hatékonyan dolgozni (a centralizacio megszuntetne a ritkasagot).

#### Kod pelda

```python
from sklearn.decomposition import TruncatedSVD

svd = TruncatedSVD(n_components=10)
X_svd = svd.fit_transform(X_train)

# Ugyanugy hasznalhato, mint a PCA
print(f"Magyarazott variancia arany: {svd.explained_variance_ratio_.sum():.4f}")
```

**Kurzus eredmeny**: A Truncated SVD nem hozott erdemi javulast a PCA-hoz kepest a tesztelt adathalmazon. Egy esetben ugyan 0.87 fole ment, de az nagy valoszinuseggel veletlen volt.

---

### LDA (Linear Discriminant Analysis)

#### Supervised DR -- Felügyelt dimenziocsokkentes

Az LDA kulonleges a dimenziocsokkento technikak kozott: **felügyelt** (supervised) modszer, tehat ismeri es hasznalja a cimkeket (y). Mig a PCA a teljes adathalmaz varianciat maximalizalja, az LDA a **csoportok kozotti tavolsagot maximalizalja** es a **csoportokon beluli szorast minimalizalja**.

#### Kulonbseg a PCA-tol

| Szempont | PCA | LDA |
|----------|-----|-----|
| Tipusa | Felügyelet nelkuli | Felügyelt |
| Cel | Variancia maximalizalas | Osztaly-szeparacio maximalizalas |
| Cimkek | Nem hasznal | Hasznalja (y-t is atadunk) |
| Max komponensek | min(n_features, n_samples) | min(n_features, n_classes - 1) |
| Mikor jo | Altalanos DR | Ha vannak osztalyok es szeparalni akarunk |

**Fontos korlatozas**: Az LDA altal letrehozható komponensek szama legfeljebb `n_classes - 1`. Tehat binaris (0/1) osztalyozas eseten **maximum 1 komponens** hozhato letre.

#### Kod pelda

```python
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

# LDA -- figyelem: az y_train-t is atadjuk!
lda = LinearDiscriminantAnalysis(n_components=1)  # binaris eseten max 1
X_lda = lda.fit_transform(X_train, y_train)

# Vizualizacio (1D eseten)
import plotly.express as px
df = pd.DataFrame({'LDA1': X_lda[:, 0], 'Class': y_train})
fig = px.scatter(df, x='LDA1', y=[0] * len(df),
                 color='Class', title='LDA Vizualizacio')
fig.show()
```

**Kurzus eredmeny**: Az LDA adta a **legjobb eredmenyt**: **0.881** CV pontossag egyetlen(!) komponenssel a 429 eredeti oszlopbol. Ez bizonyitja, hogy ha vannak cimkeink, erdemes felügyelt dimenziocsokkentéssel is probalkozni.

Az LDA vizualison is nagyon jol szeparalta az osztalyokat -- a lilak es sargak szinte teljesen kulonvaltak.

---

### Kernel PCA

#### Nemlinearis kiterjesztes

A Kernel PCA a hagyomanyos PCA nemlinearis kiterjesztese a **kernel-trukk** segitsegevel. Lehetove teszi, hogy a PCA nemlinearis osszefuggeseket is "elkapjon" az adatokban.

#### Kernel tipusok

- **RBF (Radial Basis Function)**: A leggyakrabban hasznalt kernel, jol mukodik altalanos esetre
- **Polinomialis**: Ha polinomialis osszefuggeseket sejtunk
- **Sigmoid**: Hasonlo a neuralis halozatok aktivacios fuggvenyehez
- **Cosine**: Szoveg-hasonlosagi feladatokhoz

#### Elonyok es hatranyok

**Elonyok**:
- Nemlinearis osszefuggesek felismerese
- Nagy adathalmazon is kepes dolgozni
- Altalaban gyorsabb, mint mas nemlinearis technikak

**Hatranyok**:
- A parameterek kivalasztasa nem trivialis (kernel tipus + kernel parameterei)
- Szamitasigenyes
- Az eredmenyek nem konnyen ertelmezhetok

#### Kod pelda

```python
from sklearn.decomposition import KernelPCA

# Kernel PCA RBF kernellel
kpca = KernelPCA(n_components=2, kernel='rbf')
X_kpca = kpca.fit_transform(X)

# Vizualizacio
plt.figure(figsize=(8, 6))
plt.scatter(X_kpca[:, 0], X_kpca[:, 1], c=y, cmap='viridis', edgecolor='k', s=40)
plt.title('2D Kernel PCA Vizualizacio')
plt.xlabel('Kernel PCA 1')
plt.ylabel('Kernel PCA 2')
plt.colorbar(label='Osztaly')
plt.show()

# PCA 95%-os varianciaval + Kernel PCA
from sklearn.decomposition import PCA

pca_obj = PCA(n_components=0.95)
data_pca = pd.DataFrame(pca_obj.fit_transform(X_scaled))

kernel_pca = KernelPCA(n_components=9, kernel='rbf', fit_inverse_transform=True)
data_kernel_pca = pd.DataFrame(kernel_pca.fit_transform(X_scaled))
```

**Kurzus eredmeny**: Nem hozott kiugro javulast a tesztelt adathalmazon. A continuous oszlopokon 2 komponenssel kb. 0.86-os pontossagot ert el (a tobbi oszloppal osszefuzve).

---

## Nemlinearis Modszerek

### MDS (Multidimensional Scaling)

#### Mukodesi elv

Az MDS celja, hogy a **magasdimenzios terben levo tavolsagokat megorizze** a kisebb dimenzios terben. Az euklideszi tavolsagot hasznalja az adatpontok kozott, es ugy transzformalja oket alacsonyabb dimenzioba, hogy a pontparok tavolsaga a leheto legjobban megmaradjon.

A SwissRoll adathalmazon bemutatva: mig a PCA ketdimenzios abrazolasa "siraimas" (a szinek osszafolynak), az MDS eseteben szepen latszonak a kulonbozo szincsoportok.

#### Metric vs Non-metric

- **Metric MDS**: Megprobálja az eredeti tavolsagokat pontosan megorizni (alapertelmezett)
- **Non-metric MDS**: Csak a tavolsagok **rangsorolasi** sorrendjet orzi meg (nem az abszolut ertekeket). Hasznos, ha ordinalis adatokkal dolgozunk

Az sklearn-ben: `MDS(metric=True)` (alapertelmezett) vs `MDS(metric=False)`

#### Elonyok es hatranyok

**Elonyok**:
- Jol reprezentalja az adatok kozotti tavolsagot kisebb dimenzios terben
- Intuitiv ertelmezes: a vizualizacion a kozeli pontok valoban kozel vannak

**Hatranyok**:
- Erzekeny az outlierekre
- Szamitasigenyes nagyobb adathalmazoknal
- Nem skalazhato nagyon nagy adathalmazokra

#### Kod pelda

```python
from sklearn.manifold import MDS
import plotly.express as px

# MDS 2 komponenssel
mds = MDS(n_components=2, random_state=42)
X_mds = mds.fit_transform(X_train)

# Interaktiv vizualizacio Plotly-val
fig = px.scatter(x=X_mds[:, 0], y=X_mds[:, 1],
                 color=y_train,
                 title='MDS 2 komponenssel (2D)',
                 labels={'x': '1. komponens', 'y': '2. komponens'})
fig.show()

# 3D vizualizacio
mds_3d = MDS(n_components=3, random_state=42)
X_mds_3d = mds_3d.fit_transform(X_train)

fig_3d = px.scatter_3d(x=X_mds_3d[:, 0], y=X_mds_3d[:, 1], z=X_mds_3d[:, 2],
                       color=y_train,
                       title='MDS 3 komponenssel (3D)')
fig_3d.show()
```

---

### Isomap (Isometric Mapping)

#### Geodeziai tavolsagok

Az Isomap a nemlinearis dimenziocsokkento technikak egyik leghatekonyabbja. A kulcsa a **geodeziai tavolsagok** hasznalataban rejlik:

1. Eloszor felépiti a **szomszedossagi grafot** (k-nearest neighbors)
2. A gráfon keresi a legrövidebb utakat (Dijkstra/Floyd-Warshall algoritmussal) -- ezek a geodeziai tavolsagok
3. Ezutan MDS-t alkalmaz a geodeziai tavolsag-matrixra

A SwissRoll peldan: bar a piros es zold szin euklideszi ertelemben kozel van egymashoz, a tekercsen beluli (geodeziai) tavolsag nagy. Az Isomap ezt felismeri, es a kiteritett terben messze helyezi oket.

**Elonye mas modszerekkel szemben**: A teljes terreszletet kitolti (nem tomoritődnek ossze a pontok), igy a belso mintazatok sokkal inkabb felfedezheteok.

#### Elonyok es hatranyok

**Elonyok**:
- Komplex, nemlinearis adatokon is jol mukodik
- Konnyebben vizualizalhato, interpretalhato eredmenyek
- Kepes a felügyelt tanulas pontossagat novelni

**Hatranyok**:
- Hyperparameter hangolas nem egyszeru (kulonosen `n_neighbors`)
- Idoigenyes szamitas
- Erzekeny a zajra es outlierekre

#### Kod pelda

```python
from sklearn.manifold import Isomap
import plotly.express as px

# Isomap 2 komponenssel
isomap = Isomap(n_components=2, n_neighbors=5)
X_isomap = isomap.fit_transform(X)

# Vizualizacio
isomap_df = pd.DataFrame(X_isomap, columns=['ISOMAP_0', 'ISOMAP_1'])
fig = px.scatter(isomap_df, x='ISOMAP_0', y='ISOMAP_1',
                 color=y, title='2D Isomap Vizualizacio',
                 color_continuous_scale='Viridis')
fig.show()

# Isomap csak continuous oszlopokon + konkatenal
continuous_columns = ['V4', 'V16', 'V19', 'V20', 'V22']
isomap = Isomap(n_components=2)
X_continuous_isomap = isomap.fit_transform(X[continuous_columns])

X_isomap_df = pd.DataFrame(X_continuous_isomap, index=X.index,
                            columns=['Isomap_0', 'Isomap_1'])
X_other = X.drop(columns=continuous_columns)
X_combined = pd.concat([X_isomap_df, X_other], axis=1)
```

**Kurzus eredmeny**: A continuous oszlopokon alkalmazva 0.8655-os pontossagot ert el. A teljes X vizualizacioja szep eredmenyt mutatott (sargak es lilak jol elvalnak).

---

### LLE (Locally Linear Embedding)

#### Lokalis linearis kozelites

Az LLE a **lokalis linearis kapcsolatokra fokuszal**: minden adatpontot a szomszedai linearis kombinaciojakeppen ir le, es ugy kepes nemlinearis dimenziocsokkentest vegrehajtani.

Mukodesi lepesek:
1. Minden ponthoz megkeresi a k legkozelebbi szomszedot
2. Minden pontot a szomszedai **linearis kombinaciojakeppen** fejezi ki (sulyok szamitasa)
3. Ezekkel a sulyokkal rekonstrualja a pontokat az alacsonyabb dimenzios terben

#### Elonyok es hatranyok

**Elonyok**:
- Altalaban **gyorsabb**, mint az Isomap
- Kepes ritka matrixokkal is dolgozni
- A hyperparameter hangolas egyszerubb, mint mas nemlinearis modszereknel
- Bizonyos adatokon pontosabb is lehet, mint az Isomap

**Hatranyok**:
- Erzekeny az outlierekre es a zajra
- **Inkonzisztens eredmenyek**: minden futtatasnal mas eredmenyt kaphatunk
- A kurzusban kifejezetten gyengebb eredmenyt hozott, mint az elozo modszerek

#### Kod pelda

```python
from sklearn.manifold import LocallyLinearEmbedding

# LLE 2 komponenssel
lle = LocallyLinearEmbedding(n_components=2, n_neighbors=10)
X_lle = lle.fit_transform(X)

# Vizualizacio
plt.figure(figsize=(8, 6))
plt.scatter(X_lle[:, 0], X_lle[:, 1], c=y, cmap='viridis', edgecolor='k', s=40)
plt.title('2D LLE Vizualizacio')
plt.xlabel('LLE 1')
plt.ylabel('LLE 2')
plt.colorbar(label='Osztaly')
plt.show()

# Plotly-val interaktivan
import plotly.express as px
lle_df = pd.DataFrame(X_lle, columns=['LLE_0', 'LLE_1'])
fig = px.scatter(lle_df, x='LLE_0', y='LLE_1',
                 color=y, title='2D LLE Vizualizacio (Plotly)',
                 color_continuous_scale='Viridis')
fig.show()
```

**Kurzus eredmeny**: 0.8655-os pontossag a continuous oszlopokon. A vizualizacio nem volt szep, es minden futtatasnal mas eredmenyt adott.

---

### t-SNE (t-Distributed Stochastic Neighbor Embedding)

#### Valoszinusegi megkozelites

A t-SNE egy **nemlinearis** dimenziocsokkento algoritmus, amelyet elsosorban **adatvizualizaciora** hasznalunk. Mukodese:

1. A magas dimenzios terben kiszamitja a pontparok **hasonlossagi valoszinusegeit** (Gauss-eloszlas)
2. Az alacsony dimenzios terben Student-t eloszlast hasznal (innen a neve)
3. Minimalizalja a ket eloszlas kozotti **Kullback-Leibler divergenciat**
4. Igy a kozel levo pontok kozel maradnak, a tavoli pontok tavol kerulnek

A t-SNE kulonosen hatekony az MNIST-hez hasonlo adathalmazoknal, ahol a kezzel irt szamok pixeleit 2D/3D terbe vetiti, es a kulonbozo szamjegyek szepen klasztereződnek.

#### Perplexity parameter

A **perplexity** a t-SNE legfontosabb hyperparametere:
- Kb. azt jelenti, "hany szomszedot" vegyen figyelembe
- Jellemzo ertekek: **5-50** kozott
- Kis perplexity: lokalis mintazatokat hang sulyoz (kis klaszterek)
- Nagy perplexity: globalisabb strukturat mutat
- Nincs univerzalis legjobb ertek -- kiserletezni kell

#### Kod pelda

```python
from sklearn.manifold import TSNE

# t-SNE 2 komponenssel
tsne = TSNE(n_components=2,
            perplexity=30,
            random_state=42,
            n_iter=300)
X_tsne = tsne.fit_transform(X)

# Vizualizacio
plt.figure(figsize=(8, 6))
plt.scatter(X_tsne[:, 0], X_tsne[:, 1], c=y, cmap='viridis', edgecolor='k', s=40)
plt.title('2D t-SNE Vizualizacio')
plt.xlabel('t-SNE 1')
plt.ylabel('t-SNE 2')
plt.colorbar(label='Osztaly')
plt.show()

# t-SNE 2D es 3D egyutt
fig, ax = plt.subplots(1, 2, figsize=(16, 6))
for i, n_comp in enumerate([2, 3]):
    tsne = TSNE(n_components=n_comp, random_state=42)
    X_t = tsne.fit_transform(X_train)
    if n_comp == 2:
        ax[i].scatter(X_t[:, 0], X_t[:, 1], c=y_train, cmap='viridis')
        ax[i].set_title(f't-SNE {n_comp}D')
    if n_comp == 3:
        ax_3d = fig.add_subplot(1, 2, 2, projection='3d')
        ax_3d.scatter(X_t[:, 0], X_t[:, 1], X_t[:, 2], c=y_train, cmap='viridis')
        ax_3d.set_title(f't-SNE {n_comp}D')
plt.show()
```

**Megjegyzes**: A Barnes-Hut algoritmus (alapertelmezett) csak 2 vagy 3 komponenst tamogat.

#### FONTOS korlatok

1. **Elsosorban vizualizaciora valo** -- NEM optimalizacios elofelgolgozo lepesnek. A kurzusban 2-3 komponenssel joval gyengebb volt a felügyelt tanulasi modell pontossaga, mint mas modszereknel.
2. **Inkonzisztens eredmenyek**: Minden futtatasnal mas vizualizaciot ad (meg `random_state` beallitas eseten is mas-mas geometriat kaphatunk).
3. **Sokáig tart**: A szamitasi ido jelentos, kulonosen nagy adathalmazoknal.
4. **A tavolsagok nem ertelmezhetok**: A t-SNE terben a klaszterek merete es kozottuk levo tavolsag nem tukrozi a valos tavolsagokat.
5. **Nem transzformalható uj adatra**: A `fit_transform` egyutt fut, uj adatpontokra nem lehet kozvetlenul alkalmazni (nincs `transform` kulön).

**Kurzus eredmeny**: A 2D vizualizacio "talan az eddigi legjobb" volt, de a modellpontossag 2-3 komponenssel joval gyengebb. A continuous oszlopokon + tobbi oszloppal: 0.87 es 0.8654.

---

## UMAP (Kiegeszites -- nem a kurzusbol)

> **Megjegyzes**: A UMAP nem szerepelt a Cubix kurzusban, de a gyakorlatban egyre fontosabb modszer, ezert erdemes rola tudni.

### Mi az UMAP?

A **UMAP** (Uniform Manifold Approximation and Projection) egy modern nemlinearis dimenziocsokkento modszer (2018), amely a t-SNE alternativaja es sok szempontbol felulmulja azt.

### Elonyok a t-SNE-vel szemben

| Szempont | t-SNE | UMAP |
|----------|-------|------|
| Sebesseg | Lassu | **Jelentosen gyorsabb** |
| Skalahatosag | Nehezen skalazhato | Joban skalazodik nagy adatra |
| Globalis struktura | Elvesziti | **Jobban megőrzi** |
| Konzisztencia | Inkonzisztens | **Stabilabb** eredmenyek |
| Uj adatok | Nincs `transform` | **Van `transform`** |
| Komponensek | Max 2-3 (Barnes-Hut) | Tetszoleges szam |

### Kod pelda

```python
# pip install umap-learn
import umap

# UMAP 2 komponenssel
reducer = umap.UMAP(n_components=2,
                    n_neighbors=15,
                    min_dist=0.1,
                    metric='euclidean',
                    random_state=42)
X_umap = reducer.fit_transform(X)

# Vizualizacio
plt.figure(figsize=(8, 6))
plt.scatter(X_umap[:, 0], X_umap[:, 1], c=y, cmap='viridis', s=10)
plt.title('2D UMAP Vizualizacio')
plt.xlabel('UMAP 1')
plt.ylabel('UMAP 2')
plt.colorbar(label='Osztaly')
plt.show()

# Uj adatra is alkalmazhato!
X_new_umap = reducer.transform(X_test)
```

### Mikor hasznald a UMAP-ot?

- Ha a t-SNE tul lassu
- Ha fontos a globalis struktura megorzese
- Ha uj adatpontokra is kell tudni transzformalni
- Ha tobb, mint 3 komponensre van szukseged
- Klaszterezes elott (a UMAP jobban megőrzi a klaszter-strukturat)

---

## DR Modszer-Valaszto Osszehasonlito Tablazat

| Modszer | Linearis? | Supervised? | Mit oriz meg | Mikor hasznald | Sklearn osztaly | Sebesseg |
|---------|-----------|-------------|--------------|----------------|-----------------|----------|
| **PCA** | Igen | Nem | Globalis variancia | Altalanos celra, elso valasztas | `sklearn.decomposition.PCA` | Gyors |
| **Truncated SVD** | Igen | Nem | Variancia (ritka matrixon) | NLP, ajanlorendszerek, ritka matrixok | `sklearn.decomposition.TruncatedSVD` | Gyors |
| **LDA** | Igen | **Igen** | Osztaly-szeparacio | Ha vannak cimkek es osztalyokat akarunk szeparalni | `sklearn.discriminant_analysis.LinearDiscriminantAnalysis` | Gyors |
| **Kernel PCA** | Nem | Nem | Nemlinearis variancia | Nemlinearis adatstruktura, nagy adathalmaz | `sklearn.decomposition.KernelPCA` | Kozepes |
| **MDS** | Igen* | Nem | Euklideszi tavolsagok | Tavolsag-megorzés, interpretalhato vizualizacio | `sklearn.manifold.MDS` | Lassu |
| **Isomap** | Nem | Nem | Geodeziai tavolsagok | Komplex nemlinearis adat, legjobb nemlinearis DR | `sklearn.manifold.Isomap` | Lassu |
| **LLE** | Nem | Nem | Lokalis linearis strukt. | Gyorsabb alternativa az Isomap-hoz | `sklearn.manifold.LocallyLinearEmbedding` | Kozepes |
| **t-SNE** | Nem | Nem | Lokalis hasonlosagok | **Kizarolag vizualizacio** | `sklearn.manifold.TSNE` | Lassu |
| **UMAP** | Nem | Nem | Lok.+glob. struktura | Vizualizacio + klaszterezes, t-SNE alternativa | `umap.UMAP` (kulon csomag) | Gyors |

*Az MDS az euklideszi tavolsagot hasznalja (linearis), de leteziik nemlinearis valtozata is (non-metric MDS).

---

## Gyakorlati Utmutato

### Mikor melyik modszert?

**1. Elso korben mindig probalj PCA-t:**
- Gyors, megbizhato, jol ertheto
- Hasznald az `explained_variance_ratio_`-t a komponensek kivalasztasahoz

**2. Ha vannak osztalyaid (cimkeid):**
- Mindenkeppen probald ki az **LDA**-t is
- A kurzusban ez adta a legjobb eredmenyt

**3. Ha ritka matrixod van (NLP, ajanlorendszer):**
- Hasznalj **Truncated SVD**-t

**4. Ha nemlinearis osszefuggeseket sejteszsz:**
- Probald ki az **Isomap**-ot -- a leghatekonyabb nemlinearis modszer a kurzus szerint
- Ha gyorsabb megoldast keressz: **LLE** vagy **Kernel PCA**

**5. Ha vizualizalni akarsz:**
- **t-SNE** a klasszikus valasztas
- **UMAP** a modernebb es gyorsabb alternativa

**6. Ha egy modszert szeretnel es komplex adataid vannak:**
- Az oktato ajanlasa: **Isomap**
- Ha vannak osztalyaid: **LDA**

**7. Ha van idon es eroforrasod:**
- Probald ki az osszeset, es hasonlitsd ossze!

### Kod peldak

A reszletes, futtathato kod peldak elerhetek:
- Notebook: `Tanayag/06_het/code/Cubix_ML_Engineer_Unsupervised_Learning.ipynb`
- Feldolgozott peldak: [_kod_peldak/dimenziocsokkentes.py](_kod_peldak/dimenziocsokkentes.py)

### Altalanos workflow

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier

# 1. Adat betoltese es skalazasa
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 2. Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.33, random_state=42)

# 3. Dimenziocsokkentes (pl. PCA)
from sklearn.decomposition import PCA
pca = PCA(n_components=0.95)
X_train_pca = pca.fit_transform(X_train)
X_test_pca = pca.transform(X_test)  # FONTOS: transform, nem fit_transform!

# 4. Modell tanitasa a csokkentett adaton
clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
clf.fit(X_train_pca, y_train)

# 5. Kiertekeles
from sklearn.metrics import accuracy_score
y_pred = clf.predict(X_test_pca)
print(f"Pontossag: {accuracy_score(y_test, y_pred):.4f}")
```

---

## Gyakorlati tipp: Continuous vs. osszes oszlop

A kurzusban fontos strategiakent merult fel, hogy a PCA-t (es hasonlo modszereket) csak a **folytonos (continuous) oszlopokon** alkalmazzuk, majd az igy kapott komponenseket **osszefuzzuk** a kategorikus oszlopokkal:

```python
continuous_columns = ['V4', 'V16', 'V19', 'V20', 'V22']

# DR csak a continuous oszlopokon
pca = PCA(n_components=2)
X_continuous_pca = pca.fit_transform(X[continuous_columns])
pca_names = [f'PCA_{i}' for i in range(2)]

# Osszefuzes a tobbi oszloppal
X_pca_df = pd.DataFrame(X_continuous_pca, index=X.index, columns=pca_names)
X_other = X.drop(columns=continuous_columns)
X_combined = pd.concat([X_pca_df, X_other], axis=1)
```

Ez az eljaras jobb eredmenyeket adhat, mert:
- Nem veszitjuk el a kategorikus oszlopok informaciojat
- A PCA a megfelelo adattipuson dolgozik
- A vegso modell tobb informaciohoz jut

---

## Gyakori Hibak es Tippek

### 1. Skalazas elfelejtese
A PCA es mas tavolsagalapu modszerek erzékenyek a feature-ok meretekrere. **Mindig skalazz** (StandardScaler vagy MinMaxScaler) a DR elott!

### 2. Train-test szivargas (data leakage)
- A dimenziocsokkentest **csak a train adaton** kell fit-elni
- A test adatra `transform()`-ot hivjunk, **NEM** `fit_transform()`-ot
- Kulonben a modell "latja" a teszt adatot, es tul optimista eredmenyt kapunk

### 3. Tul keves komponens valasztasa
- Ne feltetelezzuk, hogy 2-3 komponens eleg! Hasznalj explained variance ratio-t vagy CV pontossagot a donteshez

### 4. t-SNE eredmenyeken ne tanits modellt
- A t-SNE kimenete **nem alkalmas** felügyelt tanulasi modellek bemenetekent
- Hasznald vizualizaciora, ne modellezesre

### 5. Inkonzisztens eredmenyek kezelese
- Az LLE es t-SNE minden futtatasnal mas eredmenyt adhat
- Allits be `random_state`-et a reprodukalhatosag erdekeben
- De tartsd eszben, hogy a geometriai elrendezes akkor is valtozhat

### 6. Egy kiugro ertek nem elegendo
- Ha egy komponensszamnal kiugro pontossagot latunk, de az osszes tobbi eseten sokkal gyengebb, az valoszinuleg veletlen. Inkabb az atlagos trendet figyeld!

### 7. PCA kategorikus adaton
- A PCA folytonos valtozokra van tervezve
- Kategorikus valtozokra hasznalj kulon modszereket (pl. MCA - Multiple Correspondence Analysis)

---

## Kapcsolodo Temak

- [09_klaszterezes.md](09_klaszterezes.md) -- A dimenziocsokkentes gyakran a klaszterezes elofeldolgozo lepese. A kurzusban is a PCA/t-SNE eredmenyen futtattak K-Means-t.
- [04_adatelokeszites_es_feature_engineering.md](04_adatelokeszites_es_feature_engineering.md) -- A feature selection modszerek (korrelacio, mutual information) is egyfajta dimenziocsokkentes, de mas megkozelitessel.

---

## Tovabbi Forrasok

### Kurzus anyagai
- **Videok**: 06_01 - 06_10 (Cubix EDU ML Engineering, 6. het)
- **Notebook**: `Tanayag/06_het/code/Cubix_ML_Engineer_Unsupervised_Learning.ipynb`
- **Transcript-ek**: `Tanayag/06_het/06_01..06_10_*_transcript_hu.md`

### Kulso hivatkozasok (a kurzusbol)
- SwissRoll adathalmaz es nemlinearis DR osszehasonlitas: [ResearchGate cikk](https://www.researchgate.net/publication/223964057_Comparative_analysis_of_nonlinear_dimensionality_reduction_techniques_for_breast_MRI_segmentation)
- t-SNE vizualizacio MNIST-en: [Google for Developers YouTube video](https://www.youtube.com/watch?v=wvsE8jm1GzE)
- Isomap geodeziai tavolsag: [Towards Data Science cikk](https://towardsdatascience.com/preserving-geodesic-distance-for-non-linear-datasets-isomap-d24a1a1908b2)

### Tovabbi olvasmanyok
- sklearn dokumentacio: [Manifold Learning](https://scikit-learn.org/stable/modules/manifold.html)
- sklearn dokumentacio: [Decomposition](https://scikit-learn.org/stable/modules/decomposition.html)
- UMAP dokumentacio: [umap-learn.readthedocs.io](https://umap-learn.readthedocs.io/)
- StatQuest videok a PCA-rol es t-SNE-rol (YouTube)

---

## Osszefoglalas -- A kurzus legfontosabb tanulsagai

1. **PCA** a kiindulasi pont -- bevalt, gyors, meghbizhato
2. **LDA** adta a legjobb eredmenyt a kurzusban (0.881 pontossag egyetlen komponenssel!) -- ha vannak cimkeid, probald ki
3. A **nemlinearis modszerek** (Isomap, Kernel PCA) komplex adatokon jobbak lehetnek, de lassabbak
4. **t-SNE** vizualizaciora kivaló, modellezesre **nem**
5. Erdemes a **continuous oszlopokon** kulön alkalmazni a DR-t, majd osszefuzni a tobbi oszloppal
6. **Probald ki az osszeset** -- az adatodtol fugg, melyik modszer a legjobb
7. A dimenziocsokkentes nem helyettesiti a felügyelt tanulasi algoritmust, hanem **elofelgolgozo lepeskent** szolgal
