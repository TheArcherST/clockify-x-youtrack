from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str]
    clockify_token: Mapped[str] = mapped_column(unique=True)
    clockify_user_id: Mapped[str] = mapped_column(unique=True)
    clockify_workspace_id: Mapped[str]
    youtrack_token: Mapped[str] = mapped_column(unique=True)
    comment: Mapped[str | None]

    projects: Mapped[list[Project]] = relationship(
        secondary="ProjectMember.__table__",
    )


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    clockify_id: Mapped[str] = mapped_column(unique=True)
    youtrack_id: Mapped[str] = mapped_column(unique=True)

    employees: Mapped[list[Employee]] = relationship(
        secondary="ProjectMember.__table__",
    )


class ProjectMember(Base):
    __tablename__ = "project_member"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    sync_enabled: Mapped[bool] = mapped_column(default=True)
    comment: Mapped[str | None]

    project: Mapped[Project] = relationship()
    employee: Mapped[Employee] = relationship()


class JobType(Base):
    __tablename__ = "job_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(unique=True)
    youtrack_id: Mapped[str] = mapped_column(unique=True)


class WorkItem(Base):
    __tablename__ = "work_item"

    project_member_id: Mapped[int] = mapped_column(
        ForeignKey("project_member.id"),
    )
    clockify_time_record_id: Mapped[str] = mapped_column(unique=True)
    youtrack_id: Mapped[str] = mapped_column(unique=True)
    tracked_period: Mapped[timedelta]
    job_type_id: Mapped[int] = mapped_column(ForeignKey("job_type.id"))
    description: Mapped[str]

    work_item_type: Mapped[JobType] = relationship()
