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

## Gyors Áttekintés
> A gépi tanulás (Machine Learning) a mesterséges intelligencia egy részterülete, amely algoritmusok segítségével tanul az adatokból és képes predikciók vagy döntések meghozatalára. Ez az összefoglaló átfogóan bemutatja az ML alapfogalmait, a tanulási paradigmákat (felügyelt, nem felügyelt, félig felügyelt, megerősítéses), a fő feladattípusokat (osztályozás, regresszió, klaszterezés), valamint az adattudomány területeinek és szerepeinek rendszerét. A tartalom a Cubix EDU ML Engineering képzés első két hetének anyagán alapul.

---

## Kulcsfogalmak

- **Artificial Intelligence (mesterseges intelligencia)**: Olyan informatikai rendszer, amely kepes az emberek szamara intelligensnek mutatkozni. Az AI egy nagy halmaz, amelynek reszhalmazai a Machine Learning es a Deep Learning. (A prezentacio szerinti formalis definicio: "Mimicking the intelligence or behavioural pattern of humans or any other living entity.")
- **Machine Learning (gepi tanulas)**: Az AI azon aga, ahol algoritmusok adatokbol tanulnak es predikciokat, donteseket hoznak anelkul, hogy explicit modon programoznak oket minden egyes esetre. A prezentacio definicioja: "A technique by which a computer can learn from data, without using a complex set of different rules. This approach is mainly based on training a model from datasets."
- **Deep Learning (mely tanulas)**: Az ML egy specialis aga, amely mely neuralis halozatokat hasznal komplex mintazatok felismeresere, kulonosen nagy mennyisegu adat eseten. A prezentacio definicioja: "A technique to perform machine learning inspired by our brain's own network of neurons."
- **Knowledge-based systems (szakertoi rendszerek)**: Szamitogep alapu rendszerek, amelyek emberi problemamegoldast utanoznak vagy segitik. Nagy mennyisegu explicit vagy implicit szakertoi tudast tartalmaznak, es szabaly- vagy eset-alapuak. Pelda: Deep Blue sakkgep.
- **Heurisztikus kereses (AI Search)**: Szisztematikus es kimerulekeny kereses, de nem a legjobb, hanem egy eleg jo megoldast keres. Alkalmazasok: utvonalkereses (GPS), webes keresoalgoritmusok, repuloteri logisztika, robotika, videojatek AI, varosrendezes, optimalizacios feladatok, diagnosztika, tervezesi feladatok.
- **Algoritmus vs. Modell**: Az algoritmus a meg be nem tanitott eszkoz, a modell pedig mar a betanitott, mukodo entitas, amely kepes predikciokra.
- **Feature (jellemző)**: Az adatok egy-egy tulajdonsága vagy oszlopa, amelyet a modell bemenetként használ.
- **Címke (Label)**: Az adatponthoz rendelt ismert kimenet vagy kategória, amely alapján a felügyelt tanulási modell tanul.
- **Inference**: A betanított modell használata új, korábban nem látott adatokon történő predikcióhoz.
- **Baseline modell**: Egy egyszerű kiinduló modell, amelyhez a fejlettebb modelleket viszonyítjuk.
- **Data drift**: Az adatok eloszlásának változása az idő során, ami a modell teljesítményének romlását okozhatja.
- **Túltanulás (overfitting)**: Amikor a modell túlzottan alkalmazkodik a tanító adatokhoz, és rosszul általánosít új adatokra.
- **ETL (Extract, Transform, Load)**: Az adatok kinyerésének, átalakításának és betöltésének automatizált folyamata.
- **Production-ready kód**: Éles környezetben történő futtatásra alkalmas, karbantartható kód.

---

## Elméleti Áttekintés

A gépi tanulás lényege, hogy adatokból vonunk ki mintázatokat és összefüggéseket anélkül, hogy minden szabályt kézzel programoznánk. A folyamat három fő pillérre épül:

1. **Adat**: A tanuláshoz szükséges bemenet -- ennek minősége, mennyisége és relevanciája meghatározza a modell teljesítményét.
2. **Algoritmus**: Az az eljárás, amely az adatokból tanul -- különböző feladatokhoz különböző algoritmusok illeszkednek.
3. **Modell**: A tanulás eredménye -- ez végzi a tényleges predikciókat új adatokon.

A gépi tanulás nem varázslat: az adatok minősége és a domain (területi) tudás alapvetően meghatározzák a végeredményt. Rossz adat vagy félretett kérdés esetén a legjobb algoritmus sem képes jó eredményt adni.

### Az AI tortenete es az "AI-telek" (transzkript es prezentacio alapjan)

Az AI mar a 20. szazad kozepetol erosodott. Tobbszor elofordultak ugynevezett **AI-telek**: az emberek nagyon biztak az AI-ban, majd kiabrándulas kovetkaezett, mert nem volt elegendo adat es szamitasi kapacitas. Akkoriban leginkabb **knowledge-based (szakertoi) rendszerek** voltak elterjedve, amelyek szabalyalapuak es a szakertok tudasat szabalyokba ontve mukodtek.

