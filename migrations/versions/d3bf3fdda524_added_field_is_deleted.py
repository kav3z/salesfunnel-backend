"""Added field is_deleted

Revision ID: d3bf3fdda524
Revises: 
Create Date: 2026-02-16 02:15:29.377192

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3bf3fdda524'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only add the new column
    op.add_column('products', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    # Only remove the new column
    op.drop_column('products', 'is_deleted')
