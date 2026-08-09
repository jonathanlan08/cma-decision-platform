"""Suggestion provenance and strategy-to-valuation linkage.

* weight_configurations gains suggestions_assumptions: the assumption snapshot
  taken when suggested adjustments were last generated, so outdated suggested
  amounts can be detected.
* listing_strategies gains valuation_id: the valuation the strategy's derived
  metrics were computed against.

Revision ID: e4a8c15d72f9
Revises: b7d2f4a91c3e
Create Date: 2026-08-09
"""
import sqlalchemy as sa
from alembic import op

revision = "e4a8c15d72f9"
down_revision = "b7d2f4a91c3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("weight_configurations",
                  sa.Column("suggestions_assumptions", sa.JSON(), nullable=True))
    with op.batch_alter_table("listing_strategies") as batch:
        batch.add_column(sa.Column("valuation_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_listing_strategies_valuation_id",
                                 "valuation_results", ["valuation_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("listing_strategies") as batch:
        batch.drop_constraint("fk_listing_strategies_valuation_id", type_="foreignkey")
        batch.drop_column("valuation_id")
    op.drop_column("weight_configurations", "suggestions_assumptions")
