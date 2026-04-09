"""
Pandas alapok - Cubix EDU ML Engineering kurzus (2. het)
=========================================================

Ez a fajl a Pandas konyvtar alapveto muveleteit mutatja be
a kurzus notebookja es transzkriptjei alapjan.

Forrasok:
  - Cubix_ML_Engineer_Pandas.ipynb
  - 02_08_pandas_intro_transcript_hu.md
  - 02_09_pandas_folytats_transcript_hu.md

Hasznos referencia: https://pandas.pydata.org/Pandas_Cheat_Sheet.pdf
"""

import numpy as np
import pandas as pd

# ============================================================================
# 1. DATAFRAME LETREHOZAS
# ============================================================================

def dataframe_letrehozas():
    """DataFrame-ek letrehozasa kulonbozo modszerekkel."""

    print("=" * 70)
    print("1. DATAFRAME LETREHOZAS")
    print("=" * 70)

    # --- 1a) Series letrehozasa ---
    # A Series egydimenziós adatstruktura (mint egy oszlop)
    s = pd.Series([1, 3, 5])
    print("\n--- Series letrehozasa listabol ---")
    print(s)
    print(f"Tipus: {s.dtype}")

    # --- 1b) DataFrame dictionary-bol ---
    # A kulcsok lesznek az oszlopnevek, a listak azonos hosszuak legyenek
    data_dict = {
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'C': [7, 8, 9]
    }
    df_from_dict = pd.DataFrame(data_dict)
    print("\n--- DataFrame dictionary-bol ---")
    print(df_from_dict)

    # --- 1c) DataFrame dictionary-k listajabol ---
    # Minden dictionary egy sort reprezental, a kulcsok az oszlopnevek
    data_list_of_dicts = [
        {'A': 1, 'B': 4, 'C': 7},
        {'A': 2, 'B': 5, 'C': 8},
        {'A': 3, 'B': 6, 'C': 9}
    ]
    df_from_list_of_dicts = pd.DataFrame(data_list_of_dicts)
    print("\n--- DataFrame dictionary-k listajabol ---")
    print(df_from_list_of_dicts)

    # --- 1d) DataFrame listak listajabol ---
    # Minden belso lista egy sor, az oszlopneveket kulon adjuk meg
    data_list_of_lists = [
        [1, 4, 7],
        [2, 5, 8],
        [3, 6, 9]
    ]
    columns = ['A', 'B', 'C']
    df_from_lists = pd.DataFrame(data_list_of_lists, columns=columns)
    print("\n--- DataFrame listak listajabol ---")
    print(df_from_lists)

    # --- 1e) MultiIndex DataFrame ---
    # Tobbszintu indexeles hierarchikus adatokhoz
    index = pd.MultiIndex.from_tuples(
        [('a', 1), ('a', 2), ('b', 1), ('b', 2)],
        names=['first', 'second']
    )
    df_multi = pd.DataFrame({'A': [1, 2, 3, 4], 'B': [5, 6, 7, 8]}, index=index)
    print("\n--- MultiIndex DataFrame ---")
    print(df_multi)

    # --- 1f) Ures DataFrame ---
    # Hasznos, ha kesobb toltjuk fel adatokkal
    empty_df = pd.DataFrame(columns=['A', 'B', 'C'])
    print("\n--- Ures DataFrame ---")
    print(empty_df)
    print(f"Sorok szama: {len(empty_df)}")


# ============================================================================
# 2. CSV BEOLVASAS ES MENTES
# ============================================================================

