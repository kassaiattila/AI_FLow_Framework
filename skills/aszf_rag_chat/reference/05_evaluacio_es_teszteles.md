# Evaluacio es Teszteles

## Gyors Attekintes

> Az LLM es **RAG** rendszerek **evaluation**-je -- azaz ertekeloese -- ellengedhetetlen a megbizhato AI alkalmazasok fejlesztesehez. Az **evaluation** nem garantalja a teljesitmenyt, hanem elsodlegesen **hibakereso eszkoz**, amely segit felderiteni, hol teljesit rosszul a rendszer, es milyen iranyba erdemes fejleszteni. A meres harom szinten tortenik: **RAG** (retrieval minoseg), **single-turn** (prompt szintu valaszminoseg), es **multi-turn** (teljes beszelgetes szintu ertekeloes), mikozben mind **automatikus**, mind **emberi** ertekelesre szukseg van a megbizhato kep kialakulasahoz.

---

## Kulcsfogalmak

| Fogalom | Jelentes |
|---------|---------|
| **Evaluation** | Az AI modell vagy rendszer teljesitmenyenek meroseert es ertekelese kulonbozo **metrikak** es tesztek segitsegevel |
| **Metric** | Mennyisegi mutato, amely a rendszer egy adott jellemzojet meri (pl. **precision**, **relevance**) |
| **Ground truth** | Az elore meghatarozott helyes valasz vagy referencia, amelyhez a generalt valaszt hasonlitjuk |
| **LLM-as-Judge** | Olyan megkozelites, ahol egy **nagy nyelvi modell** ertekel egy masik modell altal generalt valaszt |
| **Faithfulness** | A generalt valasz husege a megadott **kontextushoz** -- nem tartalmaz kitalalt informaciot |
| **Relevance** | A valasz mennyire illeszkedik a felhasznalo kerdosehez es a tema targyahoz |
| **Coherence** | A generalt szoveg osszefuggosege, logikai konzisztenciaja es olvashatos aga |
| **Single-turn evaluation** | Egyetlen kerdes-valasz par ertekelese adott **dataset** alapjan |
| **Multi-turn evaluation** | Tobbkoros beszelgetes ertekelese, amely a teljes interakcio minoseg t vizsgalja |
| **RAG evaluation** | A **retrieval** (kereses) es **generation** (generalas) egyuttes minoseg enek mereve |
| **Retrieval quality** | A keresesi pipeline minosege: a visszaadott dokumentumok mennyire relevansak |
| **Generation quality** | A valaszgeneralas minosege: pontossag, relevancia, huseg a kontextushoz |
| **A/B testing** | Ket valtozat osszehasonlitasa kontrollalt korulmenyek kozott statisztikai szignifikanciaval |
| **Human evaluation** | Emberi ertekelok altal vegzett minoseg ertek les -- a legmegbizhatos abb, de a legdragabb modszer |
| **Online evaluation** | Valos felhasznaloi adatokon torteno ertekeloes valos idoben, monitorozas jellegu |
| **Offline evaluation** | Elore osszealitott **golden dataset**-en torteno ertekeloes, reprodukalhat a korulmenyek kozott |
| **Braintrust** | Evaluacios platform, amely tamogatja az AI alkalmazasok online es offline teszteleset, **scoring rule**-ok beallitasat |
| **Golden dataset** | Emberileg kuralt, elore elkeszitett kerdes-valasz parokat tartalmazo referencia adatallomany |
| **Precision** | A visszaadott talalatok kozul a tenylegesen relevans talalatok aranya |
| **Recall** | Az osszes relevans talalt kozul a rendszer altal visszaadottak aranya |
| **Policy matrix** | Az ertekelesek soran hasznalt szcenariok, adatallomanyok es szabalyok rendszere |
| **Scoring rule** | Szabaly, amely meghatarozza, milyen **metrikak** es pontozasi logika fut le az evaluacio soran |
| **Customer Council** | Az elso felhasznalok csoportja, akiktol azonnali visszajelzeseket kerunk a fejlesztes soran |

---

## Mit es Hogyan Merjunk?

### Az Evaluacio Celja

Az **evaluation** eredete a klasszikus **machine learning**-bol szarmazik: egy betanitott modellt olyan adaton teszteltek, ami nem volt benne a tanitohalmazban, ezzel becsiltek a **generalizalo kepesseget**. Ez a megkozelites lehetove tette:

- kulonbozo modellek osszehasonlitasat
- a **tultanitas** (**overfitting**) es **alultanitas** (**underfitting**) felfedezeset
- az adott feladatra legalkalmassabb modell kivalasztasat

> **Fontos**: Az evaluacio **nem ad garanciat** a teljesitmenyre. A teljesitmeny explicit definialasa is nehez. Az evaluacio tulajdonkeppen egy **hibakereso eszkoz** fejlesztok szamara.

A gyakorlati cel ketto:

1. **Kiadas elott**: kepet kapni arrol, hogy a rendszer a celfeladatot kiprob alt szcenariokban meg tudja oldani -- igy csokken annak eselye, hogy a felhasznalok hasznalhat lannak talalja az alkalmazast
2. **Kiadas utan**: megtalalani azokat a szcenariokat, ahol az AI rosszul teljesit, es ezeket fejleszteni

### Meresi Szintek (RAG, Single-turn, Multi-turn)

Az evaluacionak harom szintje van, amelyek kulonbozo komplexitast es hibakeresi lehetsoeget adnak:

