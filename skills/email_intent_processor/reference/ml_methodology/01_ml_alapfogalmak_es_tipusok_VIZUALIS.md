> Vizualis verzio - kepekkel kiegeszitve | Eredeti: [01_ml_alapfogalmak_es_tipusok.md](01_ml_alapfogalmak_es_tipusok.md)

> Utolso frissites: 2026-03-09 | Forrasok: 11 transzkript + 3 PDF prezentacio + 1 hazi feladat

# ML Alapfogalmak es Tipusok

## Kurzus Attekintes (Kick-off LIVE alapjan)

A Cubix EDU ML Engineering kepzes 8 hetes, az elso het elmeleti alapozas, a masodik hettol kezdve programozas es elmelet hibridje. A kurzus felvetele:

| Het | Tema |
|---|---|
| **1. het** | Elmeleti alapfogalmak (AI, ML, DL, Data Science) |
| **2. het** | Fejlesztoi kornyezet, Python, adatkezeles |
| **3. het** | Adat-elokeszites, feature engineering |
| **4. het** | Felugyelt tanulasi modellek betanitasa |
| **5. het** | Modell kiertekeles es metrikak |
| **6. het** | Felugyelet nelkuli tanulas |
| **7. het** | Uzemeletes (DevOps, MLOps), pipeline epites, REST API |
| **8. het** | Anomalia detektalas, ajanlorendszerek, zaroprojekt |

**Oktato**: Gerzson Boros (Machine Learning Engineer)

**Fontos tudnivalok a kurzusrol** (a kick-off LIVE alapjan):
- A tananyagok heti rendszeresseggel erhetek el: videok, prezentaciok, hazi feladatok
- A hazi feladatok nem kotelezoek, de visszajelzest ad az oktato
- A heti elo alkalmak kerdezz-felelek jelleggel mukodnek
- A kurzus anyagai a zarastol szamitva egy evig erhetek el
- A zaroprojekt hatarideje aprilis, ket het haladekkal
- A gepi tanulas fejlesztes 60-80%-a adatkezelesrol szol: adatgyujtes, elofeldolgozas, felderito adatelemzes, korrelaciok vizsgalata, adattranszformaciok
- A kurzus gyakorlatorientalt, nem igenyel magas szintu matematikai tudast, de az analizis ismerete elonyt jelent

## Gyors Attekintes
> A gepi tanulas (Machine Learning) a mestersege intelligencia egy reszterulete, amely algoritmusok segitsegevel tanul az adatokbol es kepes predikciok vagy dontesek meghozatalara. Ez az osszefoglalo atfogoan bemutatja az ML alapfogalmait, a tanulasi paradigmakat (felugyelt, nem felugyelt, felig felugyelt, megerositeses), a fo feladattipusokat (osztalyozas, regresszio, klaszterezes), valamint az adattudomany teruleteinek es szerepeinek rendszeret. A tartalom a Cubix EDU ML Engineering kepzes elso ket hetenek anyagan alapul.

---

## Kulcsfogalmak

- **Artificial Intelligence (mesterseges intelligencia)**: Olyan informatikai rendszer, amely kepes az emberek szamara intelligensnek mutatkozni. Az AI egy nagy halmaz, amelynek reszhalmazai a Machine Learning es a Deep Learning. (A prezentacio szerinti formalis definicio: "Mimicking the intelligence or behavioural pattern of humans or any other living entity.")
- **Machine Learning (gepi tanulas)**: Az AI azon aga, ahol algoritmusok adatokbol tanulnak es predikciokat, donteseket hoznak anelkul, hogy explicit modon programoznak oket minden egyes esetre. A prezentacio definicioja: "A technique by which a computer can learn from data, without using a complex set of different rules. This approach is mainly based on training a model from datasets."
- **Deep Learning (mely tanulas)**: Az ML egy specialis aga, amely mely neuralis halozatokat hasznal komplex mintazatok felismeresere, kulonosen nagy mennyisegu adat eseten. A prezentacio definicioja: "A technique to perform machine learning inspired by our brain's own network of neurons."
- **Knowledge-based systems (szakertoi rendszerek)**: Szamitogep alapu rendszerek, amelyek emberi problemamegoldast utanoznak vagy segitik. Nagy mennyisegu explicit vagy implicit szakertoi tudast tartalmaznak, es szabaly- vagy eset-alapuak. Pelda: Deep Blue sakkgep.
- **Heurisztikus kereses (AI Search)**: Szisztematikus es kimerulekeny kereses, de nem a legjobb, hanem egy eleg jo megoldast keres. Alkalmazasok: utvonalkereses (GPS), webes keresoalgoritmusok, repuloteri logisztika, robotika, videojatek AI, varosrendezes, optimalizacios feladatok, diagnosztika, tervezesi feladatok.
- **Algoritmus vs. Modell**: Az algoritmus a meg be nem tanitott eszkoz, a modell pedig mar a betanitott, mukodo entitas, amely kepes predikciokra.
- **Feature (jellemzo)**: Az adatok egy-egy tulajdonsaga vagy oszlopa, amelyet a modell bemetentkent hasznal.
- **Cimke (Label)**: Az adatponthoz rendelt ismert kimenet vagy kategoria, amely alapjan a felugyelt tanulasi modell tanul.
- **Inference**: A betanitott modell hasznalata uj, korabban nem latott adatokon torteno predikciohoz.
- **Baseline modell**: Egy egyszeru kiindulo modell, amelyhez a fejlettebb modelleket viszonyitjuk.
- **Data drift**: Az adatok eloszlasanak valtozasa az ido soran, ami a modell teljesitmenyenek romlását okozhatja.
- **Tultanulas (overfitting)**: Amikor a modell tulzottan alkalmazkodik a tanito adatokhoz, es rosszul altalanositgeneralizal uj adatokra.
- **ETL (Extract, Transform, Load)**: Az adatok kinyeresenek, atalakitasanak es betoltesenek automatizalt folyamata.
- **Production-ready kod**: Eles kornyezetben torteno futatasra alkalmas, karbantarthato kod.

---

## Elmeleti Attekintes

A gepi tanulas lenyege, hogy adatokbol vonunk ki mintazatokat es osszefuggeseket anelkul, hogy minden szabalyt kezzel programoznank. A folyamat harom fo pillerre epul:

1. **Adat**: A tanulashoz szukseges bemenet -- ennek minosege, mennyisege es relevanciaja meghatarozza a modell teljesitmenyet.
2. **Algoritmus**: Az az eljaras, amely az adatokbol tanul -- kulonbozo feladatokhoz kulonbozo algoritmusok illeszkednek.
3. **Modell**: A tanulas eredmenye -- ez vegzi a tenyleges predikciokat uj adatokon.

A gepi tanulas nem varazslat: az adatok minosege es a domain (teruleti) tudas alapveteen meghatarozza a vegeredmenyt. Rossz adat vagy felretett kerdes eseten a legjobb algoritmus sem kepes jo eredmenyt adni.

### Az AI tortenete es az "AI-telek" (transzkript es prezentacio alapjan)

Az AI mar a 20. szazad kozepetol erosodott. Tobbszor elofordultak ugynevezett **AI-telek**: az emberek nagyon biztak az AI-ban, majd kiabrandulas kovetkaezett, mert nem volt elegendo adat es szamitasi kapacitas. Akkoriban leginkabb **knowledge-based (szakertoi) rendszerek** voltak elterjedve, amelyek szabalyalapuak es a szakertok tudasat szabalyokba ontve mukodtek.

### Teruleti Venn-diagramok (prezentaciok alapjan)

**1. AI -> ML -> DL hierarchia**: Egymasba agyazott kordiagram, ahol az AI a legkulso halmaz, benne az ML, benne a DL.

![AI, Machine Learning es Deep Learning egymasba agyazott halmazai](_kepek_cleaned/01_basic_concepts/slide_02.png)
*1. abra: Az AI, Machine Learning es Deep Learning hierarchikus viszonya Venn-diagramon. Az AI a legtagabb fogalom, ezen belul helyezkedik el az ML, majd annak reszehalmaza a Deep Learning.*

**2. AI, ML, DL es Data Science viszonya**: A Data Science es az AI/ML/DL korok atfedik egymast. A **Data Mining** az atfedesukben helyezkedik el -- tehat a Data Science reszahalmaza is, es egyben az AI/ML/DL reszahalmaza is.

![AI, ML, Deep Learning es Data Science teruleteinek viszonya](_kepek_cleaned/01_basic_concepts/slide_03.png)
*2. abra: Az AI (piros), Machine Learning (sarga), Deep Learning (zold) es Data Science (kek) teruletek kapcsolata. A Data Mining a Data Science es az ML atfedeseben helyezkedik el.*

**3. Data Science multidiszciplinas jellege**: Harom terulet metszete:
- **Computer Science**: Programming, Big Data technologies
- **Math & Statistics**: Machine learning, Ensemble models, Anomaly detection
- **Domain Expertise**: Business knowledge, Expert systems, User testing

