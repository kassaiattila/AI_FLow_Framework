"""
Klaszterezesi algoritmusok - Unsupervised Learning
====================================================

Ez a fajl a legfontosabb klaszterezesi modszereket mutatja be
a Cubix ML Engineer kepzes anyaga alapjan.

Tartalomjegyzek:
    1. Adateloeszites klaszterezeshez (skalazo, feature kivalasztas)
    2. K-Means (KMeans, elbow modszer, K-Means++)
    3. Hierarchikus klaszterezes (AgglomerativeClustering, dendrogram)
    4. Spectral Clustering
    5. Gaussian Mixture Model (GMM) - soft clustering
    6. DBSCAN (eps, min_samples, core/border/noise)
    7. HDBSCAN (opcionalis)
    8. Klaszter-validacios metrikak
    9. Elbow modszer vizualizacio
    10. Silhouette analizis vizualizacio
    11. Klaszterezesi eredmenyek vizualizacio (2D scatter)

Futtatas:
    python klaszterezes.py
"""

import matplotlib.pyplot as plt
import numpy as np

# Scipy - dendrogram a hierarchikus klaszterezeshez
import scipy.cluster.hierarchy as shc
from matplotlib import cm

# Sklearn - klaszterezo algoritmusok
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans, SpectralClustering

# Sklearn - adatgeneralas
from sklearn.datasets import make_blobs, make_moons

# Sklearn - validacios metrikak
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
)

# Sklearn - Gaussian Mixture Model
from sklearn.mixture import GaussianMixture

# Sklearn - eloeldolgozas
from sklearn.preprocessing import MinMaxScaler, StandardScaler

# HDBSCAN - opcionalis import (nem mindig telepitett)
try:
    import hdbscan
    HDBSCAN_ELERHETO = True
except ImportError:
    HDBSCAN_ELERHETO = False
    print("[INFO] A hdbscan csomag nem elerheto. Telepites: pip install hdbscan")


# =============================================================================
# 1. ADATELOESZITES KLASZTEREZESHEZ
# =============================================================================

def adatok_generalasa():
    """
    Szintetikus adatok generalasa klaszterezeshez.

    Ket kulonbozo adathalmazt keszitunk:
    - make_blobs: gomb alaku klaszterek (jo K-Means-hez, hierarchikushoz)
    - make_moons: felhold alaku klaszterek (jo DBSCAN-hez, Spectral-hoz)

    Returns:
        tuple: (X_blobs, y_blobs, X_moons, y_moons) - adatok es valodi cimkek
    """
    # Gomb alaku klaszterek - 4 kozeppont korul
    X_blobs, y_blobs = make_blobs(
        n_samples=500,
        n_features=2,
        centers=4,
        cluster_std=0.8,
        random_state=42
    )

    # Felhold alaku klaszterek - nem-konvex alakzatok
    X_moons, y_moons = make_moons(
        n_samples=400,
        noise=0.08,
        random_state=42
    )

    return X_blobs, y_blobs, X_moons, y_moons


def adatok_skalazasa(X, modszer="standard"):
    """
    Feature skalazas klaszterezeshez.

    A klaszterezo algoritmusok (foleg a tavolsag-alapuak, mint K-Means)
    erzekenyiek a feature-ok skalajara. Skalazas nelkul a nagyobb
    mertekegysegu feature-ok dominalnak.

    Args:
        X: bemeneti feature matrix
        modszer: "standard" (StandardScaler) vagy "minmax" (MinMaxScaler)

    Returns:
        X_scaled: skalazott adatok
    """
    if modszer == "standard":
        # StandardScaler: atlag=0, szoras=1 (z-score normalas)
        # Ajanlott legtobb klaszterezo algoritmushoz
        scaler = StandardScaler()
    elif modszer == "minmax":
        # MinMaxScaler: [0, 1] tartomanyba skalaz
        # Hasznos ha a feature-oknak meghatarozott tartomanyban kell lenniuk
        scaler = MinMaxScaler()
    else:
        raise ValueError(f"Ismeretlen skalazasi modszer: {modszer}")

    X_scaled = scaler.fit_transform(X)
    print(f"[Skalazas] Modszer: {modszer}")
    print(f"  Eredeti tartomany: [{X.min():.2f}, {X.max():.2f}]")
    print(f"  Skalazott tartomany: [{X_scaled.min():.2f}, {X_scaled.max():.2f}]")

    return X_scaled


