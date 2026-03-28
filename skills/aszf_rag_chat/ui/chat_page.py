"""ASZF RAG Chat page - skill-specific Reflex page."""
import reflex as rx
from src.aiflow.ui.state.chat_state import BaseChatState, ChatMessage
from src.aiflow.ui.components.chat.chat_container import chat_container


class AszfChatState(BaseChatState):
    """ASZF-specific chat state."""
    skill_name: str = "aszf_rag_chat"
    collection: str = "azhu-aszf-2024"
    role: str = "baseline"
    company_name: str = "Allianz Hungaria"

    async def _get_response(self, question: str) -> dict:
        """Call the ASZF RAG query workflow."""
        from skills.aszf_rag_chat.workflows.query import (
            rewrite_query, search_documents, build_context,
            generate_answer, extract_citations, detect_hallucination,
        )

        # Build conversation history
        history = [{"role": m.role, "content": m.content}
                   for m in self.messages[-6:]]  # last 3 turns

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
            return {"answer": f"Hiba a feldolgozas soran: {e}", "citations": []}


def citation_card(citation: dict) -> rx.Component:
    """Display a source citation."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("file-text", size=16),
                rx.text(citation.get("document_name", ""), weight="bold", size="2"),
            ),
            rx.text(citation.get("excerpt", "")[:200], size="1", color="gray"),
            rx.badge(
                f"Relevancia: {citation.get('relevance_score', 0):.0%}",
                color_scheme="green",
            ),
            spacing="1",
        ),
        size="1",
    )


def aszf_chat_page() -> rx.Component:
    """The ASZF RAG Chat page."""
    return rx.box(
        # Header
        rx.hstack(
            rx.heading("ASZF Chat", size="5"),
            rx.spacer(),
            rx.select(
                ["baseline", "mentor", "expert"],
                value=AszfChatState.role,
                on_change=AszfChatState.set_role,
                size="2",
            ),
            rx.button("Uj beszelgetes", on_click=AszfChatState.clear_chat, variant="outline", size="2"),
            padding="16px",
            border_bottom="1px solid #eee",
            width="100%",
        ),
        # Chat
        chat_container(
            messages=AszfChatState.messages,
            current_input=AszfChatState.current_input,
            on_send=AszfChatState.send_message,
            on_input_change=AszfChatState.set_current_input,
            is_processing=AszfChatState.is_processing,
            placeholder="Kerem kerdezzen az ASZF-rol...",
        ),
        width="100%",
        max_width="800px",
        margin="0 auto",
        height="100vh",
    )
