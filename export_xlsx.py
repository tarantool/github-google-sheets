#!/usr/bin/env python3

import xlsxwriter
import datetime
import collections
import burndown

def do_export(issues, filename, milestone_filter):
    workbook = xlsxwriter.Workbook(filename)
    issue_sheet = workbook.add_worksheet("All issues")

    issue_sheet.write_row(
        'A1',
        ['path', 'orgname', 'reponame', 'id', 'title', 'state', 'created_at', 'updated_at', 'closed_at'])

    date_format = workbook.add_format()
    date_format.set_num_format('d mmmm yyyy')

    wrap_format = workbook.add_format({'text_wrap': 1})

    issue_data = []
    event_data = []

    issue_sheet.set_column('A:A', 40)
    issue_sheet.set_column('B:C', 12)

    issue_sheet.set_column('E:E', 100)
    issue_sheet.set_column('G:I', 17)

    milestones = collections.defaultdict(list)

    for orgname, org_repos in issues.items():
        for reponame, repo_issues in org_repos.items():
            for number, issue in repo_issues.items():
                if issue['is_pr']:
                    continue

                closed_at = None

                if issue['closed_at'] is not None:
                    closed_at = datetime.datetime.strptime(issue['closed_at'], "%Y-%m-%dT%H:%M:%SZ")

                issue_row = [
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
                issue_data.append(issue_row)

    issue_sheet.add_table(
        'A1:I%d'%len(issue_data),
        {'data': issue_data,
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
    issue_sheet.freeze_panes(1, 0)

    bd = burndown.burndown(issues, milestone_filter)

    for milestone, entries in bd.items():
        milestone_sheet = workbook.add_worksheet(milestone)

        milestone_sheet.set_column('A:A', 17)
        milestone_sheet.set_column('B:B', 10)

        milestone_sheet.set_column('E:E', 20)
        milestone_sheet.set_column('F:F', 20)
        milestone_sheet.set_column('G:H', 12)
        milestone_sheet.set_column('I:I', 100)
        milestone_sheet.set_column('J:J', 10)

        milestone_data = []
        event_data = []

        for day, count in entries['days'].items():
            event_row = [
                day,
                count
            ]
            event_data.append(event_row)

        for issue in entries['issues']:
            row = [
                issue['orgname'],
                issue['reponame'],
                issue['milestone'],
                int(issue['number']),
                issue['title'],
                issue['weight'],
                issue['state'],
                issue.get('source', None)
            ]
            milestone_data.append(row)

        first_row = 25

        chart = workbook.add_chart({'type': 'line'})


        milestone_sheet.add_table(
            'A%d:B%d'%(first_row, len(event_data)+first_row),
            {'data': event_data,
             'columns':
             [{'header': 'date', 'format': date_format},
              {'header': 'weight'}
              ]})

        milestone_sheet.add_table(
            'E%d:K%d'%(first_row, len(milestone_data)+first_row),
            {'data': milestone_data,
             'columns':
             [{'header': 'orgname'},
              {'header': 'reponame'},
              {'header': 'milestone'},
              {'header': 'number'},
              {'header': 'title'},
              {'header': 'weight'},
              {'header': 'state'},
              ]})


        url_format = workbook.get_default_url_format()
        for i, data in enumerate(milestone_data):
            baseurl = "https://github.com"
            if data[7] is not None:
                baseurl = data[7]
            url = "%s/%s/%s/issues/%d" % (baseurl, data[0], data[1], data[3])
            milestone_sheet.write_url('G%d' % (first_row + i+1,), url, string=str(data[3]))
            milestone_sheet.write_number('G%d' % (first_row + i+1,), data[3], url_format)

        #milestone_sheet.freeze_panes(1, 0)

        chart.set_title({'name': ''})
        chart.add_series(
            {
                'categories': '=\'%s\'!$A$%d:$A$%d'%(milestone, first_row, len(event_data)+first_row),
                'values': '=\'%s\'!$B$%d:$B$%d'%(milestone, first_row, len(event_data)+first_row)
            })

        chart.set_x_axis({
            'date_axis': True
        })
        chart.set_y_axis({
            'date_axis': False,
            'num_format': '0'
        })

        chart.set_size({'width': 1400, 'height': 420})

        milestone_sheet.insert_chart('A1', chart)

    workbook.close()
