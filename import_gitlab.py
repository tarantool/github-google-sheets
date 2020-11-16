#!/usr/bin/env python3

import gitlab
import os
import configparser
import re
import fnmatch
import pprint
import json
import datetime


def read_issues():
    issues = {}
    if os.path.exists('issues.json'):
        with open('issues.json', encoding='utf-8') as f:
            issues = json.loads(f.read())

    return issues


def write_issues(issues):
    with open('issues.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(issues, indent=4,ensure_ascii=False))

def convert_time(time):
    if time is None:
        return None

    tm = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
    tm = tm.replace(microsecond=0)

    return tm.isoformat() + 'Z'


def get_issue_events(issue):
    result = []

    events = issue.resourcemilestoneevents.list()

    for event in events:
        if event.action not in ['add', 'remove']:
            continue

        title = event.milestone['title']
        label = None
        event_name = 'milestoned'
        if event.action == 'remove':
            event_name = 'demilestoned'

        evt = {
            'created_at': convert_time(event.created_at),
            'event': event_name,
            'milestone': title,
            'label': label
        }

        result.append(evt)

    return result


def get_last_updated(issues):
    last = ""
    for num, issue in issues.items():
        if issue['updated_at'] > last:
            last = issue['updated_at']

    if last == "":
        last = "1969-12-31T21:00:00Z"
    return last



def try_sync_issues(gl, orgname, reponame, since, whitelist):
    root = gl.groups.get(orgname)

    if reponame is not None:
        reponame = orgname + '/' + reponame

    issues = read_issues()

    if orgname not in issues:
        issues[orgname] = {}
    org_issues = issues[orgname]

    c = 1
    for project in root.projects.list(include_subgroups=True, all=True, lazy=True):
        if whitelist is not None:
            found = False
            for entry in whitelist:
                if fnmatch.fnmatch(project.path_with_namespace, entry):
                    found = True
            if not found:
                continue

        if reponame is not None and reponame != project.path_with_namespace:
            continue

        repo_name = re.search(r"^%s/(.*)$" % orgname, project.path_with_namespace).group(1)

        print('scanning project: ', project.path_with_namespace)

        if repo_name not in org_issues:
            org_issues[repo_name] = {}

        repo_issues = org_issues[repo_name]

        project = gl.projects.get(project.id)

        last_updated = get_last_updated(repo_issues)
        if since is not None:
            last_updated = since


        for found_issue in project.issues.list(all=True, order_by='created_at', sort='asc', updated_after=last_updated):
            issue = project.issues.get(found_issue.iid)
            print('- ', issue.title)

            milestone = None
            milestone_number = None
            if issue.milestone is not None:
                milestone = issue.milestone['title']
                milestone_number = issue.milestone['iid']

            events = get_issue_events(issue)

            closed_at = None
            if issue.closed_at is not None:
                closed_at = issue.closed_at

            weight = 1
            try:
                weight = issue.weight
            except:
                pass

            repo_issues[str(issue.iid)] = {
                'source': 'gitlab.com',
                'title': issue.title,
                'updated_at': convert_time(issue.updated_at),
                'created_at': convert_time(issue.created_at),
                'closed_at': convert_time(closed_at),
                'state': issue.state,
                'is_pr': False,
                'labels': issue.labels,
                'milestone': milestone,
                'milestone_number': milestone_number,
                'events': events,
                'weight': weight
            }
            c = c +1
            if c % 100 == 99:
               write_issues(issues)

    write_issues(issues)


    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(org_issues)


def do_import(token, orgname, reponame=None, since=None, whitelist=None):
    gl = gitlab.Gitlab('https://gitlab.com', private_token=token)

    try_sync_issues(gl, orgname, reponame, since, whitelist)
    print("Synchronization finished successfully")

    pass


if __name__ == '__main__':
    config = configparser.ConfigParser()

    filename = 'github-google-sheets.ini'

    if os.path.exists(filename):
        config.read(filename)
    elif os.path.exists(os.path.expanduser("~/." + filename)):
        config.read(os.path.expanduser("~/." + filename))
    else:
        raise RuntimeError('Configuration file not found.')

    gitlab_token = None
    if 'gitlab_token' in config['default']:
        gitlab_token = config['default']['gitlab_token']
    gitlab_whitelist = config['default'].get('gitlab_whitelist', None)

    if gitlab_whitelist is not None:
        gitlab_whitelist = gitlab_whitelist.split(',')
    gitlab_org = config['default']['gitlab_org']


    do_import(gitlab_token, gitlab_org, whitelist=gitlab_whitelist)
