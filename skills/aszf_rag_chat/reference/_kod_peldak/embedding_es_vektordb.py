"""
Embedding modellek es vektoradatbazisok -- gyakorlati peldak
=============================================================

Ez a fajl a RAG pipeline embedding es vektorkeresei reteget mutatja be:
    1. Embedding generalas (mock + opcionalis OpenAI)
    2. Cosine similarity szamitas scratch-bol (numpy)
    3. Egyszeru in-memory vektor store (numpy-alapu, kulon DB nelkul)
    4. ChromaDB hasznalat (try/except ha nincs telepitve)
    5. FAISS hasznalat (try/except ha nincs telepitve)
    6. Szemantikus kereses demo
    7. Top-K retrieval metadata szuressel es reranking

Forras: Cubix EDU -- LLM es RAG kurzus (2. modul, 03-06 leckek)

Fuggosegek:
    - numpy (kotelezo)
    - chromadb (opcionalis)
    - faiss-cpu VAGY faiss-gpu (opcionalis)
    - openai (opcionalis)
"""

import json
import time

import numpy as np

# =============================================================================
# 1. EMBEDDING GENERALAS
# =============================================================================

def generate_mock_embedding(text: str, dim: int = 384) -> np.ndarray:
    """
    Determinisztikus mock embedding generalas szovegbol.
    A szoveg hash-ebol general reprodukalhato vektort -- csak demonstraciohoz.
    """
    seed = hash(text) % (2**31)
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float32)
    # Azonos szavak azonos dimenziokat erositik -> hasonlo szovegek kozelebb kerulnek
    for word in text.lower().split():
        vec[hash(word) % dim] += 0.5
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def generate_openai_embedding(
    text: str, model: str = "text-embedding-3-small"
) -> np.ndarray | None:
    """OpenAI embedding generalas API-n keresztul. None ha nem elerheto."""
    try:
        from openai import OpenAI
        client = OpenAI()
        response = client.embeddings.create(model=model, input=text)
        return np.array(response.data[0].embedding, dtype=np.float32)
    except ImportError:
        print("[INFO] Az 'openai' csomag nincs telepitve.")
        return None
    except Exception as e:
        print(f"[INFO] OpenAI hiba: {e}")
        return None


def batch_generate_embeddings(
    texts: list[str], dim: int = 384, use_openai: bool = False
) -> np.ndarray:
    """Tobb szoveghez generalunk embeddingeket (mock vagy OpenAI)."""
    if use_openai:
        test_emb = generate_openai_embedding(texts[0])
        if test_emb is not None:
            results = [test_emb]
            for t in texts[1:]:
                emb = generate_openai_embedding(t)
                results.append(emb if emb is not None
                               else generate_mock_embedding(t, dim=test_emb.shape[0]))
            return np.array(results)
    return np.array([generate_mock_embedding(t, dim=dim) for t in texts])


