"""
Ajanlorendszerek - Kod Peldak
==============================
12. fejezet: Ajanlorendszerek (Recommender Systems)

Tartalom:
    1. Szintetikus film-ertekeles adat generalasa
    2. Content-based filtering (cosine similarity)
    3. Collaborative filtering - item-item
    4. Collaborative filtering - user-user
    5. Association Rule Learning (support, confidence, lift)
    6. Osszehasonlitas es vizualizacio

Futtatas:
    python ajanlorendszerek.py

Fuggosegek:
    - numpy, pandas, scikit-learn
    - matplotlib (opcionalis, vizualizaciohoz)
"""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity, pairwise_distances

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_ELERHETO = True
except ImportError:
    MATPLOTLIB_ELERHETO = False
    print("[INFO] matplotlib nem elerheto, vizualizacio kimarad.")

# Mufajok es szintetikus filmcimek
MUFAJOK = [
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Documentary", "Drama", "Fantasy", "Horror", "Mystery",
    "Romance", "Sci-Fi", "Thriller", "War", "Western"
]

FILM_CIMEK = [
    "Galactic Warriors (2020)", "Love in Paris (2019)",
    "The Dark Forest (2021)", "Comedy Night Live (2018)",
    "Space Odyssey Returns (2022)", "Mystery at Midnight (2020)",
    "Robot Revolution (2023)", "Romantic Sunset (2021)",
    "Dragon Kingdom (2019)", "Crime in the City (2022)",
    "Laughing Out Loud (2020)", "The Final Frontier (2023)",
    "Horror House (2021)", "War Heroes (2019)",
    "Wild West Story (2022)", "Animated Dreams (2020)",
    "Detective Story (2023)", "Love and Thunder (2022)",
    "Time Travel (2021)", "Funny Business (2023)",
    "Deep Ocean (2020)", "Spy Thriller (2022)",
    "Family Adventure (2019)", "Zombie Apocalypse (2023)",
    "Historical Drama (2021)", "Alien Contact (2022)",
    "Musical Journey (2020)", "Ninja Warriors (2023)",
    "Romantic Comedy (2019)", "The Great Escape (2021)",
    "Cyber Punk (2023)", "Ghost Story (2022)",
    "Treasure Hunt (2020)", "Political Drama (2021)",
    "Superhero Origins (2023)", "Dance Academy (2019)",
    "The Haunting (2022)", "Desert Warriors (2020)",
    "Underwater World (2023)", "Last Stand (2021)",
]


# =============================================================================
# 1. SZINTETIKUS ADAT GENERALAS
# =============================================================================

def film_adatok_generalasa(n_filmek=40, random_state=42):
    """Szintetikus film adatbazis generalasa mufajokkal (1-3 genre/film)."""
    rng = np.random.RandomState(random_state)
    n_filmek = min(n_filmek, len(FILM_CIMEK))
    filmek = []
    for i in range(n_filmek):
        n_genre = rng.randint(1, 4)
        idx = rng.choice(len(MUFAJOK), size=n_genre, replace=False)
        genres = "|".join([MUFAJOK[j] for j in sorted(idx)])
        filmek.append({'movieId': i + 1, 'title': FILM_CIMEK[i], 'genres': genres})
    return pd.DataFrame(filmek)


def ertekeles_adatok_generalasa(movie_df, n_felhasznalok=200,
                                 atlag_per_user=15, random_state=42):
    """Szintetikus ertekelesi adatok: felhasznaloi preferencia-profillal."""
    rng = np.random.RandomState(random_state)
    n_filmek = len(movie_df)
    ertekelesek = []
    for user_id in range(1, n_felhasznalok + 1):
        n_ratings = max(3, min(rng.poisson(atlag_per_user), n_filmek))
        film_idx = rng.choice(n_filmek, size=n_ratings, replace=False)
        # Felhasznaloi preferencia: 2-3 kedvelt mufaj
        kedvelt = rng.choice(len(MUFAJOK), size=rng.randint(2, 4), replace=False)
        for fi in film_idx:
            film = movie_df.iloc[fi]
            base = rng.uniform(2.5, 4.0)
            # Bonus kedvelt mufajokra
            for m in film['genres'].split('|'):
                if m in [MUFAJOK[k] for k in kedvelt]:
                    base += rng.uniform(0.3, 0.8)
            rating = np.clip(round((base + rng.normal(0, 0.3)) * 2) / 2, 0.5, 5.0)
            ertekelesek.append({'userId': user_id, 'movieId': film['movieId'],
                                'rating': rating})
    return pd.DataFrame(ertekelesek)


