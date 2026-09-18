"""initial PackBridge schema

Revision ID: 0001_initial_schema
Revises:
"""

from alembic import op

from packbridge.extensions import db
import packbridge.models  # noqa: F401


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # checkfirst=True makes this safe for early PackBridge POC databases that
    # were created by db.create_all() before migrations were introduced.
    db.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade():
    db.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
