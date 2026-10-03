"""enable row level security

PostgreSQL only. Managed platforms such as Supabase expose the `public` schema through an
HTTP data API that is reachable with a public key. A table without row level security (RLS)
can be read and written through that API, including `users.password_hash`.

Enabling RLS without any policy denies every role except the table owner. The API connects
as the owner and is not affected; nobody else can read or write these tables. SQLite has no
RLS, so the migration does nothing there.

Every migration that creates a table must enable RLS for it as well, for example:

    op.execute("ALTER TABLE my_table ENABLE ROW LEVEL SECURITY")

Revision ID: 19b8b59854e4
Revises: 9cfe287c94fe
Create Date: 2026-10-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "19b8b59854e4"
down_revision: str | None = "9cfe287c94fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Only tables owned by the current role: ALTER TABLE on someone else's table would fail.
_FOR_EACH_OWN_TABLE = """
DO $$
DECLARE t record;
BEGIN
  FOR t IN
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public' AND tableowner = current_user
  LOOP
    EXECUTE format('ALTER TABLE public.%I {action} ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
"""


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(_FOR_EACH_OWN_TABLE.format(action="ENABLE"))


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(_FOR_EACH_OWN_TABLE.format(action="DISABLE"))
