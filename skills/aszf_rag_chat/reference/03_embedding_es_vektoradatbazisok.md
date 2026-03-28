# Embedding Modellek es Vektoradatbazisok

## Gyors Attekintes

> Az **embedding** modellek feladata, hogy szoveges (vagy kepes) adatokat fix meretu numerikus vektorokka alakitsanak ugy, hogy a jelentesben hasonlo elemek kozel keruljenek egymashoz a vektorterben. A **vektoradatbazisok** (Chroma, FAISS, Qdrant, PG vector) ezeket a vektorokat taroljan es hatekony **semantic search**-ot tesznek lehetove, meg milliardos rekordszan eseten is. A **retrieve-and-rerank** pipeline lenyege: eloszor gyorsan osszegyujtjuk a jelolt chunkokat vektorkeresessel, majd egy **cross encoder** modellel ujrarangsoroljuk oket a felhasznalo kerdese szempontjabol.

---

## Kulcsfogalmak

| Fogalom | Jelentes |
|---------|----------|
| **Embedding** | Szoveg (vagy kep) fix meretu numerikus vektorra alakitasa, ahol a jelentes megorzodik. A vektor dimenzio tipikusan 384-3072 kozott mozog. |
| **Vektor** | Egy n-dimenzios szamsorozat, amely az adatpont jellemzoit kodoja. Ket vektor kozelsege a jelentesbeli hasonlosagot tukrozi. |
| **Dimenzio** | Az embedding vektor komponenseinek szama (pl. 768, 1024, 1536, 3072). Nagyobb dimenzio tobb informaciot kepes tarolni, de lassubb es tobb memoriat igenyel. |
| **Cosine similarity** | Ket vektor kozotti hasonlosag merese a bezart szog koszinusza alapjan. Erteke -1 (ellenkezik) es +1 (azonos irany) kozott mozog; 0 = nem korrelal. |
| **Semantic search** | Jelentesalapu kereses, amely nem kulcsszavakat, hanem az embedding vektorok kozeleseget hasznalja. Peldaul "hazepites" es "ingatlanfejlesztes" kozel kerulhetnek egymashoz. |
| **Chroma** | Konnyu, Python-native vektoradatbazis, prototipalashoz idealis. Ujabb verzioi mar production-kepes funkcionalitast is kinalnak. |
| **FAISS** | Facebook AI Similarity Search -- nagyon gyors, C++ alapu in-memory vektorkeresei konyvtar. GPU-tamogatasa is van. Adatbazis-szeru metadata-szures nincsen benne. |
| **Weaviate / Qdrant** | Production-kepes, open source vektoradatbazisok Docker-alapu futatassal, metadata-szuressel, REST/gRPC API-val. |
| **Collection** | Egy logikai egyseg a vektoradatbazisban, amely osszetartozo embeddingeket es a hozzajuk kapcsolodo metaadatokat tarolja. Hasonlo egy relaciosadatbazis tablajanak. |
| **Index** | A vektorok elore feldolgozott keresesi strukuraja (pl. HNSW graf, IVF-Flat). Celbadata es dimenzio alapjan kulonbozo index-tipusok letenek. |
| **Dense retrieval** | Surus vektorokkal torteno kereses (minden dimenzio erteket kap). Szemben a sparse retrievallal, amely szora/kulcsszora epul. |
| **Sparse retrieval** | Ritka vektorokkal torteno kereses (pl. BM25, TF-IDF). A legtobb dimenzio nulla; azok a dimenziok kapnak erteket, amelyek a tokenekhez tartoznak. |
| **Hybrid search** | A **dense** es **sparse** retrieval kombinalasa egyetlen pipeline-ban, jellemzoen sulyzott osszegzessel (reciprocal rank fusion). |
| **Reranking** | A retriever altal visszaadott talalatok ujrarangsorolasa egy pontosabb (de lassabb) modellel, peldaul **cross encoder**-rel. |

---

## Embedding Modellek

### Mi az az Embedding?

Az embedding lenyege, hogy egy szoveget, kepet vagy mas adatot egy fix meretu numerikus vektorra kepezzuk le. Ket fontos tulajdonsaga van:

1. **Jelentes-megorzes**: A hasonlo jellegu szovegek kozel kerulnek egymashoz a vektorterben. Peldaul a "macskak szaporodasa" es a "haziallatok tenyesztese" vektorai kozelebb lesznek egymashoz, mint a "Python programozas" vektorahoz.
2. **Fix dimenzio**: Fuggetlenul a bemeneti szoveg hosszatol, a kimeneti vektor mindig ugyanannyi szambol all (pl. 1024 vagy 1536 dimenzio).

A kurzus peldajaban a haromdimenzios abran a citronsargak a macskakrol szolo vektorok, a lilak pedig programozasrol szoloak. A valosagban ezek sokkal magasabb dimenziojuak -- 700, 1500 vagy 3000+ dimenzio.

