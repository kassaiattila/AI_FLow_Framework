"""
Adat-elokeszites es Feature Engineering - Teljes peldakoddal
=============================================================

Ez a modul bemutatja az adatok elokeszitesenek es a feature engineering
legfontosabb lepeseit a Cubix EDU ML Engineering tananyag alapjan.

Tartalomjegyzek:
    1. Hianyzoo ertekek kezelese (SimpleImputer, KNNImputer)
    2. Outlier detektalas es kezeles (IQR, Z-score, vizualis)
    3. Feature Engineering (polinomialis, interakcios, datum-alapu)
    4. Encoding (LabelEncoder, OneHotEncoder, OrdinalEncoder, TargetEncoder)
    5. Skalazas (StandardScaler, MinMaxScaler, RobustScaler)
    6. Teljes elokeszitesi Pipeline (ColumnTransformer + Pipeline)

Forras: Cubix EDU - ML Engineering, 3. het tananyag
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# Sklearn - Pipeline es ColumnTransformer
from sklearn.compose import ColumnTransformer

# Sklearn - Imputalas
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

# Sklearn - Modell (a vegso pipeline peldahoz)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# Sklearn - Encoding
from sklearn.preprocessing import (
    LabelEncoder,
    MinMaxScaler,
    OneHotEncoder,
    OrdinalEncoder,
    PolynomialFeatures,
    RobustScaler,
    StandardScaler,
)

# Sklearn - TargetEncoder (sklearn >= 1.3)
try:
    from sklearn.preprocessing import TargetEncoder
except ImportError:
    TargetEncoder = None  # Regi sklearn verzioban nem elerheto


# =============================================================================
# Segédfuggveny: minta-adathalmaz letrehozasa
# =============================================================================

def minta_adathalmaz_letrehozasa(n=200, random_state=42):
    """
    Letrehoz egy szintetikus adathalmazt, amely tartalmaz:
    - numerikus feature-oket (kor, jovedelem, tapasztalat_ev)
    - kategorikus feature-oket (vegzettseg, varos, nem)
    - datum feature-t (csatlakozas_datum)
    - hianyzoo ertekeket (NaN)
    - outliereket
    - binaris celvaltozot (vasarolt)

    Returns:
        pd.DataFrame: A minta adathalmaz
    """
    rng = np.random.default_rng(random_state)

    n_rows = n

    # Numerikus feature-ok
    kor = rng.normal(35, 10, n_rows).clip(18, 70).astype(int)
    jovedelem = rng.normal(500_000, 200_000, n_rows).clip(100_000).astype(int)
    tapasztalat_ev = (kor - 18 - rng.integers(0, 5, n_rows)).clip(0)

    # Kategorikus feature-ok
    vegzettseg_kat = ["kozepiskola", "bsc", "msc", "phd"]
    vegzettseg = rng.choice(vegzettseg_kat, n_rows, p=[0.3, 0.35, 0.25, 0.1])

    varos_kat = ["Budapest", "Debrecen", "Szeged", "Pecs", "Gyor"]
    varos = rng.choice(varos_kat, n_rows)

    nem_kat = ["ferfi", "no"]
    nem = rng.choice(nem_kat, n_rows)

    # Datum feature
    start_date = pd.Timestamp("2018-01-01")
    days_range = (pd.Timestamp("2024-12-31") - start_date).days
    csatlakozas_datum = [
        start_date + pd.Timedelta(days=int(d))
        for d in rng.integers(0, days_range, n_rows)
    ]

    # Celvaltozo (vasarolt) - fugg a jovedelem es kor kockazattol
    p_vasarol = 1 / (1 + np.exp(-(jovedelem - 500_000) / 200_000 + (kor - 35) / 20))
    vasarolt = rng.binomial(1, p_vasarol)

    df = pd.DataFrame({
        "kor": kor.astype(float),
        "jovedelem": jovedelem.astype(float),
        "tapasztalat_ev": tapasztalat_ev.astype(float),
        "vegzettseg": vegzettseg,
        "varos": varos,
        "nem": nem,
        "csatlakozas_datum": csatlakozas_datum,
        "vasarolt": vasarolt,
    })

    # --- Hianyzoo ertekek hozzaadasa (Missing At Random minta) ---
    # A tananyag szerint: MCAR, MAR, MNAR tipusok leteznek.
    # Itt MAR-t szimulalunk: idosebbeknel nagyobb esellyel hianyzik a jovedelem.
    hianyzas_maszk_jovedelem = rng.random(n_rows) < (kor / 150)
    df.loc[hianyzas_maszk_jovedelem, "jovedelem"] = np.nan

    # MCAR pelda: teljesen veletlenszeru hianyzas a tapasztalat_ev oszlopban
    hianyzas_maszk_tapasztalat = rng.random(n_rows) < 0.08
    df.loc[hianyzas_maszk_tapasztalat, "tapasztalat_ev"] = np.nan

    # Kategorikus hianyzas: nehany vegzettseg ertek hianyzik
    hianyzas_maszk_vegzettseg = rng.random(n_rows) < 0.05
    df.loc[hianyzas_maszk_vegzettseg, "vegzettseg"] = np.nan

    # --- Outlierek hozzaadasa ---
    # Nehany szelsoseges jovedelem ertek
    outlier_indexek = rng.choice(
        df.index[df["jovedelem"].notna()], size=5, replace=False
    )
    df.loc[outlier_indexek, "jovedelem"] = rng.integers(2_000_000, 5_000_000, 5)

    return df


# =============================================================================
# 1. SZAKASZ: Hianyzoo ertekek kezelese
# =============================================================================
# A tananyag (03_05) szerint a hianyzoo ertekek harom fo tipusa:
#   - MCAR (Missing Completely At Random): teljesen veletlenszeru hianyzas
#   - MAR (Missing At Random): a hianyzas fugg mas megfigyelt valtozotol
#   - MNAR (Missing Not At Random): a hianyzas fugg maga az ertek nagysegatol
#
# Kezelesi modszerek:
#   - Eltavolitas (sorok vagy oszlopok torlee)
#   - Helyettesites statisztikai mutatokkal (atlag, median, modusz)
#   - Gepi tanulasi modellel torteno imputalas (pl. KNNImputer)
#   - Kategorikus valtozoknal: kulon "hianyzoo" kategoria letrehozasa
# =============================================================================

def hianyzoo_ertekek_kezelese(df):
    """
    Bemutatja a hianyzoo ertekek kulonbozo kezelesi modszereit.

    A tananyag szerint:
    - Ha kevés sor tartalmaz hianyzoo erteket -> eltavolithatjuk oket
    - Folytonos valtozoknal: atlag, median, modusz hasznalhato
    - Kategorikus valtozoknal: modusz VAGY kulon "hianyzoo" kategoria
    - KNNImputer: a szomszedos adatpontok alapjan becsuljuk az erteket
    """
    print("=" * 70)
    print("1. HIANYZOO ERTEKEK KEZELESE")
    print("=" * 70)

    # --- 1.1 Hianyzoo ertekek felterkepezese ---
    print("\n--- 1.1 Hianyzoo ertekek osszegzese ---")
    hianyzoo_szamlalo = df.isnull().sum()
    hianyzoo_szazalek = (df.isnull().sum() / len(df)) * 100
    hianyzoo_tabla = pd.DataFrame({
        "Hianyzoo_db": hianyzoo_szamlalo,
        "Hianyzoo_%": hianyzoo_szazalek.round(2),
    })
    print(hianyzoo_tabla[hianyzoo_tabla["Hianyzoo_db"] > 0])

    # --- 1.2 SimpleImputer: atlag es median ---
    # A tananyag szerint: "folytonos valtozokat gyakran kulonbozo atlaggal
    # helyettesitjuk, mint a szamtani kozep, median vagy modusz"
    print("\n--- 1.2 SimpleImputer (median strategia) ---")
    numerikus_oszlopok = ["kor", "jovedelem", "tapasztalat_ev"]

    imputer_median = SimpleImputer(strategy="median")
    df_imputed_median = df.copy()
    df_imputed_median[numerikus_oszlopok] = imputer_median.fit_transform(
        df[numerikus_oszlopok]
    )
    print(f"Hianyzoo ertekek a median imputalas utan: "
          f"{df_imputed_median[numerikus_oszlopok].isnull().sum().sum()}")

    # --- 1.3 SimpleImputer: leggyakoribb ertek (modusz) kategorikushoz ---
    # A tananyag figyelmeztet: ha a modusz tulsulyos, erdemesebb
    # kulon "hianyzoo" kategoriat letrehozni, hogy ne torzitsa az aranyokat.
    print("\n--- 1.3 Kategorikus hianyzoo ertekek kezelese ---")
    df_imputed_kat = df.copy()

    # Modusz-alapu kitoltes
    imputer_modusz = SimpleImputer(strategy="most_frequent")
    df_imputed_kat[["vegzettseg"]] = imputer_modusz.fit_transform(
        df[["vegzettseg"]]
    )
    print(f"Vegzettseg hianyzoo (modusz imputalas utan): "
          f"{df_imputed_kat['vegzettseg'].isnull().sum()}")

    # Alternativa: kulon "ismeretlen" kategoria (a tananyag javaslata)
    df_kat_ismeretlen = df.copy()
    df_kat_ismeretlen["vegzettseg"] = (
        df_kat_ismeretlen["vegzettseg"].fillna("ismeretlen")
    )
    print(f"Vegzettseg ertekek (ismeretlen kategoriaval): "
          f"{df_kat_ismeretlen['vegzettseg'].value_counts().to_dict()}")

    # --- 1.4 KNNImputer: szomszedos adatpontok alapjan ---
    # Ez a gepi tanulasi megkozelites, amit a tananyag emlit:
    # "gepi tanulasi modellt epitunk, amely kifejezetten a hianyzoo
    # ertekek predikciojara szolgal"
    print("\n--- 1.4 KNNImputer (k=5 szomszed) ---")
    knn_imputer = KNNImputer(n_neighbors=5)
    df_knn = df.copy()
    df_knn[numerikus_oszlopok] = knn_imputer.fit_transform(
        df[numerikus_oszlopok]
    )
    print(f"Hianyzoo ertekek KNN imputalas utan: "
          f"{df_knn[numerikus_oszlopok].isnull().sum().sum()}")

    # Osszehasonlitas: median vs KNN atlagos jovedelem
    eredeti_atlag = df["jovedelem"].mean()
    median_atlag = df_imputed_median["jovedelem"].mean()
    knn_atlag = df_knn["jovedelem"].mean()
    print("\nJovedelem atlag osszehasonlitas:")
    print(f"  Eredeti (NaN nelkul): {eredeti_atlag:,.0f} Ft")
    print(f"  Median imputalas:     {median_atlag:,.0f} Ft")
    print(f"  KNN imputalas:        {knn_atlag:,.0f} Ft")

    return df_knn  # KNN-imputalt adattal megyunk tovabb


# =============================================================================
# 2. SZAKASZ: Outlier detektalas es kezeles
# =============================================================================
# A tananyag (03_06) szerint:
#   - Outlierek: "azok az ertekek, amelyek latvannyosan kivul esnek abbol
#     a tartomanybol, ahova egyebkent szoktak esni az adatok"
#   - Z-szkor: "(X - atlag) / szoras" -> |z| > 2.58 szignifikans outlier
#   - IQR (Interquartile Range): a kozepso 50% terjedelme
#   - Fontos a domen tudas: "nem minden esetben kell kidobni az outliereket"
# =============================================================================

def outlier_detektalas_es_kezeles(df):
    """
    Bemutatja az outlierek detektalasanak es kezelesenek modszereit.

    A tananyag harom fo megkozelitest emlit:
    1. Z-szkor: ha |z| > 3, akkor outlier (szignifikancia p < 0.01)
    2. IQR: Q1 - 1.5*IQR es Q3 + 1.5*IQR kozott van a "normalis" tartomany
    3. Vizualis: boxplot es scatter plot segitsegevel
    """
    print("\n" + "=" * 70)
    print("2. OUTLIER DETEKTALAS ES KEZELES")
    print("=" * 70)

    feature = "jovedelem"
    adatok = df[feature].dropna()

    # --- 2.1 Z-szkor alapu detektalas ---
    # A tananyag szerint: "kivonjuk az aktualis adatpont ertekebol a szamtani
    # kozepet, es ezt elosztjuk a szorassal"
    # |z| > 2 -> "jo esellyel outlier" (p = 0.05)
    # |z| > 2.58 -> "nagyon szignifikans outlier" (p = 0.01)
    # |z| > 3 -> altalanos hatarerteknek szoktak tekinteni
    print("\n--- 2.1 Z-szkor alapu outlier detektalas ---")
    z_scores = np.abs(stats.zscore(adatok))
    outlier_maszk_z = z_scores > 3
    print(f"Z-szkor > 3 alapjan talalt outlierek szama: {outlier_maszk_z.sum()}")
    print(f"Outlier ertekek: {adatok[outlier_maszk_z].values}")

    # --- 2.2 IQR alapu detektalas ---
    # A tananyag emliti: "a z-szkor vagy az interquartile range segithet
    # a detektálasban"
    print("\n--- 2.2 IQR (Interquartile Range) alapu outlier detektalas ---")
    Q1 = adatok.quantile(0.25)
    Q3 = adatok.quantile(0.75)
    IQR = Q3 - Q1
    also_hatar = Q1 - 1.5 * IQR
    felso_hatar = Q3 + 1.5 * IQR

    outlier_maszk_iqr = (adatok < also_hatar) | (adatok > felso_hatar)
    print(f"Q1 = {Q1:,.0f}, Q3 = {Q3:,.0f}, IQR = {IQR:,.0f}")
    print(f"Also hatar: {also_hatar:,.0f}, Felso hatar: {felso_hatar:,.0f}")
    print(f"IQR alapjan talalt outlierek szama: {outlier_maszk_iqr.sum()}")

    # --- 2.3 Vizualis outlier detektalas (boxplot) ---
    print("\n--- 2.3 Vizualis outlier detektalas ---")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Boxplot - az IQR vizualis megjelenites
    axes[0].boxplot(adatok, vert=True)
    axes[0].set_title(f"{feature} - Boxplot (outlier detektalas)")
    axes[0].set_ylabel("Ertek (Ft)")

    # Hisztogram Z-szkor hatarral
    axes[1].hist(adatok, bins=30, edgecolor="black", alpha=0.7)
    atlag = adatok.mean()
    szoras = adatok.std()
    for z_hatar in [-3, 3]:
        hatar_ertek = atlag + z_hatar * szoras
        axes[1].axvline(
            hatar_ertek, color="red", linestyle="--",
            label=f"Z={z_hatar} ({hatar_ertek:,.0f})"
        )
    axes[1].set_title(f"{feature} - Hisztogram Z-szkor hatarokkal")
    axes[1].set_xlabel("Ertek (Ft)")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig("outlier_detektalas.png", dpi=100, bbox_inches="tight")
    plt.close()
    print("Abra mentve: outlier_detektalas.png")

    # --- 2.4 Outlierek kezelese ---
    # A tananyag szerint: "hasonloan kezelni, mint peldaul a hianyzoo
    # ertekeket" - tehat eltavolitas, vagy ertek-helyettesites
    print("\n--- 2.4 Outlierek kezelese ---")
    df_kezelt = df.copy()

    # Modszer 1: Eltavolitas (ha kevés outlier van)
    df_eltavolitas = df[~df.index.isin(adatok[outlier_maszk_iqr].index)].copy()
    print(f"Sorok eltavolitas elott: {len(df)}, utan: {len(df_eltavolitas)}")

    # Modszer 2: Clipping (vagás a hatarertek-re)
    # Az outliereket a hatarertek-re allitjuk - ez megorizti az adatpontot
    df_kezelt[feature] = df_kezelt[feature].clip(
        lower=also_hatar, upper=felso_hatar
    )
    print(f"Clipping utan outlierek szama: "
          f"{((df_kezelt[feature] < also_hatar) | (df_kezelt[feature] > felso_hatar)).sum()}")

    # Modszer 3: Median-nel helyettesites (hianyzoo ertek logika)
    df_median_helyettesites = df.copy()
    median_ertek = adatok.median()
    df_median_helyettesites.loc[
        df_median_helyettesites[feature].isin(adatok[outlier_maszk_iqr].values),
        feature
    ] = median_ertek
    print(f"Median helyettesites: outlierek -> {median_ertek:,.0f} Ft")

    return df_kezelt


# =============================================================================
# 3. SZAKASZ: Feature Engineering
# =============================================================================
# A tananyag (03_07) szerint a Feature Engineering az "egyik legfontosabb
# resze a Data Scientist munkajanak". Fo lepesek:
#   - Feature Improvement: hianyzoo ertekek, outlierek, skalazas
#   - Feature Construction: uj feature-ok letrehozasa (pl. mozgo atlag)
#   - Feature Extraction: lenyeges informacio kinyerese (PCA, TFIDF)
#   - Feature Selection: legfontosabb feature-ok kivalasztasa
#   - Feature Transformation: encoding, skalazas
# =============================================================================

def feature_engineering(df):
    """
    Bemutatja a feature engineering kulonbozo technikait:
    - Polinomialis feature-ok (negyzetes, kozep tagok)
    - Interakcios feature-ok (ket feature szorzata)
    - Datum-alapu feature-ok (ev, honap, nap, napok szama)
    - Egyedi domain-specifikus feature-ok
    """
    print("\n" + "=" * 70)
    print("3. FEATURE ENGINEERING")
    print("=" * 70)

    df_fe = df.copy()

    # --- 3.1 Feature Construction: egyedi feature-ok ---
    # A tananyag szerint: "mi magunk hozunk letre uj feature-oket"
    # Pelda: "haztartasban elok fizetesebol osszeadjuk a teljes
    # haztartas bevetelet"
    print("\n--- 3.1 Feature Construction: egyedi feature-ok ---")

    # Jovedelem/kor arany - mennyit keres evente az eletkorahoz kepest
    df_fe["jovedelem_per_kor"] = df_fe["jovedelem"] / df_fe["kor"]

    # Tapasztalat arany - tapasztalat a munkaevekhez kepest
    munka_evek = df_fe["kor"] - 18
    df_fe["tapasztalat_arany"] = (
        df_fe["tapasztalat_ev"] / munka_evek.clip(lower=1)
    )

    print("Uj feature-ok: jovedelem_per_kor, tapasztalat_arany")
    print(df_fe[["jovedelem_per_kor", "tapasztalat_arany"]].describe().round(2))

    # --- 3.2 Polinomialis feature-ok ---
    # A tananyag emliti a Feature Extraction-t: "meglevoo feature-okbol
    # emelunk ki lenyeges informaciokat"
    print("\n--- 3.2 Polinomialis feature-ok (fokszam=2) ---")
    poly = PolynomialFeatures(degree=2, include_bias=False, interaction_only=False)
    numerikus_cols = ["kor", "jovedelem"]
    poly_features = poly.fit_transform(df_fe[numerikus_cols].fillna(0))
    poly_nevek = poly.get_feature_names_out(numerikus_cols)
    print(f"Eredeti feature-ok szama: {len(numerikus_cols)}")
    print(f"Polinomialis feature-ok szama: {len(poly_nevek)}")
    print(f"Uj feature nevek: {list(poly_nevek)}")

    # --- 3.3 Interakcios feature-ok ---
    print("\n--- 3.3 Interakcios feature-ok (csak interakciok) ---")
    poly_inter = PolynomialFeatures(
        degree=2, include_bias=False, interaction_only=True
    )
    inter_features = poly_inter.fit_transform(df_fe[numerikus_cols].fillna(0))
    inter_nevek = poly_inter.get_feature_names_out(numerikus_cols)
    print(f"Interakcios feature-ok: {list(inter_nevek)}")
    # Pelda: kor * jovedelem -> magasabb erteku idosebb, jomodunak
    df_fe["kor_x_jovedelem"] = df_fe["kor"] * df_fe["jovedelem"]

    # --- 3.4 Datum-alapu feature-ok ---
    # Datum feature-ok kivonatasa - ez tipikus Feature Extraction
    print("\n--- 3.4 Datum-alapu feature-ok ---")
    df_fe["csatlakozas_ev"] = df_fe["csatlakozas_datum"].dt.year
    df_fe["csatlakozas_honap"] = df_fe["csatlakozas_datum"].dt.month
    df_fe["csatlakozas_negyedev"] = df_fe["csatlakozas_datum"].dt.quarter
    df_fe["csatlakozas_het_napja"] = df_fe["csatlakozas_datum"].dt.dayofweek

    # Napok szama a csatlakozas ota (feature construction)
    referencia_datum = pd.Timestamp("2025-01-01")
    df_fe["napok_ota_csatlakozott"] = (
        (referencia_datum - df_fe["csatlakozas_datum"]).dt.days
    )

    # Hetvege-e? (binaris feature)
    df_fe["hetvegen_csatlakozott"] = (
        df_fe["csatlakozas_het_napja"] >= 5
    ).astype(int)

    datum_feature_ok = [
        "csatlakozas_ev", "csatlakozas_honap", "csatlakozas_negyedev",
        "csatlakozas_het_napja", "napok_ota_csatlakozott",
        "hetvegen_csatlakozott",
    ]
    print(f"Letrehozott datum feature-ok: {datum_feature_ok}")
    print(df_fe[datum_feature_ok].head())

    # --- 3.5 Binning (diskretizalas) ---
    print("\n--- 3.5 Binning: folytonos valtozo kategorikussa alakitasa ---")
    df_fe["kor_csoport"] = pd.cut(
        df_fe["kor"],
        bins=[0, 25, 35, 45, 55, 100],
        labels=["fiatal", "fiatal_felnottt", "kozepkoru", "idosebb", "idos"],
    )
    print("Kor csoportok eloszlasa:")
    print(df_fe["kor_csoport"].value_counts().sort_index())

    return df_fe


# =============================================================================
# 4. SZAKASZ: Encoding (kategorikus valtozok kodolasa)
# =============================================================================
# A tananyag (03_08) szerint:
#   - LabelEncoder: kategoriak -> szamok (0, 1, 2, ...)
#     Hatrany: "az algoritmus valoszinuleg azt fogja gondolni, hogy az alma
#     es a csirke azok nagyon hasonloak" (tehat hamis sorrendet feltetelez)
#   - OneHotEncoder: minden kategoria kulon binaris oszlop lesz
#     Hatrany: "nagyon sok uj oszlopot kell letrehozni"
#   - DummyEncoding: OneHot, de egy oszloppal kevesebb (referenciakateg.)
#   - OrdinalEncoder: ha VAN termeszetes sorrend (pl. iskolai vegzettseg)
#   - TargetEncoder: a celvaltozo atlagaval kodol
# =============================================================================

def encoding_bemutatasa(df):
    """
    Bemutatja a kategorikus valtozok kulonbozo kodolasi technikait.
    """
    print("\n" + "=" * 70)
    print("4. ENCODING (KATEGORIKUS VALTOZOK KODOLASA)")
    print("=" * 70)

    df_enc = df.copy()
    # Hianyzoo kategorikus ertekek kitoltese az encoding elott
    df_enc["vegzettseg"] = df_enc["vegzettseg"].fillna("ismeretlen")
    df_enc["varos"] = df_enc["varos"].fillna("ismeretlen")
    df_enc["nem"] = df_enc["nem"].fillna("ismeretlen")

    # --- 4.1 LabelEncoder ---
    # A tananyag szerint: "kategoriavaltozookat kulonbozo szamokkal jeloljuk meg"
    # Fontos: "amint egyszer eldontottuk, hogy az alma lesz az egyes,
    # innentol kezdve kovetkezetesen ragaszkodni kell ehhez"
    # Figyelmeztes: hamis tavolsag-ertelmezest okozhat!
    print("\n--- 4.1 LabelEncoder ---")
    le = LabelEncoder()
    df_enc["nem_label"] = le.fit_transform(df_enc["nem"])
    print(f"Nem oszlop kodolasa: {dict(zip(le.classes_, le.transform(le.classes_)))}")
    print("FIGYELEM: LabelEncoder hamis sorrendet feltetelezhet az "
          "algoritmusnal!")

    # --- 4.2 OrdinalEncoder ---
    # Akkor hasznaljuk, ha VAN termeszetes sorrend a kategoriak kozott
    # Pelda: iskolai vegzettseg (kozepiskola < bsc < msc < phd)
    print("\n--- 4.2 OrdinalEncoder (rendezett kategoriak) ---")
    sorrend = [["ismeretlen", "kozepiskola", "bsc", "msc", "phd"]]
    oe = OrdinalEncoder(categories=sorrend, handle_unknown="use_encoded_value",
                        unknown_value=-1)
    df_enc["vegzettseg_ordinal"] = oe.fit_transform(
        df_enc[["vegzettseg"]]
    ).astype(int)
    print("Vegzettseg ordinalis kodolasa:")
    vegz_mapping = dict(zip(sorrend[0], range(len(sorrend[0]))))
    print(f"  {vegz_mapping}")

    # --- 4.3 OneHotEncoder ---
    # A tananyag szerint: "ahany kategoriank van, annyi oszlopot fogunk
    # letrehozni" -> minden kategoria kulon binaris oszlop
    print("\n--- 4.3 OneHotEncoder ---")
    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    varos_encoded = ohe.fit_transform(df_enc[["varos"]])
    varos_nevek = ohe.get_feature_names_out(["varos"])
    print(f"Varos OneHot oszlopok: {list(varos_nevek)}")
    print("Pelda (elso 3 sor):")
    print(pd.DataFrame(varos_encoded[:3], columns=varos_nevek))

    # Dummy encoding (drop='first' -> egy oszloppal kevesebb)
    # A tananyag szerint: "a dummy encoding eseteben egy oszloppal kevesebb van"
    print("\n--- 4.3b Dummy Encoding (drop='first') ---")
    ohe_dummy = OneHotEncoder(
        sparse_output=False, drop="first", handle_unknown="ignore"
    )
    varos_dummy = ohe_dummy.fit_transform(df_enc[["varos"]])
    varos_dummy_nevek = ohe_dummy.get_feature_names_out(["varos"])
    print(f"Dummy oszlopok (egy kevesebbel): {list(varos_dummy_nevek)}")

    # --- 4.4 TargetEncoder ---
    # A celvaltozo (target) atlagaval kodol minden kategoriat
    # Hasznos magas kardinalitasu (sok egyedi ertek) kategorikus valtozoknal
    if TargetEncoder is not None:
        print("\n--- 4.4 TargetEncoder ---")
        te = TargetEncoder(smooth="auto")
        df_enc["varos_target"] = te.fit_transform(
            df_enc[["varos"]], df_enc["vasarolt"]
        )
        print("Varos TargetEncoder ertekek (elso 5 sor):")
        print(df_enc[["varos", "varos_target"]].head(10))
    else:
        print("\n--- 4.4 TargetEncoder ---")
        print("MEGJEGYZES: TargetEncoder sklearn >= 1.3 verzioval erheto el")

    # Osszefoglalo
    print("\n--- Encoding osszefoglalo ---")
    print("| Modszer         | Mikor hasznald?                            |")
    print("|-----------------|-------------------------------------------|")
    print("| LabelEncoder    | Binaris (2 erteku) valtozok               |")
    print("| OrdinalEncoder  | Van termeszetes sorrend (pl. vegzettseg)  |")
    print("| OneHotEncoder   | Nincs sorrend, keves kategoria            |")
    print("| Dummy (drop=1)  | OneHot, de multikollinearitas elkerulese  |")
    print("| TargetEncoder   | Sok kategoria, regresszio/klasszifikacio  |")

    return df_enc


# =============================================================================
# 5. SZAKASZ: Skalazas
# =============================================================================
# A tananyag (03_09) szerint a skalazas elonyei:
#   - Elkeruljuk, hogy egy feature dominalja a tanulast
#   - Gyorsabb konvergencia (gradiens csokkentes)
#   - Tavolsagalapu algoritmusoknal (KNN, K-means) elengedhetetlen
#   - Regularizaciot (Lasso, Ridge) javitja
#
# Ket fo modszer:
#   - Min-max normalizalas: 0 es 1 koze skalaz
#     Hatrany: "outlierek miatt szuk tartomanyba zsufoldik az adat"
#   - Sztenderdizalas: atlag=0, szoras=1
#     Elony: "outlierekre nem erzekeny"
#     Elvaras: Gauss-eloszlasu adat (de nem kotelezoo)
#
# Mikor NEM kell skalazni:
#   - Fa alapu algoritmusoknal (Decision Tree, Random Forest, XGBoost)
# =============================================================================

def skalazas_bemutatasa(df):
    """
    Bemutatja a harom fo skalazasi modszert es osszehasonlitja oket.
    """
    print("\n" + "=" * 70)
    print("5. SKALAZAS")
    print("=" * 70)

    numerikus_cols = ["kor", "jovedelem", "tapasztalat_ev"]
    df_num = df[numerikus_cols].dropna()

    # --- 5.1 StandardScaler (sztenderdizalas) ---
    # A tananyag szerint: "fogja az adott x-pontot, kivonja belole az atlagot,
    # es ezt elosztjuk a szorasaval a feature-nek"
    # Eredmeny: atlag = 0, szoras = 1
    print("\n--- 5.1 StandardScaler (sztenderdizalas) ---")
    scaler_std = StandardScaler()
    df_standard = pd.DataFrame(
        scaler_std.fit_transform(df_num),
        columns=numerikus_cols,
        index=df_num.index,
    )
    print("Sztenderdizalt adatok statisztikaja:")
    print(f"  Atlag: {df_standard.mean().round(4).to_dict()}")
    print(f"  Szoras: {df_standard.std().round(4).to_dict()}")
    print("A tananyag szerint: 'az atlagot nullara allitja, es a szorast egyre'")

    # --- 5.2 MinMaxScaler (normalizalas) ---
    # A tananyag szerint: "0 es 1 koze skalazza be az adatokat"
    # Keplelt: (X - X_min) / (X_max - X_min)
    print("\n--- 5.2 MinMaxScaler (min-max normalizalas) ---")
    scaler_mm = MinMaxScaler()
    df_minmax = pd.DataFrame(
        scaler_mm.fit_transform(df_num),
        columns=numerikus_cols,
        index=df_num.index,
    )
    print("Min-max normalizalt adatok:")
    print(f"  Minimum: {df_minmax.min().round(4).to_dict()}")
    print(f"  Maximum: {df_minmax.max().round(4).to_dict()}")
    print("FIGYELEM: 'ha vannak outlierek, szuk tartomanyba zsufoldik az adat'")

    # --- 5.3 RobustScaler ---
    # A tananyag emliti, hogy a sztenderdizalas "outlierekre nem erzekeny",
    # de a RobustScaler meg kevesbe erzekeny, mert mediant es IQR-t hasznal
    print("\n--- 5.3 RobustScaler (outlier-ellenallo) ---")
    scaler_robust = RobustScaler()
    df_robust = pd.DataFrame(
        scaler_robust.fit_transform(df_num),
        columns=numerikus_cols,
        index=df_num.index,
    )
    print("RobustScaler statisztikak:")
    print(f"  Median (kozepso ertek): {df_robust.median().round(4).to_dict()}")
    print("Elonye: mediant es IQR-t hasznal, igy az outlierekre kevesbe erzekeny")

    # --- 5.4 Vizualis osszehasonlitas ---
    print("\n--- 5.4 Skalazasi modszerek vizualis osszehasonlitasa ---")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    feature_idx = 1  # jovedelem
    feature_nev = numerikus_cols[feature_idx]

    # Eredeti
    axes[0, 0].hist(df_num[feature_nev], bins=30, edgecolor="black", alpha=0.7,
                    color="steelblue")
    axes[0, 0].set_title(f"Eredeti: {feature_nev}")

    # StandardScaler
    axes[0, 1].hist(df_standard[feature_nev], bins=30, edgecolor="black",
                    alpha=0.7, color="orange")
    axes[0, 1].set_title(f"StandardScaler: {feature_nev}")

    # MinMaxScaler
    axes[1, 0].hist(df_minmax[feature_nev], bins=30, edgecolor="black",
                    alpha=0.7, color="green")
    axes[1, 0].set_title(f"MinMaxScaler: {feature_nev}")

    # RobustScaler
    axes[1, 1].hist(df_robust[feature_nev], bins=30, edgecolor="black",
                    alpha=0.7, color="purple")
    axes[1, 1].set_title(f"RobustScaler: {feature_nev}")

    plt.suptitle("Skalazasi modszerek osszehasonlitasa", fontsize=14)
    plt.tight_layout()
    plt.savefig("skalazas_osszehasonlitas.png", dpi=100, bbox_inches="tight")
    plt.close()
    print("Abra mentve: skalazas_osszehasonlitas.png")

    # --- 5.5 Mikor kell skalazni? ---
    print("\n--- 5.5 Skalazas alkalmazasa (tananyag osszefoglalo) ---")
    print("KELL skalazni:")
    print("  - KNN, K-means (tavolsagalapu)")
    print("  - Logisztikus regresszio, Linearis regresszio")
    print("  - SVM (Support Vector Machine)")
    print("  - Neuralis halozatok (gradiens csokkentes)")
    print("  - Dimenziocsokkentos megoldasok (PCA)")
    print("  - Lasso, Ridge (regularizacio)")
    print("NEM KELL skalazni:")
    print("  - Fa alapu algoritmusok (Decision Tree, Random Forest, XGBoost)")


# =============================================================================
# 6. SZAKASZ: Teljes elokeszitesi Pipeline (ColumnTransformer + Pipeline)
# =============================================================================
# A Pipeline es a ColumnTransformer lehetove teszi, hogy az osszes
# elokeszitesi lepest egyetlen objektumba foglaljuk. Elonyok:
#   - Reprodukalhato: ugyanaz a transzformacio a train es test adatokon
#   - Nincs adatszivargas: fit csak a train adatokon, transform mindketton
#   - Karbantarthato: a teljes elofeldolgozas egy helyen van
# =============================================================================

def teljes_pipeline():
    """
    Teljes end-to-end pipeline a mintaadathalmazzal:
    1. Adat betoltes
    2. Feature engineering (datum feature-ok)
    3. ColumnTransformer (imputalas + encoding + skalazas)
    4. Modell betanitas (LogisticRegression)
    5. Kiertekeles
    """
    print("\n" + "=" * 70)
    print("6. TELJES ELOKESZITESI PIPELINE (ColumnTransformer + Pipeline)")
    print("=" * 70)

    # --- 6.1 Adat betoltes es elokeszites ---
    print("\n--- 6.1 Adat betoltes ---")
    df = minta_adathalmaz_letrehozasa(n=500, random_state=42)

    # Datum feature-ok kivonatasa (ezt a pipeline elott csinalju,
    # mert a ColumnTransformer nem kezel datum tipust kozvetlenul)
    df["csatlakozas_ev"] = df["csatlakozas_datum"].dt.year
    df["csatlakozas_honap"] = df["csatlakozas_datum"].dt.month
    df["napok_ota"] = (
        pd.Timestamp("2025-01-01") - df["csatlakozas_datum"]
    ).dt.days

    # Hianyzoo kategorikus ertekek -> "ismeretlen" (a tananyag javaslata)
    df["vegzettseg"] = df["vegzettseg"].fillna("ismeretlen")

    # Feature-ok es celvaltozo szetvagasa
    # A datum oszlopot eldobjuk, mert mar kinyertuk a feature-oket belole
    X = df.drop(columns=["vasarolt", "csatlakozas_datum"])
    y = df["vasarolt"]

    print(f"Adathalmaz merete: {X.shape}")
    print(f"Celvaltozo eloszlas: {y.value_counts().to_dict()}")

    # --- 6.2 Train/test split ---
    print("\n--- 6.2 Train/test split ---")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {X_train.shape}, Test: {X_test.shape}")

    # --- 6.3 Oszlop-tipusok definialasa ---
    # Numerikus feature-ok: imputalas (median) + skalazas (StandardScaler)
    numerikus_feature_ok = [
        "kor", "jovedelem", "tapasztalat_ev",
        "csatlakozas_ev", "csatlakozas_honap", "napok_ota",
    ]

    # Kategorikus feature-ok sorrenddel: OrdinalEncoder
    ordinalis_feature_ok = ["vegzettseg"]
    ordinalis_sorrend = [["ismeretlen", "kozepiskola", "bsc", "msc", "phd"]]

    # Kategorikus feature-ok sorrend nelkul: OneHotEncoder
    nominalis_feature_ok = ["varos", "nem"]

    # --- 6.4 ColumnTransformer definiialasa ---
    # Minden oszlop-tipushoz kulon elofeldolgozasi pipeline
    print("\n--- 6.3-6.4 Pipeline felepitese ---")

    # Numerikus pipeline: hianyzoo ertekek (median) -> skalazas
    numerikus_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    # Ordinalis pipeline: OrdinalEncoder (vegzettseg szintekkel)
    ordinalis_pipeline = Pipeline(steps=[
        ("encoder", OrdinalEncoder(
            categories=ordinalis_sorrend,
            handle_unknown="use_encoded_value",
            unknown_value=-1,
        )),
    ])

    # Nominalis pipeline: OneHotEncoder (varos, nem)
    nominalis_pipeline = Pipeline(steps=[
        ("encoder", OneHotEncoder(
            sparse_output=False,
            drop="first",       # Dummy encoding: egy oszloppal kevesebb
            handle_unknown="ignore",
        )),
    ])

    # Osszerakjuk a ColumnTransformerbe
    elofeldolgozo = ColumnTransformer(
        transformers=[
            ("num", numerikus_pipeline, numerikus_feature_ok),
            ("ord", ordinalis_pipeline, ordinalis_feature_ok),
            ("nom", nominalis_pipeline, nominalis_feature_ok),
        ],
        remainder="drop",  # Nem hasznalt oszlopok eldobasa
    )

    # --- 6.5 Teljes Pipeline: elofeldolgozas + modell ---
    teljes_pipeline_obj = Pipeline(steps=[
        ("elofeldolgozas", elofeldolgozo),
        ("modell", LogisticRegression(max_iter=1000, random_state=42)),
    ])

    print("Pipeline felepitese:")
    print(teljes_pipeline_obj)

    # --- 6.6 Tanitas ---
    # FONTOS: a pipeline.fit() csak a TRAIN adaton fut -> nincs adatszivargas!
    print("\n--- 6.5-6.6 Tanitas es kiertekeles ---")
    teljes_pipeline_obj.fit(X_train, y_train)

    # --- 6.7 Predikalas es kiertekeles ---
    y_pred = teljes_pipeline_obj.predict(X_test)
    pontossag = accuracy_score(y_test, y_pred)

    print(f"\nModell pontossag (accuracy): {pontossag:.4f}")
    print("\nReszletes kiertekeles:")
    print(classification_report(
        y_test, y_pred, target_names=["Nem vasarolt", "Vasarolt"]
    ))

    # --- 6.8 Transzformalt feature nevek ---
    print("--- 6.7 Transzformalt feature-ok ---")
    try:
        feature_nevek = teljes_pipeline_obj.named_steps[
            "elofeldolgozas"
        ].get_feature_names_out()
        print(f"Osszes feature a modellben ({len(feature_nevek)} db):")
        for nev in feature_nevek:
            print(f"  - {nev}")
    except AttributeError:
        print("Feature nevek nem erheto el ebben a sklearn verzioban")

    # --- 6.9 Pipeline mentes es betoltes pelda ---
    print("\n--- 6.8 Pipeline mentes (joblib) ---")
    print("# import joblib")
    print("# joblib.dump(teljes_pipeline_obj, 'adat_pipeline.joblib')")
    print("# betoltott_pipeline = joblib.load('adat_pipeline.joblib')")
    print("# y_uj = betoltott_pipeline.predict(X_uj)")

    return teljes_pipeline_obj


# =============================================================================
# FO FUTTATAS
# =============================================================================

if __name__ == "__main__":
    print("*" * 70)
    print("ADAT-ELOKESZITES ES FEATURE ENGINEERING")
    print("Cubix EDU - ML Engineering, 3. het tananyag")
    print("*" * 70)

    # Minta adathalmaz letrehozasa
    df = minta_adathalmaz_letrehozasa()
    print(f"\nMinta adathalmaz letrehozva: {df.shape[0]} sor, {df.shape[1]} oszlop")
    print(f"Oszlopok: {list(df.columns)}")
    print("\nElso 5 sor:")
    print(df.head())

    # 1. Hianyzoo ertekek kezelese
    df_clean = hianyzoo_ertekek_kezelese(df)

    # 2. Outlier detektalas es kezeles
    df_no_outlier = outlier_detektalas_es_kezeles(df_clean)

    # 3. Feature Engineering
    df_fe = feature_engineering(df_no_outlier)

    # 4. Encoding
    df_encoded = encoding_bemutatasa(df_fe)

    # 5. Skalazas
    skalazas_bemutatasa(df_no_outlier)

    # 6. Teljes Pipeline (fuggetlen, ujra letrehozott adattal)
    pipeline = teljes_pipeline()

    print("\n" + "=" * 70)
    print("PROGRAM VEGE")
    print("=" * 70)
