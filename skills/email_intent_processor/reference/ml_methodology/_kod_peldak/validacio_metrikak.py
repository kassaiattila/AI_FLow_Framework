"""
Modell validacio es metrikak - Cubix ML Engineer tananyag (5. het)
=================================================================

Ez a fajl a modellertekelesi es validacios technikaakat mutatja be
a Cubix ML Engineer kepzes 5. heti anyaga alapjan.

Tartalomjegyzek:
  1. Train/Validation/Test split
  2. K-Fold Cross-Validation (KFold, StratifiedKFold, cross_val_score)
  3. TimeSeriesSplit
  4. Confusion Matrix
  5. Osztalyozasi metrikak (accuracy, precision, recall, F1, classification_report)
  6. ROC gorbe es AUC
  7. Precision-Recall gorbe es PR-AUC
  8. Regresszios metrikak (MAE, MSE, RMSE, R2, MAPE)
  9. Learning Curves - overfitting/underfitting vizualizalas
 10. Tobbosztalyos metrikak (macro, micro, weighted)

Futtatas: python validacio_metrikak.py
"""

import numpy as np
import matplotlib.pyplot as plt

from sklearn.datasets import load_breast_cancer, load_diabetes, load_iris
from sklearn.model_selection import (
    train_test_split,
    KFold,
    StratifiedKFold,
    cross_val_score,
    TimeSeriesSplit,
    learning_curve,
)
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MinMaxScaler, label_binarize
from sklearn.metrics import (
    # Osztalyozas
    confusion_matrix,
    ConfusionMatrixDisplay,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
    classification_report,
    roc_curve,
    roc_auc_score,
    RocCurveDisplay,
    precision_recall_curve,
    average_precision_score,
    auc,
    # Regresszio
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error,
)


# ============================================================================
# 1. TRAIN / VALIDATION / TEST SPLIT
# ============================================================================
def demo_train_val_test_split():
    """
    Az adathalmaz haromfele osztasa: tanito, validacios es teszt halmaz.

    Tipikus aranyok:
      - Train: 60-70%
      - Validation: 15-20%  (hiperparameterek hangolasahoz)
      - Test: 15-20%        (vegso, "lathatatlan" kiertekeleshez)

    A stratify parameter biztositja, hogy minden reszhalmazban
    megmaradjon az eredeti osztalyeloszlas.
    """
    print("=" * 70)
    print("1. TRAIN / VALIDATION / TEST SPLIT")
    print("=" * 70)

    # Binarys osztalyozasi dataset betoltese
    data = load_breast_cancer()
    X, y = data.data, data.target

    print(f"Teljes adathalmaz merete: {X.shape[0]} minta, {X.shape[1]} feature")
    print(f"Osztalyeloszlas: {np.bincount(y)}  (0=rosszindulatu, 1=jondulatu)")

    # ---- Elso lepes: kulonvalasztjuk a teszt halmazt (~ 20%) ----
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y,
        test_size=0.2,       # 20% teszt
        random_state=42,
        stratify=y,          # retegzett mintatvetel az osztalyeloszlas megorzesere
    )

    # ---- Masodik lepes: a maradekbol valasztjuk ki a validacios halmazt ----
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp,
        test_size=0.25,      # a maradek 80%-bol 25% = az osszes 20%-a
        random_state=42,
        stratify=y_temp,
    )

    print(f"\nTrain halmaz:      {X_train.shape[0]} minta ({X_train.shape[0]/len(X)*100:.0f}%)")
    print(f"Validation halmaz: {X_val.shape[0]} minta ({X_val.shape[0]/len(X)*100:.0f}%)")
    print(f"Test halmaz:       {X_test.shape[0]} minta ({X_test.shape[0]/len(X)*100:.0f}%)")

    # Ellenorizzuk, hogy a stratify megorizte az eloszlast
    for name, subset in [("Train", y_train), ("Val", y_val), ("Test", y_test)]:
        ratio = np.mean(subset)
        print(f"  {name:5s} - pozitiv arany: {ratio:.3f}")

    print()
    return X_train, X_val, X_test, y_train, y_val, y_test


