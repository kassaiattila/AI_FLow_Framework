"""
RAG Pipeline - Dokumentum feldolgozas es chunkolasi strategiak

Bemutatja a RAG pipeline dokumentum-elofeldelogozasi fazisait:
  1. Dokumentum betoltes (mock adatokkal, kulso fajlok nelkul)
  2. Chunkolasi strategiak (fix meretu, rekurziv, cim alapu, szemantikus)
  3. Chunk meret / overlap hatas demonstracio
  4. Metaadat-gazdagitas
  5. Egyszeru RAG pipeline demo (vektor DB nelkul -- az a 03-as guide temaja)

Hasznalat:
    python rag_pipeline.py

Fuggesegek:
    - Alapveto mukodes: csak standard library
    - Opcionalis: langchain-text-splitters, tiktoken
"""

import re
import math
import hashlib
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


# --- 1. MOCK DOKUMENTUMOK ---

_RAG_DOC = (
    "# Bevezetes a RAG rendszerekbe\n\n"
    "## Mi az a RAG?\n\n"
    "A Retrieval-Augmented Generation (RAG) egy AI pipeline, amely kulso "
    "tudasbazisbol keres relevan informaciokat, es azokat felhasznalva "
    "general valaszt. Az LLM valaszgeneralas elott relevan dokumentumokat "
    "keres ki, csokkentve a halluciaciot.\n\n"
    "## Miert fontos?\n\n"
    "Az LLM-ek korlatai: hallucinacio, elavult tudas, domain-specifikus "
    "hianyossagok. A RAG nem modositja a modell sulyait, csak a promptot "
    "egesziti ki relevan hatterinformacioval.\n\n"
    "## Valos alkalmazasok\n\n"
    "Peldak: Cursor kodbazis-indexeles, Salesforce Einstein AI, "
    "Zendesk customer support, belsos AI-asszisztensek. "
    "A vektoros keresben a hasonlo tartalmak kozel kerulnek egymashoz."
)

_CHUNK_DOC = (
    "# Dokumentumok elofeldolgozasa\n\n"
    "## Adatminoseg\n\n"
    "Ha szemet megy be, szemet jon ki. Fontos az enkodolas ellenorzese, "
    "mert a hibas enkodolas csendben romlasztja a pipeline minoseget.\n\n"
    "## Szoveg tagolasa\n\n"
    "A szoveget ertelmes egysegekre kell bontani. Kerdesek: "
    "strukturalatlan vagy strukturalt? Van benne tablazat, kep, kod?\n\n"
    "### Tablazatok kezelese\n\n"
    "Ket strategia: HTML/Markdown konverzio, vagy kepkent tarolas "
    "multimodalis embedding-gel.\n\n"
    "### Kepek kezelese\n\n"
    "A multimodalis modellek ugyanabban az embedding terben kezelik "
    "a kepeket es szoveget. OCR-rel szoveg is kinyerheto.\n\n"
    "## Chunkolasi strategiak\n\n"
    "Fix meretu: 500+ karakter, 10-20% overlap javasolt. "
    "Cim alapu: heading-hierarchia menten bont logikai egysegekre. "
    "Szemantikus: embedding-hasonlosag alapjan, de koltseg esebb.\n\n"
    "## Metaadatok\n\n"
    "A metaadatok a vektoradatbazisban a vektor mellett tarolodnak. "
    "Pelda: forras, fajltipus, nyelv, datum, kategoria."
)

_DEPLOY_DOC = (
    "# Deployment Checklist\n\n"
    "## Elokeszites\n\n"
    "Ellenorizd: enkodolas (UTF-8), chunkolasi strategia, embedding "
    "modell, vektor adatbazis, metaadatok.\n\n"
    "## Teszteles\n\n"
    "Iterativ folyamat: tesztkerdesek, talalat-relevancia ertekeles, "
    "parameterek hangolasa, ujraindexeles.\n\n"
    "## Monitoring\n\n"
    "Figyelni kell: valaszidok, talalati minoseg, felhasznaloi "
    "visszajelzesek, adatbazis-meret es frissesseg."
)

MOCK_DOCUMENTS = {
    "rag_bevezetes.md": {"content": _RAG_DOC, "metadata": {
        "source": "kurzus/02_het/rag_bevezetes.md", "file_type": "markdown",
        "language": "hu", "created_at": "2025-09-15", "category": "rag_alapok"}},
    "chunking_guide.md": {"content": _CHUNK_DOC, "metadata": {
        "source": "kurzus/02_het/chunking_guide.md", "file_type": "markdown",
        "language": "hu", "created_at": "2025-09-15", "category": "dokumentum_feldolgozas"}},
    "deployment_checklist.md": {"content": _DEPLOY_DOC, "metadata": {
        "source": "kurzus/02_het/deployment_checklist.md", "file_type": "markdown",
        "language": "hu", "created_at": "2025-09-20", "category": "deployment"}},
}


