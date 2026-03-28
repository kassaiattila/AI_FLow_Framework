> Utolso frissites: 2026-03-27 | Forrasok: 02_01 transzkript (Mi az a RAG?) + 02_02 transzkript (Dokumentumok elofeldolgozasa) + 02_10 LIVE alkalom

# RAG Pipeline es Dokumentum Feldolgozas

## Gyors Attekintes
> **RAG** = **Retrieval-Augmented Generation**. A modszer lenyege, hogy az LLM valaszgeneralas elott relevan dokumentumokat keres ki egy tudasbazisbol, ezzel csokkentve a **hallucinacio** kockazatat es frissebb, specifikusabb valaszokat adva. A RAG pipeline nem valtoztatja meg a modell sulyait -- csupan a promptot egesziti ki relevan kontextussal. Ez az osszefoglalo a pipeline felso szintu architekturajat es a dokumentum-elofeldolgozas gyakorlati lepeseit mutatja be.

---

## Kulcsfogalmak

| Fogalom | Jelentes |
|---|---|
| **RAG (Retrieval-Augmented Generation)** | Olyan AI pipeline, amely kulso tudasbazisbol keres relevan informaciokat, es azokat felhasznalva general valaszt. Az LLM sulyai nem valtoznak, csak a prompt egeszul ki. |
| **Retrieval** | A keresesi fazis, amelyben a rendszer a felhasznaloi kerdes alapjan megkeresi a legrelevan dokumentumreszeket a tudasbazisbol. |
| **Augmented Generation** | A valaszgeneralasi fazis, amelyben az LLM a megtalalt kontextus felhasznalasaval general valaszt, igy csokkentve a halluciaciot. |
| **Hallucination (hallucinacio)** | Amikor az LLM magabiztosan, de tartalmilag hibasan valaszol -- nem letezo tenyeket "talal ki". A RAG ezt csokkenti valodi forrasok beillesztesevel. |
| **Grounding** | Az a folyamat, amelyben az LLM valaszat tenyleges, ellenorizheto forrasokhoz kotjuk. A RAG a grounding egyik leggyakoribb modszere. |
| **Chunking (chunkolás)** | A dokumentumok kisebb, ertelmesen keresheto egysegekre (chunk-okra) bontasa. A chunk meret es az overlap strategia kozvetlenul befolyasolja a kereses minoseg et. |
| **Chunk size** | Egy chunk maximalis merete (karakterben vagy tokenben). Tipikusan 200-2000 karakter kozott allitjak, a feladattol fuggoen. |
| **Chunk overlap** | A szomszedos chunkok kozotti atfedes merete. Biztositja, hogy fontos informacio ne vesszen el a hatarokon. Altalaban a chunk meret 10-20%-a. |
| **Metadata (metaadat)** | A chunk-okhoz csatolt kiegeszito informacio (pl. fajltipus, forras, nyelv, keszites datuma), amely lehetove teszi a szurt keresest a vektoradatbazisban. |
| **Document loader** | Komponens, amely kulonbozo fajlformatumokbol (PDF, Word, HTML, Markdown) kinyeri a nyers szoveget. |
| **Text splitter** | Komponens, amely a nyers szoveget chunk-okra bontja valamilyen strategia (fix meretu, rekurziv, szemantikus, cim alapu) szerint. |
| **Context window** | Az LLM vagy embedding modell altal egyszerre feldolgozhato maximalis szoveghossz (tokenben merve). Napjainkban nem ritka az 1 millio tokenes context window sem. |
| **Retrieval pipeline** | A teljes kerdo-valaszoado lancnak az a resze, amely a felhasznaloi kerdestol a relevan chunk-ok visszaadasaig terjed. |
| **Embedding** | A szoveg numerikus vektor-reprezent acioja, amely lehetove teszi a hasonlosag alapu keresest. Az embedding modellek ugy lettek tanitve, hogy a tartalmilag hasonlo szovegek vektorai kozel keruljenek egymashoz. |
| **Vector database (vektoradatbazis)** | Olyan adatbazis, amely vektorokat tarol es lehetove teszi a gyors hasonlosag-alapu (similarity) keresest. |
| **Hybrid search** | Kombinalt keresesi modszer, amely egyidejuleg hasznalt vektoros (szemantikus) es klasszikus szoveges (kulcsszo-alapu) keresest a jobb talalati minoseg erdekeben. |
| **Reranking (ujrarangsorolas)** | A keresesi talalatok masodlagos, minoseg-alapu rangsorolasa. Eloszor mennyisegi alapon keresunk (top-k), majd egy reranker modell a relevancia szerint ujrarendezi oket. |

---

## Miert RAG?

### Az LLM korlatai

A nagy nyelvi modellek (LLM-ek) harom fo korlattal rendelkeznek, amelyeket a RAG cimezni tud:

1. **Hallucinacio**: Az LLM magabiztosan, de tartalmilag pontatlan valaszokat general. Ez kulonosen veszelyes uzleti, jogi vagy orvosi kornyezetben.
2. **Elavult tudas**: Az LLM training cutoff-ja utan keletkezett informaciokat nem ismeri. Egy 2024-ben tanult modell nem tud a 2025-os szabalyozasi valtozasokrol.
3. **Domain-specifikus hianyossagok**: Az LLM altalanos tudassal rendelkezik, de egy ceg belso folyamatait, dokumentacioit, szabalyzatait nem ismeri.

> A kurzus hangsulyt fektet arra, hogy a RAG pipeline nem modositja az AI modell sulyait -- kizarolag a promptot egesziti ki relevan hatterinformacioval. Igy a modell "latja" a valaszhoz szukseges kontextust, ahelyett, hogy a sajat (esetleg pontatlan) memoriajabol dolgozna.

### RAG vs Fine-tuning vs Prompt Engineering

| Szempont | **Prompt Engineering** | **RAG** | **Fine-tuning** |
|---|---|---|---|
| **Leírás** | A prompt gondos megalkotasa pelda/utasitas segitsegevel | Kulso tudasbazisbol keresett kontextus beillesztese a promptba | A modell sulyainak modositasa domain-specifikus adatokkal |
| **Koltseg** | Alacsony | Kozepes (infra + embedding) | Magas (GPU, adat, ido) |
| **Frissesseg** | A modell training cutoff-jaig | Azonnali (adatbazis frissitesevel) | Ujratanitas szukseges |
| **Elony** | Gyors, egyszeruen probalgatható | Friss, forras-alapu, ellenorizheto | Melyen testreszabott viselkedes |
| **Hatranye** | Context window korlat, nem novel tudasbazist | Infra es chunkolasi iteracio szukseges | Draga, lassu, adat kell hozza |
| **Mikor hasznald?** | Egyszeru feladatok, prototipus | Belso tudastaraknal, customer support, dokumentacio | Ha specialis nyelvet/stilust kell tanulnia a modellnek |

A kurzus oktato kiemelete: *"Igazabol minden olyan belsos AI-asszisztens, ami peldaul nagy cegeknel van, vagy valamilyen customer supportot kinal kifele, azok altalaban mind RAG pipeline-nal mukodnek."*

**Valos peldak** (a tananyag alapjan):
- **Cursor** (agentek elotti korszak): a kodbazist beindexeltek, es a chat-with-kod funkciok RAG pipeline-nal mukodtek
- **Salesforce Einstein AI** (2023): RAG pipeline-t tartalmaz
- **Zendesk**: kulonosen ajanlotta customer support rendszerekhez

---

## RAG Architektura Attekintese

A RAG pipeline ket fo fazisbol all: az **indexelesi** (offline) es a **lekerdezesi** (online) fazisbol.

### Indexelesi fazis (offline)

Ez a fazis elore felkesziti a tudasbazist a keresre. A lepesek:

```
Dokumentumok  -->  Betoltes  -->  Tisztitas  -->  Chunkolás  -->  Embedding  -->  Vektor DB
  (PDF, HTML,     (document      (encoding,     (text            (embedding       (tarolás és
   Word, MD,       loader)        format          splitter)        model)           indexeles)
   Excel...)                      validáció)
```

1. **Adatgyujtes es kuralas**: Osszeallitjuk a relevan dokumentumokat. *"Ha szemet megy be, akkor szemet is jon ki"* -- ez fokozottan igaz a RAG pipeline-ra.
2. **Dokumentum betoltes**: A kulonbozo formatumokbol (PDF, HTML, Markdown, Excel, Word) kinyerjuk a nyers szoveget.
3. **Tisztitas es elofeldelogozas**: Enkodolas ellenorzese, felesleges elemek eltavolitasa, strukturalas.
4. **Chunkolás**: A szoveget ertelmes, keresheto egysegekre bontjuk (lasd reszletesen lentebb).
5. **Embedding keszites**: Minden chunk-ot numerikus vektorra alakitunk egy embedding modellel.
6. **Tarolás**: A vektorokat es a hozzajuk kapcsolt metaadatokat vektor adatbazisba irjuk.

### Lekerdezesi fazis (online)

Ez a fazis a felhasznalo kerdesere valaszol:

```
User query  -->  Query embedding  -->  Similarity search  -->  Reranking  -->  Context + Prompt  -->  LLM  -->  Valasz
```