```
                        EVALUACIOS SZINTEK
========================================================================

1. RAG SZINT              2. PROMPT SZINT          3. APPLIKACIO SZINT
(Retrieval minoseg)       (Single-turn)            (Multi-turn)
+------------------+      +------------------+     +------------------+
| VectorDB kereses |      | Valasz minoseg   |     | Teljes beszelges |
| Precision/Recall |      | Correctness      |     | Goal achievement |
| Chunk relevancia |      | Relevance        |     | Guardrails       |
| Re-rank minoseg  |      | Faithfulness     |     | Brand protection |
+------------------+      +------------------+     +------------------+
        |                         |                         |
        v                         v                         v
   Retrieval               Prompt/LLM                Rendszer szint
   pipeline debug          optimalizalas             end-to-end teszt
```

**1. RAG szint** -- a **vector adatbazisbol** keresi a dokumentum **chunk**-okat, es azok josagat meri. Azt vizsgalja, hogy a kereses mennyire relevans dokumentumokat ad vissza.

**2. Prompt szint (single-turn)** -- azt vizsgalja, hogyan hasznalija az LLM az elokerult chunkokat, es hogyan kezeli a felhasznaloi kerest. Egyetlen kerdes-valasz part ertekel.

**3. Applikacio szint (multi-turn)** -- a teljes beszelgetes es alkalmazas mukodesenet vizsgalja. Itt tesztelenok a **guardrail**-ek, a **brand protection**, es a tobb koros interakcio minosege.

> **Gyakorlati tapasztalat**: Ha a modell jol teljesit adott **dataset**-eken, de a modul rosszul, akkor **integracios problema** lehet. Ezert erdemes mindharom szinten merni.

### Usefulness, Accuracy, Consistency

Az ertekeleskor harom fo dimenziót vizsgalunk:

| Dimenzio | Kerdes | Pelda metrika |
|----------|--------|---------------|
| **Usefulness** | Hasznos-e a valasz a felhasznalonak? | Relevance score, goal achievement |
| **Accuracy** | Helyes-e a valasz tartalmilag? | Correctness, faithfulness |
| **Consistency** | Kovetkezetes-e a rendszer viselkedese? | Valaszok varianciaja, ismeteelt kerdesek ertekelese |

---

## RAG Szintu Meres

### Retrieval Minoseg (Precision, Recall)

A **RAG** szinten a ket legfontosabb **metrika** a **Precision** es a **Recall**:

```
               RAG RETRIEVAL METRIKAK
=========================================================

     Osszes dokumentum az adatbazisban
     +--------------------------------------------+
     |                                            |
     |    Relevans dokumentumok  Visszaadott dok.  |
     |    +------------------+  +--------------+  |
     |    |                  |  |              |  |
     |    |   TRUE POSITIVE  |  |  FALSE       |  |
     |    |   (relevans ES   |  |  POSITIVE    |  |
     |    |    visszaadott)  |  |  (nem relev. |  |
     |    |                  |  |   de vissza-  |  |
     |    +------------------+  |   adott)      |  |
     |                          +--------------+  |
     |    FALSE NEGATIVE                          |
     |    (relevans de NEM visszaadott)            |
     +--------------------------------------------+

Precision = TP / (TP + FP)   -- "Ami visszajott, abbol mennyi volt relevans?"
Recall    = TP / (TP + FN)   -- "Az osszes relevansbol mennyit talalt meg?"
```

**Precision**: amit a **retrieval pipeline** visszaadott dokumentum-csomagoknak mekkora resze az, amit tenylegesen vissza kellett adnia. Idealis erteke 100%.

**Recall**: a relevans dokumentumok kozul mennyit sikerult megtalalni. Ha nincs benne fontos informacio, a valasz sem lesz jo.

> **Megjegyes**: Ha csak egy **chunk**-hoz generalunk egy **user query**-t es nincs mod eldonteni, tobb chunk is relevans-e, akkor a precision es recall egybeeshet. Ilyenkor egyetlen **metrikat** hasznalunk: a relevans chunk bekerult-e a TOP-k talalatba.

### Generation Minoseg (Faithfulness, Relevance)

A **generation** minoseg a generalt valasz tartalmat ertekeli:

| Metrika | Mit mer | Hogyan |
|---------|---------|--------|
| **Faithfulness** | A valasz husege a megadott kontextushoz | Nem tartalmaz-e olyat, ami nincs a chunk-okban |
| **Relevance** | A valasz mennyire valaszolja meg a kerdest | A kerdes es a valasz osszefuggese |
| **Correctness** | A valasz tartalmi helyessege | Osszehasonlitas a **ground truth**-szal |

### Context Relevance

A **context relevance** azt meri, hogy a keresesi pipeline altal visszaadott dokumentum chunk-ok mennyire relevansak a felhasznalo kerdesehez. Ez kulonbozik a valasz relevanciajatol:

- **Context relevance**: a *bemeneti* chunk-ok minosege
- **Answer relevance**: a *kimeneti* valasz minosege

Ha a context relevance alacsony, a generation sem tud jo valaszt adni, meg ha az LLM tokeletes is.

---

## LLM as Judge

### Koncepcio

Az **LLM-as-Judge** az evaluacios modul egyik legfontosabb resze. A lenyeg: irunk egy olyan **prompt**-ot, ami megprobal valamilyen valaszt adni arra, mennyire jo valamilyen aspektusbol a generalt valasz.

Tipikus ertekelesiszempontok:

- **Correctness** -- tartalmi helyesseg
- **Politeness** -- udvariassag
- **Tone** -- hangnem
- **Hallucination** -- hallucinacio vizsgalat
- **Relevance** -- relevancia

### Ertekelesiskalaiak

A kovetkez oskalak hasznalatosak:

| Skala | Leiras | Elony | Hatrany |
|-------|--------|-------|---------|
| **Folytonos (0.0-1.0)** | Pl. 0.75 = 75%-ban relevans | Finom granuralitas | Nehezen interpretalhato, LLM-ek nem konzisztensek |
| **Binaris (0/1)** | Jo vagy nem jo | Egyszeru, egzertelmu | Nincs arnyalat |
| **0-3 egesz** | 0-1 rossz, 2-3 jo | Paaros kategoriak -- az LLM-nek valasztania kell | Jo egyensuly reszletesseg es konzisztencia kozott |

> **Ajanlott**: A 0-tol 3-ig terjedo skala, mert paros szamu kategoria van, igy az LLM-nek valasztania kell, hogy jobb vagy rosszabb valaszrol van-e szo, es azon belul is meg kell hataroznia a fokozatot.

### Implementacio

Az **LLM-as-Judge** implementacio fo elemei:

```
LLM-AS-JUDGE PIPELINE
============================================================

1. INPUT OSSZEALLITAS
   +------------------+
   | User query       |
   | Generalt valasz   |
   | Ground truth     |  (ha offline)
   | Context chunks   |  (ha RAG eval)
   +------------------+
           |
           v
2. JUDGE PROMPT
   +----------------------------------+
   | "Ertekeld a valaszt 0-3 skalan  |
   |  az alabbi szempontok szerint:   |
   |  - Correctness                   |
   |  - Relevance                     |
   |  Adj indoklast is."              |
   +----------------------------------+
           |
           v
3. JUDGE LLM HIVAS
   +----------------------------------+
   | GPT-4 / GPT-5 / Claude          |
   | (erosebb modell mint a generalo) |
   +----------------------------------+
           |
           v
4. EREDMENY PARSZOLAS
   +----------------------------------+
   | score: 2                         |
   | reasoning: "A valasz helyes..."  |
   +----------------------------------+
```

**Fontos elvek:**

- Mindig kerjunk **indoklast** (**reasoning**) is a pontozas melle -- ez segit a kesobbi hibakeresesben
- Az ertekelest lehetoleg **erosebb modellel** vegezzuk, mint amit ertekelunk (pl. GPT-5-tel ertekelunk GPT-3.5-ot)
- Gyengebb modellek hasznalata **koltseghatekonyag i** megfontolasbol is elofordulhat

### Korlatok es Torzitasok

Az **LLM-as-Judge** megkozelitesnek vannak korl tai:

1. **Pozicio torzitas**: Az LLM hajlamos az elso vagy utolso opcion magasabb pontszamot adni
2. **Hossztorzitas**: A hosszabb valaszokat hajlamos jobban ertekeln, fuggetlen ul a tartalomtol
3. **Onertekeles torzitas**: Ha ugyanaz a modell generaija es ertekeli, hajlamos magsra ertkelni
4. **Stilus preferencia**: Az LLM-ek hajlamosak a sajat stilusukat elonyben reszesiteni

> **Ajnlas**: Soha ne bizzunk kizarolag az automatikus evaluacioban. Az **emberi felulvizsgalat** elengedhetetlen, kuln os en kisebb **golden dataset**-ek eseten.

---

## Evaluacio Implementalasa

### RAG Evaluacio Kod

A **RAG** szintu evaluacio implementacioja a kovetkezo lepesekbol all:

**1. Dokumentum chunk-okbol user query generalas**

A prompttal a dokumentum chunk-okbol generalunk **user query**-ket, amelyek viszonylag rovidek es realisztikusnak tunnek. A generalshoz erdemes gyengebb/olcsobb modellt hasznalni (pl. GPT-4o-mini).

**2. Kereses es ellenorzes**

Az evaluacio soran megnezzuk, hany szazalekban sikerul a TOP-k talalat kozot visszakapni azt a chunk-ot, amelybol a user query szarmazik.

**3. Naplozas**

Minden mintat reszletesen naplounk: milyen query keszult, melyik chunk-bol, es milyen talalatok erkeztek vissza. Ez segit a hibakeresesben.

```
RAG EVALUATION FOLYMAAT
==========================================================

Minden chunk-ra:
  1. Generaij user query-t a chunk tartalmabol (LLM)
  2. Keresi a VectorDB-ben a generalt query-vel
  3. Ellenorizd: az eredeti chunk benne van-e a TOP-k-ban
  4. Naploazd az eredmenyt (query, chunk, talalatok)

Aggregalt eredmenyek:
  - Precision, Recall, F1-score
  - (ha nincs re-rank: precision = recall)
```

> **Tapasztalat**: A kurzusban ~90%-os pontossagot mertek, azaz a chunk-ok 90%-anal sikerult visszakeresni az eredeti chunk-ot. Ha a pipeline tartalmazna **re-rank**-ot, tovabbi metrikakat is lehetne definialni (pl. hanyadik helyen ter vissza a relevans chunk).

### Single-turn Evaluacio

A **single-turn** evaluacio az AI asszisztens valaszait vizsgalja egyetlen kerdes-valasz szinten:

**1. Generate Response** -- egyszeruu **system prompt**-tal mukodik, a user prompt tartalmazza a tenyleges keresdt es a RAG pipeline altal visszateritett chunk-okat.

**2. Golden dataset keszitese** -- nem chunk-onkent, hanem a teljes dokumentum markdown fajljain alapul. Minden fajlhoz 3 kerdest generalunk, amelyek megvalszolhatoak az adott fajl alapjan. JSON formatumban taroljuk: fajl nev, tartalom, kerdesek, helyes valaszok (**ground truth**).

**3. Ertekeles** -- ket fo dimenzioban:
- **Correctness**: a generalt valasz helyes-e a ground truth-hoz kepest
- **Relevance**: a valasz mennyire relevans a kerdesre

