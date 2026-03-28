"""Reusable chat state for RAG skills."""
import reflex as rx
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = "user"
    content: str = ""
    citations: list[dict] = Field(default_factory=list)
    processing: bool = False


class BaseChatState(rx.State):
    """Base chat state - extend per skill."""
    messages: list[ChatMessage] = []
    current_input: str = ""
    is_processing: bool = False
    error_message: str = ""

    # Config (override in subclass)
    skill_name: str = "rag_chat"
    collection: str = "default"
    role: str = "baseline"  # baseline | mentor | expert

    async def send_message(self):
        """Send user message and get AI response."""
        if not self.current_input.strip():
            return

        # Add user message
        user_msg = ChatMessage(role="user", content=self.current_input)
        self.messages.append(user_msg)
        question = self.current_input
        self.current_input = ""
        self.is_processing = True
        yield

        # Get AI response (override _get_response in subclass)
        try:
            response = await self._get_response(question)
            assistant_msg = ChatMessage(
                role="assistant",
                content=response.get("answer", "Hiba tortent."),
                citations=response.get("citations", []),
            )
            self.messages.append(assistant_msg)
        except Exception as e:
            self.error_message = str(e)
            self.messages.append(ChatMessage(
                role="assistant",
                content=f"Hiba: {e}",
            ))
        finally:
            self.is_processing = False

    async def _get_response(self, question: str) -> dict:
        """Override in subclass to call specific skill."""
        return {"answer": "Not implemented", "citations": []}

    def clear_chat(self):
        self.messages = []
        self.error_message = ""

    def set_role(self, role: str):
        self.role = role