def csv_beolvasas_es_mentes():
    """CSV fajlok beolvasasa es mentese, valamint mas formatomok."""

    print("\n" + "=" * 70)
    print("2. CSV BEOLVASAS ES MENTES")
    print("=" * 70)

    # Minta DataFrame letrehozasa
    df = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David', 'Eva'],
        'kor': [25, 32, 28, 45, 37],
        'varos': ['Budapest', 'Debrecen', 'Szeged', 'Pecs', 'Gyor'],
        'fizetes': [450000, 520000, 380000, 610000, 490000]
    })

    # Ideiglenes konyvtar hasznalata a fajlmuveletekhez
    import os
    import tempfile
    tmpdir = tempfile.mkdtemp()

    # CSV mentes
    csv_path = os.path.join(tmpdir, 'minta_adat.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n--- CSV fajl elmentve: {csv_path} ---")

    # CSV beolvasas
    df_beolvasott = pd.read_csv(csv_path, encoding='utf-8-sig')
    print("\n--- CSV beolvasas ---")
    print(df_beolvasott)

    # Pickle (PKL) mentes - a kurzus szerint gyorsabb, mint CSV
    # "A PKL formatomot a Pandas gyorsan tudja olvasni a read_pickle
    # metodussal, igy egyseges es gyors adatkezelest tesz lehetove."
    pkl_path = os.path.join(tmpdir, 'minta_adat.pkl')
    df.to_pickle(pkl_path)
    print(f"\n--- Pickle fajl elmentve: {pkl_path} ---")

    # Pickle beolvasas
    df_pkl = pd.read_pickle(pkl_path)
    print("--- Pickle beolvasas sikeres ---")
    print(f"Sorok: {len(df_pkl)}, Oszlopok: {len(df_pkl.columns)}")

    # Takaritas: toroljuk a letrehozott fajlokat es konyvtarat
    for f in [csv_path, pkl_path]:
        if os.path.exists(f):
            os.remove(f)
    os.rmdir(tmpdir)
    print("\n(Ideiglenes fajlok torolve)")


# ============================================================================
# 3. ALAP MUVELETEK (head, tail, info, describe, shape, dtypes)
# ============================================================================

def alap_muveletek():
    """A DataFrame megismeresere szolgalo alapveto muveletek.

    A kurzusban a Titanic dataset-en mutattuk be ezeket.
    Itt egy sajat minta dataset-et hasznalunk.
    """

    print("\n" + "=" * 70)
    print("3. ALAP MUVELETEK")
    print("=" * 70)

    # Minta dataset letrehozasa (a kurzusban Seaborn Titanic dataset-et
    # hasznaltunk: sns.load_dataset('titanic'))
    np.random.seed(42)
    df = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David', 'Eva',
                'Ferenc', 'Gabi', 'Hajnal', 'Istvan', 'Julia'],
        'kor': [25, 32, 28, 45, 37, 29, 41, 33, 55, 23],
        'osztaly': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'C'],
        'fizetes': [450, 520, 380, 610, 490, 410, 580, 470, 650, 350],
        'aktiv': [True, True, False, True, True, False, True, True, True, False]
    })

    # head() - az elso N sor megjelenitese (alapertelmezett: 5)
    print("\n--- df.head() - Elso 5 sor ---")
    print(df.head())

    # head(3) - elso 3 sor
    print("\n--- df.head(3) - Elso 3 sor ---")
    print(df.head(3))

    # tail() - az utolso N sor megjelenitese (alapertelmezett: 5)
    print("\n--- df.tail() - Utolso 5 sor ---")
    print(df.tail())

    # shape - sorok es oszlopok szama
    print("\n--- df.shape ---")
    print(f"Merete: {df.shape} (sorok: {df.shape[0]}, oszlopok: {df.shape[1]})")

    # dtypes - oszlopok tipusai
    print("\n--- df.dtypes - Oszlop tipusok ---")
    print(df.dtypes)

    # columns - oszlopnevek
    print("\n--- df.columns - Oszlopnevek ---")
    print(df.columns.tolist())

    # info() - atfogo informacio a DataFrame-rol
    print("\n--- df.info() ---")
    df.info()

    # describe() - leiro statisztikak (csak numerikus oszlopokra)
    # "A describe() metodussal sok ertekes informaciot kapunk az oszlopokrol:
    #  nem hianyzo ertekek szama, atlag, szoras, minimum, percentilisek, maximum"
    print("\n--- df.describe() - Leiro statisztikak ---")
    print(df.describe())

    # Egyedi statisztikak
    print("\n--- Egyedi statisztikak (kor oszlop) ---")
    print(f"Median:  {df['kor'].median()}")
    print(f"Atlag:   {df['kor'].mean():.1f}")
    print(f"Minimum: {df['kor'].min()}")
    print(f"Maximum: {df['kor'].max()}")
    print(f"Osszeg:  {df['kor'].sum()}")

    # value_counts - kategoriak elofordulasa
    print("\n--- df['osztaly'].value_counts() ---")
    print(df['osztaly'].value_counts())


# ============================================================================
# 4. INDEXELES ES SZURES (loc, iloc, boolean indexing)
# ============================================================================