# --- 2. ADATSTRUKTURAK ---

@dataclass
class Chunk:
    """Egy dokumentum-chunk a RAG pipeline szamara."""
    text: str
    metadata: dict = field(default_factory=dict)
    chunk_id: str = ""
    chunk_index: int = 0

    def __post_init__(self):
        if not self.chunk_id:
            h = hashlib.md5(self.text.encode("utf-8")).hexdigest()[:12]
            self.chunk_id = f"chunk_{h}"

    def __repr__(self):
        preview = self.text[:60].replace("\n", " ")
        return f"Chunk(id={self.chunk_id}, len={len(self.text)}, preview='{preview}...')"

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def estimated_tokens(self) -> int:
        """Becsult token szam (~3.5 karakter/token magyar szovegnel)."""
        return math.ceil(len(self.text) / 3.5)


@dataclass
class Document:
    """Egy betoltott dokumentum a feldolgozas elott."""
    name: str
    content: str
    metadata: dict = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.content)


# --- 3. DOKUMENTUM BETOLTES ---

def load_mock_documents() -> list[Document]:
    """Mock dokumentumok betoltese -- nem igenyel kulso fajlokat."""
    documents = []
    for name, data in MOCK_DOCUMENTS.items():
        doc = Document(
            name=name,
            content=data["content"].strip(),
            metadata=data["metadata"].copy(),
        )
        documents.append(doc)
    print(f"[Betoltes] {len(documents)} dokumentum betoltve:")
    for doc in documents:
        print(f"  - {doc.name} ({doc.char_count} karakter)")
    print()
    return documents


# --- 4. CHUNKOLASI STRATEGIAK ---

