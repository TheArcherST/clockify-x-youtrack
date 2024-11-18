import re
import time
from datetime import datetime, timedelta
from logging import getLogger
from typing import Iterable

import requests
import youtrack_sdk
from dishka import Container
from sqlalchemy import select
from sqlalchemy.orm import Session
from clockify_api_client.client import ClockifyAPIClient
from clockify_api_client import abstract_clockify
from youtrack_sdk.entities import IssueWorkItem, DurationValue, WorkItemType
from youtrack_sdk.exceptions import YouTrackException, YouTrackUnauthorized

from cloyt.domain.models import (
    ProjectMember,
    Employee,
    Project,
    WorkItem,
    WorkItemType as WorkItemTypeModel,
)
from cloyt.infrastructure import DaemonConfig


logger = getLogger(__name__)



class PatchedAbstractClockify(abstract_clockify.AbstractClockify):
    TIMEOUT = 10

    def get(self, url):
        logger.debug("Process clockify patched GET request")
        response = requests.get(
            url, headers=self.header, timeout=self.TIMEOUT)
        if response.status_code in [200, 201, 202]:
            return response.json()
        raise Exception(response.json())

    def post(self, url, payload):
        logger.debug("Process clockify patched POST request")
        response = requests.post(
            url, headers=self.header, json=payload, timeout=self.TIMEOUT)
        if response.status_code in [200, 201, 202]:
            return response.json()
        raise Exception(response.json())

    def put(self, url, payload):
        logger.debug("Process clockify patched PUT request")
        response = requests.put(
            url, headers=self.header, json=payload, timeout=self.TIMEOUT)
        if response.status_code in [200, 201, 202]:
            return response.json()
        raise Exception(response.json())

    def delete(self, url):
        logger.debug("Process clockify patched DELETE request")
        response = requests.delete(
            url, headers=self.header, timeout=self.TIMEOUT)
        if response.status_code in [200, 201, 202, 204]:
            return response.json()
        raise Exception(response.json())


abstract_clockify.AbstractClockify.get = PatchedAbstractClockify.get
abstract_clockify.AbstractClockify.post = PatchedAbstractClockify.post
abstract_clockify.AbstractClockify.put = PatchedAbstractClockify.put
abstract_clockify.AbstractClockify.delete = PatchedAbstractClockify.delete