def indexeles_es_szures():
    """Adatok kivalasztasa es szurese loc, iloc es boolean indexelessel.

    A kurzusbol: "Az iloc az index alapjan, numerikus pozicio szerint
    valaszt ki sorokat. A loc logikai feltetelekkel is hasznalhato."
    """

    print("\n" + "=" * 70)
    print("4. INDEXELES ES SZURES")
    print("=" * 70)

    df = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David', 'Eva',
                'Ferenc', 'Gabi', 'Hajnal', 'Istvan', 'Julia'],
        'kor': [25, 32, 28, 45, 37, 29, 41, 33, 55, 23],
        'osztaly': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'C'],
        'fizetes': [450, 520, 380, 610, 490, 410, 580, 470, 650, 350]
    })

    # --- iloc: numerikus index (pozicio) szerinti kivalasztas ---
    print("\n--- iloc: elso sor (df.iloc[0]) ---")
    print(df.iloc[0])

    print("\n--- iloc: elso 3 sor (df.iloc[:3]) ---")
    print(df.iloc[:3])

    print("\n--- iloc: 3-5. sor, elso 2 oszlop (df.iloc[3:6, :2]) ---")
    print(df.iloc[3:6, :2])

    # --- loc: cimke/feltetel alapu kivalasztas ---
    # Egyetlen oszlop kivalasztasa
    print("\n--- Egyetlen oszlop: df['nev'] ---")
    print(df['nev'])

    # Tobb oszlop kivalasztasa (dupla szogletes zarojellel)
    print("\n--- Tobb oszlop: df[['nev', 'kor']] ---")
    print(df[['nev', 'kor']])

    # --- Boolean indexeles (szures) ---
    # "A loc szogletes zarojelben logikai feltetelekkel is hasznalhato"
    print("\n--- Szures: kor < 30 ---")
    print(df.loc[df['kor'] < 30])

    # Tobb feltetel (zarojelezve, & es | operatorokkal)
    # "Tobb feltetelt is megadhatunk and vagy or operatorral, zarojelezve"
    print("\n--- Szures: kor < 30 ES osztaly == 'A' ---")
    print(df.loc[(df['kor'] < 30) & (df['osztaly'] == 'A')])

    print("\n--- Szures: fizetes > 500 VAGY kor > 50 ---")
    print(df.loc[(df['fizetes'] > 500) | (df['kor'] > 50)])

    # isin() - tobb ertek kozul barmelyik
    print("\n--- Szures isin()-nel: osztaly 'A' vagy 'C' ---")
    print(df.loc[df['osztaly'].isin(['A', 'C'])])


# ============================================================================
# 5. OSZLOPOK KEZELESE (hozzaadas, torles, atnevezes)
# ============================================================================

def oszlopok_kezelese():
    """Oszlopok hozzaadasa, torlese es atnevezese.

    A kurzusbol: "Uj oszlopokat hozhatunk letre, sorokat vagy oszlopokat
    eldobni drop-pal, atnevezni oszlopokat es indexeket."
    """

    print("\n" + "=" * 70)
    print("5. OSZLOPOK KEZELESE")
    print("=" * 70)

    df = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David'],
        'kor': [25, 32, 28, 45],
        'fizetes': [450, 520, 380, 610]
    })
    print("\n--- Eredeti DataFrame ---")
    print(df)

    # Uj oszlop hozzaadasa
    df['bonus'] = df['fizetes'] * 0.1
    print("\n--- Uj oszlop hozzaadva: bonus = fizetes * 0.1 ---")
    print(df)

    # Szamitott oszlop
    df['osszeg'] = df['fizetes'] + df['bonus']
    print("\n--- Szamitott oszlop: osszeg = fizetes + bonus ---")
    print(df)

    # Oszlop torlese drop()-pal
    # "A drop metodussal teljes oszlopokat vagy sorokat tudunk eltavolitani"
    df_torolt = df.drop(columns=['bonus'])
    print("\n--- Oszlop torolve: drop(columns=['bonus']) ---")
    print(df_torolt)

    # Sor torlese index alapjan
    df_sor_torolt = df.drop(index=[0, 1])
    print("\n--- Sorok torolve: drop(index=[0, 1]) ---")
    print(df_sor_torolt)

    # Oszlop atnevezese
    df_atnevezett = df.rename(columns={'nev': 'munkatars', 'fizetes': 'havi_ber'})
    print("\n--- Oszlopok atnevezve: rename() ---")
    print(df_atnevezett)


# ============================================================================
# 6. GROUPBY MUVELETEK
# ============================================================================