def chunk_fixed_size(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Fix meretu chunkolás -- a legegyszerubb strategia.

    A kurzusbol: "Altalaban a legtobb tutorial 200-zal szamol, de az eleg
    kicsi, tehat legalabb 500 vagy nagyobb karakterszamot erdemes valasztani."
    """
    if chunk_size <= 0:
        raise ValueError("A chunk_size-nak pozitivnak kell lennie.")
    if overlap >= chunk_size:
        raise ValueError("Az overlap nem lehet >= chunk_size.")

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]
        if chunk_text.strip():
            chunks.append(chunk_text)
        start += chunk_size - overlap
    return chunks


def chunk_recursive(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    separators: Optional[list[str]] = None,
) -> list[str]:
    """Rekurziv chunkolás -- a LangChain RecursiveCharacterTextSplitter elven.

    A szoveget egyre finomabb elvalasztojelek menten bontja:
    kettos sortores -> egyes sortores -> mondat -> szo -> karakter.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    final_chunks: list[str] = []

    def _split(text_part: str, sep_idx: int = 0):
        # Belfer a chunk meretbe -> kesz
        if len(text_part) <= chunk_size:
            if text_part.strip():
                final_chunks.append(text_part)
            return

        # Elfogytak az elvalasztok -> fix meretu bontas
        if sep_idx >= len(separators) or separators[sep_idx] == "":
            for piece in chunk_fixed_size(text_part, chunk_size, overlap):
                final_chunks.append(piece)
            return

        sep = separators[sep_idx]
        parts = text_part.split(sep)
        current = ""

        for part in parts:
            candidate = (current + sep + part).strip() if current else part.strip()
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current.strip():
                    final_chunks.append(current.strip())
                if len(part) > chunk_size:
                    _split(part, sep_idx + 1)
                    current = ""
                else:
                    current = part.strip()

        if current.strip():
            final_chunks.append(current.strip())

    _split(text)
    return final_chunks


def chunk_by_heading(text: str) -> list[str]:
    """Cim (heading) alapu chunkolás -- Markdown dokumentumokhoz.

    A kurzusból: "A chunkok kovetik az eredeti szoveg strukturajat,
    es egy-egy chunk egy logikai egyseg a szovegbol."
    """
    heading_pattern = re.compile(r"^(#{1,6})\s+", re.MULTILINE)
    positions = [m.start() for m in heading_pattern.finditer(text)]

    if not positions:
        return [text.strip()] if text.strip() else []

    chunks = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        chunk_text = text[pos:end].strip()
        if chunk_text:
            chunks.append(chunk_text)
    return chunks


def chunk_semantic_simple(
    text: str,
    similarity_threshold: float = 0.3,
    min_chunk_size: int = 100,
) -> list[str]:
    """Egyszerusitett szemantikus chunkolás -- embedding modell nelkul.

    Szavak atfedese (Jaccard-hasonlosag) alapjan csoportosit mondatokat.
    Valos kornyezetben embedding modellt erdemes hasznalni.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return []

    def _jaccard(a: str, b: str) -> float:
        wa, wb = set(a.lower().split()), set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    chunks = []
    current = [sentences[0]]

    for i in range(1, len(sentences)):
        sim = _jaccard(sentences[i - 1], sentences[i])
        cur_text = " ".join(current)
        if sim >= similarity_threshold and len(cur_text) < 2000:
            current.append(sentences[i])
        else:
            if len(cur_text) >= min_chunk_size:
                chunks.append(cur_text)
                current = [sentences[i]]
            else:
                current.append(sentences[i])

    remaining = " ".join(current)
    if remaining.strip():
        chunks.append(remaining.strip())
    return chunks


# --- 5. METAADAT-GAZDAGITAS ---

def enrich_metadata(
    chunks: list[str], doc: Document, strategy_name: str = "unknown",
) -> list[Chunk]:
    """Chunk-ok gazdagitasa metaadatokkal.

    A kurzusbol: "A chunkolás biztosit metaadatot is, amit hozza tudunk
    tarsitani a vektoradatbazisba -- igy tudunk ez alapjan filterezni."
    """
    enriched = []
    for i, chunk_text in enumerate(chunks):
        metadata = {
            **doc.metadata,
            "chunk_index": i,
            "chunk_strategy": strategy_name,
            "chunk_char_count": len(chunk_text),
            "chunk_word_count": len(chunk_text.split()),
            "total_chunks_in_doc": len(chunks),
            "source_document": doc.name,
            "processed_at": datetime.now().isoformat(),
        }
        enriched.append(Chunk(text=chunk_text, metadata=metadata, chunk_index=i))
    return enriched


# --- 6. CHUNK MERET / OVERLAP HATAS DEMO ---

def demo_chunk_size_effect(text: str):
    """Bemutatja a kulonbozo chunk_size es overlap konfiguraciok hatasat."""
    print("=" * 70)
    print("CHUNK MERET ES OVERLAP HATAS DEMO")
    print("=" * 70)
    print(f"Szoveg hossza: {len(text)} karakter\n")

    configs = [
        (200, 0, "Kicsi chunk, nincs overlap"),
        (200, 50, "Kicsi chunk, kis overlap"),
        (500, 0, "Kozepes chunk, nincs overlap"),
        (500, 100, "Kozepes chunk, overlap-pal (JAVASOLT)"),
        (1000, 200, "Nagy chunk, nagy overlap"),
    ]

    print(f"{'Konfig':<45} {'Chunks':>7} {'Atl.':>7} {'Min':>5} {'Max':>5}")
    print("-" * 73)
    for size, ovlp, label in configs:
        chs = chunk_fixed_size(text, chunk_size=size, overlap=ovlp)
        if chs:
            avg = sum(len(c) for c in chs) / len(chs)
            mn, mx = min(len(c) for c in chs), max(len(c) for c in chs)
        else:
            avg = mn = mx = 0
        print(f"  {label:<43} {len(chs):>7} {avg:>7.0f} {mn:>5} {mx:>5}")

    print("\nJavasolt kiindulas: chunk_size=500, overlap=100\n")


def compare_strategies(doc: Document):
    """Osszes chunkolasi strategia osszehasonlitasa egyetlen dokumentumon."""
    print("=" * 70)
    print(f"STRATEGIAK OSSZEHASONLITASA: {doc.name}")
    print("=" * 70)
    print(f"Dokumentum: {doc.char_count} karakter\n")

    strategies = {
        "Fix meretu (500/100)": lambda t: chunk_fixed_size(t, 500, 100),
        "Rekurziv (500/100)": lambda t: chunk_recursive(t, 500, 100),
        "Cim (heading) alapu": chunk_by_heading,
        "Szemantikus (egysz.)": chunk_semantic_simple,
    }

    for name, fn in strategies.items():
        chs = fn(doc.content)
        if chs:
            avg = sum(len(c) for c in chs) / len(chs)
            mn, mx = min(len(c) for c in chs), max(len(c) for c in chs)
        else:
            avg = mn = mx = 0
        first = chs[0][:70].replace("\n", " ") + "..." if chs else "-"
        print(f"  {name}:")
        print(f"    {len(chs)} chunk, atlag {avg:.0f} kar, min/max {mn}/{mx}")
        print(f"    Elso: \"{first}\"\n")


def simple_keyword_search(
    query: str, chunks: list[Chunk], top_k: int = 3,
) -> list[tuple[Chunk, float]]:
    """Egyszeru kulcsszo-alapu kereses a vektoros kereses helyett.

    Valos pipeline-ban embedding + similarity search lenne (03-as guide).
    """
    query_words = set(query.lower().split())
    scored = []
    for chunk in chunks:
        chunk_words = set(chunk.text.lower().split())
        if not chunk_words:
            continue
        matches = query_words & chunk_words
        score = len(matches) / len(query_words) if query_words else 0.0
        scored.append((chunk, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def simple_rag_pipeline(query: str, chunks: list[Chunk], top_k: int = 3):
    """RAG pipeline demo: kereses -> kontextus -> prompt generalas.

    A kurzusbol: "A megtalalt dokumentum chunk-okat hozzaadjuk a prompthoz,
    es ezt adjuk be az AI-nak, amely igy relevansabb valaszt tud adni."
    """
    print("-" * 60)
    print(f"  Kerdes: \"{query}\"")
    print("-" * 60)

    # 1. Kereses
    results = simple_keyword_search(query, chunks, top_k=top_k)
    print(f"\n  Top {top_k} talalat:")
    for rank, (chunk, score) in enumerate(results, 1):
        src = chunk.metadata.get("source_document", "?")
        preview = chunk.text[:80].replace("\n", " ")
        print(f"    {rank}. [score: {score:.2f}] ({src}) \"{preview}...\"")

    # 2. Kontextus osszeallitas
    context_parts = [c.text for c, s in results if s > 0]
    context = "\n\n---\n\n".join(context_parts) if context_parts else "(Nincs talalat)"

    # 3. Prompt generalas (LLM-nek -- itt csak kiirjuk)
    prompt = (
        f"Kontextus alapjan valaszolj a kerdesre.\n\n"
        f"### Kontextus:\n{context}\n\n"
        f"### Kerdes:\n{query}\n\n### Valasz:"
    )
    tokens = math.ceil(len(prompt) / 3.5)
    print(f"\n  Prompt: {len(prompt)} karakter (~{tokens} token)")
    print(f"  Kontextus-chunkok: {len(context_parts)}\n")
    return prompt


# --- FO VEZERLES ---

def main():
    """A teljes demo futtatasa."""
    print("\n" + "=" * 65)
    print("  RAG PIPELINE - Dokumentum Feldolgozas es Chunkolasi Strategiak")
    print("=" * 65 + "\n")

    # 1. Betoltes
    documents = load_mock_documents()

    # 2. Strategiak osszehasonlitasa az elso ket dokumentumon
    for doc in documents[:2]:
        compare_strategies(doc)

    # 3. Chunk meret / overlap hatas
    demo_chunk_size_effect("\n\n".join(d.content for d in documents))

    # 4. Metaadat-gazdagitas demo
    print("== METAADAT-GAZDAGITAS ==")
    doc = documents[0]
    raw = chunk_by_heading(doc.content)
    enriched = enrich_metadata(raw, doc, strategy_name="by_heading")
    print(f"  {doc.name}: {len(enriched)} chunk")
    for ch in enriched[:2]:
        print(f"  Chunk #{ch.chunk_index} ({ch.char_count} kar, ~{ch.estimated_tokens()} tok)")
        for k, v in list(ch.metadata.items())[:5]:
            print(f"    {k}: {v}")
    print()

    # 5. RAG pipeline demo
    print("== RAG PIPELINE DEMO (vektor DB nelkul, kulcsszo-kereses) ==\n")
    all_chunks: list[Chunk] = []
    for d in documents:
        r = chunk_recursive(d.content, chunk_size=500, overlap=100)
        all_chunks.extend(enrich_metadata(r, d, strategy_name="recursive"))
    print(f"Tudasbazis: {len(all_chunks)} chunk\n")
    for q in ["Mi az a RAG pipeline?", "Hogyan kell chunkolni?", "Deployment checklist?"]:
        simple_rag_pipeline(q, all_chunks, top_k=3)

    # 6. Opcionalis: LangChain / tiktoken (ha telepitve vannak)
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        lc = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
        print(f"[LangChain] {len(lc.split_text(documents[0].content))} chunk\n")
    except ImportError:
        print("[LangChain] nincs telepitve (pip install langchain-text-splitters)\n")
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o")
        t = enc.encode(documents[0].content)
        print(f"[tiktoken] {len(documents[0].content)} kar -> {len(t)} token\n")
    except ImportError:
        print("[tiktoken] nincs telepitve (pip install tiktoken)\n")

    print("== OSSZEFOGLALAS ==")
    for i, step in enumerate([
        "Betoltjuk a dokumentumokat", "Chunkolasi strategiat valasztunk",
        "Chunk meretet es overlap-et allitunk", "Metaadatokkal gazdagitunk",
        "Embedding-eket keszitunk (-> kov. guide)", "Vektoradatbazisba irjuk (-> 03-as guide)",
    ], 1):
        print(f"  {i}. {step}")


if __name__ == "__main__":
    main()
