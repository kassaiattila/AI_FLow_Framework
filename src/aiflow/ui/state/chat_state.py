"""Professional chat state for RAG skills - ChatGPT/Claude style."""
import reflex as rx
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


class ChatMessage(BaseModel):
    """Single chat message."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str = "user"  # user | assistant
    content: str = ""
    citations: list[dict] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M"))
    is_loading: bool = False


class Conversation(BaseModel):
    """A conversation session."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = "Uj beszelgetes"
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    role: str = "baseline"


class BaseChatState(rx.State):
    """Base chat state - ChatGPT/Claude style with conversations."""

    conversations: list[Conversation] = []
    current_conversation_id: str = ""
    current_input: str = ""
    is_processing: bool = False
    role: str = "baseline"
    sidebar_open: bool = True
    show_citations: bool = False
    selected_message_id: str = ""

    @rx.var
    def current_messages(self) -> list[ChatMessage]:
        """Get messages for the active conversation."""
        for conv in self.conversations:
            if conv.id == self.current_conversation_id:
                return conv.messages
        return []

    @rx.var
    def current_title(self) -> str:
        """Get title of the active conversation."""
        for conv in self.conversations:
            if conv.id == self.current_conversation_id:
                return conv.title
        return "AIFlow Chat"

    @rx.var
    def has_conversations(self) -> bool:
        """Whether any conversations exist."""
        return len(self.conversations) > 0

    @rx.var
    def has_active_conversation(self) -> bool:
        """Whether a conversation is currently selected."""
        return self.current_conversation_id != ""

    @rx.var
    def has_messages(self) -> bool:
        """Whether the current conversation has any messages."""
        for conv in self.conversations:
            if conv.id == self.current_conversation_id:
                return len(conv.messages) > 0
        return False

    @rx.var
    def selected_citations(self) -> list[dict]:
        """Get citations for the selected message."""
        for conv in self.conversations:
            if conv.id == self.current_conversation_id:
                for msg in conv.messages:
                    if msg.id == self.selected_message_id:
                        return msg.citations
        return []

    @rx.var
    def role_display(self) -> str:
        """Human-readable role name."""
        role_map = {
            "baseline": "Baseline",
            "mentor": "Mentor",
            "expert": "Expert",
        }
        return role_map.get(self.role, self.role.capitalize())

    def new_conversation(self):
        """Create a new empty conversation."""
        conv = Conversation(role=self.role)
        self.conversations.insert(0, conv)
        self.current_conversation_id = conv.id
        self.current_input = ""
        self.show_citations = False
        self.selected_message_id = ""

    def select_conversation(self, conv_id: str):
        """Switch to an existing conversation."""
        self.current_conversation_id = conv_id
        self.show_citations = False
        self.selected_message_id = ""

    def delete_conversation(self, conv_id: str):
        """Delete a conversation and select the next one."""
        self.conversations = [c for c in self.conversations if c.id != conv_id]
        if self.current_conversation_id == conv_id:
            if self.conversations:
                self.current_conversation_id = self.conversations[0].id
            else:
                self.current_conversation_id = ""
        self.show_citations = False
        self.selected_message_id = ""

    def set_role(self, role: str):
        """Change the AI role for new messages."""
        self.role = role

    def toggle_sidebar(self):
        """Toggle the sidebar visibility."""
        self.sidebar_open = not self.sidebar_open

    def toggle_citations(self, message_id: str):
        """Toggle citation panel for a specific message."""
        if self.selected_message_id == message_id and self.show_citations:
            self.show_citations = False
            self.selected_message_id = ""
        else:
            self.selected_message_id = message_id
            self.show_citations = True

    def close_citations(self):
        """Close the citation panel."""
        self.show_citations = False
        self.selected_message_id = ""

    async def send_message(self):
        """Send a user message and get an AI response."""
        if not self.current_input.strip() or self.is_processing:
            return

        # Create conversation if none exists
        if not self.current_conversation_id:
            self.new_conversation()

        # Add user message
        user_msg = ChatMessage(role="user", content=self.current_input)
        for conv in self.conversations:
            if conv.id == self.current_conversation_id:
                conv.messages.append(user_msg)
                # Set title from the first message
                if len(conv.messages) == 1:
                    title_text = self.current_input[:50]
                    if len(self.current_input) > 50:
                        title_text += "..."
                    conv.title = title_text
                break

        question = self.current_input
        self.current_input = ""
        self.is_processing = True

        # Add loading placeholder
        loading_msg = ChatMessage(
            role="assistant", content="", is_loading=True
        )
        for conv in self.conversations:
            if conv.id == self.current_conversation_id:
                conv.messages.append(loading_msg)
                break
        yield

        # Get the AI response
        try:
            response = await self._get_response(question)
            answer = response.get("answer", "Hiba tortent a feldolgozas soran.")
            citations = response.get("citations", [])
        except Exception as e:
            answer = f"Hiba: {e}"
            citations = []

        # Replace loading placeholder with actual response
        for conv in self.conversations:
            if conv.id == self.current_conversation_id:
                conv.messages[-1] = ChatMessage(
                    role="assistant",
                    content=answer,
                    citations=citations,
                )
                break

        self.is_processing = False

    async def _get_response(self, question: str) -> dict:
        """Override in subclass to call the specific skill backend."""
        return {"answer": "Override _get_response in subclass.", "citations": []}

    def handle_key_down(self, key: str):
        """Handle keyboard shortcuts in the input area."""
        if key == "Enter":
            return BaseChatState.send_message