#### Hogyan tanulnak az embedding modellek?

A tanitas soran a modell megtanulja, hogy:
- **hasonlo szovegeket kozel huzza** egymashoz a vektorterben,
- **kulonbozo szovegeket tavol tartsa**.

Ez az ugynevezett **contrastive learning** alapelve. Contrastive loss fuggvennyel a modell pozitiv (hasonlo) es negativ (kulonbozo) szovegparokon tanul.

> **Fontos**: Ket kulonbozo embedding modell -- meg azonos dimenzio eseten is -- eltero vektorokat general. Ezert **tilos keverni** kulonbozo modellek embeddingeit egyetlen adatbazisban. Amit modell-A-val vektorizaltunk, azt modell-A-val kell keresni is.

### OpenAI Embedding Modellek

Az OpenAI **closed source** embedding modelleket kinal API-n keresztul.

| Modell | Dimenzio | Kontextus ablak | Jellemzo |
|--------|----------|-----------------|----------|
| `text-embedding-3-small` | 1536 | 8191 token | Gyors, olcso, altalanos hasznalatra |
| `text-embedding-3-large` | 3072 | 8191 token | Nagyobb informacios kapacitas, pontosabb |
| `text-embedding-ada-002` | 1536 | 8191 token | Korabbi generacio, meg szeles korben hasznalt |

#### Elonyok

- **Nincs infrastruktura-koltseg**: Nem kell GPU-t uzemeltetni, a hostingot es skalazast az OpenAI kezeli.
- **Egyszeru integralas**: Egyetlen API-hivas, nincs modell-betoltes vagy torch fuggoseg.
- **Altalanosan jo minoseg**: Sok nyelven es domenen jol teljesitenek.

#### Hatranyok

- **Koltseg**: Token-szintu szamlazas; nagy korpusznal felfuthat.
- **Rate limit**: Idobeli korlatozott hivasszam, ami pipeline sebesseget korlatozhat.
- **Adatvedelem**: A szovegek elhagyjak a sajat infrastrukturankat.

#### Kod pelda

```python
from openai import OpenAI

client = OpenAI()

response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Hogyan konfiguráljuk a Qdrant-ot production környezetben?"
)

embedding_vector = response.data[0].embedding
print(f"Dimenziok szama: {len(embedding_vector)}")  # 1536
```

### HuggingFace Modellek (bge-m3, multilingual)

A HuggingFace **open source** modelleket kinal, amelyeket helyileg (lokalis GPU-n vagy CPU-n) futtathatunk.

| Modell | Dimenzio | Meret | Jellemzo |
|--------|----------|-------|----------|
| `BAAI/bge-m3` | 1024 | ~550M param | Multilingvalis, kivaoan teljesit 100+ nyelven |
| `Qwen/Qwen3-Embedding` | 1024 | ~600M param | Instrukcios task-tamogatas, kivaalo benchmark |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | ~22M param | Nagyon kicsi es gyors, prototipusokhoz |
| `intfloat/multilingual-e5-large` | 1024 | ~560M param | Erosen multilingvalis |

#### Elonyok

- **Teljes kontroll**: A modell a sajat infrastrukturankon fut, nincsen adatvedelmi kockazat.
- **Nincs felhasznalasonkenti koltseg**: Egyszer kell letolteni, utana koltsegmentesen futtathatjuk.
- **Szeles valasztek**: Leaderboard-okon (MTEB) ossze lehet hasonlitani domainre, nyelvre, modalitasra szurve.

#### Hatranyok

- **Infrastruktura igeny**: GPU (CUDA) ajanlott; CPU-n a nagy modellek lassuk lehetnek.
- **Karbantartas**: A modell telepiteset, frissiteset, skalazhatasogatast nekunk kell kezelni.

#### Kod pelda

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")

sentences = [
    "Hogyan konfiguráljuk a vektoradatbázist?",
    "A Qdrant támogatja a distributed deployment módot.",
    "Csokitorta recept könnyedén."
]

