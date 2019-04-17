#!venv/bin/python3

import argparse
import datetime as dt
import json
from jsoncomment import JsonComment
import os
import requests
import sys

from dotenv import load_dotenv
load_dotenv()


def chunks(l, n):
    # https://chrisalbon.com/python/data_wrangling/break_list_into_chunks_of_equal_size/
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i+n]


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


class FeedbinAPI(object):

    class AuthException(Exception):
        pass

    class APIException(Exception):
        def __init__(self, message=None, status_code=None, errors=None, url=None, method=None):
            if errors and not message:
                message = json.dumps(errors)
            super(FeedbinAPI.APIException, self).__init__(message)
            self.status_code = status_code
            self.errors = errors or []
            self.url = url
            self.method = method

        @property
        def human_str(self):
            return 'Feedbin API Error: {msg:s}\n{method:s}: {url:s}\nHTTP Status: {status}\nError Detail:\n{detail}'.format(
                msg=self.__str__(),
                status=self.status_code or '[unknown]',
                detail=json.dumps(self.errors, sort_keys=True, indent=2),
                method='HTTP {}'.format(self.method or '[unknown method]'),
                url=self.url or '[URL unknown]'
            )

    API_BASE = 'https://api.feedbin.com/v2'

    def __init__(self, username, password):
        self.auth = (username, password)

    def _check_response(self, r):
        if r.status_code == 401:
            raise FeedbinAPI.AuthException()
        if r.status_code != 200:
            decoded = r.json()
            raise FeedbinAPI.APIException(
                message=decoded.get('message'),
                status_code=decoded.get('status'),
                errors=decoded.get('errors'),
                method=r.request.method,
                url=r.request.url,
            )

    def _get_all_pages(self, endpoint, params=None):
        if params is None:
            params = {}
        params['page'] = 1
        resp = self._get(endpoint, params)
        results = resp.json()
        next_url = resp.links.get('next')
        while next_url:
            resp = requests.get(next_url, auth=self.auth)
            self._check_response(resp)
            results.extend(resp.json())
            next_url = resp.links.get('next')
        return results

    def _get(self, endpoint, params=None):
        url = '{base:s}/{endpoint:s}.json'.format(base=FeedbinAPI.API_BASE, endpoint=endpoint)
        resp = requests.get(url, auth=self.auth, params=params)
        self._check_response(resp)
        return resp

    def _get_decoded(self, endpoint, params=None):
        return self._get(endpoint, params).json()

    def get_unread_entries(self):
        entry_ids_chunks = list(chunks(self._get_decoded('unread_entries'), 100))
        entries = []
        for entry_ids in entry_ids_chunks:
            entries.extend(self._get_all_pages('entries', params={
                'ids': ','.join([str(id) for id in entry_ids]).strip(',')
            }))
        return entries

    def get_subscriptions(self):
        return self._get_decoded('subscriptions')

    def get_feed(self, feed_id):
        return self._get_decoded('feeds/{}'.format(feed_id))

    def check_auth(self):
        r = self._get('authentication')

    def mark_read(self, entry_id):
        url = '{base:s}/{endpoint:s}.json'.format(base=FeedbinAPI.API_BASE, endpoint='unread_entries')
        resp = requests.delete(url, auth=self.auth, json={
            "unread_entries": [entry_id]
        })
        self._check_response(resp)


class Rules(object):

    class SpecException(Exception):
        pass

    class ValidationException(Exception):
        pass

    def __init__(self, max_age, only_feed_id=None):
        self.default_max_age = max_age
        self.only_feed_id = only_feed_id
        self.feed_rules = {}

    def add_rules(self, rules_dict):
        if 'max_age' not in rules_dict:
            raise Rules.SpecException('Rules file must contain a global max_age specification.')
        self.default_max_age = int(rules_dict['max_age'])
        if 'feed_specific' not in rules_dict:
            raise Rules.SpecException('Rules file must contain a feed_specific rules list.')
        for rule in rules_dict['feed_specific']:
            if 'feed_id' not in rule or 'max_age' not in rule:
                raise Rules.SpecException('Feed rule {} must include a feed_id and max_age.'.format(json.dumps(rule)))
            self.feed_rules[int(rule['feed_id'])] = int(rule['max_age'])

    def max_age(self, feed_id):
        retv = self.default_max_age
        if feed_id in self.feed_rules:
            retv = self.feed_rules[feed_id]
        if self.only_feed_id is not None and feed_id != self.only_feed_id:
            return dt.timedelta.max
        return dt.timedelta(days=retv)

    def validate_rules(self, feeds):
        all_feed_ids = list(self.feed_rules.keys())
        if self.only_feed_id is not None:
            all_feed_ids.append(self.only_feed_id)
        for feed_id in all_feed_ids:
            matches = [f for f in feeds if f['feed_id'] == feed_id]
            if not matches:
                raise Rules.ValidationException('A rule has been specified for feed ID {id:d}, but you\'re not subscribed to a feed with that ID.'.format(id=feed_id))