![Data Science harom pillerjet mutato Venn-diagram](_kepek_cleaned/01_basic_concepts/slide_04.png)
*3. abra: A Data Science harom alkotopillerje: szamitastudomany (Computer Science), matematika es statisztika (Math & Statistics), valamint teruleti szaktudas (Domain Expertise). A harom metszetebol szuletik az adattudomany.*

**4. Statistics - AI - Computer Science Venn-diagram**: Az AI, a statisztika es a szamitastudomany osszefuggeseit mutatja, kiemelve: Probability, Normalization, Distributions, Bayes Theorem, Regression, Logits, Entropy (Statisztika); Planning, Computer Vision, Reinforcement, Neural Models, Anomaly Detection, NLP (AI); Data Mining, Function Approximation, Big Data, Optimization, Graph Algorithms (Szamitastudomany).

![Statisztika, AI es szamitastudomany reszletes Venn-diagramja](_kepek_cleaned/01_basic_concepts/slide_06.png)
*4. abra: A statisztika, a mesterseges intelligencia es a szamitastudomany reszteruleteinek osszefonodasa. A metszetek mutatjak, hogy mely reszteruletek (pl. Regression, Data Mining, NLP) hol helyezkednek el a tudomanyagak kozott.*

### Adatelemzes vs. Data Science vs. Data Mining (transzkript alapjan)

- **Adatelemzes (Data Analysis)**: A multba tekint, es kovetkezteteseket von le (pl. egy ceg bevetelirol)
- **Data Science**: Hasonloan a multba tekint, de a jovorol is szeretne elorejelzeseket tenni machine learning segitsegevel
- **Data Mining**: Nagy adatallomanyokban keres ertekes informaciokat es mintazatokat, kulonbozo adatelemzesi technikakat alkalmaz, gyakran machine learninget vagy deep learninget is

---

## Az Adattudomany Teruletei es Szerepek

### A Data Scientist harom pillere

Az adattudomanyt harom terulet metszete hatarozza meg:

1. **Programozasi ismeretek (Computer Science)**: Nem kell programozonak lenni, de a kodolas alapveto az adatok elemzesehez es ML modellek fejlesztesehez.
2. **Matematikai es statisztikai tudas**: Egyetemi szintu matematika ajanlo. A mindennapi ML munkaban nem kell magasszintu matematika, de research paperek olvasasahoz es specialis algoritmusokhoz elengedhetetlen.
3. **Domain tudas (teruleti szakertelem)**: Gyakran alabecsülik, holott a modell pontossagat 60%-rol akar 92%-ra is novelheti. Pelda: egy streaming szolgaltatas ugyfelemorzsólodas-elemzesenel a tartalom-kinalat ismerete donto tenyezo.

### Adatos szerepek a szervezetekben

| Szerep | Fo feladat | Legfontosabb kepessegek |
|---|---|---|
| **Data Engineer** | Adatgyujtes, tarolas, pipeline epitese, ETL | Programozas, Big Data, adatbazisok |
| **Data Scientist** | Adatelemzes, ML modellezes, uzleti betekintes | ML modellezes, statisztika, domain tudas |
| **Data Analyst** | Adatok reszletes elemzese, riportalas | Adatismeret, adatkezeles |
| **ML Engineer** | Modellek nullarol valo epitese es betanitasa, pipeline-ok epitese, notebook -> production-ready kod | Kodolas, ML, deployment |
| **MLOps Engineer** | Modellek uzemeltetese, automatizalt tanitas, monitorozas | DevOps + ML + adatkezeles |
| **AI Engineer** | Meglevo, elore tanitott (pre-trained) foundation modellek hasznalata es alkalmazasa | Integracio, API-k, AI ismeret |
| **Business Analyst** | Uzleti igenyek felismerese, specifikacio | Uzleti erzek, kommunikacio |
| **BI Analyst** | Dashboard-ok, KPI-k, uzleti riportok | Adatvizualizacio, statisztika |

A Data Science teruleten szamos szerepkor letezik, amelyek kulonbozo kepessegeket es felelossegeket igenyelnek. Az alabbi diagram reszletesen bemutatja ezek interakcioit:

![Data Science szerepkorok es interakcioik reszletes diagramja](_kepek_cleaned/01_basic_concepts/slide_07.png)
*5. abra: A Data Engineer, Data Scientist es Business Stakeholder szerepkorok reszletes keressegterkepe es egyuttmukodesi modellje. Mindharom szerepkor kozos celja a hipotezisfejlesztes, monetizacio es governance.*

### Szerepkorok es kepessegek matrixa (Gartner, prezentacio alapjan)

A prezentaciok tartalmaznak egy reszletes kepesseg-matrixot a kulonbozo adattudomanyi szerepkorokhoz (1-4 skala, ahol 4 = eros):

| Kepesseg | Business Analyst | Data Analyst / Data Engineer | Data Scientist | ML Engineer | DevOps | MLOps |
|---|---|---|---|---|---|---|
| **Data Knowledge** | 2 | 4 | 2 | 1 | 1 | 1 |
| **Data Skills** | 3 | 4 | 3 | 3 | 1 | 1 |
| **Business Acumen** | 4 | 2 | 3 | 1 | 1 | 2 |
| **ML Modeling Skills** | 2 | 1 | 4 | 1 | 1 | 1 |
| **Coding Skills** | 1 | 3-4 | 4 | 4 | 4 | 4 |
| **Soft Skills** | 4 | 2 | 2 | 1 | 1 | 1 |

![Analitikai szerepkorok es kepessegek osszehasonlito matrixa](_kepek_cleaned/01_basic_concepts/slide_09.png)
*6. abra: A Gartner altal keszitett reszletes kepesseg-matrix a kulonbozo analitikai szerepkorokhoz (Business Analyst, Data Engineer, Data Scientist, MLOps stb.). Az 1-4 skalan jeloli az egyes kepessegek fontossagat szerepkoronkent.*

![Data Science szerepkorok kompetenciai a CRISP-DM fazisokban](_kepek_cleaned/01_basic_concepts/slide_05.png)
*7. abra: A Data Science sikerenek hajtoeroit bemutato Gartner-diagram: az uzleti (Business Skills), informatikai (IT Skills) es adattudomanyi (Data Science) kepessegek metszete alkotja az "Analytics Leader" profiltat.*

### Szerepkorok a CRISP-DM fazisokban (prezentacio alapjan)

| Szerep | Business Understanding | Data Understanding | Data Preparation | Modeling | Evaluation | Deployment |
|---|---|---|---|---|---|---|
| **Data Scientist** | Mid | High | Mid | Top | High | Lower |
| **Data Engineer** | Mid | High | Top | Lower | Lower | Mid |
| **Data Analyst** | Mid | Top | Mid | Mid | Lower | Lower |
| **ML Engineer** | Mid | Lower | Mid | Mid | High | Top |
| **Product Owner** | Top | Mid | Lower | Lower | Top | Lower |
| **Project Manager** | High | Lower | Lower | Lower | Mid | Mid |

![Szerepkorok kompetenciaszintjei a CRISP-DM munkafolyamat fazisaiban](_kepek_cleaned/01_basic_concepts/slide_10.png)
*8. abra: Az adattudomanyi szerepkorok (Data Scientist, Data Engineer, ML Engineer stb.) kompetenciaszintjei a CRISP-DM egyes fazisaiban (Business Understanding-tol a Deployment-ig). A szinezés az erosseg merteketjeloli (Lower, Mid, High, Top).*

### Fizetesi adatok Magyarorszagon (Hays Hungary Salary Guide 2023, prezentacio alapjan)

| Pozicio | Junior (0-3 ev) atlag | Medior (3-5 ev) atlag | Senior (5+ ev) atlag | Architect/Lead atlag |
|---|---|---|---|---|
| **Data Scientist** | 1 100 000 Ft | 1 500 000 Ft | 1 800 000 Ft | 2 400 000 Ft |
| **Data Engineer** | 1 200 000 Ft | 1 500 000 Ft | 2 000 000 Ft | 2 400 000 Ft |
| **ML / DL Engineer** | 1 200 000 Ft | 1 700 000 Ft | 2 000 000 Ft | 2 500 000 Ft |
| **Computer Vision Engineer** | 1 100 000 Ft | 1 450 000 Ft | 1 700 000 Ft | 2 100 000 Ft |
| **BI Developer** | 1 100 000 Ft | 1 500 000 Ft | 1 700 000 Ft | 2 200 000 Ft |

*Megjegyzes: Brutto havi fizetes forintban, teljes munkaidore, bonusz es egyeb juttatas nelkul.*

