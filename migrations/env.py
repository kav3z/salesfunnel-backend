from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from sqlmodel import SQLModel
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- IMPORT ALL MODELS HERE ---
# If these are missing, Alembic tries to delete their tables!
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.distributor_profile import DistributorProfile
from app.models.wholesaler_profile import WholesalerProfile
# Add the models that were causing issues:
# Ensure these import paths are correct for your project structure
try:
    from app.models.audit_log import AuditLog
    from app.models.cart import Cart
    from app.models.payment import Payment
    from app.models.notification import Notification
except ImportError:
    pass # If the file doesn't exist, ignore it, but check your paths.
# ------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

url = os.getenv("DATABASE_URL")
if url:
    config.set_main_option("sqlalchemy.url", url)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
