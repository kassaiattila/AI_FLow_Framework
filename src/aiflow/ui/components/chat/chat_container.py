"""Professional ChatGPT/Claude-style chat container component.

Provides a full-featured chat UI with:
- Dark sidebar with conversation history
- Clean message area with markdown rendering
- User/assistant message bubbles with proper alignment
- Loading animation during processing
- Role selector in the header
- Citation panel for RAG results
"""
import reflex as rx

# ---------------------------------------------------------------------------
# Color tokens (ChatGPT-inspired dark sidebar, light content area)
# ---------------------------------------------------------------------------
SIDEBAR_BG = "#202123"
SIDEBAR_HOVER = "#2A2B32"
SIDEBAR_BORDER = "#353740"
SIDEBAR_TEXT = "#ECECF1"
SIDEBAR_TEXT_DIM = "#8E8EA0"
SIDEBAR_WIDTH = "260px"

CONTENT_BG = "#F7F7F8"
HEADER_BG = "#FFFFFF"
HEADER_BORDER = "#E5E5E5"

USER_BUBBLE_BG = "#2563EB"
USER_BUBBLE_TEXT = "#FFFFFF"
ASSISTANT_BUBBLE_BG = "#FFFFFF"
ASSISTANT_BUBBLE_TEXT = "#1A1A1A"
ASSISTANT_BUBBLE_BORDER = "#E5E7EB"

ACCENT = "#10A37F"
ACCENT_HOVER = "#0D8C6D"

INPUT_BG = "#FFFFFF"
INPUT_BORDER = "#D1D5DB"
INPUT_FOCUS_BORDER = "#2563EB"

CITATION_BG = "#FFFFFF"
CITATION_BORDER = "#E5E7EB"


# ---------------------------------------------------------------------------
# Sidebar components
# ---------------------------------------------------------------------------
def sidebar_logo() -> rx.Component:
    """AIFlow logo and branding at the top of the sidebar."""
    return rx.box(
        rx.hstack(
            rx.icon("bot", size=22, color=ACCENT),
            rx.text(
                "AIFlow",
                font_size="18px",
                font_weight="700",
                color=SIDEBAR_TEXT,
                letter_spacing="-0.02em",
            ),
            spacing="2",
            align="center",
        ),
        padding="20px 16px 12px 16px",
    )


def new_chat_button(on_click: rx.EventHandler) -> rx.Component:
    """Button to start a new conversation."""
    return rx.box(
        rx.button(
            rx.icon("plus", size=16),
            rx.text("Uj beszelgetes", font_size="13px"),
            on_click=on_click,
            width="100%",
            variant="outline",
            cursor="pointer",
            style={
                "border": f"1px solid {SIDEBAR_BORDER}",
                "color": SIDEBAR_TEXT,
                "background": "transparent",
                "border_radius": "8px",
                "padding": "10px 12px",
                "justify_content": "flex-start",
                "gap": "8px",
                "_hover": {
                    "background": SIDEBAR_HOVER,
                },
            },
        ),
        padding="0 12px 8px 12px",
    )


