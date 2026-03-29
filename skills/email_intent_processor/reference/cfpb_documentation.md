# CFPB Panasz Intent Routing — ML Rendszer Dokumentáció

**Projekt:** Cubix ML Engineering kurzus — Pilot feladat
**Szerző:** Kassai Attila
**Dátum:** 2026. március
**Felhasznált AI eszköz:** Claude Code (Anthropic Claude Opus 4)

---

## Tartalomjegyzék

1. [Projekt áttekintés](#1-projekt-áttekintés)
2. [Módszertan (CRISP-DM)](#2-módszertan-crisp-dm)
3. [EDA összefoglaló](#3-eda-összefoglaló)
4. [Preprocessing döntések](#4-preprocessing-döntések)
5. [Modellek és eredmények](#5-modellek-és-eredmények)
6. [Optimalizációs kísérletek](#6-optimalizációs-kísérletek)
7. [Végleges modell és metrikák](#7-végleges-modell-és-metrikák)
8. [Kihívások és limitációk](#8-kihívások-és-limitációk)
9. [Hallgatói értékelés](#9-hallgatói-értékelés)
10. [Futtatási instrukciók](#10-futtatási-instrukciók)

---

## 1. Projekt áttekintés

### 1.1 Üzleti kontextus

A **Consumer Financial Protection Bureau (CFPB)** az Egyesült Államok pénzügyi fogyasztóvédelmi hivatala, amely naponta több ezer fogyasztói panaszt fogad. A panaszok rendkívül sokféle pénzügyi terméket érintenek: hiteljelentéseket, adósságbehajtást, jelzáloghiteleket, bankkártyákat, személyes kölcsönöket.

A projekt alapfelvetése: a beérkező panaszok **szöveges tartalma** alapján — hasonlóan egy e-mail routing rendszerhez — automatikusan meghatározható a panasz szándéka (intent) és a megfelelő ügyintézői csoport. Ezt a feladatot ebben a projektben **klasszikus ML módszerekkel** oldjuk meg: TF-IDF szövegreprezentáció és felügyelt tanulási algoritmusok (LinearSVC, LightGBM stb.) segítségével.

Az automatikus routing üzleti értéke:

- **Gyorsaság:** milliszekundumos routing a percek helyett
- **Konzisztencia:** determinisztikus döntés, nem függ az ügyintéző szubjektív megítélésétől
- **Skálázhatóság:** a panaszok számának növekedése nem igényel lineáris létszámnövelést
- **Kapacitástervezés:** az intent-eloszlás alapján előre tervezhető az erőforrás-allokáció

### 1.2 A feladat

Multi-class szövegklasszifikációs feladat:
- **Bemenet:** szabad szöveges panasz (`Consumer complaint narrative`)
- **Kimenet:** routing csoport (10 tematikus kategória)
- **Elsődleges metrika:** Macro F1-score — minden routing csoport egyformán fontos
- **Célérték:** Macro F1 ≥ 0.60

### 1.3 Adatforrás

- **Adathalmaz:** CFPB Consumer Finance Complaints (publikus, legálisan elérhető)
- **Fejlesztési minta:** `complaints_sample_50k.csv` — 50 000 sor, 18 oszlop
- **Célváltozó:** `Issue` mező (154 eredeti kategória → 10 routing csoport, 94 mapping szabállyal)
- **Fő feature:** `Consumer complaint narrative` (szabad szöveges panaszleírás)

### 1.4 Routing csoportok

| # | Routing csoport | Ügyintézői specializáció |
|---|----------------|--------------------------|
| 1 | credit_report_accuracy | Hiteljelentés viták, adatkorrekciók |
| 2 | identity_theft_unauthorized | Fraud team, biztonsági vizsgálat |
| 3 | investigation_escalation | Másodlagos felület, escalation desk |
| 4 | debt_collection_practice | Behajtási jogsértések, kommunikációs panaszok |
| 5 | account_management | Számla nyitás/zárás/üzemeltetés |
| 6 | payment_issues | Tranzakció-feldolgozás, díjak |
| 7 | mortgage_loan_servicing | Jelzálog- és hitelszerviz team |
| 8 | card_purchase_disputes | Bankkártyaviták, vásárlási panaszok |
| 9 | loan_lease_management | Kölcsön/lízing portfólió team |
| 10 | credit_monitoring_access | Hiteljelentés hozzáférés, monitoring |

---

## 2. Módszertan (CRISP-DM)

A projektet a **CRISP-DM** (Cross-Industry Standard Process for Data Mining) keretrendszer mentén építettem fel. Ez a 6 fázisból álló módszertan az iparban de facto standard.

### 2.1 Business Understanding — Üzleti megértés

A panasz-routing automatizálásának három fő érintettje van:
- **Fogyasztók:** gyorsabb ügyintézés, relevánsabb válasz
- **Ügyintézői csoportok:** specializált panaszokat kapnak
- **Vezetőség:** kapacitástervezés az intent-eloszlás alapján

Sikerkritérium: Macro F1 ≥ 0.60, REST API-n keresztül integrálható, gyorsabb mint a manuális routing.

### 2.2 Data Understanding — Adatmegértés

Az 50 000 soros minta 18 oszlopot tartalmaz. Az `Issue` mező 154 egyedi kategóriát fed le, amelyek közül a top 3 az összes minta ~59%-át adja — erős class imbalance. A szöveghossz mediánja ~664 karakter, jobbra ferde eloszlással. A CFPB `XXXX`/`XX` redakciókkal takarja a személyes adatokat.

### 2.3 Data Preparation — Adat-előkészítés

1. Hiányzó narratívák szűrése
2. Intent mapping: 154 Issue → 10 routing csoport (94 szabály)
3. Szövegtisztítás: `clean_text()` függvény
4. Stratifikált train-test split (80/20)
5. TF-IDF vektorizáció (10 000 feature, bigram)

### 2.4 Modeling — Modellezés

7 felügyelt tanulási algoritmust hasonlítottam össze:
1. Logistic Regression — lineáris baseline
2. LinearSVC — Support Vector Classifier
3. Decision Tree — döntési fa
4. Random Forest — ensemble bagging
5. AdaBoost — adaptív boosting (shallow DecisionTree-kkel)
6. XGBoost — gradient boosting
7. LightGBM — histogram-alapú gradient boosting

Kiegészítésként KNN-t TruncatedSVD dimenziócsökkentés után teszteltem.

### 2.5 Evaluation — Értékelés

- **Elsődleges:** Macro F1 (osztályfüggetlen, egyenlő súlyozású)
- **Kiegészítő:** Weighted F1, Accuracy, Confusion Matrix, ROC-AUC, PR-AUC, per-class F1
- **Cross-validation:** 5-fold StratifiedKFold a top modelleknél

### 2.6 Deployment — Üzembe helyezés

- **sklearn Pipeline:** TfidfVectorizer → CalibratedClassifierCV(LinearSVC)
- **Modell:** joblib szerializáció (`models/intent_routing_model.joblib`)
- **REST API:** FastAPI + uvicorn, 4 endpoint
- **CLI:** `python pipeline.py train|predict|predict_proba`
- **Tesztek:** pytest, 32 teszt eset

---

## 3. EDA összefoglaló

### 3.1 Adathalmaz alapjellemzői

Az 50 000 soros minta feldolgozása során a következő főbb jellemzőket azonosítottam:

- **Sorok:** ~49 600 (a narratíva nélküli sorok szűrése után)
- **Oszlopok:** 18
- **Egyedi Issue értékek:** 154
- **Routing csoportok száma:** 10 (az "other" kategória eldobása után)

### 3.2 Class imbalance

Az `Issue` mező erős class imbalance-t mutat. A mapping és az "other" eldobása után:

| Routing csoport | Mintaszám (hozzávetőleges) | Arány |
|----------------|---------------------------|-------|
| credit_report_accuracy | ~16 000 | ~32% |
| identity_theft_unauthorized | ~9 300 | ~19% |
| investigation_escalation | ~8 100 | ~16% |
| debt_collection_practice | ~4 800 | ~10% |
| card_purchase_disputes | ~2 400 | ~5% |
| account_management | ~1 900 | ~4% |
| mortgage_loan_servicing | ~1 200 | ~2.5% |
| payment_issues | ~1 200 | ~2.5% |
| loan_lease_management | ~500 | ~1% |
| credit_monitoring_access | ~400 | ~1% |

A `credit_report_accuracy` csoport 32-szeres fölényben van a `credit_monitoring_access`-hez képest — ez indokolja a `class_weight='balanced'` használatát és a Macro F1 elsődlegességét.

### 3.3 Vizualizációk

A notebook vizualizációi az EDA legfontosabb dimenzióit fedik le:
- **Routing csoport eloszlás** — bar chart az imbalance szemléltetésére
- **Szöveghossz eloszlás** — histogram + KDE, routing csoportonként
- **Issue × Product crosstab** — heatmap a kétdimenziós eloszlásról
- **WordCloud** — routing csoportonkénti szófelhő a jellemző kifejezésekkel

A vizualizációk az `output/figures/` mappában is mentve vannak.

---

## 4. Preprocessing döntések

### 4.1 Intent mapping (154 Issue → 10 csoport)

Az eredeti 154 `Issue` kategória konszolidálása 10 routing csoportra 94 mapping szabály segítségével történt. A döntés indokai:

1. **Üzleti relevancia:** Sok Issue tematikusan átfed (pl. "Incorrect information on your report" és "Incorrect information on credit report" lényegében azonos). Az ügyintézői csoportok ~10 tematikus egységben dolgoznak.

2. **Statisztikai megbízhatóság:** 154 kategóriánál sok kategória alig néhány mintát tartalmaz. A minimum ~200 minta/csoport küszöbbel biztosítottam, hogy minden csoport érdemben tanulható legyen.

3. **"Other" kezelése:** A 94 mapping szabály alkalmazása után az "other" catch-all kategória a minták ~1%-ára csökkent. Mivel ez a csoport túl kicsi és heterogén a megbízható tanuláshoz, eldobtam — a modell 10 jól definiált routing csoporttal dolgozik.

### 4.2 Szövegtisztítás

```python
def clean_text(text):
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'x{2,}', 'REDACTED', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
```

- **Kisbetűsítés:** konzisztencia a TF-IDF-hez
- **XXXX → REDACTED:** egységes token a redaktált adatokra, a modell ne tanuljon zajt a változó számú X-ekből
- **Speciális karakterek eltávolítása:** írásjelek, szimbólumok — szövegklasszifikációnál általában nem hordoznak hasznos információt
- **Nincs stemming/lemmatizálás:** az angol nyelvű panaszoknál a TF-IDF bigram-okkal megfelelő reprezentációt kapunk

### 4.3 TF-IDF konfiguráció

```python
TfidfVectorizer(
    max_features=10000,
    min_df=5,
    max_df=0.95,
    ngram_range=(1, 2),
    sublinear_tf=True,
    strip_accents='unicode'
)
```

| Paraméter | Érték | Indoklás |
|-----------|-------|----------|
| `max_features` | 10 000 | A 10k–20k tartomány tesztelése után a 10k bizonyult a legjobb kompromisszumnak: a további feature-ök marginálisan javítottak, miközben a mátrix méretét és a futásidőt jelentősen növelték. |
| `min_df` | 5 | Túl ritka szavak (elírások, egyedi nevek) kiszűrése |
| `max_df` | 0.95 | Szinte minden dokumentumban előforduló szavak kiszűrése |
| `ngram_range` | (1, 2) | A bigramok fontos szókapcsolatokat ragadnak meg (pl. "credit report", "identity theft") |
| `sublinear_tf` | True | Logaritmikus tf csökkenti a nagyon gyakori szavak túlreprezentáltságát |

### 4.4 Train-test split

- **80/20** arány, stratifikált (`stratify=y`), `random_state=42`
- A stratifikálás biztosítja, hogy a routing csoportok aránya megmaradjon mindkét halmazban

### 4.5 Class imbalance kezelés

- **`class_weight='balanced'`** minden modellnél (kivéve XGBoost, ahol mintasúlyozás)
- Automatikusan inverz arányos súlyokat rendel: `n_samples / (n_classes * n_samples_per_class)`
- Ez biztosítja, hogy a ~1%-os csoportok (pl. `credit_monitoring_access`) ne legyenek elnyomva a tanítás során

---

## 5. Modellek és eredmények

### 5.1 Összehasonlító táblázat (TF-IDF feature-ökkel)

7 felügyelt tanulási algoritmust hasonlítottam össze.

| Modell | Train Acc | Test Acc | Macro F1 | Weighted F1 | Gap | Állapot |
|--------|-----------|----------|----------|-------------|-----|---------|
| LightGBM | 0.932 | 0.692 | **0.630** | 0.692 | 0.240 | Túltanulás |
| LogisticRegression | 0.739 | 0.654 | 0.600 | 0.657 | 0.085 | OK |
| LinearSVC | 0.860 | 0.668 | 0.598 | 0.670 | 0.192 | Túltanulás |
| XGBoost | 0.830 | 0.670 | 0.595 | 0.665 | 0.160 | Túltanulás |
| AdaBoost | 0.489 | 0.480 | 0.428 | 0.467 | 0.008 | OK |
| Random Forest | 0.594 | 0.550 | 0.474 | 0.556 | 0.044 | OK |
| Decision Tree | 0.671 | 0.527 | 0.453 | 0.526 | 0.144 | OK |

Az AdaBoost a leggyengébb modell (Macro F1: 0.428), de a legstabilabb — mindössze 0.8% train-test gap. A shallow tree-k (max_depth=2) miatt az adaptív boosting 10 osztálynál nem ér el kellő pontosságot.

### 5.2 Modell-specifikus megfigyelések

**LightGBM** érte el a legjobb Macro F1 értéket (0.630), de erősen túltanul (24% gap). A histogram-alapú split keresés és a natív sparse mátrix kezelés teszi hatékonnyá szövegklasszifikációnál.

**LogisticRegression** a legstabilabb modell — a legkisebb train-test gap-pel (8.5%) jó generalizációs képességet mutat. Lineáris modellként sparse mátrixokon különösen hatékony.

**LinearSVC** az `SVC(kernel='linear')` optimalizált változata — matematikailag azonos, de a `liblinear` solver-rel 40 000+ mintán lényegesen gyorsabb. Valószínűségi kimenethez `CalibratedClassifierCV` wrappert alkalmaztam (Platt-scaling).

**XGBoost** jó test accuracy-t ért el, de a Macro F1-ben elmarad a LightGBM-től.

**AdaBoost** shallow DecisionTree-kkel (`max_depth=2`) dolgozik — gyenge tanulókból épít ensemble-t, ami 10 osztályos feladatnál korlátozott teljesítményt ad.

**Decision Tree** és **Random Forest** erősen hajlamosak a túltanulásra nagy dimenziós sparse adaton. A Random Forest 30 fából álló ensemble-je robusztusabb, de a test Macro F1 mindkettőnél 0.50 alatt marad.

### 5.3 KNN (TruncatedSVD után)

A KNN-t kizárólag TruncatedSVD dimenziócsökkentés után alkalmaztam, mert high-dimenziós sparse adaton a távolságmetrikák elvesztik a diszkriminatív erejüket ("curse of dimensionality"). Az eredményeket a 6.1 szekció tartalmazza.

---

## 6. Optimalizációs kísérletek

### 6.1 Dimenziócsökkentés: TruncatedSVD

**Miért TruncatedSVD és nem PCA?**

A TF-IDF mátrix ritka (sparse): a 10 000 feature közül egy dokumentumban csak néhány száz nem nulla. A PCA centralizálja az adatokat, ami megszünteti a ritkaságot és dense mátrixot eredményez — nagy memóriaigénnyel. A TruncatedSVD közvetlenül a sparse mátrixon dolgozik.

**Eredmények:**

| Komponensek | Megőrzött variancia | Macro F1 (LinearSVC) | Macro F1 (KNN-7) |
|-------------|--------------------|-----------------------|-------------------|
| 100 | 29.8% | 0.500 | 0.525 |
| 200 | 38.3% | 0.544 | 0.554 |
| 300 | 44.0% | 0.564 | 0.555 |

**Következtetések:**
- A dimenziócsökkentés jelentős teljesítménycsökkenést okoz: az eredeti TF-IDF-en a LinearSVC 0.598 Macro F1-et ért el, SVD-300-on csak 0.564-et
- A KNN SVD-200 mellett érte el a csúcsteljesítményét (0.554), SVD-300 felett már csökken
- A sparse TF-IDF feature-ök információtartalma nem tömöríthető veszteség nélkül
- A t-SNE vizualizáción látható, hogy az intent csoportok részlegesen szétválnak a redukált térben

### 6.2 Klaszterezés: K-Means feature engineering

A felügyelet nélküli tanulás (unsupervised learning) eredményeit kiegészítő feature-ként használtam a felügyelt modellek javítására.

**Lépések:**
1. SVD-redukált adaton K-Means futtatás (K-Means sparse mátrixon nem működik hatékonyan)
2. Elbow method + Silhouette score az optimális klaszterszámhoz
3. Klaszter ID (one-hot) + centroid-távolságok mint új feature-ök
4. Eredeti TF-IDF + klaszter feature-ök kombinálása

**Eredmények (LinearSVC, k=20):**

| Konfiguráció | Macro F1 | Változás |
|--------------|----------|----------|
| TF-IDF only (baseline) | 0.598 | — |
| TF-IDF + klaszter ID + centroid-távolság (k=20) | 0.596 | -0.002 |

A klaszter-feature-ök gyakorlatilag nem javítottak. Ez azt jelzi, hogy a TF-IDF feature-ök már lefedik azt az információt, amit a klaszterek hozzáadnának. A t-SNE vizualizáción a klaszterek részlegesen korrelálnak az intent csoportokkal, de nem 1:1 megfelelés.

### 6.3 Hiperparaméter optimalizálás: Optuna

3 fázisú Optuna optimalizálást végeztem:

**1. fázis: TPE (Tree-structured Parzen Estimator)**
- Bayesi optimalizálás a globális keresési tér feltérképezéséhez
- `suggest_categorical` diszkrét gridek a gyorsabb konvergenciáért

**2. fázis: NSGA-II (multi-objective)**
- Pareto-optimális megoldások keresése (F1 vs. futásidő)

**3. fázis: Finomhangolás**
- A legjobb régió körüli szűk keresés

**Optimalizált modellek:**

| Modell | Macro F1 | Megjegyzés |
|--------|----------|------------|
| LinearSVC (Optuna) | 0.619 | Az Optuna C paramétere javított az alap 1.0-hoz képest |
| LogReg (Optuna) | 0.603 | Marginális javulás a baseline-hoz képest |
| LightGBM (Optuna) | 0.595 | A teljes TF-IDF adaton, nem SVD-n |

A `suggest_categorical` diszkrét gridek használata gyorsabb konvergenciát biztosított a folytonos kereséshez képest.

---

## 7. Végleges modell és metrikák

### 7.1 Modellválasztás

A **CalibratedClassifierCV(LinearSVC)** lett a végleges modell, az Optuna-optimalizált C paraméterrel.

Választási szempontok:
1. **Macro F1:** 0.618 — a 0.60 célérték felett
2. **Inference sebesség:** <1ms per predikció (lineáris kernel)
3. **Valószínűségi kimenet:** a CalibratedClassifierCV biztosítja a `predict_proba()` képességet (confidence score, top-3 alternatívák)
4. **Generalizáció:** mérsékelt train-test gap

A CalibratedClassifierCV a LinearSVC-t Platt-scaling-gel egészíti ki, hogy `predict_proba()` is elérhető legyen. A kalibráció mellékhatásaként a generalizáció is javul a belső cross-validation révén.

### 7.2 Végleges metrikák

| Metrika | Érték |
|---------|-------|
| **Macro F1** | **0.618** |
| Test Accuracy | 0.686 |
| Weighted F1 | 0.685 |

### 7.3 Per-class teljesítmény

| Routing csoport | Precision | Recall | F1 | Support |
|----------------|-----------|--------|----|---------|
| credit_report_accuracy | 0.70 | 0.80 | 0.75 | ~3 200 |
| identity_theft_unauthorized | 0.75 | 0.72 | 0.73 | ~1 850 |
| debt_collection_practice | 0.69 | 0.74 | 0.71 | ~1 000 |
| card_purchase_disputes | 0.67 | 0.78 | 0.72 | ~520 |
| account_management | 0.63 | 0.71 | 0.67 | ~400 |
| mortgage_loan_servicing | 0.65 | 0.64 | 0.64 | ~310 |
| investigation_escalation | 0.70 | 0.58 | 0.63 | ~1 600 |
| credit_monitoring_access | 0.73 | 0.40 | 0.52 | ~140 |
| payment_issues | 0.57 | 0.46 | 0.51 | ~250 |
| loan_lease_management | 0.54 | 0.37 | 0.44 | ~120 |

### 7.4 Confusion Matrix megfigyelések

A legjelentősebb összetévesztési minták:
- **credit_report_accuracy ↔ investigation_escalation:** mindkettő hiteljelentés-vitatáshoz kapcsolódik, a különbség az, hogy az előbbi az adathibáról, az utóbbi a vizsgálat folyamatáról szól
- **identity_theft_unauthorized ↔ credit_monitoring_access:** a fraud és a fraud prevention tematikusan közel áll
- **payment_issues ↔ account_management:** a fizetési és számlakezelési problémák gyakran egybefolynak
- **loan_lease_management:** legalacsonyabb recall (0.37) és kis mintaszám (~120) — a modell sok hitel/lízing panaszt más csoportba sorol

### 7.5 18 kísérleti konfiguráció összehasonlítása

Az összes kísérlet eredménye összesítő táblázatban és vizualizációban is elérhető (`output/results/all_experiments.csv`, `output/figures/all_experiments_comparison.png`). A 18 konfiguráció a 7 baseline modellt, 3 Optuna-optimalizált változatot, 6 SVD+KNN/LinearSVC variánst, és a KMeans feature engineering-et foglalja magában.

---

## 8. Kihívások és limitációk

### 8.1 Class imbalance

A legnagyobb kihívás az erős class imbalance volt. A `credit_report_accuracy` csoport az összes minta ~32%-át adja, míg a `credit_monitoring_access` és `loan_lease_management` csoportok egyenként alig ~1%-ot. A `class_weight='balanced'` és a Macro F1 metrika használata enyhíti a problémát, de a nagyon kis csoportok (< 500 minta) predikciós megbízhatósága alacsonyabb marad.

### 8.2 Hasonló intent-ek összetévesztése

Néhány routing csoport tematikusan közel áll egymáshoz:
- **Hiteljelentés pontossága** vs. **Vizsgálat/Escalation:** mindkettő hiteljelentés-problémához kapcsolódik
- **Személyazonosság-lopás** vs. **Kredit monitoring:** a fraud és a fraud prevention átfed
- **Fizetési problémák** vs. **Számlakezelés:** sok panasz mindkettőre vonatkozik

Ez az összetévesztés inherens a feladat természetében és teljesen nem küszöbölhető ki — az üzleti kategóriák sem diszjunktak.

### 8.3 Sparse mátrix kezelés

A TF-IDF mátrix ritka (sparse) jellegéből több technikai korlát adódik:
- **PCA nem használható:** centralizáció megszünteti a ritkaságot → TruncatedSVD szükséges
- **KNN nem hatékony:** high-dimenziós sparse adaton a távolságmetrikák nem informatívak → dimenziócsökkentés kell előtte
- **Egyes ensemble modellek lassúak:** a RandomForest és a fa-alapú modellek nem optimálisak sparse adaton

### 8.4 Fejlesztési folyamat — tanulságok

1. **scikit-learn 1.8 API változások:** A `LogisticRegression` `multi_class='multinomial'` paramétere és a `TSNE` `n_iter` neve megváltozott — érdemes mindig ellenőrizni a library verziót.

2. **Futásidő-kezelés:** A 7 modell tanítása a 40 000×10 000 sparse mátrixon jelentős számítási igényű. Az Optuna-hoz almintát, a boosting modellekhez csökkentett estimátorszámot használtam.

### 8.5 TF-IDF korlátai és az LLM-alapú megközelítés kérdése

A TF-IDF bag-of-words alapú: nem ragadja meg a szekvenciális kontextust. A "The company did NOT resolve my issue" és "The company resolved my issue" nagyon hasonló TF-IDF vektort kap — a negáció, az irónia és az összetett mondatszerkezetek elvesznek.

Érdemes felvetni — a projekt keretein kívül —, hogy a szöveges tartalom alapú intent felismerés és routing támogatás ma már **LLM-ek (Large Language Models) segítségével is megoldható**, és bizonyos szempontból hatékonyabb lehet:

Ebben a kérdésben örülnék az oktató visszajelzésének is — milyen tapasztalatai vannak az LLM-alapú klasszifikáció és routing terén, és mit javasolna a továbbfejlesztéshez?

---

## 9. Hallgatói értékelés

### 9.1 Mit tanultam a projekt során?

A CRISP-DM módszertant végig tudtam követni az üzleti megértéstől az API deployment-ig. A legfontosabb tanulságok:

- **TruncatedSVD vs. PCA:** Sparse mátrixon a PCA nem járható, mert a centralizáció megszünteti a ritkaságot. A TruncatedSVD a helyes választás.
- **Lineáris modellek ereje:** A LinearSVC és LogisticRegression meglepően jól teljesít szövegklasszifikációnál — a TF-IDF + lineáris kombináció gyors és alig marad el a boosting modellektől.
- **Class imbalance kezelés:** A `class_weight='balanced'` és a Macro F1 metrika nélkül a kisebb csoportok teljesítménye láthatatlan marad — az accuracy önmagában félrevezető.
- **Optuna:** A bayesi hiperparaméter-optimalizálás hatékonyabb a grid/random search-nél, de fontos a teljes feature-halmazon futtatni.

### 9.2 Továbbfejlesztési tervek

A következő lépésként kipróbálom, hogy **LLM-ek hívásával** hogyan lehetne a routing rendszert tovább optimalizálni és valós működő környezet számára használhatóvá tenni. A 8.5 szekcióban részletezett LLM-alapú megközelítés ígéretes irány a jelenlegi TF-IDF-alapú pipeline továbbfejlesztésére.

### 9.3 Felhasznált eszközök

A projektet Claude Code (Anthropic) segítségével fejlesztettem. Az AI eszközt a kódgenerálás és hibakeresés támogatására használtam. Minden eredményt a notebook futtatásával és a tesztek futtatásával validáltam.

---

## 10. Futtatási instrukciók

### 10.1 Környezet beállítása

**Előfeltételek:** Python 3.11+ (tesztelve: 3.12.3)

```bash
cd "01_cfpb_complaints"
python -m venv venv
source venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

### 10.2 Modell tanítás

```bash
python src/pipeline.py train
```

Kimenet:
- `models/intent_routing_model.joblib` — mentett pipeline
- `models/model_metadata.json` — metaadatok (accuracy, F1, routing csoportok)

### 10.3 Predikciók

```bash
# Egyedi predikció
python src/pipeline.py predict "I found incorrect information on my credit report"

# Predikció valószínűségekkel
python src/pipeline.py predict_proba "Someone opened a credit card in my name"
```

### 10.4 Tesztek

```bash
pytest src/test_pipeline.py -v
```

32 teszt eset: `clean_text`, `intent_mapping`, `pipeline build/predict`, `model save/load`, `predict_proba`, `routing`, `data_integration`.

### 10.5 API indítása

```bash
uvicorn src.api:app --port 8000 --reload
```

| Metódus | URL | Leírás |
|---------|-----|--------|
| GET | `/health` | Rendszer állapot |
| POST | `/route` | Egyedi panasz routing |
| POST | `/route/batch` | Kötegelt routing (max 100) |
| GET | `/routing-groups` | Routing csoportok listája |

API screenshotok: `docs/api_screenshots/`

### 10.6 Jupyter Notebook

```bash
jupyter notebook notebook/cfpb_intent_routing.ipynb
```

### 10.7 Mappastruktúra

```
01_cfpb_complaints/
  requirements.txt                   # Python függőségek
  complaints_sample_50k.csv          # 50k minta adathalmaz
  notebook/
    cfpb_intent_routing.ipynb        # Jupyter notebook (futtatott)
  src/
    pipeline.py                      # Train-inference pipeline
    api.py                           # FastAPI REST API
    test_pipeline.py                 # Pytest tesztek (32 db)
  models/
    intent_routing_model.joblib      # Mentett pipeline
    model_metadata.json              # Modell metaadatok
  docs/
    documentation.md                 # Ez a dokumentum
    api_screenshots/                 # API Swagger UI screenshotok
  output/
    figures/                         # Vizualizációk (*.png)
    results/                         # Eredmény CSV-k
```

---

*Készült: 2026. március — Cubix ML Engineering kurzus, Pilot feladat*