def adat_elokeszites(movie_df, rating_df, min_ertekelesek=10):
    """Osszefuzes, szures, pivot table-ok elkeszitese."""
    movies_rating_data = pd.merge(movie_df, rating_df, on='movieId')
    stats = movies_rating_data.groupby('title').agg(
        rating_mean=('rating', 'mean'), ratings_count=('rating', 'count')
    ).reset_index()
    high = stats[stats['ratings_count'] >= min_ertekelesek]
    high_mr = pd.merge(movies_rating_data, high[['title']], on='title')
    # Pivot: filmcim oszlopokkal (content/item-CF-hez)
    pivot_title = high_mr.pivot_table(
        columns='title', index='userId', values='rating').fillna(0)
    # Pivot: movieId oszlopokkal (user-CF-hez)
    pivot_id = high_mr.pivot_table(
        columns='movieId', index='userId', values='rating').fillna(0)
    # Sparsity kiszamitasa
    osszes = pivot_title.shape[0] * pivot_title.shape[1]
    kitoltott = (pivot_title > 0).sum().sum()
    print(f"  Filmek: {movie_df.shape[0]}, Ertekelesek: {rating_df.shape[0]}")
    print(f"  Popularis ({min_ertekelesek}+): {len(high)}")
    print(f"  Pivot: {pivot_title.shape}, Sparsity: {1 - kitoltott/osszes:.1%}")
    return movies_rating_data, high_mr, pivot_title, pivot_id


# =============================================================================
# 2. CONTENT-BASED FILTERING
# =============================================================================

def content_based_matrix(movie_df):
    """Genre-alapu cosine similarity matrix szamitas CountVectorizer-rel."""
    vec = CountVectorizer(tokenizer=lambda x: x.split('|'))
    genre_mat = vec.fit_transform(movie_df['genres'])
    print(f"  Genre matrix: {genre_mat.shape}, "
          f"mufajok: {list(vec.get_feature_names_out())}")
    return cosine_similarity(genre_mat, genre_mat)


def content_ajanlas(title, movie_df, cos_sim, n=5):
    """Content-based ajanlas: leghasonlobb filmek genre alapjan."""
    idx_list = movie_df.index[movie_df['title'] == title].tolist()
    if not idx_list:
        print(f"  [HIBA] Film nem talalhato: '{title}'")
        return pd.DataFrame()
    idx = idx_list[0]
    scores = sorted(enumerate(cos_sim[idx]), key=lambda x: x[1], reverse=True)
    scores = scores[1:n + 1]
    return pd.DataFrame([{
        'title': movie_df.iloc[i]['title'],
        'genres': movie_df.iloc[i]['genres'],
        'similarity': round(s, 4)
    } for i, s in scores])


def content_based_demo(movie_df):
    """Content-based filtering bemutatasa."""
    print("\n" + "=" * 65)
    print("2. CONTENT-BASED FILTERING")
    print("=" * 65)
    cos_sim = content_based_matrix(movie_df)
    for film in [FILM_CIMEK[0], FILM_CIMEK[1], FILM_CIMEK[9]]:
        row = movie_df[movie_df['title'] == film]
        genres = row.iloc[0]['genres'] if not row.empty else "?"
        print(f"\n  '{film}' ({genres}):")
        for _, r in content_ajanlas(film, movie_df, cos_sim, n=5).iterrows():
            print(f"    --> {r['title']:<35} sim={r['similarity']:.3f}  "
                  f"({r['genres']})")
    return cos_sim


# =============================================================================
# 3. COLLABORATIVE FILTERING - ITEM-ITEM
# =============================================================================

def item_ajanlas(movie_name, pivot, n=5):
    """Item-based CF: corrwith() korrelacio alapu filmajanlás."""
    if movie_name not in pivot.columns:
        print(f"  [HIBA] '{movie_name}' nem a pivot-ban")
        return pd.Series(dtype=float)
    corr = pivot.corrwith(pivot[movie_name]).dropna()
    return corr.sort_values(ascending=False).iloc[1:n + 1]


