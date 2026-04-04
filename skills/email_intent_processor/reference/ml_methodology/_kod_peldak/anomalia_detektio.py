"""
Anomalia Detektio - Kod Peldak
==============================
11. fejezet: Anomalia Detektio

Tartalom:
    1. Adateloeszites anomalia detektiohoz
    2. GMM (Gaussian Mixture Model) anomalia detektio
    3. Isolation Forest anomalia detektio
    4. GMM + IF osszehasonlitas
    5. Self-supervised learning anomalia detektio
    6. Vizualizacio

A pelda szintetikus adatokat hasznal (make_blobs + injektalt anomaliak),
igy kulso CSV fajl nelkul is futtatahto.

Futtatas:
    python anomalia_detektio.py
"""

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# Sklearn - adatgeneralas
# Scipy - Z-score szamitas
from scipy.stats import zscore
from sklearn.datasets import make_blobs
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.impute import SimpleImputer

# Sklearn - anomalia detektio es regresszio
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import train_test_split

# Sklearn - eloeldolgozas
from sklearn.preprocessing import MinMaxScaler

# Matplotlib - vizualizacio (opcionalis)
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_ELERHETO = True
except ImportError:
    MATPLOTLIB_ELERHETO = False
    print("[INFO] A matplotlib csomag nem elerheto. Telepites: pip install matplotlib")
    print("       A vizualizacios funkciok kimaradnak.")

# t-SNE vizualizaciohoz (opcionalis, csak ha matplotlib is elerheto)
try:
    from sklearn.manifold import TSNE
    TSNE_ELERHETO = True
except ImportError:
    TSNE_ELERHETO = False


# =============================================================================
# 1. ADATELOESZITES ANOMALIA DETEKTIOHOZ
# =============================================================================

def szintetikus_adatok_generalasa(n_normalis=800, n_anomalia=40, n_features=10,
                                  random_state=42):
    """
    Szintetikus adathalmaz generalasa anomalia detektiohoz.
    Normalis pontok (make_blobs) + injektalt anomaliak (uniform a normalis tartomanyon kivul).

    Returns:
        tuple: (df, y_true, feature_names) - DataFrame, valos cimkek, feature nevek
    """
    np.random.seed(random_state)

    # Normalis adatpontok: 3 klaszter korul csoportosulnak
    X_normal, _ = make_blobs(
        n_samples=n_normalis,
        n_features=n_features,
        centers=3,
        cluster_std=1.5,
        random_state=random_state
    )

    # Anomaliak: szelsoseges, veletlenszeru ertekek
    # Az anomaliak a normalis tartomanyon kivulre esnek
    normal_min = X_normal.min(axis=0)
    normal_max = X_normal.max(axis=0)
    normal_range = normal_max - normal_min

    X_anomaliak = np.random.uniform(
        low=normal_min - 2.0 * normal_range,
        high=normal_max + 2.0 * normal_range,
        size=(n_anomalia, n_features)
    )

    # Teljes adathalmaz osszefuzese
    X_full = np.vstack([X_normal, X_anomaliak])
    y_true = np.array([0] * n_normalis + [1] * n_anomalia)

    # Keverjuk ossze az adatokat (az anomaliak ne a vegen legyenek)
    shuffle_idx = np.random.permutation(len(X_full))
    X_full = X_full[shuffle_idx]
    y_true = y_true[shuffle_idx]

    feature_names = [f"feature_{i}" for i in range(n_features)]
    df = pd.DataFrame(X_full, columns=feature_names)

    print(f"[Adatgeneralas] {len(df)} pont ({n_normalis} normalis + {n_anomalia} anomalia, "
          f"{n_anomalia / (n_normalis + n_anomalia):.2%}), {n_features} feature")

    return df, y_true, feature_names


