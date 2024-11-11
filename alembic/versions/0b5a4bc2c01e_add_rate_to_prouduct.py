"""add rate to prouduct

Revision ID: 0b5a4bc2c01e
Revises: 074a78e5272e
Create Date: 2024-11-11 11:26:23.327103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b5a4bc2c01e'
down_revision: Union[str, None] = '074a78e5272e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('products', sa.Column('rate', sa.Integer(), nullable=True))

def downgrade():
    # Remove the 'rate' column from the 'products' table if downgrading
    op.drop_column('products', 'rate')