# ============================================================================
# 2. K-FOLD CROSS-VALIDATION
# ============================================================================
def demo_kfold_cross_validation():
    """
    K-Fold Cross-Validation: az adatot K egyenlo reszre osztjuk,
    es K-szor tanitunk - minden alkalommal mas resz a validacio.

    Elonyok:
      - Minden adat bekeruel egyszer a validacios halmazba
      - Robusztusabb becslest ad, mint egyetlen split
      - Csokkenti a variance-t a teljesitmeny mereseben

    StratifiedKFold: megorizte az osztalyeloszlast minden fold-ban.
    cross_val_score: egysoros megoldas a teljes K-Fold kiertekelere.
    """
    print("=" * 70)
    print("2. K-FOLD CROSS-VALIDATION")
    print("=" * 70)

    data = load_breast_cancer()
    X, y = data.data, data.target

    # --- 2a. Sima KFold ---
    print("\n--- 2a. KFold (5 fold) ---")
    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    accuracies = []
    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X)):
        clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
        clf.fit(X[train_idx], y[train_idx])

        y_val_pred = clf.predict(X[val_idx])
        acc = accuracy_score(y[val_idx], y_val_pred)
        accuracies.append(acc)
        print(f"  Fold {fold_idx + 1}: accuracy = {acc:.4f}")

    print(f"  Atlag accuracy: {np.mean(accuracies):.4f} (+/- {np.std(accuracies):.4f})")

    # --- 2b. StratifiedKFold ---
    # Kulonbseg a sima KFold-hoz kepest: megorizte az osztaly-eloszlast
    print("\n--- 2b. StratifiedKFold (5 fold) ---")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        pos_ratio = np.mean(y[val_idx])
        print(f"  Fold {fold_idx + 1}: pozitiv arany a val-ban = {pos_ratio:.3f}")

    # --- 2c. cross_val_score - egysoros megoldas ---
    print("\n--- 2c. cross_val_score (5-fold, stratified) ---")
    clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=0)
    scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
    print(f"  Fold score-ok: {scores}")
    print(f"  Atlag: {scores.mean():.4f} (+/- {scores.std():.4f})")

    # Tovabbi scoring lehetosegek
    f1_scores = cross_val_score(clf, X, y, cv=5, scoring="f1")
    print(f"  F1 score-ok:   {f1_scores}")
    print(f"  Atlag F1:      {f1_scores.mean():.4f}")
    print()


# ============================================================================
# 3. TIMESERIESSPLIT
# ============================================================================
def demo_timeseries_split():
    """
    Idosor adatokon NEM hasznalhato a sima K-Fold, mert
    a jovobeli adatok "beszivaroghatnak" a tanito halmazba.

    TimeSeriesSplit: mindig a "multbeli" adatokon tanit,
    es a kovetkezo idoszakon validalja.

    Fold 1: Train [0..n1]    Val [n1..n2]
    Fold 2: Train [0..n2]    Val [n2..n3]
    ...
    A train halmaz folyamatosan no.
    """
    print("=" * 70)
    print("3. TIMESERIESSPLIT")
    print("=" * 70)

    # Szimulalt idosor adat
    np.random.seed(42)
    n_samples = 100
    X_ts = np.arange(n_samples).reshape(-1, 1)
    y_ts = np.sin(X_ts.ravel() / 10) + np.random.normal(0, 0.1, n_samples)

    tscv = TimeSeriesSplit(n_splits=5)
    print(f"\nTimeSeriesSplit foldok ({tscv.get_n_splits()} split):")

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X_ts)):
        print(
            f"  Fold {fold_idx + 1}: "
            f"Train index [{train_idx[0]}..{train_idx[-1]}] ({len(train_idx)} db), "
            f"Val index [{val_idx[0]}..{val_idx[-1]}] ({len(val_idx)} db)"
        )

    # Vizualizacio: melyik fold mit lat
    fig, ax = plt.subplots(figsize=(12, 4))
    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X_ts)):
        ax.scatter(train_idx, [fold_idx + 1] * len(train_idx), c="blue", s=5, label="Train" if fold_idx == 0 else "")
        ax.scatter(val_idx, [fold_idx + 1] * len(val_idx), c="red", s=5, label="Val" if fold_idx == 0 else "")
    ax.set_xlabel("Mintaindex (ido)")
    ax.set_ylabel("Fold szam")
    ax.set_title("TimeSeriesSplit vizualizacio")
    ax.legend()
    plt.tight_layout()
    plt.savefig("timeseries_split.png", dpi=100)
    plt.close()
    print("  Abra mentve: timeseries_split.png")
    print()