def groupby_muveletek():
    """Adatok csoportositasa es aggregalasa GroupBy-val.

    A kurzusbol: "A GroupBy segitsegevel csoportosithatjuk az adatokat
    egy vagy tobb oszlop alapjan, majd aggregacios fuggvenyeket,
    peldaul atlagot alkalmazhatunk."
    """

    print("\n" + "=" * 70)
    print("6. GROUPBY MUVELETEK")
    print("=" * 70)

    df = pd.DataFrame({
        'osztaly': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B'],
        'nem': ['ferfi', 'no', 'no', 'ferfi', 'ferfi', 'no', 'no', 'ferfi'],
        'kor': [25, 32, 28, 45, 37, 29, 41, 33],
        'fizetes': [450, 520, 380, 610, 490, 410, 580, 470]
    })
    print("\n--- Eredeti DataFrame ---")
    print(df)

    # Csoportositas egy oszlop szerint, atlag szamitas
    print("\n--- GroupBy osztaly szerint, atlag ---")
    print(df.groupby('osztaly').mean(numeric_only=True))

    # Csoportositas tobb oszlop szerint
    print("\n--- GroupBy osztaly es nem szerint, atlag ---")
    print(df.groupby(['osztaly', 'nem']).mean(numeric_only=True))

    # Kulonbozo aggregacios fuggvenyek
    print("\n--- GroupBy + agg(): kulonbozo fuggvenyek oszloponkent ---")
    result = df.groupby('osztaly').agg({
        'kor': ['mean', 'min', 'max'],
        'fizetes': ['mean', 'sum', 'count']
    })
    print(result)

    # Egyedi aggregacio
    print("\n--- GroupBy + size(): csoportmeret ---")
    print(df.groupby('osztaly').size())

    # value_counts - kategoriak elofordulasa
    print("\n--- value_counts: osztaly oszlop ---")
    print(df['osztaly'].value_counts())


# ============================================================================
# 7. MERGE, JOIN, CONCAT
# ============================================================================

def merge_join_concat():
    """DataFrame-ek osszefuzese es egyesitese.

    A kurzusbol: "Ket DataFrame-et osszefuzhetunk concat-tal.
    A concat fuggveny axis parameterevel szabalyozhatjuk, hogy
    sorokat vagy oszlopokat fuzzunk ossze."
    """

    print("\n" + "=" * 70)
    print("7. MERGE, JOIN, CONCAT")
    print("=" * 70)

    # --- Concat: DataFrame-ek osszefuzese ---
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]}, index=[0, 1])
    df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]}, index=[2, 3])

    # Sorok menten (axis=0, alapertelmezett)
    print("\n--- concat sorok menten (axis=0) ---")
    concat_sorok = pd.concat([df1, df2])
    print(concat_sorok)

    # Oszlopok menten (axis=1)
    print("\n--- concat oszlopok menten (axis=1) ---")
    concat_oszlopok = pd.concat([df1, df2], axis=1)
    print(concat_oszlopok)

    # Index ujraszamozasa reset_index()-szel
    # "Uj indexeket letrehozni reset_index segitsegevel"
    print("\n--- concat + reset_index(drop=True) ---")
    concat_reset = pd.concat([df2, df1]).reset_index(drop=True)
    print(concat_reset)

    # --- Merge: SQL-szeru JOIN ---
    # "Kulonbozo adatforrasokat kombinalhatunk merge-rel"
    alkalmazottak = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David'],
        'osztaly_id': [1, 2, 1, 3]
    })
    osztalyok = pd.DataFrame({
        'osztaly_id': [1, 2, 3],
        'osztaly_nev': ['Fejlesztes', 'Marketing', 'HR']
    })

    print("\n--- merge (inner join) ---")
    merged = pd.merge(alkalmazottak, osztalyok, on='osztaly_id')
    print(merged)

    # Left join (minden alkalmazott, meg ha nincs osztaly)
    print("\n--- merge (left join) ---")
    alkalmazottak2 = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David', 'Eva'],
        'osztaly_id': [1, 2, 1, 3, 99]
    })
    merged_left = pd.merge(alkalmazottak2, osztalyok, on='osztaly_id', how='left')
    print(merged_left)

    # --- Join: index alapu osszefuzes ---
    print("\n--- join (index alapu) ---")
    df_bal = pd.DataFrame({'A': [1, 2, 3]}, index=['x', 'y', 'z'])
    df_jobb = pd.DataFrame({'B': [4, 5, 6]}, index=['x', 'y', 'z'])
    joined = df_bal.join(df_jobb)
    print(joined)


# ============================================================================
# 8. APPLY ES LAMBDA
# ============================================================================