**4. Judge prompt** -- osszehasonlitja a generalt valaszt es a ground truth-ot, ker egy indoklast es egy dontest.

| Lepes | Bemenet | Kimenet |
|-------|---------|---------|
| Query kivalasztas | Golden dataset kerdesei | User query |
| RAG pipeline | User query | Relevans chunk-ok |
| Valasz generalas | Query + chunk-ok + system prompt | Generalt valasz |
| Judge ertekeles | Generalt valasz + ground truth | Score + indoklas |
| Aggregalas | Egyedi eredmenyek | Accuracy, relevance rate |

### Golden Dataset Keszites

A **golden dataset** a legfontosabb referenciaallomany az evaluaiciohoz:

**Jellemzoi:**
- Emberileg **kuralt** es **review**-zott
- Tartalmaz **elvart output**-ot (**baseline**)
- Idoeben kevesbe valtozik -- lehetove teszi az osszehasonlitast korabbi futtatsa okkal
- A **policy matrix**-hoz viszonyitva tobb **policy**-bol osszeallitott kivasltott mintakat tartalmaz

**Generalas lepesei:**

1. Osszegyujtjuk a forras dokumentumokat (markdown fajlok, PDF-ek)
2. Erosebb modellel (pl. GPT-5) generalunk kerdeseket dokumentumonkent (tipikusan 3 kerdest)
3. Ugyanez a modell generalja a helyes valaszokat (**ground truth**)
4. Emberi felulvizsgalat -- kikuloonoosen a kulcskerdeseknel
5. JSON formatumba mentjuk: `{fajlnev, tartalom, kerdesek, valaszok}`

> **Tipp**: A golden dataset minosege kritikus -- erdemes **erosebb modelleket** hasznalni a generalsahoz, es mindig vegezzunk emberi felulvizsalatot.

---

## Online vs Offline Evaluacio

### Offline Evaluacio

Az **offline evaluation** elore osszealitott **golden dataset**-en tortenik, kontrollalt korulmenyek kozott:

**Elonyok:**
- Reprodukalhato eredmenyek
- Idoeben osszehasonlithato (pl. ket hettel ezelotti teljesitmeny)
- Nincs szukseg valos felhasznaloi adatokra

**Haszanlat:**
- Fejlesztes soran rendszeres futtatsa (pl. napi / heti)
- Uj prompt valtozat tesztelese kiadas elott
- **Batch API** hasznalata -- az OpenAI batch API-val egyszerre sok kerest kuldhetunk, a valasz akar 24 oran belul erkezik, es altalaban olcsobb

### Online Evaluacio

Az **online evaluation** valos idoben fut a tenyleges felhasznaloi kerdesekkel:

**Jellemzoi:**
- Valos **user** adatokon tortenik monitorozas
- Nincs **golden truth** -- de pl. a relevanciait meg tudjuk kerdezni az ertekelotol
- Ha idoben szignifikans teljesitmenycsokkenest eszelleunk, ertesitest kuldhetunk a fejleszto csapatnak
- **Mintavetelezesi rata** alapjan mukodik (pl. 10% vagy 100% a budzsettol fuggoen)

### Braintrust Integracio

A **Braintrust** egy evaluacios platform, amely tamogatja mind az online, mind az offline tesztelest:

**Hasznalat:**
1. Az **AI SDK** beepitett Brain Trust kompatibilis automatikus logolast nyujt
2. A **chat endpoint**-nal bekapcsoljuk az **experimental telemetria**-t
3. Minden AI hivas automatikusan kiment oedik

**Scoring rule-ok beallitasa:**
- Megadjuk a pontozot (pl. **relevance**)
- Beallitjuk a **sampling rate**-et (pl. 100% vagy 20%)
- Megadjuk, melyik **span** tipusra fusson le a pontozo
- A pontozo metadata-t is kap, lehetove tevi **counter label**-ek beallitasat

```
BRAINTRUST INTEGRACIOS FLOW
============================================================

1. AI SDK telemetria bekapcsolasa
   +---> Automatikus logolas minden LLM hivashoz

2. Scoring rule definialas
   +---> Pontozo (pl. Relevance)
   +---> Sampling rate (10-100%)
   +---> Span tipus (pl. get_information)

3. Online scoring futtatasa
   +---> LLM Judge automatikusan ertekel
   +---> Eredmenyek megjelenitese tablazatban

4. Egyeni pontozok (Python / TypeScript)
   +---> Determinisztikus pontozok is irhatoak
   +---> Sajat logika implementalasa
```

> **Pelda**: Egy tesztnel, ahol a kerdes a kedvenc szin volt, a rendszer 0%-os relevanciiat adott, mert a valasz a kedvenc szamot tartalmazta. Ez jol mutatja a scoring rule-ok mukosdeset.

### Feedback Pipeline

A felhasznaloi visszajelzesek gyujtesenek es felhasznalasanak folyamata:

```
FEEDBACK PIPELINE
============================================================

Valos felhasznalok      Tesztfelhasznalok       Szimulalt felhasznalok
+----------------+      +----------------+      +------------------+
| Interjuk       |      | Belso csapat   |      | LLM szimulacio   |
| Like/Dislike   |      | Customer       |      | Param. persona   |
| Szoveges komm. |      | Council        |      | Random attributum|
+----------------+      +----------------+      +------------------+
        |                       |                        |
        v                       v                        v
+------------------------------------------------------------+
|              AGGREGALT FEEDBACK ADATBAZIS                   |
|  -> Golden dataset bovitese                                |
|  -> Problemas esetek azonositasa                           |
|  -> Metrika trendek monitorozasa                           |
+------------------------------------------------------------+
```

