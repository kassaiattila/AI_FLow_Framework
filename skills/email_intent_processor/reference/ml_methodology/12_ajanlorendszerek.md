# Ajanlorendszerek (Recommender Systems)

## Gyors Attekintes

> Az ajanlorendszerek (**recommender systems**) olyan gepi tanulasi rendszerek, amelyek felhasznaloi preferencia-adatok es termektulajdonsagok alapjan szemelyre szabott javaslatokat generalnak. A harom fo megkozelites -- **content-based filtering**, **collaborative filtering** es **association rule learning** -- egymast kiegeszitve kepes megoldani az ajanlas kulonbozo kihivasait. A modern ipari rendszerek (Netflix, Amazon, Spotify, LinkedIn) jellemzoen **hibrid** architekturakat alkalmaznak, amelyek tobb modszert kombinalkak, es felügyelt tanulasi modelleket is beepitenek a vegso rangsorolasba.

---

## Kulcsfogalmak

| Fogalom | Jelentes |
|---------|---------|
| **Ajanlórendszer** (**Recommender System**) | Rendszer, amely felhasznaloi preferenciák es termektulajdonsagok alapjan javaslatokat general |
| **Content-Based Filtering** | Tartalomalapu szures: termekek tulajdonsagai (genre, leiras, kategoria) alapjan ajanlunk hasonlo termekeket |
| **Collaborative Filtering** | Egyuttmukodesi szures: felhasznaloi viselkedesmintak (ertekelesek, kattintasok) alapjan ajanlunk |
| **User-Based CF** | Hasonlo felhasznalokat keres, es az o kedvelt termekeiket ajanlja |
| **Item-Based CF** | Hasonlo termekeket keres egy adott termekhez a felhasznaloi ertekelesmintak alapjan |
| **Cosine Similarity** | Koszinusz-hasonlosag: ket vektor kozotti szog koszinusza, ertek 0 es 1 kozott (pozitiv ertekek eseten) |
| **CountVectorizer** | Szoveg/kategoria vektorizalo, amely a megjelent elemek szamat szamolja |
| **Pivot Table** | Felhasznalo-termek matrix, ahol a cellak az ertekeleseket tartalmazzak |
| **Korrelaciol matrix** | Termekek kozotti linearis osszefuggeseket taro matrix (corrwith) |
| **Cold Start** | Uj felhasznalonal vagy uj termeknel nincs eleg adat az ajanlashoz |
| **Sparsity** | A felhasznalo-termek matrix ritka: a legtobb cella ures (a felhasznalok csak toredeket ertekelik) |
| **Association Rule** | Asszociacios szabaly: termekek egyuttes elofordulasanak mintazata tranzakciokban |
| **Support** | Egy termek vagy termekhalmaznak elofordulasi gyakorisaga az osszes tranzakciohoz kepest |
| **Confidence** | Felteteles valoszinuseg: ha A-t megvette, mekkora esellyel veszi meg B-t is |
| **Lift** | A confidence es a support hanyadosa: mutatja, mennyire erosebb az asszociacio a veletlennel |
| **Hybrid rendszer** | Tobb ajanlasi modszert kombinal (content + collaborative + supervised) |
| **Matching problema** | Annak a feladatnak a meghataroza, ahol felhasznalokat es termekeket kell osszeparositani |

---

## Ajanlórendszerek Üzleti Erteke

Az ajanlórendszerek az egyik legnagyobb uzleti hatasu gepi tanulasi alkalmazasok. A McKinsey becslese szerint az Amazon forgalmanak kb. 35%-a, a Netflix megtekintett tartalmainak 80%-a ajanlasbol szarmazik.

### Fo Alkalmazasi Teruletek

#### E-commerce (pl. Amazon, eBay)

A vasarloi elozmenyek, bongeszesi szokasok es hasonlo felhasznalok viselkedese alapjan termekajanlasokat generalnak. A "Customers who bought this also bought..." es "Recommended for you" szekciok collaborative es content-based filteringet egyarant alkalmaznak.

```
Felhasznaloi elozmenyek --> CF + Content-Based --> Szemelyre szabott termekajanlas
```

#### Streaming (pl. Netflix, Spotify)

A Netflix a vilagszinten legfejlettebb ajanlórendszert uzemelteti. A felhasznalo megtekintett tartalmai, ertekelesei, bongeszesi szokasai es a tartalmak metaadatai (mufaj, rendezo, szineszek) alapjan ajanl. A Spotify a zenei preferenciakat collaborative filtering es audio feature analysis kombinaval kezeli.

#### Munkaero-kozvetites (pl. LinkedIn)

A LinkedIn ajanlórendszere a **matching problema** klasszikus peldaja: felhasznalokat es allasajanlatok/kapcsolatokat kell osszeparositani. A feature-ok lehetnek:
- **Job title** (pozicio megnevezese)
- **Skills** (kepessegek, technologiak)
- **Company** (vallalat, iparag)
- **Location** (folrajzi hely)
- **Seniority** (tapasztalati szint)

