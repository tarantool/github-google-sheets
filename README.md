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
google_sheet_id=<the ID of your google sheet>
```

You can get a personal API token for GitHub here: https://github.com/settings/tokens .
Google sheet ID can be copied from the URL in your browser.

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

## Export

To view your issues locally, you can export them to a `tsv` file like this:

```sh
./sync.py export tsv myissues.tsv
```

If you want to view issues with Microsoft Excel, do this:

```sh
./sync.py export xlsx myissues.xlsx
```
