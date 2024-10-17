from dishka import AsyncContainer
from fastapi import FastAPI
from sqladmin import ModelView, Admin
from sqlalchemy.ext.asyncio import AsyncEngine


from cloyt.domain.models import (
    Employee,
    Project,
    ProjectMember,
    TimeRecord,
)


class EmployeeAdmin(ModelView, model=Employee):
    column_list = [
        Employee.full_name,
        Employee.clockify_token,
        Employee.youtrack_token,
        Employee.created_at,
        Employee.projects,
    ]


class ProjectAdmin(ModelView, model=Project):
    column_list = [
        Project.title,
        Project.clockify_id,
        Project.youtrack_id,
        Project.created_at,
        Project.employees,
    ]


class TimeRecordAdmin(ModelView, model=TimeRecord):
    column_list = [
        TimeRecord.description,
        TimeRecord.clockify_id,
        TimeRecord.youtrack_id,
        TimeRecord.job_type,
    ]
    can_edit = False
    can_create = False
    can_delete = False


class ProjectMemberAdmin(ModelView, model=ProjectMember):
    column_list = [
        ProjectMember.employee_id
    ]


async def setup_admin(container: AsyncContainer, app: FastAPI) -> Admin:
    engine = await container.get(AsyncEngine)
    admin = Admin(app, engine)
    return admin