### Teruleti Venn-diagramok (prezentaciok alapjan)

**1. AI -> ML -> DL hierarchia**: Egymasba agyazott kordiagram, ahol az AI a legkulso halmaz, benne az ML, benne a DL.

**2. AI, ML, DL es Data Science viszonya**: A Data Science es az AI/ML/DL korök atfedik egymast. A **Data Mining** az atfedesukben helyezkedik el -- tehat a Data Science reszahalmaza is, es egyben az AI/ML/DL reszahalmaza is.

**3. Data Science multidiszciplinas jellege**: Harom terület metszete:
- **Computer Science**: Programming, Big Data technologies
- **Math & Statistics**: Machine learning, Ensemble models, Anomaly detection
- **Domain Expertise**: Business knowledge, Expert systems, User testing

**4. Statistics - AI - Computer Science Venn-diagram**: Az AI, a statisztika es a szamitastudomany osszefuggeseit mutatja, kiemelve: Probability, Normalization, Distributions, Bayes Theorem, Regression, Logits, Entropy (Statisztika); Planning, Computer Vision, Reinforcement, Neural Models, Anomaly Detection, NLP (AI); Data Mining, Function Approximation, Big Data, Optimization, Graph Algorithms (Szamitastudomany).

### Adatelemzes vs. Data Science vs. Data Mining (transzkript alapjan)

- **Adatelemzes (Data Analysis)**: A multba tekint, es kovetkezteteseket von le (pl. egy ceg bevetelirol)
- **Data Science**: Hasonloan a multba tekint, de a jovorol is szeretne elorejelzeseket tenni machine learning segitsegevel
- **Data Mining**: Nagy adatallomanyokban keres ertekes informaciokat es mintazatokat, kulonbozo adatelemzesi technikakat alkalmaz, gyakran machine learninget vagy deep learninget is

---

## Az Adattudomány Területei és Szerepek

### A Data Scientist három pillére

Az adattudományt három terület metszete határozza meg:

1. **Programozási ismeretek (Computer Science)**: Nem kell programozónak lenni, de a kódolás alapvető az adatok elemzéséhez és ML modellek fejlesztéséhez.
2. **Matematikai és statisztikai tudás**: Egyetemi szintű matematika ajánlott. A mindennapi ML munkában nem kell magasszintű matematika, de research paperek olvasásához és speciális algoritmusokhoz elengedhetetlen.
3. **Domain tudás (területi szakértelem)**: Gyakran alábecsülik, holott a modell pontosságát 60%-ról akár 92%-ra is növelheti. Példa: egy streaming szolgáltatás ügyfélemorzsolódás-elemzésénél a tartalom-kínálat ismerete döntő tényező.

### Adatos szerepek a szervezetekben

| Szerep | Fő feladat | Legfontosabb képességek |
|---|---|---|
| **Data Engineer** | Adatgyűjtés, tárolás, pipeline építése, ETL | Programozás, Big Data, adatbázisok |
| **Data Scientist** | Adatelemzés, ML modellezés, üzleti betekintés | ML modellezés, statisztika, domain tudás |
| **Data Analyst** | Adatok részletes elemzése, riportálás | Adatismeret, adatkezelés |
| **ML Engineer** | Modellek nulláról való építése és betanítása, pipeline-ok építése, notebook -> production-ready kód | Kódolás, ML, deployment |
| **MLOps Engineer** | Modellek üzemeltetése, automatizált tanítás, monitorozás | DevOps + ML + adatkezelés |
| **AI Engineer** | Meglévő, előre tanított (pre-trained) foundation modellek használata és alkalmazása | Integráció, API-k, AI ismeret |
| **Business Analyst** | Üzleti igények felismerése, specifikáció | Üzleti érzék, kommunikáció |
| **BI Analyst** | Dashboard-ok, KPI-k, üzleti riportok | Adatvizualizáció, statisztika |

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

### Szerepkorok a CRISP-DM fazisokban (prezentacio alapjan)

| Szerep | Business Understanding | Data Understanding | Data Preparation | Modeling | Evaluation | Deployment |
|---|---|---|---|---|---|---|
| **Data Scientist** | Mid | High | Mid | Top | High | Lower |
| **Data Engineer** | Mid | High | Top | Lower | Lower | Mid |
| **Data Analyst** | Mid | Top | Mid | Mid | Lower | Lower |
| **ML Engineer** | Mid | Lower | Mid | Mid | High | Top |
| **Product Owner** | Top | Mid | Lower | Lower | Top | Lower |
| **Project Manager** | High | Lower | Lower | Lower | Mid | Mid |

### Fizetesi adatok Magyarorszagon (Hays Hungary Salary Guide 2023, prezentacio alapjan)