def item_based_demo(movie_df, pivot):
    """Item-based collaborative filtering bemutatasa."""
    print("\n" + "=" * 65)
    print("3. COLLABORATIVE FILTERING - ITEM-ITEM")
    print("=" * 65)
    print(f"  Pivot: {pivot.shape}")
    for film in pivot.columns[:3]:
        row = movie_df[movie_df['title'] == film]
        genres = row.iloc[0]['genres'] if not row.empty else "?"
        print(f"\n  '{film}' ({genres}):")
        for cim, corr in item_ajanlas(film, pivot, n=5).items():
            fr = movie_df[movie_df['title'] == cim]
            g = fr.iloc[0]['genres'] if not fr.empty else "?"
            print(f"    --> {cim:<35} corr={corr:+.3f}  ({g})")


# =============================================================================
# 4. COLLABORATIVE FILTERING - USER-USER
# =============================================================================

def user_sim_matrix(user_pivot):
    """Felhasznalok kozotti cosine similarity matrix."""
    dist = pairwise_distances(user_pivot, metric='cosine')
    sim = 1 - dist
    return pd.DataFrame(sim, index=user_pivot.index, columns=user_pivot.index)


def user_ajanlas(user_id, user_pivot, sim_df, movie_df,
                  n_ajanlas=5, n_similar=10):
    """User-based CF: hasonlo felhasznalok altal kedvelt, nem latott filmek."""
    if user_id not in sim_df.index:
        print(f"  [HIBA] userId={user_id} nem talalhato")
        return pd.DataFrame()
    # Hasonlo felhasznalok (sajat magat kihagyva)
    similar = sim_df[user_id].sort_values(ascending=False)[1:n_similar + 1]
    # Median rating az o ertekeleseikbol
    med = user_pivot.loc[similar.index].median().sort_values(ascending=False)
    # Mar latott filmek kiszurese
    watched = user_pivot.loc[user_id]
    watched_ids = watched[watched > 0].index
    unwatched = med[~med.index.isin(watched_ids)]
    unwatched = unwatched[unwatched > 0].head(n_ajanlas)
    # Eredmeny
    result = []
    for mid, rating in unwatched.items():
        fr = movie_df[movie_df['movieId'] == mid]
        cim = fr.iloc[0]['title'] if not fr.empty else f"id={mid}"
        g = fr.iloc[0]['genres'] if not fr.empty else "?"
        result.append({'movieId': mid, 'title': cim, 'genres': g,
                       'median_rating': rating})
    return pd.DataFrame(result)


def user_based_demo(movie_df, user_pivot):
    """User-based collaborative filtering bemutatasa."""
    print("\n" + "=" * 65)
    print("4. COLLABORATIVE FILTERING - USER-USER")
    print("=" * 65)
    sim_df = user_sim_matrix(user_pivot)
    print(f"  Similarity matrix: {sim_df.shape}")
    for uid in [1, 5, 10]:
        if uid not in user_pivot.index:
            continue
        n_w = (user_pivot.loc[uid] > 0).sum()
        print(f"\n  userId={uid} ({n_w} film latva):")
        top3 = sim_df[uid].sort_values(ascending=False)[1:4]
        for sid, sv in top3.items():
            print(f"    hasonlo: userId={sid}, sim={sv:.3f}")
        recs = user_ajanlas(uid, user_pivot, sim_df, movie_df, n_ajanlas=5)
        if not recs.empty:
            for _, r in recs.iterrows():
                print(f"    --> {r['title']:<35} med={r['median_rating']:.1f}")
    return sim_df


# =============================================================================
# 5. ASSOCIATION RULE LEARNING
# =============================================================================

def support_szamitas(df):
    """Support: termek elofordulasi gyakorisaga."""
    return df.sum() / len(df)


def confidence_szamitas(df, felt_termek):
    """Confidence: P(B | A) - felteteles vasarlasi valoszinuseg."""
    felt = df[df[felt_termek] == 1]
    if len(felt) == 0:
        return pd.Series(0, index=df.columns)
    return felt.sum() / len(felt)


