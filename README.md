# Synchronize GitHub with Google Sheets

This Python script allows you to synchronize the issues of your GitHub
organization to a Google Sheet. You can use it then to make queries or
draw diagrams or burndown charts.

Currently the script can do complete synchronization of GitHub issues,
but can't yet push them to a spreadsheet. Stay tuned.

## Usage

Create a file called `github-google-sheets.ini` and fill it as follows:

```ini
[default]
github_token=<your API token>
github_org=<your organization name>
```

You can get a personal API token for GitHub here: https://github.com/settings/tokens .

How to synchronise:

```sh
./sync.py sync
```

There are request limits, and you can only do 5000 requests per
hour. If you cross that limit, the script will pause for 10 minutes
and try to continue fetching.

The synchronization is also incremental, so if you re-start the
script, it will resume where it finished last time. You can run it
periodically to fetch new issues.
