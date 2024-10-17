import re
import time
from datetime import datetime, timedelta
from logging import getLogger
from typing import Iterable

import pytz
import youtrack_sdk
from dishka import Container
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from clockify_api_client.client import ClockifyAPIClient
from youtrack_sdk.entities import IssueWorkItem, DurationValue, WorkItemType

from cloyt.domain.models import ProjectMember


logger = getLogger(__name__)


class CloytSynchronizer:
    def __init__(
            self,
            container: Container,
            sync_tolerance_delay_seconds: int,
            throttling_delay_seconds: int,
            window_size: int,
            ignore_entries_before: datetime,
            youtrack_base_url: str,
            tz: pytz.BaseTzInfo,
    ):
        self.container = container
        self.youtrack_base_url = youtrack_base_url
        self.sync_tolerance_delay_seconds = sync_tolerance_delay_seconds
        self.throttling_delay_seconds = throttling_delay_seconds
        self.window_size = window_size
        self.ignore_entries_before = ignore_entries_before
        self.tz = tz

    def _sync_project_member(self, project_member: ProjectMember):
        clockify_client = (
            ClockifyAPIClient()
            .build(
                api_key=project_member.employee.clockify_token,
                api_url="api.clockify.me/v1",
            )
        )
        youtrack_client = youtrack_sdk.client.Client(
            base_url=self.youtrack_base_url,
            token=project_member.employee.youtrack_token,
        )

        entries = clockify_client.time_entries.get_time_entries(
            workspace_id=project_member.employee.clockify_workspace_id,
            user_id=project_member.employee.clockify_user_id,
        )
        for entry in entries[:self.window_size]:
            raw_time_interval = entry["timeInterval"]

            if raw_time_interval["end"] is None:
                continue  # skip active time entries

            start = datetime.fromisoformat(raw_time_interval["start"])
            end = datetime.fromisoformat(raw_time_interval["end"])

            if (end
                    + timedelta(seconds=self.sync_tolerance_delay_seconds)
                    >= datetime.now(tz=self.tz)):
                continue

            if start <= self.ignore_entries_before:
                continue

            description = entry["description"].strip()

            match = re.match(r"(\S+-\d+)\s*(.*)\s*", description)
            if match is None:
                logger.debug(f"Cannot match issue by text {description}")
                continue

            issue_id = match.group(1)
            time_entry_description = match.group(2)

            existing_items = youtrack_client.get_issue_work_items(
                issue_id=issue_id)
            all_entry_ids = set()
            for i in existing_items:
                match = re.search(r".*Time entry id: `([a-f0-9]+)`.*", i.text)
                if match is None:
                    logger.debug(
                        f"Cannot match time entry of "
                        f"issue work item's text `{i.text}`"
                    )
                    continue
                entry_id = match.group(1)
                all_entry_ids.add(entry_id)

            if entry["id"] in all_entry_ids:
                continue

            current_datetime_str = datetime.now(tz=self.tz).strftime(
                "%Y-%m-%d %H:%M:%S (%z)")
            r = youtrack_client.create_issue_work_item(
                issue_id=issue_id,
                issue_work_item=IssueWorkItem(
                    date=start,
                    duration=DurationValue(
                        minutes=round((end - start).total_seconds() / 60),
                    ),
                    text=(
                        f"**{time_entry_description}**\n\n"
                        f"Inserted from clockify on {current_datetime_str}"
                        f"\nDO NOT EDIT CONTENT BELOW MANUALLY"
                        f"\nTime entry id: `{entry["id"]}`"
                    ),
                    work_item_type=WorkItemType(
                        id=project_member,
                    )
                )
            )
            logger.info(
                f"Time entry with id `{entry["id"]}` upserted to "
                f"issue `{issue_id}` as work item with id `{r.id}`"
            )

    def _iteration(self, container: Container):
        with container.get(Session) as session:
            project_members: Iterable[ProjectMember] = session.scalars(
                select(ProjectMember),
                execution_options=(joinedload(
                    ProjectMember.project,
                    ProjectMember.employee,
                )),
            )
            for i in project_members:
                self._sync_project_member(i)

    def run(self):
        while True:
            starts_at = datetime.now()
            with self.container() as request_container:
                self._iteration(request_container)
            ends_at = datetime.now()

            total_seconds = (ends_at-starts_at).total_seconds()
            delay = self.throttling_delay_seconds - total_seconds

            if delay <= 1:
                logger.warning(f"To small delay ({delay:.4f}s)")

            time.sleep(delay)