---

## Automatikus vs Emberi Ertekeles

### Visszajelzesek Forrasai

A visszajelzesek harom forrasbol szarmazhatnak:

**1. Valos felhasznalok:**
- Interjuk (szabad formatum)
- **Customer Council** -- az elso nehany felhasznalo, akikkel kulonkonzultaalnak a fejlesztok, es azonnali visszajelzeseket kernek
- Like/dislike -- lehetuzeneteenkent vagy teljes beszelgetesre
- Szoveges kommentek

**2. Tesztfelhasznalok:**
- Altalaban a cegen belul dolgoznak a relevans domenben
- Kozvetlen kapcsolatban allnak a fejlesztokkel
- Specializalt **Customer Council**
- Meg kulon fejlesztett applikacio nelkul is el lehet kezdeni -- a legtobb evaluacios tool kinla egy felultet, ahol ki tudjak probalni a promptot

**3. Szimulalt felhasznalok:**
- LLM altal szimulalt felhasznalok, amelyek teljes beszelgeteseket szimulalnak
- Nagyon jo **skalazhat osag** -- temerekszer lefuttathatoak
- Parameterezheto **persona**: turelsmesseg (1-10), szakertelem, cel

### Mikor Melyiket?

| Modszer | Mikor | Elony | Hatrany |
|---------|-------|-------|---------|
| **Automatikus (LLM Judge)** | Fejlesztes soran, minden commit / release elott | Gyors, olcso, skalaz hato | Nem latja a "valos" felhasznaloi viselkedest |
| **Emberi (Customer Council)** | Elso release elott es utan rendszeresen | Valos insight-ok, prioritasok | Lassu, draga, nem skalaz hato |
| **Szimulalt felhasznalo** | Multi-turn teszteles, regresszios tesztek | Skalaz hato, automatizalhato | A szimulacios minoseg korlatozott |
| **Valos feedback (like/dislike)** | Produkcioban folyamatosan | Valos adat, valodi preferencia | Alacsony kitoltesi rata |

> **Kulcs tapasztalat**: Az automatikus evaluacio egy szukseges, de messze **nem elegseges** eszkozkeszlet. Mindig torekednunk kell arra, hogy a **valodi adatokbol**, a valodi felhasznaloktol nyerjunk visszajelzeseket. A legnagyobb veszely, hogy az automatikus evaluaciok hamis biztonsagi erzetet adhatnak.

### Hibrid Megkozelites

A legjobb eredmeny a hibrid megkozelitessel erheto el:

```
HIBRID EVALUACIOS STRATEGIA
============================================================

                    +-------------------+
                    | DEVELOPMENT FAZIS |
                    +-------------------+
                            |
              +-------------+-------------+
              v                           v
    +------------------+       +------------------+
    | Automatikus eval |       | Tesztfelhasznalok|
    | (Golden dataset) |       | (Prompt tesztel.)|
    | Napi/heti futtas |       | Heti/ketheti     |
    +------------------+       +------------------+
              |                           |
              +-------------+-------------+
                            |
                    +-------------------+
                    | RELEASE ELOTT     |
                    +-------------------+
                            |
              +-------------+-------------+
              v                           v
    +------------------+       +------------------+
    | Multi-turn szim. |       | Customer Council |
    | (Izolalt korny.) |       | (Beta testers)   |
    +------------------+       +------------------+
                            |
                    +-------------------+
                    | PRODUKCIO         |
                    +-------------------+
                            |
              +-------------+-------------+
              v                           v
    +------------------+       +------------------+
    | Online eval      |       | Valos feedback   |
    | (Braintrust)     |       | (Like/Dislike)   |
    | Sampling rate    |       | Szoveges komment |
    +------------------+       +------------------+
```

### Felhasznaloi Feedback Formatumok

Ha egyetlen feedback formatumot teszunk bele az AI applikacioban, az egy AI Assistant teren mindig legyen a **teljes beszelegetest visszajelzo formatum**:

- A beszelgetes vegen tegyunk fel egy **konkret kerdest** (pl. "Valaszt kaptal a kerdesedre?")
- Huyvelykujj felfelel / lefelel jel
- Plusz szoveges komment szekcio

> **Kerulendo**: Az altalanos "Tudasd velunk, jol csinaljuk-e" tipus kevesbe hatekony -- a felhasznalo nem tud jol reflektalni, es igazabol nem kapunk visszajelzest.

---

## A/B Teszteles

### Promptvaltozatok Osszehasonlitasa

Az **A/B teszteles** ket kulonbozo variaciot hasonlit ossze ugyanarra a celra:

1. Feltetelezzu, hogy a ketto **ugyanolyan jol** fog teljesiteni valamilyen **metrikaban**
2. Osszehasonlitjuk a ket variacio teljesitmenyet
3. Ha tul nagy elterest tapasztalunk, **elvetjuk a feltetelezest** (szignifikaans eredmeny)
4. Amelyik jobban teljesitett, annak valasztjuk

**Promptokra alkalmazva:**
- Irunk ket kulonbozo **system prompt**-ot
- Mindketto feltetelezeteten ugyanolyan relevans valaszokat biztosit
- Online **LLM Judge**-dzsal merjuk a relevanciat
- Megnezzuk, vajon az egyik jobban teljesitett-e

### Single-turn vs Multi-turn A/B Teszt

