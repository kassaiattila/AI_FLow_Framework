"""
Dimenziócsökkentési módszerek áttekintése
=========================================

Ez a fájl a legfontosabb dimenziócsökkentő (dimensionality reduction) algoritmusokat
mutatja be scikit-learn segítségével, vizualizációval kiegészítve.

Tartalomjegyzék:
    1. PCA  – Principal Component Analysis
    2. SVD  – Truncated SVD (ritka mátrixokhoz)
    3. LDA  – Linear Discriminant Analysis (felügyelt)
    4. Kernel PCA – nemlineáris PCA (RBF, poly)
    5. MDS  – Multidimensional Scaling
    6. Isomap
    7. LLE  – Locally Linear Embedding
    8. t-SNE – t-distributed Stochastic Neighbor Embedding
    9. UMAP – Uniform Manifold Approximation and Projection (opcionális)
   10. Összehasonlító vizualizáció

Forrás: Cubix ML Engineer – Unsupervised Learning tananyag (6. hét)
"""

import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA, KernelPCA, TruncatedSVD
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.manifold import MDS, TSNE, Isomap, LocallyLinearEmbedding
from sklearn.preprocessing import StandardScaler

# UMAP opcionális – csak akkor használjuk, ha telepítve van
try:
    from umap import UMAP
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

# Figyelmeztetések elnyomása a tisztább kimenet érdekében
warnings.filterwarnings("ignore")


# =============================================================================
# Segédfüggvények
# =============================================================================

def load_data():
    """
    Digits adathalmaz betöltése és standardizálása.
    A digits adathalmaz 8x8-as kézzel írt számjegyképeket tartalmaz (0–9),
    ami 64 dimenziós – ideális dimenziócsökkentési példákhoz.
    """
    digits = load_digits()
    X = digits.data          # (1797, 64) – 64 jellemző
    y = digits.target        # 10 osztály (0–9)
    feature_names = [f"pixel_{i}" for i in range(X.shape[1])]

    # Standardizálás – sok módszernél fontos
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"Digits adathalmaz betöltve: {X.shape[0]} minta, {X.shape[1]} jellemző, "
          f"{len(np.unique(y))} osztály")
    return X_scaled, y, feature_names