![Magyarorszagi Data & Advanced Analytics fizetesek reszletes tablazata](_kepek_cleaned/01_basic_concepts/slide_11.png)
*9. abra: A Hays Hungary Salary Guide 2023 adatai: brutto havi fizetesek forintban a Data & Advanced Analytics teruleten, Junior-tol Architect/Lead szintig. Az ML/DL Engineer pozicio a legmagasabb fizetesu a senior es architect szinteken.*

### Glassdoor USA rangsor (prezentacio alapjan, 2022)

| Rang | Pozicio | Median fizetes (USD) | Elegedettseg (5-bol) |
|---|---|---|---|
| 3 | Data Scientist | $120,000 | 4.1 |
| 6 | ML Engineer | $130,489 | 4.3 |
| 7 | Data Engineer | $113,960 | 4.3 |
| 35 | Data Analyst | $74,224 | 4.0 |

![Glassdoor legjobb munkak rangsor az USA-ban (2022)](_kepek_cleaned/01_basic_concepts/slide_12.png)
*10. abra: A Glassdoor 2022-es "Best Jobs in America" rangsora. Az ML Engineer a 6. helyen all $130,489 median fizestessel es 4.3-as elegedettsegi pontszammal, mig a Data Scientist a 3. helyen $120,000-os fizetessel.*

**ML Engineer vs AI Engineer vs Halado ML Engineer** (kick-off LIVE alapjan):
- A **Machine Learning Engineer** nullarol epit modelleket: egy algoritmust betanit adatok segitsegevel, es igy jon letre a modell
- Az **AI Engineer** elore tanitott (pre-trained) foundation modelleket hasznal es alkalmaz
- A **halado Machine Learning Engineer** kepes az elore tanitott modelleket tovabb finomhangolni (fine tuning) sajat adatokon
- A fine tuning-hoz altalaban kevesebb adat is elegendo, mig nullarol valo tanitashoz tobb ezer adatpont szukseges
- A foundation modellek deep learninghez tartoznak, es a Generativ AI is ezekre epul

**Fontos megfigyeles a gyakorlatbol**: Az ML modellek 85-90%-a sosem jut el production-be, vagy hamar lekapcsoljak. Ennek fo oka a rossz tervezes es az MLOps hianya. Egy senior Data Scientist es egy ML Engineer idealis parost alkothat: a Data Scientist a notebook-ban fejleszt es domain tudasat alkalmazza, az ML Engineer pedig ebbol production-ready pipeline-okat epit.

**Startup vs. multi**: Startupnal gyakran egy ember visz minden adatos feladatot, mig nagyvallalatoknal akar tobb tiz fos dedikalt csapatok dolgoznak kulon-kulon teruleteken.

### Szervezeti felepites (prezentacio alapjan)

A prezentacio bemutatja a tipikus nagyvallalati adattudomanyi szervezeti strukturat:
- **CDO (Chief Data Officer)** ala tartozik harom csapat:
  - **Data Science Team**: Modellezes, elemzes, kiserletezés
  - **Data Engineering Team**: Adat-pipeline-ok, infrastruktura, ETL
  - **Data Operations Team**: Uzemeltetés, monitoring, adatminoseg

![Tipikus nagyvallalati adattudomanyi szervezeti abra](_kepek_cleaned/01_basic_concepts/slide_13.png)
*11. abra: Egy tipikus nagyvallalati szervezeti struktura, ahol a CDO (Chief Data Officer) ala tartozik a Data Science Team, a Data Engineering Team es a Data Operations Team. A CEO alatt szamos C-szintu vezeto helyezkedik el (CTO, CDO, CIO, CMO, CFO, COO).*

A Data Science eletciklus erettsegi szintjei: Data Collection -> Data Storage -> Data Transformation -> Reporting -> Insights -> Consumption -> Decisions. A Data Engineer az elso harom fazisert felelos, a Data Scientist a negyediktol a hatodikig jatszik fo szerepet.

![Adattudomanyi szerepkorok az erettsegi szintek menten](_kepek_cleaned/01_basic_concepts/slide_08.png)
*12. abra: A Data Science erettsegi szintjeit bemutato tablazat (Data Collection-tol Decisions-ig), feltuntetve az egyes fazisokhoz tartozo tevekenysegeket es szerepkorokat (Data Engineer, Data Scientist, ML Engineer, Info Designer stb.).*

---

## Data Science Folyamat (CRISP-DM)

A Data Science projekt egy iterativ folyamat, amely az alabbi lepesekbol all.

**A prezentacio ket kulonbozo folyamatmodellt mutat be:**

1. **Linearis Data Science folyamat**: Understand Business Problem -> Define Analytical Problem -> Define Tech Architecture -> Data Understanding -> Data Preparation -> Data Modelling -> Evaluation -> Deployment -> Feedback (visszacsatolasi hurkokkal az egyes fazisok kozott)

![Linearis Data Science folyamatmodell visszacsatolasi hurkokkal](_kepek_cleaned/01_basic_concepts/slide_14.png)
*13. abra: A Data Science projekt linearis folyamata az uzleti problema megertesetol a deploymentig. A zold fazisok (Business Problem, Analytical Problem, Tech Architecture) a tervezest, a kek fazisok (Data Understanding-tol Deployment-ig) a megvalositast jelzik. A nyilak visszacsatolasi hurkokat jelolnek az egyes fazisok kozott.*

2. **CRISP-DM harom fazisa reszletesen**:
   - **Conceptualisation**: Klinikusokkal/szakertokkel valo egyeztetes, hipotezisek megfogalmazasa, irodalomfeldolgozas, adatkovetelmeny-elemzes, prediktorok azonositasa, inkluzios/exkluzios kriteriumok meghatarozasa
   - **Exploratory (Discovery)**: Adatok feltarasa, ETL fejlesztes, adat-szotaralkotot es adatminoseg-ellenorzes, algoritmus kivalasztas, egyszeru validalas, teljesitmeny meres, prototipus fejlesztes
   - **Delivery**: Ujabb adatforrasok azonositasa, ETL optimalizalas, adatminoseg-felulvizsgalat, modell finomhangolas, keresztvalidalas, teljesitmeny meres, API/GUI/UX/dashboard fejlesztes

![CRISP-DM reszletes folyamatabra a harom fo fazissal](_kepek_cleaned/01_basic_concepts/slide_15.png)
*14. abra: A CRISP-DM (Cross Industry Standard Process for Data Mining) reszletes folyamatabra. A felso sav mutatja a hat fo fazist (Business Understanding, Data Understanding, Data Preparation, Modelling, Evaluation, Deployment), alatta a harom reszletezett szakasz: Conceptualisation, Exploratory (Discovery) es Delivery, mindegyik konkretallepesekkel.*

### 1. Uzleti problema megertese (Business Understanding)
- Felismerni az uzleti problemat es **jo kerdeseket feltenni**
- Pelda: "Miert csokken az arbevetelunk?" -> jobb kerdes: "Miert hagyjak el az ugyfeleinkavelszolgaltatásunkat?"
- A jo kerdesfeltetel az egyik legfontosabb uzleti kepesseg

### 2. ML problemava alakitas (Define Analytical Problem)
- Eldonteni, hogy megoldhato-e ML-lel a problema
- Pelda: gep meghibasodasanak elorejlzese -> binaris osztalyozas (elromlik-e a kovetkezo honapban: igen/nem)
- Megvizsgalni: vannak-e adatok? Van-e megfelelo hardver? Elerheto-e az adat a predkicio idopontjaban?

### 3. Adatmegertes (Data Understanding)
- Adatok minosegnek, mennyisegenek, relevanciajaak vizsgalata
- Uj feature-ok lehetosegeinek felismerese
- EDA (Exploratory Data Analysis) -- felderito adatelemzes

### 4. Adat-elokeszites (Data Preparation)
- Adattisztitas, transzformacio, elofeldolgozas
- Akar maga az adattisztitas is megoldhato ML-lel (konkret pelda: 99,x%-os pontossag)
- Iterativ: gyakran vissza kell terni az adatmegerteshez

### 5. Modellezes (Modeling)
- Baseline modell letrehozasa (egyszeru kiindulas)
- Kulonbozo algoritmusok kiprobablasa
- Feature engineering -- domain tudas konvertalasa feature-okke

### 6. Kiertekeles (Evaluation)
- Modellek osszehasonlitasa metrikak alapjan
- Lehet, hogy vissza kell menni egeszen az uzleti problema megerteseig
- Az ML fejlesztes R&D (kutatas-fejlesztes) jellegu: nem mindig trivialis, hogy megoldhato-e a feladat

### 7. Uzembe helyezes (Deployment) es Inference
- Szolgaltatas letrehozasa, ahol a modell predikciokat ad uj adatokra
- **MLOps**: a modell hosszu tavu mukodesnek biztositasa
- Folyamatos monitorozas szukseges (data drift figyelese)