# =============================================================================
# 2. COSINE SIMILARITY SCRATCH-BOL
# =============================================================================

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Cosine similarity szamitas: cos(A,B) = (A . B) / (|A| * |B|)
    Ertek: -1 (ellentetes) .. 0 (fuggetlen) .. +1 (azonos irany)
    """
    dot = np.dot(vec_a, vec_b)
    norm_a, norm_b = np.linalg.norm(vec_a), np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def cosine_similarity_matrix(matrix_a: np.ndarray, matrix_b: np.ndarray) -> np.ndarray:
    """Cosine similarity matrix (n, dim) x (m, dim) -> (n, m)."""
    norms_a = np.linalg.norm(matrix_a, axis=1, keepdims=True)
    norms_b = np.linalg.norm(matrix_b, axis=1, keepdims=True)
    norms_a = np.where(norms_a == 0, 1, norms_a)
    norms_b = np.where(norms_b == 0, 1, norms_b)
    return (matrix_a / norms_a) @ (matrix_b / norms_b).T


def demo_cosine_similarity():
    """Cosine similarity demonstracio kulonbozo szovegparokkal."""
    print("\n" + "=" * 70)
    print("2. COSINE SIMILARITY DEMONSTRACIO")
    print("=" * 70)

    szovegek = [
        "A vektoradatbázis hatékony keresést tesz lehetővé.",
        "Az adatbázisban gyorsan lehet keresni vektorok között.",
        "A macska az ablakpárkányon ült és a madarat figyelte.",
        "Csokitorta recept: liszt, cukor, kakaó, tojás.",
    ]
    embeddings = batch_generate_embeddings(szovegek, dim=384)

    print("\nSzoveg-parok cosine similarity ertekei:")
    for i in range(len(szovegek)):
        for j in range(i + 1, len(szovegek)):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            print(f"  [{i}] vs [{j}]: {sim:.4f}")
            print(f"      {szovegek[i][:55]}")
            print(f"      {szovegek[j][:55]}\n")


# =============================================================================
# 3. EGYSZERU IN-MEMORY VEKTOR STORE (numpy alapu)
# =============================================================================

class SimpleVectorStore:
    """
    Egyszeru in-memory vektoradatbazis numpy-val.
    Brute-force cosine similarity keeressel, Top-K retrieval-lal,
    metadata szuressel es score threshold-dal.
    A kurzusban bemutatott Qdrant funkcionalitas egyszeru valtozata.
    """

    def __init__(self, dimension: int):
        self.dimension = dimension
        self.vectors: list[np.ndarray] = []
        self.payloads: list[dict] = []
        self.ids: list[str] = []

    def add(self, id: str, vector: np.ndarray, payload: dict | None = None):
        """Egy vektor hozzaadasa az adatbazishoz."""
        if vector.shape[0] != self.dimension:
            raise ValueError(f"Dimenzio: vart {self.dimension}, kapott {vector.shape[0]}")
        self.vectors.append(vector)
        self.payloads.append(payload or {})
        self.ids.append(id)

    def add_batch(self, ids: list[str], vectors: np.ndarray,
                  payloads: list[dict] | None = None):
        """Tobb vektor hozzaadasa egyszerre."""
        if payloads is None:
            payloads = [{}] * len(ids)
        for i, (doc_id, vec) in enumerate(zip(ids, vectors, strict=False)):
            self.add(doc_id, vec, payloads[i])

    def search(self, query_vector: np.ndarray, top_k: int = 5,
               score_threshold: float = 0.0,
               filter_fn: callable | None = None) -> list[dict]:
        """
        Top-K kereses cosine similarity alapjan, opcionalis szuressel.
        Return: [{"id": ..., "score": ..., "payload": ...}, ...]
        """
        if not self.vectors:
            return []
        db_matrix = np.array(self.vectors)
        q_norm = query_vector / (np.linalg.norm(query_vector) + 1e-10)
        db_norms = db_matrix / (np.linalg.norm(db_matrix, axis=1, keepdims=True) + 1e-10)
        sims = db_norms @ q_norm

        results = []
        for i, sim in enumerate(sims):
            if sim < score_threshold:
                continue
            if filter_fn and not filter_fn(self.payloads[i]):
                continue
            results.append({"id": self.ids[i], "score": float(sim),
                            "payload": self.payloads[i]})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def stats(self) -> dict:
        """Statisztikak (a kurzus peldajat kovetjuk)."""
        if not self.payloads:
            return {"count": 0}
        categories = {}
        word_counts = []
        for p in self.payloads:
            cat = p.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            wc = p.get("word_count", 0)
            if wc > 0:
                word_counts.append(wc)
        s = {"count": len(self.vectors), "dimension": self.dimension,
             "categories": categories}
        if word_counts:
            s.update({"word_count_min": min(word_counts),
                       "word_count_max": max(word_counts),
                       "word_count_avg": round(sum(word_counts) / len(word_counts), 1)})
        return s

    def __len__(self):
        return len(self.vectors)

    def __repr__(self):
        return f"SimpleVectorStore(dim={self.dimension}, count={len(self)})"


def demo_simple_vector_store():
    """In-memory vektor store demonstracio."""
    print("\n" + "=" * 70)
    print("3. EGYSZERU IN-MEMORY VEKTOR STORE DEMO")
    print("=" * 70)

    documents = [
        {"text": "A Qdrant egy open source vektoradatbázis Docker konténerrel.",
         "category": "composite_element", "word_count": 9},
        {"text": "A collection létrehozásánál meg kell adni a dimenziót.",
         "category": "composite_element", "word_count": 10},
        {"text": "Docker futtatás: docker run -p 6333:6333 qdrant/qdrant",
         "category": "composite_element", "word_count": 8},
        {"text": "Score threshold kiszűri az irreleváns találatokat.",
         "category": "composite_element", "word_count": 7},
        {"text": "| Paraméter | Alapértelmezett | Leírás |",
         "category": "table", "word_count": 5},
        {"text": "A PG vector a PostgreSQL kiterjesztése vektorok tárolására.",
         "category": "composite_element", "word_count": 9},
        {"text": "Az HNSW algoritmus approximatív keresést biztosít.",
         "category": "composite_element", "word_count": 6},
        {"text": "| Chroma | FAISS | Qdrant | sebesség |",
         "category": "table", "word_count": 6},
    ]

    dim = 384
    store = SimpleVectorStore(dimension=dim)
    texts = [d["text"] for d in documents]
    embeddings = batch_generate_embeddings(texts, dim=dim)
    store.add_batch([f"doc_{i}" for i in range(len(documents))], embeddings, documents)

    print(f"\nFeltoltve: {len(store)} dokumentum")
    print(f"Stats: {json.dumps(store.stats(), indent=2, ensure_ascii=False)}")

    # Kereses 1: altalanos
    print("\n--- Kereses: 'vektoradatbázis Docker' ---")
    q = generate_mock_embedding("vektoradatbázis Docker", dim=dim)
    for r in store.search(q, top_k=3):
        print(f"  [{r['score']:.4f}] {r['payload']['text'][:65]}")

    # Kereses 2: kategoria filter (csak table chunkokbol)
    print("\n--- Kategoria filter: csak 'table' ---")
    q = generate_mock_embedding("paraméterek összehasonlítás", dim=dim)
    for r in store.search(q, top_k=3,
                          filter_fn=lambda p: p.get("category") == "table"):
        print(f"  [{r['score']:.4f}] [{r['payload']['category']}] "
              f"{r['payload']['text'][:55]}")

    # Kereses 3: szohossz szures
    print("\n--- Szohossz filter: 8+ szo ---")
    q = generate_mock_embedding("production deployment", dim=dim)
    for r in store.search(q, top_k=3,
                          filter_fn=lambda p: p.get("word_count", 0) >= 8):
        print(f"  [{r['score']:.4f}] ({r['payload']['word_count']} szo) "
              f"{r['payload']['text'][:55]}")


# =============================================================================
# 4. CHROMADB HASZNALAT
# =============================================================================

def demo_chromadb():
    """ChromaDB demonstracio. Kihagyjuk ha nincs telepitve."""
    print("\n" + "=" * 70)
    print("4. CHROMADB DEMO")
    print("=" * 70)

    try:
        import chromadb
    except ImportError:
        print("[KIHAGYVA] A 'chromadb' csomag nincs telepitve.")
        print("  Telepites: pip install chromadb")
        return

    client = chromadb.Client()  # in-memory, nem kell Docker
    collection = client.get_or_create_collection(
        name="demo_docs", metadata={"hnsw:space": "cosine"}
    )

    docs = [
        ("A Qdrant egy open source vektoradatbázis.", "database"),
        ("Docker konténerrel egyszerűen indítható.", "deployment"),
        ("A FAISS gyors vektorkereső könyvtár a Meta-tól.", "library"),
        ("A PG vector a PostgreSQL kiterjesztése.", "database"),
        ("Score threshold szűri az irreleváns találatokat.", "search"),
        ("Csokitorta recept: liszt, cukor, kakaópor.", "recipe"),
    ]

    dim = 384
    collection.add(
        ids=[f"ch_{i}" for i in range(len(docs))],
        documents=[d[0] for d in docs],
        metadatas=[{"category": d[1]} for d in docs],
        embeddings=[generate_mock_embedding(d[0], dim=dim).tolist() for d in docs]
    )
    print(f"Feltoltve: {collection.count()} dokumentum")

    # Kereses
    query = "vektoradatbázis telepítés"
    q_emb = generate_mock_embedding(query, dim=dim).tolist()
    results = collection.query(query_embeddings=[q_emb], n_results=3)
    print(f"\nKereses: '{query}'")
    for i, (doc, dist) in enumerate(zip(results["documents"][0],
                                         results["distances"][0], strict=False)):
        print(f"  [{i+1}] (dist={dist:.4f}) {doc[:65]}")

    # Metadata filterrel
    print("\nMetadata filter (category='database'):")
    res = collection.query(query_embeddings=[q_emb], n_results=3,
                           where={"category": "database"})
    for i, doc in enumerate(res["documents"][0]):
        print(f"  [{i+1}] (dist={res['distances'][0][i]:.4f}) {doc[:65]}")

    client.delete_collection("demo_docs")
    print("Collection torolve.")


# =============================================================================
# 5. FAISS HASZNALAT
# =============================================================================

def demo_faiss():
    """FAISS demonstracio. Kihagyjuk ha nincs telepitve."""
    print("\n" + "=" * 70)
    print("5. FAISS DEMO")
    print("=" * 70)

    try:
        import faiss
    except ImportError:
        print("[KIHAGYVA] A 'faiss' csomag nincs telepitve.")
        print("  Telepites: pip install faiss-cpu  (vagy faiss-gpu)")
        return

    dim = 384
    docs = [
        "A vektoradatbázis hatékony keresést tesz lehetővé.",
        "Az HNSW algoritmus approximatív keresést végez.",
        "Docker konténerrel könnyen indítható a szolgáltatás.",
        "A cosine similarity két vektor hasonlóságát méri.",
        "Production környezetben skálázhatóság szükséges.",
        "A PG vector a PostgreSQL vektoros kiterjesztése.",
        "Csokitorta recept: liszt, cukor, kakaópor.",
    ]

    embeddings = batch_generate_embeddings(docs, dim=dim)
    faiss.normalize_L2(embeddings)  # L2 normalizalas (IP = cosine)

    # Flat index (brute force)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"FAISS index: {index.ntotal} vektor, {dim} dim")

    query = "vektoradatbázis keresés algoritmus"
    q_vec = generate_mock_embedding(query, dim=dim).reshape(1, -1)
    faiss.normalize_L2(q_vec)
    distances, indices = index.search(q_vec, k=3)

    print(f"\nKereses: '{query}' (Top-3)")
    for i in range(3):
        print(f"  [{i+1}] (sim={distances[0][i]:.4f}) {docs[indices[0][i]][:65]}")

    # IVF index (klaszter-alapu, nagyobb adathalmazokhoz)
    print("\n--- IVF index (klaszter-alapu) ---")
    nlist = 2
    quantizer = faiss.IndexFlatIP(dim)
    index_ivf = faiss.IndexIVFFlat(quantizer, dim, nlist)
    index_ivf.train(embeddings)
    index_ivf.add(embeddings)
    index_ivf.nprobe = 2
    d_ivf, i_ivf = index_ivf.search(q_vec, k=3)
    for i in range(3):
        print(f"  [{i+1}] (sim={d_ivf[0][i]:.4f}) {docs[i_ivf[0][i]][:65]}")


# =============================================================================
# 6. SZEMANTIKUS KERESES DEMO
# =============================================================================

def demo_semantic_search():
    """Szemantikus kereses demonstracio a SimpleVectorStore-ral."""
    print("\n" + "=" * 70)
    print("6. SZEMANTIKUS KERESES DEMO")
    print("=" * 70)

    corpus = [
        "A RAG külső tudásbázisból keres releváns információt az LLM válaszhoz.",
        "A vektoradatbázisok szemantikai keresést tesznek lehetővé embeddingekkel.",
        "Az embedding modellek fix méretű vektorrá alakítják a szöveget.",
        "A Docker izolált környezetet biztosít alkalmazások futtatásához.",
        "A PostgreSQL nyílt forráskódú relációs adatbázis-kezelő rendszer.",
        "A re-ranking cross encoder modellel javítja a keresési pontosságot.",
        "Csokitorta: liszt, cukor, kakaópor, tojás. Süssük 180 fokon.",
        "A FAISS GPU támogatással milliárd vektoros keresésre is képes.",
    ]

    dim = 384
    store = SimpleVectorStore(dimension=dim)
    embeddings = batch_generate_embeddings(corpus, dim=dim)
    for i, (text, emb) in enumerate(zip(corpus, embeddings, strict=False)):
        store.add(f"sem_{i}", emb, {"text": text, "word_count": len(text.split())})

    print(f"Korpusz: {len(store)} dokumentum")

    queries = [
        ("Hogyan működik a szemantikai keresés?", "domain-specifikus"),
        ("Mi az a RAG és mire jó?", "kozeli fogalom"),
        ("recept sütemény készítés", "out-of-domain"),
    ]
    for query, qtype in queries:
        print(f"\n--- ({qtype}): '{query}' ---")
        q_emb = generate_mock_embedding(query, dim=dim)
        for r in store.search(q_emb, top_k=3):
            print(f"  [{r['score']:.4f}] {r['payload']['text'][:70]}")


# =============================================================================
# 7. TOP-K RETRIEVAL METADATA SZURESSEL ES RERANKING
# =============================================================================

class RetrieveAndRerank:
    """
    Retrieve-and-Rerank pipeline.
    1. Retrieve: vektorkeresessel Top-N jeloltet gyujtunk (gyors)
    2. Rerank: ujrarangsoroljuk pontosabb modellel (lassabb, de jobb)

    Mock reranker-t hasznal (valos cross encoder helyett).
    Valos alkalmazasban:
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    """

    def __init__(self, vector_store: SimpleVectorStore):
        self.store = vector_store

    def retrieve(self, query: str, top_k: int = 10,
                 score_threshold: float = 0.0,
                 category_filter: str | None = None,
                 min_word_count: int | None = None) -> list[dict]:
        """Retrieve fazis: vektorkeresessel jelolteket gyujtunk."""
        def filt(payload):
            if category_filter and payload.get("category") != category_filter:
                return False
            return not (min_word_count and payload.get("word_count", 0) < min_word_count)

        q_emb = generate_mock_embedding(query, dim=self.store.dimension)
        return self.store.search(q_emb, top_k=top_k,
                                 score_threshold=score_threshold, filter_fn=filt)

    @staticmethod
    def mock_rerank(query: str, candidates: list[dict]) -> list[dict]:
        """Mock reranking szo-atfedes alapjan (valos: cross encoder)."""
        q_words = set(query.lower().split())
        reranked = []
        for c in candidates:
            t_words = set(c["payload"].get("text", "").lower().split())
            overlap = len(q_words & t_words) / max(len(q_words), 1)
            reranked.append({**c, "rerank_score": overlap, "original_score": c["score"]})
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked

    def retrieve_and_rerank(self, query: str, retrieve_top_k: int = 10,
                            rerank_top_k: int = 5, **kwargs) -> list[dict]:
        """Teljes pipeline: retrieve + rerank."""
        candidates = self.retrieve(query, top_k=retrieve_top_k, **kwargs)
        if not candidates:
            return []
        return self.mock_rerank(query, candidates)[:rerank_top_k]


def demo_retrieve_and_rerank():
    """Retrieve-and-Rerank pipeline demonstracio."""
    print("\n" + "=" * 70)
    print("7. RETRIEVE-AND-RERANK PIPELINE DEMO")
    print("=" * 70)

    documents = [
        {"text": "A Qdrant open source vektoradatbázis Rust-ban írva.",
         "category": "overview", "word_count": 8},
        {"text": "Docker konténerrel indítható: docker run -p 6333:6333.",
         "category": "deployment", "word_count": 8},
        {"text": "Collection létrehozásánál definiáljuk a dimenziót.",
         "category": "config", "word_count": 7},
        {"text": "A Qdrant támogatja a Distributed Deployment módot.",
         "category": "deployment", "word_count": 8},
        {"text": "Qdrant operating parameters a configuration file-ból.",
         "category": "config", "word_count": 7},
        {"text": "A FAISS gyors vektorkereső könyvtár GPU támogatással.",
         "category": "overview", "word_count": 8},
        {"text": "Score threshold szűri az irreleváns találatokat.",
         "category": "search", "word_count": 7},
        {"text": "A cross encoder újrarangsorolja a keresési eredményeket.",
         "category": "search", "word_count": 8},
        {"text": "A PG vector PostgreSQL alapú vektoros tárolás.",
         "category": "overview", "word_count": 7},
        {"text": "Terraform scriptek használhatók production deploymenthez.",
         "category": "deployment", "word_count": 6},
    ]

    dim = 384
    store = SimpleVectorStore(dimension=dim)
    embeddings = batch_generate_embeddings([d["text"] for d in documents], dim=dim)
    for i, (doc, emb) in enumerate(zip(documents, embeddings, strict=False)):
        store.add(f"rr_{i}", emb, doc)

    pipeline = RetrieveAndRerank(store)
    query = "How to configure Qdrant for production deployment?"

    # Retrieve fazis
    print(f"\nKereses: '{query}'")
    print("  Retrieve Top-10, Rerank Top-5\n")
    retrieved = pipeline.retrieve(query, top_k=10)
    print("  RETRIEVE eredmenyek:")
    for i, r in enumerate(retrieved):
        print(f"    [{i+1}] (sim={r['score']:.4f}) {r['payload']['text'][:60]}")

    # Rerank fazis
    reranked = pipeline.retrieve_and_rerank(query, retrieve_top_k=10, rerank_top_k=5)
    print("\n  RERANK eredmenyek:")
    for i, r in enumerate(reranked):
        print(f"    [{i+1}] (rerank={r['rerank_score']:.4f}, "
              f"orig={r['original_score']:.4f}) {r['payload']['text'][:50]}")

    # Kategoria filter
    print("\n--- Kategoria filter: 'config' ---")
    for r in pipeline.retrieve(query, top_k=5, category_filter="config"):
        print(f"  [{r['score']:.4f}] [{r['payload']['category']}] "
              f"{r['payload']['text'][:55]}")

    # Szohossz szures
    print("\n--- Szohossz filter: min 8 szo ---")
    for r in pipeline.retrieve(query, top_k=5, min_word_count=8):
        print(f"  [{r['score']:.4f}] ({r['payload']['word_count']} szo) "
              f"{r['payload']['text'][:55]}")


# =============================================================================
# FO PROGRAM
# =============================================================================

def main():
    """Osszes demo futtatasa egymas utan."""
    print("=" * 70)
    print("EMBEDDING MODELLEK ES VEKTORADATBAZISOK -- GYAKORLATI PELDAK")
    print("Cubix EDU -- LLM es RAG kurzus (2. modul)")
    print("=" * 70)
    start = time.time()

    # 1. Embedding generalas
    print("\n" + "=" * 70)
    print("1. EMBEDDING GENERALAS")
    print("=" * 70)
    text = "A vektoradatbázis hatékony keresést tesz lehetővé."
    mock_emb = generate_mock_embedding(text, dim=384)
    print(f"Mock embedding: alak={mock_emb.shape}, norma={np.linalg.norm(mock_emb):.4f}")
    print(f"Elso 10 ertek: {mock_emb[:10]}")
    oai_emb = generate_openai_embedding(text)
    if oai_emb is not None:
        print(f"OpenAI embedding: alak={oai_emb.shape}")
    else:
        print("OpenAI nem elerheto -- mock embeddingeket hasznalunk.")

    # 2-7. Demok
    demo_cosine_similarity()
    demo_simple_vector_store()
    demo_chromadb()
    demo_faiss()
    demo_semantic_search()
    demo_retrieve_and_rerank()

    elapsed = time.time() - start
    print(f"\n{'=' * 70}")
    print(f"OSSZES DEMO BEFEJEZVE ({elapsed:.2f} masodperc)")
    print("=" * 70)


if __name__ == "__main__":
    main()