#### Kozossegi media (pl. Facebook, TikTok, Instagram)

A feed ranking es tartalomajanlat kulonbozo jelekre (engagement, megosztasok, bongeszesi ido, hasonlo felhasznalok) tamaszkodik.

### Miert fontos az ajanlórendszer?

| Szempont | Hatas |
|----------|-------|
| Felhasznaloi elmeny | Szemelyre szabott tartalom, kevesebb "keresesi ido" |
| Konverzio | Magasabb vasarlasi/megtekintest arany |
| Retention | A felhasznalo visszater, mert relevans tartalmat kap |
| Revenue | Kozvetlen bevetelnovekedes a celzott ajanlasoknak koszonhetoen |
| Discovery | A felhasznalo talal termekeket, amiket magatol nem keresett volna |

---

## Content-Based Filtering

![Ajanlorendszerek: Collaborative Filtering vs Content-Based Filtering](_kepek_cleaned/02_tasks_of_ml/slide_16.png)

*1. abra: Ajanlorendszerek ket fo megkozelitese -- Content-Based Filtering (item tulajdonsagok alapjan) vs Collaborative Filtering (felhasznaloi viselkedes alapjan).*

A **content-based filtering** (tartalomalapu szures) termektulajdonsagok (attributumok) alapjan ajanl hasonlo termekeket. Nem fugg mas felhasznalok viselkedetol -- kizarolag a termek jellemzoi szamitanak.

### Mukodesi elv

1. Minden termekhez letrehozunk egy **feature vektort** a tulajdonsagai alapjan
2. Kiszamitjuk a termekek kozotti **hasonlosagot** (jellemzoen cosine similarity)
3. Egy adott termekhez a leghasonlobb termekeket ajanlljuk

### Pelda: filmek mufaj alapu ajanlasa

Ha egy felhasznalo megnez egy sci-fi/thriller filmet, a rendszer keresendo a tobbi filmet, amelynek genre-osszetetele a leghasonlobb.

```
Film A: Sci-Fi|Thriller|Action     -->  vektor: [0, 1, 0, 1, 0, 1, 0]
Film B: Sci-Fi|Thriller|Drama      -->  vektor: [0, 1, 0, 0, 1, 1, 0]
Film C: Romance|Comedy             -->  vektor: [1, 0, 1, 0, 0, 0, 0]

cosine_sim(A, B) = 0.816  --> magas hasonlosag
cosine_sim(A, C) = 0.000  --> nincs hasonlosag
```

### Implementacio: CountVectorizer + Cosine Similarity

A **CountVectorizer** a mufajok listajat (pl. "Sci-Fi|Thriller|Action") numerikus vektorra alakitja. A **cosine_similarity** kiszamitja a filmek kozotti hasonlosagot:

```python
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Film adatok betoltese
movie = pd.read_csv("movie.csv")

# Genre-ok vektorizalasa
# A tokenizer a '|' karakterrel valasztja el a mufajokat
count_vectorizer = CountVectorizer(tokenizer=lambda x: x.split('|'))
genre_matrix = count_vectorizer.fit_transform(movie['genres'])

# Cosine similarity matrix kiszamitasa
cosine_sim = cosine_similarity(genre_matrix, genre_matrix)

# Ajanlasi fuggveny
def get_recommendations(title, n=10):
    """
    Egy adott filmhez a leghasonlobb filmeket adja vissza
    content-based filtering alapjan (genre hasonlosag).

    Args:
        title: A film cime
        n: Ajanlott filmek szama (default: 10)

    Returns:
        A leghasonlobb filmek listaja
    """
    # A film indexenek meghatarozasa
    idx = movie.index[movie['title'] == title][0]

    # Hasonlosagi pontszamok kinyerese
    sim_scores = list(enumerate(cosine_sim[idx]))

    # Rendezes csokkeno hasonlosag szerint
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Az elso 1:n+1 elem (az elso maga a film, 1.0 hasonlosaggal)
    sim_scores = sim_scores[1:n + 1]

    # Film indexek kinyerese
    movie_indices = [i[0] for i in sim_scores]

    return movie['title'].iloc[movie_indices]
```

### Elonyok es hatranyok

| Szempont | Elony | Hatrany |
|----------|-------|---------|
| Fuggetlenseg | Nem kell mas felhasznalok adata | Nem fedez fel ujat (filter bubble) |
| Cold start (termek) | Uj termeket is tud ajanlani, ha vannak attributumai | Uj felhasznalonak nem tud ajanlani |
| Atlathatosag | Megmagyarazhato, miert ajanl valamit | Csak hasonlot ajanl, nem meglepot |
| Skalazhatosag | Kevesebb adat is eleg | Attributum-minoseg kritikus |

---

## Collaborative Filtering

A **collaborative filtering** (CF, egyuttmukodesi szures) a felhasznaloi viselkedesmintak (ertekelesek, vasarlasok, kattintasok) alapjan ajanl. Az alapotlet: ha ket felhasznalo eddig hasonloan ertekelt, valsoinuleg a jovoben is hasonloan fog.