def lift_szamitas(confidence, support):
    """Lift = Confidence / Support. Lift>1: pozitiv asszociacio."""
    return confidence / support.replace(0, np.nan)


def osszes_szabaly(df, min_support=0.1, min_confidence=0.3, min_lift=1.0):
    """Az osszes kuszobnek megfelelo asszociacios szabaly kigyujtese."""
    support = support_szamitas(df)
    szabalyok = []
    for felt in df.columns:
        if support[felt] < min_support:
            continue
        conf = confidence_szamitas(df, felt)
        lift = lift_szamitas(conf, support)
        for cel in df.columns:
            if cel == felt:
                continue
            c, l = conf[cel], lift[cel]
            if c >= min_confidence and l >= min_lift and not np.isnan(l):
                szabalyok.append({
                    'feltetel': felt, 'kovetkezmeny': cel,
                    'support_felt': round(support[felt], 3),
                    'confidence': round(c, 3), 'lift': round(l, 3)
                })
    result = pd.DataFrame(szabalyok)
    if not result.empty:
        result = result.sort_values('lift', ascending=False).reset_index(drop=True)
    return result


def tranzakcios_adat_generalasa(n=100, random_state=42):
    """Szintetikus kosarelemzesi adat beepitett korrelaciokal."""
    rng = np.random.RandomState(random_state)
    alap = {'citrom': 0.45, 'kenyer': 0.50, 'tej': 0.40, 'tejfol': 0.20,
            'tea': 0.35, 'vaj': 0.30, 'tojas': 0.35, 'rizs': 0.25}
    tranzakciok = []
    for _ in range(n):
        t = {k: int(rng.random() < v) for k, v in alap.items()}
        # Beepitett korrelaciok
        if t['citrom'] == 1 and rng.random() < 0.75:
            t['tea'] = 1
        if t['kenyer'] == 1 and rng.random() < 0.65:
            t['vaj'] = 1
        if t['tej'] == 1 and rng.random() < 0.50:
            t['tojas'] = 1
        tranzakciok.append(t)
    return pd.DataFrame(tranzakciok)