embeddings = model.encode(sentences)
print(f"Alak: {embeddings.shape}")  # (3, 1024)
```

### Embedding Dimenzio es Minoseg

A dimenzio valasztas nem trivialis: a **nagyobb dimenzio tobb informaciot** tarol, de **lassubb keresehez** es **nagyobb tarhelyhez** vezet.

#### Az informacios bottleneck jelenseg

A deep learning modelleknél az **information bottleneck** elv ervenyesul: a nagyobb dimenzio tobb nuanszot kepes megragadni, de egy ponton tul a hozzaadott dimenziok mar csak zajt tartalmaznak.

#### Gyakorlati ajanlasok

| Felhasznalasi eset | Ajanlott dimenzio | Peldamodellek |
|--------------------|-------------------|---------------|
| Prototipus, gyors kiserletezes | 384 | all-MiniLM-L6-v2 |
| Altalanos production | 768-1024 | bge-m3, Qwen3 |
| Magas pontossag, nagy korpusz | 1536-3072 | OpenAI text-embedding-3-large |

#### Nyelvi szempontok

A **magyar nyelv** kulonleges kihivast jelent:
- A legtobb modell **angol-dominans** treningadattal tanult, igy a magyar tokenizacio "drágább" (tobb token/szo).
- A **multilingvalis modellek** (bge-m3, multilingual-e5) kifejezetten tobbnyelvure treningeltek.
- Erdemes sajat adatainkon tesztelni, mert a benchmark-eredmenyek nem mindig tukrozik a magyar teljesitmenyt.

#### Modalitas

Vannak **multimodalis** embedding modellek, amelyek szoveget es kepet is kezelnek:
- Egy epulet tervrajza es annak szoieges leirasa is kozel kerulhet egymashoz az embedding terben.
- Peldak: CLIP, ImageBind.
- A kurzusban elsodlegesen szoveges embeddingekkel dolgozunk.

---

## Vektoradatbazisok

### A problema

Amikor millio vagy milliard vektorunk van, a naive "brute force" kereses (mindegyikkel kiszamoljuk a tavolsagot) nem skalazodik. Szukseg van:
1. **Hatekony keresostrukturara** (index),
2. **Metadata-szuresre** (pl. kategoriafilter),
3. **Parhuzamos kiszolgalasra** (sok user egyidoben kerdez),
4. **Perzisztens tarolasra** (adatok ne vesszenek el ujraindulaskor).

### A HNSW algoritmus

A legtobb modern vektoradatbazis a **Hierarchical Navigable Small World (HNSW)** grafot hasznalja.

#### Mukodese

1. **Beszuras**: Amikor uj vektort szurunk be, a rendszer kivalaszt nehany mar letezno vektort, lemeri hozzajuk a **cosine** (vagy mas) tavolsagot, es elekre felfuzi a gráfba.
2. **Kereses**: A user query vektoraval az algoritmus egy veletlen csucsbol indul, megmeri a tavolsagot, majd az osszes szomszedra is megmeri. A legkozelebbi szomszedra ugrik, es ismetli a folyamatot.
3. **Hierarchia**: A graf tobb retegbol all. A felso retegben nagy leptekkel (kluszterek kozott) keresunk, az also retegekben finom-kereses tortenik.

> **Fontos**: Az HNSW **approximativ** -- nem garantalja a legjobb talalat megtalalasat, de nagyon kozel kerul hozza, mikozben nagyrendekkel gyorsabb a brute force-nal.

#### Vizualis pelda

```
Felso reteg:     A ------- B ------- C       (nagy leptekek)
                 |                   |
Kozep reteg:  A1--A2    B1--B2   C1--C2      (kozepes leptekek)
                 |         |         |
Also reteg: a1-a2-a3  b1-b2-b3  c1-c2-c3    (finom kereses)
```

A kereses az also retegen all meg, amikor mar nem talal kozelebbi szomszedot -- ez a **lokalis optimum**.

### Chroma

A **Chroma** egy Python-native vektoradatbazis, amely kivaloan alkalmas **prototipusokhoz** es **oktatasi celokra**.

#### Jellemzoi

- **Telepites**: `pip install chromadb` -- nincsen Docker vagy kulon szolgaltatas.
- **In-process**: A Python folyamaton belul fut, nincsen halozati overhead.
- **Persistent mode**: A `PersistentClient` segitsegevel lemezre ment, igy az adatok tulelnek az ujrainditast.
- **Metadata szures**: Tamogatja a where-feltetelek hasznalatat keresnel.

#### Tipikus hasznalat

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="dokumentumok",
    metadata={"hnsw:space": "cosine"}
)

# Dokumentumok hozzaadasa
collection.add(
    ids=["doc_1", "doc_2"],
    documents=["Ez az elso dokumentum.", "Ez a masodik dokumentum."],
    metadatas=[{"category": "tutorial"}, {"category": "reference"}],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]]
)

# Kereses
results = collection.query(
    query_embeddings=[[0.15, 0.22, ...]],
    n_results=3,
    where={"category": "tutorial"}
)
```

#### Mikor valasszuk?

- Gyors prototipus vagy POC fejlesztes
- Kisebb adathalmaz (< 100K vektor)
- Oktatasi celok, kiserletezesek
- Nem szukseges kulon szolgaltatas

### FAISS

A **FAISS** (Facebook AI Similarity Search) a Meta AI kutatocsoportja altal fejlesztett, **rendkivul gyors** vektorkeresei konyvtar.

#### Jellemzoi