### Ket fo tipus

```
Collaborative Filtering
    |
    +-- Item-Based CF
    |     "Akik ezt a filmet szerettek, ezeket is szerettek"
    |     --> termekek kozotti korrelaciot szamol
    |
    +-- User-Based CF
          "A hozzad hasonlo felhasznalok ezeket szeretik"
          --> felhasznalok kozotti hasonlosagot szamol
```

### Adatelokeszites: Felhasznalo-Termek Matrix

Mindket CF tipus kiindulasi pontja a **pivot table** (felhasznalo-termek matrix):

```python
import pandas as pd

# Adatok betoltese es osszefuzese
movie = pd.read_csv("movie.csv")
rating = pd.read_csv("rating_only_5000.csv")
rating = rating.loc[rating["userId"] < 5000]
movies_rating_data = pd.merge(movie, rating, on='movieId')

# Aggregalt statisztikak: atlag rating es ertekelok szama
ratings = movies_rating_data.groupby('title').agg(
    rating_mean=('rating', 'mean'),
    ratings_count=('rating', 'count')
).reset_index()

# Csak a 100-nal tobb ertekelessel rendelkezo filmek
# (a ritkan ertekelt filmek torzitenéek az eredmenyt)
high_ratings = ratings[ratings['ratings_count'] > 100]
high_movies_rating = pd.merge(
    movies_rating_data,
    high_ratings[['title']],
    on='title'
)

# Pivot table: sorok = felhasznalok, oszlopok = filmek, ertekek = rating
movie_vs_userRating = high_movies_rating.pivot_table(
    columns='title',
    index='userId',
    values='rating'
).fillna(0)
```

> **Megjegyzes**: A `fillna(0)` fontos, mert a legtobb felhasznalo a filmek toredeket ertekeli. A 0 ertek "nem ertekelt" jelenti, nem "rossz ertekelest".

### Item-Based Collaborative Filtering

Az **item-based CF** ket termek kozotti korrelaciot szamit a felhasznaloi ertekelesek alapjan. Ha ket filmet hasonloan ertekelnek a felhasznalok, akkor hasonlonak tekintjuk oket.

#### Mukodesi elv

1. Vegyuk egy film ertekelesi vektorat (minden felhasznalo ertekelese arra a filmre)
2. Szamitsunk **korrelaciot** (`corrwith()`) az osszes tobbi film ertekelesi vektoraval
3. A legmagasabb korrelaciot mutatokat ajanjuk

#### Implementacio

```python
def item_based_recommender(movie_name, movie_vs_userRating):
    """
    Item-based collaborative filtering: egy adott filmhez
    hasonlo filmeket keres a felhasznaloi ertekelesek korrelacoja alapjan.

    A corrwith() a Pandas beepitett fuggvenye, amely
    oszloponkent szamitja a Pearson-korrelaciot.

    Args:
        movie_name: A film cime
        movie_vs_userRating: Felhasznalo-film pivot table

    Returns:
        Top 10 leghasonlobb film korrelacioertekkel
    """
    movie_ratings = movie_vs_userRating[movie_name]
    similar_movies = movie_vs_userRating.corrwith(movie_ratings)
    return similar_movies.sort_values(ascending=False).head(10)

# Pelda hasznalat:
# item_based_recommender("Forrest Gump (1994)", movie_vs_userRating)
```

#### Miert corrwith?

A `corrwith()` a **Pearson korrelacios egyutthatot** szamitja ket numerikus sorozat kozott. Ertelme:
- **+1**: teljesen pozitiv korrelacioval -- ha valaki az egyik filmet magasra ertekeli, a masikat is
- **0**: nincs linearis kapcsolat
- **-1**: teljesen negativ korrelacioval -- ha valaki az egyiket szereti, a masikat nem

### User-Based Collaborative Filtering

A **user-based CF** hasonlo felhasznalokat keres, es az o altaluk jol ertekelt (de az aktualis felhasznalo altal meg nem latott) termekeket ajanlja.

#### Mukodesi elv

1. Szamitsuk ki a felhasznalok kozotti **cosine similarity**-t
2. Keressuk meg az aktualis felhasznalohoz leghasonlobb felhasznalokat
3. Nezzuk meg, mit szerettek ok, amit mi meg nem lattunk
4. Rangsoroljuk az ajanlasat (pl. **median rating** alapjan)
5. Szurjuk ki a mar megnezett filmeket

#### Implementacio