1. **Felhasznaloi kerdes befogadasa**: A user begepeli a kerdeset.
2. **Query embedding**: A kerdest ugyanazzal az embedding modellel vektorra alakitjuk, mint amivel az indexelest vegeztuk.
3. **Similarity search**: A vektoradatbazisban megkeressuk a kerdes-vektorhoz legkozelebb eso chunk-vektorokat (top-k).
4. **Reranking (ujrarangsorolas)**: A top-k talalatot egy reranker modell minoseg szerint ujrarendezi. *"Ez egy ketlepcsos kereses: eloszor mennyisegi alapon keresunk, majd a leszurt talalatokat minoseg ileg rangsoroljuk."*
5. **Prompt osszealliitás**: A releváns chunk-okat hozzáadjuk a prompthoz a felhasználói kérdés mellé.
6. **LLM válaszgenerálás**: Az LLM a kibővített prompt alapján generálja a választ.

> **Fontos**: Az embedding modell es az LLM ket kulon modell. Az embedding modellnek sajat context window-ja van, amelyet a chunkolasnál figyelembe kell venni. Az LLM context window-ja a teljes prompt (kerdes + kontextus) befogadasara szolgal.

### A vektor-ter szemleletes leirasa

Az embedding modell a szovegeket egy tobb szaz dimenzios terbe kepezi le. Ebben a terben:

- **Tartalmilag hasonlo** szovegek vektorai **kozel** kerulnek egymashoz
- **Tartalmilag tavoli** szovegek vektorai **messze** kerulnek egymastol

Pelda (a tananyag alapjan): a deployment-rol szolo dokumentaciok vektorai kozel vannak egymashoz, mig a kulonbozo funkciokat leiro dokumentumok vektorai tavol. Ha a felhasznalo azt kerdezi, *"milyen checklistet kell kovetnem a deployment-nel?"*, a rendszer a deployment-hez kapcsolodo chunk-okat keresi meg.

---

## Dokumentum Elofeldolgozas

### Miert kritikus az elofeldelogozas?

Az elofeldelogozas minosege kozvetlenul meghatarozza a RAG pipeline hatekonysagat. A kurzus oktatoja tobbszor hangsulyt fektet a **"garbage in, garbage out"** elvre:

> *"Egyszer szinte 30-40 szazaleka a dokumentumoknak masfajta enkodolassal volt feldolgozva, es ezert rosszul kerult be a pipeline-ba. Igazabol ez tok csendben meg tudta jonni az egesz pipeline, mert igazabol minden lefutott. Utolag derult ki felhasznaloi visszajelzesek alapjan."*

Ez a pelda jol mutatja, hogy a pipeline nem jelez hibat, ha az adat technikai ertelemben valid, de tartalmilag serult.

### Dokumentum Betoltes (Document Loading)

A betoltes celja, hogy kulonbozo forratipusokbol egysegesen kinyerjuk a nyers szoveget.

**Tamogatando fajlformatumok:**

| Formatum | Kihivasok |
|---|---|
| **PDF** | Tobboszlopos elrendezes, kepek, tablazatok, fejlec/lablex |
| **Word (.docx)** | Beagyazott kepek, formatalas, tablazatok |
| **HTML** | Menu, navigacio, reklam elemek szurese |
| **Markdown** | Heading hierarchia, kodblokkok, linkek |
| **Excel** | Tablazatos adat, tobblapos munkalapok |
| **Programkod** | Szintaxis-specifikus tagolas szukseges |

**Lenyeges szempontok a betoltesnel:**

1. **Enkodolas ellenorzese**: UTF-8 a legelterjedtebb, de regebbi dokumentumokban elofordul Latin-1, Windows-1250 stb. Enkodolasi hiba eseten a szoveg olvashatatlan lesz, es a pipeline ennek ellenere le fog futni.
2. **Fajlformatum-specifikus betoltes**: Kulonbozo parser-t kell hasznalni PDF-hez, HTML-hez, Markdown-hoz stb. Az **unstructured** library peldaul kulon `partition_text`, `partition_html`, `partition_md` fuggvenyeket kinal.
3. **Strukturalatlan vs. strukturalt elemek**: Egy dokumentumban lehetnek vegyes elemek (szoveg, tablazat, kep, kod).

### Tartalom-tipusok es kezelesuk

A kurzus reszletesen kitert a kulonbozo tartalom-tipusok kezelesere:

**Szoveg**:
- Mi a szoveg logikai strukturaja? (bekezdések, fejezetek, alfejezetek)
- Strukturalatlan vagy strukturalt? (pl. jogi szoveg vs. technikai dokumentacio)
- Van-e benne programkod? (kulon tagolas szukseges)

**Tablazat**:
- Ket fo strategia:
  1. **Konverzio HTML vagy Markdown tablazatta**: A szoveges formatum tagolast ad, amit az LLM konnyebben ertelmez
  2. **Kepkent tarolás**: Az egesz tablazat embeddinget kap kepi formaban (multimodalis modellek kepesek erre)
- *"Egy tablazatnal mar nem mindegy, hogy a tablazat melyik reszet adjuk vissza a modellnek."*