> **Gyakorlati tanulsag a LIVE alkalomrol**: Az AI projektek 80-90%-os bukasi aranyanak fo okai: nem megfelelo use case valasztas, adatminosegi problemak, az uzleti tamogatottsag hianya, a tervezes es uzemeltetes hianyossagai. Az is elofordul, hogy az erintettek (pl. orvosok) ellenerdekelttek es nem hasznaljak az eszkozt.

---

## Algoritmus vs. Modell

Ez a kulonbsegtetel fontos es gyakran osszekeverelt:

| | ML Algoritmus | ML Modell |
|---|---|---|
| **Allapot** | Meg nincs betanitva | Mar betanitott |
| **Mikor hasznaljuk** | Kivalasztjuk, melyiket probaljuk ki | Kiertekelesnel, inference-nel |
| **Analogia** | Ures kenyersuto formak | Kisult kenyerek |

Tehat: elobb **algoritmusokat** valasztunk, betanitjuk oket adatokkal, es az eredmeny a **modell**, amely kepes predikciokat adni.

![ML Algoritmus es ML Modell kozotti kulonbseg vizualis magyarazata](_kepek_cleaned/01_basic_concepts/slide_16.png)
*15. abra: Az ML algoritmus es modell kozotti kulonbseg. Bal oldalon az adatok (binarisan abrazolva) az algoritmusba kerlneket, amely egy f(x) fuggvenyt kepez -- az eredmeny a modell. A jobb oldali tablazat osszefoglalja a ket fogalom definiciojat es technikai jellemzoit.*

**Formalis definiciok a prezentaciobol** (PDF dia):

| | **Modell** | **Algoritmus** |
|---|---|---|
| **Definicio** | Egy algoritmus kifejezesenek eredmenye, amely rejtett mintazatokat azonosit vagy predikciokat keszit | Jol definialt programok vagy utasitasok halmaza, amelyet osszetett problemak megoldasara hasznalnak |
| **Mire hivatkozik** | Reprezentalja, amit az algoritmus mar megtanult | A gepi tanulas motorjai, amelyek adathalmazbol modellt allitanak elo |
| **Technikai jelleg** | Egy szamitogep-program, amely specifikus utasitasokat es adatstrukturakat tartalmaz | Statisztikan, kalkulus es linearis algebran alapulnak |

A folyamat vizualisan: `Adat -> Algoritmus f(x) -> Modell`

---

## ML Tanulasi Paradigmak

A gepi tanulas tobb kulonbozo paradigma szerint mukodhet. Az alabbi abra attekinteset adja a harom fo tanulasi tipusnak: felugyelt, nem felugyelt es megerositeses tanulas.

![A harom fo tanulasi paradigma szemleletes osszehasonlitasa](_kepek/02_tasks_of_ml/slide_12.png)
*16. abra: A harom fo ML tanulasi paradigma intuitiv abrazolasa. A felugyelt tanulas (Supervised) egy tanitar-diak paroshoz hasonlit, a nem felugyelt tanulas (Unsupervised) az onallo felfedezeshez, mig a megerositeses tanulas (Reinforcement) egy autonomrobot donteshozatalahoz.*

![A gepi tanulas fo teruletei es alkalmazasaik](_kepek/02_tasks_of_ml/slide_02.png)
*17. abra: A Machine Learning harom fo iranya -- Supervised Learning (osztályozas, regresszio), Unsupervised Learning (klaszterezes, dimenziocsokkentes) es Reinforcement Learning (jatek AI, robot navigacio) -- es ezek tipikus alkalmazasi peldai.*

### Felugyelt tanulas (Supervised Learning)

A legelterjedtebb es altalaban legpontosabb megkozelites.

**Lenyege**: Rendelkezesre allnak **cimkezett adatok** (ismert bemenet-kimenet parok). A modell ezekbol tanul, es uj adatokra prediktal.

**A cimkek forrasai** (gyakorlati peldak):
- **Spam szures**: A Gmail besorolja az e-maileket spam/nem spam kategoriakba
- **Rakdiagnosztika**: A radiologus megjeloli az MRI felvetelen a tumor helyet
- **Ugyfelemorzsólodas**: Torteneti adatokbol latjuk, ki mondta le az elofizeteset
- **Gyuloletbeszed detektalas**: Onkentesek cimkezik az internetes kommenteket
- **Lopas felismeres**: Bizonyitott esetek alapjan hozhatunk letre cimkeket

**Ket fo feladattipus**: osztalyozas es regresszio (lasd lentebb).

![Felugyelt es nem felugyelt tanulas osszehasonlitasa allatfelismeressel](_kepek/02_tasks_of_ml/slide_07.png)
*18. abra: A felugyelt tanulas (Supervised Learning) es a nem felugyelt tanulas (Unsupervised Learning) kulonbsege szemleletes peldaval. A felugyelt modell ismert cimkek ("Duck" / "Not Duck") alapjan tanul es uj kepeketosztalyoz, mig a nem felugyelt modell cimkek nelkul csoportositja az allatokat.*

### Nem felugyelt tanulas (Unsupervised Learning)

**Lenyege**: **Nincsenek cimkek**, a modellnek maganak kell mintazatokat felismernie.

**Fontos**: Torekedni kell arra, hogy lehetoleg felugyelt tanulasi problemava alakitsuk a feladatot, mert az nagyobb pontossagot biztosit. De a nem felugyelt tanulas jol tamogathatja a felugyelt tanulast (pl. klaszterezes eredmenye uj feature-kent).

**Fo teruletek**:
- **Klaszterezes**: Adatok csoportokba rendezese cimkek nelkul
- **Dimenziocsokkentes**: Sok dimenzio lecsokkentese 2-3-ra vizualizaciohoz, vagy a pontossag novelesehez
- **Ajanlorendszerek**: Content-based es kollaborativ filtering

### Felig felugyelt tanulas (Semi-supervised Learning)

**Lenyege**: Az adatok **egy reszehez vannak cimkek**, a tobbihez nincsenek.

**Mukodese**:
1. A meglevo cimkezett adatokkal betanitunk egy felugyelt modellt
2. A modellel prediktaljuk a cimkezetlen adatokat
3. A magas konfidenciaju predikciiokatelfokadjuk uj cimkekkent
4. Ujratanítas a bovitett adathalmazon
5. Idealis esetben szuropróbaszeruen validaljuk az uj cimkeket

**Mikor alkalmazzuk**: Amikor sok cimkezetlen adat all rendelkezesre es az emberi cimkezes draga vagy idoigenyes. Uzleti dontes kerdese: merlegelni kell a cimkezes koltsegeit, az elerheto pontossagot es az uzleti igenyeket.

![Felugyelt, felig felugyelt es nem felugyelt tanulas osszehasonlitasa](_kepek/02_tasks_of_ml/slide_13.png)
*19. abra: A harom tanulasi tipus osszehasonlitasa az adatcimkezes szempontjabol. A felugyelt tanulasnal (Supervised) minden adat cimkezett, a felig felugyelt tanulasnal (Semi-supervised) az adatok kis resze cimkezett es nagy resze cimkezetlen, mig a nem felugyelt tanulasnal (Unsupervised) egyaltalan nincs cimke.*

### Megerositeses tanulas (Reinforcement Learning)

**Lenyege**: Egy **agens** akciokat hajt vegre egy **kornyezetben**, es **jutalmat** vagy **buntest** kap. A cel: maximalizalni az osszegyujtott jutalmat.

**Mukodesi modell**:
- **Agens**: A donteshozo entitas (pl. Mario figura, tozsdei kereskedo bot)
- **Kornyezet**: A vilag, amelyben az agens mukodik (pl. a jatek, a tozsde)
- **Akcio**: Az agens cselekvese (ugras, vasarlas, eladas, varakozas)
- **Jutalom/buntetes**: A kornyezet visszacsatolasa (pontgyujtes, nyereseg/veszteseg)

![A megerositeses tanulas mukodesi modellje](_kepek/02_tasks_of_ml/slide_15.png)
*20. abra: A Reinforcement Learning mukodesi modellje. Az AI agens akciokat hajt vegre a kornyezetben (Environment), es visszajelzest kap: jo akciokert jutalmat (Reward), rossz akciokert buntest (No Reward) kap. A neuralis halozat a tapasztalatok alapjan optimalizalja a donteseket.*

**Peldak**:
- **Jatek (Mario)**: Az agens megtanulja, hogy a kerdojelhez fejleles gombot ad, es a gomba jutalom. Ha ellenfebe utkozik, buntest kap.
- **Tozsdei kereskedes**: Az agens vesz/elad/var, es a nyereseg/veszteseg adja a jutalmat/buntest.

**A prezentacio altal kiemelt RL alkalmazasi teruletek**: Real-time decisions, Game AI, Robot Navigation, Skill Acquisition, Learning Tasks.

**Jellomzo**: A harom paradigma kozul a reinforcement learning hasonlit leginkabb az emberi tanulasra, hiszen mi is kornyezeti megerositesek alapjan fejlodunk.