# ============================================================================
# 4. CONFUSION MATRIX (Tevesztesi matrix)
# ============================================================================
def demo_confusion_matrix():
    """
    A Confusion Matrix (tevesztesi matrix) megmutatja, hogy a modell
    mely osztalyokat keveri ossze.

    Binaris osztalyozas eseten:
                          Prediktalt
                       Negativ  Pozitiv
    Valos  Negativ  [   TN       FP   ]
           Pozitiv  [   FN       TP   ]

    TN = True Negative  - helyesen negativ
    FP = False Positive - tevesen pozitiv (I. fajta hiba)
    FN = False Negative - tevesen negativ (II. fajta hiba)
    TP = True Positive  - helyesen pozitiv
    """
    print("=" * 70)
    print("4. CONFUSION MATRIX")
    print("=" * 70)

    data = load_breast_cancer()
    X, y = data.data, data.target

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y,
    )

    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=0)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    # Confusion matrix szamitas
    cm = confusion_matrix(y_test, y_pred)
    print(f"\nConfusion Matrix:\n{cm}")

    # Ertekek kinyerese (binaris eset)
    tn, fp, fn, tp = cm.ravel()
    print(f"\n  True Negative  (TN): {tn}")
    print(f"  False Positive (FP): {fp}  <- I. fajta hiba")
    print(f"  False Negative (FN): {fn}  <- II. fajta hiba")
    print(f"  True Positive  (TP): {tp}")

    # Vizualizacio a ConfusionMatrixDisplay segitsegevel
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Abszolut ertekek
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred,
        display_labels=["Rosszindulatu", "Joindalatu"],
        ax=axes[0],
        cmap="Blues",
    )
    axes[0].set_title("Confusion Matrix (darabszam)")

    # Normalizalt (aranyok)
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred,
        display_labels=["Rosszindulatu", "Joindalatu"],
        normalize="true",      # soronkent normalizal (recall / sensitivity)
        ax=axes[1],
        cmap="Blues",
        values_format=".2%",
    )
    axes[1].set_title("Confusion Matrix (normalizalt)")

    plt.tight_layout()
    plt.savefig("confusion_matrix.png", dpi=100)
    plt.close()
    print("\n  Abra mentve: confusion_matrix.png")
    print()
    return clf, X_test, y_test, y_pred


# ============================================================================
# 5. OSZTALYOZASI METRIKAK
# ============================================================================
def demo_classification_metrics(clf, X_test, y_test, y_pred):
    """
    A legfontosabb osztalyozasi metrikak:

    Accuracy  = (TP + TN) / (TP + TN + FP + FN)
      - Arany: hany szazalekban talalt jol? Kiegyensulyozatlan adatnal FELREVEZETO!

    Precision = TP / (TP + FP)
      - Ha a modell azt mondja "pozitiv", mennyire bizhatunk benne?
      - Fontos, ha a fals pozitiv koltsege magas (pl. spam szuro)

    Recall    = TP / (TP + FN)
      - A tenyleges pozitivok kozul mennyit talalt meg?
      - Fontos, ha a fals negativ koltsege magas (pl. rakszures)

    F1 Score  = 2 * (Precision * Recall) / (Precision + Recall)
      - Precision es Recall harmonikus kozepe
      - Kiegyensulyozott kompromisszum a ketto kozott

    F-beta    = (1 + beta^2) * (P * R) / (beta^2 * P + R)
      - beta > 1: a recall fontosabb
      - beta < 1: a precision fontosabb
    """
    print("=" * 70)
    print("5. OSZTALYOZASI METRIKAK")
    print("=" * 70)

    # Egyenkenti metrikak
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    f_beta_05 = fbeta_score(y_test, y_pred, beta=0.5)  # precision sulya nagyobb
    f_beta_2 = fbeta_score(y_test, y_pred, beta=2.0)    # recall sulya nagyobb

    print(f"\n  Accuracy:              {acc:.4f}")
    print(f"  Precision:             {prec:.4f}")
    print(f"  Recall (Sensitivity):  {rec:.4f}")
    print(f"  F1 Score:              {f1:.4f}")
    print(f"  F-beta (beta=0.5):     {f_beta_05:.4f}  <- precision sulyozott")
    print(f"  F-beta (beta=2.0):     {f_beta_2:.4f}  <- recall sulyozott")

    # Classification report - osszefoglalo tablazat
    print("\n  Classification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=["Rosszindulatu", "Joindalatu"],
    ))


