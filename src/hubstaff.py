import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
import logging
from logging import getLogger

import requests
from dotenv import load_dotenv


load_dotenv()
logger = getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


@dataclass
class Organization:
    id: int


@dataclass
class Project:
    id: int


@dataclass
class Activity:
    id: int
    date: str
    user_id: int
    project_id: int
    task_id: int
    keyboard: int
    mouse: int
    overall: int
    tracked: int
    input_tracked: int
    manual: int
    idle: int
    resumed: int
    billable: int
    created_at: datetime
    updated_at: datetime


class HubStaffClientException(Exception):
    pass


class HubStaffClient:
    def __init__(self, organization_id=None, base_url=None) -> None:
        if organization_id:
            self._organization_id = organization_id

        self.session = requests.Session()  # TODO: Move to a RequestsClient class
        self._base_url = os.environ.get("HUBSTAFF_BASE_URL", base_url)
        self._app_token = os.environ.get("HUBSTAFF_APP_TOKEN")
        self._debug = os.environ.get("HUBSTAFF_DEBUG")  # TODO: move to logging config

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

        result = []
        for _act in activities:
            result.append(Activity(**_act))
        if self._debug:
            logger.debug(f"Got activities={activities}")
        return result


def main(organization_id):
    hc = HubStaffClient(organization_id=organization_id)
    activities = hc.daily_activities()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gets daily activities for a certain organization")
    parser.add_argument(
        "-o",
        "--organization",
        dest="organization_id",
        required=True,
        help="Organization id as specified in Hubstaff API"
    )

    args = parser.parse_args()
    main(args.organization_id)