- **Sebesség**: C++ kernel, opcionalis GPU-tamogatas -- a leggyorsabb lehetosegek egyike.
- **Tobbfele index**: Flat (brute force), IVF-Flat (klaszter-alapu), IVF-PQ (kvantalt), HNSW.
- **Nincsen metadata**: Tiszta vektorkeresei konyvtar, metadata-szurest kulon kell megoldani.
- **In-memory**: Alapertelmezetten a memoriaban tarolja a vektorokat (disk-alapu valtozat: `faiss.OnDiskInvertedLists`).

#### Tipikus hasznalat

```python
import faiss
import numpy as np

dimension = 1024
index = faiss.IndexFlatIP(dimension)  # Inner Product (cosine, ha normalizalt)

# Normalizalt vektorok hozzaadasa
vectors = np.random.randn(1000, dimension).astype("float32")
faiss.normalize_L2(vectors)
index.add(vectors)

# Kereses
query = np.random.randn(1, dimension).astype("float32")
faiss.normalize_L2(query)
distances, indices = index.search(query, k=5)

print(f"Top-5 index: {indices[0]}")
print(f"Top-5 similarity: {distances[0]}")
```

#### Mikor valasszuk?

- Millio+ vektoros kereses szukseges, maximalis sebesseg mellett
- GPU-s gyorsitasra van szukseg
- A metadata-szurest alkalmazas-szinten oldjuk meg (pl. pre-filter + FAISS)
- Kutatas, benchmarking

### Weaviate

A **Weaviate** egy production-kepes, open source vektoradatbazis, gazdag funkcionalitassal.

#### Jellemzoi

- **Schema-definicio**: Erosen tipusos, schema-alapu (hasonloan a relaciosadatbazisokhoz).
- **Modularitas**: Plug-in embedding modulok (OpenAI, Cohere, HuggingFace, stb.) -- az adatbazis maga vegzi az embedding generalast.
- **Hibrid kereses**: Beepitett BM25 + vektor kereses (dense + sparse) kombinalas.
- **GraphQL API**: Standardizalt lekerdezesi nyelv.

#### Mikor valasszuk?

- Production alkalmazas, ahol schema-definicio es governance szukseges
- Beepitett embedding generalast szeretnenk (nem kell kulon pipeline)
- Hibrid kereses szukseges (kulcsszo + szemantika)

### Qdrant

A kurzusban a **Qdrant** (a transzkriptben "Quadrant") az elsolegesen hasznalt vektoradatbazis.

#### Jellemzoi

- **Rust kernel**: Nagyon gyors es memoriahatekon, Rust-ban irva.
- **Docker**: Egyetlen parancs az inditas: `docker run -p 6333:6333 qdrant/qdrant`.
- **Dashboard**: Beepitett webes feluleti (localhost:6333/dashboard).
- **Metadata filter**: A HNSW gráfot ugy implementalta, hogy a keresessallel egyidoben lehetseges metaadat-filterezni.
- **Payload**: A vektorokhoz tetszoleges JSON payload kapcsolhato (szoveg, kategorak, szam-attributumok).

#### Tipikus hasznalat

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient(host="localhost", port=6333)

# Collection letrehozas
client.recreate_collection(
    collection_name="docs",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
)

# Feltoltes
client.upsert(
    collection_name="docs",
    points=[
        PointStruct(
            id=1,
            vector=[0.1, 0.2, ...],  # 1024 dimenzio
            payload={"text": "Qdrant Docker config", "category": "tutorial"}
        )
    ]
)

# Kereses score threshold-dal
results = client.search(
    collection_name="docs",
    query_vector=[0.15, 0.22, ...],
    limit=5,
    score_threshold=0.7
)
```

### Osszehasonlitas (mikor melyiket?)

| Szempont | Chroma | FAISS | Qdrant | Weaviate | PG vector |
|----------|--------|-------|--------|----------|-----------|
| **Telepites** | pip install | pip install | Docker | Docker/Cloud | PostgreSQL ext. |
| **Metadata szures** | Igen | Nem (kulon) | Igen (hatekony) | Igen | Igen (SQL) |
| **Sebesség** | Atlagos | Kimagaslo | Jo / Nagyon jo | Jo | Jo (pgvector-scale) |
| **Skalazhatosag** | Korlátozott | In-memory | Distributed | Distributed | PostgreSQL infra |
| **Production-kepes** | Ujabb verzioknal | Igen (de nincs DB) | Igen | Igen | Igen |
| **Hibrid kereses** | Nem | Nem | Plugin-nel | Beepitett | Kulon |
| **API** | Python | Python/C++ | REST/gRPC | GraphQL | SQL |
| **Legjobb hasznalat** | Prototipus, POC | Benchmark, GPU | MVP, production | Enterprise | Meglevo PG infra |

> A kurzusban a Qdrant-ot hasznaljak az elso modulban, a PG vector-t a masodik modulban. A FAISS-t es Chroma-t inkabb prototipushoz ajanlottak.

---

## Embedding Feltoltes Gyakorlat

### Collection Letrehozas

Egy **collection** a vektoradatbazis alapegysege. A letrehozaskor meg kell adni:

1. **Nev**: egyedi azonosito (pl. `"qdrant_docs_openai"`).
2. **Vektor dimenzio**: meg kell egyeznie az embedding modell dimenziojaval (pl. 1024 vagy 1536).
3. **Tavolsag metrika**: `COSINE`, `EUCLID` vagy `DOT` (inner product).

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="localhost", port=6333)

# Ha mar letezik, toroljuk (fejlesztes soran hasznos)
client.delete_collection("my_docs")

# Uj collection
client.create_collection(
    collection_name="my_docs",
    vectors_config=VectorParams(
        size=1024,        # meg kell egyeznie az embedding modellel
        distance=Distance.COSINE
    )
)
```

