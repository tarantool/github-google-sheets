#!/usr/bin/env python3


import argparse
import pickle
import os.path
import datetime
import json
import time
import configparser
import csv
import collections
import burndown

import export_xlsx
import export_tsv
import export_google_sheets
import import_github
import import_gitlab

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

    google_sheets = export_subparsers.add_parser("google_sheets")
    google_sheets.add_argument('filename')

    xlsx = subparsers.add_parser("daemon")


    args = parser.parse_args()

    config = configparser.ConfigParser()

    filename = 'github-google-sheets.ini'

    if os.path.exists(filename):
        config.read(filename)
    elif os.path.exists(os.path.expanduser("~/." + filename)):
        config.read(os.path.expanduser("~/." + filename))
    else:
        raise RuntimeError('Configuration file not found.')

    github_token = config['default'].get('github_token', None)
    gitlab_token = config['default'].get('gitlab_token', None)

    if gitlab_token is not None:
        gitlab_whitelist = config['default'].get('gitlab_whitelist', None)
        if gitlab_whitelist is not None:
            gitlab_whitelist = gitlab_whitelist.split(',')
        gitlab_org = config['default']['gitlab_org']

    github_org = config['default']['github_org']

    sheet_name = config['default'].get('google_sheet_name', None)

    milestones = {}
    for section in config.sections():
        if section == 'default':
            continue
        if section not in milestones:
            milestones[section] = {}

        for key in config[section]:
            if key not in milestones[section]:
                milestones[section][key] = []
            milestones[section][key].extend(
                [m.strip() for m in config[section][key].split(',')]
            )
    print(milestones)

    if args.command == 'sync':
        since = None
        if args.full:
            since = datetime.datetime.strptime("1969-12-31T21:00:00Z", "%Y-%m-%dT%H:%M:%SZ")

        if github_token is not None:
            import_github.do_import(github_token, github_org, args.reponame, since)
        if gitlab_token is not None:
            import_gitlab.do_import(gitlab_token, gitlab_org, args.reponame, since, whitelist=gitlab_whitelist)
        print("Synchronization finished successfully")

    elif args.command == 'export':
        issues = {}
        if os.path.exists('issues.json'):
            with open('issues.json', encoding='utf-8') as f:
                issues = json.loads(f.read())

        if args.export_command == 'tsv':
            export_tsv.do_export(issues, args.filename, github_org)
        elif args.export_command == 'xlsx':
            export_xlsx.do_export(issues, args.filename, milestones)
        elif args.export_command == 'google_sheets':
            export_google_sheets.do_export(issues, args.filename, milestones)
    elif args.command == 'daemon':
        while True:
            if github_token is not None:
                import_github.do_import(github_token, github_org)
            if gitlab_token is not None:
                import_gitlab.do_import(gitlab_token, gitlab_org, whitelist=gitlab_whitelist)
            print("Synchronization finished successfully")

            issues = {}
            if os.path.exists('issues.json'):
                with open('issues.json', encoding='utf-8') as f:
                    issues = json.loads(f.read())

            if sheet_name is not None:
                export_google_sheets.do_export(issues, sheet_name, milestones)

            print("Sleeping for 60 minutes")
            time.sleep(3600)