**Kep**:
- A mai **multimodalis modellek** (pl. GPT-4V, Gemini) ugyan abban az embedding terben kezelik a kepeket es a szoveget
- Ha a kepen szoveg van, erdemes **OCR**-t futtatni es a kinyert szoveget tarolni
- Alternativa: a kep embeddingjét kozvetlenul a vektoradatbazisba tenni

**Programkod**:
- Kulon kihivas: a chunkolasi strategiak gyakran nem tudjak ertelmesen kezelni
- Az LLM kepes ertelmezni a kodot akkor is, ha a chunk nem teljesen "szajragos"
- Evaluacioval merendő, hogy a kodblokk-tartalmu chunkok milyen minosegu valaszokat eredmenyeznek

### Chunkolasi Strategiak

A chunkolás a dokumentum-elofeldogozás legkritikusabb lepese. A cel: **ertelmes, keresheto szovegesgyseget** letrehozni, amelyek a vektoradatbazisban talalhatoak es a promptba beilleszthetok.

#### Fix meretu (naiv) chunkolás

A legegyszerubb strategia: a szoveget fix karakterszam alapjan bontjuk.

- **Tipikus meret**: 200-2000 karakter (a kurzus 500+-t javasol; 200 "eleg kicsi")
- **Overlap**: Altalaban 10-20% (pl. 500 karakteres chunk eseten 50-100 karakter)
- **Elony**: Egyszeruen implementalhato, kiszamithato
- **Hatrany**: Nem veszi figyelembe a szoveg logikai strukturajat; mondat/bekezdes kozepen is vaghat

```python
# Pelda: fix meretu chunkolás
chunk_size = 500
overlap = 100
chunks = []
for i in range(0, len(text), chunk_size - overlap):
    chunks.append(text[i:i + chunk_size])
```

#### Rekurziv chunkolás (Recursive Text Splitting)

A LangChain `RecursiveCharacterTextSplitter` strategiaja. A szoveget egyre finomabb elvalasztojelek menten bontja:

1. Elobb kettős sortores (`\n\n`) menten probalkozik
2. Ha a chunk meg mindig tul nagy, egyes sortores (`\n`) menten
3. Vegul mondat- vagy szó hataron

- **Elony**: Jobban megőrzi a logikai strukturat, mint a fix meretu megoldas
- **Hatrany**: A hierarchikus bontas nem mindig illeszkedik a dokumentum temat valtojelentosseghez

#### Szemantikus chunkolás (Semantic Chunking)

A szoveget tartalmi-szemantikus hatarok menten bontja, nem pusztan strukturalis jelek alapjan.

- Embedding-hasonlosag alapjan donthet arrol, hogy ket szomszedos mondat ugyan abba a chunk-ba tartozik-e
- **Elony**: A legfinomabb granularitas, tartalmilag koherens chunk-ok
- **Hatrany**: Computacionalisan koltsege sebb (embedding keszites szukseges a bontas soran is)

#### Cim alapu chunkolás (By Title)

Az **unstructured** library altal kinalat `chunk_by_title` strategia. Figyelembe veszi a szoveg heading-hierarchiajat.

- Eloszor a szoveget elemekre bontja (partition): title, narrative text, list item, table, code stb.
- Majd a title-ok menten szervezi chunk-okba
- **Elony**: *"A chunkok kovetik az eredeti szovegnek a strukturajat, es egy-egy chunk az igazabol egy-egy logikai egyseg a szovegbol."*
- **Hatrany**: Fugg a dokumentum strukturaltsagatol; rossz heading-ek eseten rosszul bont

A kurzusban bemutatott pelda:
- Naiv strategia: 3 chunk (mert a soft max korlatozas miatt kevesebb lett)
- By title strategia: 6 chunk -- es minden chunk egy-egy logikai alfejezet (Bevezetes, Document Processing, Vector Embedding stb.)

### Chunk Meret es Overlap Beallitas

A chunk meret megvalasztasa az egyik legfontosabb hangolasi parameter a RAG pipeline-ban.

| Szempont | Kis chunk (200-500) | Nagy chunk (1000-2000+) |
|---|---|---|
| **Keresi pontossag** | Pontosabb talalatot ad | Tobb zaj kerulhet a promptba |
| **Kontextus teljesség** | Hianyos kontextus | Teljesebb kontextus |
| **Token-felhasznalás** | Kevesebb token/talalat | Több token/talalat |
| **Embedding modell** | Jobban illeszkedik kis context window-hoz | Nagy context window szukseges |

**A kurzus oktato tapolasa:**

> *"Hogyha egy egesz oldalt csinalunk egy chunk-ba, akkor nem annyira faj nekunk, hogyha egy nagyobb kontextust kapunk ugy, hogy ilyen hosszabb chunk-okat teszunk be a promptba. Ugye foleg a reasoning modellek egyre jobbak abban, hogy megtalaljak a relevan informaciot egy sokkal strukturalatlanabb promptból is."*