```python
from sklearn.metrics import pairwise_distances
import pandas as pd
import numpy as np

# Felhasznalo-film matrix elkeszitese
user_movie_matrix = high_movies_rating.pivot_table(
    columns='movieId',
    index='userId',
    values='rating'
).fillna(0)

# Felhasznalok kozotti cosine similarity matrix
# pairwise_distances cosine tavolsagot ad: similarity = 1 - distance
user_similarity = 1 - pairwise_distances(user_movie_matrix, metric='cosine')

# Similarity matrix DataFrame-be
similarity_matrix = pd.DataFrame(
    user_similarity,
    index=user_movie_matrix.index,
    columns=user_movie_matrix.index
)

def user_based_recommender(user_id, top_n=5, n_similar_users=10):
    """
    User-based collaborative filtering: hasonlo felhasznalok
    altal kedvelt, de meg nem latott filmeket ajanl.

    Lepesek:
    1. Hasonlo felhasznalok keresese cosine similarity alapjan
    2. Az o ertekelesik median-janak kiszamitasa
    3. Mar megnezett filmek kiszurese

    Args:
        user_id: A cel-felhasznalo ID-ja
        top_n: Hany filmet ajanljunk
        n_similar_users: Hany hasonlo felhasznalot nezzunk

    Returns:
        Ajanolt filmek listaja
    """
    # Hasonlo felhasznalok (az elso maga a felhasznalo, 1.0-as hasonlosaggal)
    similar_users = similarity_matrix[user_id].sort_values(
        ascending=False
    )[1:n_similar_users + 1]

    # A hasonlo felhasznalok ertekelesei
    recommended_movies = user_movie_matrix.loc[similar_users.index]

    # Median rating az ajanlott filmekre
    recommended_movies = recommended_movies.median().sort_values(ascending=False)

    # Mar megnezett filmek kiszurese
    watched = user_movie_matrix.loc[user_id]
    watched_movieIds = watched[watched > 0].index

    unwatched = recommended_movies[
        ~recommended_movies.index.isin(watched_movieIds)
    ]

    return unwatched.head(top_n)
```

#### Miert median es nem mean?

A **median** robusztusabb a szelsoertes ertekelesekkel szemben. Ha 10 hasonlo felhasznalobol 9 magasra ertekelt egy filmet, de 1 nagyon alacsonyra, a median meg mindig magas lesz, mig az atlag jelentosen csokken.

### Item-Based vs User-Based CF Osszehasonlitas

| Szempont | Item-Based CF | User-Based CF |
|----------|---------------|---------------|
| Mit szamol | Termekek kozotti korrelacioval | Felhasznalok kozotti hasonlosaggal |
| Kiindulas | "Melyik filmek kapnak hasonlo ertekeleseket?" | "Kik ertekelnek hasonloan?" |
| Skalazas | Jobb skalazas sok felhasznalonal (kevesebb termek) | Skalazasi problema sok felhasznalonal |
| Stabilitás | Stabilabb: termekkorrelaciok lassan valtoznak | Valtozekonyabb: uj felhasznaloi ertekelesek valtoztatjak |
| Cold start | Uj termek: nincs korrelacios adat | Uj felhasznalo: nincs hasonlosagi adat |
| Tipikus hasznat | Amazon "Hasonlo termekek" | Netflix "Neked ajanlott" |

---

## Cosine Similarity Reszletesen

A **cosine similarity** (koszinusz-hasonlosag) a ket legfontosabb hasonlosagmertek egyike az ajanlórendszerekben. A ket vektor kozotti szoget meri, nem a tavolsagukat.

### Matematikai Formula

```
                    A . B           Szumi(Ai * Bi)
cos(theta) = --------------- = ---------------------------
              ||A|| * ||B||    sqrt(Szumi(Ai^2)) * sqrt(Szumi(Bi^2))
```

Ahol:
- `A . B` = a ket vektor **skalaris szorzata** (dot product)
- `||A||` = az A vektor **normaja** (hossza)
- Az eredmeny **-1 es +1 kozott** van (nem-negativ ertekeknel 0 es 1 kozott)

### Vizualis magyarazat

```
         B (0.8, 0.6)
        /
       / ) theta = kis szog --> magas hasonlosag (kozel 1)
      /  )
     /---)--> A (0.9, 0.1)
    O

         B (0.0, 1.0)
         |
         | ) theta = 90 fok --> nulla hasonlosag (0)
         |
         O-------> A (1.0, 0.0)
```

### Peldaszamitas kezzel

```
Film X genre vektor: [1, 0, 1, 1, 0]   (Action, Drama, Sci-Fi)
Film Y genre vektor: [1, 1, 1, 0, 0]   (Action, Comedy, Sci-Fi)

Skalaris szorzat:  1*1 + 0*1 + 1*1 + 1*0 + 0*0 = 2
||X|| = sqrt(1+0+1+1+0) = sqrt(3) = 1.732
||Y|| = sqrt(1+1+1+0+0) = sqrt(3) = 1.732

cos(theta) = 2 / (1.732 * 1.732) = 2/3 = 0.667
```

> **Ertelmezes**: 0.667 -- kozepesen magas hasonlosag, ket kozos mufajjal.

### Miert cosine es nem euklideszi tavolsag?

| Szempont | Cosine Similarity | Euklideszi Tavolsag |
|----------|-------------------|---------------------|
| Mit mer | Irany (szog) | Abszolut tavolsag |
| Skalafuggetlenseg | Igen -- az irany szamit | Nem -- a nagyobbertekek dominalnalnak |
| Ritka matrixok | Jo, mert a 0-k nem "buntetnek" | Rossz, mert sok 0 nagy tavolsagot ad |
| Ajanlórendszerereknel | Elonyosebb | Kevesbe jellemzo |