# ============================================================================
# 6. ROC GORBE ES AUC
# ============================================================================
def demo_roc_curve(clf, X_test, y_test):
    """
    ROC gorbe (Receiver Operating Characteristic):
      - X tengely: False Positive Rate (FPR) = FP / (FP + TN)
      - Y tengely: True Positive Rate (TPR) = TP / (TP + FN) = Recall

    AUC (Area Under the Curve):
      - 0.5 = veletlen talalgatast jelent (atlos vonal)
      - 1.0 = tokeletes osztalyozo
      - Minel nagyobb, annal jobb a modell

    A ROC gorbe kulonfele kuszobertekeknel mutatja az FPR vs TPR trade-off-ot.
    """
    print("=" * 70)
    print("6. ROC GORBE ES AUC")
    print("=" * 70)

    # Valoszinusegi predikciok (a pozitiv osztaly valoszinusege)
    y_probs = clf.predict_proba(X_test)[:, 1]

    # ROC gorbe szamitasa
    fpr, tpr, thresholds = roc_curve(y_test, y_probs)
    roc_auc = roc_auc_score(y_test, y_probs)

    print(f"\n  ROC AUC score: {roc_auc:.4f}")

    # Vizualizacio
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # --- Bal oldal: kezi rajzolas ---
    axes[0].plot(fpr, tpr, color="blue", lw=2, label=f"ROC gorbe (AUC = {roc_auc:.3f})")
    axes[0].plot([0, 1], [0, 1], color="darkgrey", lw=2, linestyle="--", label="Veletlen (AUC = 0.5)")
    axes[0].fill_between(fpr, tpr, alpha=0.1, color="blue")
    axes[0].set_xlabel("False Positive Rate (FPR)")
    axes[0].set_ylabel("True Positive Rate (TPR / Recall)")
    axes[0].set_title("ROC gorbe - kezi rajzolas")
    axes[0].legend(loc="lower right")
    axes[0].grid(True, alpha=0.3)

    # --- Jobb oldal: sklearn RocCurveDisplay ---
    RocCurveDisplay.from_estimator(clf, X_test, y_test, ax=axes[1], name="RandomForest")
    axes[1].plot([0, 1], [0, 1], color="darkgrey", lw=2, linestyle="--")
    axes[1].set_title("ROC gorbe - RocCurveDisplay")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("roc_curve.png", dpi=100)
    plt.close()
    print("  Abra mentve: roc_curve.png")

    # Nehany kuszob ertek kiirasa
    print("\n  Peldak kuszobertekekre:")
    indices = np.linspace(0, len(thresholds) - 1, 5, dtype=int)
    for i in indices:
        print(f"    Kuszob={thresholds[i]:.3f} -> FPR={fpr[i]:.3f}, TPR={tpr[i]:.3f}")
    print()

    return y_probs


# ============================================================================
# 7. PRECISION-RECALL GORBE ES PR-AUC
# ============================================================================
def demo_precision_recall_curve(y_test, y_probs):
    """
    Precision-Recall gorbe:
      - Kiegyensulyozatlan adatoknal FONTOSABB, mint a ROC gorbe!
      - X tengely: Recall
      - Y tengely: Precision

    PR-AUC (Average Precision):
      - Minel nagyobb, annal jobb
      - average_precision_score: sulyozott atlag a kuszobertekekre

    Ha a pozitiv osztaly ritka (pl. 1%), a ROC gorbe megteveszto lehet,
    mert az FPR nagyon alacsony marad - a PR gorbe vilagosabban mutatja
    a tenyleges teljesitmenyt.
    """
    print("=" * 70)
    print("7. PRECISION-RECALL GORBE ES PR-AUC")
    print("=" * 70)

    # Precision-Recall gorbe szamitasa
    precision_vals, recall_vals, pr_thresholds = precision_recall_curve(y_test, y_probs)
    pr_auc = auc(recall_vals, precision_vals)
    avg_prec = average_precision_score(y_test, y_probs)

    print(f"\n  PR-AUC (gorbe alatti terulet): {pr_auc:.4f}")
    print(f"  Average Precision Score:       {avg_prec:.4f}")

    # Vizualizacio
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(recall_vals, precision_vals, color="green", lw=2,
            label=f"PR gorbe (AP = {avg_prec:.3f})")
    ax.fill_between(recall_vals, precision_vals, alpha=0.1, color="green")
    ax.axhline(y=np.mean(y_test), color="darkgrey", linestyle="--",
               label=f"Veletlen baseline ({np.mean(y_test):.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall gorbe")
    ax.legend(loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.05])

    plt.tight_layout()
    plt.savefig("precision_recall_curve.png", dpi=100)
    plt.close()
    print("  Abra mentve: precision_recall_curve.png")
    print()