| Szempont | Single-turn | Multi-turn |
|----------|-------------|------------|
| **Mit mer** | Egy kerdes-valasz par | Teljes beszelgetes |
| **Eszkozok** | Legtobb tool tamogatja | Altalaban sajat implementacio kell |
| **Kihivas** | Egyszerubb, de kevesbe realisztikus | Komplexebb, de valos hasznalatot tukrozi |
| **Prompt kiosztsa** | Egyszerfu random | Figyelni kell, hogy a user ne kapjon vegyes promptokat |

> **Fontos**: Valos idoben, ha nem allitjuk be megfeleloen a prompt kiosztast, elofordulhat, hogy az egyik nap a felhasznalo megkapja az A system prompt-ot, de ket nap mulva folytaja a beszelgestet es B-t kap. Igy mar kevesbe tudjuk merni a hatekonysagot. **Utolag nem lehet javitani ezt a hibat.**

### Statisztikai Szignifikancia

A statisztikai szignifikancia meghatarozasahoz szukseges:

1. **Mintameret**: Elegendo keres szukseges ahhoz, hogy a kulonbseg nem a veletlen muve
2. **Szignifikancia szint**: Altalaban p < 0.05 (5%-os valoszinuseg, hogy a kulonbseg veletlen)
3. **Konfidencia intervallum**: Az eredmeny megbizhatosagi tartomanya

> **Gyakorlati pelda a kurzusbol**: Egy e-commerce (Shopify jellegu) platformon az A/B teszt setupja egy adott IP-nek egy adott nap random kisorsolta, melyik UI-t mutassa. Problema: egy ovatos felhasznalo egyik nap megnyitja az oldalt de nem vasarol, masnap ujra megllatogatja es mas UI-t lat. Az ilyen vegyes felhasznaloi **historik** nagy zajt jelentenek a meresben. A megoldas: also es felso becslest keszitenek az ilyen vegyes historik ertelmezesere. **Tanulsag**: az A/B teszteles **szkopjat** jol kell definialni.

---

## Multi-turn Evaluacio

### Szimulacio Felepitese

A **multi-turn** evaluacio soran teljes beszelgeteseket szimulalunk:

**Komponensek:**

1. **Personak** -- a szimulalt felhasznalo jellemzoi:
   - Description (leiras)
   - Parameterek (turkelmesseg, szakertelem, stb.)
   - Ezeket **random generatorral** szamitjuk ki, nem az LLM-re bizzuk

2. **Goalok** -- a beszelgetes celja:
   - Goal description (mit akar elerni)
   - Success criteria (mikor teljesul)
   - Max korok szama

3. **User response generalas** -- prompt, amely tartalmazza:
   - Eddigi beszelgetes reszei
   - Hanyadik kor
   - Goal progress (becsult ertek)
   - User turelmessge es szakertelme

4. **Simulation runner** -- a szimulacioes folyamat vezereloje

### Evaluacios Dimenziok

A multi-turn evaluacio kulonbozo dimenziok menten ertekel:

| Dimenzio | Mit vizsgal |
|----------|-------------|
| **Goal Achievement** | A kituzott cel teljesult-e (goal description + success criteria) |
| **Clarity** | A valaszok vilagossaga, erthetoseg (negyf le kategoria) |
| **User Satisfaction** | A szimulat felhasznalo elegdettsege (0-1 skala, szimulalt like) |
| **Turn Count** | Hany kor kellett a cel teljesitesehez |

### Izolalt Futtatas

Az izolalt szimulacios futtatas (**Isolated Simulation Runner**) **Docker Compose**-szal kulonallo kornyezetet futtat:

- Felhuz egy teljesen uj **VectorDB**-t es applikacioot
- Erre azert van szukseg, mert ha a beszelgetesekben valamit lement a memoria, az hatna a tobbi szimulalt beszelgetesre
- Minden evaluacioanak meg kell lennie izolalva

---

## Osszehasonlito Tablazat

### Evaluacios Modszerek Osszehasonlitasa

| Modszer | Szint | Automatizaltsag | Koltseg | Megbizhatosag | Skalazhatosag |
|---------|-------|-----------------|---------|---------------|---------------|
| **RAG Precision/Recall** | RAG | Teljes | Alacsony | Kozepes | Magas |
| **LLM-as-Judge (offline)** | Single-turn | Teljes | Kozepes | Kozepes | Magas |
| **LLM-as-Judge (online)** | Single-turn | Teljes | Kozepes-magas | Kozepes | Magas |
| **Golden dataset eval** | Single-turn | Teljes | Kozepes | Magas | Kozepes |
| **Multi-turn szimulacios** | Multi-turn | Teljes | Magas | Kozepes | Kozepes |
| **Customer Council** | Applikacio | Manualis | Magas | Magas | Alacsony |
| **Like/Dislike feedback** | Applikacio | Reszleges | Alacsony | Kozepes | Magas |
| **Braintrust online** | Applikacio | Teljes | Kozepes | Kozepes | Magas |
| **A/B teszt** | Applikacio | Reszleges | Magas | Magas | Kozepes |

### Metrikak Osszehasonlitasa

| Metrika | Alkalmazasi terulent | Meresi skala | Megjegyzes |
|---------|----------------------|-------------|------------|
| **Precision** | RAG retrieval | 0-100% | Visszaadott talalatok relevancia aranya |
| **Recall** | RAG retrieval | 0-100% | Relevans talalatok megtalalsai aranya |
| **F1-score** | RAG retrieval | 0-100% | Precision es Recall harmonikus atlaga |
| **Correctness** | Single-turn | 0-3 / binaris | Tartalmi helyesseg |
| **Relevance** | Single/Multi-turn | 0-3 / binaris | Valasz relevanci ja a kerdesre |
| **Faithfulness** | Single-turn | 0-3 / binaris | Huseg a kontextushoz |
| **Goal Achievement** | Multi-turn | 0-1 | Cel teljesulese a beszelgetesben |
| **Clarity** | Multi-turn | Kategorikus | Valaszok vilagossaga |