Tehat a nagyobb context window-ok es jobb LLM-ek fele mozdulva a nagyobb chunk meretek egyre kevesbe problematikusak.

**Az overlap szerepe:**

Az overlap biztositja, hogy a chunk-hatarokon ne vesszen el fontos informacio:

- Overlap **nelkul**: ha egy mondat ket chunk hataran van, akkor a vektor-kereses csak az egyik felet adja vissza -> "fel informaciobol kellene megmondani a modellnek a jo valaszt"
- Overlap **-pal**: a szomszedos chunk-ok atfednek, igy a hatarterulet mindket chunk-ban megjelenik

**Ajanlott aranyok:**

| Chunk meret | Javasolt overlap |
|---|---|
| 500 karakter | 50-100 karakter |
| 1000 karakter | 100-200 karakter |
| 2000 karakter | 200-400 karakter |

### Metaadatok Hozzaadasa

A metaadatok nem az embeddingbe kerulnek, hanem a vektoradatbazisban a vektor mellett tarolodnak. Lehetove teszik a **szurt keresest** (filtered search).

**Tipikus metaadatok:**

| Metaadat | Pelda | Hasznalat |
|---|---|---|
| **source** (forras) | `internal_docs/onboarding.md` | Forras szerinti szures |
| **file_type** (fajltipus) | `markdown`, `pdf`, `html` | Formatumspecifikus szures |
| **language** (nyelv) | `hu`, `en` | Nyelv szerinti szures |
| **created_at** | `2025-09-01` | Idobeli szures |
| **category** | `deployment`, `api`, `hr` | Temat szerinti szures |
| **page_number** | `3` | Pontos forras-helyre navigalas |
| **chunk_index** | `0`, `1`, `2` | A chunk sorrendje az eredeti dokumentumban |

A kurzusbol:
> *"Fontos, hogy a chunkolás biztosit nekunk egy metaadatot is, ez azert jo, mert ezt hozza tudjuk majd tarsitani a vektoradatbazisba a vektorhoz. Igy tudunk majd ez alapjan filterezni."*

Pelda: ha ugyanabban a vektoradatbazisban Markdown es HTML forrasok is vannak, a `file_type` metaadat alapjan a kereses leszukitheto csak Markdown forrasokra.

---

## Osszehasonlito Tablazat: Chunkolasi Strategiak

| Strategia | Bontas alapja | Chunk koherencia | Implementacitos koltseg | Mikor hasznald? |
|---|---|---|---|---|
| **Fix meretu** | Karakterszam | Alacsony | Nagyon alacsony | Prototipus, gyors teszteles |
| **Rekurziv** | Sortores-hierarchia | Kozepes | Alacsony | Altalanos szoveges dokumentumok |
| **Cim alapu (by title)** | Heading-ek | Magas | Kozepes | Strukturalt dokumentumok (MD, HTML, PDF fejezetekkel) |
| **Szemantikus** | Embedding-hasonlosag | Nagyon magas | Magas | Amikor a tartalmi koherencia kritikus |
| **Oldalankent** | PDF oldalhatárok | Közepes-Magas | Alacsony | PDF-ek, ahol az oldal = logikai egyseg |

---

## Az unstructured Library Hasznalata

A kurzus az **unstructured** Python libraryt mutatja be a dokumentum-elofeldelogozashoz. A konyvtar ket fo lepesben mukodik:

### 1. Particionálás (Partition)

A partícionalas meg nem chunkolás -- ez a szoveg **elemekre bontasa** a formatum alapjan.

```python
from unstructured.partition.text import partition_text
from unstructured.partition.md import partition_md
from unstructured.partition.html import partition_html

# Text particionálás -> pl. 18 elem
elements_text = partition_text(filename="doc.txt")

# Markdown particionálás -> pl. 15 elem (jobb heading felismeres)
elements_md = partition_md(filename="doc.md")
```

Minden elem kap egy **tipust**: `Title`, `NarrativeText`, `ListItem`, `Table`, `Image`, stb.

> *"Ha hasznaljuk azt a partíciot, ami az adott file-formatumnak megfelelo, akkor maris valoszinuleg jobb strukturalis felbontast tudunk kapni."*

### 2. Chunkolás (Chunk)

A particionalt elemeket chunk-okra bontjuk:

```python
from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title

# Naiv strategia
chunks_naive = chunk_elements(
    elements,
    max_characters=500,
    overlap=100,
    new_after_n_chars=400  # soft maximum
)

# Cim alapu strategia
chunks_by_title = chunk_by_title(
    elements,
    max_characters=500,
    overlap=100
)
```

---

## Embedding Modellek es Context Window

Az embedding modellnek sajat context window-ja van, amit a chunkolasnál figyelembe kell venni:

| Embedding modell | Context window | Megjegyzes |
|---|---|---|
| OpenAI `text-embedding-3-small` | 8191 token | Jo ar-ertek arany |
| OpenAI `text-embedding-3-large` | 8191 token | Magasabb minoseg |
| Sentence-BERT | ~512 token | Open-source, lokalis futtatas |
| E5 / BGE | ~512-8192 token | Open-source, kulonbozo meretek |

> *"Fontos meg az, hogy az embedding modellek nem ugyanaz az elem, aminek aztán beadjuk a promptot. Tehat ezeknek az embedding modelleknek is van egy kontextusablakja, meg van, hogy kb. mekkora szovegeken treningeztek."*

Ha a chunk nagyobb, mint az embedding modell context window-ja, a vektor torz lesz. Ezert a chunk meret hangolasanal az embedding modell korlatait is figyelembe kell venni.

---

## Gyakorlati Utmutato

### Elso RAG Pipeline epitese -- lepesrol lepesre

1. **Adatok osszegyujtese**: Gyujtsd ossze a dokumentumokat egy konyvtarba. Ellenorizd az enkodolast (UTF-8).
2. **Document loader kivalasztasa**: Hasznalja az **unstructured** libraryt vagy a LangChain document loader-eket.
3. **Particionalas**: Futasd a formatum-specifikus partition fuggvenyt (pl. `partition_md` Markdown-ra).
4. **Chunkolási strategia megvalasztasa**: Kezdj a **rekurziv** strategiaval -- ez a leggyakrabban alkalmazott, jo kiindulopont.
5. **Chunk meret es overlap hangolása**: Kiindulopont: `chunk_size=500`, `overlap=100`. Iteralj az evaluacios eredmenyek alapjan.
6. **Metaadatok hozzaadasa**: Csatolj forras, fajltipus, nyelv es datum informaciot minden chunk-hoz.
7. **Embedding keszites**: Hasznalj egy embedding modellt (pl. OpenAI `text-embedding-3-small`) a chunk-ok vektorizalasahoz.
8. **Vektor DB feltoltese**: Toltsd be a vektorokat es metaadatokat egy vektoradatbazisba (pl. ChromaDB, Pinecone, Qdrant).
9. **Kereses tesztelese**: Teszteld a keresest kulonbozo kerdesekkel, es ertekeld a talalatok relevanciajat.
10. **Iteracio**: A chunkolasi parametereket, metaadatokat es keresesi logikát az evaluacios eredmenyek alapjan hangold.

### Checklist az elofeldelogozashoz

- [ ] Dokumentumok enkodolasa ellenorizve (UTF-8)?
- [ ] Fajlformatumok azonositva es megfelelo loader hasznalva?
- [ ] Tablazatok kezelese eldontve (szoveg vs. kep)?
- [ ] Kepek kezelese eldontve (OCR vs. embedding)?
- [ ] Programkod kezelese meghatározva?
- [ ] Chunkolasi strategia kivalasztva es tesztelve?
- [ ] Chunk meret es overlap beallitva?
- [ ] Metaadatok definiálva?
- [ ] Embedding modell kivalasztva (context window ellenorizve)?

---

## Gyakori Hibak es Tippek

### Hibak

| Hiba | Kovetkezmeny | Megoldas |
|---|---|---|
| **Enkodolasi hiba nem eszlelt** | Serult szoveg kerul a pipeline-ba, a rendszer nem jelez | Enkodolas detektalas a betoltesnel (pl. `chardet` library) |
| **Tul kicsi chunk meret** | Hianyos kontextus, nem ertelmes szovegegyseg | Minimum 500 karakter, de inkabb 500-1000 |
| **Overlap nelkul chunkolás** | Fontos informacio elveszik a chunk hatarokon | Mindig hasznalj overlappet (10-20%) |
| **Rossz partition fuggveny** | Heading-ek nem felismerhetek, rossz tagolas | A fajlformátumnak megfelelo partition fuggvenyt hasznald |
| **Metaadatok kihagyasa** | Nem lehet szurni a keresest | Mindig adj hozza legalabb forras es fajltipus metaadatot |
| **Embedding modell context window tullepese** | Torz vektor, rossz keresesi eredmenyek | A chunk meret legyen kisebb, mint az embedding modell context window-ja |

### Tippek

1. **Kezdd egyszeruen**: A cim alapu chunkolás + 500-1000 karakteres chunk meret + 100-200 overlap altalaban jo kiindulás.
2. **Ismereld meg az adatod**: Mielott chunkolnal, nezd meg a dokumentumok strukturajat. PDF-eknel sokszor elegseges az oldal-alapu bontas.
3. **Iteralj**: A chunkolasi strategia hangolasa iterativ folyamat. Az evaluacios eredmenyek mutatjak, hol van javitanivalo.
4. **Hasznalj frameworkot**: Ne implementálj mindent from scratch. Az unstructured library es a LangChain text splitter-ek bevalt megoldasokat kinalnak.
5. **Figyeld a csendben hibazó pipeline-t**: Technikai ertelemben minden lefuthat, mikozben a tartalmi minoseg rossz. Rendszeres emberi ellenorzes es evaluacio szukseges.

