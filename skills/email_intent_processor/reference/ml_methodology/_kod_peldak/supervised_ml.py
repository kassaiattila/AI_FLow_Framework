"""
Supervised Machine Learning algoritmusok - Cubix EDU ML Engineering kurzus
===========================================================================

Ez a fajl a feluegyelt (supervised) tanulasi algoritmusokat mutatja be
a scikit-learn es egyeb konyvtarak segitsegevel.

Tartalomjegyzek:
    1.  KNN (K-Nearest Neighbors) - Klasszifikacio es Regresszio
    2.  Linearis Regresszio (LinearRegression, Ridge, Lasso, ElasticNet)
    3.  Logisztikus Regresszio (binaris es tobbosztalyos)
    4.  SVM (Support Vector Machine - linearis es RBF kernel)
    5.  Dontesi Fa (DecisionTree - Classifier es Regressor)
    6.  Random Forest (Classifier es Regressor)
    7.  Gradient Boosting (GradientBoostingClassifier)
    8.  AdaBoost (AdaBoostClassifier)
    9.  XGBoost (XGBClassifier)
    10. LightGBM (LGBMClassifier)
    11. CatBoost (CatBoostClassifier)
    12. Modell osszehasonlitas sablon (cross_val_score)

Forras: Cubix EDU - ML Engineering kurzus, 4. het
       Cubix_ML_Engineer_ML_algorithms.ipynb notebook alapjan
"""

import warnings
import numpy as np
import pandas as pd

# Sklearn alap importok
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    classification_report,
)
from sklearn.preprocessing import StandardScaler

# Figyelmeztetesek elnyomasa a tisztabb kimenetert
warnings.filterwarnings("ignore")


# =============================================================================
#  SEGÉDFÜGGVÉNYEK
# =============================================================================

def szeparator(cim: str) -> None:
    """Vizualis szeparator kiirasa a szekcio cimevel."""
    print("\n" + "=" * 80)
    print(f"  {cim}")
    print("=" * 80)


def klasszifikacio_kiertekeles(model, X_train, X_test, y_train, y_test,
                                modell_nev: str) -> dict:
    """
    Klasszifikacios modell kiertekelo fuggveny.

    Kiszamolja a train es test pontossagot (accuracy),
    es visszaadja szotarkent az eredmenyeket.

    Parameterek:
        model:      betanitott sklearn-kompatibilis modell
        X_train:    tanito feature-ok
        X_test:     teszt feature-ok
        y_train:    tanito cimkek
        y_test:     teszt cimkek
        modell_nev: a modell megjelenito neve

    Visszateresi ertek:
        dict: {'nev', 'train_acc', 'test_acc'}
    """
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    print(f"  {modell_nev}")
    print(f"    Train Accuracy: {train_acc:.4f}")
    print(f"    Test  Accuracy: {test_acc:.4f}")

    return {"nev": modell_nev, "train_acc": train_acc, "test_acc": test_acc}


def regresszio_kiertekeles(model, X_train, X_test, y_train, y_test,
                            modell_nev: str) -> dict:
    """
    Regresszios modell kiertekelo fuggveny.

    Kiszamolja a MAE, MSE es R2 ertekeket.

    Visszateresi ertek:
        dict: {'nev', 'mae', 'mse', 'r2'}
    """
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"  {modell_nev}")
    print(f"    MAE:  {mae:.4f}")
    print(f"    MSE:  {mse:.4f}")
    print(f"    R2:   {r2:.4f}")

    return {"nev": modell_nev, "mae": mae, "mse": mse, "r2": r2}


# =============================================================================
#  ADATOK ELŐKÉSZÍTÉSE
# =============================================================================

