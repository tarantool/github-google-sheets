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
import csv
import xlsxwriter

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


def get_issue_events(issue):
    result = []

    for event in issue.get_events():
        if event.event not in ['milestoned', 'demilestoned', 'labeled', 'unlabeled']:
            continue

        #print(event.event)
        #print(event.milestone, event.label)

        milestone_title = None

        if event.milestone is not None:
            milestone_title = event.milestone.title

        label_name = None
        if event.label is not None:
            label_name = event.label.name


        evt = {
            'created_at': event.created_at.isoformat() + 'Z',
            'event': event.event,
            'milestone': milestone_title,
            'label': label_name
        }

        #print(evt)
        result.append(evt)

    return result


def try_sync_issues(gh, orgname, reponame=None, since=None):
    issues = read_issues()

    if orgname not in issues:
        issues[orgname] = {}
    org_issues = issues[orgname]

    org = gh.get_organization(orgname)
    for repo in org.get_repos():
        if reponame is not None and reponame != repo.name:
            continue

        if repo.name not in org_issues:
            org_issues[repo.name] = {}
        repo_issues = org_issues[repo.name]

        last_updated = get_last_updated(repo_issues)
        if since is not None:
            last_updated = since

        c = 1
        for issue in repo.get_issues(state='all', since=last_updated, sort='updated', direction='asc'):
            print("%s: %s/%s %d %s" % (issue.updated_at, orgname, repo.name, int(issue.number), issue.title))
            events = get_issue_events(issue)

            milestone = None
            milestone_number = None
            if issue.milestone is not None:
                milestone = issue.milestone.title
                milestone_number = issue.milestone.number

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
                'milestone': milestone,
                'milestone_number': milestone_number,
                'events': events
            }
            c = c +1
            if c % 100 == 99:
                write_issues(issues)

    write_issues(issues)

    return last_updated


def sync_issues(token, orgname, reponame=None, since=None):
    gh = github_connect(token)

    while True:
        try:
            try_sync_issues(gh, orgname, reponame, since)
            print("Synchronization finished successfully")
            break
        except RateLimitExceededException as e:
            print("API request limit reached. Sleeping for 10 minutes.")
            time.sleep(3600/6)


def export_issues_tsv(filename, orgname):
    issues = read_issues()

    with open(filename, 'w', newline='', encoding='utf-8') as fd:
        writer = csv.writer(fd, delimiter="\t",
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['path', 'orgname', 'reponame', 'id', 'title', 'state', 'created_at', 'updated_at', 'closed_at'])
        if orgname in issues:
            for reponame, repo_issues in issues[orgname].items():
                for number, issue in repo_issues.items():
                    if issue['is_pr']:
                        continue

                    try:
                        writer.writerow(
                            [
                                "%s/%s/issues/%s" % (orgname, reponame, number),
                                orgname,
                                reponame,
                                number,
                                issue['title'].strip(),
                                issue['state'],
                                issue['created_at'],
                                issue['updated_at'],
                                issue['closed_at']
                            ])
                    except:
                        print(issue)


def export_issues_xls(filename, orgname):
    issues = read_issues()

    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()

    worksheet.write_row(
        'A1',
        ['path', 'orgname', 'reponame', 'id', 'title', 'state', 'created_at', 'updated_at', 'closed_at'])

    date_format = workbook.add_format()
    date_format.set_num_format('d mmmm yyyy')

    wrap_format = workbook.add_format({'text_wrap': 1})

    data = []

    worksheet.set_column('A:A', 40)
    worksheet.set_column('B:C', 12)

    worksheet.set_column('E:E', 100)
    worksheet.set_column('G:I', 17)

    if orgname in issues:
        line = 2
        for reponame, repo_issues in issues[orgname].items():
            for number, issue in repo_issues.items():
                if issue['is_pr']:
                    continue

                try:
                    closed_at = None

                    if issue['closed_at'] is not None:
                        closed_at = datetime.datetime.strptime(issue['closed_at'], "%Y-%m-%dT%H:%M:%SZ")
                    row = [
                            "%s/%s/issues/%s" % (orgname, reponame, number),
                            orgname,
                            reponame,
                            int(number),
                            issue['title'].strip(),
                            issue['state'],
                            datetime.datetime.strptime(issue['created_at'], "%Y-%m-%dT%H:%M:%SZ"),
                            datetime.datetime.strptime(issue['updated_at'], "%Y-%m-%dT%H:%M:%SZ"),
                            closed_at
                        ]

                    data.append(row)

                    #worksheet.write_row("A%d"%line, row)
                    #line = line+1

                except:
                    print(issue)
    worksheet.add_table(
        'A1:I%d'%len(data),
        {'data': data,
         'columns':
         [{'header': 'path'},
          {'header': 'orgname'},
          {'header': 'reponame'},
          {'header': 'id'},
          {'header': 'title'},
          {'header': 'state'},
          {'header': 'created_at', 'format': date_format},
          {'header': 'updated_at', 'format': date_format},
          {'header': 'closed_at', 'format': date_format}]})

    worksheet.freeze_panes(1, 0)
    workbook.close()



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
    sync.add_argument('reponame', default=None, nargs='?')
    sync.add_argument('--full', action='store_true')

    export = subparsers.add_parser("export")

    export_subparsers = export.add_subparsers(title="export commands", dest="export_command")

    tsv = export_subparsers.add_parser("tsv")
    tsv.add_argument('filename')

    xlsx = export_subparsers.add_parser("xlsx")
    xlsx.add_argument('filename')


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
    sheet_id = config['default']['google_sheet_id']

    if args.command == 'sync':
        since = None
        if args.full:
            since = datetime.datetime.strptime("1969-12-31T21:00:00Z", "%Y-%m-%dT%H:%M:%SZ")

        sync_issues(token, orgname, args.reponame, since)
    elif args.command == 'export':
        if args.export_command == 'tsv':
            export_issues_tsv(args.filename, orgname)
        elif args.export_command == 'xlsx':
            export_issues_xls(args.filename, orgname)
