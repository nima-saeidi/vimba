"""add rate to prouduct1

Revision ID: 699a1b65d7ad
Revises: 0b5a4bc2c01e
Create Date: 2024-11-11 23:40:23.121622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '699a1b65d7ad'
down_revision: Union[str, None] = '0b5a4bc2c01e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add a new column 'rate' to the 'products' table
    op.add_column('products', sa.Column('rate', sa.Integer(), nullable=True))

def downgrade():
    # Remove the 'rate' column from the 'products' table if downgrading
    op.drop_column('products', 'rate')