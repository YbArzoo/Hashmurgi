"""Add user_id to Notification

Revision ID: 27e100889c2c
Revises: 
Create Date: 2025-05-05 19:37:30.492882

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27e100889c2c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_notification_user_id',  # ✅ Add a constraint name
            'user',
            ['user_id'], ['id']
        )

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.drop_constraint('fk_notification_user_id', type_='foreignkey')  # ✅ Use same name
        batch_op.drop_column('user_id')

    # ### end Alembic commands ###
