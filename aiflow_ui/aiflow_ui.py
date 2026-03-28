"""AIFlow Reflex application with skill-specific pages."""
import reflex as rx
from skills.aszf_rag_chat.ui.chat_page import aszf_chat_page, AszfChatState
from skills.aszf_rag_chat.ui.config_page import aszf_admin_page, AszfAdminState


def index() -> rx.Component:
    return rx.vstack(
        rx.heading("AIFlow", size="7"),
        rx.text("Enterprise AI Automation Framework", color="gray"),
        rx.divider(),
        rx.heading("Elerheto Skill-ek", size="5"),
        rx.link(rx.card(
            rx.hstack(rx.icon("message-circle"), rx.text("ASZF RAG Chat")),
        ), href="/chat"),
        rx.link(rx.card(
            rx.hstack(rx.icon("git-branch"), rx.text("Process Documentation")),
        ), href="/diagrams"),
        spacing="4",
        padding="24px",
        align="center",
    )


app = rx.App(
    theme=rx.theme(appearance="light", accent_color="blue"),
)
app.add_page(index, route="/", title="AIFlow")
app.add_page(aszf_chat_page, route="/chat", title="ASZF Chat")
app.add_page(aszf_admin_page, route="/admin", title="ASZF Admin")
