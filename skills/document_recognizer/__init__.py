"""Document Recognizer skill — generic doc-type recognition + extraction.

Sprint V SV-1 foundation. Replaces and generalizes the legacy ``invoice_finder``
scaffold (renamed via ``git mv``). The skill can recognize and extract data
from multiple document types — invoice, ID card, address card, passport,
contract, etc. — driven by per-doctype YAML descriptors.

Adoption sequence (Sprint V):

* SV-1 (this session): contracts + DocTypeRegistry skeleton + safe-eval +
  skill rename. **No real descriptors loaded yet.**
* SV-2: classifier rule engine + LLM fallback gate + 2 doctypes (hu_invoice,
  hu_id_card) + ``id_card_extraction_chain.yaml`` PromptWorkflow descriptor.
* SV-3: API router (``/api/v1/document-recognizer``) + Alembic 048
  ``doc_recognition_runs`` + cost preflight integration + 2 more doctypes.
* SV-4: admin UI page ``/document-recognizer`` + 1 more doctype + Playwright.
* SV-5: per-doctype golden-path corpora + accuracy gate + close + tag v1.6.0.
"""

from pathlib import Path

from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager

__all__ = ["SKILL_NAME", "models_client", "prompt_manager"]

SKILL_NAME = "document_recognizer"

_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
models_client = ModelClient(generation_backend=_backend, embedding_backend=_backend)

prompt_manager = PromptManager()
prompt_manager.register_yaml_dir(Path(__file__).parent / "prompts")