# =============================================================================
# 2. K-MEANS KLASZTEREZES
# =============================================================================

def kmeans_klaszterezes(X, n_klaszter=4):
    """
    K-Means klaszterezes.

    Mukodese:
    1. Veletlenszeruen valaszt K db kozeppontot (centroid)
    2. Minden pontot a legkozelebbi centroidhoz rendel
    3. Ujraszamolja a centroidokat (az adott klaszter pontjainak atlaga)
    4. Ismetli 2-3 lepest, amig a centroidok stabilizalodnak

    K-Means++ (alapertelmezett az sklearn-ben):
    - Okos inicializalas: az elso centroid veletlenszeru,
      a tobbi ugy van valasztva, hogy tavolabb legyenek egymastol
    - Gyorsabb konvergencia, jobb eredmeny

    Args:
        X: skalazott bemeneti adatok
        n_klaszter: klaszterek szama (K ertek)

    Returns:
        tuple: (labels, centroids, kmeans_model) - cimkek, kozeppontok, modell
    """
    # init='k-means++' az alapertelmezett: okos centroid inicializalas
    # n_init=10: 10-szer futtatja kulonbozo inicializalassal, a legjobbat valasztja
    # random_state: reprodukalhato eredmenyek
    kmeans = KMeans(
        n_clusters=n_klaszter,
        init='k-means++',
        n_init=10,
        max_iter=300,
        random_state=42
    )
    kmeans.fit(X)

    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_
    inertia = kmeans.inertia_  # WCSS (Within-Cluster Sum of Squares)

    print(f"[K-Means] K={n_klaszter}")
    print(f"  Inertia (WCSS): {inertia:.2f}")
    print(f"  Iteraciok szama: {kmeans.n_iter_}")
    print(f"  Klaszter meretek: {np.bincount(labels)}")

    return labels, centroids, kmeans


# =============================================================================
# 3. HIERARCHIKUS KLASZTEREZES
# =============================================================================

def hierarchikus_klaszterezes(X, n_klaszter=4, linkage="ward"):
    """
    Agglomerative (bottom-up) hierarchikus klaszterezes.

    Mukodese:
    1. Minden pont kulon klaszter
    2. A ket legkozelebbi klasztert osszevonja
    3. Ismetli amig a kivant klaszterszamot el nem eri

    Linkage tipusok:
    - ward: a klaszteren beluli variancianovedekest minimalizalja (ajanlott)
    - single: a ket klaszter legkozelebbi pontjai kozti tavolsag (lancolo hatas!)
    - complete: a ket klaszter legtavolabbi pontjai kozti tavolsag
    - average: az osszes pontpar atlagos tavolsaga

    Args:
        X: skalazott bemeneti adatok
        n_klaszter: klaszterek szama
        linkage: osszekapcsolasi modszer ("ward", "single", "complete", "average")

    Returns:
        tuple: (labels, model) - cimkek es modell
    """
    model = AgglomerativeClustering(
        n_clusters=n_klaszter,
        linkage=linkage
    )
    model.fit(X)
    labels = model.labels_

    print(f"[Hierarchikus] K={n_klaszter}, linkage={linkage}")
    print(f"  Klaszter meretek: {np.bincount(labels)}")

    return labels, model


