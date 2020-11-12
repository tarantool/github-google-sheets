#!/usr/bin/env python3

from github import Github
from github.GithubException import RateLimitExceededException
import os
import json
import datetime
import re


def get_weight(title, labels):
    match = re.search(r'^\[(\d+)pt\]', title)

    if match:
        return int(match.group(1))

    for label in labels:
        match = re.search(r'^(\d+)pt\$', label)

        if match:
            return int(match.group(1))

    return 1


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

    for orgname, org_repos in issues.items():
        for reponame, repo_issues in org_repos.items():
            for number, issue in repo_issues.items():
                issue['weight'] = get_weight(issue['title'], issue['labels'])

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

    last_updated = None

    org = gh.get_organization(orgname)
    for repo in org.get_repos(type='all'):
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

            labels = [l.name for l in issue.labels]

            repo_issues[str(issue.number)] = {
                'title': issue.title,
                'updated_at': issue.updated_at.isoformat() + 'Z',
                'created_at': issue.created_at.isoformat() + 'Z',
                'closed_at': closed_at,
                'state': issue.state,
                'is_pr': issue.pull_request is not None,
                'labels': labels,
                'milestone': milestone,
                'milestone_number': milestone_number,
                'events': events,
                'weight': get_weight(issue.title, labels)
            }
            c = c +1
            if c % 100 == 99:
               write_issues(issues)

    write_issues(issues)

    return last_updated


def do_import(token, orgname, reponame=None, since=None):
    gh = Github(token)

    while True:
        try:
            try_sync_issues(gh, orgname, reponame, since)
            print("Synchronization finished successfully")
            break
        except RateLimitExceededException as e:
            print("API request limit reached. Sleeping for 10 minutes.")
            time.sleep(3600/6)
