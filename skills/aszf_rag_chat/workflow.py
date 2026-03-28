"""ASZF RAG Chat workflow - retrieval-augmented Q&A pipeline.

TODO: Implement full workflow steps:
  1. rewrite_query - Rewrite user question for optimal retrieval
  2. retrieve - Hybrid search (vector + keyword) against ASZF documents
  3. generate_answer - LLM answer grounded in retrieved chunks
  4. extract_citations - Extract and format source references
  5. detect_hallucination - Verify answer is grounded in sources
  6. manage_conversation - Track multi-turn context
"""
from aiflow.engine.workflow import workflow, WorkflowBuilder


@workflow(name="aszf-rag-chat", version="1.0.0", skill="aszf_rag_chat")
def aszf_rag_chat(wf: WorkflowBuilder) -> None:
    """RAG-based Q&A chatbot for Hungarian legal documents."""
    # TODO: Register steps
    # wf.step(rewrite_query)
    # wf.step(retrieve, depends_on=["rewrite_query"])
    # wf.step(generate_answer, depends_on=["retrieve"])
    # wf.step(extract_citations, depends_on=["generate_answer"])
    # wf.step(detect_hallucination, depends_on=["generate_answer", "retrieve"])
    # wf.step(manage_conversation, depends_on=["detect_hallucination"])
    pass
