# Klaszterezés (Clustering)

## Gyors Áttekintés

> A klaszterezés egy nem felügyelt tanulási (unsupervised learning) módszer, amelynek célja az adatpontok hasonlóság alapján történő csoportosítása előre definiált címkék nélkül. A felügyelt tanulással ellentétben itt nem ismerjük a helyes választ -- az algoritmusnak magának kell felfedeznie az adatok belső struktúráját. A klaszterezés önálló elemzési eszközként (pl. ügyfélszegmentálás) és felügyelt tanulási modellek támogató feature engineering módszereként egyaránt használható.

---

## Kulcsfogalmak

| Fogalom | Jelentés |
|---------|---------|
| **Klaszter** | Hasonló adatpontok csoportja |
| **Centroid** | Egy klaszter középpontja (az adatpontok átlaga) |
| **Hard clustering** | Minden adatpont pontosan egy klaszterhez tartozik (pl. K-Means) |
| **Soft clustering** | Egy adatpont több klaszterhez is tartozhat valószínűségi alapon (pl. GMM) |
| **Inertia** | Az adatpontok és a hozzájuk tartozó centroid közötti távolságok négyzetösszege |
| **Linkage** | Hierarchikus klaszterezésnél a klaszterek közötti távolság számítási módja |
| **Dendrogram** | Fa struktúrájú diagram a hierarchikus klaszterek megjelenítésére |
| **Epsilon (eps)** | DBSCAN paramétere: maximális távolság két pont között, hogy szomszédnak számítsanak |
| **Core pont** | DBSCAN: olyan pont, amelynek eps sugarú környezetében legalább min_samples pont van |
| **Noise (zaj)** | DBSCAN: olyan adatpont, amely nem tartozik egyetlen klaszterhez sem (-1 címke) |
| **Doméntudás** | Szakterületi ismeret, amely segíti a klaszterszám és az eredmények értelmezését |

---

## Adatelőkészítés Klaszterezéshez

A klaszterezés eredménye nagymértékben függ az adatok előfeldolgozásától. A távolság-alapú algoritmusok (K-Means, hierarchikus) különösen érzékenyek a skálázásra és az outlierekre.

### Skálázás szükségessége

A legtöbb klaszterezési algoritmus távolságmértékeket használ (euklideszi, Manhattan stb.), ezért az eltérő skálájú feature-ök torzítják az eredményt. A **MinMaxScaler** a [0, 1] intervallumba normalizálja az adatokat:

```python
from sklearn.preprocessing import MinMaxScaler

minMax_scale = MinMaxScaler()
scaled_data = minMax_scale.fit_transform(data)
```

### Feature selection és dimenziócsökkentés

Nem mindig szükséges a teljes adathalmazt klaszterezni. Doméntudás alapján kiválaszthatjuk a releváns feature-csoportokat, és ezekre külön klasztereket hozhatunk létre. A dimenziócsökkentés segíthet:

- **PCA**: lineáris dimenziócsökkentés, megőrzi a variancia adott százalékát
- **Kernel PCA**: nemlineáris változat, kernel trükköt alkalmaz
- **t-SNE**: elsősorban vizualizációra szolgál, klaszterezéshez nem ideális bemeneti adat

```python
from sklearn.decomposition import PCA
from sklearn.decomposition import KernelPCA

# PCA: legalább 95%-os variancia megőrzés
pca_obj = PCA(n_components=0.95)
data_pca = pd.DataFrame(pca_obj.fit_transform(scaled_data))

# Kernel PCA
kernel_pca = KernelPCA(n_components=9, kernel='rbf', fit_inverse_transform=True)
data_kernel_pca = pd.DataFrame(kernel_pca.fit_transform(scaled_data))
```

### Hiányzó értékek kezelése

A hiányzó értékeket klaszterezés előtt pótolni kell. A **SimpleImputer** medián stratégiával robusztus megoldást ad:

```python
from sklearn.impute import SimpleImputer

data = pd.DataFrame(
    SimpleImputer(strategy='median').fit_transform(data),
    columns=data.columns
)
```

### Outlier kezelés

Az outlierek a klaszterek centroidjait eltorzíthatják. A **log1p transzformáció** a szélsőséges értékeket közelebb hozza a többihez:

```python
import numpy as np

# log1p: log(1 + x), biztonságos nulla értékeknél is
# np.log(0) = -inf, de np.log1p(0) = 0
data = pd.DataFrame(np.log1p(data))
```

> **Fontos**: A `log1p` csak pozitív értékekre működik helyesen. Negatív értékek jelenlétét előzetesen ellenőrizni kell: `(data < 0).any().any()`