def plot_2d(X_2d, y, title, ax=None):
    """2D scatter plot készítése a transzformált adatokból."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(
        X_2d[:, 0], X_2d[:, 1],
        c=y, cmap="tab10", s=8, alpha=0.7, edgecolors="none"
    )
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("1. komponens")
    ax.set_ylabel("2. komponens")
    # Színskála (legend) hozzáadása
    if ax.get_figure() is not None:
        cbar = ax.get_figure().colorbar(scatter, ax=ax, ticks=range(10))
        cbar.set_label("Osztály")
    return ax


# =============================================================================
# 1. PCA – Principal Component Analysis
# =============================================================================

def demo_pca(X, y):
    """
    PCA: a legklasszikusabb lineáris dimenziócsökkentő módszer.

    A PCA a legnagyobb varianciájú irányokat (főkomponenseket) keresi az adatokban.
    A főkomponensek egymásra merőlegesek (ortogonálisak).

    Fontos attribútumok:
        - explained_variance_ratio_: az egyes komponensek által megőrzött variancia aránya
        - components_: a főkomponensek (a jellemzőtérben)
    """
    print("\n" + "=" * 70)
    print("1. PCA – Principal Component Analysis")
    print("=" * 70)

    # --- 1a. Teljes PCA illesztése a variancia vizsgálatához ---
    pca_full = PCA()  # n_components megadása nélkül: minden komponenst megtart
    pca_full.fit(X)

    explained_var = pca_full.explained_variance_ratio_
    cumulative_var = np.cumsum(explained_var)

    # Hány komponens kell a variancia 95%-ának megőrzéséhez?
    n_95 = np.argmax(cumulative_var >= 0.95) + 1
    print(f"  A variancia 95%-ának megőrzéséhez {n_95} komponens szükséges "
          f"(az eredeti {X.shape[1]}-ből)")

    # --- 1b. Scree plot (könyök-diagram) ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Egyedi variancia-arányok
    axes[0].bar(range(1, len(explained_var) + 1), explained_var, alpha=0.7, color="steelblue")
    axes[0].set_xlabel("Főkomponens sorszáma")
    axes[0].set_ylabel("Megőrzött variancia aránya")
    axes[0].set_title("Scree plot – egyedi variancia")
    axes[0].set_xlim(0, 30)  # Az első 30 komponens

    # Kumulatív variancia
    axes[1].plot(range(1, len(cumulative_var) + 1), cumulative_var, "o-", color="darkorange")
    axes[1].axhline(y=0.95, color="red", linestyle="--", label="95% küszöb")
    axes[1].axvline(x=n_95, color="green", linestyle="--", alpha=0.7, label=f"{n_95} komponens")
    axes[1].set_xlabel("Komponensek száma")
    axes[1].set_ylabel("Kumulatív megőrzött variancia")
    axes[1].set_title("Kumulatív variancia – hány komponens elég?")
    axes[1].legend()
    axes[1].set_xlim(0, 30)

    plt.suptitle("PCA – Scree plot és kumulatív variancia", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()

    # --- 1c. 2D vetítés ---
    pca_2d = PCA(n_components=2)
    X_pca = pca_2d.fit_transform(X)

    print(f"  2D PCA megőrzött variancia: {pca_2d.explained_variance_ratio_.sum():.2%}")

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_2d(X_pca, y, "PCA – 2D vetítés (digits)", ax=ax)
    plt.tight_layout()
    plt.show()

    return X_pca


# =============================================================================
# 2. SVD – Truncated SVD (Singular Value Decomposition)
# =============================================================================

def demo_svd(X, y):
    """
    TruncatedSVD: hasonló célú, mint a PCA, de ritka (sparse) mátrixokkal is működik.

    Tipikus felhasználás:
        - NLP (szövegbányászat): TF-IDF mátrixok csökkentése
        - Ajánlórendszerek: felhasználó-termék mátrixok

    A PCA-val ellentétben NEM központosítja (mean-center) az adatokat,
    ezért ritka mátrixok esetén megőrzi a ritkasági struktúrát.
    """
    print("\n" + "=" * 70)
    print("2. Truncated SVD – ritka mátrixokhoz")
    print("=" * 70)

    # Ritka mátrix készítése demonstrációhoz
    X_sparse = csr_matrix(X)
    print(f"  Ritka mátrix típusa: {type(X_sparse).__name__}, "
          f"nem-nulla elemek: {X_sparse.nnz} / {X_sparse.shape[0] * X_sparse.shape[1]} "
          f"({X_sparse.nnz / (X_sparse.shape[0] * X_sparse.shape[1]):.1%})")

    # SVD illesztése
    svd = TruncatedSVD(n_components=2, random_state=42)
    X_svd = svd.fit_transform(X_sparse)

    total_var = svd.explained_variance_ratio_.sum()
    print(f"  2D SVD megőrzött variancia: {total_var:.2%}")

    # Vizualizáció
    fig, ax = plt.subplots(figsize=(8, 6))
    plot_2d(X_svd, y, "Truncated SVD – 2D vetítés (sparse digits)", ax=ax)
    plt.tight_layout()
    plt.show()

    return X_svd


# =============================================================================
# 3. LDA – Linear Discriminant Analysis (felügyelt dimenziócsökkentés)
# =============================================================================

def demo_lda(X, y):
    """
    LDA: felügyelt (supervised) lineáris dimenziócsökkentő módszer.

    A PCA-val ellentétben az LDA figyelembe veszi az osztálycímkéket (y).
    Célja: maximalizálni az osztályok közötti szórást, miközben minimalizálja
    az osztályokon belüli szórást.

    Korlátok:
        - Legfeljebb (n_classes - 1) komponens hozható létre
        - Feltételezi, hogy az osztályok normális eloszlásúak
        - A digits adatnál: max 9 komponens (10 osztály - 1)
    """
    print("\n" + "=" * 70)
    print("3. LDA – Linear Discriminant Analysis (felügyelt)")
    print("=" * 70)

    n_classes = len(np.unique(y))
    max_components = min(n_classes - 1, X.shape[1])
    print(f"  Osztályok száma: {n_classes}, "
          f"max LDA komponensek: {max_components}")

    # 2D LDA
    lda = LinearDiscriminantAnalysis(n_components=2)
    X_lda = lda.fit_transform(X, y)  # Az LDA-nak szüksége van y-ra!

    print(f"  2D LDA megőrzött variancia: {lda.explained_variance_ratio_[:2].sum():.2%}")

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_2d(X_lda, y, "LDA – 2D vetítés (felügyelt, digits)", ax=ax)
    plt.tight_layout()
    plt.show()

    return X_lda


# =============================================================================
# 4. Kernel PCA – nemlineáris PCA
# =============================================================================

def demo_kernel_pca(X, y):
    """
    Kernel PCA: a PCA nemlineáris kiterjesztése kernel trükk segítségével.

    A kernel trükk lehetővé teszi, hogy az adatokat implicit módon egy
    magasabb dimenziós térbe képezzük le, ahol lineáris PCA-t alkalmazunk.

    Gyakori kernelek:
        - 'rbf'   : Radial Basis Function (Gauss) – általános célú
        - 'poly'  : polinomiális – polinomiális kapcsolatok
        - 'sigmoid': szigmoid
        - 'cosine': koszinusz hasonlóság
    """
    print("\n" + "=" * 70)
    print("4. Kernel PCA – nemlineáris dimenziócsökkentés")
    print("=" * 70)

    kernels = ["rbf", "poly"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, kernel in enumerate(kernels):
        # gamma='scale' automatikusan beállítja az RBF gamma paraméterét
        kpca = KernelPCA(n_components=2, kernel=kernel, gamma=10, random_state=42)
        X_kpca = kpca.fit_transform(X)

        print(f"  Kernel: {kernel} – transzformált alak: {X_kpca.shape}")

        plot_2d(X_kpca, y, f"Kernel PCA ({kernel} kernel)", ax=axes[idx])

    plt.suptitle("Kernel PCA – különböző kernelek összehasonlítása",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()

    return X_kpca


# =============================================================================
# 5. MDS – Multidimensional Scaling
# =============================================================================

def demo_mds(X, y):
    """
    MDS: a pontok közötti távolságok megőrzésére törekszik alacsonyabb dimenzióban.

    A metrikás MDS megpróbálja megőrizni a pontpárok közötti euklideszi
    távolságokat. Számításigényes nagy adathalmazoknál.

    Megjegyzés: az MDS nem determinisztikus, ezért random_state-et használunk.
    """
    print("\n" + "=" * 70)
    print("5. MDS – Multidimensional Scaling")
    print("=" * 70)

    # Csak az adatok egy részén futtatjuk, mert az MDS O(n^2) memóriát igényel
    n_samples = min(500, X.shape[0])
    indices = np.random.RandomState(42).choice(X.shape[0], n_samples, replace=False)
    X_sub = X[indices]
    y_sub = y[indices]

    print(f"  {n_samples} mintán futtatjuk (az MDS lassú nagy adatokon)")

    start = time.time()
    mds = MDS(n_components=2, random_state=42, normalized_stress="auto")
    X_mds = mds.fit_transform(X_sub)
    elapsed = time.time() - start

    print(f"  Futási idő: {elapsed:.1f} mp")
    print(f"  Stress érték: {mds.stress_:.2f}")

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_2d(X_mds, y_sub, f"MDS – 2D vetítés ({n_samples} minta)", ax=ax)
    plt.tight_layout()
    plt.show()

    return X_mds


# =============================================================================
# 6. Isomap
# =============================================================================

def demo_isomap(X, y):
    """
    Isomap: nemlineáris dimenziócsökkentés geodéziai távolságok alapján.

    Az Isomap a pontok közötti legrövidebb gráf-útvonalat (geodéziai távolságot)
    használja az euklideszi távolság helyett. Ez lehetővé teszi görbült
    sokaságok (manifold) helyes kibontását.

    Fontos paraméter:
        - n_neighbors: hány szomszédot vegyen figyelembe a gráf építésekor
    """
    print("\n" + "=" * 70)
    print("6. Isomap – geodéziai távolságon alapuló beágyazás")
    print("=" * 70)

    n_neighbors_list = [5, 15, 30]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, n_neighbors in enumerate(n_neighbors_list):
        isomap = Isomap(n_components=2, n_neighbors=n_neighbors)
        X_isomap = isomap.fit_transform(X)

        print(f"  n_neighbors={n_neighbors}: rekonstrukciós hiba = "
              f"{isomap.reconstruction_error():.4f}")

        plot_2d(X_isomap, y, f"Isomap (n_neighbors={n_neighbors})", ax=axes[idx])

    plt.suptitle("Isomap – szomszédszám hatása", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()

    return X_isomap


# =============================================================================
# 7. LLE – Locally Linear Embedding
# =============================================================================

def demo_lle(X, y):
    """
    LLE: lokálisan lineáris beágyazás.

    Minden pontot a szomszédai lineáris kombinációjaként rekonstruál,
    majd megkeresi az alacsonyabb dimenziós beágyazást, amely megőrzi
    ezeket a lokális lineáris kapcsolatokat.

    Fontos paraméter:
        - n_neighbors: a lokális környezet mérete
    """
    print("\n" + "=" * 70)
    print("7. LLE – Locally Linear Embedding")
    print("=" * 70)

    lle = LocallyLinearEmbedding(n_components=2, n_neighbors=12, random_state=42)
    X_lle = lle.fit_transform(X)

    print(f"  Rekonstrukciós hiba: {lle.reconstruction_error_:.6f}")

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_2d(X_lle, y, "LLE – 2D vetítés (digits)", ax=ax)
    plt.tight_layout()
    plt.show()

    return X_lle


# =============================================================================
# 8. t-SNE – t-distributed Stochastic Neighbor Embedding
# =============================================================================

def demo_tsne(X, y):
    """
    t-SNE: az egyik legjobb módszer magas dimenziós adatok 2D vizualizációjára.

    A t-SNE a lokális struktúrákat őrzi meg különösen jól.
    NEM alkalmas dimenziócsökkentésre gépi tanulási pipeline-ban
    (csak vizualizációra), mert:
        - nincs transform() metódusa (nem transzformálható új adatra)
        - a Barnes-Hut algoritmus csak 2D és 3D-t támogat
        - a futási ideje O(n^2) vagy O(n*log(n)) a Barnes-Hut változatnál

    Fontos paraméter:
        - perplexity: a lokális szomszédság méretét befolyásolja (tipikusan 5–50)
    """
    print("\n" + "=" * 70)
    print("8. t-SNE – perplexity hatásának vizualizálása")
    print("=" * 70)

    perplexities = [5, 15, 30, 50]
    fig, axes = plt.subplots(1, 4, figsize=(22, 5))

    for idx, perp in enumerate(perplexities):
        start = time.time()
        tsne = TSNE(n_components=2, perplexity=perp, random_state=42, n_iter=1000)
        X_tsne = tsne.fit_transform(X)
        elapsed = time.time() - start

        print(f"  perplexity={perp:2d}: KL-divergencia = {tsne.kl_divergence_:.4f}, "
              f"futás: {elapsed:.1f} mp")

        plot_2d(X_tsne, y, f"t-SNE (perplexity={perp})", ax=axes[idx])

    plt.suptitle("t-SNE – perplexity paraméter hatása", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()

    return X_tsne


# =============================================================================
# 9. UMAP – Uniform Manifold Approximation and Projection (opcionális)
# =============================================================================

def demo_umap(X, y):
    """
    UMAP: modern, gyors nemlineáris dimenziócsökkentő algoritmus.

    Előnyei a t-SNE-vel szemben:
        - gyorsabb (nagy adathalmazokon is használható)
        - jobban megőrzi a globális struktúrát
        - van transform() metódusa (alkalmazható új adatra)

    Telepítés: pip install umap-learn

    Fontos paraméterek:
        - n_neighbors: lokális/globális struktúra közti egyensúly
        - min_dist: mennyire sűrűn csoportosulhatnak a pontok
    """
    print("\n" + "=" * 70)
    print("9. UMAP – Uniform Manifold Approximation and Projection")
    print("=" * 70)

    if not UMAP_AVAILABLE:
        print("  [KIHAGYVA] Az umap-learn csomag nincs telepítve.")
        print("  Telepítés: pip install umap-learn")
        return None

    n_neighbors_list = [5, 15, 50]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, n_neighbors in enumerate(n_neighbors_list):
        start = time.time()
        reducer = UMAP(n_components=2, n_neighbors=n_neighbors, min_dist=0.1,
                       random_state=42)
        X_umap = reducer.fit_transform(X)
        elapsed = time.time() - start

        print(f"  n_neighbors={n_neighbors:2d}: futás: {elapsed:.1f} mp")

        plot_2d(X_umap, y, f"UMAP (n_neighbors={n_neighbors})", ax=axes[idx])

    plt.suptitle("UMAP – n_neighbors paraméter hatása", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()

    return X_umap


# =============================================================================
# 10. Összehasonlító vizualizáció – minden módszer egy ábrán
# =============================================================================

def demo_comparison(X, y):
    """
    Az összes dimenziócsökkentő módszer eredményének összehasonlítása
    egyetlen subplot-rácson.
    """
    print("\n" + "=" * 70)
    print("10. ÖSSZEHASONLÍTÓ VIZUALIZÁCIÓ")
    print("=" * 70)

    # Módszerek definiálása: (név, objektum, szükség van-e y-ra?)
    methods = [
        ("PCA", PCA(n_components=2), False),
        ("Truncated SVD", TruncatedSVD(n_components=2, random_state=42), False),
        ("LDA", LinearDiscriminantAnalysis(n_components=2), True),
        ("Kernel PCA (RBF)", KernelPCA(n_components=2, kernel="rbf", gamma=10), False),
        ("MDS", MDS(n_components=2, random_state=42, normalized_stress="auto"), False),
        ("Isomap", Isomap(n_components=2, n_neighbors=15), False),
        ("LLE", LocallyLinearEmbedding(n_components=2, n_neighbors=12, random_state=42), False),
        ("t-SNE", TSNE(n_components=2, perplexity=30, random_state=42), False),
    ]

    # UMAP hozzáadása, ha elérhető
    if UMAP_AVAILABLE:
        methods.append(
            ("UMAP", UMAP(n_components=2, n_neighbors=15, min_dist=0.1, random_state=42), False)
        )

    n_methods = len(methods)
    # MDS-hez kisebb minta kell a futásidő miatt
    n_samples_mds = min(500, X.shape[0])
    mds_indices = np.random.RandomState(42).choice(X.shape[0], n_samples_mds, replace=False)

    # Grid kiszámítása
    n_cols = 3
    n_rows = int(np.ceil(n_methods / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
    axes = axes.flatten()

    for idx, (name, model, needs_y) in enumerate(methods):
        ax = axes[idx]

        # MDS és a nagy adatok kezelése
        if name == "MDS":
            X_input = X[mds_indices]
            y_input = y[mds_indices]
        else:
            X_input = X
            y_input = y

        print(f"  [{idx + 1}/{n_methods}] {name}...", end=" ", flush=True)
        start = time.time()

        try:
            if needs_y:
                X_2d = model.fit_transform(X_input, y_input)
            else:
                X_2d = model.fit_transform(X_input)

            elapsed = time.time() - start
            print(f"{elapsed:.1f} mp")

            scatter = ax.scatter(
                X_2d[:, 0], X_2d[:, 1],
                c=y_input, cmap="tab10", s=5, alpha=0.7, edgecolors="none"
            )
            suffix = f" ({n_samples_mds} minta)" if name == "MDS" else ""
            ax.set_title(f"{name}{suffix}", fontsize=11, fontweight="bold")
            ax.set_xticks([])
            ax.set_yticks([])

        except Exception as e:
            elapsed = time.time() - start
            print(f"HIBA: {e}")
            ax.set_title(f"{name} – HIBA", fontsize=11, color="red")
            ax.text(0.5, 0.5, str(e), ha="center", va="center",
                    transform=ax.transAxes, fontsize=8)

    # Üres subplot-ok elrejtése
    for idx in range(n_methods, len(axes)):
        axes[idx].set_visible(False)

    # Közös színskála
    cbar = fig.colorbar(scatter, ax=axes[:n_methods].tolist(), shrink=0.6,
                        ticks=range(10), pad=0.02)
    cbar.set_label("Osztály (számjegy)", fontsize=11)

    fig.suptitle("Dimenziócsökkentő módszerek összehasonlítása – Digits adathalmaz",
                 fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.show()


# =============================================================================
# Összefoglaló táblázat (szöveges)
# =============================================================================

def print_summary():
    """A módszerek rövid összefoglalása szöveges formában."""
    print("\n" + "=" * 70)
    print("MÓDSZEREK ÖSSZEFOGLALÓ TÁBLÁZATA")
    print("=" * 70)
    table = """
    Módszer       | Típus      | Felügyelt? | Fő előny                          | Fő korlát
    --------------|------------|------------|-----------------------------------|----------------------------------
    PCA           | Lineáris   | Nem        | Gyors, jól érthető                | Csak lineáris kapcsolatokat lát
    Truncated SVD | Lineáris   | Nem        | Ritka mátrixokkal is működik      | Nem központosít (mean-center)
    LDA           | Lineáris   | Igen       | Osztályokat jól szétválasztja      | Max (K-1) komponens
    Kernel PCA    | Nemlineáris| Nem        | Nemlineáris mintázatok kezelése   | Kernel és gamma hangolása kell
    MDS           | Nemlineáris| Nem        | Távolságokat megőrzi              | Lassú, O(n^2) memória
    Isomap        | Nemlineáris| Nem        | Görbült sokaságokat kibontja      | Érzékeny a szomszédszámra
    LLE           | Nemlineáris| Nem        | Lokális struktúrát megőrzi        | Érzékeny a szomszédszámra
    t-SNE         | Nemlineáris| Nem        | Kiváló 2D vizualizáció            | Nincs transform(), lassú
    UMAP          | Nemlineáris| Nem        | Gyors, globális struktúrát is őrzi| Külső csomag szükséges
    """
    print(table)


# =============================================================================
# Fő belépési pont
# =============================================================================

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║    DIMENZIÓCSÖKKENTÉSI MÓDSZEREK – Áttekintés és vizualizáció       ║")
    print("║    Forrás: Cubix ML Engineer – Unsupervised Learning (6. hét)       ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    # Adatok betöltése
    X, y, feature_names = load_data()

    # 1. PCA
    demo_pca(X, y)

    # 2. Truncated SVD
    demo_svd(X, y)

    # 3. LDA
    demo_lda(X, y)

    # 4. Kernel PCA
    demo_kernel_pca(X, y)

    # 5. MDS
    demo_mds(X, y)

    # 6. Isomap
    demo_isomap(X, y)

    # 7. LLE
    demo_lle(X, y)

    # 8. t-SNE
    demo_tsne(X, y)

    # 9. UMAP (ha elérhető)
    demo_umap(X, y)

    # 10. Összehasonlító vizualizáció
    demo_comparison(X, y)

    # Összefoglaló táblázat
    print_summary()

    print("\n  Kész! Minden módszer lefutott.")