def adatok_elokeszitese():
    """
    Sklearn beepitett adathalmazok betoltese es elokeszitese.

    Klasszifikacios feladathoz: Iris adathalmaz (tobbosztalyos)
    Binaris klasszifikaciohoz: Breast Cancer adathalmaz
    Regressziohoz: Diabetes adathalmaz

    Visszateresi ertek:
        tuple: (klasszifikacios adatok, binaris adatok, regresszios adatok)
               Mindegyik egy dict: {'X_train', 'X_test', 'y_train', 'y_test'}
    """
    from sklearn.datasets import load_iris, load_diabetes, load_breast_cancer

    # --- Iris: tobbosztalyos klasszifikacio (3 osztaly) ---
    iris = load_iris()
    X_iris = pd.DataFrame(iris.data, columns=iris.feature_names)
    y_iris = pd.Series(iris.target, name="target")

    X_train_cls, X_test_cls, y_train_cls, y_test_cls = train_test_split(
        X_iris, y_iris, test_size=0.33, random_state=42
    )

    # --- Breast Cancer: binaris klasszifikacio (0/1) ---
    cancer = load_breast_cancer()
    X_cancer = pd.DataFrame(cancer.data, columns=cancer.feature_names)
    y_cancer = pd.Series(cancer.target, name="target")

    X_train_bin, X_test_bin, y_train_bin, y_test_bin = train_test_split(
        X_cancer, y_cancer, test_size=0.33, random_state=42
    )

    # --- Diabetes: regresszio (folytonos cel-valtozo) ---
    diabetes = load_diabetes()
    X_diab = pd.DataFrame(diabetes.data, columns=diabetes.feature_names)
    y_diab = pd.Series(diabetes.target, name="target")

    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(
        X_diab, y_diab, test_size=0.33, random_state=42
    )

    print("Adathalmazok betoltve:")
    print(f"  Iris (klasszifikacio):     {X_train_cls.shape[0]} train, "
          f"{X_test_cls.shape[0]} test, {X_iris.shape[1]} feature")
    print(f"  Breast Cancer (binaris):   {X_train_bin.shape[0]} train, "
          f"{X_test_bin.shape[0]} test, {X_cancer.shape[1]} feature")
    print(f"  Diabetes (regresszio):     {X_train_reg.shape[0]} train, "
          f"{X_test_reg.shape[0]} test, {X_diab.shape[1]} feature")

    klasszifikacio = {
        "X_train": X_train_cls, "X_test": X_test_cls,
        "y_train": y_train_cls, "y_test": y_test_cls,
        "feature_names": iris.feature_names,
        "target_names": iris.target_names,
    }
    binaris = {
        "X_train": X_train_bin, "X_test": X_test_bin,
        "y_train": y_train_bin, "y_test": y_test_bin,
        "feature_names": cancer.feature_names,
        "target_names": cancer.target_names,
    }
    regresszio = {
        "X_train": X_train_reg, "X_test": X_test_reg,
        "y_train": y_train_reg, "y_test": y_test_reg,
        "feature_names": diabetes.feature_names,
    }

    return klasszifikacio, binaris, regresszio


# =============================================================================
#  1. KNN - K NEAREST NEIGHBORS
# =============================================================================
# A KNN egy egyszeru, nem-linearis algoritmus. A K legkozelebbi szomszed
# alapjan prediktal euklideszi tavolsag segitsegevel.
#
# Elonyei:  egyszeru, keves parameter, gyors prototipizalas
# Hatranyai: lassu nagy adathalmazoknal (sok sor vagy sok feature)
# =============================================================================

def knn_pelda(cls_data, reg_data):
    """KNN klasszifikacio es regresszio bemutatasa."""
    szeparator("1. K-NEAREST NEIGHBORS (KNN)")

    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor

    # --- KNN Klasszifikacio ---
    # n_neighbors: hany legkozelebbi szomszedot vegyen figyelembe
    # A kurzusban n_neighbors=4 volt hasznalva
    print("\n  --- KNN Classifier (Iris, n_neighbors=4) ---")
    knn_clf = KNeighborsClassifier(n_neighbors=4)
    knn_clf.fit(cls_data["X_train"], cls_data["y_train"])

    eredmeny_clf = klasszifikacio_kiertekeles(
        knn_clf,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "KNN Classifier"
    )

    # Elso 10 predikalt ertek osszehasonlitasa a valos ertekekkel
    y_pred_10 = knn_clf.predict(cls_data["X_test"][:10])
    print(f"    Elso 10 valos:      {np.array(cls_data['y_test'][:10].values)}")
    print(f"    Elso 10 prediktalt: {y_pred_10}")

    # --- KNN Regresszio ---
    # Ugyan az a logika, de a szomszedok ertekeinek atlagat adja vissza
    print("\n  --- KNN Regressor (Diabetes, n_neighbors=5) ---")
    knn_reg = KNeighborsRegressor(n_neighbors=5)
    knn_reg.fit(reg_data["X_train"], reg_data["y_train"])

    eredmeny_reg = regresszio_kiertekeles(
        knn_reg,
        reg_data["X_train"], reg_data["X_test"],
        reg_data["y_train"], reg_data["y_test"],
        "KNN Regressor"
    )

    return eredmeny_clf


