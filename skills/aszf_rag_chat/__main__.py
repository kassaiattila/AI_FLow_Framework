"""ASZF RAG Chat skill - standalone entry point.

Usage:
    # Ingest documents into vectorstore:
    python -m skills.aszf_rag_chat ingest --source ./docs/ --collection my-collection

    # Ask a question:
    python -m skills.aszf_rag_chat query --question "Mi a felmondasi ido?" --role expert --collection my-collection
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def run_ingest(source_path: str, collection: str, language: str) -> None:
    """Process documents through the ingestion pipeline."""
    from skills.aszf_rag_chat.workflows.ingest import (
        load_documents, parse_documents, chunk_documents,
        generate_embeddings, store_chunks, verify_ingestion,
    )

    source = Path(source_path)
    if not source.exists():
        print(f"Forraskonytar nem talalhato: {source_path}")
        return

    print("ASZF RAG Ingestion Pipeline")
    print(f"Source: {source}")
    print(f"Collection: {collection}")
    print(f"Language: {language}")
    print()

    start = time.monotonic()
    data: dict = {"source_path": str(source), "collection": collection, "language": language}

    r1 = await load_documents(data)
    print(f"1. Load: {len(r1['files'])} fajl talalva")

    r2 = await parse_documents(r1)
    total_chars = sum(len(d["text"]) for d in r2["documents"])
    print(f"2. Parse: {len(r2['documents'])} dokumentum, {total_chars:,} karakter")

    r3 = await chunk_documents(r2)
    print(f"3. Chunk: {r3['total_chunks']} darab chunk")

    r4 = await generate_embeddings(r3)
    print(f"4. Embed: {len(r4['chunks_with_embeddings'])} embedding, ${r4['embedding_cost_usd']:.4f}")

    r5 = await store_chunks(r4)
    print(f"5. Store: {r5['stored_count']} chunk tarolva")

    r6 = await verify_ingestion(r5)
    elapsed = time.monotonic() - start
    status = "SIKERES" if r6["verified"] else "SIKERTELEN"
    print(f"6. Verify: {status} ({r6['total_chunks']} chunk)")
    print(f"\nKesz! Ido: {elapsed:.1f}s")


async def run_query(
    question: str,
    collection: str,
    role: str,
    language: str,
) -> None:
    """Ask a question against the ingested documents."""
    from skills.aszf_rag_chat.workflows.query import (
        rewrite_query, search_documents, build_context,
        generate_answer, extract_citations, detect_hallucination,
    )

    print("ASZF RAG Query Pipeline")
    print(f"Question: {question}")
    print(f"Collection: {collection}")
    print(f"Role: {role}")
    print()

    start = time.monotonic()
    data: dict = {
        "question": question,
        "collection": collection,
        "role": role,
        "language": language,
    }

    r1 = await rewrite_query(data)
    print(f"1. Rewrite: {r1['rewritten_query'][:80]}...")

    r2 = await search_documents({**data, **r1})
    print(f"2. Search: {len(r2['search_results'])} talalat")

    r3 = await build_context(r2)
    print(f"3. Context: {len(r3['sources'])} forras, {len(r3['context'])} karakter")

    r4 = await generate_answer({**r3, "role": role})
    print(f"4. Answer: {len(r4['answer'])} karakter")

    r5 = await extract_citations(r4)
    print(f"5. Citations: {len(r5['citations'])} hivatkozas")

    r6 = await detect_hallucination(r5)
    elapsed = time.monotonic() - start
    print(f"6. Hallucination: {r6['hallucination_score']:.2f} (1.0 = teljes megalapozottsag)")

    print(f"\n{'=' * 60}")
    print(f"Valasz ({role}):")
    print(f"{'=' * 60}")
    print(r6["answer"])
    print(f"\nHivatkozasok:")
    for cit in r6.get("citations", []):
        doc = cit.get("document_name", "?")
        sec = cit.get("section", "")
        print(f"  - {doc}" + (f" / {sec}" if sec else ""))
    print(f"\nIdo: {elapsed:.1f}s | Koltseg: ${r6.get('cost_usd', 0):.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASZF RAG Chat")
    sub = parser.add_subparsers(dest="command", help="Command")

    # ingest subcommand
    ip = sub.add_parser("ingest", help="Ingest documents into vectorstore")
    ip.add_argument("--source", "-s", required=True, help="Source directory path")
    ip.add_argument("--collection", "-c", default="default", help="Collection name")
    ip.add_argument("--language", "-l", default="hu", help="Document language")

    # query subcommand
    qp = sub.add_parser("query", help="Ask a question against ingested documents")
    qp.add_argument("--question", "-q", required=True, help="Question to ask")
    qp.add_argument("--collection", "-c", default="default", help="Collection name")
    qp.add_argument("--role", "-r", default="baseline", choices=["baseline", "mentor", "expert"],
                     help="Response role/persona")
    qp.add_argument("--language", "-l", default="hu", help="Language")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(run_ingest(args.source, args.collection, args.language))
    elif args.command == "query":
        asyncio.run(run_query(args.question, args.collection, args.role, args.language))
    else:
        parser.print_help()