class CloytSynchronizer:
    def __init__(
            self,
            container: Container,
    ):
        self.container = container
        self.config: DaemonConfig = container.get(DaemonConfig)

    def _sync_employee(self, container: Container, employee: Employee):
        config = self.config
        clockify_client = (
            ClockifyAPIClient()
            .build(
                api_key=employee.clockify_token,
                api_url="api.clockify.me/v1",
            )
        )
        youtrack_client = youtrack_sdk.client.Client(
            base_url=config.youtrack_base_url,
            token=employee.youtrack_token,
            timeout=5,
        )

        # sync available youtrack projects and memberships

        projects = youtrack_client.get_projects()
        with container.get(Session) as session:
            for i in projects:
                stmt = (
                    select(Project)
                    .where(Project.youtrack_id == i.id)
                )
                project: Project | None = session.scalar(stmt)
                if project is None:
                    project = Project(
                        youtrack_id=i.id,
                        name=i.name,
                        short_name=i.short_name,
                    )
                    session.add(project)
                else:
                    project.short_name = i.short_name
                    project.name = i.name
                session.flush()

                project_item_types = youtrack_client\
                    .get_project_work_item_types(
                        project_id=project.youtrack_id,
                    )
                for j in project_item_types:
                    stmt = (
                        select(WorkItemTypeModel)
                        .where(WorkItemTypeModel.youtrack_id == j.id)
                    )
                    item_type = session.scalar(stmt)
                    if item_type is None:
                        item_type = WorkItemTypeModel(
                            name=j.name,
                            youtrack_id=j.id,
                            project_id=project.id,
                        )
                        session.add(item_type)
                        session.flush()
                stmt = (
                    select(ProjectMember)
                    .where(ProjectMember.employee_id == employee.id)
                    .where(ProjectMember.project_id == project.id)
                )
                project_member = session.scalar(stmt)
                if project_member is None:
                    project_member = ProjectMember(
                        employee_id=employee.id,
                        project_id=project.id,
                        sync_enabled=True,
                        comment="Automatically inserted",
                    )
                    session.add(project_member)
                    session.flush()
            session.commit()

        # retrieve and process clockify time entries

        entries = clockify_client.time_entries.get_time_entries(
            workspace_id=employee.clockify_workspace_id,
            user_id=employee.clockify_user_id,
            params={
                "page_size": config.sync_window_size,
                "start": config.ignore_entries_before.isoformat(),
                "in-progress": False,
            },
        )
        sorted_entries = sorted(
            entries,
            key=lambda x: datetime.fromisoformat(
                x["timeInterval"]["start"],
            ),
            reverse=True,
        )
        assert sorted_entries == entries
        for entry in entries:
            raw_time_interval = entry["timeInterval"]
            start = datetime.fromisoformat(raw_time_interval["start"])
            end = datetime.fromisoformat(raw_time_interval["end"])

            if (end
                    + timedelta(seconds=config.sync_tolerance_delay_seconds)
                    >= datetime.now(tz=self.config.tz)):
                continue  # skip sync tolerant by delay time entries

            if start <= config.ignore_entries_before:
                continue  # skip sync tolerant by threshold time entries

            description = entry["description"].strip()

            match = re.match(r"(\S+)-(\d+)\s*(.*)\s*", description)
            if match is None:
                logger.debug(f"Cannot match issue of entry {entry['id']} "
                             f"by description")
                continue

            youtrack_project_short_name = match.group(1)
            youtrack_project_issue_number = match.group(2)
            issue_id = (f"{youtrack_project_short_name}"
                        f"-{youtrack_project_issue_number}")
            time_entry_description = match.group(3)

            with container.get(Session) as session:
                stmt = (
                    select(WorkItem)
                    .where(WorkItem.clockify_time_entry_id == entry["id"])
                )
                existing_work_item: WorkItem | None = session.scalar(stmt)
                if existing_work_item is not None:
                    continue  # work item already created

            current_datetime_str = datetime.now(tz=config.tz).strftime(
                "%Y-%m-%d %H:%M:%S (%z)")

            with container.get(Session) as session:
                stmt = (
                    select(Project)
                    .where(Project.short_name == youtrack_project_short_name)
                )
                project = session.scalar(stmt)

                stmt = (
                    select(ProjectMember)
                    .where(ProjectMember.employee_id == employee.id)
                    .where(ProjectMember.project_id == project.id)
                )
                member: ProjectMember = session.scalar(stmt)
                work_item_type = member.default_work_item_type
                work_item_type = (
                        work_item_type
                        or project.default_work_item_type
                )

            # note: you cannot create zero minute work item in youtrack.
            normalized_minutes = max(
                round((end - start).total_seconds() / 60),
                1,
            )
            work_item = IssueWorkItem(
                date=start,
                duration=DurationValue(
                    minutes=normalized_minutes
                ),
                text=(f"**{time_entry_description}**\n\n"
                      f"Inserted from clockify at {current_datetime_str}"),
                work_item_type=
                work_item_type and WorkItemType(
                    id=work_item_type.youtrack_id,
                ),
            )
            try:
                r = youtrack_client.create_issue_work_item(
                    issue_id=issue_id,
                    issue_work_item=work_item,
                )
            except YouTrackException as e:
                logger.warning(
                    f"Can't insert issue work item {work_item} to issue "
                    f"`{issue_id}`. Err args: {e.args}"
                )
                continue
            logger.info(
                f"Time entry with id `{entry["id"]}` upserted to "
                f"issue `{issue_id}` as work item with id `{r.id}`"
            )
            with container.get(Session) as session:
                entity = WorkItem(
                    youtrack_id=r.id,
                    clockify_time_entry_id=entry["id"],
                    project_member_id=member.id,
                    duration=end-start,
                    text=r.text,
                    work_item_type=work_item_type,
                )
                session.add(entity)
                session.flush()
                session.commit()

    def _iteration(self, container: Container):
        with container.get(Session) as session:
            employees: Iterable[Employee] = session.scalars(
                select(Employee)
                .where(Employee.deleted_at.is_(None)),
            )
            for i in employees:
                while True:
                    try:
                        self._sync_employee(container, i)
                    except YouTrackUnauthorized:
                        logger.error(
                            f"Youtrack client unauthorized for"
                            f" employee id={i.id}"
                            f" full_name={i.full_name}"
                        )
                        break
                    except Exception as e:
                        logger.exception(
                            "Unexpected error when syncing"
                             f" employee id={i.id}"
                             f" full_name={i.full_name}",
                             exc_info=e,
                        )
                        break
                    except TimeoutError as e:
                        logger.warning(
                            f"Retry syncing"
                            f" employee id={i.id}"
                            f" full_name={i.full_name}"
                            f" due timeout error: `{e}`."
                        )
                        break

    def run(self):
        config = self.config

        while True:
            logger.debug("Start next sync iteration")
            starts_at = datetime.now()
            with self.container() as request_container:
                self._iteration(request_container)
            ends_at = datetime.now()

            total_seconds = (ends_at-starts_at).total_seconds()
            delay = config.sync_throttling_delay_seconds - total_seconds

            if delay > 0:
                logger.debug(f"Enter {delay}s delay")
                time.sleep(delay)
                logger.debug(f"Exit delay")
            else:
                logger.warning(f"Continue without delay (delay={delay}")