| Pozicio | Junior (0-3 ev) atlag | Medior (3-5 ev) atlag | Senior (5+ ev) atlag | Architect/Lead atlag |
|---|---|---|---|---|
| **Data Scientist** | 1 100 000 Ft | 1 500 000 Ft | 1 800 000 Ft | 2 400 000 Ft |
| **Data Engineer** | 1 200 000 Ft | 1 500 000 Ft | 2 000 000 Ft | 2 400 000 Ft |
| **ML / DL Engineer** | 1 200 000 Ft | 1 700 000 Ft | 2 000 000 Ft | 2 500 000 Ft |
| **Computer Vision Engineer** | 1 100 000 Ft | 1 450 000 Ft | 1 700 000 Ft | 2 100 000 Ft |
| **BI Developer** | 1 100 000 Ft | 1 500 000 Ft | 1 700 000 Ft | 2 200 000 Ft |

*Megjegyzes: Brutto havi fizetes forintban, teljes munkaidore, bonusz es egyeb juttatas nelkul.*

### Glassdoor USA rangsor (prezentacio alapjan, 2022)

| Rang | Pozicio | Median fizetes (USD) | Elegedettseg (5-bol) |
|---|---|---|---|
| 3 | Data Scientist | $120,000 | 4.1 |
| 6 | ML Engineer | $130,489 | 4.3 |
| 7 | Data Engineer | $113,960 | 4.3 |
| 35 | Data Analyst | $74,224 | 4.0 |

**ML Engineer vs AI Engineer vs Halado ML Engineer** (kick-off LIVE alapjan):
- A **Machine Learning Engineer** nullarol epit modelleket: egy algoritmust betanit adatok segitsegevel, es igy jon letre a modell
- Az **AI Engineer** elore tanitott (pre-trained) foundation modelleket hasznal es alkalmaz
- A **halado Machine Learning Engineer** kepes az elore tanitott modelleket tovabb finomhangolni (fine tuning) sajat adatokon
- A fine tuning-hoz altalaban kevesebb adat is elegendo, mig nullarol valo tanitashoz tobb ezer adatpont szukseges
- A foundation modellek deep learninghez tartoznak, es a Generativ AI is ezekre epul

**Fontos megfigyelés a gyakorlatból**: Az ML modellek 85-90%-a sosem jut el production-be, vagy hamar lekapcsolják. Ennek fő oka a rossz tervezés és az MLOps hiánya. Egy senior Data Scientist és egy ML Engineer ideális párost alkothat: a Data Scientist a notebook-ban fejleszt és domain tudását alkalmazza, az ML Engineer pedig ebből production-ready pipeline-okat épít.

**Startup vs. multi**: Startupnál gyakran egy ember visz minden adatos feladatot, míg nagyvállalatoknál akár több tíz fős dedikált csapatok dolgoznak külön-külön területeken.

### Szervezeti felepites (prezentacio alapjan)

A prezentacio bemutatja a tipikus nagyvallalati adattudomanyi szervezeti strukturat:
- **CDO (Chief Data Officer)** ala tartozik harom csapat:
  - **Data Science Team**: Modellezés, elemzes, kiserletezés
  - **Data Engineering Team**: Adat-pipeline-ok, infrastruktura, ETL
  - **Data Operations Team**: Üzemeltetés, monitoring, adatminőség

A Data Science eletciklus erettsegi szintjei: Data Collection -> Data Storage -> Data Transformation -> Reporting -> Insights -> Consumption -> Decisions. A Data Engineer az első harom fazisert felelos, a Data Scientist a negyediktol a hatodikig jatszik fo szerepet.

---

## Data Science Folyamat (CRISP-DM)

A Data Science projekt egy iteratív folyamat, amely az alábbi lépésekből áll.

**A prezentacio ket kulonbozo folyamatmodellt mutat be:**

1. **Linearis Data Science folyamat** (dia 14): Understand Business Problem -> Define Analytical Problem -> Define Tech Architecture -> Data Understanding -> Data Preparation -> Data Modelling -> Evaluation -> Deployment -> Feedback (visszacsatolasi hurkokkal az egyes fazisok kozott)

2. **CRISP-DM harom fazisa reszletesen** (dia 15):
   - **Conceptualisation**: Klinikusokkal/szakertokkel valo egyeztetes, hipotezisek megfogalmazasa, irodalomfeldolgozas, adatkovetelmeny-elemzes, prediktorok azonositasa, inkluzios/exkluzios kriteriumok meghatarozasa
   - **Exploratory (Discovery)**: Adatok feltarasa, ETL fejlesztes, adat-szotaralkotot es adatminoseg-ellenorzes, algoritmus kivalasztas, egyszeru validalas, teljesitmeny meres, prototipus fejlesztes
   - **Delivery**: Ujabb adatforrasok azonositasa, ETL optimalizalas, adatminoseg-felulvizsgalat, modell finomhangolas, keresztvalidalas, teljesitmeny meres, API/GUI/UX/dashboard fejlesztes

### 1. Üzleti probléma megértése (Business Understanding)
- Felismerni az üzleti problémát és **jó kérdéseket feltenni**
- Példa: "Miért csökken az árbevételünk?" -> jobb kérdés: "Miért hagyják el az ügyfeleink a szolgáltatásunkat?"
- A jó kérdésfeltevés az egyik legfontosabb üzleti képesség