---

## A Particio es a Chunkolás Kulonbsege

A kurzus fontos fogalmi kulonbseget tesz a ket lepes kozott:

### Particio (Partition)

A particio a dokumentum **elemekre** bontasa a formatum alapjan. Ez meg nem a vegleges chunkolás -- ez egy elofeldelogozasi lepes, amely az elemek tipusat is azonositja.

Az **unstructured** library particio fuggvenyei:

| Fuggveny | Bemeneti formatum | Pelda |
|---|---|---|
| `partition_text()` | Sima szoveg (.txt) | 18 elem |
| `partition_md()` | Markdown (.md) | 15 elem (jobb heading felismeres) |
| `partition_html()` | HTML weboldalak | Menu, tablazat, kod felis meres |
| `partition_pdf()` | PDF dokumentumok | Oldalankenti feldolgozas |

> *"A partition_text osszesen 18 darabra bontja. Ha ugyanezt a szoveget lefuttatom ugy, hogy Markdown-kent particionalom, akkor maromis csak 15 elem van, es a ket es harom hashtag-eseket is most mar title-kent tudta ertelmezni."*

Tehat a **formatumnak megfelelo partition fuggveny** jobb strukturalis felbontast ad.

### Chunkolás (Chunking)

A chunkolás a particionalt elemekbol kesziti el a vegleges chunk-okat, amelyek a vektoradatbazisba kerulnek. Ket kulonbozo dolog:

- **Particio**: beolvasas + tipusfelismeres (Title, NarrativeText, ListItem, Table, Image, stb.)
- **Chunkolás**: a vegleges keresheto egysegek letrehozasa meretre es logikara optimalizalva

### Az unstructured library altal felismert elem tipusok

| Elem tipus | Leiras |
|---|---|
| `Title` | Cimsor (heading) |
| `NarrativeText` | Osszefuggo szoveg (bekezdes) |
| `ListItem` | Listaelem |
| `Table` | Tablazat |
| `Image` | Kep |
| `Text` | Altalanos szoveg |

---

## LIVE Q&A Kiemelt Pontok (02_10 alkalom alapjan)

A LIVE alkalmon a hallgatok tobb praktikus kerdest vetettek fel a RAG pipeline-nal es az elofeldelogozassal kapcsolatban:

### Embedding generalas nehezseges

- **CUDA hianyaban** (GPU nelkul) a chunk-ok feldolgozasa CPU-n nagyon lassu lehet
- **Megoldas**: Google Colab ingyenes GPU-val, vagy kisebb modellek hasznalata (pl. MiniLM)
- Egy hallgato tapasztalata: *"Otthon CPU-n futtat egy private GPT for all modellt, ami lassabb, de mukodik 16 GB RAM-mal."*
- A Google Colab ingyenes szintje GPU-t biztosit, igy a kod gyorsan futtathatoPython notebookban

### Embedding modellek mukodese

- A **word2vec** pelda jol illusztralja a mûkodest: a modell a szovegkornyezetbol tanul
- A **PyTorch nn.embedding** osztalya vektor-reprezentaciokat tanul (lookup table-kent mukodik)
- A **pre-trained** modellek mar elore betanitott sulyokat tartalmaznak, amelyeket **fine-tuning**-gal tovabb lehet tanitani kisebb, domain-specifikus adathalmazon
- A fine-tuning a RAG pipeline kontextusaban azt jelenti, hogy az embedding modellt a sajat dokumentumainkra optimalizaljuk -- de ez nem feltetlenul szukseges, a legtobb esettben a pre-trained modellek is jo eredmenyt adnak

### Evaluacio es teszteles

- AI fejlesztesben az **evaluaciok** helyettesitik a hagyomanyos unit teszteket, de nem garantaljak a hibamentesseget
- *"Az evaluaciok nem fedik le teljesen a valos hasznaalatot."*
- Az eles kornyezetben torteno teszteles kulonosen fontos AI applikacioknál
- **Test-driven development (TDD)** AI fejlesztesben: eloszor az evaluacios metrikakat es teszt-kerdeseket allitjuk ossze, majd a pipeline-t ezek alapjan iteraljuk

### Hasznos eszkozok a fejleszteshez

Az elso alkalommal az oktatonal a kovetkezo eszkozok kerultek szoban a RAG fejlesztessel kapcsolatban:

| Eszkoz | Mire jo |
|---|---|
| **OLLAMA** | Kicsi modellek lokalis futtatasa, GPU nelkul is |
| **GPT4All** | Kenyelmes UI tobb modellhez, lokalis futtatas |
| **LM Studio** | Open source modell-futtato kliens |
| **Google Colab** | Ingyenes felhobeli GPU a kiserletezeshez |

