#!/usr/bin/env python3
import datetime
import collections
import os
import json

def read_issues():
    issues = {}
    if os.path.exists('issues.json'):
        with open('issues.json', encoding='utf-8') as f:
            issues = json.loads(f.read())
    return issues


def burndown(issues, orgname):
    bd = {}

    if orgname in issues:
        for reponame, repo_issues in issues[orgname].items():
            bd[reponame] = collections.defaultdict(list)

            for number, issue in repo_issues.items():
                if issue['is_pr']:
                    continue

                closed_at = None

                if issue['closed_at'] is not None:
                    closed_at = datetime.datetime.strptime(issue['closed_at'], "%Y-%m-%dT%H:%M:%SZ")

                for event in issue['events']:
                    if event['event'] not in ['milestoned', 'demilestoned']:
                        continue

                    created_at = datetime.datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ")

                    if closed_at is not None and created_at > closed_at:
                        continue

                    if event['event'] == 'milestoned':
                        bd[reponame][event['milestone']].append(
                            (created_at.date(),
                             1))
                    else:
                        bd[reponame][event['milestone']].append(
                            (created_at.date(),
                             -1))

            for milestone, evts in bd[reponame].items():
                evts.sort(key=lambda e: e[0])

                start_date = evts[0][0]
                end_date = evts[-1][0]
                delta = datetime.timedelta(days=1)

                days = collections.OrderedDict()
                while start_date <= end_date:
                    days[start_date] = 0
                    start_date += delta

                for evt in evts:
                    days[evt[0]] += evt[1]

                acc = 0
                for day, count in days.items():
                    acc = acc + count
                    days[day] = acc

                print(reponame, milestone, days)

if __name__ == '__main__':
    issues = read_issues()

    bd = burndown(issues, 'tarantool')
