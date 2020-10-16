#!/usr/bin/env python3


from github import Github
from github.GithubException import RateLimitExceededException
import argparse
import pickle
import os.path
import datetime
import json
import time
import configparser

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SHEET_ID = ''

def github_connect(token):
    with open('token.txt') as f:
        token = f.read().strip()

    gh = Github(token)
    return gh

def google_connect():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'sheets-credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()

    return sheet


def get_last_updated(issues):
    last = ""
    for num, issue in issues.items():
        if issue['updated_at'] > last:
            last = issue['updated_at']

    if last == "":
        last = "1969-12-31T21:00:00Z"
    return datetime.datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ")

def read_issues():
    issues = {}
    if os.path.exists('issues.json'):
        with open('issues.json', encoding='utf-8') as f:
            issues = json.loads(f.read())
    return issues

def write_issues(issues):
    with open('issues.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(issues, indent=4,ensure_ascii=False))

def try_sync_issues(gh, orgname):
    issues = read_issues()

    if orgname not in issues:
        issues[orgname] = {}
    org_issues = issues[orgname]

    org = gh.get_organization(orgname)
    for repo in org.get_repos():
        if repo.name not in org_issues:
            org_issues[repo.name] = {}
        repo_issues = org_issues[repo.name]

        last_updated = get_last_updated(repo_issues)

        c = 1
        for issue in repo.get_issues(state='all', since=last_updated, sort='updated', direction='asc'):
            print("%s: %s/%s %d %s" % (issue.updated_at, orgname, repo.name, int(issue.number), issue.title))

            milestone = None
            if issue.milestone is not None:
                due_on = None
                if issue.milestone.due_on is not None:
                    due_on = issue.milestone.due_on.isoformat() + 'Z'

                milestone = {
                    'number': issue.milestone.number,
                    'tile': issue.milestone.title,
                    'created_at': issue.milestone.created_at.isoformat() + 'Z',
                    'due_on': due_on
                }

            closed_at = None
            if issue.closed_at is not None:
                closed_at = issue.closed_at.isoformat() + 'Z'

            repo_issues[str(issue.number)] = {
                'title': issue.title,
                'updated_at': issue.updated_at.isoformat() + 'Z',
                'created_at': issue.created_at.isoformat() + 'Z',
                'closed_at': closed_at,
                'state': issue.state,
                'is_pr': issue.pull_request is not None,
                'labels': [l.name for l in issue.labels],
                'milestone': milestone
            }
            c = c +1
            if c % 100 == 99:
                write_issues(issues)

    write_issues(issues)

    pass

def sync_issues(token, orgname):
    gh = github_connect(token)

    while True:
        try:
            try_sync_issues(gh, orgname)
            print("Synchronization finished successfully")
            break
        except RateLimitExceededException as e:
            print("API request limit reached. Sleeping for 10 minutes.")
            time.sleep(3600/6)

#for repo in org.get_repos():
#    print(repo.full_name)
#    break

#for evt in org.get_events():
#    print(evt)
#    break



#for repo in g.get_user().get_repos():
#    print(repo.full_name)


#sheet = google_connect()


#result = sheet.values().get(spreadsheetId=SHEET_ID,
#                            range='A1:A6').execute()

#values = result.get('values', [])

#if not values:
#    print('No data found.')
#else:
#    print('Columns:')
#    for row in values:
#        print('%s' % (row[0],))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    subparsers = parser.add_subparsers(title="commands", dest="command")
    subparsers.required = True

    sync = subparsers.add_parser("sync")

    args = parser.parse_args()

    config = configparser.ConfigParser()

    filename = 'github-google-sheets.ini'

    if os.path.exists(filename):
        config.read(filename)
    elif os.path.exists(os.path.expanduser("~/." + filename)):
        config.read(os.path.expanduser("~/." + filename))
    else:
        raise RuntimeError('Configuration file not found.')

    token = config['default']['github_token']
    orgname = config['default']['github_org']

    sync_issues(token, orgname)