def list_feeds(feedbin_api):
    feeds = feedbin_api.get_subscriptions()
    feeds.sort(key=lambda f: f['title'].lower())
    for f in feeds:
        print('{id:d}\t\t{title:s}  -  {url:s}'.format(id=f['feed_id'], title=f['title'], url=f['site_url']))


def run_archive(feedbin_api, rules, dry_run):
    if dry_run:
        print('Listing entries which would be archived...')
    else:
        print('Archiving old entries...')
    now = dt.datetime.now(dt.timezone.utc)
    entries = feedbin_api.get_unread_entries()
    count = 0
    for entry in entries:
        entry_ts = dt.datetime.strptime(entry['published'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.timezone.utc)
        entry_age = now - entry_ts
        max_age = rules.max_age(entry['feed_id'])
        if entry_age > max_age:
            feed = feedbin_api.get_feed(entry['feed_id'])
            print('')
            print('{feed_title:s}: {entry_title:s}'.format(feed_title=feed['title'], entry_title=entry['title']))
            print('{age:d} days old (max age is {max:d} days)'.format(age=entry_age.days, max=max_age.days))
            print(entry['url'])
            if not dry_run:
                feedbin_api.mark_read(entry['id'])
            count += 1
    print('')
    print('{:d} entries affected.'.format(count))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mark old Feedbin entries as read.')
    parser.add_argument('action', nargs='?', default='run', choices={'run', 'list-feeds'})
    parser.add_argument('--dry-run', type=str2bool, default='true', help='True to print what would be archived, then exit. False to archive old unread entries. Default: True.')
    parser.add_argument('--ignore-rules-validation', type=str2bool, default='false', help='True to ignore validation checks on the rules file; false to exit on validation errors. Default: False.')
    parser.add_argument('--max-age', type=int, default=30, help='Entries older than this many days will be marked as read. Ignored if using --rules-file. Default: 30.')
    parser.add_argument('--only-feed', type=int, default=None, help='Operate on only the given feed ID. Default: none.')
    parser.add_argument('--rules-file', default=None, help='Extended rules JSON file. See rules.sample.json for an example.')
    args = parser.parse_args()

    feedbin_user = os.getenv('FEEDBIN_ARCHIVER_USERNAME')
    feedbin_pass = os.getenv('FEEDBIN_ARCHIVER_PASSWORD')
    if not feedbin_user or not feedbin_pass:
        eprint("Feedbin username & password must be set using environment variables.")
        eprint("Copy .env.sample to .env and fill it out to provide credentials.")
        sys.exit(1)
    feedbin_api = FeedbinAPI(feedbin_user, feedbin_pass)
    try:
        feedbin_api.check_auth()
    except FeedbinAPI.AuthException:
        eprint("Feedbin authentication failed.")
        eprint("Check your credentials and try again.")
        sys.exit(1)

    if args.action == 'list-feeds':
        try:
            list_feeds(feedbin_api)
        except FeedbinAPI.APIException as e:
            eprint(e.human_str)
            sys.exit(3)
        sys.exit(0)

    if args.action == 'run':
        rules = Rules(args.max_age, only_feed_id=args.only_feed)
        if args.rules_file:
            rules_dict = JsonComment().loadf(args.rules_file)
            try:
                rules.add_rules(rules_dict)
            except Rules.SpecException as e:
                eprint(e)
                sys.exit(1)
        try:
            rules.validate_rules(feeds=feedbin_api.get_subscriptions())
        except Rules.ValidationException as e:
            eprint(e)
            if not args.ignore_rules_validation:
                sys.exit(2)
        try:
            run_archive(feedbin_api, rules=rules, dry_run=args.dry_run)
        except FeedbinAPI.APIException as e:
            eprint(e.human_str)
            sys.exit(3)
        sys.exit(0)

    raise Exception('Unexpected/unhandled action argument encountered.')