### 2. ML problémává alakítás (Define Analytical Problem)
- Eldönteni, hogy megoldható-e ML-lel a probléma
- Példa: gép meghibásodásának előrejelzése -> bináris osztályozás (elromlik-e a következő hónapban: igen/nem)
- Megvizsgálni: vannak-e adatok? Van-e megfelelő hardver? Elérhető-e az adat a predikció időpontjában?

### 3. Adatmegértés (Data Understanding)
- Adatok minőségének, mennyiségének, relevanciájának vizsgálata
- Új feature-ök lehetőségeinek felismerése
- EDA (Exploratory Data Analysis) -- felderítő adatelemzés

### 4. Adat-előkészítés (Data Preparation)
- Adattisztítás, transzformáció, előfeldolgozás
- Akár maga az adattisztítás is megoldható ML-lel (konkrét példa: 99,x%-os pontosság)
- Iteratív: gyakran vissza kell térni az adatmegértéshez

### 5. Modellezés (Modeling)
- Baseline modell létrehozása (egyszerű kiindulás)
- Különböző algoritmusok kipróbálása
- Feature engineering -- domain tudás konvertálása feature-ökké

### 6. Kiértékelés (Evaluation)
- Modellek összehasonlítása metrikák alapján
- Lehet, hogy vissza kell menni egészen az üzleti probléma megértéséig
- Az ML fejlesztés R&D (kutatás-fejlesztés) jellegű: nem mindig triviális, hogy megoldható-e a feladat

### 7. Üzembe helyezés (Deployment) és Inference
- Szolgáltatás létrehozása, ahol a modell predikciókat ad új adatokra
- **MLOps**: a modell hosszú távú működésének biztosítása
- Folyamatos monitorozás szükséges (data drift figyelése)

> **Gyakorlati tanulság a LIVE alkalomról**: Az AI projektek 80-90%-os bukási arányának fő okai: nem megfelelő use case választás, adatminőségi problémák, az üzleti támogatottság hiánya, a tervezés és üzemeltetés hiányosságai. Az is előfordul, hogy az érintettek (pl. orvosok) ellenérdekeltek és nem használják az eszközt.

---

## Algoritmus vs. Modell

Ez a különbségtétel fontos és gyakran összekevert:

| | ML Algoritmus | ML Modell |
|---|---|---|
| **Állapot** | Még nincs betanítva | Már betanított |
| **Mikor használjuk** | Kiválasztjuk, melyiket próbáljuk ki | Kiértékelésnél, inference-nél |
| **Analógia** | Üres kenyérsütő formák | Kisült kenyerek |

Tehát: előbb **algoritmusokat** választunk, betanítjuk őket adatokkal, és az eredmény a **modell**, amely képes predikciókat adni.

**Formalis definiciok a prezentaciobol** (PDF dia):

| | **Modell** | **Algoritmus** |
|---|---|---|
| **Definicio** | Egy algoritmus kifejezesenek eredmenye, amely rejtett mintazatokat azonosit vagy predikciokat keszit | Jol definialt programok vagy utasitasok halmaza, amelyet osszetett problemak megoldasara hasznalnak |
| **Mire hivatkozik** | Reprezentalja, amit az algoritmus mar megtanult | A gepi tanulas motorjai, amelyek adathalmazbol modellt allitanak elo |
| **Technikai jelleg** | Egy szamitogep-program, amely specifikus utasitasokat es adatstrukturakat tartalmaz | Statisztikan, kalkulus es linearis algebran alapulnak |

A folyamat vizualisan: `Adat -> Algoritmus f(x) -> Modell`

---

## ML Tanulási Paradigmák

### Felügyelt tanulás (Supervised Learning)

A legelterjedtebb és általában legpontosabb megközelítés.

**Lényege**: Rendelkezésre állnak **címkézett adatok** (ismert bemenet-kimenet párok). A modell ezekből tanul, és új adatokra prediktál.

**A címkék forrásai** (gyakorlati példák):
- **Spam szűrés**: A Gmail besorolja az e-maileket spam/nem spam kategóriákba
- **Rákdiagnosztika**: A radiológus megjelöli az MRI felvételen a tumor helyét
- **Ügyfélemorzsolódás**: Történeti adatokból látjuk, ki mondta le az előfizetést
- **Gyűlöletbeszéd detektálás**: Önkéntesek címkézik az internetes kommenteket
- **Lopás felismerés**: Bizonyított esetek alapján hozhatunk létre címkéket

**Két fő feladattípus**: osztályozás és regresszió (lásd lentebb).

### Nem felügyelt tanulás (Unsupervised Learning)

**Lényege**: **Nincsenek címkék**, a modellnek magának kell mintázatokat felismernie.

**Fontos**: Törekedni kell arra, hogy lehetőleg felügyelt tanulási problémává alakítsuk a feladatot, mert az nagyobb pontosságot biztosít. De a nem felügyelt tanulás jól támogathatja a felügyelt tanulást (pl. klaszterezés eredménye új feature-ként).

