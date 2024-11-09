"""Make charge_date nullable

Revision ID: 074a78e5272e
Revises: 7583cf815dc5
Create Date: 2024-11-10 00:25:04.419430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '074a78e5272e'
down_revision: Union[str, None] = '7583cf815dc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Alter the 'charge_date' column to allow NULL values
    op.alter_column('charges', 'charge_date', nullable=True)




def downgrade():
    # Alter the 'charge_date' column to disallow NULL values
    op.alter_column('charges', 'charge_date', nullable=False)
