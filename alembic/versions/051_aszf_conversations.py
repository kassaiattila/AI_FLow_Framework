"""Sprint X / SX-4 — aszf_conversations + aszf_conversation_turns persistence.

Revision ID: 051
Revises: 050
Create Date: 2026-04-28

Conversation-history layer that promotes the stateless ``/v1/chat/completions``
RAG retrieval path into a professional management surface (sidebar history,
persona switcher, citation card, cost meter, transcript export). The
retrieval API itself stays byte-stable; persistence sits *above* it.

Two tables:

* ``aszf_conversations`` — one row per conversation. Tenant-scoped, persona-
  pinned (operator can switch mid-conversation; the marker is rendered in
  the turn stream by the UI), bound to a single RAG collection name. Title
  is operator-editable (NULL → UI labels from first user-turn snippet).

* ``aszf_conversation_turns`` — one row per turn (user OR assistant).
  ``turn_index`` is 0-based and UNIQUE per conversation so render order is
  deterministic regardless of clock skew. Citations + cost + latency only
  populate on assistant turns (NULL on user turns).

CHECK constraints pin the persona + role enums at write time so a stray
client cannot persist garbage. ON DELETE CASCADE on the FK keeps cleanup
trivial when v1.8.1 ships ``DELETE /conversations/{id}``.

Indexes:

* ``(tenant_id, updated_at DESC)`` — sidebar list (fast per-tenant ordered
  pagination).
* ``(conversation_id, turn_index)`` UNIQUE — turn render order + a free
  duplicate-write guard.

Idempotent + reversible: upgrade creates both tables + indexes, downgrade
drops them in reverse order.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aszf_conversations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("persona", sa.Text(), nullable=False),
        sa.Column("collection_name", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "persona IN ('baseline','expert','mentor')",
            name="ck_aszf_conversations_persona_enum",
        ),
    )
    op.create_index(
        "ix_aszf_conversations_tenant_updated",
        "aszf_conversations",
        ["tenant_id", "updated_at"],
    )

    op.create_table(
        "aszf_conversation_turns",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("aszf_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", JSONB(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "role IN ('user','assistant')",
            name="ck_aszf_conversation_turns_role_enum",
        ),
        sa.CheckConstraint(
            "turn_index >= 0",
            name="ck_aszf_conversation_turns_turn_index_nonneg",
        ),
        sa.CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="ck_aszf_conversation_turns_cost_nonneg",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_aszf_conversation_turns_latency_nonneg",
        ),
    )
    op.create_index(
        "ux_aszf_conversation_turns_conv_index",
        "aszf_conversation_turns",
        ["conversation_id", "turn_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_aszf_conversation_turns_conv_index",
        table_name="aszf_conversation_turns",
    )
    op.drop_table("aszf_conversation_turns")
    op.drop_index(
        "ix_aszf_conversations_tenant_updated",
        table_name="aszf_conversations",
    )
    op.drop_table("aszf_conversations")