# ============================================================================
# 8. REGRESSZIOS METRIKAK
# ============================================================================
def demo_regression_metrics():
    """
    Regresszios feladatokhoz hasznalt metrikak:

    MAE  = mean(|y - y_hat|)
      - Atlagos abszolut hiba, kozvetlen ertelmezhetosg
      - Nem bunteti a nagy hibakat sulyosabban

    MSE  = mean((y - y_hat)^2)
      - Negyzetesen bunteti a nagy hibakat
      - Optimalizalasra jo, de nehezebben ertelmezhetou (negyzetben van)

    RMSE = sqrt(MSE)
      - Visszatranszformalja az eredeti mertekegysegbe
      - Megorizte a nagy hibak bunteteset

    R2   = 1 - SS_res / SS_tot
      - Coefficient of Determination
      - Mennyit magyaraz meg a modell a varianciabol
      - 1.0 = tokeletes, 0.0 = atlagot jobb hasznalni, < 0 = rosszabb az atlagnalt

    MAPE = mean(|y - y_hat| / |y|) * 100
      - Szazalekos hiba - uzleti kommunikaciohoz hasznos
      - VIGYAZAT: ha y-ban van 0 kozeli ertek, a MAPE felrobbanhat!
    """
    print("=" * 70)
    print("8. REGRESSZIOS METRIKAK")
    print("=" * 70)

    # Diabetes dataset (regresszio)
    diabetes = load_diabetes()
    X = diabetes.data
    y = diabetes.target

    print(f"\nDiabetes dataset: {X.shape[0]} minta, {X.shape[1]} feature")
    print(f"Celvaltozo (target) atlag: {y.mean():.1f}, szoras: {y.std():.1f}")

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42,
    )

    # Modell tanitasa
    regr = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=0)
    regr.fit(X_train, y_train)
    y_pred_train = regr.predict(X_train)
    y_pred_test = regr.predict(X_test)

    # --- Metrikak szamitasa ---
    mae_train = mean_absolute_error(y_train, y_pred_train)
    mae_test = mean_absolute_error(y_test, y_pred_test)

    mse_test = mean_squared_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mse_test)

    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)

    mape_test = mean_absolute_percentage_error(y_test, y_pred_test) * 100

    print(f"\n  {'Metrika':<12s} {'Train':>10s} {'Test':>10s}")
    print(f"  {'-'*34}")
    print(f"  {'MAE':<12s} {mae_train:>10.2f} {mae_test:>10.2f}")
    print(f"  {'MSE':<12s} {'':>10s} {mse_test:>10.2f}")
    print(f"  {'RMSE':<12s} {'':>10s} {rmse_test:>10.2f}")
    print(f"  {'R2':<12s} {r2_train:>10.4f} {r2_test:>10.4f}")
    print(f"  {'MAPE (%)':<12s} {'':>10s} {mape_test:>10.2f}%")

    # Ertelmezesi segitseg
    print(f"\n  Ertelmezesi tippek:")
    print(f"    - MAE {mae_test:.1f} azt jelenti: atlagosan {mae_test:.1f} egysegnyi a hiba")
    print(f"    - R2 {r2_test:.3f} azt jelenti: a modell a variancia {r2_test*100:.1f}%-at magyarazza")
    if r2_train - r2_test > 0.1:
        print(f"    - FIGYELEM: R2 train ({r2_train:.3f}) >> R2 test ({r2_test:.3f}) -> overfitting jele!")

    # Vizualizacio: valos vs prediktalt
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Scatter plot: valos vs prediktalt
    axes[0].scatter(y_test, y_pred_test, alpha=0.5, edgecolors="k", linewidths=0.5)
    min_val = min(y_test.min(), y_pred_test.min())
    max_val = max(y_test.max(), y_pred_test.max())
    axes[0].plot([min_val, max_val], [min_val, max_val], "r--", lw=2, label="Tokeletes predikicio")
    axes[0].set_xlabel("Valos ertek")
    axes[0].set_ylabel("Prediktalt ertek")
    axes[0].set_title(f"Valos vs Prediktalt (R2={r2_test:.3f})")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Residual plot: hibak eloszlasa
    residuals = y_test - y_pred_test
    axes[1].scatter(y_pred_test, residuals, alpha=0.5, edgecolors="k", linewidths=0.5)
    axes[1].axhline(y=0, color="r", linestyle="--", lw=2)
    axes[1].set_xlabel("Prediktalt ertek")
    axes[1].set_ylabel("Hiba (valos - prediktalt)")
    axes[1].set_title("Residual plot (maradek hibak)")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("regression_metrics.png", dpi=100)
    plt.close()
    print("\n  Abra mentve: regression_metrics.png")
    print()