def apply_es_lambda():
    """Fuggvenyek alkalmazasa DataFrame sorokra/oszlopokra."""

    print("\n" + "=" * 70)
    print("8. APPLY ES LAMBDA")
    print("=" * 70)

    df = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David'],
        'kor': [25, 32, 28, 45],
        'fizetes': [450, 520, 380, 610]
    })
    print("\n--- Eredeti DataFrame ---")
    print(df)

    # Lambda fuggveny oszlopra
    df['fizetes_eur'] = df['fizetes'].apply(lambda x: round(x / 390, 2))
    print("\n--- Apply + lambda: fizetes EUR-ban (HUF/390) ---")
    print(df)

    # Apply sajat fuggvennyel
    def korcsoport(kor):
        """Korcsoport meghatározasa."""
        if kor < 30:
            return 'fiatal'
        elif kor < 40:
            return 'kozepkoru'
        else:
            return 'idos'

    df['korcsoport'] = df['kor'].apply(korcsoport)
    print("\n--- Apply sajat fuggvennyel: korcsoport ---")
    print(df)

    # Apply teljes sorra (axis=1)
    df['bemutatkozas'] = df.apply(
        lambda row: f"{row['nev']} ({row['kor']} eves, {row['korcsoport']})",
        axis=1
    )
    print("\n--- Apply sorra (axis=1): bemutatkozas ---")
    print(df[['nev', 'bemutatkozas']])

    # Map - ertekek lekepezes szotar alapjan
    osztaly_map = {'fiatal': 'Junior', 'kozepkoru': 'Mid', 'idos': 'Senior'}
    df['szint'] = df['korcsoport'].map(osztaly_map)
    print("\n--- Map: szint leképezes ---")
    print(df[['nev', 'korcsoport', 'szint']])


# ============================================================================
# 9. HIANYZO ERTEKEK (isnull, fillna, dropna)
# ============================================================================

def hianyzo_ertekek():
    """Hianyzo (NaN) ertekek kezelese.

    A kurzusbol: "A hianyzo adatokat kezelhetjuk dropna-val vagy
    fillna-val, utóbbi segitsegevel kitolthetjuk hianyzo ertekeket."
    """

    print("\n" + "=" * 70)
    print("9. HIANYZO ERTEKEK")
    print("=" * 70)

    df = pd.DataFrame({
        'nev': ['Anna', 'Bela', 'Csilla', 'David', 'Eva'],
        'kor': [25, np.nan, 28, 45, np.nan],
        'varos': ['Budapest', 'Debrecen', None, 'Pecs', 'Gyor'],
        'fizetes': [450, 520, np.nan, np.nan, 490]
    })
    print("\n--- DataFrame hianyzo ertekekkel ---")
    print(df)

    # isnull() / isna() - hianyzo ertekek detektalasa
    print("\n--- isnull(): hianyzo ertekek logikai tablaval ---")
    print(df.isnull())

    # Hianyzo ertekek szama oszloponkent
    print("\n--- Hianyzo ertekek szama oszloponkent ---")
    print(df.isnull().sum())

    # dropna() - sorok torlese, ahol barmelyik ertek hianyzo
    print("\n--- dropna(): sorok torlese hianyzo ertekekkel ---")
    print(df.dropna())

    # dropna(subset) - csak bizonyos oszlopok alapjan
    print("\n--- dropna(subset=['kor']): csak kor oszlop alapjan ---")
    print(df.dropna(subset=['kor']))

    # fillna() - hianyzo ertekek kitoltese
    print("\n--- fillna(0): kitoltes nullaval ---")
    print(df.fillna(0))

    # fillna oszloponkent kulonbozo ertekekkel
    print("\n--- fillna oszloponkent ---")
    df_kitoltott = df.fillna({
        'kor': df['kor'].mean(),       # atlaggal
        'varos': 'Ismeretlen',          # szoveggel
        'fizetes': df['fizetes'].median()  # mediannal
    })
    print(df_kitoltott)

    # Forward fill (elozo ertek atmasolasa)
    print("\n--- ffill(): elozo ertek atmasolasa ---")
    print(df.ffill())


# ============================================================================
# 10. RENDEZES (sort_values, sort_index)
# ============================================================================

