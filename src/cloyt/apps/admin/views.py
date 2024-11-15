from datetime import timedelta, datetime
from typing import Type, Any

import wtforms
from dishka import AsyncContainer
from fastapi import FastAPI
from sqladmin import ModelView, Admin
from sqladmin._queries import Query
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.requests import Request
from wtforms import Form

from cloyt.apps.admin.auth_backend import AdminAuthBackend
from cloyt.domain.models import (
    Employee,
    Project,
    ProjectMember,
    WorkItem,
    WorkItemType,
)
from cloyt.infrastructure import AdminConfig


class EmployeeAdmin(ModelView, model=Employee):
    model: Type[Employee]

    column_list = [
        Employee.full_name,
        Employee.projects,
        Employee.created_at,
    ]
    form_create_rules = [
        "full_name",
    ]
    form_edit_rules = [
        "full_name",
    ]

    def list_query(self, request: Request) -> Select:
        stmt = (select(self.model)
                .where(self.model.deleted_at.is_(None)))
        return stmt

    async def delete_model(self, request: Request, pk: Any) -> None:
        await Query(self).update(
            pk=pk,
            data={
                "deleted_at": datetime.now(),
            },
            request=request,
        )

    async def scaffold_form(self, *args) -> Type[Form]:
        form = await super().scaffold_form()
        form.youtrack_token = wtforms.PasswordField(
            "Youtrack token", render_kw={"class": "form-control"}
        )
        form.clockify_token = wtforms.PasswordField(
            "Clockify token", render_kw={"class": "form-control"}
        )
        return form

    async def on_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        if not is_created:
            if "clockify_token" in data and not data["clockify_token"]:
                data["clockify_token"] = model.clockify_token
            if "youtrack_token" in data and not data["youtrack_token"]:
                data["youtrack_token"] = model.youtrack_token


class ProjectAdmin(ModelView, model=Project):
    column_list = [
        Project.name,
        Project.short_name,
        Project.youtrack_id,
        Project.default_work_item_type,
        Project.created_at,
        Project.employees,
    ]


class ProjectMemberAdmin(ModelView, model=ProjectMember):
    column_list = [
        ProjectMember.employee,
        ProjectMember.project,
        ProjectMember.sync_enabled,
        ProjectMember.default_work_item_type,
    ]
    form_edit_rules = [
        "sync_enabled",
        "default_work_item_type",
    ]


class WorkItemAdmin(ModelView, model=WorkItem):
    column_list = [
        WorkItem.text,
        WorkItem.clockify_time_entry_id,
        WorkItem.youtrack_id,
        WorkItem.work_item_type,
    ]
    can_edit = False
    can_create = False


class WorkItemTypeAdmin(ModelView, model=WorkItemType):
    column_list = [
        WorkItemType.name,
        WorkItemType.youtrack_id,
        WorkItemType.created_at,
    ]

    can_edit = [
        "title",
    ]


async def setup_admin(container: AsyncContainer, app: FastAPI) -> Admin:
    engine = await container.get(AsyncEngine)
    config: AdminConfig = await container.get(AdminConfig)
    admin = Admin(app, engine, authentication_backend=AdminAuthBackend(
        secret_key=config.secret_key,
        username=config.username,
        password=config.password,
        login_duration=timedelta(days=30),
    ))

    admin.add_view(EmployeeAdmin)
    admin.add_view(ProjectAdmin)
    admin.add_view(WorkItemTypeAdmin)
    admin.add_view(ProjectMemberAdmin)
    admin.add_view(WorkItemAdmin)

    return admin