def adatok_elokeszitese(df, hianyzo_arany=0.02, random_state=42):
    """
    Adateloeszites: hianyzo ertekek potlasa (median), log1p transzformacio,
    MinMax skalazas [0,1].

    Returns:
        tuple: (scaled_data, df_log) - skalazott numpy array es log-transzformalt DataFrame
    """
    np.random.seed(random_state)

    # Hianyzo ertekek szimulalasa
    df_with_nan = df.copy()
    n_hianyzo = int(df.size * hianyzo_arany)
    hianyzo_sorok = np.random.randint(0, df.shape[0], size=n_hianyzo)
    hianyzo_oszlopok = np.random.randint(0, df.shape[1], size=n_hianyzo)
    for s, o in zip(hianyzo_sorok, hianyzo_oszlopok, strict=False):
        df_with_nan.iat[s, o] = np.nan
    print(f"\n[Eloeszites] Hianyzo ertekek szimulalva: {df_with_nan.isna().sum().sum()}")

    # Hianyzo ertekek potlasa (median)
    df_imputed = pd.DataFrame(
        SimpleImputer(strategy='median').fit_transform(df_with_nan),
        columns=df.columns)

    # Log1p transzformacio (negativ ertekek shiftjeevel)
    df_shifted = df_imputed.copy()
    for col in df_shifted.columns:
        col_min = df_shifted[col].min()
        if col_min < 0:
            df_shifted[col] = df_shifted[col] - col_min
    df_log = pd.DataFrame(np.log1p(df_shifted), columns=df.columns)

    # MinMax skalazas [0, 1]
    scaled_data = MinMaxScaler().fit_transform(df_log)
    print(f"  Eloeszites kesz: imputer + log1p + MinMax [{scaled_data.min():.2f}, {scaled_data.max():.2f}]")

    return scaled_data, df_log


# =============================================================================
# 2. GMM (GAUSSIAN MIXTURE MODEL) ANOMALIA DETEKTIO
# =============================================================================

def gmm_anomalia_detektio(scaled_data, n_components=5, kvantilis=0.05,
                           random_state=42):
    """
    GMM alapu anomalia detektio: score_samples() log-likelihood + kvantilis threshold.
    Alacsony skor = valoszinuetlen pont = potencialis anomalia.

    Returns: (labels, scores, threshold, gm_model)
    """
    print(f"\n{'='*60}")
    print("  GMM ANOMALIA DETEKTIO")
    print(f"{'='*60}")

    gm = GaussianMixture(n_components=n_components, covariance_type='full',
                         random_state=random_state)
    gm.fit(scaled_data)

    # Log-valoszinusegi skorok + kvantilis threshold
    scores = gm.score_samples(scaled_data)
    threshold = np.quantile(scores, kvantilis)
    labels = [-1 if val <= threshold else 1 for val in scores]
    n_anomalia = labels.count(-1)

    print(f"  n_components={n_components}, kvantilis={kvantilis:.2%}, "
          f"threshold={threshold:.4f}")
    print(f"  Skor: [{scores.min():.4f}, {scores.max():.4f}] | "
          f"Anomaliak: {n_anomalia} ({n_anomalia/len(labels):.2%})")
    print(f"  BIC={gm.bic(scaled_data):.2f}, AIC={gm.aic(scaled_data):.2f}")

    return labels, scores, threshold, gm


# =============================================================================
# 3. ISOLATION FOREST ANOMALIA DETEKTIO
# =============================================================================

def isolation_forest_detektio(scaled_data, contamination=0.05,
                               n_estimators=100, random_state=42):
    """
    Isolation Forest anomalia detektio.
    Izolacio elve: anomaliak kevesebb vagassal izoalhatoak (rovid ut a faban).

    Returns: (labels, scores, iso_model) - -1=anomalia, 1=normalis
    """
    print(f"\n{'='*60}")
    print("  ISOLATION FOREST ANOMALIA DETEKTIO")
    print(f"{'='*60}")

    iso_forest = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        max_samples='auto',
        random_state=random_state
    )

    # fit_predict: illesztes es prediktalas egyben
    labels = iso_forest.fit_predict(scaled_data)

    # Anomalia szkorok (decision_function)
    scores = iso_forest.decision_function(scaled_data)

    # Statisztikak
    n_anomalia = (labels == -1).sum()

    print(f"  contamination={contamination:.2%}, n_estimators={n_estimators}")
    print(f"  Skor: [{scores.min():.4f}, {scores.max():.4f}] | "
          f"Anomaliak: {n_anomalia} ({n_anomalia/len(labels):.2%})")

    return labels, scores, iso_forest


# =============================================================================
# 4. GMM + ISOLATION FOREST OSSZEHASONLITAS
# =============================================================================

