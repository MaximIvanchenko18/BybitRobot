"""base 4 tables created

Revision ID: dd678e9a5c66
Revises: 747e8f32913b
Create Date: 2025-05-14 17:45:46.772180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd678e9a5c66'
down_revision: Union[str, None] = '747e8f32913b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('trades', sa.Column('is_active', sa.Boolean(), nullable=False))
    op.alter_column('trades', 'current_pnl',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.drop_column('trades', 'in_position')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('trades', sa.Column('in_position', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.alter_column('trades', 'current_pnl',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False)
    op.drop_column('trades', 'is_active')
    # ### end Alembic commands ###
