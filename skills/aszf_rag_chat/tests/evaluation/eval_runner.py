#!/usr/bin/env python3
"""RAG Evaluation Runner - golden dataset tester.

Runs all queries from golden_queries.yaml against the RAG pipeline
and measures quality metrics (retrieval precision, answer relevance,
hallucination rate).

Usage:
    python -m skills.aszf_rag_chat.tests.evaluation.eval_runner \
        --collection azhu-test-v2 --role expert

Based on Cubix RAG reference Module 05 (evaluacio_es_teszteles.md).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")


async def run_evaluation(collection: str, role: str, output_dir: str) -> None:
    from skills.aszf_rag_chat.workflows.query import (
        rewrite_query, search_documents, build_context,
        generate_answer, extract_citations, detect_hallucination,
    )

    # Load golden queries
    dataset_path = Path(__file__).parent.parent / "datasets" / "golden_queries.yaml"
    with open(dataset_path, encoding="utf-8") as f:
        dataset = yaml.safe_load(f)

    queries = dataset.get("queries", [])
    eval_config = dataset.get("evaluation", {})

    print(f"RAG Evaluation Runner")
    print(f"Collection: {collection}")
    print(f"Role: {role}")
    print(f"Queries: {len(queries)}")
    print(f"=" * 60)

    results = []
    total_start = time.monotonic()

    for i, q in enumerate(queries):
        qid = q.get("id", f"q{i:03d}")
        question = q["question"]
        expect_no_results = q.get("expect_no_results", False)

        print(f"\n[{qid}] {question[:60]}...")

        start = time.monotonic()

        try:
            data = {
                "question": question,
                "collection": collection,
                "role": role,
                "language": "hu",
                "top_k": 5,
            }

            r1 = await rewrite_query(data)
            r2 = await search_documents({**data, **r1})
            r3 = await build_context({**data, **r2})
            r4 = await generate_answer({**data, **r3})
            r5 = await extract_citations(r4)
            r6 = await detect_hallucination(r5)

            duration = (time.monotonic() - start) * 1000
            search_count = len(r2.get("search_results", []))
            answer = r6.get("answer", "")
            hallucination = r6.get("hallucination_score", 0.5)
            citations = len(r6.get("citations", []))

            # Evaluate retrieval
            expected_sources = q.get("expected_sources", [])
            found_sources = [s.get("document_title", "") for s in r2.get("search_results", [])]
            retrieval_hit = any(
                any(exp in found for found in found_sources)
                for exp in expected_sources
            ) if expected_sources else search_count > 0

            # Evaluate answer relevance (simple: expected topics in answer)
            expected_topics = q.get("expected_topics", [])
            topic_hits = sum(1 for t in expected_topics if t.lower() in answer.lower())
            topic_coverage = topic_hits / max(len(expected_topics), 1)

            result = {
                "id": qid,
                "question": question,
                "search_results": search_count,
                "retrieval_hit": retrieval_hit,
                "answer_len": len(answer),
                "topic_coverage": round(topic_coverage, 2),
                "hallucination_score": round(hallucination, 2),
                "citations": citations,
                "duration_ms": round(duration),
                "pass": (
                    (not expect_no_results and search_count > 0 and retrieval_hit)
                    or (expect_no_results and search_count == 0)
                ),
            }
            results.append(result)

            status = "PASS" if result["pass"] else "FAIL"
            print(f"  {status} | {search_count} hits | topics {topic_coverage:.0%} | "
                  f"halluc {hallucination:.2f} | {duration:.0f}ms")

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            results.append({
                "id": qid,
                "question": question,
                "error": str(e),
                "pass": False,
                "duration_ms": round(duration),
            })
            print(f"  ERROR: {e}")

    # Summary
    total_duration = (time.monotonic() - total_start)
    passed = sum(1 for r in results if r.get("pass"))
    failed = len(results) - passed
    avg_hallucination = sum(r.get("hallucination_score", 0) for r in results) / max(len(results), 1)
    avg_topic = sum(r.get("topic_coverage", 0) for r in results) / max(len(results), 1)

    print(f"\n{'=' * 60}")
    print(f"EREDMENY: {passed}/{len(results)} PASS ({passed / max(len(results), 1):.0%})")
    print(f"  Atlag topic coverage: {avg_topic:.0%}")
    print(f"  Atlag hallucination: {avg_hallucination:.2f}")
    print(f"  Teljes ido: {total_duration:.1f}s")
    print(f"{'=' * 60}")

    # Save results
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "eval_report.json"
    report_path.write_text(
        json.dumps({
            "collection": collection,
            "role": role,
            "total_queries": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / max(len(results), 1), 2),
            "avg_topic_coverage": round(avg_topic, 2),
            "avg_hallucination": round(avg_hallucination, 2),
            "total_duration_s": round(total_duration, 1),
            "results": results,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Report: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")
    parser.add_argument("--collection", default="azhu-test-v2")
    parser.add_argument("--role", default="expert")
    parser.add_argument("--output", default="./test_output/eval")
    args = parser.parse_args()
    asyncio.run(run_evaluation(args.collection, args.role, args.output))
