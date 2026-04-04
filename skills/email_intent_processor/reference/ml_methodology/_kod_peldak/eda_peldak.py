"""
Exploratory Data Analysis (EDA) - Felderito adatelemzes peldak
==============================================================

Cubix EDU - ML Engineering tananyag alapjan

Ez a fajl bemutatja az EDA legfontosabb lepeseit es technikait:
  1. Adat beolvasas es elso attekintes
  2. Hianyzo ertekek vizualizalasa
  3. Univariate elemzes (egyvaltozos)
  4. Bivariate elemzes (ketvaltozos)
  5. Korrelacios matrix es heatmap
  6. Pairplot
  7. Kategorikus valtozok elemzese
  8. Eloszlas vizsgalat (ferdeseg, csucossag)

Hasznalt adathalmaz: Titanic (seaborn beepitett dataset)
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# --- Matplotlib alapbeallitasok ---
plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["figure.dpi"] = 100
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
sns.set_style("whitegrid")


# ============================================================================
# 1. ADAT BEOLVASAS ES ELSO ATTEKINTES
# ============================================================================
# Az EDA elso lepese mindig az adatok megismerese: mekkora az adathalmaz,
# milyen tipusu oszlopok vannak, vannak-e hianyzo ertekek.
# A Pandas DataFrame .info(), .describe(), .shape, .dtypes metodusai
# mar adatvizualizacio nelkul is jo betekintest nyujtanak.
# ============================================================================

def adat_attekintes(df: pd.DataFrame) -> None:
    """Az adathalmaz alapveto jellemzoinek kiirasa."""

    print("=" * 70)
    print("1. ADAT ATTEKINTES")
    print("=" * 70)

    # --- Merete ---
    print(f"\nAdathalmaz merete (sorok, oszlopok): {df.shape}")

    # --- Oszlopok tipusai ---
    print(f"\nOszlopok tipusai:\n{df.dtypes}")

    # --- Info: tipusok, nem-null ertekek szama ---
    print("\n--- DataFrame.info() ---")
    df.info()

    # --- Leiro statisztikak numerikus oszlopokra ---
    print("\n--- Numerikus oszlopok leiro statisztikai (describe) ---")
    print(df.describe())

    # --- Leiro statisztikak kategorikus oszlopokra ---
    print("\n--- Kategorikus oszlopok leiro statisztikai ---")
    print(df.describe(include=["object", "category"]))

    # --- Elso es utolso sorok ---
    print("\n--- Elso 5 sor ---")
    print(df.head())

    print("\n--- Utolso 5 sor ---")
    print(df.tail())


# ============================================================================
# 2. HIANYZO ERTEKEK VIZUALIZALASA
# ============================================================================
# A hianyzo adatok felmerese az EDA egyik legfontosabb lepese.
# A tananyagban emlitett modszer: oszloponkenti hianyzo ertekek szama,
# heatmap a hianyzo ertekek mintazatanak felfedezesehez.
# A missingno konyvtar kifejezetten erre a celra keszult.
# ============================================================================

def hianyzo_ertekek_elemzese(df: pd.DataFrame) -> None:
    """Hianyzo ertekek vizualizalasa tobb modszerrel."""

    print("\n" + "=" * 70)
    print("2. HIANYZO ERTEKEK VIZUALIZALASA")
    print("=" * 70)

    # --- Hianyzo ertekek szama es aranya oszloponkent ---
    hianyzo = df.isnull().sum()
    hianyzo_pct = (df.isnull().sum() / len(df)) * 100
    hianyzo_tablazat = pd.DataFrame({
        "Hianyzo (db)": hianyzo,
        "Hianyzo (%)": hianyzo_pct.round(2)
    })
    # Csak azokat az oszlopokat mutatjuk, ahol van hianyzo ertek
    hianyzo_tablazat = hianyzo_tablazat[hianyzo_tablazat["Hianyzo (db)"] > 0]
    hianyzo_tablazat = hianyzo_tablazat.sort_values("Hianyzo (%)", ascending=False)
    print(f"\nHianyzo ertekek osszesen: {df.isnull().sum().sum()}")
    print(f"Hianyzo ertekek aranya: {(df.isnull().sum().sum() / df.size * 100):.1f}%")
    print(f"\nHianyzo ertekek oszloponkent:\n{hianyzo_tablazat}")

    # --- 2a. Oszlopdiagram a hianyzo ertekekrol ---
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))

    # Bal oldal: barplot a hianyzo ertekek szamarol
    if not hianyzo_tablazat.empty:
        hianyzo_tablazat["Hianyzo (%)"].plot(
            kind="bar", ax=axes[0], color="coral", edgecolor="black"
        )
        axes[0].set_title("Hianyzo ertekek aranya oszloponkent (%)")
        axes[0].set_ylabel("Hianyzo ertekek (%)")
        axes[0].tick_params(axis="x", rotation=45)
    else:
        axes[0].text(0.5, 0.5, "Nincs hianyzo ertek!", ha="center", va="center",
                     fontsize=14)
        axes[0].set_title("Hianyzo ertekek aranya")

    # Jobb oldal: heatmap a hianyzo ertekek mintazatarol
    # Hasonlo a missingno matrix abrajahoz
    sns.heatmap(
        df.isnull(),
        cbar=True,
        yticklabels=False,
        cmap="YlOrRd",
        ax=axes[1]
    )
    axes[1].set_title("Hianyzo ertekek heatmap (sarga = hianyzo)")

    plt.tight_layout()
    plt.savefig("eda_02_hianyzo_ertekek.png", bbox_inches="tight")
    plt.show()

    # --- 2b. missingno konyvtar (opcionalis) ---
    # Ha telepitve van a missingno, hasznaljuk azt is
    try:
        import missingno as msno

        fig, axes = plt.subplots(1, 2, figsize=(16, 5))

        # Matrix abra: vizualisan mutatja, hol vannak hianyzo ertekek
        msno.matrix(df, ax=axes[0], sparkline=False, fontsize=8)
        axes[0].set_title("missingno matrix")

        # Bar abra: oszloponkenti kitoltottseg
        msno.bar(df, ax=axes[1], fontsize=8)
        axes[1].set_title("missingno bar (kitoltottseg)")

        plt.tight_layout()
        plt.savefig("eda_02_missingno.png", bbox_inches="tight")
        plt.show()

        print("\nmissingno abrak elkeszultek.")
    except ImportError:
        print("\n[INFO] A 'missingno' konyvtar nincs telepitve.")
        print("       Telepites: pip install missingno")


# ============================================================================
# 3. UNIVARIATE ELEMZES (egyvaltozos)
# ============================================================================
# Az univariate elemzes soran egyetlen valtozot vizsgalunk onmagaban.
# Folytonos valtozoknal: hisztogram, boxplot, KDE (surusegfuggveny)
# Kategorikus valtozoknal: value_counts, oszlopdiagram
# ============================================================================

def univariate_elemzes(df: pd.DataFrame) -> None:
    """Egyvaltozos elemzes: hisztogramok, boxplotok, value_counts."""

    print("\n" + "=" * 70)
    print("3. UNIVARIATE ELEMZES")
    print("=" * 70)

    # --- Numerikus oszlopok kivalasztasa ---
    numerikus_oszlopok = df.select_dtypes(include=[np.number]).columns.tolist()
    kategorikus_oszlopok = df.select_dtypes(include=["object", "category"]).columns.tolist()

    print(f"\nNumerikus oszlopok ({len(numerikus_oszlopok)}): {numerikus_oszlopok}")
    print(f"Kategorikus oszlopok ({len(kategorikus_oszlopok)}): {kategorikus_oszlopok}")

    # --- 3a. Hisztogramok a numerikus oszlopokra ---
    # A hisztogram a folytonos valtozok eloszlasat mutatja.
    # KDE (Kernel Density Estimation) gorbevel egyutt meg informativabb.
    if numerikus_oszlopok:
        n_cols = 3
        n_rows = (len(numerikus_oszlopok) + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
        axes = axes.flatten() if n_rows * n_cols > 1 else [axes]

        for i, col in enumerate(numerikus_oszlopok):
            sns.histplot(df[col].dropna(), kde=True, ax=axes[i],
                         color="steelblue", edgecolor="black")
            axes[i].set_title(f"{col} eloszlasa")
            axes[i].set_xlabel(col)
            axes[i].set_ylabel("Gyakorisag")

        # Ures tengelyek elrejtese
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.suptitle("Numerikus valtozok hisztogramjai (KDE gorbevel)", fontsize=14, y=1.02)
        plt.tight_layout()
        plt.savefig("eda_03a_hisztogramok.png", bbox_inches="tight")
        plt.show()

    # --- 3b. Boxplotok a numerikus oszlopokra ---
    # A boxplot megmutatja: minimum, Q1, median, Q3, maximum es az outliereket.
    if numerikus_oszlopok:
        n_rows = (len(numerikus_oszlopok) + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
        axes = axes.flatten() if n_rows * n_cols > 1 else [axes]

        for i, col in enumerate(numerikus_oszlopok):
            sns.boxplot(y=df[col].dropna(), ax=axes[i], color="lightgreen",
                        flierprops={"marker": "o", "markerfacecolor": "red"})
            axes[i].set_title(f"{col} boxplot")
            axes[i].set_ylabel(col)

        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.suptitle("Numerikus valtozok boxplotjai", fontsize=14, y=1.02)
        plt.tight_layout()
        plt.savefig("eda_03b_boxplotok.png", bbox_inches="tight")
        plt.show()

    # --- 3c. Kategorikus valtozok: value_counts es oszlopdiagram ---
    if kategorikus_oszlopok:
        for col in kategorikus_oszlopok:
            print(f"\n--- {col} ertekek gyakorisaga ---")
            print(df[col].value_counts())

        n_rows_cat = (len(kategorikus_oszlopok) + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows_cat, n_cols,
                                 figsize=(5 * n_cols, 4 * n_rows_cat))
        if n_rows_cat * n_cols == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        for i, col in enumerate(kategorikus_oszlopok):
            # Maximum 15 kategoria megjelenitese (atlathatosag)
            top_vals = df[col].value_counts().head(15)
            top_vals.plot(kind="bar", ax=axes[i], color="mediumpurple",
                          edgecolor="black")
            axes[i].set_title(f"{col} gyakorisaga")
            axes[i].set_ylabel("Darabszam")
            axes[i].tick_params(axis="x", rotation=45)

        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.suptitle("Kategorikus valtozok oszlopdiagramjai", fontsize=14, y=1.02)
        plt.tight_layout()
        plt.savefig("eda_03c_kategorikus.png", bbox_inches="tight")
        plt.show()


# ============================================================================
# 4. BIVARIATE ELEMZES (ketvaltozos)
# ============================================================================
# Ket valtozo egyuttes vizsgalata:
#   - Folytonos vs. folytonos: scatter plot
#   - Kategorikus vs. folytonos: boxplot csoportositva, barplot
#   - Kategorikus vs. kategorikus: count plot, crosstab
# ============================================================================

def bivariate_elemzes(df: pd.DataFrame) -> None:
    """Ketvaltozos elemzes: scatter plot, csoportositott boxplot es barplot."""

    print("\n" + "=" * 70)
    print("4. BIVARIATE ELEMZES")
    print("=" * 70)

    fig, axes = plt.subplots(2, 2, figsize=(14, 11))

    # --- 4a. Scatter plot: folytonos vs. folytonos ---
    # Eletkor es viteldij kapcsolata, szinezve a tuleles szerint
    sns.scatterplot(
        data=df, x="age", y="fare", hue="survived",
        palette="Set1", alpha=0.6, ax=axes[0, 0]
    )
    axes[0, 0].set_title("Eletkor vs. Viteldij (szinezve: tuleles)")
    axes[0, 0].set_xlabel("Eletkor (ev)")
    axes[0, 0].set_ylabel("Viteldij (fare)")

    # --- 4b. Csoportositott boxplot: kategorikus vs. folytonos ---
    # A kurzusban emlitett pelda: osztaly vs. kor, szinezve a tulelessel
    sns.boxplot(
        data=df, x="class", y="age", hue="survived",
        palette="Set2", ax=axes[0, 1]
    )
    axes[0, 1].set_title("Osztaly vs. Eletkor (szinezve: tuleles)")
    axes[0, 1].set_xlabel("Jegyosztaly")
    axes[0, 1].set_ylabel("Eletkor (ev)")

    # --- 4c. Barplot csoportositva: atlagos viteldij osztalyonkent ---
    sns.barplot(
        data=df, x="class", y="fare", hue="sex",
        palette="muted", errorbar="sd", ax=axes[1, 0]
    )
    axes[1, 0].set_title("Atlagos viteldij osztalyonkent es nementkent")
    axes[1, 0].set_xlabel("Jegyosztaly")
    axes[1, 0].set_ylabel("Atlagos viteldij")

    # --- 4d. Violin plot: eloszlas reszletesebb abrazolasa ---
    sns.violinplot(
        data=df, x="class", y="age", hue="survived",
        split=True, palette="pastel", ax=axes[1, 1]
    )
    axes[1, 1].set_title("Eletkor eloszlasa osztalyonkent (violin plot)")
    axes[1, 1].set_xlabel("Jegyosztaly")
    axes[1, 1].set_ylabel("Eletkor (ev)")

    plt.suptitle("Bivariate elemzes - kulonbozo diagramtipusok", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig("eda_04_bivariate.png", bbox_inches="tight")
    plt.show()


# ============================================================================
# 5. KORRELACIOS MATRIX ES HEATMAP
# ============================================================================
# A korrelacios matrix megmutatja a numerikus valtozok kozotti linearis
# kapcsolat erossegel. A heatmap vizualisan segit azonositani az eros
# korrelaciokat. A tananyagban kiemelt pelda: V24 (target) es V1, V18
# kozotti eros korrelacio (>0.5).
# ============================================================================

def korrelacios_matrix(df: pd.DataFrame) -> None:
    """Korrelacios matrix szamitasa es heatmap abrazolasa."""

    print("\n" + "=" * 70)
    print("5. KORRELACIOS MATRIX ES HEATMAP")
    print("=" * 70)

    # --- Pearson korrelacio (alapertelmezett) ---
    numerikus_df = df.select_dtypes(include=[np.number])
    corr_pearson = numerikus_df.corr(method="pearson")

    print("\n--- Pearson korrelacios matrix ---")
    print(corr_pearson.round(3))

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    # --- 5a. Teljes heatmap ---
    sns.heatmap(
        corr_pearson,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",         # Piros-kek szinpaletta (eros vizualis kontraszt)
        center=0,               # 0 legyen a kozepso ertek
        square=True,
        linewidths=0.5,
        ax=axes[0],
        vmin=-1, vmax=1
    )
    axes[0].set_title("Pearson korrelacios matrix")

    # --- 5b. Spearman korrelacio (rangsorrendi) ---
    # Ordinalis valtozoknal es nem-linearis kapcsolatoknal is mukodik
    corr_spearman = numerikus_df.corr(method="spearman")
    sns.heatmap(
        corr_spearman,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        ax=axes[1],
        vmin=-1, vmax=1
    )
    axes[1].set_title("Spearman korrelacios matrix")

    plt.suptitle("Korrelacios matrixok osszehasonlitasa", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig("eda_05_korrelacio.png", bbox_inches="tight")
    plt.show()

    # --- Eros korrelaciok kiirasa (|r| > 0.5, kizarva az onkorrelaciokat) ---
    print("\n--- Eros korrelaciok (|r| > 0.5) ---")
    eros_korr = []
    for i in range(len(corr_pearson.columns)):
        for j in range(i + 1, len(corr_pearson.columns)):
            r = corr_pearson.iloc[i, j]
            if abs(r) > 0.5:
                eros_korr.append({
                    "Valtozo 1": corr_pearson.columns[i],
                    "Valtozo 2": corr_pearson.columns[j],
                    "Pearson r": round(r, 3)
                })
    if eros_korr:
        print(pd.DataFrame(eros_korr).to_string(index=False))
    else:
        print("Nincs 0.5-nel erosebb korrelacio.")


# ============================================================================
# 6. PAIRPLOT
# ============================================================================
# A pair plot tobb valtozo paronkenti kapcsolatat abrazoja egyetlen
# matrixban. Az atlon hisztogramok (vagy KDE), a matrix tobbi cellajaban
# scatter plotok lathatoak. A tananyagban kiemelt eszkoz a multivariate
# elemzeshez.
# ============================================================================

def pairplot_elemzes(df: pd.DataFrame) -> None:
    """Pairplot keszitese a numerikus valtozokra, szinezve a target szerint."""

    print("\n" + "=" * 70)
    print("6. PAIRPLOT")
    print("=" * 70)

    # A pairplot mindegyik numerikus valtozot parhuzamosan osszehasonlitja.
    # Sok valtozo eseten erdemes szukiteni a kivalasztast.
    valtozok = ["age", "fare", "pclass", "survived"]

    print(f"Valasztott valtozok a pairplothoz: {valtozok}")

    # --- 6a. Alap pairplot ---
    g = sns.pairplot(
        df[valtozok].dropna(),
        hue="survived",
        palette="Set1",
        diag_kind="kde",    # Atlon: KDE (simított hisztogram)
        plot_kws={"alpha": 0.5, "s": 20},
        height=2.5
    )
    g.figure.suptitle("Pairplot - szinezve a tuleles szerint", y=1.02, fontsize=14)
    plt.savefig("eda_06_pairplot.png", bbox_inches="tight")
    plt.show()

    print("Pairplot elkeszult. Az atlon a KDE gorbek lathatoak,")
    print("a tobbi cellaban scatter plotok a valtozok paronkenti kapcsolatarol.")


# ============================================================================
# 7. KATEGORIKUS VALTOZOK ELEMZESE
# ============================================================================
# Kategorikus valtozok osszehasonlitasa:
#   - Countplot: ket kategorikus valtozo gyakorisaganak osszehasonlitasa
#   - Crosstab: kontingencia tabla (kereszttabla)
# A tananyagban peldakent a Titanic osztalyai es a tuleles kapcsolata
# szerepelt.
# ============================================================================

def kategorikus_elemzes(df: pd.DataFrame) -> None:
    """Kategorikus valtozok elemzese: countplot, crosstab."""

    print("\n" + "=" * 70)
    print("7. KATEGORIKUS VALTOZOK ELEMZESE")
    print("=" * 70)

    fig, axes = plt.subplots(2, 2, figsize=(14, 11))

    # --- 7a. Countplot: osztaly es tuleles ---
    # A tananyag kiemelt peldaja: harom osztaly, szinezve a tulelessel
    sns.countplot(
        data=df, x="class", hue="survived",
        palette="Set2", ax=axes[0, 0]
    )
    axes[0, 0].set_title("Tuleles osztalyonkent (countplot)")
    axes[0, 0].set_xlabel("Jegyosztaly")
    axes[0, 0].set_ylabel("Darabszam")

    # --- 7b. Countplot: nem es tuleles ---
    sns.countplot(
        data=df, x="sex", hue="survived",
        palette="pastel", ax=axes[0, 1]
    )
    axes[0, 1].set_title("Tuleles nementkent (countplot)")
    axes[0, 1].set_xlabel("Nem")
    axes[0, 1].set_ylabel("Darabszam")

    # --- 7c. Countplot: beszallasi kikoto ---
    sns.countplot(
        data=df, x="embark_town", hue="class",
        palette="muted", ax=axes[1, 0]
    )
    axes[1, 0].set_title("Jegyosztaly beszallasi kikoto szerint")
    axes[1, 0].set_xlabel("Beszallasi kikoto")
    axes[1, 0].set_ylabel("Darabszam")

    # --- 7d. Heatmap a kereszttablabol ---
    crosstab = pd.crosstab(df["class"], df["survived"], margins=True)
    print("\n--- Kereszttabla: osztaly vs. tuleles ---")
    print(crosstab)

    # Heatmap a kereszttablabol (marginok nelkul)
    crosstab_clean = pd.crosstab(df["class"], df["survived"])
    sns.heatmap(
        crosstab_clean,
        annot=True,
        fmt="d",
        cmap="YlGnBu",
        ax=axes[1, 1]
    )
    axes[1, 1].set_title("Kereszttabla heatmap: osztaly vs. tuleles")
    axes[1, 1].set_xlabel("Tulelte-e?")
    axes[1, 1].set_ylabel("Jegyosztaly")

    plt.suptitle("Kategorikus valtozok elemzese", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig("eda_07_kategorikus.png", bbox_inches="tight")
    plt.show()

    # --- Normalizer/aranyos osszehasonlitas ---
    print("\n--- Tulelesi arany osztalyonkent (%) ---")
    tuleles_arany = pd.crosstab(
        df["class"], df["survived"], normalize="index"
    ) * 100
    tuleles_arany.columns = ["Nem elte tul (%)", "Tulelte (%)"]
    print(tuleles_arany.round(1))


# ============================================================================
# 8. ELOSZLAS VIZSGALAT (ferdeseg, csucossag)
# ============================================================================
# A ferdeseg (skewness) es csucossag (kurtosis) merik, mennyire
# szimmetrikus es csucos egy valtozo eloszlasa.
#   - Ferdeseg = 0: szimmetrikus eloszlas
#   - Ferdeseg > 0: jobbra ferde (hosszu jobb farok)
#   - Ferdeseg < 0: balra ferde (hosszu bal farok)
#   - Kurtosis = 3: normalis eloszlas (mesokurtikus)
#   - Kurtosis > 3: csucsos (leptokurtikus)
#   - Kurtosis < 3: lapos (platikurtikus)
# ============================================================================

def eloszlas_vizsgalat(df: pd.DataFrame) -> None:
    """Eloszlas vizsgalat: ferdeseg (skewness) es csucossag (kurtosis)."""

    print("\n" + "=" * 70)
    print("8. ELOSZLAS VIZSGALAT (ferdeseg, csucossag)")
    print("=" * 70)

    numerikus_oszlopok = df.select_dtypes(include=[np.number]).columns.tolist()

    # --- Ferdeseg es csucossag kiszamitasa ---
    eloszlas_stat = pd.DataFrame({
        "Oszlop": numerikus_oszlopok,
        "Ferdeseg (skew)": [df[col].skew() for col in numerikus_oszlopok],
        "Csucossag (kurt)": [df[col].kurtosis() for col in numerikus_oszlopok],
        "Atlag": [df[col].mean() for col in numerikus_oszlopok],
        "Median": [df[col].median() for col in numerikus_oszlopok],
        "Szoras": [df[col].std() for col in numerikus_oszlopok],
    })
    eloszlas_stat = eloszlas_stat.set_index("Oszlop")

    # --- Ertelmezes ---
    def ertelmezes_ferdeseg(s):
        if abs(s) < 0.5:
            return "kozel szimmetrikus"
        elif s > 0:
            return "jobbra ferde"
        else:
            return "balra ferde"

    def ertelmezes_kurtosis(k):
        if abs(k) < 0.5:
            return "kozel normalis"
        elif k > 0:
            return "csucsosabb a normalisnal"
        else:
            return "laposabb a normalisnal"

    eloszlas_stat["Ferdeseg ertelmezese"] = eloszlas_stat["Ferdeseg (skew)"].apply(
        ertelmezes_ferdeseg
    )
    eloszlas_stat["Csucossag ertelmezese"] = eloszlas_stat["Csucossag (kurt)"].apply(
        ertelmezes_kurtosis
    )

    print("\n--- Eloszlas statisztikak ---")
    print(eloszlas_stat.round(3).to_string())

    # --- Vizualizacio: hisztogram + QQ-plot a legferdebb valtozohoz ---
    # Kivalasztjuk a legferdebb valtozot (abszolut ertek alapjan)
    legferdebb = eloszlas_stat["Ferdeseg (skew)"].abs().idxmax()
    print(f"\nLegferdebb valtozo: {legferdebb} "
          f"(skew = {eloszlas_stat.loc[legferdebb, 'Ferdeseg (skew)']:.3f})")

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Eredeti eloszlas
    sns.histplot(df[legferdebb].dropna(), kde=True, ax=axes[0],
                 color="coral", edgecolor="black")
    axes[0].axvline(df[legferdebb].mean(), color="red", linestyle="--",
                    label=f"Atlag: {df[legferdebb].mean():.1f}")
    axes[0].axvline(df[legferdebb].median(), color="green", linestyle="--",
                    label=f"Median: {df[legferdebb].median():.1f}")
    axes[0].legend()
    axes[0].set_title(f"{legferdebb} - eredeti eloszlas\n"
                      f"(skew={df[legferdebb].skew():.2f}, "
                      f"kurt={df[legferdebb].kurtosis():.2f})")

    # Log-transzformalt eloszlas (ha minden ertek pozitiv)
    adat_tiszta = df[legferdebb].dropna()
    if (adat_tiszta > 0).all():
        log_adat = np.log1p(adat_tiszta)
        sns.histplot(log_adat, kde=True, ax=axes[1],
                     color="steelblue", edgecolor="black")
        axes[1].set_title(f"{legferdebb} - log1p transzformacio\n"
                          f"(skew={log_adat.skew():.2f}, "
                          f"kurt={log_adat.kurtosis():.2f})")
        axes[1].set_xlabel(f"log1p({legferdebb})")
    else:
        axes[1].text(0.5, 0.5, "Log-transzformacio nem lehetseges\n(negativ ertekek)",
                     ha="center", va="center", fontsize=12)
        axes[1].set_title("Log-transzformacio")

    # QQ-plot: normalitas vizsgalat
    adat_qq = df[legferdebb].dropna()
    stats.probplot(adat_qq, dist="norm", plot=axes[2])
    axes[2].set_title(f"{legferdebb} - QQ-plot (normalitas vizsgalat)")

    plt.suptitle("Eloszlas vizsgalat es transzformacio", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig("eda_08_eloszlas.png", bbox_inches="tight")
    plt.show()


# ============================================================================
# FO PROGRAM
# ============================================================================

def main():
    """
    Az EDA teljes folyamatanak bemutatasa a Titanic adathalmazon.

    A Titanic dataset a seaborn konyvtar beepitett peldaadathalmaza.
    Oszlopok:
      - survived: tulelte-e (0/1)
      - pclass: jegyosztaly (1/2/3)
      - sex: nem (male/female)
      - age: eletkor
      - sibsp: testverek/hazastars szama a hajon
      - parch: szulok/gyermekek szama a hajon
      - fare: viteldij
      - embarked: beszallasi kikoto (C/Q/S)
      - class: jegyosztaly szovegesen
      - who: ferfi/no/gyermek
      - adult_male: felnott ferfi-e
      - deck: kabinfedezet
      - embark_town: beszallasi kikoto szovegesen
      - alive: tulelte-e szovegesen
      - alone: egyedul utazott-e
    """

    print("=" * 70)
    print("EXPLORATORY DATA ANALYSIS (EDA) - FELDERITO ADATELEMZES")
    print("Adathalmaz: Titanic (seaborn)")
    print("=" * 70)

    # --- Adatok betoltese ---
    df = sns.load_dataset("titanic")
    print(f"\nAdathalmaz sikeresen betoltve: {df.shape[0]} sor, {df.shape[1]} oszlop")

    # --- Az EDA 8 lepese ---
    adat_attekintes(df)
    hianyzo_ertekek_elemzese(df)
    univariate_elemzes(df)
    bivariate_elemzes(df)
    korrelacios_matrix(df)
    pairplot_elemzes(df)
    kategorikus_elemzes(df)
    eloszlas_vizsgalat(df)

    # --- Osszefoglalas ---
    print("\n" + "=" * 70)
    print("OSSZEFOGLALAS")
    print("=" * 70)
    print("""