def dendrogram_rajzolas(X, linkage_method="ward", cut_level=None):
    """
    Dendrogram rajzolasa scipy segitsegevel.

    A dendrogram a hierarchikus klaszterezes fastrukturajat abrazoja.
    A fuggoleges tengely a klaszterek kozti tavolsagot (dissimilarity) mutatja.
    A vagasi vonal segit a klaszterszam megvalasztasaban.

    Args:
        X: bemeneti adatok
        linkage_method: osszekapcsolasi modszer
        cut_level: vagasi szint (opcionalis vizszintes vonal)
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title("Dendrogram - Hierarchikus klaszterezes", fontsize=14)
    ax.set_xlabel("Adatpont index")
    ax.set_ylabel("Tavolsag (dissimilarity)")

    # Linkage matrix szamitasa
    linkage_matrix = shc.linkage(X, method=linkage_method, metric="euclidean")

    # Dendrogram kirajzolasa
    shc.dendrogram(
        linkage_matrix,
        truncate_mode="lastp",  # csak az utolso p osszevonast mutatja
        p=30,                   # max 30 levelet mutat (atlathatosag)
        leaf_rotation=90,
        leaf_font_size=8,
        ax=ax
    )

    # Vagasi vonal (ha megadva)
    if cut_level is not None:
        ax.axhline(y=cut_level, color="r", linestyle="--", linewidth=2,
                   label=f"Vagasi szint: {cut_level}")
        ax.legend(fontsize=11)

    plt.tight_layout()
    plt.show()


# =============================================================================
# 4. SPECTRAL CLUSTERING
# =============================================================================

def spectral_klaszterezes(X, n_klaszter=4, affinity="nearest_neighbors"):
    """
    Spectral Clustering.

    Mukodese:
    1. Affinitasi (hasonlossagi) matrixot epit az adatokbol
    2. A Laplace-matrix sajatertekeit/sajatvetorait szamolja ki
    3. A sajatvektor-terben K-Means-t futtat

    Elonyei:
    - Nem-konvex (tetszoleges alaku) klasztereket is felismer
    - Grafelmelet-alapu megkozelites

    Affinity tipusok:
    - 'nearest_neighbors': k-legkozelebbi szomszed grafbol epit
    - 'rbf': Radial Basis Function kernel (Gauss-kernel)

    Args:
        X: skalazott bemeneti adatok
        n_klaszter: klaszterek szama
        affinity: affinitasi metrika

    Returns:
        tuple: (labels, model)
    """
    model = SpectralClustering(
        n_clusters=n_klaszter,
        affinity=affinity,
        random_state=42,
        n_neighbors=10  # a nearest_neighbors-hoz
    )
    labels = model.fit_predict(X)

    print(f"[Spectral] K={n_klaszter}, affinity={affinity}")
    print(f"  Klaszter meretek: {np.bincount(labels)}")

    return labels, model


# =============================================================================
# 5. GAUSSIAN MIXTURE MODEL (GMM) - SOFT CLUSTERING
# =============================================================================

def gmm_klaszterezes(X, n_komponens=4):
    """
    Gaussian Mixture Model - valoszinusegi (soft) klaszterezes.

    A GMM feltételezi, hogy az adatok tobb Gauss-eloszlasbol szarmaznak.
    Minden adatponthoz valoszinusegeket rendel, nem egyertelmuen oszt be.

    Elonyei:
    - Soft clustering: minden ponthoz klaszter-valoszinusegeket ad
    - Elipszis alaku klasztereket is kezel (nem csak gomb alakut)
    - BIC/AIC kriteriummal valaszthato a komponensek szama

    Hard clustering vs Soft clustering:
    - Hard: minden pont pontosan egy klaszterbe kerul (K-Means, DBSCAN)
    - Soft: minden pont valoszinuseggel tartozik minden klaszterhez (GMM)

    Args:
        X: skalazott bemeneti adatok
        n_komponens: Gauss-komponensek (klaszterek) szama

    Returns:
        tuple: (labels, probabilities, model) - cimkek, valoszinusegek, modell
    """
    gmm = GaussianMixture(
        n_components=n_komponens,
        covariance_type="full",  # teljes kovarianciamtrix (rugalmas klaszter alak)
        n_init=5,
        random_state=42
    )
    gmm.fit(X)

    labels = gmm.predict(X)
    probabilities = gmm.predict_proba(X)

    print(f"[GMM] Komponensek szama: {n_komponens}")
    print(f"  BIC: {gmm.bic(X):.2f}  (alacsonyabb = jobb)")
    print(f"  AIC: {gmm.aic(X):.2f}  (alacsonyabb = jobb)")
    print(f"  Klaszter meretek: {np.bincount(labels)}")
    print("  Pelda valoszinusegek (elso 3 pont):")
    for i in range(min(3, len(probabilities))):
        prob_str = ", ".join([f"{p:.3f}" for p in probabilities[i]])
        print(f"    Pont {i}: [{prob_str}]")

    return labels, probabilities, gmm


# =============================================================================
# 6. DBSCAN
# =============================================================================

def dbscan_klaszterezes(X, eps=0.5, min_samples=5):
    """
    DBSCAN (Density-Based Spatial Clustering of Applications with Noise).

    Surused-alapu klaszterezes. Nem kell elore megadni a klaszterek szamat!

    Fogalmak:
    - Core point (magpont): legalabb min_samples szomszedja van eps sugaron belul
    - Border point (hataros pont): eps sugaron belul van egy core ponttol,
      de kevesebb szomszedja van, mint min_samples
    - Noise point (zajpont): se nem core, se nem border -> cimke = -1

    Parameterek:
    - eps: szomszedsagi sugar (kisebb -> tobb klaszter / tobb zaj)
    - min_samples: minimum pontszam egy core pont kornyezeteben

    Elonyei:
    - Tetszoleges alaku klasztereket felismer
    - Automatikusan kezeli a zajt (outlier-eket)
    - Nem kell K-t elore megadni

    Args:
        X: skalazott bemeneti adatok
        eps: epsilon sugar
        min_samples: minimum szomszedszam a core pontokhoz

    Returns:
        tuple: (labels, model)
    """
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    dbscan.fit(X)
    labels = dbscan.labels_

    n_klaszter = len(set(labels)) - (1 if -1 in labels else 0)
    n_zaj = list(labels).count(-1)

    # Ponttipusok szamlalasa
    core_mask = np.zeros(len(X), dtype=bool)
    core_mask[dbscan.core_sample_indices_] = True
    n_core = core_mask.sum()
    n_border = ((labels != -1) & (~core_mask)).sum()

    print(f"[DBSCAN] eps={eps}, min_samples={min_samples}")
    print(f"  Talalt klaszterek: {n_klaszter}")
    print(f"  Zajpontok (noise): {n_zaj}")
    print(f"  Core pontok: {n_core}")
    print(f"  Border pontok: {n_border}")

    return labels, dbscan


# =============================================================================
# 7. HDBSCAN (OPCIONALIS)
# =============================================================================

def hdbscan_klaszterezes(X, min_cluster_size=15, min_samples=5):
    """
    HDBSCAN (Hierarchical DBSCAN).

    A DBSCAN javitott valtozata:
    - Nem kell eps-t megadni (automatikusan valasztja)
    - Hierarchikus megkozelitest hasznal a kulonbozo surusegu klaszterekhez
    - Robusztusabb a parametererzekenysegre

    Args:
        X: skalazott bemeneti adatok
        min_cluster_size: minimum klaszter meret
        min_samples: a core pont minimalis szomszedszama

    Returns:
        tuple: (labels, model) vagy (None, None) ha nem elerheto
    """
    if not HDBSCAN_ELERHETO:
        print("[HDBSCAN] Nem elerheto - telepites: pip install hdbscan")
        return None, None

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=0.0
    )
    labels = clusterer.fit_predict(X)

    n_klaszter = len(set(labels)) - (1 if -1 in labels else 0)
    n_zaj = list(labels).count(-1)

    print(f"[HDBSCAN] min_cluster_size={min_cluster_size}, min_samples={min_samples}")
    print(f"  Talalt klaszterek: {n_klaszter}")
    print(f"  Zajpontok (noise): {n_zaj}")

    return labels, clusterer


# =============================================================================
# 8. KLASZTER-VALIDACIOS METRIKAK
# =============================================================================

def klaszter_validacio(X, labels, nev=""):
    """
    Klaszter-validacios metrikak szamitasa.

    Silhouette Score:
        - Meri mennyire jol van minden pont a sajat klasztereben
        - Ertek: [-1, 1], magasabb = jobb
        - a = atlagos klaszteren beluli tavolsag (kohezio)
        - b = atlagos legkozelebbi klaszter tavolsag (szeparacio)
        - Si = (b - a) / max(a, b)

    Davies-Bouldin Index:
        - A klaszterek atlagos hasonlosagat meri
        - Ertek: [0, vegtelen), alacsonyabb = jobb
        - Figyelembe veszi a klaszteren beluli szorast es kozeppontok tavolsagat

    Calinski-Harabasz Index (Variance Ratio Criterion):
        - A klaszterek kozotti es beluli variancia aranya
        - Ertek: [0, vegtelen), magasabb = jobb
        - Jol szeparalt, tomor klasztereknel magas

    Args:
        X: bemeneti adatok
        labels: klaszter cimkek
        nev: az algoritmus neve (kiiras celjara)

    Returns:
        dict: metrikak szotara
    """
    # Zajpontok kiszurese a validaciobol (DBSCAN/HDBSCAN -1 cimkei)
    mask = labels != -1
    if mask.sum() < 2 or len(set(labels[mask])) < 2:
        print(f"[Validacio - {nev}] Nem eleg klaszter vagy pont a validaciohoz.")
        return {}

    X_valid = X[mask]
    labels_valid = labels[mask]

    sil = silhouette_score(X_valid, labels_valid, metric="euclidean")
    db = davies_bouldin_score(X_valid, labels_valid)
    ch = calinski_harabasz_score(X_valid, labels_valid)

    print(f"\n[Validacio - {nev}]")
    print(f"  Silhouette Score:        {sil:+.4f}  (kozelebb +1-hez = jobb)")
    print(f"  Davies-Bouldin Index:    {db:.4f}   (alacsonyabb = jobb)")
    print(f"  Calinski-Harabasz Index: {ch:.2f}  (magasabb = jobb)")

    return {"silhouette": sil, "davies_bouldin": db, "calinski_harabasz": ch}


# =============================================================================
# 9. ELBOW MODSZER VIZUALIZACIO
# =============================================================================

def elbow_modszer(X, k_min=2, k_max=10):
    """
    Elbow (konyok) modszer a K-Means optimalis K ertekenek meghatarozasahoz.

    Az inertia (WCSS - Within-Cluster Sum of Squares) az egyes klaszterek
    pontjainak a centroidtol mert negyzetes tavolsagosszege. K novelesekor
    az inertia csokken, de egy pont utan a javulas merteke lelassul - ez a "konyok".

    Az optimalis K ott van, ahol a gorbe megtörik (konyok pont).

    Args:
        X: skalazott bemeneti adatok
        k_min: minimum K ertek
        k_max: maximum K ertek
    """
    k_values = range(k_min, k_max + 1)
    inertias = []
    silhouette_scores = []

    for k in k_values:
        kmeans = KMeans(n_clusters=k, init="k-means++", n_init=10, random_state=42)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(X, kmeans.labels_))

    # Ket panelos abra: Inertia + Silhouette
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Bal panel: Elbow gorbe (Inertia)
    ax1.plot(k_values, inertias, "bo-", linewidth=2, markersize=8)
    ax1.set_xlabel("Klaszterek szama (K)", fontsize=12)
    ax1.set_ylabel("Inertia (WCSS)", fontsize=12)
    ax1.set_title("Elbow modszer - Optimalis K meghatarozasa", fontsize=13)
    ax1.set_xticks(list(k_values))
    ax1.grid(True, alpha=0.3)

    # Konyok pont megjelolese (a legnagyobb inertia-csokkenesi valtozas)
    inertia_diffs = np.diff(inertias)
    inertia_diff2 = np.diff(inertia_diffs)
    konyok_idx = np.argmax(np.abs(inertia_diff2)) + 2  # +2 mert k_min=2 es diff2
    konyok_k = k_min + konyok_idx
    ax1.axvline(x=konyok_k, color="r", linestyle="--", alpha=0.7,
                label=f"Konyok pont: K={konyok_k}")
    ax1.legend(fontsize=11)

    # Jobb panel: Silhouette score K fuggvenyeben
    ax2.plot(k_values, silhouette_scores, "rs-", linewidth=2, markersize=8)
    ax2.set_xlabel("Klaszterek szama (K)", fontsize=12)
    ax2.set_ylabel("Silhouette Score", fontsize=12)
    ax2.set_title("Silhouette Score a klaszterszam fuggvenyeben", fontsize=13)
    ax2.set_xticks(list(k_values))
    ax2.grid(True, alpha=0.3)

    # Legjobb silhouette pont kiemelese
    best_k = list(k_values)[np.argmax(silhouette_scores)]
    ax2.axvline(x=best_k, color="g", linestyle="--", alpha=0.7,
                label=f"Legjobb K={best_k} (sil={max(silhouette_scores):.3f})")
    ax2.legend(fontsize=11)

    plt.tight_layout()
    plt.show()

    print(f"[Elbow] Javasolt K (konyok): {konyok_k}")
    print(f"[Elbow] Legjobb Silhouette K: {best_k}")


# =============================================================================
# 10. SILHOUETTE ANALIZIS VIZUALIZACIO
# =============================================================================

def silhouette_analizis(X, labels, n_klaszter, cim=""):
    """
    Reszletes Silhouette analizis vizualizacio.

    Minden adatponthoz megmutatja a silhouette erteket, klaszterenkent csoportositva.
    A jol szeparalt klaszterekben a pontok silhouette erteke kozel van 1-hez.
    A rosszul besorolt pontoknak negativ ertekuk van.

    Args:
        X: bemeneti adatok
        labels: klaszter cimkek
        n_klaszter: klaszterek szama
        cim: az abra cime
    """
    # Zajpontok kiszurese
    mask = labels != -1
    X_valid = X[mask]
    labels_valid = labels[mask]

    if len(set(labels_valid)) < 2:
        print("[Silhouette analizis] Nem eleg klaszter az analizishez.")
        return

    # Silhouette ertekek szamitasa minden pontra
    sample_silhouette_values = silhouette_samples(X_valid, labels_valid)
    avg_score = silhouette_score(X_valid, labels_valid)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_title(f"Silhouette analizis - {cim}" if cim else "Silhouette analizis",
                 fontsize=14)

    y_lower = 10  # also hatar az abran
    szinek = cm.nipy_spectral(np.linspace(0.1, 0.9, n_klaszter))

    for i in range(n_klaszter):
        # Az i-edik klaszter silhouette ertekei
        klaszter_sil_values = sample_silhouette_values[labels_valid == i]
        klaszter_sil_values.sort()

        meret = klaszter_sil_values.shape[0]
        y_upper = y_lower + meret

        ax.fill_betweenx(
            np.arange(y_lower, y_upper),
            0,
            klaszter_sil_values,
            facecolor=szinek[i],
            edgecolor=szinek[i],
            alpha=0.7
        )
        # Klaszter cimke az y tengelyen
        ax.text(-0.05, y_lower + 0.5 * meret, str(i), fontsize=11, fontweight="bold")
        y_lower = y_upper + 10

    # Atlagos silhouette erteket jelzo fuggoleges vonal
    ax.axvline(x=avg_score, color="red", linestyle="--", linewidth=2,
               label=f"Atlag silhouette: {avg_score:.3f}")

    ax.set_xlabel("Silhouette ertek", fontsize=12)
    ax.set_ylabel("Klaszter", fontsize=12)
    ax.set_yticks([])  # y cimkeket nem kell mutatni
    ax.legend(loc="best", fontsize=11)
    ax.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    plt.show()


# =============================================================================
# 11. KLASZTEREZESI EREDMENYEK VIZUALIZACIO (2D SCATTER)
# =============================================================================

def klaszter_vizualizacio(X, labels, centroids=None, cim="Klaszterezes", ax=None):
    """
    2D scatter plot a klaszterezesi eredmenyekrol.

    Args:
        X: 2D bemeneti adatok (n_samples, 2)
        labels: klaszter cimkek
        centroids: kozeppontok (opcionalis, K-Means-hez)
        cim: az abra cime
        ax: matplotlib axis (opcionalis, tobb abra egyben)
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 7))

    # Egyedi klaszterek szinei
    egyedi_cimkek = sorted(set(labels))
    n_szin = len(egyedi_cimkek)
    szinek = cm.nipy_spectral(np.linspace(0.1, 0.9, max(n_szin, 2)))

    for i, cimke in enumerate(egyedi_cimkek):
        mask = labels == cimke
        if cimke == -1:
            # Zajpontok (DBSCAN/HDBSCAN) szurkevel es kisebb merettel
            ax.scatter(X[mask, 0], X[mask, 1], c="gray", marker="x",
                       s=30, alpha=0.5, label="Zaj (noise)")
        else:
            ax.scatter(X[mask, 0], X[mask, 1], c=[szinek[i]], marker="o",
                       s=40, alpha=0.7, edgecolors="k", linewidths=0.3,
                       label=f"Klaszter {cimke}")

    # Centroidok rajzolasa (ha vannak)
    if centroids is not None:
        ax.scatter(centroids[:, 0], centroids[:, 1],
                   c="red", marker="*", s=300, edgecolors="black",
                   linewidths=1.5, zorder=5, label="Centroid")

    ax.set_title(cim, fontsize=14)
    ax.set_xlabel("Feature 1", fontsize=11)
    ax.set_ylabel("Feature 2", fontsize=11)
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.2)