**Fő területek**:
- **Klaszterezés**: Adatok csoportokba rendezése címkék nélkül
- **Dimenziócsökkentés**: Sok dimenzió lecsökkentése 2-3-ra vizualizációhoz, vagy a pontosság növeléséhez
- **Ajánlórendszerek**: Content-based és kollaboratív filtering

### Félig felügyelt tanulás (Semi-supervised Learning)

**Lényege**: Az adatok **egy részéhez vannak címkék**, a többihez nincsenek.

**Működése**:
1. A meglévő címkézett adatokkal betanítunk egy felügyelt modellt
2. A modellel prediktáljuk a címkézetlen adatokat
3. A magas konfidenciájú predikciókat elfogadjuk új címkékként
4. Újratanítás a bővített adathalmazon
5. Ideális esetben szúrópróbaszerűen validáljuk az új címkéket

**Mikor alkalmazzuk**: Amikor sok címkézetlen adat áll rendelkezésre és az emberi címkézés drága vagy időigényes. Üzleti döntés kérdése: mérlegelni kell a címkézés költségeit, az elérhető pontosságot és az üzleti igényeket.

### Megerősítéses tanulás (Reinforcement Learning)

**Lényege**: Egy **ágens** akciókat hajt végre egy **környezetben**, és **jutalmat** vagy **büntetést** kap. A cél: maximalizálni az összegyűjtött jutalmat.

**Működési modell**:
- **Ágens**: A döntéshozó entitás (pl. Mario figura, tőzsdei kereskedő bot)
- **Környezet**: A világ, amelyben az ágens működik (pl. a játék, a tőzsde)
- **Akció**: Az ágens cselekvése (ugrás, vásárlás, eladás, várakozás)
- **Jutalom/büntetés**: A környezet visszacsatolása (pontgyűjtés, nyereség/veszteség)

**Példák**:
- **Játék (Mario)**: Az ágens megtanulja, hogy a kérdőjelhez fejlelés gombát ad, és a gomba jutalom. Ha ellenfébe ütközik, büntetést kap.
- **Tőzsdei kereskedés**: Az ágens vesz/elad/vár, és a nyereség/veszteség adja a jutalmat/büntetést.

**A prezentacio altal kiemelt RL alkalmazasi teruletek**: Real-time decisions, Game AI, Robot Navigation, Skill Acquisition, Learning Tasks.

**Jellemző**: A három paradigma közül a reinforcement learning hasonlít leginkább az emberi tanulásra, hiszen mi is környezeti megerősítések alapján fejlődünk.

### Tanulasi paradigmak rendszere (prezentacio dia alapjan)

A prezentacio egy reszletes faobraban mutatja a tanulasi paradigmak rendszeret:

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

**Artificial Intelligence** (legkulso reteg):
- Rule Based Systems, Game Playing, Knowledge Representation and Reasoning, Propositional Calculus, Cognitive Modeling, Planning, Search Algorithms

**Machine Learning** (kozepso reteg):
- Support Vector Machines (SVM), Linear Regression, Logistic Regression, Random Forest, Gaussian Process Regression, K-Means Clustering

**Deep Learning** (belso reteg):
- MLP (Multi-Layer Perceptron), CNN (Convolutional Neural Network), GAN (Generative Adversarial Network), RBFN (Radial Basis Function Network), LSTM (Long Short-Term Memory), RNN (Recurrent Neural Network), Autoencoders

### ML algortimusok nepszerusege (trend grafikon, 2010-2019)

A prezentacio egy Google Trends alapu grafikont mutat az atlagos havi keresesek alakulasarol:
- **Deep Learning**: 2014-tol robbanasszeru novekedes, 2017-tol dominans (ertek: ~100)
- **SVM**: Stabil nepszeruseg (~30-40), enyhén csokkeno
- **Neural Networks**: Lassú csokkenés, majd stabilizalodas (~25-30)
- **K-Means**: Lassú növekedés (~20)
- **Decision Trees**: Stabil, alacsony ertek (~5)

### Mikor melyiket válasszuk?

| Szempont | Klasszikus ML | Deep Learning |
|---|---|---|
| **Adat mennyiség** | Kevés adat (néhány száz - néhány ezer) | Sok adat (milliók - milliárdok) |
| **Hardver** | Átlagos számítógép elegendő | GPU (videokártya) szükséges |
| **Feature engineering** | Ember végzi, domain tudás kell | Részben vagy egészben automatizált |
| **Tipikus terület** | Táblázatos adatok, kisebb adathalmazok | Kép, hang, szöveg, nagy adathalmazok |
| **Átláthatóság** | Jobban értelmezhető | "Fekete doboz" jellegű |

### Fontos árnyalatok
- **Computer vision** esetén szinte mindig deep learning-et használunk, még akár 80-500 adatponttól is (pl. CT felvételek)
- **Nem mindig a deep learning a legjobb**: Egy logisztikus regresszió vagy random forest gyakran felülmúlja a deep learning-et táblázatos adatokon
- **Mindig az adattól függ**: Érdemes több algoritmust kipróbálni és összehasonlítani
- Az AI > ML > Deep Learning hierarchia: a deep learning az ML részhalmaza, az ML az AI részhalmaza

