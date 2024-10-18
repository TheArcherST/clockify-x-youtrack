from datetime import datetime
from os import getenv
from typing import AsyncIterable, Iterable, Type

import zoneinfo
from dishka import Provider, provide, Scope
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    TomlConfigSettingsSource,
    PydanticBaseSettingsSource,
)
from sqlalchemy import (
    create_engine,
    Engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
)


class PostgresConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    
    def get_sqlalchemy_url(self, driver: str):
        return "postgresql+{}://{}:{}@{}:{}/{}".format(
            driver,
            self.user,
            self.password,
            self.host,
            self.port,
            self.database,
        )


class AdminConfig(BaseModel):
    secret_key: str
    username: str
    password: str
    logging_level: str = "DEBUG"
    logs_path: str


class DaemonConfig(BaseModel):
    sync_tolerance_delay_seconds: int
    sync_throttling_delay_seconds: int
    sync_window_size: int
    ignore_entries_before: datetime
    youtrack_base_url: str
    tz: zoneinfo.ZoneInfo
    logging_level: str = "DEBUG"
    logs_path: str


class CloytConfig(BaseSettings):
    postgres: PostgresConfig = None
    daemon: DaemonConfig = None
    admin: AdminConfig = None

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_prefix="CLOYT__",
        toml_file="cloyt.toml",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: Type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            TomlConfigSettingsSource(settings_cls),
        )


class InfrastructureProvider(Provider):
    @provide(scope=Scope.APP)
    def get_config(self) -> CloytConfig:
        return CloytConfig()

    @provide(scope=Scope.APP)
    def get_postgres_config(
            self,
            config: CloytConfig,
    ) -> PostgresConfig:
        if config.postgres is None:
            raise RuntimeError("Postgres configuration not found")

        return config.postgres

    @provide(scope=Scope.APP)
    def get_admin_config(
            self,
            config: CloytConfig,
    ) -> AdminConfig:
        if config.admin is None:
            raise RuntimeError("Admin panel configuration not found")

        return config.admin

    @provide(scope=Scope.APP)
    def get_daemon_config(
            self,
            config: CloytConfig,
    ) -> DaemonConfig:
        if config.daemon is None:
            raise RuntimeError("Daemon configuration not found.")

        return config.daemon

    @provide(scope=Scope.APP)
    async def get_async_engine(
            self,
            postgres_config: PostgresConfig,
    ) -> AsyncEngine:
        return create_async_engine(
            postgres_config.get_sqlalchemy_url("asyncpg"),
        )

    @provide(scope=Scope.REQUEST)
    async def get_async_session(
            self,
            engine: AsyncEngine,
    ) -> AsyncIterable[AsyncSession]:
        async with AsyncSession(bind=engine) as session:
            yield session

    @provide(scope=Scope.APP)
    def get_sync_engine(
            self,
            postgres_config: PostgresConfig,
    ) -> Engine:
        return create_engine(
            postgres_config.get_sqlalchemy_url("psycopg"),
        )

    @provide(scope=Scope.REQUEST)
    def get_sync_session(
            self,
            engine: Engine
    ) -> Iterable[Session]:
        with Session(bind=engine, expire_on_commit=False) as session:
            yield session