### Vizualizáció előkészítése t-SNE-vel

A t-SNE 2D vagy 3D térbe vetíti az adatokat a klaszterek vizuális ellenőrzéséhez:

```python
from sklearn.manifold import TSNE

tsne = TSNE(
    n_components=2,
    perplexity=30,
    random_state=42,
    n_iter=300
).fit_transform(scaled_data)

embedding_df = pd.DataFrame(tsne, columns=['feature1', 'feature2'])
```

---

## K-Means

A K-Means a legismertebb és leggyakrabban használt klaszterezési algoritmus. Iteratív módon k darab klasztert hoz létre, ahol a k-t előre meg kell adni.

### Működési elv (Lloyd algoritmus)

1. **Inicializáció**: Véletlenszerűen kiválaszt k centroidot
2. **Hozzárendelés**: Minden adatpontot a legközelebbi centroidhoz rendel
3. **Újraszámítás**: A centroidokat újraszámolja az adott klaszter pontjainak átlagaként
4. **Iteráció**: A 2-3. lépést ismétli, amíg a centroidok változása minimálisra csökken

A klaszteren belüli variancia (minimalizálandó célfüggvény):

$$W_{ck} = \frac{1}{C_k} \sum (X_k - X')^2$$

ahol:
- $C_k$: az adott klaszterhez tartozó adatpontok száma
- $X_k$: az adatpont
- $X'$: a klaszter centroidja

### K megválasztása (Elbow módszer, Silhouette)

A klaszterszám meghatározása nem triviális feladat. Több módszer együttes alkalmazása javasolt:

**Elbow (könyök) módszer**: Különböző k értékek mellett kiszámítjuk az inertiát (torzítást), és a grafikonon megkeressük a "könyökpontot", ahol az inertia csökkenése meredekről laposra vált.

```python
from sklearn.cluster import KMeans
from yellowbrick.cluster import KElbowVisualizer

kmeans = KMeans(random_state=42)
visualizer = KElbowVisualizer(kmeans, k=(2, 10))
visualizer.fit(scaled_data)
visualizer.show()
```

**Distortion** (torzítás):

$$Distortion = \frac{1}{n} \sum (pont - centroid)^2$$

**Inertia**:

$$Inertia = \sum (pont - centroid)^2$$

> **Megjegyzés**: A könyökpont nem mindig egyértelmű. Ilyenkor érdemes a doméntudást, a Silhouette-szkórt és a vizualizációt is figyelembe venni.

### K-Means++ inicializáció

A K-Means++ az alapértelmezett inicializálási módszer az sklearn-ben (`init='k-means++'`). A centroidokat úgy választja ki, hogy azok egymástól távol legyenek, ami gyorsabb konvergenciát és jobb eredményt biztosít.

### Előnyök / Hátrányok

| Előnyök | Hátrányok |
|---------|-----------|
| Egyszerű és gyorsan futó: O(n) időkomplexitás | A k-t előre meg kell adni |
| Nagy adathalmazokra is alkalmas | Csak gömb alakú klasztereket talál |
| Jól értelmezhető eredmény | Érzékeny az inicializációra és az outlierekre |
| Széles körben támogatott | Nem kezeli a változó sűrűségű adatokat |

### Kód példa

```python
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns

# K-Means klaszterezés PCA-val csökkentett adatokon
k = 4
kmeans = KMeans(n_clusters=k, random_state=42).fit(data_pca)
labels = kmeans.labels_

# Vizualizáció t-SNE vetítéssel
embedding_df_kmeans = pd.DataFrame(tsne, columns=['feature1', 'feature2'])
embedding_df_kmeans['Cluster'] = pd.DataFrame(labels)

plt.figure(figsize=(12, 8))
sns.scatterplot(
    x='feature1', y='feature2',
    data=embedding_df_kmeans,
    hue=embedding_df_kmeans['Cluster'],
    palette=sns.color_palette("hls", k)
).set(title='K-Means Clustering')
plt.show()
```

#### Kernel K-Means

A Kernel K-Means nemlineáris klaszterhatárok kezelésére alkalmas, RBF kernellel:

```python
from sklearn.metrics.pairwise import pairwise_kernels

k = 4
kernel = pairwise_kernels(data_pca, metric='rbf')
kmeans = KMeans(n_clusters=k, random_state=42).fit(kernel)
labels = kmeans.labels_
```

---

## Hierarchikus Klaszterezés

A hierarchikus klaszterezés fa struktúrába szervezi az adatokat, amely a dendrogrammal kiválóan vizualizálható. Két fő megközelítése van.

### Agglomeratív vs Divízív

| Megközelítés | Irány | Működés |
|-------------|-------|---------|
| **Agglomeratív** (bottom-up) | Alulról felfelé | Minden adatpont külön klaszterként indul, fokozatosan egyesíti őket |
| **Divízív** (top-down) | Felülről lefelé | Egyetlen nagy klaszterből indul, fokozatosan bontja kisebbekre |

Az agglomeratív megközelítés a gyakoribb a gyakorlatban.

### Linkage típusok (single, complete, average, Ward)

A linkage határozza meg, hogyan mérjük a klaszterek közötti távolságot:

| Linkage típus | Meghatározás |
|--------------|-------------|
| **Single** | A két klaszter két legközelebbi pontjának távolsága |
| **Complete** | A két klaszter két legtávolabbi pontjának távolsága |
| **Average** | Az összes pontpár átlagos távolsága a két klaszter között |
| **Ward** | A klasztereken belüli variancia növekedését minimalizálja (ajánlott alapértelmezett) |

### Dendrogram

A dendrogram fa struktúrájú diagram, amely vizualizálja a hierarchikus kapcsolatokat:

- Az **y-tengely** a klaszterek közötti távolságot (dissimilarity) mutatja
- Alulról felfelé haladva egyre nagyobb csoportok alakulnak ki
- Egy **vízszintes vágóvonal** (cutoff) meghúzásával meghatározhatjuk a klaszterek számát
- A vágóvonalat ott érdemes meghúzni, ahol **nagy távolság** van két összevonás között

```python
import scipy.cluster.hierarchy as shc

plt.figure(figsize=(10, 7))
plt.title("Dendrogram")
dend = shc.dendrogram(
    shc.linkage(y=data_pca, method="ward", metric='euclidean')
)
plt.axhline(y=38, color='r', linestyle='--')  # Cutoff vonal
plt.show()
```

### Összehasonlítás K-Means-szel

| Szempont | K-Means | Hierarchikus |
|----------|---------|-------------|
| Időkomplexitás | O(n) -- lineáris | O(n^2) -- négyzetes |
| Nagy adathalmazok | Alkalmas | Nem ideális |
| Klaszterszám ismerete | Szükséges előre | Dendrogram segít |
| Átláthatóság | Korlátozott | Dendrogram révén jobb |
| Komplex struktúrák | Gyengébb | Jobb |

### Kód példa

```python
from sklearn.cluster import AgglomerativeClustering
import scipy.cluster.hierarchy as shc

# Dendrogram készítése a klaszterszám meghatározásához
plt.figure(figsize=(10, 7))
plt.title("Dendrogram")
dend = shc.dendrogram(
    shc.linkage(y=data_pca, method="ward", metric='euclidean')
)
plt.axhline(y=38, color='r', linestyle='--')
plt.show()

# Agglomeratív klaszterezés 4 klaszterrel
clustering_agg = AgglomerativeClustering(n_clusters=4).fit(data_pca)
hier_labels = clustering_agg.labels_

# Vizualizáció
embedding_df_hier = pd.DataFrame(tsne, columns=['feature1', 'feature2'])
embedding_df_hier['Cluster'] = pd.DataFrame(hier_labels)

plt.figure(figsize=(12, 8))
sns.scatterplot(
    x='feature1', y='feature2',
    data=embedding_df_hier,
    hue=embedding_df_hier['Cluster'],
    palette=sns.color_palette("hls", 4)
).set(title='Hierarchikus Klaszterezés')
plt.show()

# Metrikák
from sklearn.metrics import silhouette_score, davies_bouldin_score

print(f"Silhouette Score: {silhouette_score(data_pca, hier_labels, metric='euclidean'):.3f}")
print(f"Davies-Bouldin Score: {davies_bouldin_score(data_pca, hier_labels):.3f}")
```

---

## Spectral Clustering (Spektrális Klaszterezés)

A spektrális klaszterezés a gráfelmélet és a lineáris algebra eszközeit használja. Az egyik leghatékonyabb módszer **nemlineáris mintázatok** felismerésére.

### Működési elv (gráf Laplacian)

1. **Hasonlósági gráf építése**: Az adatpontok egy gráfot alkotnak, ahol az élek a hasonlóságot fejezik ki
2. **Laplacian mátrix kiszámítása**: A gráf Laplacian mátrixát számítjuk ki
3. **Sajátértékek/sajátvektorok**: A Laplacian mátrix sajátvektorait használjuk dimenziócsökkentésre
4. **K-Means a sajátvektorokon**: Az alacsony dimenziós térben K-Means-t alkalmazunk

### Mikor használd

- **Nemlineáris klaszterhatárok** esetén (félkör, gyűrű alakú klaszterek)
- Komplex geometriájú adatoknál
- Amikor a K-Means és hierarchikus módszerek nem adnak jó eredményt
- Az összehasonlító tesztek alapján a spektrális klaszterezés a **legtöbb adatmintán a legjobban teljesített**

> **Figyelmeztetés**: A Silhouette és Davies-Bouldin metrikák gyengébb értéket mutathatnak a spektrális klaszterezésnél, mint a K-Means-nél, annak ellenére, hogy a vizuális eredmény szebb. Ezeket a metrikákat fenntartásokkal kell kezelni.

### Kód példa

```python
from sklearn.cluster import SpectralClustering

# Spektrális klaszterezés PCA adatokon
clustering_spectral = SpectralClustering(
    n_clusters=6,
    affinity='nearest_neighbors'
).fit(data_pca)
spectral_labels = clustering_spectral.labels_

# Vizualizáció
embedding_df_spectral = pd.DataFrame(tsne_2d, columns=['TSNE1', 'TSNE2'])
embedding_df_spectral['Cluster'] = pd.DataFrame(spectral_labels)

plt.figure(figsize=(12, 8))
sns.scatterplot(
    x='TSNE1', y='TSNE2',
    data=embedding_df_spectral,
    hue=embedding_df_spectral['Cluster'],
    palette=sns.color_palette("hls", 6)
).set(title='Spectral Clustering')
plt.show()

# Metrikák
from sklearn.metrics import silhouette_score, davies_bouldin_score

print(f"Silhouette Score: {silhouette_score(scaled_data, spectral_labels, metric='euclidean'):.3f}")
print(f"Davies-Bouldin Score: {davies_bouldin_score(scaled_data, spectral_labels):.3f}")
```

> **Tipp**: A spektrális klaszterezés az eredeti (skálázott) adatokon és a PCA adatokon is hasonló eredményt ad. Kernel PCA adatokkal is kipróbálható.

---

## Gaussian Mixture Model (GMM)

A GMM valószínűségi modell, amely az adatokat több Gauss-eloszlás keverékeként modellezi. A legfőbb előnye, hogy **soft clustering**-re képes.

### Soft clustering

A GMM minden adatponthoz megadja, **milyen valószínűséggel tartozik az egyes klaszterekhez**. Ezzel árnyaltabb képet ad, mint a hard clustering módszerek:

```python
# Klaszter valószínűségek lekérdezése
cluster_probabilities = gmm.predict_proba(scaled_data)
# Eredmény: minden sorban annyi valószínűség, ahány klaszter van
# Összegük soronként 1.0
```

### EM algoritmus

A GMM az **Expectation-Maximization (EM)** algoritmussal tanul:

1. **E-lépés (Expectation)**: Kiszámítja az adatpontok valószínűségi hozzárendelését a klaszterekhez
2. **M-lépés (Maximization)**: Frissíti a Gauss-eloszlások paramétereit (átlag, szórás, súlyok)
3. **Iteráció**: Ismétli amíg konvergál

### Előnyök / Hátrányok

| Előnyök | Hátrányok |
|---------|-----------|
| Soft clustering (valószínűségek) | Önmagában nem mindig hatékony |
| Nagyon gyors futás | Érzékeny az inicializációra |
| Flexibilis klaszter alakok (elliptikus) | Feltételezi a Gauss-eloszlást |

### Kód példa

```python
from sklearn.mixture import GaussianMixture

# GMM betanítása
gmm = GaussianMixture(n_components=5).fit(scaled_data)
gmm_labels = gmm.predict(scaled_data)

# Vizualizáció
embedding_df_gmm = pd.DataFrame(tsne_2d, columns=['TSNE1', 'TSNE2'])
embedding_df_gmm['Cluster'] = pd.DataFrame(gmm_labels)

plt.figure(figsize=(12, 8))
sns.scatterplot(
    x='TSNE1', y='TSNE2',
    data=embedding_df_gmm,
    hue=embedding_df_gmm['Cluster'],
    palette=sns.color_palette("hls", 5)
).set(title='Gaussian Mixture Model Clustering')
plt.show()

# Klaszter valószínűségek
cluster_probabilities = gmm.predict_proba(scaled_data)
for i in range(cluster_probabilities.shape[1]):
    embedding_df_gmm[f'Cluster_{i}_Probability'] = cluster_probabilities[:, i]

print(embedding_df_gmm.head())
```

> **Tipp**: A GMM eredménye javul, ha az adatokat előzetesen skálázzuk. Skálázott adatokon a klaszterek jobban elkülönülnek.

---

## DBSCAN

A DBSCAN (Density-Based Spatial Clustering of Applications with Noise) sűrűség-alapú klaszterezési algoritmus, amely **automatikusan meghatározza a klaszterek számát** és képes **outliereket azonosítani**.

### Működési elv (eps, min_samples)

Két fő paraméter:
- **eps (epsilon)**: Maximális távolság két pont között, hogy szomszédnak számítsanak
- **min_samples**: Minimum pontszám az eps sugarú környezetben, hogy egy pont core pont legyen

### Core, border, noise pontok

| Pont típusa | Meghatározás |
|------------|-------------|
| **Core pont** | eps sugarú környezetében legalább min_samples pont van |
| **Border pont** | Egy core pont eps sugarú környezetében van, de ő maga nem core pont |
| **Noise (zaj)** | Nem core pont és nem is border pont; a -1 címkét kapja |

### Előnyök (tetszőleges alakú klaszterek, outlier detektálás)

| Előnyök | Hátrányok |
|---------|-----------|
| Tetszőleges alakú klasztereket talál | Nagyon érzékeny az eps paraméterre |
| Automatikus klaszterszám meghatározás | Változó sűrűségű adatoknál gyenge |
| Beépített outlier/zaj detektálás | Az eps finomhangolása nehéz |
| Nem kell előre megadni k-t | Nem teljesen veszi le a paraméterválasztás terhét |

### Kód példa

```python
from sklearn.cluster import DBSCAN

# DBSCAN klaszterezés
dbscan = DBSCAN(eps=0.1, min_samples=5).fit(data_kernel_pca)
dbscan_labels = dbscan.labels_
# A -1 címke zajos (noise) mintákat jelöl

# Vizualizáció
embedding_df_dbscan = pd.DataFrame(tsne_2d, columns=['TSNE1', 'TSNE2'])
embedding_df_dbscan['Cluster'] = pd.DataFrame(dbscan_labels)

plt.figure(figsize=(12, 8))
sns.scatterplot(
    x='TSNE1', y='TSNE2',
    data=embedding_df_dbscan,
    hue=embedding_df_dbscan['Cluster'],
    palette=sns.color_palette("hls", len(set(dbscan_labels)))
).set(title='DBSCAN Clustering')
plt.show()

# Klaszterszám és zaj
n_clusters = len(set(dbscan_labels)) - (1 if -1 in dbscan_labels else 0)
n_noise = list(dbscan_labels).count(-1)
print(f"Talált klaszterek: {n_clusters}, Zajos pontok: {n_noise}")
```

> **Figyelem**: Az eps érzékeny paraméter! Példa a hatására:
> - `eps=0.05` --> 62 klaszter (túl sok)
> - `eps=0.10` --> 5 klaszter
> - `eps=0.15` --> 1 klaszter + zaj (túl kevés)

---

## HDBSCAN

A HDBSCAN (Hierarchical DBSCAN) a DBSCAN továbbfejlesztett változata, amely hierarchikus megközelítéssel **változó sűrűségű** adatokat is jobban kezel.

### Különbség a DBSCAN-tól

| Szempont | DBSCAN | HDBSCAN |
|----------|--------|---------|
| Globális eps | Szükséges | Nem szükséges (adaptív) |
| Változó sűrűség | Gyenge | Jobb |
| Paraméterek | eps, min_samples | min_samples, cluster_selection_epsilon |
| Robusztusság | Érzékeny eps-re | Robusztusabb |

> **Megjegyzés**: A HDBSCAN nem része az sklearn alapcsomagnak, külön telepíteni kell: `pip install hdbscan`

### Kód példa

```python
import hdbscan

clusterer = hdbscan.HDBSCAN(
    cluster_selection_epsilon=0.1,
    min_samples=5
)
hdbscan_labels = clusterer.fit_predict(data_kernel_pca)

# Vizualizáció
embedding_df_hdbscan = pd.DataFrame(tsne_2d, columns=['TSNE1', 'TSNE2'])
embedding_df_hdbscan['Cluster'] = hdbscan_labels

plt.figure(figsize=(12, 8))
sns.scatterplot(
    x='TSNE1', y='TSNE2',
    data=embedding_df_hdbscan,
    hue=embedding_df_hdbscan['Cluster'],
    palette=sns.color_palette("hls", len(set(hdbscan_labels)))
).set(title='HDBSCAN Clustering')
plt.show()
```

> **Tapasztalat**: A HDBSCAN előnye elsősorban olyan adatoknál mutatkozik meg, ahol a klaszterek sűrűsége erősen változó. Ha az adatban viszonylag egyenletes a sűrűség, a DBSCAN is elegendő.

---

## Klaszter-Validációs Metrikák

A klaszterezés értékelése nehezebb, mint a felügyelt tanulásé, mert nincsenek "helyes" címkék. Több metrika együttes használata javasolt.

### Silhouette Score

A Silhouette-szkor azt méri, mennyire jól illeszkedik egy adatpont a saját klaszteréhez a többi klaszterhez képest.

$$S_i = \frac{b - a}{\max(b, a)}$$

ahol:
- **a**: átlagos klaszteren belüli távolság (mean intra-cluster distance)
- **b**: átlagos legközelebbi klaszter távolság (mean nearest-cluster distance)

| Érték tartomány | Értelmezés |
|-----------------|-----------|
| **1** | Tökéletes klaszterezés |
| **0.5 -- 1** | Jó klaszterezés |
| **0 -- 0.5** | Közepes, átfedő klaszterek |
| **< 0** | Rossz klaszterezés, rossz hozzárendelés |

```python
from sklearn.metrics import silhouette_score

score = silhouette_score(data_pca, labels, metric='euclidean')
print(f'Silhouette Score: {score:.3f}')
```

### Davies-Bouldin Index

Az átlagos klaszterek közötti hasonlóságot méri. Figyelembe veszi a klasztereken belüli átlagos távolságokat és a centroidok közötti távolságot.

| Szempont | Értelmezés |
|----------|-----------|
| Tartomány | 0-tól végtelenig |
| Cél | Minél **kisebb**, annál jobb |
| 0 | Tökéletesen elkülönülő klaszterek |

Számítás komponensei:
- **s(i)**: az i-edik klaszteren belüli átlagos távolság
- **s(j)**: a j-edik klaszteren belüli átlagos távolság
- **d(i,j)**: az i és j klaszterek centroidjainak távolsága

```python
from sklearn.metrics import davies_bouldin_score

score = davies_bouldin_score(data_pca, labels)
print(f'Davies-Bouldin Score: {score:.3f}')
```

### Calinski-Harabasz Index

A klaszterek közötti szóródás és a klasztereken belüli szóródás arányát méri. Minél **nagyobb**, annál jobb.

```python
from sklearn.metrics import calinski_harabasz_score

score = calinski_harabasz_score(data_pca, labels)
print(f'Calinski-Harabasz Score: {score:.3f}')
```

### Elbow módszer (inertia)

Az inertia a klasztereken belüli négyzetösszeg (WCSS). Különböző k értékekre kiszámítva, a grafikonon a "könyökpont" jelzi az optimális klaszterszámot.

```python
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

inertias = []
K_range = range(2, 11)

for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42).fit(scaled_data)
    inertias.append(kmeans.inertia_)

plt.figure(figsize=(10, 6))
plt.plot(K_range, inertias, 'bo-')
plt.xlabel('Klaszterek száma (k)')
plt.ylabel('Inertia')
plt.title('Elbow módszer')
plt.show()
```

### Komplex kiértékelési példa

```python
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

def evaluate_clustering(data, labels, name=""):
    """Klaszterezés kiértékelése több metrikával."""
    sil = silhouette_score(data, labels, metric='euclidean')
    db = davies_bouldin_score(data, labels)
    ch = calinski_harabasz_score(data, labels)
    print(f"--- {name} ---")
    print(f"  Silhouette Score:       {sil:.3f}  (közelebb 1-hez = jobb)")
    print(f"  Davies-Bouldin Index:   {db:.3f}  (közelebb 0-hoz = jobb)")
    print(f"  Calinski-Harabasz:      {ch:.1f}  (nagyobb = jobb)")
    return {'silhouette': sil, 'davies_bouldin': db, 'calinski_harabasz': ch}

# Használat
evaluate_clustering(data_pca, kmeans_labels, "K-Means (k=4)")
evaluate_clustering(data_pca, hier_labels, "Hierarchikus (k=4)")
evaluate_clustering(scaled_data, spectral_labels, "Spectral (k=6)")
```

---

## Összehasonlító Táblázat

| Algoritmus | Klaszter alak | K szükséges? | Outlier kezelés | Méretezhetőség | Soft/Hard | Sebesség | Mikor használd |
|-----------|---------------|-------------|----------------|---------------|-----------|----------|---------------|
| **K-Means** | Gömb alakú | Igen | Nincs | Nagy adatokra jó, O(n) | Hard | Gyors (~5s) | Alapértelmezett választás, nagy adathalmazok |
| **Hierarchikus** | Tetszőleges | Nem (dendrogram segít) | Nincs | Kicsi/közepes, O(n^2) | Hard | Lassú (~16s) | Hierarchikus struktúra, klaszterszám ismeretlen |
| **Spectral** | Tetszőleges, nemlineáris | Igen | Nincs | Közepes | Hard | Közepes (~9s) | Nemlineáris határok, komplex geometria |
| **GMM** | Elliptikus | Igen (n_components) | Nincs | Nagy adatokra jó | **Soft** | Nagyon gyors (~3s) | Valószínűségi hozzárendelés kell |
| **DBSCAN** | Tetszőleges | **Nem** | **Igen** (noise=-1) | Jó | Hard | Gyors (~5s) | Outlier detektálás, ismeretlen klaszterszám |
| **HDBSCAN** | Tetszőleges | **Nem** | **Igen** (noise=-1) | Jó | Hard | Gyors (~5s) | Változó sűrűségű adatok |

> **Megjegyzés**: A sebességadatok a kurzus Credit Card Dataset-jére vonatkoznak, és orientációs jellegűek.

---

## Gyakorlati Útmutató

### Klaszterezési workflow

```
1. ADATELŐKÉSZÍTÉS
   ├── Hiányzó értékek pótlása (SimpleImputer, medián)
   ├── Outlier kezelés (log1p transzformáció)
   ├── Skálázás (MinMaxScaler)
   └── (Opcionális) Dimenziócsökkentés (PCA, 95% variancia)

2. FELTÁRÓ VIZUALIZÁCIÓ
   ├── t-SNE 2D/3D vetítés
   └── Szabad szemmel becsülhető klaszterszám

3. KLASZTEREZÉS
   ├── Elbow módszer / Dendrogram --> klaszterszám becslés
   ├── Több algoritmus kipróbálása
   │   ├── K-Means (baseline)
   │   ├── Spektrális klaszterezés (nemlineáris)
   │   ├── DBSCAN (outlierek)
   │   └── GMM (ha soft clustering kell)
   └── Eredmények vizualizálása t-SNE-vel

4. KIÉRTÉKELÉS
   ├── Silhouette Score
   ├── Davies-Bouldin Index
   ├── Calinski-Harabasz Index
   ├── Vizuális ellenőrzés
   └── Doméntudás bevonása

5. FELÜGYELT TANULÁS TÁMOGATÁSA (opcionális)
   ├── Klaszter címkék hozzáadása feature-ként
   ├── Cross-validation különböző klaszterszámokkal
   └── A legjobb kombináció kiválasztása
```

### Kód példák

Teljes klaszterezési pipeline: lasd `_kod_peldak/klaszterezes.py`

#### Gyors összehasonlító script

```python
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.preprocessing import MinMaxScaler
from sklearn.impute import SimpleImputer
from sklearn.decomposition import PCA
import time

# --- 1. Adatelőkészítés ---
data = pd.read_csv("CC GENERAL.csv")
data.set_index('CUST_ID', inplace=True)
data = pd.DataFrame(
    SimpleImputer(strategy='median').fit_transform(data),
    columns=data.columns
)
data = pd.DataFrame(np.log1p(data))

scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

pca = PCA(n_components=0.95)
data_pca = pca.fit_transform(scaled_data)

# --- 2. Klaszterezés és kiértékelés ---
algorithms = {
    'K-Means (k=4)': KMeans(n_clusters=4, random_state=42),
    'K-Means (k=6)': KMeans(n_clusters=6, random_state=42),
    'Hierarchikus (k=4)': AgglomerativeClustering(n_clusters=4),
    'Hierarchikus (k=6)': AgglomerativeClustering(n_clusters=6),
    'Spectral (k=6)': SpectralClustering(n_clusters=6, affinity='nearest_neighbors'),
    'DBSCAN (eps=0.1)': DBSCAN(eps=0.1, min_samples=5),
}

results = []
for name, algo in algorithms.items():
    start = time.time()
    labels = algo.fit_predict(data_pca)
    elapsed = time.time() - start

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    if n_clusters < 2:
        results.append({'Algoritmus': name, 'Klaszterek': n_clusters,
                        'Idő (s)': f'{elapsed:.2f}', 'Silhouette': 'N/A',
                        'Davies-Bouldin': 'N/A'})
        continue

    sil = silhouette_score(data_pca, labels, metric='euclidean')
    db = davies_bouldin_score(data_pca, labels)
    results.append({
        'Algoritmus': name,
        'Klaszterek': n_clusters,
        'Idő (s)': f'{elapsed:.2f}',
        'Silhouette': f'{sil:.3f}',
        'Davies-Bouldin': f'{db:.3f}'
    })

# GMM külön (predict kell)
start = time.time()
gmm = GaussianMixture(n_components=5, random_state=42).fit(scaled_data)
gmm_labels = gmm.predict(scaled_data)
elapsed = time.time() - start
sil = silhouette_score(scaled_data, gmm_labels, metric='euclidean')
db = davies_bouldin_score(scaled_data, gmm_labels)
results.append({
    'Algoritmus': 'GMM (k=5)',
    'Klaszterek': 5,
    'Idő (s)': f'{elapsed:.2f}',
    'Silhouette': f'{sil:.3f}',
    'Davies-Bouldin': f'{db:.3f}'
})

print(pd.DataFrame(results).to_string(index=False))
```

---

## Gyakori Hibák és Tippek

### Hibák

1. **Skálázás elmulasztása**: A K-Means és hierarchikus klaszterezés távolság-alapú; skálázás nélkül a nagy értéktartományú feature-ök dominálnak.

2. **t-SNE adaton klaszterezés**: A t-SNE vizualizációra szolgál, nem klaszterezési bemeneti adatnak. Használj PCA-t vagy az eredeti skálázott adatot.

3. **Egyetlen metrikára hagyatkozás**: A Silhouette-szkor és a Davies-Bouldin index nem mindig korrelál a vizuálisan jó eredménnyel (pl. spektrális klaszterezésnél gyenge metrikát, de szép klasztereket kaptunk).

4. **A klaszterszám "golden rule" keresése**: Nincs egyetlen helyes klaszterszám. Az Elbow módszer könyökpontja nem mindig egyértelmű. Kombináld a doméntudással.

5. **DBSCAN eps paraméterének vak beállítása**: Mindig próbálj meg több eps értéket, és vizualizáld az eredményt.

### Tippek

1. **Kezdd K-Means-szel** mint baseline, majd próbáld ki a spektrális klaszterezést a nemlineáris mintázatokhoz.

2. **Használj dendrogramot**, ha nem tudod a klaszterszámot -- a hierarchikus klaszterezés vizuálisan segít a döntésben.

3. **Felügyelt tanulás támogatásához**: Ha van felügyelt tanulási feladatod, a klaszter címkéket hozzáadhatod feature-ként, és cross-validation-nel tesztelheted a különböző klaszterszámok hatását.

4. **Doméntudás**: A szakterületi szakértők gyakran jobb becslést adnak a klaszterszámra, mint bármely automatikus módszer.

5. **GMM a soft clustering-hez**: Ha fontos tudni, hogy egy adatpont melyik klaszterhez tartozik milyen valószínűséggel, a GMM a legjobb választás.

6. **3D vizualizáció**: Ha a 2D ábrán átfedő klasztereket látsz, próbáld meg 3D-ben -- a klaszterek gyakran jobban elkülönülnek.

7. **Feature engineering klaszterezéssel**: Domén tudás alapján kiválasztott feature-csoportokra külön klasztereket hozhatsz létre, és ezeket új feature-ként adhatod a felügyelt modellhez.

---

## Kapcsolódó Témák

- [08_dimenziocsokkentes.md](08_dimenziocsokkentes.md) -- PCA, Kernel PCA, t-SNE, LDA, Isomap, LLE részletes tárgyalása
- [04_adatelokeszites_es_feature_engineering.md](04_adatelokeszites_es_feature_engineering.md) -- Skálázás, hiányzó értékek, outlier kezelés, feature engineering
- [11_anomalia_detektio.md](11_anomalia_detektio.md) -- GMM alkalmazása anomália detektióra, Isolation Forest, self-supervised learning

---

## További Források

- **scikit-learn dokumentáció**: [Clustering](https://scikit-learn.org/stable/modules/clustering.html)
- **K-Means részletes leírás**: https://towardsdatascience.com/k-means-a-complete-introduction-1702af9cd8c
- **Hierarchikus klaszterezés**: https://towardsdatascience.com/hierarchical-clustering-explained-e59b13846da8
- **DBSCAN**: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html
- **HDBSCAN**: https://hdbscan.readthedocs.io/
- **Yellowbrick (Elbow vizualizáció)**: https://www.scikit-yb.org/en/latest/api/cluster/elbow.html
- **Klaszterezési algoritmusok összehasonlítása**: https://scikit-learn.org/stable/modules/clustering.html#overview-of-clustering-methods