---

## Gyakorlati Utmutato

### Tipikus Evaluacios Kod Struktura

Egy evaluacios modul altalaban az alabbi komponensekbol all:

```
evaluacios_modul/
  |-- golden_dataset.json       # Kerdes-valasz parok (ground truth)
  |-- rag_evaluation.py         # Retrieval minoseg meres
  |-- single_turn_eval.py       # Egyedi valaszok ertekelese
  |-- multi_turn_simulation.py  # Teljes beszelgetes szimulacio
  |-- judge_prompts.py          # LLM-as-Judge prompt sablonok
  |-- report_generator.py       # Riport generalas
  |-- run_evaluation.py         # Fo futtato script
```

**RAG evaluacio pseudokod:**

```
minden chunk-ra:
    query = LLM.general_kerdest(chunk)
    talalatok = VectorDB.kereses(query, top_k=3)
    ha chunk BENNE VAN talalatok-ban:
        true_positive += 1
    total += 1

precision = true_positive / total
```

**Single-turn evaluacio pseudokod:**

```
minden kerdes-valasz par-ra a golden dataset-bol:
    chunks = VectorDB.kereses(kerdes)
    generalt_valasz = LLM.valasz(kerdes, chunks)
    correctness = Judge.ertekel(generalt_valasz, ground_truth)
    relevance = Judge.ertekel(generalt_valasz, kerdes)
    eredmenyek.append(correctness, relevance)

accuracy = jo_valaszok / osszes
```

**LLM-as-Judge prompt minta (0-3 skala):**

```
Te egy AI evaluator vagy. Ertekeld a valaszt tartalmi
helyesseg szempontjabol a ground truth alapjan.

Skala:
  0 = teljesen rossz
  1 = gyenge
  2 = nagyresztre jo
  3 = teljesen jo

Valaszolj JSON-ben:
  {"score": <0-3>, "reasoning": "<rovid indoklas>"}
```

> **Megjegyzes**: A 0-3 skala paros szamu kategoriakat hasznal, igy az LLM-nek dontenie kell, hogy inkabb jo vagy rossz a valasz -- nem tud kozepre menekuelni.

### Nem Tudom Valasz Kezelese

A kurzus kulon kiemeli a **"nem tudom" valasz** ertelmezesenek fontossag at. A metrikakat mindig az adott adatallomany kontextusaban kell ertelmezni:

| Kerdes tipusa | Elvart viselkedes | Megjegyzes |
|---------------|-------------------|------------|
| **In-scope** (a rendszer tudasaban van) | Erdemleges valasz | "Nem tudom" itt rossz kimenetel |
| **Out-of-scope** (nem celja valaszolni) | "Nem tudom" / visszautasitas | "Nem tudom" itt jo kimenetel |
| **Veszelyes** (guardrail trigger) | Visszautasitas | A guardrail-nek kell kezelnie |

> **Pelda**: Egy FAQ chatbotnal elvratjuk, hogy ne hallucinaljon. Ha nem tud jo valaszt adni, explicit mondja meg, hogy nem tudja. De ha egy in-scope kerdest kap es "nem tudom"-ot valaszol, az rossz kimenetel. Ezert **ellenttes erojel** van abban, hogy melyiket akarjuk -- es ezert szamit, milyen **dataset**-en ertelmezzuk a metrikat.

### Python Judge Gyakorlati Peldak

A LIVE alkalmon felmerult kerdes: mikor erdemes **Python script**-tel evalualni (nem LLM-mel)?

| Felhasznalasi eset | Python Judge logika |
|--------------------|---------------------|
| Generalt linkek letezesnek ellenorzese | HTTP request, statusz kod ellenorzes |
| Generalt kod szintaktikai helyessege | `compile()` vagy `exec()` futtatoknyezetben |
| Szamszeru eredmenyek validalasa | Regex parseolas + numerikus osszehasonlitas |
| Adott szavak/mintak jelenlete | String kereses, regex |
| Valasz formazas ellenorzese | Strukturalis parseolas (JSON, Markdown) |

> **Tapasztalat**: Ha az AI generalt linkeket, amelyek nem leteznek, az evaluacional kiszedik a linkeket es ellenorzik, hogy leteznek-e. Ha nem, visszadobjak az LLM-nek, hogy javitsa. Ez statisztikailag merheto es javithato.

### 1. Elso Lepesek -- Minimum Viable Evaluation

Ha epp most kezdunk egy AI projektet, a minimalis evaluacios setup:

1. **Golden dataset keszitese** (15-30 kerdes-valasz par)
2. **RAG precision meres** -- a chunk-ok megtalalhatok-e
3. **Correctness judge** -- egyszerfu LLM-as-Judge a valaszok helyessegere
4. **Like/dislike feedback** az applikacioban

### 2. Kozepes Erettsegu Evaluacio

Amikor mar vannak valos felhasznaloi adatok:

1. Bovitsuk a golden datasetet **valos problemas esetekkel**
2. Adjunk hozza **relevance** es **faithfulness** metrikakat
3. Allitsunk be **online evaluaciot** (Braintrust vagy sajat megoldas)
4. Rendszeres **heti** evaluacios futtats

### 3. Erett Evaluacios Pipeline

Teljes korfu evaluacio:

1. **Multi-turn szimulacio** izolalt kornyezetben
2. **A/B teszteles** uj prompt valtozatokra
3. **Customer Council** rendszeres egyeztetesekkel
4. **Automatikus riasztasok** teljesitmenycsokkeneskor
5. **Batch API** hasznalata a koltsegek optimalizalasara