# =============================================================================
#  2. LINEÁRIS REGRESSZIÓ (LinearRegression, Ridge, Lasso, ElasticNet)
# =============================================================================
# Y = theta_0 + theta_1*X_1 + theta_2*X_2 + ... + theta_p*X_p + epsilon
#
# A linearis modell a bemeneti valtozok sulyzott osszegekent modellezi
# a kimenetet. A koltsegfuggveny (pl. MSE) minimalizalasaval tanul.
#
# Ridge:     L2 regularizacio (alpha * sum(theta_i^2))
# Lasso:     L1 regularizacio (alpha * sum(|theta_i|))
# ElasticNet: L1 + L2 kombinacio (l1_ratio szabalyozza az aranyt)
# =============================================================================

def linearis_regresszio_pelda(reg_data):
    """Linearis regresszios modellek bemutatasa: alap, Ridge, Lasso, ElasticNet."""
    szeparator("2. LINEARIS REGRESSZIO")

    from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet

    eredmenyek = []

    # --- Alap linearis regresszio ---
    print("\n  --- LinearRegression ---")
    lin_reg = LinearRegression()
    lin_reg.fit(reg_data["X_train"], reg_data["y_train"])

    # Az egyutthatokbol (coefficients) lathatjuk, melyik feature milyen
    # mertekben befolyasolja a celvaltozot
    print(f"    Intercept: {lin_reg.intercept_:.2f}")
    print(f"    Egyutthatok szama: {len(lin_reg.coef_)}")

    eredmenyek.append(regresszio_kiertekeles(
        lin_reg,
        reg_data["X_train"], reg_data["X_test"],
        reg_data["y_train"], reg_data["y_test"],
        "LinearRegression"
    ))

    # --- Ridge (L2 regularizacio) ---
    # alpha: a regularizacio erossege (nagyobb = erosebb bunetetes)
    print("\n  --- Ridge (alpha=0.1) ---")
    ridge = Ridge(alpha=0.1)
    ridge.fit(reg_data["X_train"], reg_data["y_train"])

    eredmenyek.append(regresszio_kiertekeles(
        ridge,
        reg_data["X_train"], reg_data["X_test"],
        reg_data["y_train"], reg_data["y_test"],
        "Ridge"
    ))

    # --- Lasso (L1 regularizacio) ---
    # A Lasso egyes egyutthatokat nullara allithatja (feature szelekciora is jo)
    print("\n  --- Lasso (alpha=0.001) ---")
    lasso = Lasso(alpha=0.001)
    lasso.fit(reg_data["X_train"], reg_data["y_train"])

    eredmenyek.append(regresszio_kiertekeles(
        lasso,
        reg_data["X_train"], reg_data["X_test"],
        reg_data["y_train"], reg_data["y_test"],
        "Lasso"
    ))

    # --- ElasticNet (L1 + L2) ---
    # l1_ratio=0.5: 50% L1 + 50% L2 regularizacio
    print("\n  --- ElasticNet (alpha=0.001, l1_ratio=0.5) ---")
    elasticnet = ElasticNet(alpha=0.001, l1_ratio=0.5)
    elasticnet.fit(reg_data["X_train"], reg_data["y_train"])

    eredmenyek.append(regresszio_kiertekeles(
        elasticnet,
        reg_data["X_train"], reg_data["X_test"],
        reg_data["y_train"], reg_data["y_test"],
        "ElasticNet"
    ))

    # --- Osszegzo tablazat ---
    print("\n  --- Linearis modellek osszehasonlitasa ---")
    print(f"    {'Modell':<20} {'MAE':>10} {'MSE':>10} {'R2':>10}")
    print(f"    {'-'*50}")
    for e in eredmenyek:
        print(f"    {e['nev']:<20} {e['mae']:>10.4f} {e['mse']:>10.2f} {e['r2']:>10.4f}")


# =============================================================================
#  3. LOGISZTIKUS REGRESSZIÓ
# =============================================================================
# Hasonlo a linearis regressziohoz, de klasszifikaciora hasznaljuk.
# A sigmoid fuggveny segitsegevel 0 es 1 koze kepezi le az eredmenyt.
#
# z = theta_0 + theta_1*x_1 + theta_2*x_2 + ... + theta_n*x_n
# sigmoid(z) = 1 / (1 + exp(-z))
#
# Tobbosztalyos esetben Softmax fuggvenyt hasznal.
#
# Elonyei: gyors, interpretalhato, az output 0-1 kozotti valoszinuseg
# =============================================================================