def rendezes():
    """Adatok rendezese oszlop ertekek vagy index szerint.

    A kurzusbol: "A sort_values metodussal egy adott oszlop szerint
    rendezhetjuk az adatokat, peldaul az eletkor szerint."
    """

    print("\n" + "=" * 70)
    print("10. RENDEZES")
    print("=" * 70)

    df = pd.DataFrame({
        'nev': ['David', 'Anna', 'Eva', 'Bela', 'Csilla'],
        'kor': [45, 25, 37, 32, 28],
        'osztaly': ['C', 'A', 'B', 'B', 'A'],
        'fizetes': [610, 450, 490, 520, 380]
    })
    print("\n--- Eredeti DataFrame ---")
    print(df)

    # Rendezes egy oszlop szerint (novekvo)
    print("\n--- sort_values('kor'): kor szerint novekvo ---")
    print(df.sort_values('kor'))

    # Rendezes egy oszlop szerint (csokkeno)
    print("\n--- sort_values('fizetes', ascending=False): csokkeno ---")
    print(df.sort_values('fizetes', ascending=False))

    # Rendezes tobb oszlop szerint
    print("\n--- sort_values(['osztaly', 'kor']): osztaly, majd kor ---")
    print(df.sort_values(['osztaly', 'kor']))

    # Index szerinti rendezes
    df_kevert = df.iloc[[3, 1, 4, 0, 2]]
    print("\n--- Kevert indexu DataFrame ---")
    print(df_kevert)

    print("\n--- sort_index(): index szerint rendezve ---")
    print(df_kevert.sort_index())

    # Rendezes + reset_index: tiszta uj sorszamok
    print("\n--- sort_values + reset_index(drop=True) ---")
    df_rendezett = df.sort_values('kor').reset_index(drop=True)
    print(df_rendezett)

    # Transpose (sorok es oszlopok csereje)
    # "A transpose metodus felcsereli a sorokat es oszlopokat"
    print("\n--- Transpose (.T): sorok es oszlopok csereje ---")
    print(df.head(3).T)


# ============================================================================
# BONUS: PIVOT TABLE ES MELT
# ============================================================================

def pivot_es_melt():
    """Pivot tablak es melt (szeles/hosszu formatum konverzio).

    A kurzusbol: "A pivot_table segitsegevel indexbe tesszuk az osztalyt
    es nemet, az ertekeket a valtozokhoz rendeljuk, es aggregacios
    fuggvenykent az atlagot hasznaljuk."
    """

    print("\n" + "=" * 70)
    print("BONUS: PIVOT TABLE ES MELT")
    print("=" * 70)

    df = pd.DataFrame({
        'osztaly': ['A', 'B', 'A', 'B', 'A', 'B'],
        'nem': ['ferfi', 'no', 'no', 'ferfi', 'ferfi', 'no'],
        'kor': [25, 32, 28, 45, 37, 29],
        'fizetes': [450, 520, 380, 610, 490, 470]
    })
    print("\n--- Eredeti DataFrame ---")
    print(df)

    # Pivot table
    pivot = df.pivot_table(
        index='osztaly',
        columns='nem',
        values='fizetes',
        aggfunc='mean'
    )
    print("\n--- Pivot table: atlag fizetes osztaly es nem szerint ---")
    print(pivot)

    # Melt (szeles -> hosszu formatum)
    df_subset = df[['osztaly', 'nem', 'kor', 'fizetes']]
    long_df = pd.melt(
        df_subset,
        id_vars=['osztaly', 'nem'],
        value_vars=['kor', 'fizetes']
    )
    print("\n--- Melt: szeles -> hosszu formatum ---")
    print(long_df)


# ============================================================================
# FOPROGRAM
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  PANDAS ALAPOK - Cubix EDU ML Engineering kurzus")
    print("  Osszeallitva a kurzus notebookja es transzkriptjei alapjan")
    print("=" * 70)

    dataframe_letrehozas()          # 1. DataFrame letrehozas
    csv_beolvasas_es_mentes()       # 2. CSV beolvasas es mentes
    alap_muveletek()                # 3. Alap muveletek
    indexeles_es_szures()           # 4. Indexeles es szures
    oszlopok_kezelese()             # 5. Oszlopok kezelese
    groupby_muveletek()             # 6. GroupBy muveletek
    merge_join_concat()             # 7. Merge, Join, Concat
    apply_es_lambda()               # 8. Apply es Lambda
    hianyzo_ertekek()               # 9. Hianyzo ertekek
    rendezes()                      # 10. Rendezes
    pivot_es_melt()                 # Bonus: Pivot es Melt

    print("\n" + "=" * 70)
    print("  Minden pelda sikeresen lefutott!")
    print("  Tovabbi tanulas: https://pandas.pydata.org/Pandas_Cheat_Sheet.pdf")
    print("=" * 70)