### Evaluacios Ciklus

```
EVALUACIOS CIKLUS
============================================================

1. Fejlesztes   --> 2. Offline eval   --> 3. Review
      ^                                       |
      |                                       v
6. Javitas  <-- 5. Problema azonositas <-- 4. Release
      |                                       |
      v                                       v
7. Uj eval   --> 8. Online monitoring --> 9. Feedback
                                               |
                                               v
                                     10. Golden dataset
                                         bovitese
```

---

## Gyakori Hibak es Tippek

### Hibak

| Hiba | Kovetkezmeny | Megoldas |
|------|-------------|---------|
| Csak automatikus evaluaciora tamaszkodni | Hamis biztonsagi erzet | Kombina juk emberi visszajelzessel |
| Gyenge modellel ertekelni erso modellt | Pontatlan scoring | Mindig erosebb modellt hasznaljunk judge-nak |
| Golden dataset neklul evalualni | Nem reprodukalhato eredmenyek | Keszitsunk es tartsunk karban golden datasetet |
| A/B tesztnel vegyes prompt kiosztsa | Zajos, ertelmezhetetlen eredmenyek | User/session szintu prompt fixalas |
| Metrikakat kontextus nelkul ertelmezni | Felrevezeto kovetkeztetesek | Mindig a dataseettel es szcenaroival egyutt ertelmezkunk |
| Nem tudom valasz universalis ertekelesehttps | Rossz ertekeles | Kulon dataset in-scope es out-of-scope kerdesekre |
| Izolaltasag nelkuli multi-turn teszt | Beszelgetesek memoriaija zavarja egymast | Docker Compose-szal izolalt kornyezet |

### Tippek

1. **Induljunk egyszeru metrikakkal** -- a binaris correctness es relevance mar sokat mond
2. **Naploizzunk mindent** -- a reszletes logok a legertekesebb hibakereso eszkozok
3. **A golden dataset legyen elo** -- rendszeresen bovitsuk problemas esetekkel
4. **Hasznaljunk policy matrix-ot** -- szervezzuk a szcenariokat es adathalmazokat
5. **A szimulalt felhasznaloknal hasznaljunk random parametreket** -- ne az LLM-re bizzuk a variabilitast
6. **Online evaluacional allitsunk be mintavetelezest** -- nem kell 100%, a 10-20% is informativi
7. **Batch API-t hasznaljunk** ha nem kell azonnali eredmeny -- olcsobb es hatekonyabb
8. **Rendszeres ertekelest** futtassunk -- a regresszio felderitese idoeben torteno osszehasonlitassal lehetseges

---

## Kapcsolodo Temak

| Tema | Relevancia |
|------|-----------|
| **RAG Pipeline es Dokumentum Feldolgozas** | A retrieval minoseg kozvetlenuel hatassal van az evaluacios eredmenyekre |
| **Embedding es Vektor Adatbazisok** | A vektor kereses minosege a RAG evaluacio alapja |
| **Prompt Engineering** | A prompt minosege kozvetlenul befolyasolja a single-turn evaluacioes eredmenyeket |
| **Backend Architektura** | Az API endpoint-ok es a streaming implementacio befolysolja az online evaluacioot |
| **Observability es Tracing** | A logolats es tracing szukseges az evaluacios eredmenyek interpretala sahoz |
| **Guardrails** | Az applikacio szintu evaluacio kulonm a guardrail-ek tesztelesevel foglalkozik |

---

## Tovabbi Forrasok

### Hivatkozott Konyvek
- **The Elements of Statistical Learning** -- statisztika-kozpontu szakkonyv, amely a modern AI elotti machine learning modelleket targyalja, es az evaluacio alapjaihoz nylujt hatteret

### Eszkozok es Platformok
- **Braintrust** (braintrust.dev) -- Evaluacios platform online es offline teszteleshez, scoring rule-ok beallitasaval
- **OpenAI Batch API** -- Tomoesges kereskuldese olcsobban, keseltetett valaszokkal (akr 24 oran belul)
- **Docker Compose** -- Izolalt kornyezet futtatasa multi-turn evaluaciokhoz

### Kulcsfogalmak Tovabbtanulashoz
- **Statistical significance** (statisztikai szignifikancia) -- A/B teszteknel a kulonbseg ertelmezes
- **Confusion matrix** -- Precision, Recall es F1-score reszletes megertese
- **Inter-annotator agreement** -- Emberi ertekelok kozotti egyeteres meroese
- **Human-in-the-loop** -- Emberi visszajelzes integralasa az automatizalt folyamatokba
- **Observability / Tracing** -- AI alkalmazasok monitorozasa es hibakereses (OpenTelemetry, LangFuse)

### A Kurzus Kapcsolodo Videoi
- **04_01**: Mit es hogyan merjunk? (evaluacio alapfogalmak, harom szint)
- **04_02**: RAG szintu meres (Precision, Recall, golden dataset)
- **04_03**: LLM as Judge (ertekelesiskalaiak, indoklas)
- **04_04**: RAG es single-turn evaluacio implementalasa
- **04_05**: Online evaluacio Braintrust-tal
- **04_06**: Automatikus vs. emberi ertekeles
- **04_07**: Automatikus evaluacio futtatasa (multi-turn szimulacios)
- **04_08**: Promptvaltozatok osszehasonlitasa (A/B teszt)
- **04_09**: Opcionalis: RAG es single-turn evaluacio teljes kod
- **04_12**: LIVE alkalom -- Python Judge, AI eszkozok, A/B teszteles