def logisztikus_regresszio_pelda(bin_data, cls_data):
    """Logisztikus regresszio: binaris es tobbosztalyos klasszifikacio."""
    szeparator("3. LOGISZTIKUS REGRESSZIO")

    from sklearn.linear_model import LogisticRegression

    eredmenyek = []

    # --- Binaris klasszifikacio (Breast Cancer) ---
    print("\n  --- Binaris LogisticRegression (Breast Cancer) ---")
    logreg_bin = LogisticRegression(random_state=42, max_iter=10000)
    logreg_bin.fit(bin_data["X_train"], bin_data["y_train"])

    eredmenyek.append(klasszifikacio_kiertekeles(
        logreg_bin,
        bin_data["X_train"], bin_data["X_test"],
        bin_data["y_train"], bin_data["y_test"],
        "LogReg (binaris)"
    ))

    # --- Tobbosztalyos klasszifikacio (Iris - 3 osztaly, Softmax) ---
    # multi_class='multinomial': Softmax-ot hasznal One-vs-Rest helyett
    print("\n  --- Tobbosztalyos LogisticRegression (Iris, Softmax) ---")
    logreg_multi = LogisticRegression(
        multi_class="multinomial",  # Softmax alapu tobbosztalyos
        solver="lbfgs",             # Gradient-alapu optimalizalo
        max_iter=10000,
        random_state=42,
    )
    logreg_multi.fit(cls_data["X_train"], cls_data["y_train"])

    eredmenyek.append(klasszifikacio_kiertekeles(
        logreg_multi,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "LogReg (multiclass)"
    ))

    # Reszletes klasszifikacios jelentes
    y_pred = logreg_multi.predict(cls_data["X_test"])
    print("\n    Classification Report (Iris):")
    report = classification_report(
        cls_data["y_test"], y_pred,
        target_names=cls_data["target_names"]
    )
    for line in report.split("\n"):
        print(f"    {line}")

    return eredmenyek


# =============================================================================
#  4. SVM - SUPPORT VECTOR MACHINE
# =============================================================================
# Az SVM a legjobb elvalaszto hipersikot keresi az osztalyok kozott.
# A kernel trukk segitsegevel nem-linearis dontest is tud hozni.
#
# Kernelek: 'linear', 'poly', 'rbf', 'sigmoid'
# C parameter: a hibak buntetese (nagyobb C = kevesebb felreosztalyozas,
#              de tultanulas veszelye)
#
# SVC: klasszifikacio, SVR: regresszio
# =============================================================================

def svm_pelda(bin_data, reg_data):
    """SVM bemutatasa linearis es RBF kernellel, klasszifikacio es regresszio."""
    szeparator("4. SUPPORT VECTOR MACHINE (SVM)")

    from sklearn.svm import SVC, SVR

    eredmenyek = []

    # Skalazes szukseges az SVM-hez (tavolsag-alapu algoritmus)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(bin_data["X_train"])
    X_test_scaled = scaler.transform(bin_data["X_test"])

    # --- SVC linearis kernellel ---
    print("\n  --- SVC linearis kernel (Breast Cancer) ---")
    svc_linear = SVC(kernel="linear", C=1.0)
    svc_linear.fit(X_train_scaled, bin_data["y_train"])

    eredmenyek.append(klasszifikacio_kiertekeles(
        svc_linear, X_train_scaled, X_test_scaled,
        bin_data["y_train"], bin_data["y_test"],
        "SVC (linear)"
    ))

    # --- SVC RBF kernellel ---
    # A kurzusban kernel='rbf' es C=2 volt hasznalva
    print("\n  --- SVC RBF kernel, C=2 (Breast Cancer) ---")
    svc_rbf = SVC(kernel="rbf", C=2)
    svc_rbf.fit(X_train_scaled, bin_data["y_train"])

    eredmenyek.append(klasszifikacio_kiertekeles(
        svc_rbf, X_train_scaled, X_test_scaled,
        bin_data["y_train"], bin_data["y_test"],
        "SVC (rbf)"
    ))

    # --- SVR regresszio (Diabetes) ---
    print("\n  --- SVR RBF kernel (Diabetes) ---")
    scaler_reg = StandardScaler()
    X_train_reg_sc = scaler_reg.fit_transform(reg_data["X_train"])
    X_test_reg_sc = scaler_reg.transform(reg_data["X_test"])

    svr = SVR(kernel="rbf", C=100, epsilon=0.1)
    svr.fit(X_train_reg_sc, reg_data["y_train"])

    regresszio_kiertekeles(
        svr, X_train_reg_sc, X_test_reg_sc,
        reg_data["y_train"], reg_data["y_test"],
        "SVR (rbf)"
    )

    return eredmenyek