### Cosine Similarity vs Pearson Korrelacioval

A **corrwith()** (item-based CF-nel hasznalt) a **Pearson korrelacioval** szamol, ami lenyegeben a kozepre centralt cosine similarity:

```
Pearson(A, B) = cosine_similarity(A - mean(A), B - mean(B))
```

A Pearson korrelacioval figyelembe veszi, hogy kulonbozo felhasznalok kulonbozo "atlagos" szinten ertekelnek (valaki mindent 4-5-re, valaki 2-3-ra).

---

## Association Rule Learning

Az **association rule learning** (asszociacios szabalytanulas) a tranzakcio-alapu ajanlás modszere. Nem felhasznaloi preferenciakat, hanem termekek **egyuttes vasarlasi mintazatait** elemzi.

### Tipikus alkalmazas: kosarelemzes (Market Basket Analysis)

"Akik citromot vettek, azok teat is vettek" -- ez egy tipikus asszociacios szabaly.

### Harom fo metrika

#### 1. Support (Tamogatottsag)

A **support** megmutatja, milyen gyakran fordul elo egy termek (vagy termekkombinacio) az osszes tranzakcioban.

```
                   termeket tartalmazo tranzakciok szama
Support(A) = ------------------------------------------------
                      osszes tranzakciok szama
```

**Pelda**: 10 tranzakciobol 6-ban van citrom --> `Support(citrom) = 6/10 = 0.6`

#### 2. Confidence (Megbizhatosag)

A **confidence** felteteles valoszinuseg: ha A-t megvette, mekkora esellyel veszi meg B-t is.

```
                         Support(A es B)
Confidence(A --> B) = --------------------
                         Support(A)
```

**Pelda**: 6 citroomos tranzakciobol 5-ben van tea --> `Confidence(citrom --> tea) = 5/6 = 0.833`

#### 3. Lift (Emeles)

A **lift** megmutatja, mennyire erosebb az asszociacio, mint amit a veletlentol varnanank.

```
                      Confidence(A --> B)
Lift(A --> B) = ---------------------------
                      Support(B)
```

**Lift ertelmezese**:
- **Lift > 1**: pozitiv asszociacio -- A jelenlete noveli B vasarlasanak eselyet
- **Lift = 1**: fuggetlenek -- nincs kapcsolat
- **Lift < 1**: negativ asszociacio -- A jelenlete csokkenti B vasarlasanak eselyet

### Implementacio: kezzel szamolt pelda

```python
import pandas as pd

# Tranzakcios adat: 10 tranzakcio, binaris (0/1) ertekek
df = pd.DataFrame({
    'lemon':      [1, 0, 1, 1, 0, 1, 1, 0, 1, 0],
    'bread':      [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    'milk':       [0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
    'sour cream': [0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
    'tea':        [1, 0, 1, 0, 0, 1, 1, 0, 1, 0]
})

# 1. Support: minden termek gyakorisaga
support = df.sum() / len(df)
print("Support:")
print(support)
# lemon:      0.6
# bread:      0.2
# milk:       0.2
# sour cream: 0.2
# tea:        0.5

# 2. Confidence: ha citromot vett, mit vett meg?
lemon_transactions = df[df['lemon'] == 1]  # csak citroomos tranzakciok
confidence = lemon_transactions.sum() / len(lemon_transactions)
print("\nConfidence (citrom --> ?):")
print(confidence)
# lemon:      1.000  (trivialis)
# bread:      0.167
# milk:       0.167
# sour cream: 0.167
# tea:        0.833  <-- magas! ha citromot vesz, 83%-ban teat is vesz

# 3. Lift: mennyire erősebb a veletlennel
lift = confidence / support
print("\nLift (citrom --> ?):")
print(lift)
# tea:  0.833 / 0.5 = 1.667  <-- erős pozitiv assszociacio
# bread: 0.167 / 0.2 = 0.833 <-- gyenge negativ
```

### A harom metrika kapcsolata -- vizuális osszefoglalas

```
Support     = "Mennyire gyakori ez a termek?"
Confidence  = "Ha A-t megvette, milyen esellyel veszi B-t?"
Lift        = "Ez erosebb-e a veletlennel? (>1 = igen)"

Pelda: citrom --> tea
  Support(citrom)  = 0.6   (a tranzakciok 60%-ban van citrom)
  Support(tea)     = 0.5   (a tranzakciok 50%-ban van tea)
  Confidence       = 0.833 (ha citromot vesz, 83%-ban teat is)
  Lift             = 1.667 (67%-kal erosebb, mint a veletlen)
```

### Ipari alkalmazasok