> **Tipp**: Fejlesztes soran `recreate_collection`-t hasznaljuk, ami torol+letrehoz, igy tobbszori futatasnal nincs nevutkozesi hiba.

### Dokumentum Chunk -> Embedding -> Feltoltes

A teljes pipeline lepeseit a kovetkezo:

#### 1. Dokumentum feldolgozas es chunkalas

```python
from unstructured.partition.md import partition_md

elements = partition_md(filename="docs/configuration.md")

# Chunkokra bontas: mindegyiknek van category-ja es szovege
chunks = []
for elem in elements:
    chunks.append({
        "text": str(elem),
        "category": elem.category,
        "word_count": len(str(elem).split())
    })

print(f"Osszes chunk: {len(chunks)}")  # pl. 532
```

#### 2. Embedding generalas

```python
# Lokalis modell eseten:
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
texts = [c["text"] for c in chunks]
embeddings = model.encode(texts, show_progress_bar=True)

# VAGY OpenAI eseten:
from openai import OpenAI

client_oai = OpenAI()
response = client_oai.embeddings.create(
    model="text-embedding-3-small",
    input=texts
)
embeddings = [d.embedding for d in response.data]
```

#### 3. Feltoltes payload-dal

```python
from qdrant_client.models import PointStruct

points = []
for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    points.append(PointStruct(
        id=i,
        vector=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
        payload={
            "text": chunk["text"],
            "category": chunk["category"],
            "word_count": chunk["word_count"]
        }
    ))

# Batch feltoltes
client.upsert(
    collection_name="my_docs",
    points=points
)

print(f"{len(points)} pont feltoltve.")
```

A kurzus peldajaban **532 dokumentumot** dolgoztak fel, mindegyikhez **1024 dimenzios** vektort generaltak a lokalis Qwen3 modellel.

---

## Kereses es Hasonlosag

### Cosine Similarity

A **cosine similarity** ket vektor kozotti szoget meri. Formulaja:

```
cosine_sim(A, B) = (A . B) / (|A| * |B|)
```

Ahol:
- `A . B` a skalaris szorzat (dot product),
- `|A|` es `|B|` a vektorok hossza (norma).

**Ertelmezese**:
- **1.0**: A ket vektor azonos iranyu -- azonos jelentes.
- **0.0**: Merolegesek -- nincsen kapcsolat.
- **-1.0**: Ellentetesek -- ellenteetes jelentes.

A gyakorlatban az embedding modellek altal generalt vektorok altalaban 0.0 es 1.0 kozott mozognak.

#### Miert cosine es nem euklideszi?

A cosine similarity **iranyerzekeny**, nem hosszerzekeny. Tehat ha ket szoveg embedding-je **azonos iranyba mutat** de kulonbozo hosszuak (ami elojforulhat kulonbozo hosszusagu szovegeknel), a cosine ettol meg magasnal fogja oket ertekeli. Az euklideszi tavolsag viszont buntetne a hosszkulonbseget.

### Semantic Search vs Keyword Search

| Szempont | Keyword Search (BM25) | Semantic Search (embedding) |
|----------|----------------------|----------------------------|
| **Mukodes** | Szo-egyezes, token-frekvencia | Jelentes-alapu vektortavolsag |
| **Szinonimak** | Nem ismeri fel | Felismeri (kozel esnek a terben) |
| **Nyelvi variansok** | Kulon kell kezelni | Automatikusan kezeli |
| **Sebesség** | Nagyon gyors (invertalt index) | Gyors (HNSW), de lassabb mint BM25 |
| **Out-of-domain** | Nincs talalatja, ha nincs szo-egyezes | Visszaad valamit (akaar irrelevansat is) |
| **Egyuttes hasznalatuk** | **Hibrid kereses**: BM25 + vektor | |