def osszes_eredmeny_megjelenites(X_blobs, eredmenyek_blobs, X_moons, eredmenyek_moons):
    """
    Az osszes klaszterezo algoritmus eredmenyenek osszehasonlitasa
    egyszerre ket adathalmazon.

    Args:
        X_blobs: gomb alaku adat
        eredmenyek_blobs: dict {nev: (labels, centroids_or_None)}
        X_moons: felhold alaku adat
        eredmenyek_moons: dict {nev: (labels, centroids_or_None)}
    """
    n_alg = max(len(eredmenyek_blobs), len(eredmenyek_moons))
    fig, axes = plt.subplots(2, n_alg, figsize=(5 * n_alg, 10))

    # Ha csak egy algoritmus van, biztositjuk a 2D indexelest
    if n_alg == 1:
        axes = axes.reshape(2, 1)

    fig.suptitle("Klaszterezo algoritmusok osszehasonlitasa", fontsize=16, y=1.02)

    # Felso sor: blobs adat
    for i, (nev, (labels, centroids)) in enumerate(eredmenyek_blobs.items()):
        klaszter_vizualizacio(X_blobs, labels, centroids=centroids,
                              cim=f"{nev}\n(blobs)", ax=axes[0, i])

    # Also sor: moons adat
    for i, (nev, (labels, centroids)) in enumerate(eredmenyek_moons.items()):
        klaszter_vizualizacio(X_moons, labels, centroids=centroids,
                              cim=f"{nev}\n(moons)", ax=axes[1, i])

    plt.tight_layout()
    plt.show()