# ============================================================================
# 9. LEARNING CURVES - OVERFITTING / UNDERFITTING VIZUALIZALAS
# ============================================================================
def demo_learning_curves():
    """
    Learning curve: megmutatja, hogyan valtozik a modell teljesitmenye
    a tanito adatok szamanak fuggvenyeben.

    Overfitting jelei:
      - A train score magasan marad
      - A validacios score lenyegesen alacsonyabb
      - Tobb adat nem segit (a res megmarad)

    Underfitting jelei:
      - Mind a train, mind a validacios score alacsony
      - A ket gorbe kozel van egymashoz, de mindketto rossz

    Jo generalizacio:
      - A ket gorbe konvergal egymas fele
      - Mindketto magas ertek korul stabilizalodik
    """
    print("=" * 70)
    print("9. LEARNING CURVES")
    print("=" * 70)

    data = load_breast_cancer()
    X, y = data.data, data.target

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    models = [
        ("Underfitting (max_depth=1)", RandomForestClassifier(n_estimators=10, max_depth=1, random_state=0)),
        ("Jo illesztes (max_depth=5)", RandomForestClassifier(n_estimators=50, max_depth=5, random_state=0)),
        ("Overfitting (max_depth=None)", RandomForestClassifier(n_estimators=200, max_depth=None, random_state=0)),
    ]

    for ax, (title, model) in zip(axes, models):
        # Learning curve szamitasa
        train_sizes, train_scores, val_scores = learning_curve(
            model, X, y,
            train_sizes=np.linspace(0.1, 1.0, 10),  # 10%-tol 100%-ig
            cv=5,                                     # 5-fold cross-validation
            scoring="accuracy",
            n_jobs=-1,                                # parhuzamos szamitas
        )

        # Atlag es szoras szamitasa a fold-okra
        train_mean = train_scores.mean(axis=1)
        train_std = train_scores.std(axis=1)
        val_mean = val_scores.mean(axis=1)
        val_std = val_scores.std(axis=1)

        # Rajzolas
        ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="blue")
        ax.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.1, color="orange")
        ax.plot(train_sizes, train_mean, "o-", color="blue", label="Train score")
        ax.plot(train_sizes, val_mean, "o-", color="orange", label="Validacios score")
        ax.set_xlabel("Tanito mintak szama")
        ax.set_ylabel("Accuracy")
        ax.set_title(title)
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0.8, 1.02])

        gap = train_mean[-1] - val_mean[-1]
        print(f"\n  {title}:")
        print(f"    Train score (vegleges): {train_mean[-1]:.4f}")
        print(f"    Val score (vegleges):   {val_mean[-1]:.4f}")
        print(f"    Gap (kulonbseg):        {gap:.4f}")

    plt.suptitle("Learning Curves - Underfitting / Jo illesztes / Overfitting", fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig("learning_curves.png", dpi=100, bbox_inches="tight")
    plt.close()
    print("\n  Abra mentve: learning_curves.png")
    print()


# ============================================================================
# 10. TOBBOSZTALYOS METRIKAK (MULTI-CLASS)
# ============================================================================
def demo_multiclass_metrics():
    """
    Tobbosztalyos osztalyozas eseten az atlagolasi strategiak:

    macro:    egyszeruen atlagoljuk az osztalyonkenti metrikakat
              -> minden osztaly azonos sulyu (kisebb osztalyoknak is van hangja)

    micro:    globalis TP, FP, FN alapjan szamol
              -> a nagy osztaly dominal

    weighted: az osztalyok merete szerinti sulyozott atlag
              -> figyelembe veszi a kiegyensulyozatlansagot

    Pelda (Iris dataset - 3 osztaly):
      - setosa, versicolor, virginica
    """
    print("=" * 70)
    print("10. TOBBOSZTALYOS METRIKAK")
    print("=" * 70)

    # Iris dataset (3 osztaly)
    iris = load_iris()
    X, y = iris.data, iris.target
    class_names = iris.target_names

    print(f"\nIris dataset: {X.shape[0]} minta, {len(class_names)} osztaly")
    print(f"Osztalyok: {list(class_names)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y,
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=0)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    # --- Classification report (a legkenyelmesebb osszefoglalo) ---
    print("\n  Classification Report (tobbosztalyos):")
    print(classification_report(y_test, y_pred, target_names=class_names))

    # --- Kulonbozo atlagolasi strategiak ---
    print("  Atlagolasi strategiak osszehasonlitasa:")
    for avg in ["macro", "micro", "weighted"]:
        p = precision_score(y_test, y_pred, average=avg)
        r = recall_score(y_test, y_pred, average=avg)
        f = f1_score(y_test, y_pred, average=avg)
        print(f"    {avg:8s} -> Precision={p:.4f}, Recall={r:.4f}, F1={f:.4f}")

    # --- Tobbosztalyos Confusion Matrix ---
    fig, ax = plt.subplots(figsize=(7, 6))
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred,
        display_labels=class_names,
        cmap="Blues",
        ax=ax,
    )
    ax.set_title("Tobbosztalyos Confusion Matrix (Iris)")
    plt.tight_layout()
    plt.savefig("multiclass_confusion_matrix.png", dpi=100)
    plt.close()
    print("\n  Abra mentve: multiclass_confusion_matrix.png")

    # --- Tobbosztalyos ROC gorbe (One-vs-Rest strategia) ---
    # Minden osztalyra kulon ROC gorbet rajzolunk
    y_test_bin = label_binarize(y_test, classes=[0, 1, 2])
    n_classes = y_test_bin.shape[1]

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["blue", "green", "red"]

    for i, (color, name) in enumerate(zip(colors, class_names)):
        fpr_i, tpr_i, _ = roc_curve(y_test_bin[:, i], y_proba[:, i])
        auc_i = roc_auc_score(y_test_bin[:, i], y_proba[:, i])
        ax.plot(fpr_i, tpr_i, color=color, lw=2, label=f"{name} (AUC = {auc_i:.3f})")

    # Macro-atlagolt AUC
    macro_auc = roc_auc_score(y_test_bin, y_proba, multi_class="ovr", average="macro")
    ax.plot([0, 1], [0, 1], color="darkgrey", lw=2, linestyle="--")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"Tobbosztalyos ROC gorbe (macro AUC = {macro_auc:.3f})")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("multiclass_roc_curve.png", dpi=100)
    plt.close()
    print("  Abra mentve: multiclass_roc_curve.png")
    print()