def conversation_item(
    conv,
    current_id: rx.Var,
    on_select: rx.EventHandler,
    on_delete: rx.EventHandler,
) -> rx.Component:
    """Single conversation entry in the sidebar list."""
    is_active = conv.id == current_id
    return rx.box(
        rx.hstack(
            rx.icon(
                "message-square",
                size=14,
                color=rx.cond(is_active, SIDEBAR_TEXT, SIDEBAR_TEXT_DIM),
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    conv.title,
                    font_size="13px",
                    color=rx.cond(is_active, SIDEBAR_TEXT, SIDEBAR_TEXT_DIM),
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                    max_width="160px",
                    line_height="1.4",
                ),
                rx.text(
                    conv.created_at,
                    font_size="11px",
                    color=SIDEBAR_TEXT_DIM,
                    line_height="1.2",
                ),
                spacing="0",
                align_items="start",
                flex="1",
                min_width="0",
            ),
            rx.icon(
                "trash-2",
                size=13,
                color=SIDEBAR_TEXT_DIM,
                cursor="pointer",
                on_click=on_delete(conv.id),
                _hover={"color": "#EF4444"},
                flex_shrink="0",
                opacity="0",
                class_name="conv-delete-icon",
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        padding="8px 12px",
        border_radius="8px",
        cursor="pointer",
        on_click=on_select(conv.id),
        background=rx.cond(is_active, SIDEBAR_HOVER, "transparent"),
        _hover={
            "background": SIDEBAR_HOVER,
            "& .conv-delete-icon": {"opacity": "1"},
        },
        transition="background 0.15s ease",
    )


def sidebar_settings(role: rx.Var, on_role_change: rx.EventHandler) -> rx.Component:
    """Settings section at the bottom of the sidebar."""
    return rx.box(
        rx.vstack(
            rx.separator(color=SIDEBAR_BORDER),
            rx.hstack(
                rx.icon("settings", size=14, color=SIDEBAR_TEXT_DIM),
                rx.text("Szerepkor", font_size="12px", color=SIDEBAR_TEXT_DIM),
                spacing="2",
                align="center",
            ),
            rx.select(
                ["baseline", "mentor", "expert"],
                value=role,
                on_change=on_role_change,
                size="1",
                variant="surface",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        padding="12px 16px 20px 16px",
    )


def sidebar(
    conversations: rx.Var,
    current_id: rx.Var,
    role: rx.Var,
    sidebar_open: rx.Var,
    on_new_chat: rx.EventHandler,
    on_select: rx.EventHandler,
    on_delete: rx.EventHandler,
    on_role_change: rx.EventHandler,
) -> rx.Component:
    """Full sidebar with conversation history, new-chat button, and settings."""
    return rx.box(
        rx.vstack(
            # -- Top: logo + new chat button --
            sidebar_logo(),
            new_chat_button(on_new_chat),
            # -- Middle: conversation list (scrollable) --
            rx.box(
                rx.foreach(
                    conversations,
                    lambda conv: conversation_item(
                        conv, current_id, on_select, on_delete
                    ),
                ),
                overflow_y="auto",
                flex="1",
                padding="4px 4px",
                width="100%",
            ),
            # -- Bottom: settings --
            sidebar_settings(role, on_role_change),
            spacing="0",
            height="100%",
        ),
        width=rx.cond(sidebar_open, SIDEBAR_WIDTH, "0px"),
        min_width=rx.cond(sidebar_open, SIDEBAR_WIDTH, "0px"),
        height="100vh",
        background=SIDEBAR_BG,
        overflow="hidden",
        transition="width 0.25s ease, min-width 0.25s ease",
        border_right=f"1px solid {SIDEBAR_BORDER}",
        flex_shrink="0",
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def chat_header(
    title: rx.Var,
    role_display: rx.Var,
    on_toggle_sidebar: rx.EventHandler,
) -> rx.Component:
    """Top header bar with sidebar toggle, title, and role badge."""
    return rx.box(
        rx.hstack(
            rx.icon(
                "panel-left",
                size=20,
                color="#6B7280",
                cursor="pointer",
                on_click=on_toggle_sidebar,
                _hover={"color": "#111827"},
            ),
            rx.text(
                title,
                font_size="15px",
                font_weight="600",
                color="#111827",
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
                flex="1",
            ),
            rx.badge(
                role_display,
                color_scheme="green",
                variant="soft",
                size="1",
            ),
            spacing="3",
            align="center",
            width="100%",
            padding="12px 20px",
        ),
        background=HEADER_BG,
        border_bottom=f"1px solid {HEADER_BORDER}",
        flex_shrink="0",
    )


# ---------------------------------------------------------------------------
# Message components
# ---------------------------------------------------------------------------
def loading_dots() -> rx.Component:
    """Animated loading indicator for pending assistant responses."""
    return rx.hstack(
        rx.box(
            width="8px",
            height="8px",
            border_radius="50%",
            background="#9CA3AF",
            class_name="loading-dot dot-1",
        ),
        rx.box(
            width="8px",
            height="8px",
            border_radius="50%",
            background="#9CA3AF",
            class_name="loading-dot dot-2",
        ),
        rx.box(
            width="8px",
            height="8px",
            border_radius="50%",
            background="#9CA3AF",
            class_name="loading-dot dot-3",
        ),
        spacing="1",
        align="center",
        padding="4px 0",
    )


def assistant_avatar() -> rx.Component:
    """Small avatar icon for assistant messages."""
    return rx.box(
        rx.icon("bot", size=16, color="#FFFFFF"),
        width="28px",
        height="28px",
        min_width="28px",
        border_radius="50%",
        background=ACCENT,
        display="flex",
        align_items="center",
        justify_content="center",
        flex_shrink="0",
    )


def user_avatar() -> rx.Component:
    """Small avatar icon for user messages."""
    return rx.box(
        rx.icon("user", size=16, color="#FFFFFF"),
        width="28px",
        height="28px",
        min_width="28px",
        border_radius="50%",
        background=USER_BUBBLE_BG,
        display="flex",
        align_items="center",
        justify_content="center",
        flex_shrink="0",
    )


def citation_badge(msg, on_toggle: rx.EventHandler) -> rx.Component:
    """Small clickable badge showing citation count."""
    citation_count = msg.citations.length()
    return rx.cond(
        citation_count > 0,
        rx.box(
            rx.hstack(
                rx.icon("file-text", size=12, color=ACCENT),
                rx.text(
                    citation_count.to(str) + " forras",
                    font_size="11px",
                    color=ACCENT,
                    font_weight="500",
                ),
                spacing="1",
                align="center",
                cursor="pointer",
                on_click=on_toggle(msg.id),
                padding="4px 8px",
                border_radius="6px",
                border=f"1px solid {ACCENT}",
                _hover={"background": "#F0FDF9"},
                transition="background 0.15s ease",
            ),
            margin_top="6px",
        ),
        rx.fragment(),
    )


def message_bubble(msg, on_citation_toggle: rx.EventHandler) -> rx.Component:
    """Single chat message - user (right) or assistant (left)."""
    is_user = msg.role == "user"
    is_loading = msg.is_loading

    # -- User message: right-aligned blue bubble --
    user_message = rx.hstack(
        rx.spacer(),
        rx.box(
            rx.text(
                msg.content,
                color=USER_BUBBLE_TEXT,
                font_size="14px",
                line_height="1.6",
                white_space="pre-wrap",
            ),
            background=USER_BUBBLE_BG,
            padding="10px 16px",
            border_radius="18px 18px 4px 18px",
            max_width="70%",
            word_break="break-word",
        ),
        user_avatar(),
        spacing="2",
        align="end",
        width="100%",
        justify="end",
    )

    # -- Assistant message: left-aligned light bubble with avatar --
    assistant_message = rx.hstack(
        assistant_avatar(),
        rx.vstack(
            rx.cond(
                is_loading,
                # Loading state: animated dots
                rx.box(
                    loading_dots(),
                    background=ASSISTANT_BUBBLE_BG,
                    padding="12px 16px",
                    border_radius="18px 18px 18px 4px",
                    border=f"1px solid {ASSISTANT_BUBBLE_BORDER}",
                    min_width="60px",
                ),
                # Normal content: markdown rendered
                rx.box(
                    rx.markdown(
                        msg.content,
                        component_map={
                            "p": lambda text: rx.text(
                                text,
                                color=ASSISTANT_BUBBLE_TEXT,
                                font_size="14px",
                                line_height="1.6",
                                margin_bottom="8px",
                            ),
                            "code": lambda text: rx.code(
                                text,
                                color="#E53E3E",
                                background="#F7F7F8",
                                padding="1px 4px",
                                border_radius="3px",
                                font_size="13px",
                            ),
                            "pre": lambda text, **props: rx.box(
                                rx.code_block(
                                    text,
                                    language="python",
                                    show_line_numbers=True,
                                    theme="one-light",
                                ),
                                margin_y="8px",
                                border_radius="8px",
                                overflow="hidden",
                            ),
                        },
                    ),
                    background=ASSISTANT_BUBBLE_BG,
                    padding="10px 16px",
                    border_radius="18px 18px 18px 4px",
                    border=f"1px solid {ASSISTANT_BUBBLE_BORDER}",
                    max_width="70%",
                    word_break="break-word",
                ),
            ),
            # Citation badge under the assistant bubble
            rx.cond(
                ~is_loading,
                citation_badge(msg, on_citation_toggle),
                rx.fragment(),
            ),
            spacing="0",
            align_items="start",
        ),
        spacing="2",
        align="start",
        width="100%",
    )

    return rx.box(
        rx.cond(is_user, user_message, assistant_message),
        width="100%",
        padding_x="20px",
        padding_y="6px",
    )


def empty_state() -> rx.Component:
    """Placeholder shown when there are no messages."""
    return rx.center(
        rx.vstack(
            rx.icon("message-circle", size=48, color="#D1D5DB", stroke_width=1.5),
            rx.text(
                "Kezdjen egy uj beszelgetest",
                font_size="18px",
                font_weight="500",
                color="#6B7280",
            ),
            rx.text(
                "Irja be a kerdeset az also mezoben, vagy kattintson az 'Uj beszelgetes' gombra.",
                font_size="14px",
                color="#9CA3AF",
                text_align="center",
                max_width="400px",
            ),
            spacing="3",
            align="center",
        ),
        flex="1",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Message list
# ---------------------------------------------------------------------------
def message_area(
    messages: rx.Var,
    has_messages: rx.Var,
    on_citation_toggle: rx.EventHandler,
) -> rx.Component:
    """Scrollable message area with auto-scroll."""
    return rx.cond(
        has_messages,
        rx.box(
            rx.foreach(
                messages,
                lambda msg: message_bubble(msg, on_citation_toggle),
            ),
            display="flex",
            flex_direction="column",
            overflow_y="auto",
            flex="1",
            padding_y="16px",
            width="100%",
            # CSS to auto-scroll to the bottom
            style={
                "scroll_behavior": "smooth",
                "overflow_anchor": "auto",
            },
        ),
        empty_state(),
    )


# ---------------------------------------------------------------------------
# Citation panel (right drawer)
# ---------------------------------------------------------------------------
def citation_card(citation) -> rx.Component:
    """Single citation card in the panel."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("file-text", size=14, color=ACCENT),
                rx.text(
                    citation["document_name"],
                    font_size="13px",
                    font_weight="600",
                    color="#111827",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.text(
                citation["excerpt"],
                font_size="12px",
                color="#6B7280",
                line_height="1.5",
                max_height="80px",
                overflow="hidden",
            ),
            rx.cond(
                citation.contains("relevance_score"),
                rx.badge(
                    "Relevancia: " + (citation["relevance_score"] * 100).to(int).to(str) + "%",
                    color_scheme="green",
                    variant="soft",
                    size="1",
                ),
                rx.fragment(),
            ),
            spacing="2",
        ),
        padding="12px",
        border_radius="8px",
        border=f"1px solid {CITATION_BORDER}",
        background=CITATION_BG,
    )


def citation_panel(
    citations: rx.Var,
    show: rx.Var,
    on_close: rx.EventHandler,
) -> rx.Component:
    """Right-side panel showing citations for a selected message."""
    return rx.cond(
        show,
        rx.box(
            rx.vstack(
                # Panel header
                rx.hstack(
                    rx.text(
                        "Forrasok",
                        font_size="14px",
                        font_weight="600",
                        color="#111827",
                    ),
                    rx.spacer(),
                    rx.icon(
                        "x",
                        size=18,
                        color="#6B7280",
                        cursor="pointer",
                        on_click=on_close,
                        _hover={"color": "#111827"},
                    ),
                    width="100%",
                    align="center",
                    padding="16px",
                    border_bottom=f"1px solid {CITATION_BORDER}",
                ),
                # Citation list
                rx.box(
                    rx.foreach(citations, citation_card),
                    overflow_y="auto",
                    flex="1",
                    padding="12px",
                    display="flex",
                    flex_direction="column",
                    gap="8px",
                ),
                spacing="0",
                height="100%",
            ),
            width="300px",
            min_width="300px",
            height="100vh",
            background="#FAFAFA",
            border_left=f"1px solid {CITATION_BORDER}",
            flex_shrink="0",
            transition="width 0.25s ease",
        ),
        rx.fragment(),
    )


# ---------------------------------------------------------------------------
# Input area
# ---------------------------------------------------------------------------
def chat_input(
    current_input: rx.Var,
    on_change: rx.EventHandler,
    on_send: rx.EventHandler,
    is_processing: rx.Var,
) -> rx.Component:
    """Bottom input area with textarea and send button."""
    return rx.box(
        rx.box(
            rx.hstack(
                rx.text_area(
                    value=current_input,
                    on_change=on_change,
                    placeholder="Irja be az uzenetet...",
                    auto_height=True,
                    min_height="44px",
                    max_height="200px",
                    flex="1",
                    resize="none",
                    style={
                        "border": f"1px solid {INPUT_BORDER}",
                        "border_radius": "12px",
                        "padding": "10px 16px",
                        "font_size": "14px",
                        "line_height": "1.5",
                        "background": INPUT_BG,
                        "outline": "none",
                        "_focus": {
                            "border_color": INPUT_FOCUS_BORDER,
                            "box_shadow": f"0 0 0 2px {INPUT_FOCUS_BORDER}33",
                        },
                    },
                ),
                rx.button(
                    rx.cond(
                        is_processing,
                        rx.spinner(size="1"),
                        rx.icon("send", size=18),
                    ),
                    on_click=on_send,
                    disabled=is_processing,
                    size="3",
                    style={
                        "background": ACCENT,
                        "color": "#FFFFFF",
                        "border_radius": "12px",
                        "width": "44px",
                        "height": "44px",
                        "min_width": "44px",
                        "padding": "0",
                        "cursor": "pointer",
                        "_hover": {"background": ACCENT_HOVER},
                        "_disabled": {
                            "opacity": "0.5",
                            "cursor": "not-allowed",
                        },
                    },
                ),
                spacing="2",
                align="end",
                width="100%",
            ),
            max_width="768px",
            width="100%",
            margin="0 auto",
        ),
        padding="12px 20px 20px 20px",
        background=CONTENT_BG,
        border_top=f"1px solid {HEADER_BORDER}",
        flex_shrink="0",
    )


# ---------------------------------------------------------------------------
# Loading animation CSS
# ---------------------------------------------------------------------------
LOADING_CSS = """
@keyframes loadingPulse {
    0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1.0); }
}
.loading-dot {
    animation: loadingPulse 1.4s ease-in-out infinite;
}
.dot-1 { animation-delay: 0s; }
.dot-2 { animation-delay: 0.2s; }
.dot-3 { animation-delay: 0.4s; }
"""


# ---------------------------------------------------------------------------
# Main chat_container: assembles everything
# ---------------------------------------------------------------------------
def chat_container(
    # State vars
    conversations: rx.Var,
    current_conversation_id: rx.Var,
    current_messages: rx.Var,
    current_input: rx.Var,
    current_title: rx.Var,
    role: rx.Var,
    role_display: rx.Var,
    is_processing: rx.Var,
    sidebar_open: rx.Var,
    has_messages: rx.Var,
    show_citations: rx.Var,
    selected_citations: rx.Var,
    # Event handlers
    on_new_chat: rx.EventHandler,
    on_select_conversation: rx.EventHandler,
    on_delete_conversation: rx.EventHandler,
    on_role_change: rx.EventHandler,
    on_toggle_sidebar: rx.EventHandler,
    on_send: rx.EventHandler,
    on_input_change: rx.EventHandler,
    on_citation_toggle: rx.EventHandler,
    on_citation_close: rx.EventHandler,
) -> rx.Component:
    """Full ChatGPT/Claude-style chat layout.

    Composed of: sidebar | main content area | optional citation panel.
    """
    return rx.fragment(
        # Inject loading animation CSS
        rx.el.style(LOADING_CSS),
        rx.hstack(
            # -- Left: Sidebar --
            sidebar(
                conversations=conversations,
                current_id=current_conversation_id,
                role=role,
                sidebar_open=sidebar_open,
                on_new_chat=on_new_chat,
                on_select=on_select_conversation,
                on_delete=on_delete_conversation,
                on_role_change=on_role_change,
            ),
            # -- Center: Main chat area --
            rx.vstack(
                chat_header(
                    title=current_title,
                    role_display=role_display,
                    on_toggle_sidebar=on_toggle_sidebar,
                ),
                message_area(
                    messages=current_messages,
                    has_messages=has_messages,
                    on_citation_toggle=on_citation_toggle,
                ),
                chat_input(
                    current_input=current_input,
                    on_change=on_input_change,
                    on_send=on_send,
                    is_processing=is_processing,
                ),
                spacing="0",
                flex="1",
                height="100vh",
                background=CONTENT_BG,
                min_width="0",
            ),
            # -- Right: Citation panel --
            citation_panel(
                citations=selected_citations,
                show=show_citations,
                on_close=on_citation_close,
            ),
            spacing="0",
            width="100%",
            height="100vh",
            overflow="hidden",
        ),
    )