# =============================================================================
# FO PROGRAM
# =============================================================================

if __name__ == "__main__":

    print("=" * 70)
    print("  KLASZTEREZESI ALGORITMUSOK - OSSZEFOGLALO PELDA")
    print("=" * 70)

    # -----------------------------------------------------------------
    # 1. Adatok generalasa es eloeldolgozas
    # -----------------------------------------------------------------
    print("\n--- 1. Adatok generalasa es skalazas ---")
    X_blobs, y_blobs, X_moons, y_moons = adatok_generalasa()

    print(f"\nBlobs adathalmaz: {X_blobs.shape[0]} pont, {X_blobs.shape[1]} feature")
    print(f"Moons adathalmaz: {X_moons.shape[0]} pont, {X_moons.shape[1]} feature")

    # Skalazas
    X_blobs_scaled = adatok_skalazasa(X_blobs, modszer="standard")
    X_moons_scaled = adatok_skalazasa(X_moons, modszer="standard")

    # -----------------------------------------------------------------
    # 9. Elbow modszer (K-Means optimalis K meghatarozasa)
    # -----------------------------------------------------------------
    print("\n--- 9. Elbow modszer vizualizacio ---")
    elbow_modszer(X_blobs_scaled, k_min=2, k_max=10)

    # -----------------------------------------------------------------
    # 2. K-Means
    # -----------------------------------------------------------------
    print("\n--- 2. K-Means klaszterezes ---")
    kmeans_labels_blobs, kmeans_centroids_blobs, _ = kmeans_klaszterezes(
        X_blobs_scaled, n_klaszter=4
    )
    kmeans_labels_moons, kmeans_centroids_moons, _ = kmeans_klaszterezes(
        X_moons_scaled, n_klaszter=2
    )

    # -----------------------------------------------------------------
    # 3. Hierarchikus klaszterezes
    # -----------------------------------------------------------------
    print("\n--- 3. Hierarchikus klaszterezes ---")

    # Dendrogram rajzolasa
    dendrogram_rajzolas(X_blobs_scaled, linkage_method="ward", cut_level=5.0)

    hier_labels_blobs, _ = hierarchikus_klaszterezes(
        X_blobs_scaled, n_klaszter=4, linkage="ward"
    )
    hier_labels_moons, _ = hierarchikus_klaszterezes(
        X_moons_scaled, n_klaszter=2, linkage="ward"
    )

    # -----------------------------------------------------------------
    # 4. Spectral Clustering
    # -----------------------------------------------------------------
    print("\n--- 4. Spectral Clustering ---")
    spectral_labels_blobs, _ = spectral_klaszterezes(
        X_blobs_scaled, n_klaszter=4, affinity="nearest_neighbors"
    )
    spectral_labels_moons, _ = spectral_klaszterezes(
        X_moons_scaled, n_klaszter=2, affinity="nearest_neighbors"
    )

    # -----------------------------------------------------------------
    # 5. Gaussian Mixture Model (soft clustering)
    # -----------------------------------------------------------------
    print("\n--- 5. Gaussian Mixture Model ---")
    gmm_labels_blobs, gmm_probs_blobs, _ = gmm_klaszterezes(
        X_blobs_scaled, n_komponens=4
    )
    gmm_labels_moons, gmm_probs_moons, _ = gmm_klaszterezes(
        X_moons_scaled, n_komponens=2
    )

    # -----------------------------------------------------------------
    # 6. DBSCAN
    # -----------------------------------------------------------------
    print("\n--- 6. DBSCAN ---")
    dbscan_labels_blobs, _ = dbscan_klaszterezes(
        X_blobs_scaled, eps=0.3, min_samples=5
    )
    dbscan_labels_moons, _ = dbscan_klaszterezes(
        X_moons_scaled, eps=0.3, min_samples=5
    )

    # -----------------------------------------------------------------
    # 7. HDBSCAN (opcionalis)
    # -----------------------------------------------------------------
    print("\n--- 7. HDBSCAN (opcionalis) ---")
    hdbscan_labels_blobs, _ = hdbscan_klaszterezes(
        X_blobs_scaled, min_cluster_size=15, min_samples=5
    )
    hdbscan_labels_moons, _ = hdbscan_klaszterezes(
        X_moons_scaled, min_cluster_size=15, min_samples=5
    )

    # -----------------------------------------------------------------
    # 8. Klaszter-validacios metrikak
    # -----------------------------------------------------------------
    print("\n--- 8. Klaszter-validacios metrikak ---")
    validacio_eredmenyek = {}
    validacio_eredmenyek["K-Means"] = klaszter_validacio(
        X_blobs_scaled, kmeans_labels_blobs, nev="K-Means (blobs)"
    )
    validacio_eredmenyek["Hierarchikus"] = klaszter_validacio(
        X_blobs_scaled, hier_labels_blobs, nev="Hierarchikus (blobs)"
    )
    validacio_eredmenyek["Spectral"] = klaszter_validacio(
        X_blobs_scaled, spectral_labels_blobs, nev="Spectral (blobs)"
    )
    validacio_eredmenyek["GMM"] = klaszter_validacio(
        X_blobs_scaled, gmm_labels_blobs, nev="GMM (blobs)"
    )
    validacio_eredmenyek["DBSCAN"] = klaszter_validacio(
        X_blobs_scaled, dbscan_labels_blobs, nev="DBSCAN (blobs)"
    )

    # -----------------------------------------------------------------
    # Metrikak osszefoglalo tablazat
    # -----------------------------------------------------------------
    print("\n--- Metrikak osszefoglalo tablazat (blobs adathalmaz) ---")
    print(f"{'Algoritmus':<18} {'Silhouette':>12} {'Davies-Bouldin':>16} {'Calinski-H.':>14}")
    print("-" * 62)
    for nev, metrikak in validacio_eredmenyek.items():
        if metrikak:
            print(
                f"{nev:<18} "
                f"{metrikak['silhouette']:>+12.4f} "
                f"{metrikak['davies_bouldin']:>16.4f} "
                f"{metrikak['calinski_harabasz']:>14.2f}"
            )

    # -----------------------------------------------------------------
    # 10. Silhouette analizis vizualizacio
    # -----------------------------------------------------------------
    print("\n--- 10. Silhouette analizis ---")
    silhouette_analizis(
        X_blobs_scaled, kmeans_labels_blobs, n_klaszter=4, cim="K-Means (blobs)"
    )

    # -----------------------------------------------------------------
    # 11. Osszes eredmeny vizualizacio (2D scatter)
    # -----------------------------------------------------------------
    print("\n--- 11. Klaszterezesi eredmenyek vizualizacio ---")

    # Eredmenyek osszegyujtese
    eredmenyek_blobs = {
        "K-Means": (kmeans_labels_blobs, kmeans_centroids_blobs),
        "Hierarchikus": (hier_labels_blobs, None),
        "Spectral": (spectral_labels_blobs, None),
        "GMM": (gmm_labels_blobs, None),
        "DBSCAN": (dbscan_labels_blobs, None),
    }

    eredmenyek_moons = {
        "K-Means": (kmeans_labels_moons, kmeans_centroids_moons),
        "Hierarchikus": (hier_labels_moons, None),
        "Spectral": (spectral_labels_moons, None),
        "GMM": (gmm_labels_moons, None),
        "DBSCAN": (dbscan_labels_moons, None),
    }

    # HDBSCAN hozzaadasa ha elerheto
    if hdbscan_labels_blobs is not None:
        eredmenyek_blobs["HDBSCAN"] = (hdbscan_labels_blobs, None)
    if hdbscan_labels_moons is not None:
        eredmenyek_moons["HDBSCAN"] = (hdbscan_labels_moons, None)

    # Megjelenites
    osszes_eredmeny_megjelenites(
        X_blobs_scaled, eredmenyek_blobs,
        X_moons_scaled, eredmenyek_moons
    )

    print("\n" + "=" * 70)
    print("  KESZ - Klaszterezesi algoritmusok bemutatasa befejezodott.")
    print("=" * 70)
