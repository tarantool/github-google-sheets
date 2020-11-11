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
import import_github


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
    #print(milestones)
    if args.command == 'sync':
        since = None
        if args.full:
            since = datetime.datetime.strptime("1969-12-31T21:00:00Z", "%Y-%m-%dT%H:%M:%SZ")

        import_github.do_import(token, orgname, args.reponame, since)
    elif args.command == 'export':
        issues = {}
        if os.path.exists('issues.json'):
            with open('issues.json', encoding='utf-8') as f:
                issues = json.loads(f.read())

        if args.export_command == 'tsv':
            export_tsv.do_export(issues, args.filename, orgname)
        elif args.export_command == 'xlsx':
            export_xlsx.do_export(issues, args.filename, orgname, milestones)
