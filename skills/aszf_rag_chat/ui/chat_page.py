"""ASZF RAG Chat page - professional ChatGPT/Claude-style interface.

Extends BaseChatState with ASZF-specific RAG query pipeline.
Uses the professional chat_container component for the full layout.
"""
import reflex as rx
from src.aiflow.ui.components.chat.chat_container import chat_container
from src.aiflow.ui.state.chat_state import BaseChatState


class AszfChatState(BaseChatState):
    """ASZF-specific chat state with RAG pipeline integration."""

    skill_name: str = "aszf_rag_chat"
    collection: str = "azhu-aszf-2024"
    company_name: str = "Allianz Hungaria"

    async def _get_response(self, question: str) -> dict:
        """Call the ASZF RAG query workflow pipeline.

        Executes the full 6-step RAG pipeline:
        1. rewrite_query  - reformulate for better retrieval
        2. search_documents - hybrid vector + BM25 search
        3. build_context  - assemble context from chunks
        4. generate_answer - LLM generation with role
        5. extract_citations - pull source references
        6. detect_hallucination - quality gate check
        """
        from skills.aszf_rag_chat.workflows.query import (
            build_context,
            detect_hallucination,
            extract_citations,
            generate_answer,
            rewrite_query,
            search_documents,
        )

        # Build conversation history from recent messages (last 3 turns = 6 msgs)
        history = [
            {"role": m.role, "content": m.content}
            for m in self.current_messages[-6:]
        ]

        data = {
            "question": question,
            "collection": self.collection,
            "role": self.role,
            "language": "hu",
            "conversation_history": history,
            "top_k": 5,
        }

        try:
            r1 = await rewrite_query(data)
            r2 = await search_documents({**data, **r1})
            r3 = await build_context({**data, **r2})
            r4 = await generate_answer({**data, **r3, "role": self.role})
            r5 = await extract_citations(r4)
            r6 = await detect_hallucination(r5)
            return r6
        except Exception as e:
            return {
                "answer": f"Hiba a feldolgozas soran: {e}",
                "citations": [],
            }


def aszf_chat_page() -> rx.Component:
    """The ASZF RAG Chat page - full professional layout."""
    return chat_container(
        # State vars
        conversations=AszfChatState.conversations,
        current_conversation_id=AszfChatState.current_conversation_id,
        current_messages=AszfChatState.current_messages,
        current_input=AszfChatState.current_input,
        current_title=AszfChatState.current_title,
        role=AszfChatState.role,
        role_display=AszfChatState.role_display,
        is_processing=AszfChatState.is_processing,
        sidebar_open=AszfChatState.sidebar_open,
        has_messages=AszfChatState.has_messages,
        show_citations=AszfChatState.show_citations,
        selected_citations=AszfChatState.selected_citations,
        # Event handlers
        on_new_chat=AszfChatState.new_conversation,
        on_select_conversation=AszfChatState.select_conversation,
        on_delete_conversation=AszfChatState.delete_conversation,
        on_role_change=AszfChatState.set_role,
        on_toggle_sidebar=AszfChatState.toggle_sidebar,
        on_send=AszfChatState.send_message,
        on_input_change=AszfChatState.set_current_input,
        on_citation_toggle=AszfChatState.toggle_citations,
        on_citation_close=AszfChatState.close_citations,
    )
