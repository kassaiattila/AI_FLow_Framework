"""Bootstrap BAAI/bge-m3 into a local sentence-transformers cache.

Sprint J / UC2 (v1.4.6 / S103). Downloads the Profile A embedder weights
(~2GB combined: model + tokenizer) so the test suite and the rag_engine
provider registry flow can run offline afterwards.

Idempotent: if the model is already present in the target cache directory
the script exits immediately without re-downloading.

Usage:
    uv run python scripts/bootstrap_bge_m3.py
    AIFLOW_BGE_M3__CACHE_FOLDER=/custom/path uv run python scripts/bootstrap_bge_m3.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

DEFAULT_MODEL_NAME = "BAAI/bge-m3"
DEFAULT_CACHE = Path(".cache/models/bge-m3")


def _cache_has_model(cache_dir: Path) -> bool:
    if not cache_dir.exists():
        return False
    hits = list(cache_dir.rglob("config.json"))
    return any("bge-m3" in str(h).lower() or "BAAI" in str(h) for h in hits)


def main() -> int:
    model_name = os.getenv("AIFLOW_BGE_M3__MODEL_NAME", DEFAULT_MODEL_NAME)
    cache_env = os.getenv("AIFLOW_BGE_M3__CACHE_FOLDER")
    cache_dir = Path(cache_env) if cache_env else DEFAULT_CACHE
    cache_dir.mkdir(parents=True, exist_ok=True)

    if _cache_has_model(cache_dir):
        print(f"[bootstrap_bge_m3] model already present at {cache_dir} — skipping")
        return 0

    print(f"[bootstrap_bge_m3] downloading {model_name} into {cache_dir} …")
    start = time.time()

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        print(f"[bootstrap_bge_m3] ERROR: sentence-transformers not installed: {exc}")
        return 1

    model = SentenceTransformer(model_name, cache_folder=str(cache_dir))
    vectors = model.encode(["bootstrap smoke test"], normalize_embeddings=True)
    dim = len(vectors[0])
    elapsed = time.time() - start
    print(f"[bootstrap_bge_m3] OK — dim={dim} elapsed={elapsed:.1f}s cache={cache_dir}")
    return 0 if dim == 1024 else 2


if __name__ == "__main__":
    sys.exit(main())
