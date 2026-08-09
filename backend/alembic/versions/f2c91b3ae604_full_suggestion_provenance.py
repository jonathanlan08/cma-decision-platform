"""Full suggestion provenance and unknown-friendly subject fields.

* weight_configurations gains suggestions_fingerprint: a hash of ALL inputs
  that shape suggested adjustments (assumptions + subject + comparable
  fields), replacing the assumptions-only comparison as the outdatedness
  authority.
* subject_properties.property_type / has_pool become nullable: like the
  comparables, an unknown value is stored as unknown instead of defaulting
  to single_family / no pool.

Revision ID: f2c91b3ae604
Revises: e4a8c15d72f9
Create Date: 2026-08-09
"""
import sqlalchemy as sa
from alembic import op

revision = "f2c91b3ae604"
down_revision = "e4a8c15d72f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("weight_configurations",
                  sa.Column("suggestions_fingerprint", sa.String(length=64),
                            nullable=True))
    with op.batch_alter_table("subject_properties") as batch:
        batch.alter_column("property_type", existing_type=sa.String(length=30),
                           nullable=True)
        batch.alter_column("has_pool", existing_type=sa.Boolean(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("subject_properties") as batch:
        batch.alter_column("has_pool", existing_type=sa.Boolean(), nullable=False)
        batch.alter_column("property_type", existing_type=sa.String(length=30),
                           nullable=False)
    op.drop_column("weight_configurations", "suggestions_fingerprint")
