"""AIFlow Reflex application - professional routing and landing page."""
import reflex as rx
from skills.aszf_rag_chat.ui.chat_page import aszf_chat_page, AszfChatState
from skills.aszf_rag_chat.ui.config_page import aszf_admin_page, AszfAdminState


# ---------------------------------------------------------------------------
# Color tokens (consistent with chat_container)
# ---------------------------------------------------------------------------
ACCENT = "#10A37F"
BG = "#F7F7F8"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E5E7EB"
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#6B7280"
TEXT_DIM = "#9CA3AF"


# ---------------------------------------------------------------------------
# Landing page components
# ---------------------------------------------------------------------------
def skill_card(
    icon_name: str,
    title: str,
    description: str,
    href: str,
    badge_text: str = "",
    badge_color: str = "green",
) -> rx.Component:
    """Professional skill card for the landing page."""
    return rx.link(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon(icon_name, size=20, color="#FFFFFF"),
                        width="40px",
                        height="40px",
                        border_radius="10px",
                        background=ACCENT,
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.spacer(),
                    rx.cond(
                        badge_text != "",
                        rx.badge(
                            badge_text,
                            color_scheme=badge_color,
                            variant="soft",
                            size="1",
                        ),
                        rx.fragment(),
                    ),
                    width="100%",
                    align="center",
                ),
                rx.text(
                    title,
                    font_size="16px",
                    font_weight="600",
                    color=TEXT_PRIMARY,
                ),
                rx.text(
                    description,
                    font_size="13px",
                    color=TEXT_SECONDARY,
                    line_height="1.5",
                ),
                rx.hstack(
                    rx.text(
                        "Megnyitas",
                        font_size="13px",
                        font_weight="500",
                        color=ACCENT,
                    ),
                    rx.icon("arrow-right", size=14, color=ACCENT),
                    spacing="1",
                    align="center",
                ),
                spacing="3",
            ),
            padding="20px",
            border_radius="12px",
            border=f"1px solid {CARD_BORDER}",
            background=CARD_BG,
            width="100%",
            max_width="350px",
            cursor="pointer",
            transition="all 0.2s ease",
            _hover={
                "border_color": ACCENT,
                "box_shadow": f"0 4px 12px {ACCENT}15",
                "transform": "translateY(-2px)",
            },
        ),
        href=href,
        text_decoration="none",
    )


def index() -> rx.Component:
    """Landing page with professional layout and skill cards."""
    return rx.box(
        rx.vstack(
            # -- Header --
            rx.box(
                rx.hstack(
                    rx.hstack(
                        rx.icon("bot", size=28, color=ACCENT),
                        rx.text(
                            "AIFlow",
                            font_size="24px",
                            font_weight="700",
                            color=TEXT_PRIMARY,
                            letter_spacing="-0.02em",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.spacer(),
                    rx.link(
                        rx.button(
                            rx.icon("settings", size=16),
                            rx.text("Admin", font_size="13px"),
                            variant="outline",
                            size="2",
                            cursor="pointer",
                        ),
                        href="/admin",
                    ),
                    width="100%",
                    align="center",
                    padding="16px 32px",
                    max_width="1000px",
                    margin="0 auto",
                ),
                border_bottom=f"1px solid {CARD_BORDER}",
                background="#FFFFFF",
                width="100%",
            ),
            # -- Hero --
            rx.center(
                rx.vstack(
                    rx.text(
                        "Enterprise AI Automation",
                        font_size="36px",
                        font_weight="700",
                        color=TEXT_PRIMARY,
                        text_align="center",
                        letter_spacing="-0.02em",
                    ),
                    rx.text(
                        "Valasszon az elerheto AI skill-ek kozul az indulashoz.",
                        font_size="16px",
                        color=TEXT_SECONDARY,
                        text_align="center",
                    ),
                    spacing="2",
                    align="center",
                    padding_top="48px",
                    padding_bottom="36px",
                ),
                width="100%",
            ),
            # -- Skill cards grid --
            rx.center(
                rx.hstack(
                    skill_card(
                        icon_name="message-circle",
                        title="ASZF RAG Chat",
                        description=(
                            "Kerdesek es valaszok az Altalanos Szerzodesi "
                            "Feltetelekrol, AI-alapu dokumentum kereso "
                            "rendszerrel."
                        ),
                        href="/chat",
                        badge_text="AI",
                        badge_color="green",
                    ),
                    skill_card(
                        icon_name="git-branch",
                        title="Process Documentation",
                        description=(
                            "BPMN diagramok generalasa termeszetes nyelvu "
                            "leirasokbol. Kimenet: SVG, DrawIO, Mermaid."
                        ),
                        href="/diagrams",
                        badge_text="AI",
                        badge_color="blue",
                    ),
                    skill_card(
                        icon_name="mail",
                        title="Email Intent",
                        description=(
                            "Email-ek automatikus osztalyozasa es "
                            "tovabbitasa a megfelelo csapatnak."
                        ),
                        href="#",
                        badge_text="Hamarosan",
                        badge_color="gray",
                    ),
                    spacing="5",
                    flex_wrap="wrap",
                    justify="center",
                    padding_x="24px",
                    width="100%",
                    max_width="1100px",
                ),
                width="100%",
            ),
            # -- Footer --
            rx.spacer(),
            rx.center(
                rx.text(
                    "AIFlow v0.1 - BestIx Kft.",
                    font_size="12px",
                    color=TEXT_DIM,
                ),
                padding="24px",
                width="100%",
            ),
            spacing="0",
            min_height="100vh",
            width="100%",
        ),
        background=BG,
        width="100%",
        min_height="100vh",
    )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="green",
        radius="medium",
    ),
    style={
        "font_family": (
            "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', "
            "Roboto, sans-serif"
        ),
        "::selection": {
            "background": f"{ACCENT}33",
        },
    },
)
app.add_page(index, route="/", title="AIFlow - Enterprise AI Automation")
app.add_page(aszf_chat_page, route="/chat", title="ASZF Chat - AIFlow")
app.add_page(aszf_admin_page, route="/admin", title="Admin - AIFlow")