### ML vs. DL dontesi folyamatabra (prezentaciobol)

```
Van-e jo hardver (GPU) ES sok adat?
|
|-- IGEN --> DEEP LEARNING
|             (automatikus feature extraction + classification egyutt)
|
|-- NEM  --> MACHINE LEARNING (klasszikus)
              (ember vegzi a feature extraction-t, kulon classification lepes)
```

A prezentacio szemleletesen mutatja a kulonbseget:
- **ML**: Input -> Feature extraction (ember vegzi) -> Classification (halo) -> Output
- **DL**: Input -> Feature extraction + Classification (egyetlen mely halo vegzi) -> Output

### Feature engineering vs. automatikus feature extraction
- **Kevés adat**: Több feature engineering szükséges, a domain tudás értéke nő
- **Sok adat + jó hardver**: End-to-end deep learning lehetséges, minimális előfeldolgozással

---

## Feladattípusok

### Osztályozás (Classification)

**Definíció**: Adatpontok előre meghatározott kategóriákba sorolása. Felügyelt tanulási feladat.

**Bináris osztályozás** (a leggyakoribb ML feladat):
- Spam / nem spam
- Lemorzsolódik / nem morzsolódik le
- Csalás / nem csalás
- Gyűlöletbeszéd / nem gyűlöletbeszéd
- Kutya / macska a képen
- Rák van / nincs rák az MRI felvételen

**Multiclass classification** (több kategória):
- Ügyfélszolgálati e-mailek kategorizálása (akár 250 osztály)
- Képfelismerés (több állat- vagy tárgyosztály)

**Tipikus alkalmazások** (prezentacio es transzkriptek alapjan): diagnosztika, fraud detection, képosztályozás, gyűlöletbeszéd detektálás, customer retention, Image Classification, Identity Fraud Detection

### Regresszió (Regression)

**Definíció**: Folytonos érték előrejelzése. Szintén felügyelt tanulási feladat.

**Példa**: "Mennyi ruhát adunk el a következő hónapban?" -- a válasz egy konkrét szám (pl. 1500 db), nem egy kategória.

**Tipikus alkalmazások** (prezentacio es transzkriptek alapjan):
- Időjárás-előrejelzés / Weather Forecasting (hány Celsius fok lesz holnap?)
- Bevétel-predikció (sales, marketing adatok) / Market Forecasting
- Árfolyam-előrejelzés (tőzsde, deviza)
- Várható élettartam becslés / Estimating life expectancy
- Populációbecslés / Population Growth Prediction
- Reklam nepszeruseg elorejlzes / Advertising Popularity Prediction

**Különbség az osztályozástól**: Az osztályozás kategóriákat rendel (hideg/meleg), a regresszió pontos értéket prediktál (23,5 Celsius fok).

### Klaszterezés (Clustering)

**Definíció**: Adatpontok csoportokba rendezése **címkék nélkül**. Nem felügyelt tanulási feladat.

**Fontos különbség az osztályozástól**:
- Osztályozásnál tudjuk, milyen csoportok vannak (címkék ismertek)
- Klaszterezésnél az algoritmus maga hozza létre a csoportokat
- Az algoritmus **nem tudja megmondani**, mit jelentenek a csoportok -- ezt az elemzőnek kell értelmeznie

**Figyelmeztetés**: A klaszterező algoritmus nem feltétlenül az általunk várt szempont szerint csoportosít. Példa: állatok képeinél nem feltétlenül állatfaj szerint, hanem akár szín alapján csoportosíthat.

**Tipikus alkalmazások** (prezentacio es transzkriptek alapjan):
- Ügyfélszegmentáció / Customer Segmentation (pl. focirajongók, télisport kedvelők azonosítása)
- Targeted marketing / celzott marketing
- Felügyelt tanulást támogató feature generálás
- Structure Discovery (adatstruktúra felfedezése)

### Dimenziócsökkentés (Dimensionality Reduction)

**Definíció**: Az adatok dimenzióinak (oszlopainak) számának csökkentése.

**Miért érdemes alkalmazni**:
- **Vizualizáció**: Ember számára csak 2-3 dimenzió értelmezhető
- **Gyorsabb tanulás**: Kevesebb feature = gyorsabb algoritmus
- **Memória-megtakarítás**: Kevesebb adat tárolandó
- **Pontosság növelése**: Megakadályozza a túltanulást (overfitting), javítja az általánosítóképességet

A prezentaciok alkalmazasi peldai: Meaningful Compression, Big Data Visualisation, Feature Elicitation. A dia egy 3D gomb feluletet mutat, amelyet 2D-be redukálnak -- a szinekkel jelolt pontok elosztasa megmarad, de a dimenzio csokkentes utan konnyebben ertelmezheto a struktúra.

### Ajánlórendszerek (Recommendation Systems)

**Content-based filtering**:
- A tartalom hasonlósága alapján ajánl (pl. ugyanaz a szerző, műfaj, rendező)
- Implicit visszajelzések is használhatók: kattintás, időzés, olvasási idő