# ============================================================================
# FOPROGRAM
# ============================================================================
if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("#  MODELL VALIDACIO ES METRIKAK - TELJES DEMO")
    print("#  Cubix ML Engineer tananyag - 5. het")
    print("#" * 70 + "\n")

    # 1. Train/Val/Test split
    X_train, X_val, X_test, y_train, y_val, y_test = demo_train_val_test_split()

    # 2. K-Fold Cross-Validation
    demo_kfold_cross_validation()

    # 3. TimeSeriesSplit
    demo_timeseries_split()

    # 4. Confusion Matrix (visszaad clf-et a tovabbi demokhoz)
    clf, X_test_cm, y_test_cm, y_pred_cm = demo_confusion_matrix()

    # 5. Osztalyozasi metrikak
    demo_classification_metrics(clf, X_test_cm, y_test_cm, y_pred_cm)

    # 6. ROC gorbe es AUC
    y_probs = demo_roc_curve(clf, X_test_cm, y_test_cm)

    # 7. Precision-Recall gorbe
    demo_precision_recall_curve(y_test_cm, y_probs)

    # 8. Regresszios metrikak
    demo_regression_metrics()

    # 9. Learning curves
    demo_learning_curves()

    # 10. Tobbosztalyos metrikak
    demo_multiclass_metrics()

    print("=" * 70)
    print("OSSZES DEMO LEFUTOTT!")
    print("Generalt abrak:")
    print("  - timeseries_split.png")
    print("  - confusion_matrix.png")
    print("  - roc_curve.png")
    print("  - precision_recall_curve.png")
    print("  - regression_metrics.png")
    print("  - learning_curves.png")
    print("  - multiclass_confusion_matrix.png")
    print("  - multiclass_roc_curve.png")
    print("=" * 70)
