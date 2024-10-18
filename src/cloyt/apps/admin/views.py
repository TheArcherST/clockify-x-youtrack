from datetime import timedelta

from dishka import AsyncContainer
from fastapi import FastAPI
from sqladmin import ModelView, Admin
from sqlalchemy.ext.asyncio import AsyncEngine

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
    column_list = [
        Employee.full_name,
        Employee.clockify_token,
        Employee.youtrack_token,
        Employee.created_at,
        Employee.projects,
    ]
    form_edit_rules = [
        "full_name",
        "clockify_token",
        "youtrack_token",
        "sync_by_default",
        "projects",
    ]


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
