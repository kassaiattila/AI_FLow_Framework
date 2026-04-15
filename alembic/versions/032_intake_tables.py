"""Add intake tables for v2 Phase 1a IntakePackage domain.

Revision ID: 032
Revises: 031
Create Date: 2026-04-15

Adds:
- intake_packages: multi-source intake package root entity
- intake_files: files within an intake package
- intake_descriptions: free-text descriptions associated with a package
- package_associations: many-to-many file <-> description mapping
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "032"
down_revision: str | None = "031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intake_packages",
        sa.Column("package_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="received",
        ),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "package_context",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "cross_document_signals",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("received_by", sa.String(255), nullable=True),
        sa.Column(
            "provenance_chain",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("routing_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_task_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("idx_intake_packages_tenant", "intake_packages", ["tenant_id"])
    op.create_index("idx_intake_packages_status", "intake_packages", ["status"])
    op.create_index("idx_intake_packages_created", "intake_packages", ["created_at"])

    op.create_table(
        "intake_files",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "package_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_packages.package_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sequence_index", sa.Integer(), nullable=True),
    )
    op.create_index("idx_intake_files_package", "intake_files", ["package_id"])
    op.create_index("idx_intake_files_sha256", "intake_files", ["sha256"])

    op.create_table(
        "intake_descriptions",
        sa.Column("description_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "package_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_packages.package_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default="free_text",
        ),
        sa.Column("association_confidence", sa.Float(), nullable=True),
        sa.Column("association_method", sa.String(50), nullable=True),
    )
    op.create_index(
        "idx_intake_descriptions_package",
        "intake_descriptions",
        ["package_id"],
    )

    op.create_table(
        "package_associations",
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_files.file_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "description_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_descriptions.description_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("file_id", "description_id"),
    )


def downgrade() -> None:
    op.drop_table("package_associations")
    op.drop_index("idx_intake_descriptions_package")
    op.drop_table("intake_descriptions")
    op.drop_index("idx_intake_files_sha256")
    op.drop_index("idx_intake_files_package")
    op.drop_table("intake_files")
    op.drop_index("idx_intake_packages_created")
    op.drop_index("idx_intake_packages_status")
    op.drop_index("idx_intake_packages_tenant")
    op.drop_table("intake_packages")
