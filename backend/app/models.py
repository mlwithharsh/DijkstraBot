from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Influencer(Base):
    __tablename__ = "influencers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    profile_url: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    followers: Mapped[int | None] = mapped_column(BigInteger)
    following: Mapped[int | None] = mapped_column(BigInteger)
    posts: Mapped[int | None] = mapped_column(BigInteger)
    displayed_category: Mapped[str | None] = mapped_column(Text)
    derived_category: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    external_url: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(Text, default="apify")
    confidence_score: Mapped[float | None] = mapped_column(Float)
    country_confidence: Mapped[float | None] = mapped_column(Float)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshJob(Base):
    __tablename__ = "refresh_jobs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    profile_url: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    source: Mapped[str | None] = mapped_column(Text)