def modszerek_osszehasonlitasa(gmm_labels, if_labels, y_true=None):
    """
    GMM es IF eredmenyek osszehasonlitasa (consensus megkozelites).
    Ha mindketto -1: eros jelzes. Ha van y_true, precision/recall kiertekeles is.
    """
    print(f"\n{'='*60}")
    print("  GMM + ISOLATION FOREST OSSZEHASONLITAS")
    print(f"{'='*60}")

    # DataFrame az osszehasonlitashoz
    df = pd.DataFrame({
        'Labels_GMM': gmm_labels,
        'Labels_IF': if_labels
    })

    # Kategoriak szamolasa
    both_anomaly = len(df[(df['Labels_GMM'] == -1) & (df['Labels_IF'] == -1)])
    only_gmm = len(df[(df['Labels_GMM'] == -1) & (df['Labels_IF'] == 1)])
    only_if = len(df[(df['Labels_GMM'] == 1) & (df['Labels_IF'] == -1)])
    both_normal = len(df[(df['Labels_GMM'] == 1) & (df['Labels_IF'] == 1)])

    print(f"\n  Mindketto anomalia (-1, -1):  {both_anomaly:>5}  <-- eros jelzes")
    print(f"  Csak GMM anomalia (-1,  1):   {only_gmm:>5}  <-- gyanus")
    print(f"  Csak IF anomalia  ( 1, -1):   {only_if:>5}  <-- gyanus")
    print(f"  Mindketto normalis ( 1,  1):  {both_normal:>5}")

    # Egyezes aranya
    egyezes = (both_anomaly + both_normal) / len(df)
    print(f"\n  Egyezes aranya: {egyezes:.2%}")

    eredmeny = {
        'both_anomaly': both_anomaly,
        'only_gmm': only_gmm,
        'only_if': only_if,
        'both_normal': both_normal,
        'egyezes': egyezes
    }

    # Ha van valos cimke, kiertekeles
    if y_true is not None:
        print("\n  --- Kiertekeles valos cimkekhez kepest ---")

        # Konverzio: -1 --> 1 (anomalia), 1 --> 0 (normalis)
        gmm_pred = np.array([1 if x == -1 else 0 for x in gmm_labels])
        if_pred = np.array([1 if x == -1 else 0 for x in if_labels])
        consensus_pred = np.array([1 if g == -1 and i == -1 else 0
                                   for g, i in zip(gmm_labels, if_labels, strict=False)])

        valos_anomaliak = y_true.sum()
        print(f"  Valos anomaliak szama: {valos_anomaliak}")

        for nev, pred in [("GMM", gmm_pred), ("IF", if_pred),
                          ("Consensus", consensus_pred)]:
            tp = ((pred == 1) & (y_true == 1)).sum()
            fp = ((pred == 1) & (y_true == 0)).sum()
            fn = ((pred == 0) & (y_true == 1)).sum()
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = (2 * precision * recall / (precision + recall)
                  if (precision + recall) > 0 else 0)
            print(f"  {nev:>10}: TP={tp:>3}, FP={fp:>3}, "
                  f"Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}")

        eredmeny['evaluation'] = True

    return eredmeny


# =============================================================================
# 5. SELF-SUPERVISED LEARNING ANOMALIA DETEKTIO
# =============================================================================

def self_supervised_anomalia(df_log, target_column_idx=0, threshold_z=3.0,
                              test_size=0.2, random_state=42):
    """
    Self-supervised anomalia detektio: egy feature-t target-kent kezelunk,
    a tobbibol prediktaljuk (RF Regressor), es a nagy residualu (|z|>threshold)
    pontokat anomaliakent jeloljuk.

    Returns: (anomaly_indices, z_scores_arr, residuals_arr, test_indices)
    """
    print(f"\n{'='*60}")
    print("  SELF-SUPERVISED ANOMALIA DETEKTIO")
    print(f"{'='*60}")

    # Target feature kivalasztasa
    target_col = df_log.columns[target_column_idx]
    print(f"  Target feature: '{target_col}' (index: {target_column_idx})")

    # Features es target szeparalasa
    features = df_log.drop(columns=[target_col])
    target = df_log[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=test_size, random_state=random_state)
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

    # Random Forest Regressor betanitasa
    regressor = RandomForestRegressor(n_estimators=100, random_state=random_state)
    regressor.fit(X_train, y_train)

    # Predikcio, residualok, Z-score
    predictions = regressor.predict(X_test)
    residuals = y_test.values - predictions
    r2 = regressor.score(X_test, y_test)
    z_scores_arr = zscore(residuals)
    anomaly_mask = np.abs(z_scores_arr) > threshold_z
    anomaly_indices = np.where(anomaly_mask)[0]
    test_indices = X_test.index.values

    print(f"  R2: {r2:.4f} | Residual atlag: {residuals.mean():.6f}, "
          f"std: {residuals.std():.6f}")
    print(f"  Threshold: |z| > {threshold_z} | "
          f"Anomaliak: {len(anomaly_indices)}/{len(X_test)} "
          f"({len(anomaly_indices) / len(X_test):.2%})")

    # Feature importance (top 5)
    fi_df = pd.DataFrame({
        'feature': features.columns, 'importance': regressor.feature_importances_
    }).sort_values('importance', ascending=False)
    top5 = ", ".join(f"{r['feature']}={r['importance']:.3f}"
                     for _, r in fi_df.head(5).iterrows())
    print(f"  Top 5 feature: {top5}")

    return anomaly_indices, z_scores_arr, residuals, test_indices