### Top-K Kereses es Szures

A **Top-K** kereses a K legkozelebbi vektort adja vissza. De ez nem elegendo a jo minoseghez -- szukseges:

#### Score threshold

```python
results = client.search(
    collection_name="my_docs",
    query_vector=query_embedding,
    limit=10,           # Top-K
    score_threshold=0.7  # Csak 0.7 feletti talalatok
)
```

A score threshold kizarja a **tavoli, kevesbe releváns talalatokat**. Ez kuolonosen fontos **out-of-domain** kerdeseknel (pl. "csokitorta recept" egy Qdrant dokumentacioban), ahol a legjobb talalat is alacsony score-t kap.

#### Metadata filter

A Qdrant-ban a **query filter** segitsegevel szukithetjuk a kereset:

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

# Kategoria szerinti szures
results = client.search(
    collection_name="my_docs",
    query_vector=query_embedding,
    limit=5,
    query_filter=Filter(
        must=[
            FieldCondition(key="category", match=MatchValue(value="table"))
        ]
    )
)

# Szohossz szerinti szures (pl. 10-30 szo kozotti chunkokat kerunk)
results = client.search(
    collection_name="my_docs",
    query_vector=query_embedding,
    limit=5,
    query_filter=Filter(
        must=[
            FieldCondition(key="word_count", range=Range(gte=10, lte=30))
        ]
    )
)
```

A kurzusban bemutatott peldaban:
- 10-30 szo kozott: 12, 29, 22 szavas talalatok
- 0-20 szo kozott: 12, 7, 9 szavas talalatok
- 50+ szo: 61, 71, 70 szavas talalatok

### Hibrid Kereses (dense + sparse)

A **hibrid kereses** egyesiti a kulcsszo-alapu (sparse) es a szemantikus (dense) keresest.

#### Miert fontos?

- A **dense retrieval** jo a szinonimak es parafrazisok kezelesen, de gyenge lehet egzakt kifejezeseknel.
- A **sparse retrieval** (BM25) kivaalo egzakt kifejezeseknel, de nem erti a szemantikai atvikalakat.
- **Egyutt**: a kettot kombinava mindket vilagbol kapjuk a legjobbat.

#### Reciprocal Rank Fusion (RRF)

A leggyakoribb kombinacios modszer az **RRF**:

```
RRF_score(doc) = sum( 1 / (k + rank_i(doc)) )
```

Ahol `rank_i(doc)` a dokumentum helyezese az i-edik kereses szerint, es `k` egy konstans (tipikusan 60).

---

## Retrieve and Rerank Pipeline

A kurzus egyik kozponti temaja a **retrieve-and-rerank** megkozelites, amely ket fazisbol all:

### 1. Retrieve fazis

A **retriever** (vektoradatbazis kereses) gyorsan osszegyujti a jelolt chunkokat -- pl. Top-50.

- Gyors, mert approximativ (HNSW).
- Nem garantaltan a legjobb sorrendben adja vissza.

### 2. Rerank fazis

Egy **cross encoder** modell egyesevel megvizsgalja a jelolt chunkokat es a user query-t, es uj score-t ad.

#### Miert kell rerank?

A retriever **bi-encoder** alapu: a query-t es a dokumentumot kulon vektorizalja, es a vektortavolsagot meri. A **cross encoder** viszont **egyutt** dolgozza fel a ket szoveget, igy pontosabb hasonlosag-becslest ad -- de lassabb.

#### Mukoedes

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Szovegparok kialakitasa: (user query, talalat szovege)
query = "How to configure Qdrant for production deployment?"
candidates = [result.payload["text"] for result in search_results]

pairs = [(query, candidate) for candidate in candidates]
scores = reranker.predict(pairs)

# Rendezes score szerint
ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
top_5 = ranked[:5]
```

#### A kurzus peldaja

A kurzusban bemutattak egy peldat:
- **Kereses**: "HowToConfigureQdrantForProductionDeployment" -- Top-10 talalat
- **Rerank utan**: A TOP-1 megvaltozott:
  - **Rerank elott**: "A 0.8-as Qdrant tamogatja a Distributed Deployment modot" (Docker-specifikus)
  - **Rerank utan**: "Qdrant operating parameters from the configuration file" (konfiguracio-specifikusabb)
- A Docker-es szoveg a 4. helyre csuszott, mert a reranker jobban ertette, hogy a kerdes a **konfiguraciorol** szol, nem a Docker telepitesrol.

> **Fontos**: A re-rank skor es az eredeti cosine similarity skor **nem osszevethetok** -- mas skalan mozognak. De ket re-rank skor egymassal igen, ezert hasznaljuk rendezesre.

---

## Osszehasonlito Tablazat

### Embedding modellek osszehasonlitasa

