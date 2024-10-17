import logging
import os
import re
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from time import sleep
from logging import getLogger, basicConfig

import pytz
from clockify_api_client.client import ClockifyAPIClient
import youtrack_sdk
from youtrack_sdk.entities import IssueWorkItem, DurationValue, WorkItemType
from pydantic_settings import BaseSettings
from fastapi import FastAPI
from dishka import make_container


class CYSettings(BaseSettings):
    tz: str
    sync_window_size: int
    sync_delay_seconds: int


tz = pytz.timezone(os.getenv("APPLICATION__TZ"))


logger = getLogger(__name__)


def upsert_clockify_to_youtrack(
        clockify_client: ClockifyAPIClient,
        youtrack_client: youtrack_sdk.Client,
):
    entries = clockify_client.time_entries.get_time_entries(
        workspace_id=os.getenv("CLOCKIFY__WORKSPACE_ID"),
        user_id=os.getenv("CLOCKIFY__USER_ID"),
    )
    threshold = datetime.fromisoformat(os.getenv("APPLICATION__IGNORE_ENTRIES_BEFORE"))
    sync_window_size = int(os.getenv("APPLICATION__SYNC_WINDOW_SIZE"))
    for entry in entries[:sync_window_size]:
        sleep(1)
        raw_time_interval = entry["timeInterval"]

        if raw_time_interval["end"] is None:
            continue  # skip active time entries
        
        start = datetime.fromisoformat(raw_time_interval["start"])
        end = datetime.fromisoformat(raw_time_interval["end"])
        
        sync_delay = int(os.getenv("APPLICATION__SYNC_DELAY"))
        if end + timedelta(seconds=sync_delay) >= datetime.now(tz=tz):
            continue

        if start <= threshold:
            continue

        description = entry["description"].strip()

        match = re.match(r"(\S+-\d+)\s*(.*)\s*", description)
        if match is None:
            logger.debug(f"Cannot match issue by text {description}")
            continue

        issue_id = match.group(1)
        time_entry_description = match.group(2)

        existing_items = youtrack_client.get_issue_work_items(issue_id=issue_id)
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

        current_datetime_str = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S (%z)")
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
                    id=os.getenv("YOUTRACK__WORK_ITEM_TYPE_ID"),
                )
            )
        )
        logger.info(
            f"Time entry with id `{entry["id"]}` upserted to "
            f"issue `{issue_id}` as work item with id `{r.id}`"
        )


def main():
    handler = RotatingFileHandler(
        filename="/logs/clockify-x-youtrack.log",
        maxBytes=1000*1000,
        backupCount=10,
    )
    basicConfig(handlers=[handler], level=logging.DEBUG)

    container = make_container()
    app = FastAPI()
    register_admin(app)

    clockify_client = (
        ClockifyAPIClient()
        .build(
            api_key=os.getenv("CLOCKIFY__API_KEY"),
            api_url="api.clockify.me/v1",
        )
    )
    youtrack_client = youtrack_sdk.client.Client(
        base_url=os.getenv("YOUTRACK__BASE_URL"),
        token=os.getenv("YOUTRACK__TOKEN"),
    )

    while True:
        upsert_clockify_to_youtrack(
            clockify_client=clockify_client,
            youtrack_client=youtrack_client,
        )
        sleep(int(os.getenv("APPLICATION__TIMEOUT")))


if __name__ == '__main__':
    main()