# =============================================================================
#  5. DÖNTÉSI FA (Decision Tree)
# =============================================================================
# A dontesi fa az adatokat rekurzivan felosztja a feature-ok menten,
# igy fa-strukturat epitve.
#
# max_depth: a fa maximalis melysege (tultanulas elleni vedelem)
# Melyebb fa = jobban illeszkedik a tanito adatokra, de tultanulhat
#
# Elonyei: interpretalhato, vizualizalhato, keves adat-elokeszites
# Hatranyai: hajlamos a tultanulasra, instabil (kis valtozas = nagy kulonbseg)
# =============================================================================

def dontesi_fa_pelda(cls_data, reg_data):
    """Dontesi fa klasszifikacio es regresszio."""
    szeparator("5. DONTESI FA (Decision Tree)")

    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

    eredmenyek = []

    # --- DecisionTree Classifier ---
    # max_depth=3: a kurzusban is ez volt hasznalva, megakadalyozza a tultanulast
    print("\n  --- DecisionTreeClassifier (Iris, max_depth=3) ---")
    dt_clf = DecisionTreeClassifier(max_depth=3, random_state=42)
    dt_clf.fit(cls_data["X_train"], cls_data["y_train"])

    eredmenyek.append(klasszifikacio_kiertekeles(
        dt_clf,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "DecisionTree Clf"
    ))

    # Feature fontossag kiirasa
    importances = dt_clf.feature_importances_
    feature_names = cls_data["feature_names"]
    sorted_idx = np.argsort(importances)[::-1]
    print("    Feature fontossag:")
    for idx in sorted_idx:
        print(f"      {feature_names[idx]}: {importances[idx]:.4f}")

    # --- DecisionTree Regressor ---
    print("\n  --- DecisionTreeRegressor (Diabetes, max_depth=5) ---")
    dt_reg = DecisionTreeRegressor(max_depth=5, random_state=42)
    dt_reg.fit(reg_data["X_train"], reg_data["y_train"])

    regresszio_kiertekeles(
        dt_reg,
        reg_data["X_train"], reg_data["X_test"],
        reg_data["y_train"], reg_data["y_test"],
        "DecisionTree Reg"
    )

    return eredmenyek


# =============================================================================
#  6. RANDOM FOREST
# =============================================================================
# Ensemble modell: sok dontesi fa egyuttes predikcioja (bagging).
# Minden fa az adatok veletlenszeru reszhalmazan tanul (bootstrap).
#
# n_estimators: hany fat hasznaljon (tobb = stabilabb, de lassabb)
# max_depth:    egyedi fak maximalis melysege
#
# Elonyei: pontos, kezeli a tultanulast, feature fontossagot ad
# Hatranyai: lassabb mint egyetlen fa, nehezebb interpretalni
# =============================================================================

def random_forest_pelda(cls_data, reg_data):
    """Random Forest klasszifikacio es regresszio."""
    szeparator("6. RANDOM FOREST")

    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

    eredmenyek = []

    # --- RandomForest Classifier ---
    # A kurzusban n_estimators=50, max_depth=10 volt
    print("\n  --- RandomForestClassifier (Iris, 50 fa, max_depth=10) ---")
    rf_clf = RandomForestClassifier(
        n_estimators=50,
        max_depth=10,
        random_state=0,
    )
    rf_clf.fit(cls_data["X_train"], cls_data["y_train"])

    eredmenyek.append(klasszifikacio_kiertekeles(
        rf_clf,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "RandomForest Clf"
    ))

    # Feature fontossag
    importances = rf_clf.feature_importances_
    feature_names = cls_data["feature_names"]
    sorted_idx = np.argsort(importances)[::-1]
    print("    Feature fontossag:")
    for idx in sorted_idx:
        print(f"      {feature_names[idx]}: {importances[idx]:.4f}")

    # --- RandomForest Regressor ---
    print("\n  --- RandomForestRegressor (Diabetes, 100 fa) ---")
    rf_reg = RandomForestRegressor(
        n_estimators=100,
        max_depth=8,
        random_state=42,
    )
    rf_reg.fit(reg_data["X_train"], reg_data["y_train"])

    regresszio_kiertekeles(
        rf_reg,
        reg_data["X_train"], reg_data["X_test"],
        reg_data["y_train"], reg_data["y_test"],
        "RandomForest Reg"
    )

    return eredmenyek