| Szempont | OpenAI (3-small) | OpenAI (3-large) | bge-m3 | Qwen3 (0.6B) | all-MiniLM |
|----------|-------------------|-------------------|--------|---------------|------------|
| **Dimenzio** | 1536 | 3072 | 1024 | 1024 | 384 |
| **Futtatas** | API | API | Lokalis | Lokalis | Lokalis |
| **Koltseg** | $/token | $/token | Ingyenes | Ingyenes | Ingyenes |
| **Nyelv** | Multi | Multi | Multi (100+) | Multi | Angol-dominans |
| **GPU igeny** | Nem | Nem | Ajanlott | Ajanlott | CPU-n is jo |
| **Legjobb hasznalat** | Production | Max pontossag | Multilingvalis | Instrukcios | Prototipus |

### Vektoradatbazisok osszehasonlitasa

| Szempont | Chroma | FAISS | Qdrant | Weaviate | PG vector |
|----------|--------|-------|--------|----------|-----------|
| **Implementacio** | Python | C++/Python | Rust | Go | PostgreSQL ext. |
| **Metadata filter** | Igen | Nem | Igen (HNSW szinten) | Igen | Igen (SQL) |
| **Perzisztencia** | File-based | Manualis | Automatikus | Automatikus | PostgreSQL |
| **Dashboard** | Nem | Nem | Igen | Igen | pgAdmin |
| **Hibrid kereses** | Nem | Nem | BM25 plugin | Beepitett | Kulon |
| **Distributed** | Nem | Nem | Igen | Igen | PG replikacio |
| **Legjobb mikor** | POC, tanulas | Benchmark, kutatas | MVP -> prod | Enterprise | Meglevo PG |

---

## Gyakorlati Utmutato

### 1. Kornyezet elokeszitese

```bash
pip install chromadb faiss-cpu qdrant-client numpy openai sentence-transformers
# VAGY GPU-s FAISS: pip install faiss-gpu
# Docker Qdrant inditasa:
docker run -p 6333:6333 qdrant/qdrant
```

### 2. Embedding modell valasztasa

1. **Hatarozzuk meg a nyelvet**: Magyar szovegekhez multilingvalis modell szukseges (bge-m3, multilingual-e5).
2. **Hatarozzuk meg az infrastrukturat**: Van-e GPU? Ha nem, OpenAI API vagy kis modell (all-MiniLM).
3. **Teszteljunk sajat adatokon**: A benchmarkok hasznos kiindulasok, de a sajat domain-specifikus tesztek fontosabbak.

### 3. Vektoradatbazis valasztasa

1. **Prototipus**: Chroma (egyszeru, pip install, nincsen Docker).
2. **MVP / kis production**: Qdrant (Docker, dashboard, metadata filter).
3. **Meglevo PostgreSQL**: PG vector (nem kell uj szolgaltatas).
4. **Maximalis sebesség**: FAISS (de nincsen metadata, kulon kell megoldani).
5. **Enterprise**: Weaviate (schema, governance, beepitett hibrid kereses).

### 4. Pipeline fejlesztese

```
[Dokumentum] -> [Chunkalas] -> [Embedding generalas] -> [Feltoltes a vektorDB-be]
                                                                    |
[User query] -> [Query embedding] -> [Top-K kereses] -> [Reranking] -> [LLM prompt]
```

### 5. Google Colab tipp

Ha nincsen lokalis GPU, a **Google Colab** ingyenes GPU-t biztosit:
- A kurzus soran tobb hallgato is Colab-on futtatta a lokalis embedding modelleket.
- CPU-n a nagy modellek (600M+ parameter) nagyon lassuk lehetnek.

---

## Gyakori Hibak es Tippek

### 1. Kulonbozo embedding modellek keverese

**Hiba**: Az adatbazisba modell-A embeddingeit toltjuk, de a keresest modell-B embeddingevel vegezzuk.

**Kovetkezmeny**: Ertelmetlen talalatok, mert a ket modell mas "nyelven beszel".

**Megoldas**: Mindig ugyanazt a modellt hasznaljuk a feltolteshez es a keresesshez.

### 2. Score threshold elhagyasa

**Hiba**: Nem allitunk be score threshold-ot.

**Kovetkezmeny**: Out-of-domain kerdesekre is kapunk talalatokat, amelyek felrevezeto valaszokhoz vezetnek.

**Megoldas**: Allitsunk be 0.6-0.8 kozott score threshold-ot (az embedding modelltol fuggoen), es teszteljuk out-of-domain kerdesekkel.

### 3. Dimenzio-elteres

**Hiba**: A collection-t 1024 dimenziosra definialjtuk, de 1536 dimenzios embeddingeket probalunk feltolteni.

**Kovetkezmeny**: Hibat dob a vektoradatbazis.

