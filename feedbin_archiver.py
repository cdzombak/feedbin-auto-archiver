#!venv/bin/python3

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Final

import commentjson
import requests
from dotenv import load_dotenv

load_dotenv()


TIMEOUT: Final = 20


def chunks(a_list, n):
    # https://chrisalbon.com/python/data_wrangling/break_list_into_chunks_of_equal_size/
    # For item i in a range that is a length of l,
    for i in range(0, len(a_list), n):
        # Create an index range for l of n items:
        yield a_list[i : i + n]


def truncate_string_with_ellipsis(s, max_len):
    return (s[: max_len - 3] + "...") if len(s) > max_len else s


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse_entry_date(entry):
    """Parse the published date from an entry and return as UTC datetime."""
    return dt.datetime.strptime(entry["published"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=dt.timezone.utc
    )


def str2bool(v):
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


class FeedbinAPI(object):
    class AuthException(Exception):
        pass

    class APIException(Exception):
        def __init__(
            self, message=None, status_code=None, errors=None, url=None, method=None
        ):
            if errors and not message:
                message = json.dumps(errors)
            super(FeedbinAPI.APIException, self).__init__(message)
            self.status_code = status_code
            self.errors = errors or []
            self.url = url
            self.method = method

        @property
        def human_str(self):
            return (
                "Feedbin API Error: {msg:s}\n{method:s}: {url:s}\n"
                "HTTP Status: {status}\nError Detail:\n{detail}"
            ).format(
                msg=self.__str__(),
                status=self.status_code or "[unknown]",
                detail=json.dumps(self.errors, sort_keys=True, indent=2),
                method="HTTP {}".format(self.method or "[unknown method]"),
                url=self.url or "[URL unknown]",
            )

    API_BASE = "https://api.feedbin.com/v2"

    def __init__(self, username, password):
        self.auth = (username, password)

    def _check_response(self, r):
        if r.status_code == 401:
            raise FeedbinAPI.AuthException()
        if r.status_code != 200:
            decoded = r.json()
            raise FeedbinAPI.APIException(
                message=decoded.get("message"),
                status_code=decoded.get("status"),
                errors=decoded.get("errors"),
                method=r.request.method,
                url=r.request.url,
            )

    def _get_all_pages(self, endpoint, params=None):
        if params is None:
            params = {}
        params["page"] = 1
        resp = self._get(endpoint, params)
        results = resp.json()
        next_url = resp.links.get("next")
        while next_url:
            resp = requests.get(next_url, auth=self.auth, timeout=TIMEOUT)
            self._check_response(resp)
            results.extend(resp.json())
            next_url = resp.links.get("next")
        return results

    def _get(self, endpoint, params=None):
        url = "{base:s}/{endpoint:s}.json".format(
            base=FeedbinAPI.API_BASE, endpoint=endpoint
        )
        resp = requests.get(url, auth=self.auth, params=params, timeout=TIMEOUT)
        self._check_response(resp)
        return resp

    def _get_decoded(self, endpoint, params=None):
        return self._get(endpoint, params).json()

    def get_unread_entries(self):
        entry_ids_chunks = list(chunks(self._get_decoded("unread_entries"), 100))
        entries = []
        for entry_ids in entry_ids_chunks:
            entries.extend(
                self._get_all_pages(
                    "entries",
                    params={"ids": ",".join([str(id) for id in entry_ids]).strip(",")},
                )
            )
        return entries

    def get_subscriptions(self):
        return self._get_decoded("subscriptions")

    def get_feed(self, feed_id):
        return self._get_decoded("feeds/{}".format(feed_id))

    def check_auth(self):
        self._get("authentication")

    def mark_read(self, entry_id):
        url = "{base:s}/{endpoint:s}.json".format(
            base=FeedbinAPI.API_BASE, endpoint="unread_entries"
        )
        resp = requests.delete(
            url, auth=self.auth, json={"unread_entries": [entry_id]}, timeout=TIMEOUT
        )
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
        self.keep_n_rules = {}
        self.title_regex_rules = {}
        self.title_regex_keep_n_rules = {}

    def add_rules(self, rules_dict):
        if "max_age" in rules_dict:
            self.default_max_age = int(rules_dict["max_age"])

        # Handle feed_specific rules
        if "feed_specific" in rules_dict:
            for rule in rules_dict["feed_specific"]:
                if "feed_id" not in rule:
                    raise Rules.SpecException(
                        "Feed rule {} must include a feed_id.".format(json.dumps(rule))
                    )

                has_max_age = "max_age" in rule
                has_keep_n = "keep_n" in rule

                if not has_max_age and not has_keep_n:
                    raise Rules.SpecException(
                        "Feed rule {} must include at least max_age or keep_n.".format(
                            json.dumps(rule)
                        )
                    )

                feed_id = int(rule["feed_id"])
                if has_max_age:
                    self.feed_rules[feed_id] = int(rule["max_age"])
                if has_keep_n:
                    self.keep_n_rules[feed_id] = int(rule["keep_n"])

        # Handle title_regex rules
        if "title_regex" in rules_dict:
            for rule in rules_dict["title_regex"]:
                if "title_regex" not in rule:
                    raise Rules.SpecException(
                        "Title regex rule {} must include a title_regex.".format(
                            json.dumps(rule)
                        )
                    )

                has_max_age = "max_age" in rule
                has_keep_n = "keep_n" in rule

                if not has_max_age and not has_keep_n:
                    raise Rules.SpecException(
                        "Title regex rule {} must include at least max_age or keep_n.".format(
                            json.dumps(rule)
                        )
                    )

                # Validate regex pattern
                try:
                    re.compile(rule["title_regex"])
                except re.error as e:
                    raise Rules.SpecException(
                        "Invalid regex pattern '{}': {}".format(
                            rule["title_regex"], str(e)
                        )
                    )

                regex_pattern = rule["title_regex"]
                if has_max_age:
                    self.title_regex_rules[regex_pattern] = int(rule["max_age"])
                if has_keep_n:
                    self.title_regex_keep_n_rules[regex_pattern] = int(rule["keep_n"])

        # Require at least one rule type
        if "feed_specific" not in rules_dict and "title_regex" not in rules_dict:
            raise Rules.SpecException(
                "Rules file must contain either feed_specific or title_regex rules."
            )

    def max_age(self, feed_id, feed_title=None):
        # Collect all applicable max_age rules
        applicable_max_ages = [self.default_max_age]

        # Add feed-specific max_age rule if it exists
        if feed_id in self.feed_rules:
            applicable_max_ages.append(self.feed_rules[feed_id])

        # Add all matching title regex max_age rules
        if feed_title:
            for regex_pattern, max_age_value in self.title_regex_rules.items():
                if re.search(regex_pattern, feed_title):
                    applicable_max_ages.append(max_age_value)

        # Use the most aggressive (smallest) max_age
        retv = min(applicable_max_ages)

        if self.only_feed_id is not None and feed_id != self.only_feed_id:
            return dt.timedelta.max
        return dt.timedelta(days=retv)

    def keep_n(self, feed_id, feed_title=None):
        """Return the keep_n value for a feed, or None if not using keep_n."""
        # Collect all applicable keep_n rules
        applicable_keep_ns = []

        # Add feed-specific keep_n rule if it exists
        if feed_id in self.keep_n_rules:
            applicable_keep_ns.append(self.keep_n_rules[feed_id])

        # Add all matching title regex keep_n rules
        if feed_title:
            for regex_pattern, keep_n_value in self.title_regex_keep_n_rules.items():
                if re.search(regex_pattern, feed_title):
                    applicable_keep_ns.append(keep_n_value)

        # Use the most aggressive (smallest) keep_n, or None if no keep_n rules apply
        retv = min(applicable_keep_ns) if applicable_keep_ns else None

        if self.only_feed_id is not None and feed_id != self.only_feed_id:
            return None  # Skip keep_n logic for feeds not being processed
        return retv

    def uses_keep_n(self, feed_id, feed_title=None):
        """Check if a feed uses keep_n logic."""
        # Check if feed has feed-specific keep_n rule
        if feed_id in self.keep_n_rules:
            return True

        # Check if feed title matches any title regex keep_n rule
        if feed_title:
            for regex_pattern in self.title_regex_keep_n_rules:
                if re.search(regex_pattern, feed_title):
                    return True

        return False

    def uses_max_age(self, feed_id, feed_title=None):
        """Check if a feed uses max_age logic."""
        # Check if feed has feed-specific max_age rule
        if feed_id in self.feed_rules:
            return True

        # Check if feed title matches any title regex max_age rule
        if feed_title:
            for regex_pattern in self.title_regex_rules:
                if re.search(regex_pattern, feed_title):
                    return True

        # Use max_age if no keep_n rules apply (fallback to default behavior)
        return not self.uses_keep_n(feed_id, feed_title)

    def validate_rules(self, feeds):
        all_feed_ids = list(self.feed_rules.keys()) + list(self.keep_n_rules.keys())
        if self.only_feed_id is not None:
            all_feed_ids.append(self.only_feed_id)
        for feed_id in all_feed_ids:
            matches = [f for f in feeds if f["feed_id"] == feed_id]
            if not matches:
                raise Rules.ValidationException(
                    "A rule has been specified for feed ID {id:d}, but you're "
                    "not subscribed to a feed with that ID.".format(id=feed_id)
                )


def list_feeds(feedbin_api):
    feeds = feedbin_api.get_subscriptions()
    feeds.sort(key=lambda f: f["title"].lower())
    for f in feeds:
        print(
            "{id:d}\t\t{title:s}  -  {url:s}".format(
                id=f["feed_id"], title=f["title"], url=f["site_url"]
            )
        )


def run_archive(feedbin_api, rules, dry_run):
    if dry_run:
        print("Listing entries which would be archived...")
    else:
        print("Archiving old entries...")
    now = dt.datetime.now(dt.timezone.utc)
    entries = feedbin_api.get_unread_entries()

    # Parse dates for all entries and sort by date (newest first)
    for entry in entries:
        entry["parsed_date"] = parse_entry_date(entry)
    entries.sort(key=lambda e: e["parsed_date"], reverse=True)

    # Preload all feeds to get titles for title regex matching
    feeds_by_id = {}
    unique_feed_ids = set(entry["feed_id"] for entry in entries)
    for feed_id in unique_feed_ids:
        feeds_by_id[feed_id] = feedbin_api.get_feed(feed_id)

    # Track counts per feed for keep_n logic
    feed_counts = {}
    count = 0

    for entry in entries:
        feed_id = entry["feed_id"]
        entry_ts = entry["parsed_date"]
        entry_age = now - entry_ts
        feed_title = feeds_by_id[feed_id]["title"]

        should_archive = False
        archive_reasons = []

        if rules.uses_keep_n(feed_id, feed_title):
            feed_counts[feed_id] = feed_counts.get(feed_id, 0) + 1
            keep_n = rules.keep_n(feed_id, feed_title)
            if keep_n is not None and feed_counts[feed_id] > keep_n:
                should_archive = True
                archive_reasons.append(
                    "keeping only {keep:d} most recent entries".format(keep=keep_n)
                )

        if rules.uses_max_age(feed_id, feed_title):
            max_age = rules.max_age(feed_id, feed_title)
            if entry_age > max_age:
                should_archive = True
                archive_reasons.append(
                    "{age:d} days old (max age is {max:d} days)".format(
                        age=entry_age.days, max=max_age.days
                    )
                )

        archive_reason = "; ".join(archive_reasons)

        if should_archive:
            feed = feeds_by_id[feed_id]
            print("")
            entry_title = entry.get("title")
            if not entry_title and entry["summary"]:
                entry_title = truncate_string_with_ellipsis(entry["summary"], 70)
            if not entry_title and entry["content"]:
                entry_title = truncate_string_with_ellipsis(entry["content"], 70)
            print(
                "{feed_title:s}: {entry_title:s}".format(
                    feed_title=feed["title"], entry_title=entry_title
                )
            )
            print(archive_reason)
            print(entry["url"])
            if not dry_run:
                feedbin_api.mark_read(entry["id"])
            count += 1

    print("")
    print("{:d} entries affected.".format(count))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mark old Feedbin entries as read.")
    parser.add_argument(
        "action", nargs="?", default="run", choices={"run", "list-feeds"}
    )
    parser.add_argument(
        "--dry-run",
        type=str2bool,
        default="true",
        help="True to print what would be archived, then exit; "
        "false to archive old unread entries. Default: True.",
    )
    parser.add_argument(
        "--ignore-rules-validation",
        type=str2bool,
        default="true",
        help="False to fail with an error if given a rule for a feed you're "
        "not subscribed to; True to ignore this case. Default: True.",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=30,
        help="Entries older than this many days will be marked as read. "
        "Ignored if using --rules-file. Default: 30.",
    )
    parser.add_argument(
        "--only-feed",
        type=int,
        default=None,
        help="Operate on only the given feed ID. Default: none.",
    )
    parser.add_argument(
        "--rules-file",
        default=None,
        help="Extended rules JSON file. See rules.sample.json for an example.",
    )
    args = parser.parse_args()

    feedbin_user = os.getenv("FEEDBIN_ARCHIVER_USERNAME")
    feedbin_pass = os.getenv("FEEDBIN_ARCHIVER_PASSWORD")
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

    if args.action == "list-feeds":
        try:
            list_feeds(feedbin_api)
        except FeedbinAPI.APIException as e:
            eprint(e.human_str)
            sys.exit(3)
        sys.exit(0)

    if args.action == "run":
        rules = Rules(args.max_age, only_feed_id=args.only_feed)
        if args.rules_file:
            with open(args.rules_file, "r", encoding="utf-8") as f:
                rules_dict = commentjson.load(f)
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

    raise Exception("Unexpected/unhandled action argument encountered.")