# =============================================================================
#  7. GRADIENT BOOSTING
# =============================================================================
# Boosting: szekvencialisan epiti a fakat, mindegyik az elozo hibait
# probalja javitani (rezidualis hibak csokkenteseere torekszik).
#
# learning_rate: tanulasi rata (kisebb = ovatosabb tanulas, tobb fa kell)
# n_estimators:  hany fat epitsen egymas utan
# max_depth:     egyes fak melysege (altalaban kicsi: 2-5)
# =============================================================================

def gradient_boosting_pelda(cls_data):
    """Gradient Boosting klasszifikacio bemutatasa."""
    szeparator("7. GRADIENT BOOSTING")

    from sklearn.ensemble import GradientBoostingClassifier

    # A kurzusban max_depth=2, n_estimators=300, learning_rate=0.2 volt
    print("\n  --- GradientBoostingClassifier (Iris) ---")
    gbc = GradientBoostingClassifier(
        max_depth=2,
        n_estimators=300,
        learning_rate=0.2,
        random_state=42,
    )
    gbc.fit(cls_data["X_train"], cls_data["y_train"])

    eredmeny = klasszifikacio_kiertekeles(
        gbc,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "GradientBoosting"
    )

    return [eredmeny]


# =============================================================================
#  8. ADABOOST
# =============================================================================
# Az AdaBoost a hibasan osztalyozott mintakra nagyobb sulyt ad a kovetkezo
# iteracioban, igy fokozatosan javitja a teljesitmenyt.
#
# n_estimators: hany gyenge tanulot kombinaljon
# A minta-sulyozas miatt erzekenyebb a zajra, mint a Gradient Boosting.
# =============================================================================

def adaboost_pelda(cls_data):
    """AdaBoost klasszifikacio bemutatasa."""
    szeparator("8. ADABOOST")

    from sklearn.ensemble import AdaBoostClassifier

    # A kurzusban n_estimators=100 volt
    print("\n  --- AdaBoostClassifier (Iris, 100 becsloe) ---")
    ab = AdaBoostClassifier(
        n_estimators=100,
        random_state=0,
        algorithm="SAMME",  # sklearn >=1.4 alapertelmezett
    )
    ab.fit(cls_data["X_train"], cls_data["y_train"])

    eredmeny = klasszifikacio_kiertekeles(
        ab,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "AdaBoost"
    )

    return [eredmeny]


# =============================================================================
#  9. XGBOOST
# =============================================================================
# Az XGBoost (eXtreme Gradient Boosting) a Gradient Boosting optimalizalt
# implementacioja, beepitett L1/L2 regularizacioval.
#
# Elonyei: gyors, pontos, kezeli a ritka (sparse) adatokat
# FONTOS: opcionalis fuggoseg, kulon kell telepiteni (pip install xgboost)
# =============================================================================

def xgboost_pelda(cls_data):
    """XGBoost klasszifikacio bemutatasa (opcionalis konyvtar)."""
    szeparator("9. XGBOOST")

    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("  [KIHAGYVA] Az xgboost nincs telepitve.")
        print("  Telepites: pip install xgboost")
        return []

    # A kurzusban max_depth=4, n_estimators=10 volt
    print("\n  --- XGBClassifier (Iris) ---")
    xgb = XGBClassifier(
        max_depth=4,
        n_estimators=10,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )
    xgb.fit(cls_data["X_train"], cls_data["y_train"])

    eredmeny = klasszifikacio_kiertekeles(
        xgb,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "XGBoost"
    )

    return [eredmeny]