### Tanulasi paradigmak rendszere (prezentacio dia alapjan)

A prezentacio egy reszletes faobraban mutatja a tanulasi paradigmak rendszeret:

![Tanulasi paradigmak reszletes taxonmiaja faabran](_kepek/02_tasks_of_ml/slide_14.png)
*21. abra: A tanulasi paradigmak teljes rendszere ket fo szempont szerint. Bal oldalon a visszajelzes mennyisege (feedback) szerinti felosztas: Supervised, Unsupervised, Semi-supervised. Jobb oldalon az informacio-ellatas modja: Offline, Online es Active learning.*

**Visszajelzes mennyisege szerint (Amount of feedback)**:
| Paradigma | Jellemzo |
|---|---|
| **Supervised** | A tanulo ismeri az osszes bemenetet es kimenetet |
| **Unsupervised** | A tanulo csak a bemeneteket ismeri |
| **Semi-supervised** | A tanulo csak nehany bemenet-kimenet part ismer |

**Informacio-ellatas modja szerint (Amount of information)**:
| Paradigma | Jellemzo |
|---|---|
| **Offline learning** | Az algoritmus a teljes adathalmazon tanul egyszerre |
| **Online learning** | Folyamatosan, szekvencialisan erkezo uj adatokbol tanul |
| **Active learning (Aktiv tanulas)** | A modell kivalasztja a leghasznosabb/legbizonytalanabb adatpontokat emberi cimkezesre |

---

## ML vs. Deep Learning

### AI -> ML -> DL taxonomiaja (prezentacio dia alapjan)

A prezentacio reszletes taxonomiai abrat mutat az AI teruleterol:

![Az AI, ML es Deep Learning reszletes taxonomiai abraja](_kepek/02_tasks_of_ml/slide_06.png)
*22. abra: Az AI teruletenek reszletes taxonomiaja egymasba agyazott retegekkel. A legkulso reteg az AI (Rule Based Systems, Game Playing, Planning stb.), kozepen az ML (SVM, Random Forest, K-Means stb.), belul a Deep Learning (CNN, RNN, GAN, LSTM, Autoencoders stb.).*

**Artificial Intelligence** (legkulso reteg):
- Rule Based Systems, Game Playing, Knowledge Representation and Reasoning, Propositional Calculus, Cognitive Modeling, Planning, Search Algorithms

**Machine Learning** (kozepso reteg):
- Support Vector Machines (SVM), Linear Regression, Logistic Regression, Random Forest, Gaussian Process Regression, K-Means Clustering

**Deep Learning** (belso reteg):
- MLP (Multi-Layer Perceptron), CNN (Convolutional Neural Network), GAN (Generative Adversarial Network), RBFN (Radial Basis Function Network), LSTM (Long Short-Term Memory), RNN (Recurrent Neural Network), Autoencoders

### ML algoritmusok nepszerusege (trend grafikon, 2010-2019)

A prezentacio egy Google Trends alapu grafikont mutat az atlagos havi keresesek alakulasarol:

![ML algoritmusok keresesi trendjeinek alakulasa 2010-2019](_kepek/02_tasks_of_ml/slide_05.png)
*23. abra: Az ML algoritmusok nepszerusegenek alakulasa a Google Trends alapjan (2010-2019). A Deep Learning 2014-tol robbanásszeru novekedesbe kezdett es 2017-re dominanssa valt, megelozve az SVM-et, a Neural Network-oket, a K-Means-t es a Decision Tree-ket.*

- **Deep Learning**: 2014-tol robbanasszeru novekedes, 2017-tol dominans (ertek: ~100)
- **SVM**: Stabil nepszeruseg (~30-40), enyhen csokkeno
- **Neural Networks**: Lassu csokkenés, majd stabilizalodas (~25-30)
- **K-Means**: Lassu novekedes (~20)
- **Decision Trees**: Stabil, alacsony ertek (~5)

### Mikor melyiket valasszuk?

| Szempont | Klasszikus ML | Deep Learning |
|---|---|---|
| **Adat mennyiseg** | Keves adat (nehany szaz - nehany ezer) | Sok adat (milliok - milliardok) |
| **Hardver** | Atlagos szamitogep elegendo | GPU (videokartya) szukseges |
| **Feature engineering** | Ember vegzi, domain tudas kell | Reszben vagy egeszben automatizalt |
| **Tipikus terulet** | Tablazatos adatok, kisebb adathalmazok | Kep, hang, szoveg, nagy adathalmazok |
| **Atlathato-sag** | Jobban ertelmezheto | "Fekete doboz" jellegu |

### ML vs. DL dontesi folyamatabra (prezentaciobol)

![ML vs. Deep Learning valasztas: hardver es adat donti el](_kepek/02_tasks_of_ml/slide_03.png)
*24. abra: A dontesi folyamat a klasszikus ML es a Deep Learning kozott. Ha jo hardver (GPU) es sok adat all rendelkezesre, Deep Learning javasolt; ha nem, klasszikus Machine Learning az alkalmasabb megoldas.*

![ML es Deep Learning feature extraction osszehasonlitasa](_kepek/02_tasks_of_ml/slide_04.png)
*25. abra: A klasszikus ML es a Deep Learning kozotti fo kulonbseg a feature extraction-ben rejlik. ML eseten az ember vegzi a feature extraction-t (kulon lepes), majd a halozat osztalyoz. DL eseten egyetlen mely neuralis halo vegzi a feature extraction-t es az osztalyozast egyutt, automatikusan.*

### Fontos arnalatok
- **Computer vision** eseten szinte mindig deep learning-et hasznalunk, meg akar 80-500 adatponttol is (pl. CT felvetelk)
- **Nem mindig a deep learning a legjobb**: Egy logisztikus regresszio vagy random forest gyakran felulmúlja a deep learning-et tablazatos adatokon
- **Mindig az adattol fugg**: Erdemes tobb algoritmust kiprobalni es osszehasonlitani
- Az AI > ML > Deep Learning hierarchia: a deep learning az ML reszhaalmaza, az ML az AI reszhalmaza

### Feature engineering vs. automatikus feature extraction
- **Keves adat**: Tobb feature engineering szukseges, a domain tudas erteke no
- **Sok adat + jo hardver**: End-to-end deep learning lehetseges, minimalis elofeldolgozassal

---

## Feladattipusok

### Osztalyozas (Classification)

**Definicio**: Adatpontok elore meghatarozott kategoriakba sorolasa. Felugyelt tanulasi feladat.

**Binaris osztalyozas** (a leggyakoribb ML feladat):
- Spam / nem spam
- Lemorzsolodik / nem morzsolodik le
- Csalas / nem csalas
- Gyuloletbeszéd / nem gyuloletbeszéd
- Kutya / macska a kepen
- Rak van / nincs rak az MRI felvetelen

**Multiclass classification** (tobb kategoria):
- Ugyfeszolgalati e-mailek kategorizalasa (akar 250 osztaly)
- Kepfelismeres (tobb allat- vagy targyosztaly)

### Regresszio (Regression)

**Definicio**: Folytonos ertek elorejlzese. Szinten felugyelt tanulasi feladat.

**Pelda**: "Mennyi ruhat adunk el a kovetkezo honapban?" -- a valasz egy konkret szam (pl. 1500 db), nem egy kategoria.

### Regresszio vs. Osztalyozas

![A regresszio es osztályozas kulonbsegenek szemleletes bemutatasa](_kepek/02_tasks_of_ml/slide_10.png)
*26. abra: A regresszio es az osztalyozas kozotti kulonbseg idojaras-peldaval. A regresszio pontos erteket prediktal ("Hany fok lesz holnap?" -> 84F), mig az osztalyozas kategoriat rendel ("Meleg vagy hideg lesz?" -> COLD/HOT).*

**Tipikus alkalmazasok** (prezentacio es transzkriptek alapjan):
- Idojaras-elorejlzes / Weather Forecasting (hany Celsius fok lesz holnap?)
- Bevetel-predickio (sales, marketing adatok) / Market Forecasting
- Arfolyam-elorejlzes (tozsde, deviza)
- Varhato elettartam becsles / Estimating life expectancy
- Populaciobecslés / Population Growth Prediction
- Reklam nepszeruseg elorejlzes / Advertising Popularity Prediction

![Regresszios modell vizualizacioja tanito es teszt adatokon](_kepek/02_tasks_of_ml/slide_11.png)
*27. abra: Egy regresszios modell illesztese (zold gorbe) a tanito adatokra (kek pontok) es teszt adatokra (piros pontok). A grafikon 100 epoch utani allapotot mutatja, ahol a modell jo altalanositasi kepesseget mutat.*

**Kulonbseg az osztalyozastol**: Az osztalyozas kategoriakat rendel (hideg/meleg), a regresszio pontos erteket prediktal (23,5 Celsius fok).

### Osztályozas vs. Klaszterezes vizualisan

