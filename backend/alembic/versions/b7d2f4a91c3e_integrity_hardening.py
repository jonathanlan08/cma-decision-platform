"""Integrity hardening: staleness fingerprints and honest unknowns.

* valuation_results gains input_fingerprint (staleness detection) and
  effective_count (positive-weight sample size).
* comparable_properties.property_type / has_pool become nullable so an
  unknown value is stored as unknown instead of a guessed default.

Revision ID: b7d2f4a91c3e
Revises: 55c46505a0e3
Create Date: 2026-08-09
"""
import sqlalchemy as sa
from alembic import op

revision = "b7d2f4a91c3e"
down_revision = "55c46505a0e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("valuation_results",
                  sa.Column("effective_count", sa.Integer(), nullable=True))
    op.add_column("valuation_results",
                  sa.Column("input_fingerprint", sa.String(length=64), nullable=True))
    with op.batch_alter_table("comparable_properties") as batch:
        batch.alter_column("property_type", existing_type=sa.String(length=30),
                           nullable=True)
        batch.alter_column("has_pool", existing_type=sa.Boolean(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("comparable_properties") as batch:
        batch.alter_column("has_pool", existing_type=sa.Boolean(), nullable=False)
        batch.alter_column("property_type", existing_type=sa.String(length=30),
                           nullable=False)
    op.drop_column("valuation_results", "input_fingerprint")
    op.drop_column("valuation_results", "effective_count")