**Kollaboratív filtering** (általában pontosabb):
- Felhasználók közötti hasonlóság alapján ajánl
- "Hozzád hasonló felhasználók ezeket is szerették"
- Lájkolások, kommentek, értékelések felhasználása

A prezentacio egy szemleletes diagramot mutat: a **Collaborative Filtering** eseten ket hasonlo felhasznalo ("Similar users") olvasasi szokasai alapjan tortenek az ajanlasok ("Read by her, recommended to him!"), mig a **Content-Based Filtering** eseten az adott felhasznalo altal olvasott tartalom ("Read by user") hasonlosaga alapjan talalunk hasonlo cikkeket ("Similar articles"), es ezeket ajanljuk.

---

## Döntési Segédlet: Melyik Megközelítést Válasszam?

```
Van-e címkézett adat?
|
|-- IGEN (mind címkézett) --> FELÜGYELT TANULÁS
|   |
|   |-- Kategóriát prediktálunk? --> OSZTÁLYOZÁS
|   |   |-- 2 osztály --> Bináris osztályozás (pl. spam/nem spam)
|   |   |-- 2+ osztály --> Multiclass classification
|   |
|   |-- Folytonos értéket prediktálunk? --> REGRESSZIÓ
|       (pl. hőmérséklet, ár, darabszám)
|
|-- RÉSZBEN (csak egy rész címkézett) --> SEMI-SUPERVISED LEARNING
|   (Betanítás a címkézetteken, magas konfidenciájú predikciók elfogadása)
|
|-- NEM --> NEM FELÜGYELT TANULÁS
|   |
|   |-- Csoportokat szeretnénk létrehozni? --> KLASZTEREZÉS
|   |-- Dimenziót szeretnénk csökkenteni? --> DIMENZIÓCSÖKKENTÉS
|   |-- Ajánlást szeretnénk adni? --> AJÁNLÓRENDSZER
|
|-- Valós idejű döntések + környezeti visszacsatolás?
    --> MEGERŐSÍTÉSES TANULÁS
```

**További szempontok**:
- Mindig törekedj a felügyelt tanulásra, ha lehetséges (nagyobb pontosság)
- Táblázatos adat + kevés adat = klasszikus ML (random forest, logisztikus regresszió)
- Kép/hang/szöveg + sok adat = deep learning
- Nem felügyelt tanulás eredményei feature-ként beépíthetők a felügyelt modellbe
- Mindig több algoritmust próbálj ki és metrikák alapján hasonlítsd össze

---

## Összehasonlító Táblázat

| Paradigma | Adat típusa | Címke? | Példa feladat | Tipikus algoritmusok |
|---|---|---|---|---|
| **Felügyelt - Osztályozás** | Címkézett | Igen (kategória) | Spam szűrés, rákdiagnosztika, fraud detection | Logisztikus regresszió, Random Forest, SVM, Neurális hálók |
| **Felügyelt - Regresszió** | Címkézett | Igen (szám) | Árfolyam-előrejelzés, hőmérséklet-becslés | Lineáris regresszió, Random Forest, Gradient Boosting |
| **Nem felügyelt - Klaszterezés** | Címkézetlen | Nem | Ügyfélszegmentáció, targeted marketing | K-Means, DBSCAN, Hierarchikus klaszterezés |
| **Nem felügyelt - Dimenziócsökkentés** | Címkézetlen | Nem | Adatvizualizáció, feature reduction | PCA, t-SNE, UMAP |
| **Nem felügyelt - Ajánlórendszer** | Felhasználói adatok | Nem | Filmajánlás, cikkajánlás | Kollaboratív filtering, Content-based filtering |
| **Félig felügyelt** | Részben címkézett | Részben | Drága címkézésű adatok (pl. orvosi képek) | Self-training, Label Propagation |
| **Megerősítéses** | Környezeti visszacsatolás | Jutalom/büntetés | Robotnavigáció, játékstratégia, tőzsdei kereskedés | Q-Learning, Policy Gradient, DQN |

---

## Gyakori Hibák és Tippek

### Az AI projektek bukásának fő okai (a LIVE alkalomról)

1. **Nem megfelelő use case választás**: Ne erőltessünk AI-t oda, ahol egyszerű szabályalapú megoldás is elegendő. A menedzserek gyakran túlértékelik az AI-t.
2. **Adatminőség, mennyiség, relevancia**: Ha nincsenek megfelelő adatok, az ML nem fog működni. Az adatoknak a predikció pillanatában is elérhetőnek kell lenniük (inference ideje).
3. **Data drift figyelmen kívül hagyása**: Az adatok eloszlása változik az időben. Folyamatos monitorozás és újratanítás szükséges.
4. **Tesztadat helytelen használata**: Ha a tesztadatot is felhasználjuk tanításra, a modell túlzottan optimista eredményeket ad, de a valóságban gyenge lesz.
5. **Üzleti támogatás hiánya**: AI projekt nem indulhat menedzseri támogatás nélkül. A hard ROI (közvetlen megtérülés) rövid távon ritkán pozitív.
6. **Ellenérdekelt felek**: Pl. orvosok nem használják a diagnosztikai AI-t, mert félnek a munkájuk elvesztésétől.
7. **MLOps hiánya**: A modell deployment után is karbantartást igényel. Enélkül a modell hamar elavul.