![Osztalyozas (felugyelt) es klaszterezes (nem felugyelt) vizualis osszehasonlitasa](_kepek/02_tasks_of_ml/slide_09.png)
*28. abra: A felugyelt tanulás osztalyozasa (Classification) es a nem felugyelt tanulas klaszterezese (Clustering) osszehasonlitasa. Bal oldalon a cimkezett adatpontok (piros, kek, zold) dontesi hatarokkal elvalasztva lathatoak. Jobb oldalon cimkek nelkuli adatpontok, amelyeket az algoritmus onalloan csoportosit.*

### Klaszterezes (Clustering)

**Definicio**: Adatpontok csoportokba rendezese **cimkek nelkul**. Nem felugyelt tanulasi feladat.

**Fontos kulonbseg az osztalyozastol**:
- Osztalyozasnal tudjuk, milyen csoportok vannak (cimkek ismertek)
- Klaszterezesnel az algoritmus maga hozza letre a csoportokat
- Az algoritmus **nem tudja megmondani**, mit jelentenek a csoportok -- ezt az elemzonek kell ertelmeznie

**Figyelmeztetes**: A klaszterezo algoritmus nem feltetlenul az altalunk vart szempont szerint csoportosit. Pelda: allatok kepeinel nem feltetlenul allatfaj szerint, hanem akar szin alapjan csoportosithat.

![Klaszterezes vizualizacioja: eredeti es csoportositott adatok](_kepek/02_tasks_of_ml/slide_08.png)
*29. abra: A klaszterezes mukodesenek szemleltetes. Bal oldalon az eredeti, csooportositatlan adatpontok (Original Data), jobb oldalon a klaszterezes utan harom szinnel jelolt csoportba rendezett adatok (Clustered Data). Az algoritmus automatikusan felismeri a termeszetes csoportokat.*

**Tipikus alkalmazasok** (prezentacio es transzkriptek alapjan):
- Ugyfélszegmentacio / Customer Segmentation (pl. focirajongók, telisport kedvelok azonositasa)
- Targeted marketing / celzott marketing
- Felugyelt tanulast tamogato feature generalas
- Structure Discovery (adatstruktura felfedezese)

### Dimenziocsokkentes (Dimensionality Reduction)

**Definicio**: Az adatok dimenzoinak (oszlopainak) szamanak csokkentese.

**Miert erdemes alkalmazni**:
- **Vizualizacio**: Ember szamara csak 2-3 dimenzio ertelmezheto
- **Gyorsabb tanulas**: Kevesebb feature = gyorsabb algoritmus
- **Memoria-megtakaritas**: Kevesebb adat tarolando
- **Pontossag novelese**: Megakadalyozza a tultanulast (overfitting), javitja az altalanositokepesseget

![Dimenziocsokkentes vizualizacioja: 3D-bol 2D-be](_kepek/02_tasks_of_ml/slide_17.png)
*30. abra: A dimenziocsokkentes muvelet szemleltetese. A bal oldali 3D pontfelho (szinesekbe szinezett pontok egy gomb feluleten) a jobb oldalon 2D-be kerul leketpezesre, megorizve a pontok egymashoz viszonyitott tavolsagait es szineloszlasat.*

### Ajanlorendszerek (Recommendation Systems)

**Content-based filtering**:
- A tartalom hasonlosaga alapjan ajanl (pl. ugyanaz a szerezo, mufaj, rendezo)
- Implicit visszajelzesek is hasznalhatoknk: kattintas, idozes, olvasasi ido

**Kollaborativ filtering** (altalaban pontosabb):
- Felhasznalok kozotti hasonlosag alapjan ajanl
- "Hozzad hasonlo felhasznalok ezeket is szerettetk"
- Lajkolasok, kommentek, ertekelesek felhasznalasa

![Ajanlorendszerek ket fo tipusa: kollaborativ es tartalom-alapu szures](_kepek/02_tasks_of_ml/slide_16.png)
*31. abra: Az ajanlorendszerek ket fo megkozelitese. A Collaborative Filtering (bal oldal) hasonlo felhasznalok preferenciait hasznalja: "amit o olvasott, ajanlom neked". A Content-Based Filtering (jobb oldal) a tartalom hasonlosaga alapjan ajanl: az olvasott cikk jellemzoi alapjan keres hasonlo cikkeket.*

---

## Dontesi Segedlet: Melyik Megkozelitest Valasszam?

```
Van-e cimkezett adat?
|
|-- IGEN (mind cimkezett) --> FELUGYELT TANULAS
|   |
|   |-- Kategoriat prediktalunk? --> OSZTALYOZAS
|   |   |-- 2 osztaly --> Binaris osztalyozas (pl. spam/nem spam)
|   |   |-- 2+ osztaly --> Multiclass classification
|   |
|   |-- Folytonos erteket prediktalunk? --> REGRESSZIO
|       (pl. homerseklet, ar, darabszam)
|
|-- RESZBEN (csak egy resz cimkezett) --> SEMI-SUPERVISED LEARNING
|   (Betanitas a cimkezetteken, magas konfidenciaju predikciok elfogadasa)
|
|-- NEM --> NEM FELUGYELT TANULAS
|   |
|   |-- Csoportokat szeretnenk letrehozni? --> KLASZTEREZES
|   |-- Dimenziot szeretnenk csokkenteni? --> DIMENZIOCSOKKENTES
|   |-- Ajanlast szeretnenk adni? --> AJANLORENDSZER
|
|-- Valos ideju dontesek + kornyezeti visszacsatolas?
    --> MEGEROSITESES TANULAS
```

**Tovabbi szempontok**:
- Mindig torekedj a felugyelt tanulasra, ha lehetseges (nagyobb pontossag)
- Tablazatos adat + keves adat = klasszikus ML (random forest, logisztikus regresszio)
- Kep/hang/szoveg + sok adat = deep learning
- Nem felugyelt tanulas eredmenyei feature-kent beepithetok a felugyelt modellbe
- Mindig tobb algoritmust probablj ki es metrikak alapjan hasonlitsd ossze

---

## Osszehasonlito Tablazat

| Paradigma | Adat tipusa | Cimke? | Pelda feladat | Tipikus algoritmusok |
|---|---|---|---|---|
| **Felugyelt - Osztalyozas** | Cimkezett | Igen (kategoria) | Spam szures, rakdiagnosztika, fraud detection | Logisztikus regresszio, Random Forest, SVM, Neuralis halok |
| **Felugyelt - Regresszio** | Cimkezett | Igen (szam) | Arfolyam-elorejlzes, homerseklet-becsles | Linearis regresszio, Random Forest, Gradient Boosting |
| **Nem felugyelt - Klaszterezes** | Cimkezetlen | Nem | Ugyfszegmentacio, targeted marketing | K-Means, DBSCAN, Hierarchikus klaszterezes |
| **Nem felugyelt - Dimenziocsokkentes** | Cimkezetlen | Nem | Adatvizualizacio, feature reduction | PCA, t-SNE, UMAP |
| **Nem felugyelt - Ajanlorendszer** | Felhasznaloi adatok | Nem | Filmajanlas, cikkajanlas | Kollaborativ filtering, Content-based filtering |
| **Felig felugyelt** | Reszben cimkezett | Reszben | Draga cimkezesu adatok (pl. orvosi kepek) | Self-training, Label Propagation |
| **Megerositeses** | Kornyezeti visszacsatolas | Jutalom/buntetes | Robotnavigacio, jatek strategia, tozsdei kereskedes | Q-Learning, Policy Gradient, DQN |

---

## Gyakori Hibak es Tippek

### Az AI projektek bukasának fo okai (a LIVE alkalomrol)

1. **Nem megfelelo use case valasztas**: Ne eroltessunk AI-t oda, ahol egyszeru szabalyalapu megoldas is elegendo. A menedzserek gyakran tuleretkelik az AI-t.
2. **Adatminoseg, mennyiseg, relevancia**: Ha nincsenek megfelelo adatok, az ML nem fog mukodni. Az adatoknak a predkicio pillanataban is elerhetonek kell lenniuk (inference ideje).
3. **Data drift figyelmen kivul hagyasa**: Az adatok eloszlasa valtozik az idoben. Folyamatos monitorozas es ujratanítas szukseges.
4. **Tesztadat helytelen hasznalata**: Ha a tesztadatot is felhasznaljuk tanitasra, a modell tulzottan optimista eredmenyeket ad, de a valosagban gyenge lesz.
5. **Uzleti tamogatas hianya**: AI projekt nem indulhat menedzseri tamogatas nelkul. A hard ROI (kozvetlen megterules) rovid tavon ritkan pozitiv.
6. **Ellenerdekelt felek**: Pl. orvosok nem hasznaljak a diagnosztikai AI-t, mert felnek a munkajuk elvesztesetol.
7. **MLOps hianya**: A modell deployment utan is karbantartast igenyel. Enelkul a modell hamar elavul.