# =============================================================================
#  10. LIGHTGBM
# =============================================================================
# A LightGBM gyorsabb tanulasi sebessegu es kevesebb memoriat hasznal
# a tobbi boosting algoritmusnal. Leaf-wise novesztesi strategiat hasznal
# (nem level-wise mint a hagyomanyos GBM).
#
# Elonyei: gyors, pontos, kezeli a tultanulast, nagy adathalmazokra jo
# FONTOS: opcionalis fuggoseg (pip install lightgbm)
# =============================================================================

def lightgbm_pelda(cls_data):
    """LightGBM klasszifikacio bemutatasa (opcionalis konyvtar)."""
    szeparator("10. LIGHTGBM")

    try:
        from lightgbm import LGBMClassifier
    except ImportError:
        print("  [KIHAGYVA] A lightgbm nincs telepitve.")
        print("  Telepites: pip install lightgbm")
        return []

    # A kurzusban max_depth=4, n_estimators=50 volt
    print("\n  --- LGBMClassifier (Iris) ---")
    lgbm = LGBMClassifier(
        max_depth=4,
        n_estimators=50,
        random_state=42,
        verbose=-1,  # Csendes mod
    )
    lgbm.fit(cls_data["X_train"], cls_data["y_train"])

    eredmeny = klasszifikacio_kiertekeles(
        lgbm,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "LightGBM"
    )

    return [eredmeny]


# =============================================================================
#  11. CATBOOST
# =============================================================================
# A CatBoost nativ modon kezeli a kategorikus valtozokat (nincs szukseg
# one-hot-encodingra). Gyors es pontos, kulonosen vegyes tipusu adatoknal.
#
# Elonyei: kategorikus feature-ok automatikus kezelese, pontos, gyors
# FONTOS: opcionalis fuggoseg (pip install catboost)
# =============================================================================

def catboost_pelda(cls_data):
    """CatBoost klasszifikacio bemutatasa (opcionalis konyvtar)."""
    szeparator("11. CATBOOST")

    try:
        from catboost import CatBoostClassifier
    except ImportError:
        print("  [KIHAGYVA] A catboost nincs telepitve.")
        print("  Telepites: pip install catboost")
        return []

    # A kurzusban max_depth=7, n_estimators=5, verbose=0 volt
    print("\n  --- CatBoostClassifier (Iris) ---")
    catboost = CatBoostClassifier(
        max_depth=7,
        n_estimators=5,
        verbose=0,  # Csendes mod (ne irjon ki tanulasi infokat)
        random_state=42,
    )
    catboost.fit(cls_data["X_train"], cls_data["y_train"])

    eredmeny = klasszifikacio_kiertekeles(
        catboost,
        cls_data["X_train"], cls_data["X_test"],
        cls_data["y_train"], cls_data["y_test"],
        "CatBoost"
    )

    return [eredmeny]


# =============================================================================
#  12. MODELL ÖSSZEHASONLÍTÁS SABLON (cross_val_score)
# =============================================================================
# A cross_val_score segitsegevel megbizhatobban hasonlithatjuk ossze
# a modelleket, mert tobbszoros felosztast hasznal (k-fold).
#
# cv=5: 5-szoros keresztvalidacio (az adathalmaz 5 reszre osztasa,
#       minden resz egyszer teszt, tobbszor tanito adat)
#
# Ez biztositja, hogy az eredmenyek nem fuggnek egyetlen veletlenszeru
# felosztastol.
# =============================================================================

