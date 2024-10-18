"""Add default work type to proj

Revision ID: 6dbc5c7cb1df
Revises: db1e13ec28c0
Create Date: 2024-10-18 04:22:56.413155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6dbc5c7cb1df'
down_revision: Union[str, None] = 'db1e13ec28c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('default_work_item_type_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'project', 'work_item_type', ['default_work_item_type_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'project', type_='foreignkey')
    op.drop_column('project', 'default_work_item_type_id')
    # ### end Alembic commands ###
