import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from logging import getLogger

import pandas as pd
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

    def projects(self) -> list[Project]:
        response = self._get(f"v339/company/{self.organization_id}/projects")
        if self._debug:
            logger.debug(f"Getting projects: sc={response.status_code}, content={response.content}")

        projects = []
        if response.status_code == 200:
            projects = response.json().get("projects", [])

        if self._debug:
            logger.debug(f"Got projects={projects}")

        return [
            Project(
                id=project["id"],
                name=project["name"],
                status=project["status"],
                billable=project["billable"],
                created_at=datetime.fromisoformat(project["created_at"]),  # only works in py3.11+
                updated_at=datetime.fromisoformat(project["updated_at"]),  # only works in py3.11+
            )
            for project in projects
        ]


def render_output(activities_repo: ActivityRepo, start=None, stop=None):
    """
    Present the aggregated information in an HTML table.
    In the columns, there should be the employees, in the rows, there should be the projects, and in the cells in the middle, there should be the amount of time that a given employee spent working on a given project
    """
    raw_results = activities_repo.get(raw_data=True)  # TODO: implement filters
    df = pd.DataFrame.from_records(data=raw_results, columns=Activity.__annotations__.keys())

    if start == stop and start is not None:
        df = df[df["date"] == start]
    elif start is not None and stop is not None:
        df = df[(df["date"] >= start) & (df["date"] <= stop)]
    pivot = pd.pivot_table(df, index=["user_id"], columns=["project_id"], values="tracked", aggfunc="sum").fillna(0)

    to_hour = lambda x: str(timedelta(seconds=x))
    for col in pivot.columns:
        pivot[col] = pivot[col].apply(to_hour) # improve readability
    html = pivot.to_html()
    print(html)


def main(organization_id, start=None, stop=None, report=None, debug=False):
    arepo = ActivityRepo()
    prepo = ProjectRepo()
    if not report:
        hc = HubStaffClient(organization_id=organization_id)
        activities = hc.daily_activities(start=start, stop=stop)
        arepo.insert(activities)
        projects = hc.projects()
        prepo.insert(projects)

    render_output(arepo, start=None, stop=None)


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

    parser.add_argument(
        "-s",
        "--start",
        help="Start date for the activities"
    )
    parser.add_argument(
        "-e",
        "--end",
        help="End date for the activities"
    )

    parser.add_argument(
        "-r",
        "--report",
        action="store_true",
        help="Only generate the report for the given dates. If no dates, then report for only last day."
    )

    args = parser.parse_args()
    if args.install:
        install(debug=args.debug)
    else:
        main(args.organization_id, start=args.start, stop=args.end, report=args.report, debug=args.debug)