def association_demo():
    """Association Rule Learning bemutatasa."""
    print("\n" + "=" * 65)
    print("5. ASSOCIATION RULE LEARNING")
    print("=" * 65)

    # --- 5a. Kezi pelda (tananyagbol) ---
    print("\n--- 5a. Kezi pelda (10 tranzakcio, tananyagbol) ---")
    df_kezi = pd.DataFrame({
        'lemon':      [1, 0, 1, 1, 0, 1, 1, 0, 1, 0],
        'bread':      [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
        'milk':       [0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
        'sour cream': [0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
        'tea':        [1, 0, 1, 0, 0, 1, 1, 0, 1, 0]
    })
    print("\nTranzakcios matrix:")
    print(df_kezi.to_string())

    sup = support_szamitas(df_kezi)
    conf = confidence_szamitas(df_kezi, 'lemon')
    lft = lift_szamitas(conf, sup)

    print("\nSupport:")
    for t, s in sup.items():
        print(f"  {t:<12} = {s:.2f}")
    print("\nConfidence (lemon --> ?):")
    for t, c in conf.items():
        if t != 'lemon':
            print(f"  lemon --> {t:<12} = {c:.3f}")
    print("\nLift (lemon --> ?):")
    for t, l in lft.items():
        if t != 'lemon':
            j = "pozitiv" if l > 1 else ("negativ" if l < 1 else "fuggetlen")
            print(f"  lemon --> {t:<12} = {l:.3f}  ({j})")

    # --- 5b. Nagyobb szintetikus adat ---
    print("\n--- 5b. Szintetikus kosarelemzes (100 tranzakcio) ---")
    df_nagy = tranzakcios_adat_generalasa(n=100, random_state=42)
    print(f"  Tranzakciok: {len(df_nagy)}, Termekek: {len(df_nagy.columns)}")

    print("\nOsszes eros szabaly (lift>1.0, confidence>0.3):")
    rules = osszes_szabaly(df_nagy, min_support=0.1,
                            min_confidence=0.3, min_lift=1.0)
    if not rules.empty:
        print(rules.to_string(index=False))
    else:
        print("  Nincs megfelelo szabaly.")
    return df_nagy


# =============================================================================
# 6. COSINE SIMILARITY RESZLETES DEMO
# =============================================================================

def cosine_sim_kezzel(a, b):
    """Cosine similarity kezi szamitasa: cos(theta) = A.B / (||A||*||B||)"""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return np.dot(a, b) / (na * nb)


def cosine_demo():
    """Cosine similarity reszletes bemutatasa kezi szamitassal."""
    print("\n" + "=" * 65)
    print("6. COSINE SIMILARITY - RESZLETES MATEMATIKA")
    print("=" * 65)

    # Genre vektorok: [Action, Comedy, Drama, Sci-Fi, Thriller]
    print("\nMufajok: [Action, Comedy, Drama, Sci-Fi, Thriller]")
    x = [1, 0, 0, 1, 1]  # Action|Sci-Fi|Thriller
    y = [1, 1, 0, 1, 0]  # Action|Comedy|Sci-Fi
    z = [0, 0, 1, 0, 0]  # Drama

    print(f"  Film X (Action|Sci-Fi|Thriller): {x}")
    print(f"  Film Y (Action|Comedy|Sci-Fi):   {y}")
    print(f"  Film Z (Drama):                  {z}")

    # Kezi levezetés X vs Y
    dot = sum(a * b for a, b in zip(x, y, strict=False))
    nx = np.sqrt(sum(a**2 for a in x))
    ny = np.sqrt(sum(b**2 for b in y))
    print("\n  X vs Y levezetés:")
    print(f"    Dot product: {' + '.join(f'{a}*{b}' for a, b in zip(x, y, strict=False))} = {dot}")
    print(f"    ||X|| = sqrt({sum(a**2 for a in x)}) = {nx:.3f}")
    print(f"    ||Y|| = sqrt({sum(b**2 for b in y)}) = {ny:.3f}")
    print(f"    cos = {dot}/({nx:.3f}*{ny:.3f}) = {dot/(nx*ny):.4f}")

    print(f"\n  cos(X,Y) = {cosine_sim_kezzel(x, y):.4f}  (kozepes, 2 kozos)")
    print(f"  cos(X,Z) = {cosine_sim_kezzel(x, z):.4f}  (nincs kozos)")
    print(f"  cos(Y,Z) = {cosine_sim_kezzel(y, z):.4f}  (nincs kozos)")

    # sklearn ellenorzes
    mat = np.array([x, y, z])
    sk = cosine_similarity(mat)
    print(f"\n  sklearn ellenorzes: cos(X,Y)={sk[0,1]:.4f}, "
          f"cos(X,Z)={sk[0,2]:.4f}, cos(Y,Z)={sk[1,2]:.4f}")

    # Felhasznaloi ertekelesi vektorok
    print("\n  Felhasznalo ertekelesi vektorok:")
    ua = [5, 4, 0, 0, 3, 0, 5]
    ub = [5, 5, 0, 0, 4, 0, 4]
    uc = [0, 0, 5, 4, 0, 5, 0]
    print(f"    A: {ua}  B: {ub}  C: {uc}")
    print(f"    cos(A,B) = {cosine_sim_kezzel(ua, ub):.4f}  (hasonlo izles)")
    print(f"    cos(A,C) = {cosine_sim_kezzel(ua, uc):.4f}  (eltero izles)")


# =============================================================================
# 7. VIZUALIZACIO
# =============================================================================

def vizualizacio(movie_df, cos_sim, df_trx):
    """Heatmap + association rule bar chart."""
    if not MATPLOTLIB_ELERHETO:
        print("\n[INFO] Vizualizacio kimarad (matplotlib nem elerheto).")
        return
    print("\n" + "=" * 65)
    print("7. VIZUALIZACIO")
    print("=" * 65)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 7a. Cosine similarity heatmap
    n = min(15, len(movie_df))
    sub = cos_sim[:n, :n]
    labels = [t[:18] + ".." if len(t) > 18 else t
              for t in movie_df['title'].iloc[:n]]
    im = axes[0].imshow(sub, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)
    axes[0].set_xticks(range(n))
    axes[0].set_yticks(range(n))
    axes[0].set_xticklabels(labels, rotation=90, fontsize=7)
    axes[0].set_yticklabels(labels, fontsize=7)
    axes[0].set_title("Content-Based Cosine Similarity (Genre)")
    plt.colorbar(im, ax=axes[0], fraction=0.046)

    # 7b. Association rules bar chart
    sup = support_szamitas(df_trx)
    conf = confidence_szamitas(df_trx, 'citrom')
    lft = lift_szamitas(conf, sup)
    terms = [t for t in df_trx.columns if t != 'citrom']
    x_pos = np.arange(len(terms))
    w = 0.25
    axes[1].bar(x_pos - w, [sup[t] for t in terms], w,
                label='Support', color='steelblue')
    axes[1].bar(x_pos, [conf[t] for t in terms], w,
                label='Confidence', color='darkorange')
    axes[1].bar(x_pos + w,
                [lft[t] if not np.isnan(lft[t]) else 0 for t in terms],
                w, label='Lift', color='forestgreen')
    axes[1].set_xticks(x_pos)
    axes[1].set_xticklabels(terms, rotation=45, ha='right')
    axes[1].set_title("Association Rules: citrom --> ?")
    axes[1].axhline(y=1.0, color='red', ls='--', alpha=0.5,
                     label='Lift=1 (fuggetlen)')
    axes[1].legend(fontsize=8)

    plt.tight_layout()
    plt.savefig("ajanlorendszerek_viz.png", dpi=120, bbox_inches='tight')
    print("  Mentve: ajanlorendszerek_viz.png")
    plt.show()


# =============================================================================
# 8. MODSZEREK OSSZEHASONLITASA
# =============================================================================

def modszerek_osszehasonlitasa():
    """Ajanlasi modszerek osszehasonlito tablazata."""
    print("\n" + "=" * 65)
    print("8. MODSZEREK OSSZEHASONLITASA")
    print("=" * 65)
    df = pd.DataFrame({
        'Modszer': ['Content-Based', 'Item-Based CF', 'User-Based CF',
                    'Assoc. Rules', 'Supervised'],
        'Bemenet': ['Termek attr.', 'Rating matrix', 'Rating matrix',
                    'Tranzakcio', 'Feature+label'],
        'Hasonlosag': ['Cosine sim.', 'Pearson corr.', 'Cosine sim.',
                       'Sup/Conf/Lift', 'Nem hasonlosag'],
        'Cold Start (user)': ['Nem', 'Nem', 'Nem', 'Igen', 'Igen'],
        'Cold Start (item)': ['Igen', 'Nem', 'Nem', 'Igen', 'Igen'],
        'Skalazhatosag': ['Jo', 'Kozepes', 'Gyenge', 'Gyenge', 'Jo'],
    })
    print("\n" + df.to_string(index=False))


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 65)
    print("AJANLORENDSZEREK - TELJES DEMO PIPELINE")
    print("=" * 65)

    # 1. Adat generalas
    print("\n" + "=" * 65)
    print("1. SZINTETIKUS ADAT GENERALAS")
    print("=" * 65)
    movie_df = film_adatok_generalasa(n_filmek=40)
    print(f"  {len(movie_df)} film generalva. Pelda:")
    for _, r in movie_df.head(3).iterrows():
        print(f"    [{r['movieId']:2d}] {r['title']:<30} {r['genres']}")

    rating_df = ertekeles_adatok_generalasa(movie_df, n_felhasznalok=200)
    print(f"  {len(rating_df)} ertekelest ({rating_df['userId'].nunique()} user)")
    print(f"  Rating: min={rating_df['rating'].min()}, "
          f"max={rating_df['rating'].max()}, "
          f"atlag={rating_df['rating'].mean():.2f}")

    print("\nAdat elokeszites:")
    _, _, pivot_title, pivot_id = adat_elokeszites(
        movie_df, rating_df, min_ertekelesek=10)

    # 2-8. Demo fuggvenyek futtatasa
    cos_sim = content_based_demo(movie_df)
    item_based_demo(movie_df, pivot_title)
    user_based_demo(movie_df, pivot_id)
    df_trx = association_demo()
    cosine_demo()
    vizualizacio(movie_df, cos_sim, df_trx)
    modszerek_osszehasonlitasa()

    print("\n" + "=" * 65)
    print("PIPELINE BEFEJEZVE")
    print("=" * 65)