| Alkalmazas | Pelda |
|------------|-------|
| Kiskereskedelem | "Akik kenyeret vesznek, azok tejet is vesznek" -- polcelrendezes |
| Webshop | "Akik laptopot vettek, azok egerpaddot is vettek" -- cross-selling |
| Content | "Akik ezt a cikket olvastak, ezt is olvastak" |
| Egeszsegugy | Tunet-kombinaciok es diagnoszis mintazatok |

---

## Felugyelt Tanulas Ajanlórendszerekben

A **supervised learning** (felugyelt tanulas) is hasznalhato ajanlórendszerek reszenekent, kulonosen ott, ahol gazdag feature-keszlet all rendelkezesre.

### Mikor erdemes supervised megkozelitest alkalmazni?

- Amikor a **matching problema** bonyolult es sok feature-rel rendelkezunk
- Amikor explicit cel-valtozo letezik (pl. kattintott-e, vasarolt-e, jelentkezett-e)
- Amikor a content-based es CF modszerek egyedul nem eleg jok

### Pelda: Recruitment Recommender

Egy allasajanlat-ajanlo rendszerben a kovetkezo feature-ok hasznalhatoal:

```
Feature Engineering - Recruitment Recommender:

Jelolt oldalrol:              Allas oldalrol:
  - job_title_match (0/1)       - required_skills
  - skills_overlap (0-1)        - company_size
  - experience_years            - location
  - location_match (0/1)        - salary_range
  - seniority_level             - industry
  - education_level

Cel-valtozo (target):
  - applied (0/1)  -- jelentkezett-e?
  - hired (0/1)    -- felvettek-e?
```

### Supervised modell mint rangsoro

```
Feature vektor (jelolt + allas) --> Supervised Model --> P(match)
                                    (pl. XGBoost)       |
                                                        v
                                                   Rangsorolas
                                                   (top N ajanlat)
```

A supervised modell minden (jelolt, allas) parra kiszamit egy **match valoszinuseget**, es a legnagyobb valoszinuseguket ajanlja.

### Hibrid rendszer: a harom megkozelites kombinálasa

A legtobb ipari rendszer **hibrid**: tobb modszert kombalnal egymással.

```
+---------------------------+
|    HIBRID RENDSZER        |
+---------------------------+
|                           |
|  Content-Based Filtering  | --> termek-hasonlosag alapjan szur
|    (genre, leiras)        |
|                           |
|  Collaborative Filtering  | --> felhasznaloi viselkedes alapjan szur
|    (user-CF, item-CF)     |
|                           |
|  Supervised Learning      | --> feature-alapu rangsorolas
|    (XGBoost, NN)          |
|                           |
+---------------------------+
            |
            v
   Vegso rangsort ajanlas
   (sulyzott kombinalas)
```

**Elonyok**:
- A content-based megoldja a **cold start** problemat (uj termekeknel)
- A CF megoldja a **discovery** problemat (ujat is felfedezheti a felhasznalo)
- A supervised **finomhangolast** biztosit es explicit cel-valtozora optimalizal

---

## Osszehasonlito Tablazat

| Szempont | Content-Based | Item-Based CF | User-Based CF | Association Rules | Supervised |
|----------|---------------|---------------|---------------|-------------------|------------|
| **Bemenet** | Termek attributumok | Ertekelesi matrix | Ertekelesi matrix | Tranzakcio adat | Feature vektor + label |
| **Hasonlosag** | Cosine sim (attributumok) | Pearson korrelacioval | Cosine sim (ertekelest) | Support/Confidence/Lift | Nem hasonlosag-alapu |
| **Cold start (uj user)** | Nem tud ajanlani | Nem tud ajanlani | Nem tud ajanlani | Tud (nincs user-fuggoseg) | Tud (ha vannak feature-ok) |
| **Cold start (uj item)** | Tud ajanlani | Nem tud ajanlani | Nem tud ajanlani | Tud | Tud (ha vannak feature-ok) |
| **Skalazas** | O(n*m) | O(m^2) | O(n^2) | O(2^m) | O(n) predikcioval |
| **Magyarazhatosag** | Magas | Kozepes | Kozepes | Magas | Alacsony-kozepes |
| **Tipikus tool** | CountVectorizer, TF-IDF | corrwith, Surprise | pairwise_distances | mlxtend, Apriori | XGBoost, DNN |
| **Adatigenye** | Termek metaadat | Sok ertekelest | Sok ertekelest | Tranzakcio log | Labeled adat |
| **"Meglepetes" ajanlas** | Nem (filter bubble) | Igen | Igen | Igen | Kozepes |

---

## Gyakorlati Utmutato

### Ajanlórendszer Epitesi Workflow