### Gyakorlati tippek

- **Mindig jo kerdeseket tegyel fel**: A jo kerdes fel valasz. "Miert csokken az arbevetel?" nem elegendo -- "Miert hagyják el az ügyfelek a szolgaltatast?" mar jobb.
- **Domain tudas nelkul ne kezdj ML projektet**: Beszelj szakertokkel, olvass cikkeket az adott teruletrol.
- **Baseline modellel indits**: Eloszor egy egyszeru modellt hozz letre, es ahhoz viszonyitsd a bonyolultabbakat.
- **Tobb algoritmust probablj ki**: Az adattol fugg, melyik mukodik legjobban.
- **Production szemlelettel kezdj**: Mar a fejlesztes elejen gondolj arra, hogy a modellnek eles kornyezetben is mukodnie kell.
- **Az ML fejlesztes R&D jellegu**: Nem garantalhato az eredmeny, iterativ kiserletezés szukseges.
- **Prediktiv karbantartas** az egyik legkonnyebben megterulo AI alkalmazas az iparban.

---

## ML Fejlesztoi Eszkozok (prezentacio alapjan)

### Python konyvtarak es framework-ok

A prezentacio bemutatja a legfontosabb ML eszkozoket:

![A legfontosabb ML fejlesztoi eszkozok es Python konyvtarak](_kepek/02_tasks_of_ml/slide_18.png)
*32. abra: A Machine Learning fejlesztes legfontosabb Python konyvtarai es framework-jei: TensorFlow (kozeppontban), PyTorch, Keras, Scikit-learn, Pandas, NumPy, NLTK, Spark, Theano es MXNet.*

| Eszkoz | Terulet |
|---|---|
| **Scikit-learn** | Klasszikus ML algoritmusok, elofeldolgozas |
| **TensorFlow** | Deep learning framework (Google) |
| **Keras** | Magas szintu DL API (TensorFlow felett) |
| **PyTorch** | Deep learning framework (Meta/Facebook) |
| **Pandas** | Adatkezeles, adattranszformacio |
| **NumPy** | Numerikus szamitasok, tombok |
| **NLTK** | Termeszetes nyelvfeldolgozas (NLP) |
| **Spark** | Big Data feldolgozas |
| **Theano** | Numerikus szamitasok (korabbi DL framework) |
| **MXNet** | Deep learning framework (Apache) |

### PyCaret - AutoML eszkoz (prezentaciobol)

A prezentacio bemutat egy PyCaret peldakodot es eredmenytablazatot, ahol egy sorban osszehasonlithaatoak kulonbozo modellek:

```python
# functional API
best = compare_models()
# OOP API
best = s.compare_models()
```

![PyCaret AutoML modell-osszehasonlito tablazat](_kepek/02_tasks_of_ml/slide_19.png)
*33. abra: A PyCaret compare_models() fuggveny kimenete: automatikus modell-osszehasonlitas tablazata, amely metrikank szerint (Accuracy, AUC, Recall, Precision, F1, Kappa, MCC, futasi ido) rangsorolja az osszes kiprobalt algoritmust. A sargaval kiemelt ertekek az adott metrikaban legjobb eredmenyt jelzik.*

![PyCaret Learning Curve vizualizacio](_kepek/02_tasks_of_ml/slide_20.png)
*34. abra: A PyCaret evaluate_model() fuggveny Learning Curve vizualizacioja egy GradientBoostingRegressor modellre. A kek gorbe a tanito pontszamot, a zold gorbe a keresztvalidacios pontszamot mutatja a tanito adatok szamanak fuggvenyeben.*

### MLOps Pipeline architektura (prezentaciobol)

A prezentacio egy tipikus MLOps pipeline-t mutat be:

![MLOps pipeline architektura Docker kornyezetben](_kepek/02_tasks_of_ml/slide_21.png)
*35. abra: Egy tipikus MLOps pipeline architekturaja. A Backend oldalon H2O AutoML (modelltanitas) -> MLflow (modell registry es tracking) -> FastAPI (API endpoint), a Frontend oldalon Streamlit (web alkalmazas). Mindketto Docker kontenekben fut egy kozos Docker Host Network-on.*

### Fejlesztoi kornyezetek

A prezentacio harom fo fejlesztoi kornyezetet mutat be:

1. **Jupyter Notebook / JupyterLab**: Interaktiv notebook kornyezet, tamogatja Python, R, Julia, C++ nyelveket

2. **Google Colab**: Felhoalapu notebook kornyezet ingyen GPU/TPU hozzaferessel

![Google Colab fejlesztoi kornyezet](_kepek/02_tasks_of_ml/slide_23.png)
*36. abra: A Google Colab fejlesztoi kornyezet, amely egy felhoalapu Jupyter notebook. A kepnyofelvetel egy projekt-boilerplate notebookot mutat adatletoltessel, projekt-beallitassal es script futatassal. A bal oldali panelen a fajlstruktura lathato.*

3. **VS Code / IDE**: Hagyomanyos fejlesztoi kornyezet Python bovitmenyekkel, terminallal

---

## Gyakorlo Feladatok (1. heti hazi feladat)

### 1. feladat: Osztalyozas vagy klaszterezes?

Dontsd el, hogy a lentebbi pontok osztalyozashoz vagy klaszterezeshez tartoznak! Lehetnek olyanok, amelyek nem egyertelmuek (pl. mindketto lehetseges bizonyos feltetalek mellett), azokat jelold.

1. Azonositsd a betegek kulonbozo tipusu rakos megbetegadeseit a laboratoriumieredmenyek alapjan.
2. Csoportositsd a vasarlokat vasarlasi szokasaik alapjan anelkul, hogy elozetes cimkeket hasznalnal.
3. Osztalyozd a leveleket spam es nem spam kategoriakba azok tartalma alapjan.
4. Talald meg a kozos jellemzoket birtoklo termekcsoportokat egy webaruhaz kinalataban, cimkek nelkul.
5. Azonositsd es csoportositsd a kulonbozo nyelveken irodott szovegeket.
6. Talalj ki algoritmust, amely kepes azonositani a kulonbozo automarkakat a jarmuvek jellemzoi alapjan.
7. Osztalyozd a filmeket mufajuk alapjan azok leirasa alapjan.
8. Csoportositsd az ugyfeleket koruk es vasarlasi gyakorisaguk alapjan.
9. Hatarozzd meg, hogy egy adott e-mail uzenet fontos-e vagy sem.
10. Azonositsd a varosokat lakossagszamuk es foldrajzi helyzetuk alapjan.
11. Osztalyozd a diakokat teljesitmenyuk alapjan kulonbozo szintu osztalyokba.
12. Hozz letre csoportokat az allatok kozott azok elohelye alapjan.
13. Azonositsd a kulonbozo eghajlati zonakat a vilagon meteorologiai adatok alapjan.
14. Csoportositsd a novenyeket azok viragzasanak ideje szerint.
15. Hatarozzd meg a sportolok teljesitmenyet kulonbozo sportagakban.
16. Azonositsd a csillagkepeket az ejszakai egbolton.
17. Osztalyozd a mobilalkalmazasokat kategoriak szerint, mint peldaul jatek, uzleti, oktatas.
18. Hozz letre csoportokat a szamitogepes virusok kozott a terjedesi modjuk alapjan.
19. Azonositsd a kulonbozo penzugyi tranzakciotipusokat, mint peldaul vasarlas, atutalas, befizetes.
20. Csoportositsd a zenei stilusokat a hangzasuk alapjan.
21. Azonositsd a kulonbozo tengeri elolenyeleket azok fizikai jellemzoi alapjan.
22. Osztalyozd az eteleket azok fo osszetevoje alapjan, peldaul hus, zoldseg, teszta.
23. Csoportositsd a hoteleket azok szolgaltatasai es arkategoriaja alapjan.
24. Hatarozzd meg, hogy egy adott noveny mergezo-e vagy sem.
25. Azonositsd a kulonbozo gepjarmuveket azok uzemanyag fogyasztasa alapjan.
26. Osztalyozd a konyveket a kiadasuk eve alapjan.
27. Csoportositsd a festmenyeket azok stilusa es a festo koranak alapjan.
28. Azonositsd a kulonbozo orszagokat azok GDP-je alapjan.
29. Osztalyozd a diakokat az altaluk valasztott szakkorok alapjan.
30. Hozz letre csoportokat a filmrendezok kozott a filmjeik altalanos temaja alapjan.

### 2. feladat: Szerepkorok hozzarendelese

Dontsd el, hogy a kovetkezo kepessegek es feladatok Data Scientisthez, ML Engineerhez vagy Data Engineerhez tartozik inkabb! Lesznek olyanok, amelyeket tobbhoz is sorolhatsz.

