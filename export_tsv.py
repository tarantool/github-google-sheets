#!/usr/bin/env python3

import csv

def do_export(issues, filename, orgname):
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