```
[1. Adatgyujtes]
     |
     v
[2. Felderites es EDA]
  - Hany felhasznalo, termek?
  - Milyen sur az ertekelesi matrix? (sparsity)
  - Milyen attributumok elerhetoek?
     |
     v
[3. Modszervalasztas]
  - Kevés adat --> Content-Based
  - Sok ertekelest --> Collaborative Filtering
  - Tranzakcio adat --> Association Rules
  - Sok feature + label --> Supervised
  - Ipari rendszer --> Hibrid
     |
     v
[4. Adatelokeszites]
  - Pivot table epitese (CF-hez)
  - Feature vektorizalas (content-based-hez)
  - Rating szures (min. N ertekelest)
     |
     v
[5. Modell epitese]
  - Hasonlosagi matrix szamitas
  - Ajanlasi fuggveny implementalasa
     |
     v
[6. Kiertekeles]
  - Train/test split (idoalapu!)
  - Precision@K, Recall@K, NDCG
  - A/B teszt produkcioban
     |
     v
[7. Deployment]
  - Offline batch szamitas (hasonlosagi matrix)
  - Online szerviralas (top-N lekerdezes)
  - Cache es frissitesi strategia
```

### Kod peldak -- Teljes pipeline

#### 1. Adat betoltes es elokeszites

```python
import pandas as pd
import numpy as np

# Adatok betoltese
movie = pd.read_csv("movie.csv")
rating = pd.read_csv("rating_only_5000.csv")
rating = rating.loc[rating["userId"] < 5000]

# Osszefuzes
movies_rating_data = pd.merge(movie, rating, on='movieId')

# Aggregalas: filmenkenti atlag es darabszam
ratings = movies_rating_data.groupby('title').agg(
    rating_mean=('rating', 'mean'),
    ratings_count=('rating', 'count')
).reset_index()

# Szures: csak a popularisok (100+ ertekelest)
high_ratings = ratings[ratings['ratings_count'] > 100]
high_movies_rating = pd.merge(
    movies_rating_data,
    high_ratings[['title']],
    on='title'
)

print(f"Osszes film: {movie.shape[0]}")
print(f"Osszes ertekelest: {rating.shape[0]}")
print(f"Popularis filmek szama: {high_ratings.shape[0]}")
```

#### 2. Content-based ajanlás

```python
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Genre vektorizalas
vectorizer = CountVectorizer(tokenizer=lambda x: x.split('|'))
genre_matrix = vectorizer.fit_transform(movie['genres'])

# Hasonlosagi matrix
cosine_sim = cosine_similarity(genre_matrix, genre_matrix)

# Ajanlas
def content_recommend(title, n=5):
    idx = movie.index[movie['title'] == title][0]
    scores = list(enumerate(cosine_sim[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:n+1]
    return movie['title'].iloc[[i[0] for i in scores]]

print(content_recommend("Toy Story (1995)"))
```

#### 3. Item-based CF ajanlás

```python
# Pivot table
pivot = high_movies_rating.pivot_table(
    columns='title', index='userId', values='rating'
).fillna(0)

def item_recommend(movie_name, n=5):
    correlations = pivot.corrwith(pivot[movie_name])
    return correlations.sort_values(ascending=False).head(n + 1).iloc[1:]

print(item_recommend("Forrest Gump (1994)"))
```

#### 4. User-based CF ajanlás

```python
from sklearn.metrics import pairwise_distances

user_pivot = high_movies_rating.pivot_table(
    columns='movieId', index='userId', values='rating'
).fillna(0)

user_sim = 1 - pairwise_distances(user_pivot, metric='cosine')
sim_df = pd.DataFrame(user_sim, index=user_pivot.index, columns=user_pivot.index)

def user_recommend(user_id, n=5, k=10):
    similar = sim_df[user_id].sort_values(ascending=False)[1:k+1]
    recs = user_pivot.loc[similar.index].median().sort_values(ascending=False)
    watched = user_pivot.loc[user_id]
    watched_ids = watched[watched > 0].index
    return recs[~recs.index.isin(watched_ids)].head(n)

print(user_recommend(1))
```

---

## Cold Start es Sparsity Problemak

Ezek az ajanlórendszerek ket legkritikusabb kihivasa.

### Cold Start Problema

A **cold start** (hideginditas) problema akkor all fenn, amikor nincs eleg adat az ajanláshoz.

#### Uj felhasznalo (User Cold Start)

- Nincs korabbi ertekelese, bongeszesi elozmeny
- A CF modszerek nem tudnak hasonlo felhasznalot keresni

**Megoldasok**:
- **Onboarding kerdoiv**: "Milyen mufajokat szeretsz?" --> content-based ajanlas
- **Popularitas-alapu ajanlas**: a globalis toplista alapjan ajanl
- **Demografiai hasonlosag**: kor, nem, regio alapjan hasonlo felhasznalok keresese
- **Implicit feedback**: bongeszesi ido, kattintasok (nem kell explicit ertekelest)

#### Uj termek (Item Cold Start)

- Nincs meg ertekelese a termeknek
- Az item-based CF nem tudja korrelalni mas termekekkel

**Megoldasok**:
- **Content-based ajanlas**: a termek attributumai (mufaj, leiras) alapjan is tud ajanlani
- **Metadata-alapu hasonlosag**: kozos szineszek, rendezo, kategoria
- **Exploration/exploitation**: idnkent random uj termekeket is megmutatni

### Sparsity Problema

A **sparsity** (ritkaság) problema: a felhasznalo-termek matrix tobbsege ures.

