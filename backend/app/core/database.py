import ssl
from collections.abc import AsyncGenerator

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


def normalize_database_url(url: str) -> str:
    """Accept postgres://, postgresql://, or postgresql+asyncpg:// from Supabase."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


def create_db_engine(url: str, **extra: object) -> AsyncEngine:
    parsed = make_url(normalize_database_url(url))
    query = dict(parsed.query)
    sslmode = str(query.pop("sslmode", "") or "").lower()
    query.pop("ssl", None)
    host = parsed.host or ""
    is_supabase = "supabase.co" in host or "supabase.com" in host
    is_pooler = parsed.port == 6543 or "pooler.supabase.com" in host
    connect_args: dict[str, object] = {}
    if sslmode in {"require", "verify-ca", "verify-full"} or is_supabase:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    if is_pooler:
        connect_args["statement_cache_size"] = 0
    return create_async_engine(
        parsed.set(query=query),
        pool_pre_ping=True,
        connect_args=connect_args,
        **extra,
    )


settings = get_settings()
engine = create_db_engine(settings.resolved_database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
