#!/usr/bin/env python3
import datetime
import collections
import os
import json
import pprint

def read_issues():
    issues = {}
    if os.path.exists('issues.json'):
        with open('issues.json', encoding='utf-8') as f:
            issues = json.loads(f.read())
    return issues


def merge_days(lhs, rhs):
    if len(list(lhs)) == 0 and len(list(rhs)) == 0:
        return collections.OrderedDict()

    if len(list(lhs)) == 0:
        return rhs

    if len(list(rhs)) == 0:
        return lhs

    start_date = min(list(lhs)[0], list(rhs)[0])
    end_date = max(list(lhs)[-1], list(rhs)[-1])

    delta = datetime.timedelta(days=1)

    days = collections.OrderedDict()

    last_lhs = None
    last_rhs = None

    while start_date <= end_date:
        days[start_date] = 0

        if start_date in lhs:
            days[start_date] += lhs[start_date]
            last_lhs = lhs[start_date]
        elif last_lhs is not None:
            days[start_date] += last_lhs

        if start_date in rhs:
            days[start_date] += rhs[start_date]
            last_rhs = rhs[start_date]
        elif last_rhs is not None:
            days[start_date] += last_rhs


        start_date += delta


    return days

def burndown(issues, orgname, milestones):
    bd = {}

    burndowns = {}
    if orgname in issues:
        for reponame, repo_issues in issues[orgname].items():
            milestone_issues = {}
            if reponame not in burndowns:
                burndowns[reponame] = {}

            bd[reponame] = collections.defaultdict(list)

            aliases = {}

            for number, issue in repo_issues.items():
                issue['number'] = number

            for number, issue in repo_issues.items():
                if issue['is_pr']:
                    continue
                if issue['milestone'] is not None:
                    if issue['milestone'] not in milestone_issues:
                        milestone_issues[issue['milestone']] = []

                    milestone_issues[issue['milestone']].append(issue)


                for event in reversed(issue['events']):
                    if event['event'] == 'demilestoned':
                        break

                    if event['event'] == 'milestoned' and issue['milestone'] is not None:
                        if event['milestone'] != issue['milestone']:
                            aliases[event['milestone']] = issue['milestone']


            for number, issue in repo_issues.items():
                if issue['is_pr']:
                    continue

                closed_at = None

                if issue['closed_at'] is not None:
                    closed_at = datetime.datetime.strptime(issue['closed_at'], "%Y-%m-%dT%H:%M:%SZ")

                milestoned = {}
                last_milestone = None
                for event in issue['events']:
                    if event['event'] not in ['milestoned', 'demilestoned']:
                        continue

                    created_at = datetime.datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ")

                    if closed_at is not None and created_at > closed_at:
                        continue

                    milestone = event['milestone']

                    if milestone in aliases:
                        milestone = aliases[milestone]

                    if event['event'] == 'milestoned':
                        last_milestone = milestone
                        milestoned[milestone] = created_at
                        bd[reponame][milestone].append(
                            (created_at.date(),
                             1))
                    else:
                        last_milestone = None
                        last = milestoned.get(event['milestone'], None)
                        if last == None:
                            continue

                        if closed_at is not None and last <= closed_at and closed_at <= created_at:
                            bd[reponame][event['milestone']].append(
                                (closed_at.date(),
                                 -1))
                        else:
                            bd[reponame][event['milestone']].append(
                                (created_at.date(),
                                 -1))

                if last_milestone is not None and closed_at is not None:
                    bd[reponame][last_milestone].append(
                        (closed_at.date(),
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

                burndowns[reponame][milestone] = {
                    "days": days,
                    "issues": milestone_issues.get(milestone, [])
                }

    res = {}

    #print(milestones)
    for reponame in burndowns:
        for milestone in burndowns[reponame]:

            for m in milestones:
                if reponame in milestones[m] and milestone in milestones[m][reponame]:
                    if m not in res:
                        res[m] = {"days": collections.OrderedDict(), "issues": []}

                    res[m]['days'] = merge_days(res[m]['days'], burndowns[reponame][milestone]['days'])

                    for issue in burndowns[reponame][milestone]['issues']:
                        issue['reponame'] = reponame
                        if issue['milestone'] == milestone:
                            res[m]['issues'].append(issue)


    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(res)

    return res

if __name__ == '__main__':
    issues = read_issues()

    bd = burndown(issues, 'tarantool')
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(bd)