# =============================================================================
# 6. VIZUALIZACIO
# =============================================================================

def anomalia_vizualizacio_2d(scaled_data, gmm_labels, if_labels, y_true=None):
    """
    Az anomalia detektio eredmenyeinek 2D vizualizacioja t-SNE vetitessel.
    Harom subplot: GMM, Isolation Forest, Consensus.
    """
    if not MATPLOTLIB_ELERHETO or not TSNE_ELERHETO:
        print("\n[SKIP] Vizualizacio: matplotlib vagy TSNE nem elerheto")
        return

    print(f"\n{'='*60}")
    print("  VIZUALIZACIO (t-SNE 2D vetites)")
    print(f"{'='*60}")
    print("  t-SNE szamitas folyamatban...")

    # t-SNE 2D vetites
    tsne = TSNE(n_components=2, perplexity=30, random_state=42, n_iter=300)
    embedding = tsne.fit_transform(scaled_data)

    gmm_arr = np.array(gmm_labels)
    if_arr = np.array(if_labels)
    consensus = np.ones(len(gmm_arr))
    consensus[(gmm_arr == -1) & (if_arr == -1)] = -1

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    normalis_szin, anomalia_szin, valos_szin = '#2196F3', '#F44336', '#FF9800'
    valos_mask = y_true == 1 if y_true is not None else None

    # Kozos rajzolo segedfuggveny
    cimkek_lista = [
        (gmm_arr, f"GMM (anomalia: {(gmm_arr == -1).sum()})"),
        (if_arr, f"Isolation Forest (anomalia: {(if_arr == -1).sum()})"),
        (consensus, f"Consensus (anomalia: {(consensus == -1).sum()})"),
    ]
    for ax, (labels_arr, cim) in zip(axes, cimkek_lista, strict=False):
        szinek = [anomalia_szin if x == -1 else normalis_szin for x in labels_arr]
        ax.scatter(embedding[:, 0], embedding[:, 1], c=szinek, s=10, alpha=0.6)
        if valos_mask is not None:
            ax.scatter(embedding[valos_mask, 0], embedding[valos_mask, 1],
                       facecolors='none', edgecolors=valos_szin, s=60,
                       linewidths=1.5, label='Valos anomalia')
            ax.legend(loc='upper right', fontsize=8)
        ax.set_title(cim)
        ax.set_xlabel("t-SNE 1")
        ax.set_ylabel("t-SNE 2")

    plt.suptitle("Anomalia Detektio Eredmenyek - t-SNE Vetites", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig("anomalia_detektio_eredmenyek.png", dpi=150, bbox_inches='tight')
    print("  Abra mentve: anomalia_detektio_eredmenyek.png")
    plt.show()


def self_supervised_vizualizacio(residuals, z_scores_arr, anomaly_indices,
                                  threshold_z=3.0):
    """
    Self-supervised residualok vizualizacioja: hisztogram + Z-score scatter.
    """
    if not MATPLOTLIB_ELERHETO:
        print("\n[SKIP] Self-supervised vizualizacio: matplotlib nem elerheto")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Residualok eloszlasa
    axes[0].hist(residuals, bins=50, color='#2196F3', alpha=0.7,
                 edgecolor='black', linewidth=0.5)
    axes[0].axvline(x=residuals.mean(), color='green', linestyle='--',
                    label=f'Atlag ({residuals.mean():.4f})')
    axes[0].set_title("Residualok eloszlasa")
    axes[0].set_xlabel("Residual (tenyleges - prediktalt)")
    axes[0].set_ylabel("Darabszam")
    axes[0].legend()

    # Z-score ertekek
    szinek = ['#F44336' if np.abs(z) > threshold_z else '#2196F3'
              for z in z_scores_arr]
    axes[1].scatter(range(len(z_scores_arr)), z_scores_arr, c=szinek, s=10, alpha=0.6)
    axes[1].axhline(y=threshold_z, color='red', linestyle='--',
                    label=f'Threshold (+/-{threshold_z})')
    axes[1].axhline(y=-threshold_z, color='red', linestyle='--')
    axes[1].axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    axes[1].set_title(f"Z-score ertekek (anomalia: |z| > {threshold_z})")
    axes[1].set_xlabel("Adatpont index")
    axes[1].set_ylabel("Z-score")
    axes[1].legend()

    plt.suptitle("Self-Supervised Anomalia Detektio", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig("self_supervised_anomalia.png", dpi=150, bbox_inches='tight')
    print("  Abra mentve: self_supervised_anomalia.png")
    plt.show()


def gmm_skor_eloszlas_vizualizacio(scores, threshold):
    """A GMM log-likelihood skorok eloszlasanak vizualizacioja."""
    if not MATPLOTLIB_ELERHETO:
        print("\n[SKIP] GMM skor vizualizacio: matplotlib nem elerheto")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(scores, bins=80, color='#2196F3', alpha=0.7, edgecolor='black',
            linewidth=0.5)
    ax.axvline(x=threshold, color='red', linestyle='--', linewidth=2,
               label=f'Threshold ({threshold:.4f})')
    ax.set_title("GMM Log-Likelihood Skorok Eloszlasa")
    ax.set_xlabel("Log-likelihood skor")
    ax.set_ylabel("Darabszam")
    ax.legend()
    plt.tight_layout()
    plt.savefig("gmm_skor_eloszlas.png", dpi=150, bbox_inches='tight')
    print("  Abra mentve: gmm_skor_eloszlas.png")
    plt.show()


# =============================================================================
# OSSZEFOGLALO TABLAZAT
# =============================================================================

def osszefoglalo_tablazat():
    """
    A harom anomalia detekcios modszer osszehasonlito tablazata.
    """
    print(f"\n{'='*80}")
    print("  ANOMALIA DETEKCIOS MODSZEREK OSSZEHASONLITASA")
    print(f"{'='*80}")

    header = (f"{'Jellemzo':<25} {'GMM':>15} {'Isolation Forest':>18} "
              f"{'Self-Supervised':>17}")
    print(f"\n  {header}")
    print(f"  {'-'*75}")

    sorok = [
        ("Tipus", "Valoszinusegi", "Faalap, ensemble", "Regresszio+Z-score"),
        ("Cimke szukseges?", "Nem", "Nem", "Nem"),
        ("Kimenet", "Log-likelihood", "Anomalia skor", "Residual Z-score"),
        ("Threshold", "Kvantilis", "Contamination", "Z-score (pl. 3)"),
        ("Eloszlas felt.", "Gauss keverek", "Nincs", "Norm. residualok"),
        ("Skalazhatosag", "Jo", "Kivalo", "Korrekt"),
        ("Fo elony", "Val. framework", "Gyors + robust", "Feature koherencia"),
        ("Fo hatrany", "n_components", "contamination", "Target valasztas"),
    ]

    for jellemzo, gmm, if_val, ss in sorok:
        print(f"  {jellemzo:<25} {gmm:>15} {if_val:>18} {ss:>17}")


# =============================================================================
# MAIN - TELJES PIPELINE FUTTATAS
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("  ANOMALIA DETEKTIO - TELJES PIPELINE")
    print("  Cubix ML Engineer kepzes - 11. fejezet")
    print("=" * 70)

    # 1. Adatgeneralas es eloeszites
    df, y_true, feature_names = szintetikus_adatok_generalasa(
        n_normalis=800, n_anomalia=40, n_features=10, random_state=42)
    scaled_data, df_log = adatok_elokeszitese(df)

    # 2. GMM anomalia detektio
    gmm_labels, gmm_scores, gmm_threshold, gmm_model = gmm_anomalia_detektio(
        scaled_data, n_components=5, kvantilis=0.05, random_state=42)

    # 3. Isolation Forest anomalia detektio
    if_labels, if_scores, if_model = isolation_forest_detektio(
        scaled_data, contamination=0.05, random_state=42)

    # 4. GMM + IF osszehasonlitas
    eredmeny = modszerek_osszehasonlitasa(gmm_labels, if_labels, y_true=y_true)

    # 5. Self-supervised anomalia detektio
    ss_anomaliak, ss_z_scores, ss_residuals, ss_test_idx = self_supervised_anomalia(
        df_log, target_column_idx=0, threshold_z=3.0, test_size=0.2, random_state=42)

    # 6. Osszefoglalo tablazat
    osszefoglalo_tablazat()

    # 7. Vizualizacio (ha matplotlib elerheto)
    gmm_skor_eloszlas_vizualizacio(gmm_scores, gmm_threshold)
    anomalia_vizualizacio_2d(scaled_data, gmm_labels, if_labels, y_true=y_true)
    self_supervised_vizualizacio(ss_residuals, ss_z_scores, ss_anomaliak, threshold_z=3.0)

    print("\n" + "=" * 70)
    print("  KESZ - Anomalia detektio pipeline befejezodott.")
    print("=" * 70)