1. Adatok elokeszitese es tisztitasa
2. Statikus adatelemzes es hipotezisvizsgalat
3. Big Data technologiak, mint peldaul Hadoop es Spark
4. Adattarhazak es ETL folyamatok kialakitasa
5. Deep learning modellek productionbe helyezese
6. Adatvizualizacio es jelenteszkeszites
7. Idosoros elemzes es elorejelzes
8. Adatbazis-kezeles es lekerdezsesek SQL-ben
9. Adatbiztonsag es adatkezelesi szabalyozasok
10. Algoritmus optimalizalas es teljesitmenyelemzes
11. Kiserleti kialakitas es A/B teszteles
12. Felhoalapu szolgaltatasok, mint az AWS vagy Azure
13. ML rendszerek pipeline-jainak kialakitasa
14. Adatpiaci trendek es uzleti intelligencia
15. Generative AI
16. Adatbanyaszat es komplex adatelemzes
17. Adatintegracio es adataramlasok kezelese
18. Deployment technikak
19. Docker es Kubernetes kontenerizacios technologiak
20. Prediktiv modellezes es valoszinusegi statisztikak

### 3. feladat: Regresszio peldak

Irj legalabb 10 peldat regressziora!

*(Segitseg: gondolj olyan feladatokra, ahol folytonos erteket kell prediktalni, nem kategoriat.)*

### 4. feladat: Reinforcement learning peldak

Irj legalabb 10 peldat reinforcement learningre!

*(Segitseg: gondolj olyan feladatokra, ahol egy agens kornyezeti visszacsatolas alapjan tanul, jutalom es buntetes rendszerevel.)*

---

## Kapcsolodo Temak

- -> [02_fejlesztoi_kornyezet_es_pandas.md](02_fejlesztoi_kornyezet_es_pandas.md) -- Fejlesztoi kornyezet, Python, Pandas alapok
- -> [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- Felugyelt tanulasi algoritmusok reszletesen (logisztikus regresszio, dontesi fak, random forest, SVM)

---

## Tovabbi Forrasok

- **scikit-learn Algorithm Cheat Sheet**: [https://scikit-learn.org/stable/tutorial/machine_learning_map/](https://scikit-learn.org/stable/tutorial/machine_learning_map/) -- Vizualis dontestamogato a megfelelo algoritmus kivalasztasahoz
- **Google Machine Learning Crash Course**: [https://developers.google.com/machine-learning/crash-course](https://developers.google.com/machine-learning/crash-course) -- Ingyenes, gyakorlatias ML bevezeto
- **Kaggle Learn**: [https://www.kaggle.com/learn](https://www.kaggle.com/learn) -- Interaktiv ML kurzusok Python-ban
- **CRISP-DM Modell**: [https://en.wikipedia.org/wiki/Cross-industry_standard_process_for_data_mining](https://en.wikipedia.org/wiki/Cross-industry_standard_process_for_data_mining) -- A Data Science folyamat ipari szabványa
- **MLOps Principles**: [https://ml-ops.org/](https://ml-ops.org/) -- MLOps bevezeto es best practices

---

## Kepjegyzek

| Abra | Leiras | Forras |
|---|---|---|
| 1. abra | AI, ML es Deep Learning hierarchikus viszonya Venn-diagramon | `_kepek_cleaned/01_basic_concepts/slide_02.png` |
| 2. abra | AI, ML, Deep Learning es Data Science teruletek kapcsolata | `_kepek_cleaned/01_basic_concepts/slide_03.png` |
| 3. abra | Data Science harom alkotopillerje Venn-diagramon | `_kepek_cleaned/01_basic_concepts/slide_04.png` |
| 4. abra | Statisztika, AI es szamitastudomany reszteruleteinek osszefonodasa | `_kepek_cleaned/01_basic_concepts/slide_06.png` |
| 5. abra | Data Science szerepkorok es interakcioik reszletes diagramja | `_kepek_cleaned/01_basic_concepts/slide_07.png` |
| 6. abra | Gartner analitikai szerepkor-kepesseg matrix | `_kepek_cleaned/01_basic_concepts/slide_09.png` |
| 7. abra | Data Science sikertenyezoi Gartner-diagram (Business, IT, Data Science) | `_kepek_cleaned/01_basic_concepts/slide_05.png` |
| 8. abra | Szerepkorok kompetenciaszintjei a CRISP-DM fazisaiban | `_kepek_cleaned/01_basic_concepts/slide_10.png` |
| 9. abra | Magyarorszagi Data & Advanced Analytics fizetesek (Hays 2023) | `_kepek_cleaned/01_basic_concepts/slide_11.png` |
| 10. abra | Glassdoor "Best Jobs in America" rangsor (2022) | `_kepek_cleaned/01_basic_concepts/slide_12.png` |
| 11. abra | Tipikus nagyvallalati adattudomanyi szervezeti abra (CDO) | `_kepek_cleaned/01_basic_concepts/slide_13.png` |
| 12. abra | Data Science erettsegi szintek es szerepkorok | `_kepek_cleaned/01_basic_concepts/slide_08.png` |
| 13. abra | Linearis Data Science folyamatmodell visszacsatolasi hurkokkal | `_kepek_cleaned/01_basic_concepts/slide_14.png` |
| 14. abra | CRISP-DM reszletes folyamatabra harom fazissal | `_kepek_cleaned/01_basic_concepts/slide_15.png` |
| 15. abra | ML Algoritmus es ML Modell kozotti kulonbseg | `_kepek_cleaned/01_basic_concepts/slide_16.png` |
| 16. abra | Harom fo ML tanulasi paradigma intuitiv osszehasonlitasa | `_kepek/02_tasks_of_ml/slide_12.png` |
| 17. abra | Machine Learning fo teruletei es alkalmazasi peldai | `_kepek/02_tasks_of_ml/slide_02.png` |
| 18. abra | Felugyelt es nem felugyelt tanulas osszehasonlitasa allatfelismeressel | `_kepek/02_tasks_of_ml/slide_07.png` |
| 19. abra | Supervised vs. Semi-supervised vs. Unsupervised tanulas | `_kepek/02_tasks_of_ml/slide_13.png` |
| 20. abra | Reinforcement Learning mukodesi modellje (agens-kornyezet-jutalom) | `_kepek/02_tasks_of_ml/slide_15.png` |
| 21. abra | Tanulasi paradigmak teljes taxonomiaja faabran | `_kepek/02_tasks_of_ml/slide_14.png` |
| 22. abra | AI, ML es Deep Learning reszletes taxonomiai abraja | `_kepek/02_tasks_of_ml/slide_06.png` |
| 23. abra | ML algoritmusok keresesi trendjeinek alakulasa (2010-2019) | `_kepek/02_tasks_of_ml/slide_05.png` |
| 24. abra | ML vs. Deep Learning valasztas dontesi diagramja | `_kepek/02_tasks_of_ml/slide_03.png` |
| 25. abra | ML es Deep Learning feature extraction osszehasonlitasa | `_kepek/02_tasks_of_ml/slide_04.png` |
| 26. abra | Regresszio vs. osztalyozas kulonbsege idojaras-peldaval | `_kepek/02_tasks_of_ml/slide_10.png` |
| 27. abra | Regresszios modell vizualizacioja tanito es teszt adatokon | `_kepek/02_tasks_of_ml/slide_11.png` |
| 28. abra | Osztalyozas (felugyelt) es klaszterezes (nem felugyelt) vizualis osszehasonlitasa | `_kepek/02_tasks_of_ml/slide_09.png` |
| 29. abra | Klaszterezes vizualizacioja: eredeti es csoportositott adatok | `_kepek/02_tasks_of_ml/slide_08.png` |
| 30. abra | Dimenziocsokkentes: 3D pontfelho 2D-be vetitese | `_kepek/02_tasks_of_ml/slide_17.png` |
| 31. abra | Ajanlorendszerek: kollaborativ es tartalom-alapu szures | `_kepek/02_tasks_of_ml/slide_16.png` |
| 32. abra | ML fejlesztoi eszkozok es Python konyvtarak | `_kepek/02_tasks_of_ml/slide_18.png` |
| 33. abra | PyCaret AutoML modell-osszehasonlito tablazat | `_kepek/02_tasks_of_ml/slide_19.png` |
| 34. abra | PyCaret Learning Curve vizualizacio | `_kepek/02_tasks_of_ml/slide_20.png` |
| 35. abra | MLOps pipeline architektura Docker kornyezetben | `_kepek/02_tasks_of_ml/slide_21.png` |
| 36. abra | Google Colab fejlesztoi kornyezet | `_kepek/02_tasks_of_ml/slide_23.png` |

---

*Forras: Cubix EDU ML Engineering kepzes, 1-2. het videoi es LIVE alkalmak (2026.01.28, 2026.02.04), PDF prezentaciok ("1 Basic concepts.pdf", "2 Tasks of Machine Learning.pdf"), hazi feladat ("1_hazi_feladat.pdf")*