### A hazi feladatok megkozelitese

- A kurzus hazijai iterativ modszertant kovetnek: *"Kezdjek el, es a szukseges kodreszleteket csak a megoldando lepeshez keressek ki es integraljak."*
- A kodok nem veglegesek -- AI generalta reszek is lehetnek bennuk, ezert iteralni kell rajtuk
- A RAG pipeline resz a hallgatok szerint a legnehezebb -- de a legtanulsagosabb is

---

## Kapcsolodo Temak

| Tema | Hol talalhato | Megjegyzes |
|---|---|---|
| **Embedding modellek reszletesen** | 02_03-02_04 leckek | Embedding keszites, modellek osszehasonlitasa |
| **Vektoradatbazisok** | 02_05-02_06 leckek (3. guide) | ChromaDB, Pinecone, hasonlosagi kereses |
| **Kereses es reranking** | 02_07-02_08 leckek | Similarity search, hybrid search, reranker |
| **Promptolas es valaszgeneralas** | 02_09 lecke | A RAG pipeline utolso lepese |
| **LLM alapok** | 01_xx leckek (1. het) | Tokenizacio, attention, transformer architektura |

---

## Tovabbi Forrasok

### Konyvtarak es eszkozok
- **unstructured** library: https://github.com/Unstructured-IO/unstructured
- **LangChain Text Splitters**: https://python.langchain.com/docs/how_to/#text-splitters
- **LlamaIndex Node Parsers**: https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/
- **ChromaDB**: https://www.trychroma.com/

### Cikkek es blogoposztok
- RAG pipeline Wikipedia: https://en.wikipedia.org/wiki/Retrieval-augmented_generation
- Zendesk RAG ajanlás customer support-hoz
- Salesforce Einstein AI dokumentacio

### Embedding modellek
- OpenAI Embeddings API: https://platform.openai.com/docs/guides/embeddings
- Sentence-BERT (SBERT): https://www.sbert.net/
- MTEB Leaderboard (embedding modellek osszehasonlitasa): https://huggingface.co/spaces/mteb/leaderboard

---

## Dontes-tamogato: Mikor Melyik Strategiat Valaszd?

### Prototipus / gyors teszteles
- **Fix meretu chunkolás** (500 karakter, 100 overlap)
- Nincs szukseg a dokumentum-struktura ismeretere
- 5 perc alatt mukodokepes pipeline

### Altalanos szoveges dokumentumok (belso doku, FAQ, utmutatok)
- **Rekurziv chunkolás** (LangChain `RecursiveCharacterTextSplitter`)
- Jo egyensuly a minoseg es az egyszeruseg kozott
- A legtobb tutorialban es production rendszerben ez a kiindulas

### Strukturalt dokumentumok (fejezetes PDF, Markdown, HTML)
- **Cim alapu chunkolás** (unstructured `chunk_by_title`)
- A chunkok logikai egysegeket kovetnek
- Kulonosen hatekonyo belso szabalyzatoknal, technikai dokumentacional

### Magas minosegi kovetelmenyek (jogi szovegek, orvosi dokumentaciok)
- **Szemantikus chunkolás**
- Tartalmilag koherens chunk-ok
- Magasabb szamitasi koltseg, de jobb talalati minoseg

### Nagy mennyisegu PDF
- **Oldal-alapu chunkolás**
- *"Nagyon sok dokumentum olyan, hogy eleve emberi fogyasztasra lett kitalálva, ezert van egy ertelmes strukturaja, amit akar simán az oldalbbontas kovet."*
- Gyors implementacio, kevesebb hangolasi igennyel

---

## Osszefoglalas

A RAG pipeline lehetove teszi, hogy az LLM ne csak a sajat (potencialisan elavult vagy pontatlan) tudasara tamaszkodjon, hanem egy naprakesz, strukturalt tudasbazisbol keressen relevan informaciokat a valaszgeneralas elott. A pipeline sikeressegenek kulcsa a dokumentumok gondos elofeldelogozasaban rejlik:

1. **Ismereld meg az adatot**: Formatum, struktura, tartalom-tipusok
2. **Valaszd ki a megfelelo chunkolasi strategiat**: Fix meretu -> Rekurziv -> Cim alapu -> Szemantikus (novekvo minosegben)
3. **Hangold a parametreket**: Chunk meret, overlap, metaadatok
4. **Evaluálj es iterálj**: A pipeline minosege csak valodi tesztkerdesekkel es felhasznaloi visszajelzesekkel meerheto
5. **Figyeld a csendben hibazó pipeline-t**: Minden lefuthat technikai ertelemben, mikozben a tartalmi minoseg rossz

A kovetkezo guide (03) a **vektoradatbazisokkal** es a **similarity search**-cel foglalkozik -- ott kerul sor az itt letrehozott chunk-ok tenyleges tarolasara es kereshetove tetelere.