### Gyakorlati tippek

- **Mindig jó kérdéseket tegyél fel**: A jó kérdés fél válasz. "Miért csökken az árbevétel?" nem elegendő -- "Miért hagyják el az ügyfelek a szolgáltatást?" már jobb.
- **Domain tudás nélkül ne kezdj ML projektet**: Beszélj szakértőkkel, olvass cikkeket az adott területről.
- **Baseline modellel indíts**: Először egy egyszerű modellt hozz létre, és ahhoz viszonyítsd a bonyolultabbakat.
- **Több algoritmust próbálj ki**: Az adattól függ, melyik működik legjobban.
- **Production szemlélettel kezdj**: Már a fejlesztés elején gondolj arra, hogy a modellnek éles környezetben is működnie kell.
- **Az ML fejlesztés R&D jellegű**: Nem garantálható az eredmény, iteratív kísérletezés szükséges.
- **Prediktív karbantartás** az egyik legkönnyebben megtérülő AI alkalmazás az iparban.

---

## ML Fejlesztoi Eszkozok (prezentacio alapjan)

### Python konyvtarak es framework-ok

A prezentacio bemutatja a legfontosabb ML eszkozoket:

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

A prezentacio bemutat egy PyCaret peldakodot es eredmenytablazatot, ahol egy sorban osszehasonlithatok kulonbozo modellek:

```python
# functional API
best = compare_models()
# OOP API
best = s.compare_models()
```

Ez automatikusan kiertekeli a kovetkezo modelleket es metrikaikat (Accuracy, AUC, Recall, Precision, F1, Kappa, MCC, ido):
- Logistic Regression, Ridge Classifier, LDA, Random Forest, Naive Bayes, CatBoost, Gradient Boosting, AdaBoost, Extra Trees, QDA, LightGBM, KNN, Decision Tree, XGBoost, SVM

### MLOps Pipeline architektura (prezentaciobol)

A prezentacio egy tipikus MLOps pipeline-t mutat be:

```
Backend:
H2O AutoML (Trained Models) -> MLflow (Model Registry & Tracking) -> FastAPI (Model API Endpoint)
                                                                            |
Frontend:                                                                   v
Streamlit (Web App Interface)
                |
                v
     [Docker Host Network]
  Backend Container <--> Frontend Container
```

### Fejlesztoi kornyezetek

A prezentacio harom fo fejlesztoi kornyezetet mutat be:
1. **Jupyter Notebook / JupyterLab**: Interaktiv notebook kornyezet, tamogatja Python, R, Julia, C++ nyelveket
2. **Google Colab**: Felhoalapu notebook kornyezet ingyen GPU/TPU hozzaferessel
3. **VS Code / IDE**: Hagyomanyos fejlesztoi kornyezet Python bovitmenyekkel, terminalnal

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

## Kapcsolódó Témák

- -> [02_fejlesztoi_kornyezet_es_pandas.md](02_fejlesztoi_kornyezet_es_pandas.md) -- Fejlesztői környezet, Python, Pandas alapok
- -> [05_felugyelt_tanulasi_algoritmusok.md](05_felugyelt_tanulasi_algoritmusok.md) -- Felügyelt tanulási algoritmusok részletesen (logisztikus regresszió, döntési fák, random forest, SVM)
- -> [13_deep_learning_alapok.md](13_deep_learning_alapok.md) -- Deep Learning alapfogalmak, perceptron, neurális hálózatok, aktivációs függvények

---

## További Források

- **scikit-learn Algorithm Cheat Sheet**: [https://scikit-learn.org/stable/tutorial/machine_learning_map/](https://scikit-learn.org/stable/tutorial/machine_learning_map/) -- Vizuális döntéstámogató a megfelelő algoritmus kiválasztásához
- **Google Machine Learning Crash Course**: [https://developers.google.com/machine-learning/crash-course](https://developers.google.com/machine-learning/crash-course) -- Ingyenes, gyakorlatias ML bevezető
- **Kaggle Learn**: [https://www.kaggle.com/learn](https://www.kaggle.com/learn) -- Interaktív ML kurzusok Python-ban
- **CRISP-DM Modell**: [https://en.wikipedia.org/wiki/Cross-industry_standard_process_for_data_mining](https://en.wikipedia.org/wiki/Cross-industry_standard_process_for_data_mining) -- A Data Science folyamat ipari szabványa
- **MLOps Principles**: [https://ml-ops.org/](https://ml-ops.org/) -- MLOps bevezető és best practices

---

*Forras: Cubix EDU ML Engineering kepzes, 1-2. het videoi es LIVE alkalmak (2026.01.28, 2026.02.04), PDF prezentaciok ("1 Basic concepts.pdf", "2 Tasks of Machine Learning.pdf"), hazi feladat ("1_hazi_feladat.pdf")*
