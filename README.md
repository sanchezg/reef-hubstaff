# reef-hubstaff
Reef.pl code assessment 

This app fetches all daily activities (for the last day if no dates are provided) from Hubstaff API and report them as a pivot table in HTML in standard output.

## Installation

Once the files are extracted, install a Python3.11+ version, and install all necessary requirements with poetry:

1. `$ pip install poetry`
2. `$ poetry install --no-root`

The following environment variables must be defined, otherwise add a `.env` file with them:

```
HUBSTAFF_APP_TOKEN = "YOURTOKEN"
HUBSTAFF_BASE_URL = "https://mutator.reef.pl"

HUBSTAFF_EMAIL="your_user@email.com"
HUBSTAFF_PASSWORD="Y0urP4$sW0Rd"
DB_FILENAME="hubstaff.db"
```

Run the app in install mode to create the local DB:

- `$ python src/hubstaff.py -i` 

## Execution

The most simple way is to run the app for the previous day:

`python src/hubstaff.py -o 123456`

This will run the API fetcher (daily activities and projects), insert them in the local DB and then build a report for the previous day.

Running in this mode daily (with `cron`) will retrieve the activities for every day:

```
$ crontab -e

0 0 * * * python src/hubstaff.py -o 123456 >> /home/your_user/husbtaff.log
```

Refer to below "Options" section for more information about options and execution modes.

## Options

This app runs as a standalone script and has the following options:
- `-o | --organization`: Organization ID. This must be obtained from the Hubstaff API. Is mandatory unless `-i | --install` is provided.
- `-i | --install`: Must be run once to create the local DB.
- `-s | --start`: Start date for the fetcher and report. Useful if you want to populate the DB with data from past.
- `-e | --end`: End date for the fetcher and report. Useful if you want to populate the DB with data from past.
- `-r | --report`: Runs the script only in report mode. When executed as this, will log to stdout the report for the specified dates or the previous days (if no dates provided with `-s` and `-e`).

## Examples

1. Runs the app in "fetcher and report" mode for the specified dates:

`$ python src/hubstaff.py -o 123456 -s 2024-02-06 -e 2024-02-12`

2. Runs the app in "only report" mode (does not fetch the API) and builds a report for the specified dates. In this case the DB must have been populated previously with that data:

`$ python src/hubstaff.py -o 123456 -s 2024-02-06 -e 2024-02-12 -r`

## Troubleshooting

- Some combinations of environment/version of pandas can output a warning when the pivot table is been made, if you want to ignore it add a DeprecationWarning ignore to python:

`$ python -W ignore::DeprecationWarning src/hubstaff.py ...`

- If you get a `ModuleNotFoundError` when running the script, ensure that the current path is in the python lookup paths:

`$ PYTHONPATH=. python -W src/hubstaff.py ...`
