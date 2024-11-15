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
    deleted_at: Mapped[datetime | None]
    comment: Mapped[str | None]

    projects: Mapped[list[Project]] = relationship(
        secondary=lambda: ProjectMember.__table__,
        viewonly=False,
    )

    def __str__(self):
        return self.full_name


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    youtrack_id: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    short_name: Mapped[str]
    default_work_item_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_item_type.id"),
    )

    employees: Mapped[list[Employee]] = relationship(
        secondary=lambda: ProjectMember.__table__,
        viewonly=True,
    )
    default_work_item_type: Mapped[WorkItemType | None] = relationship(
        foreign_keys=default_work_item_type_id,
    )

    def __str__(self):
        return f"{self.name} ({self.short_name})"


class WorkItemType(Base):
    __tablename__ = "work_item_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    name: Mapped[str] = mapped_column(unique=True)
    youtrack_id: Mapped[str] = mapped_column(unique=True)

    def __str__(self):
        return f"{self.name} (youtrack_id={self.youtrack_id})"


class ProjectMember(Base):
    __tablename__ = "project_member"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    default_work_item_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_item_type.id"),
    )
    sync_enabled: Mapped[bool] = mapped_column(default=True)
    comment: Mapped[str | None]

    project: Mapped[Project] = relationship(viewonly=True)
    employee: Mapped[Employee] = relationship(viewonly=True)
    default_work_item_type: Mapped[WorkItemType | None] = relationship()


class WorkItem(Base):
    __tablename__ = "work_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_member_id: Mapped[int] = mapped_column(
        ForeignKey("project_member.id"),
    )
    clockify_time_entry_id: Mapped[str] = mapped_column(unique=True)
    youtrack_id: Mapped[str] = mapped_column(unique=True)
    duration: Mapped[timedelta]
    work_item_type_id: Mapped[str | None] = mapped_column(
        ForeignKey("work_item_type.id"),
    )
    text: Mapped[str]

    work_item_type: Mapped[WorkItemType] = relationship()