Az EDA soran a kovetkezo lepeseket vegeztuk el:

  1. Adat attekintes: info(), describe(), shape, dtypes
  2. Hianyzo ertekek vizualizalasa: heatmap, missingno
  3. Univariate elemzes: hisztogramok, boxplotok, value_counts
  4. Bivariate elemzes: scatter, boxplot csoportositva, violin plot
  5. Korrelacios matrix: Pearson es Spearman heatmap
  6. Pairplot: paronkenti osszefuggesek (KDE + scatter)
  7. Kategorikus valtozok: countplot, crosstab, aranyos osszehasonlitas
  8. Eloszlas vizsgalat: ferdeseg, csucossag, QQ-plot, log-transzformacio

Fontos megjegyzes (a tananyag alapjan):
  - Az automatizalt EDA riportok (YData Profiling, SweetViz) gyors
    attekintest adnak, de NEM helyettesitik a sajat kezzel vegzett elemzest.
  - Mindig kommunikaljunk a domen szakertokkel es az adatgyujto
    mernokokkel az adatok megertese erdekeben.
  - Tartsuk szem elott az uzleti celt: mely oszlopok lehetnek a
    legfontosabbak a jo predikciohoz?
  - Valodi projekten minden fazisra sokkal tobb idot kell szanni.
""")
    print("Abrak mentve: eda_02_*.png, eda_03_*.png, eda_04_*.png, "
          "eda_05_*.png, eda_06_*.png, eda_07_*.png, eda_08_*.png")


if __name__ == "__main__":
    main()
