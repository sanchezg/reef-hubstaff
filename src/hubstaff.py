import argparse
import logging
import os
import sys
from datetime import date, datetime
from logging import getLogger

import requests
from dotenv import load_dotenv

from src.models import Activity, Organization, Project
from src.repositories import ActivityRepo, ProjectRepo, UserRepo

load_dotenv()
logger = getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class HubStaffClientException(Exception):
    pass


class HubStaffClient:
    def __init__(self, organization_id=None, base_url=None, debug=False) -> None:
        if organization_id:
            self._organization_id = organization_id

        self.session = requests.Session()  # TODO: Move to a RequestsClient class
        self._base_url = os.environ.get("HUBSTAFF_BASE_URL", base_url)
        self._app_token = os.environ.get("HUBSTAFF_APP_TOKEN")
        self._debug = debug or os.environ.get("HUBSTAFF_DEBUG")
        self._set_session_token()
        if self._debug:
            logger.debug(f"Running Hubstaff client with org={self.organization_id}, app_token={self._app_token}")

    @property
    def organization_id(self):
        return self._organization_id or None

    @property
    def base_url(self):
        return self._base_url
    
    @property
    def credentials(self):
        return {
            "email": os.environ.get("HUBSTAFF_EMAIL"),
            "password": os.environ.get("HUBSTAFF_PASSWORD")
        }

    def organizations(self) -> Organization:
        raise NotImplementedError()

    def projects(self, project_id=None) -> Project:
        raise NotImplementedError()

    def _set_session_token(self):
        self.session.headers.update({"AppToken": self._app_token})

    def _authenticate(self):
        response = self.session.post(
            f"{self.base_url}/v339/members/login",
            data=self.credentials
        )  # TODO: Move to a RequestsClient class
        if self._debug:
            logger.debug(f"Trying to authenticate: {response.status_code}")
        if response.status_code == 200 and "auth_token" in response.json():
            self.session.headers.update({
                "AuthToken": response.json()["auth_token"]
            })

    def _get(self, path, *args, **kwargs):  # TODO: Move to a RequestsClient class
        url = f"{self.base_url}/{path}"
        if "AuthToken" not in self.session.headers:  # TODO: detect if auth_token expired
            self._authenticate()
        return self.session.get(url, **kwargs)

    def daily_activities(self, project_id=None, start=None, stop=None) -> list[Activity]:
        if start is None and stop is None:
            _today = datetime.today().date()
            start = _today.isoformat()
            stop = _today.isoformat()

        self.session.headers.update(
            {"DateStart": start}
        )

        response = self._get(
            f"v339/company/{self.organization_id}/operations/by_day", params={"date[stop]": stop}
        )
        if self._debug:
            logger.debug(f"Getting daily activities: start={start}, stop={stop}, sc={response.status_code}, content={response.content}")

        activities = []
        if response.status_code == 200:
            activities = response.json().get("daily_activities", [])

        if self._debug:
            logger.debug(f"Got activities={activities}")

        return [
            Activity(
                id=activity["id"],
                date=date.fromisoformat(activity["date"]),
                user_id=activity["user_id"],
                project_id=activity["project_id"],
                task_id=activity["task_id"],
                keyboard=activity["keyboard"],
                mouse=activity["mouse"],
                overall=activity["overall"],
                tracked=activity["tracked"],
                input_tracked=activity["input_tracked"],
                manual=activity["manual"],
                idle=activity["idle"],
                resumed=activity["resumed"],
                billable=activity["billable"],
                created_at=datetime.fromisoformat(activity["created_at"]),  # only works in py3.11+
                updated_at=datetime.fromisoformat(activity["updated_at"]),  # only works in py3.11+
            )
            for activity in activities
        ]


def main(organization_id, debug=False):
    hc = HubStaffClient(organization_id=organization_id)
    activities = hc.daily_activities()

    arepo = ActivityRepo()
    arepo.insert(activities)


def install(debug=False):
    logger.debug("Running install")
    arepo = ActivityRepo()
    prepo = ProjectRepo()
    urepo = UserRepo()

    arepo.create_table()
    prepo.create_table()
    urepo.create_table()

    logger.debug("Install done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gets daily activities for a certain organization")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-o",
        "--organization",
        dest="organization_id",
        help="Organization id as specified in Hubstaff API"
    )
    group.add_argument(
        "-i",
        "--install",
        action="store_true",
        help="Run once to create the DB file and tables"
    )

    args = parser.parse_args()
    if args.install:
        install(debug=args.debug)
    else:
        main(args.organization_id, debug=args.debug)