def modell_osszehasonlitas(cls_data):
    """
    Minden elerheto klasszifikacios modell osszehasonlitasa
    5-fold keresztvalidacioval.
    """
    szeparator("12. MODELL OSSZEHASONLITAS (cross_val_score, 5-fold CV)")

    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import (
        RandomForestClassifier,
        GradientBoostingClassifier,
        AdaBoostClassifier,
    )

    # Alapmodellek (mindig elerheto sklearn-bol)
    modellek = {
        "KNN (k=5)": KNeighborsClassifier(n_neighbors=5),
        "LogReg": LogisticRegression(max_iter=10000, random_state=42),
        "SVC (rbf)": SVC(kernel="rbf", C=2, random_state=42),
        "DecisionTree": DecisionTreeClassifier(max_depth=5, random_state=42),
        "RandomForest": RandomForestClassifier(
            n_estimators=50, max_depth=10, random_state=42
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
        ),
        "AdaBoost": AdaBoostClassifier(
            n_estimators=100, random_state=42, algorithm="SAMME"
        ),
    }

    # Opcionalis konyvtarak hozzaadasa, ha elerheto
    try:
        from xgboost import XGBClassifier
        modellek["XGBoost"] = XGBClassifier(
            max_depth=4, n_estimators=50, verbosity=0,
            eval_metric="mlogloss", random_state=42
        )
    except ImportError:
        pass

    try:
        from lightgbm import LGBMClassifier
        modellek["LightGBM"] = LGBMClassifier(
            max_depth=4, n_estimators=50, verbose=-1, random_state=42
        )
    except ImportError:
        pass

    try:
        from catboost import CatBoostClassifier
        modellek["CatBoost"] = CatBoostClassifier(
            max_depth=5, n_estimators=50, verbose=0, random_state=42
        )
    except ImportError:
        pass

    # --- Teljes adathalmaz osszefuzese a keresztvalidaciohoz ---
    X_full = pd.concat([cls_data["X_train"], cls_data["X_test"]])
    y_full = pd.concat([cls_data["y_train"], cls_data["y_test"]])

    # --- Keresztvalidacio minden modellre ---
    eredmenyek = []
    print(f"\n  {'Modell':<22} {'Atlag CV Acc':>14} {'Szorasnegyzet':>14}")
    print(f"  {'-'*50}")

    for nev, modell in modellek.items():
        scores = cross_val_score(modell, X_full, y_full, cv=5, scoring="accuracy")
        atlag = scores.mean()
        szoras = scores.std()
        print(f"  {nev:<22} {atlag:>14.4f} {szoras:>14.4f}")
        eredmenyek.append({"nev": nev, "atlag_acc": atlag, "szoras": szoras})

    # --- Legjobb modell ---
    legjobb = max(eredmenyek, key=lambda x: x["atlag_acc"])
    print(f"\n  Legjobb modell: {legjobb['nev']} "
          f"(atlag accuracy: {legjobb['atlag_acc']:.4f})")

    # --- Szempontok a kurzus alapjan ---
    print("\n  A modellvalasztas szempontjai (a kurzus alapjan):")
    print("    - Interpretalhato: Linearis modellek, Dontesi Fa")
    print("    - Pontos: Ensemble modellek, SVM (magas dimenzioban)")
    print("    - Gyors: Linearis modellek, DecisionTree, KNN, LightGBM")
    print("    - Minimalis elokeszites: LightGBM, CatBoost")
    print("    - Nagy adathalmazokra: RandomForest, GradientBoosting, Linearis+SGD")


# =============================================================================
#  FŐ FUTTATÁS
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("  SUPERVISED ML ALGORITMUSOK - CUBIX EDU ML ENGINEERING KURZUS")
    print("  Forras: Cubix_ML_Engineer_ML_algorithms.ipynb (4. het)")
    print("=" * 80)

    # Adatok betoltese
    szeparator("ADATOK ELOKESZITESE")
    cls_data, bin_data, reg_data = adatok_elokeszitese()

    # 1. KNN
    knn_eredmenyek = knn_pelda(cls_data, reg_data)

    # 2. Linearis Regresszio
    linearis_regresszio_pelda(reg_data)

    # 3. Logisztikus Regresszio
    logreg_eredmenyek = logisztikus_regresszio_pelda(bin_data, cls_data)

    # 4. SVM
    svm_eredmenyek = svm_pelda(bin_data, reg_data)

    # 5. Dontesi Fa
    dt_eredmenyek = dontesi_fa_pelda(cls_data, reg_data)

    # 6. Random Forest
    rf_eredmenyek = random_forest_pelda(cls_data, reg_data)

    # 7. Gradient Boosting
    gb_eredmenyek = gradient_boosting_pelda(cls_data)

    # 8. AdaBoost
    ab_eredmenyek = adaboost_pelda(cls_data)

    # 9. XGBoost (opcionalis)
    xgb_eredmenyek = xgboost_pelda(cls_data)

    # 10. LightGBM (opcionalis)
    lgbm_eredmenyek = lightgbm_pelda(cls_data)

    # 11. CatBoost (opcionalis)
    catboost_eredmenyek = catboost_pelda(cls_data)

    # 12. Modell osszehasonlitas
    modell_osszehasonlitas(cls_data)

    szeparator("VEGEREDMENY")
    print("\n  Minden algoritmus sikeresen lefutott.")
    print("  A fenti eredmenyek alapjan osszehasonlithatod a modelleket.")
    print("  A 12. szekcio (cross_val_score) ad a legmegbizhatobb kepet.\n")