```
Pelda sparsity:
  - 5000 felhasznalo x 10000 film = 50 millio lehetseges ertekelest
  - Valos ertekelesek szama: 500 000
  - Kitoltottseg: 1%
  - Sparsity: 99%
```

**Kovetkezmeny**: a korrelaciok es hasonlosagok megbizhatatlanok, mert keves kozos adat all rendelkezesre.

**Megoldasok**:
- **Minimalis ertekelestszam szures**: csak 100+ ertekelessel rendelkezo filmek/felhasznalok
- **Dimenziocsokkentes**: SVD, NMF a matrix faktorializaciojara
- **Implicit feedback bevonasa**: nem csak explicit ertekelesek, hanem megtekintest, bongeszesi ido stb.
- **Hibrid megkozelites**: tobb adatforras kombinálása

---

## Gyakori Hibak es Tippek

### Hibak

1. **Sparsity figyelmen kivul hagyasa**: A ritka matrixon szamolt korrelaciok megbizhatatlanok. Mindig szurjuk a minimalis ertekelestszamra (pl. `ratings_count > 100`).

2. **fillna(0) felreertelmezese**: A `fillna(0)` "nem ertekelt"-et jelent, NEM "0 pontos ertekeles"-t. Egyes algoritmusok (pl. SVD) mas defaultot hasznalnalnak (pl. atlag ertekelest).

3. **Csak egy modszerre hagyatkozas**: A content-based egyedul **filter bubble**-hoz vezet (mindig hasonlot ajanl). A CF egyedul **cold start** problemat okoz. A hibrid megkozelites szinte mindig jobb.

4. **Nem idoalapu kiertekeles**: Az ajanlórendszererek kiertekelesnel idorendileg kell szétválasztani a train/test adatot. Veletlen split eseten "jovobol" tanuhat a modell.

5. **A lift metrika felreertelmezese**: A lift = 1 nem jelent "rossz" assszociaciot, hanem fuggetlenseget. Lift < 1 negativ asszociacio (ritkabban fordulnak elo egyutt, mint a veletlen).

6. **Skalazasi problemak production-ben**: A teljes user-similarity matrix O(n^2) memoriait es idot igenyel. 1 millio felhasznalonal ez nem memoriatban tarthato -- approximate nearest neighbors (ANN) kell.

### Tippek

1. **Kezdd content-based-del**: Ez a legegyszerubb baseline. Ha jol mukodik, a CF csak novekmenyes javulast hoz.

2. **Hasznalj rating kuszob szurest**: A `ratings_count > 100` szures dramatikusan javitja a CF minosseget. A pontos kuszob adat-specifikus -- kiserletezes kell.

3. **Median vs mean az user-based CF-nel**: A median robusztusabb a szelsoertekekkel szemben. Ha egy outlier felhasznalo 1-est ad egy alapvetoen jo filmnek, a median nem torzul.

4. **Association rules skálazasa**: Nagy tranzakciovalszam eseten a nyers brute-force megkozelites lassú. Hasznald az **Apriori** vagy **FP-Growth** algoritmust (pl. `mlxtend` konyvtar).

5. **Implicit feedback**: Sok rendszerben nincs explicit ertekelest (1-5 csillag), de van implicit signal: bongeszesi ido, kattintast, kosar, wishliszt. Ezeket is felhasznalhatod.

6. **A/B teszteles**: Az offline metrikak (precision@K) nem mindig korrelalnalnak a valos felhasznaloi elegedettseg-gel. Production-ben A/B teszt kell.

7. **Elso ajanlas**: Az elso benyomas kritikus. Uj felhasznaloknak a popularitas-alapu ajanlas biztonsagos kiindulas, majd fokozatosan personalizalj.

---

## Kapcsolodo Temak

- [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- Felugyelt tanulasi modszerek, amelyek az ajanlorendszerek supervised komponensenel hasznalhatoal (XGBoost, Random Forest, logisztikus regresszio)
- [08_dimenziocsokkentes.md](08_dimenziocsokkentes.md) -- PCA, SVD, NMF, amelyek a sparsity-problema megoldasahoz es a matrix faktorizaciohoz hasznalhatoak

---

## Tovabbi Forrasok

- **scikit-learn Pairwise Metrics**: https://scikit-learn.org/stable/modules/metrics.html#cosine-similarity
- **Surprise konyvtar** (Collaborative Filtering): https://surpriselib.com/
- **mlxtend Association Rules**: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/
- **Google Recommendation Systems Course**: https://developers.google.com/machine-learning/recommendation
- **Netflix Prize**: https://en.wikipedia.org/wiki/Netflix_Prize
- **Matrix Factorization technikak**: https://datajobs.com/data-science-repo/Recommender-Systems-[Netflix].pdf
- **Implicit Feedback CF**: https://ieeexplore.ieee.org/document/4781121
- **Facebook DLRM**: https://ai.meta.com/blog/dlrm-an-advanced-open-source-deep-learning-recommendation-model/