**Megoldas**: Mindig ellenorizzuk, hogy a collection dimenzio megegyezik az embedding modell dimenziojával.

### 4. Tul rovid chunkak

**Hiba**: 2-3 szavas chunkokbol generalt embeddingek.

**Kovetkezmeny**: Kevés informacio, gyenge talalatok.

**Megoldas**: 50-200 szavas chunkokat celozzunk meg, es allitsunk be minimum szohossz filtert.

### 5. Nincs rerank

**Hiba**: Csak a retriever talalatait hasznaljuk kozvetlenul.

**Kovetkezmeny**: A legjobb talalat nem feltetlenul a legrelevansabb.

**Megoldas**: Kerjunk Top-20-at a retriever-tol, es cross encoder-rel rankeljuk a Top-5-re.

### 6. CPU-n lassu az embedding generalas

**Hiba**: 600M parameterews modellt CPU-n futtattunk sok ezres dokumentumra.

**Kovetkezmeny**: Nagyon lassú, akaar orakig is tarthat.

**Megoldas**: Hasznalas Google Colab GPU-t, vagy valtsunk kisebb modellre (all-MiniLM), vagy OpenAI API-t.

### 7. Jupyter Notebook production-ben

**Hiba**: A notebook-ot hasznaljuk production pipeline-kent.

**Kovetkezmeny**: Nehezen karbantarthato, tesztelheto, verziozhatonak kod.

**Megoldas**: A notebook demonstraciohoz jo, de production-hoz Python script (.py) szukseges. A kurzus oktatoja is kiemelte: "általában projektekhez nem ajánlott a Notebook használata".

---

## Kapcsolodo Temak

- **RAG pipeline** (Retrieval-Augmented Generation): Az embeddingek es vektoradatbazisok a RAG legfontosabb komponenseit kepezik. A kovetkezo modul konkret AI asszisztenst epít RAG pipeline-nal.
- **Dokumentum feldolgozas es chunkalas** (elozo lecke): A szovegek csankolasa az embedding elotti lepes.
- **LLM promptba epites**: A retrieved chunkokat a prompthoz adjuk, hogy az LLM kontextusban tudjon valaszolni.
- **Fine tuning**: Sajat domainre finomhangolt embedding modellek javithatjak a keresesi minoseg.
- **Evaluacio**: Az AI applikaciok tesztelese -- ahogy a kurzus eloadoja megjegyezte, az "evaluációk nem garantálják a hibamentességet", de fontosak az iterativ fejleszteshez.

---

## LIVE alkalom kiegeszitesek (02_10)

A LIVE alkalmon tobb gyakorlati kerdes es tapasztalat merult fel:

- **GPU vs CPU**: CUDA nelkul a chunkok feldolgozasa lokalis modellel nagyon lassu vagy nem fut le. A Google Colab ingyenes GPU-t biztosit.
- **Kis modell CPU-n**: Egy hallgato "GPT for all" modellet futtatott CPU-n 16 GB RAM-mal -- lassu, de mukodik.
- **PyTorch nn.Embedding**: A PyTorch beepitett Embedding osztalya vektor-reprezentaciokat tanul; a pre-trained modelleknel mar eloretanított sulyokat hasznalunk, amelyeket fine tuninggal tovabb tanitshatunk.
- **Word2Vec es item2vec**: Az embedding modellek torteneti elodjei, amelyek a szovegkornyezetbol tanulnak vektor-aabrazolasokat.
- **TDD AI fejlesztesben**: Az evaluaciok a tesztek AI-s megfeleloi, de nem garantaljak a hibamentesseget. Az eles kornyezetben torteno teszteles kuolonosen fontos.

---

## Tovabbi Forrasok

### Embedding modell benchmarkok
- **MTEB Leaderboard** (Massive Text Embedding Benchmark): https://huggingface.co/spaces/mteb/leaderboard -- Modelleket domén, nyelv, modalitas es meret szerint szurhetjuk.

### Vektoradatbazis dokumentaciok
- **Qdrant**: https://qdrant.tech/documentation/
- **Chroma**: https://docs.trychroma.com/
- **FAISS**: https://github.com/facebookresearch/faiss/wiki
- **Weaviate**: https://weaviate.io/developers/weaviate
- **PG vector**: https://github.com/pgvector/pgvector

### Embedding modellek
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Sentence Transformers**: https://www.sbert.net/
- **BAAI/bge-m3**: https://huggingface.co/BAAI/bge-m3

### Reranking
- **Cross-encoder modellek**: https://www.sbert.net/docs/cross_encoder/pretrained_models.html

### Eszkozok
- **Google Colab** (ingyenes GPU): https://colab.research.google.com/
- **OLLAMA** (lokalis modellek futtatasa): https://ollama.ai/
- **LM Studio**: https://lmstudio.ai/
