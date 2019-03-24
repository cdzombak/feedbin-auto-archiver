# Feedbin Auto-Archiver

*Auto-archiving for older unread posts in Feedbin, inspired by Pocket Casts’ configurable auto-archive feature.*

## Motivation

Someone in the RSS/microblogging ecosystem — I forget who — recently posted something along the lines of “RSS shouldn’t be a source of stress. It’s okay to just mark it all as read and move on.”

The same is true of podcasts. Pocket Casts has an auto-archive feature which is quite configurable on a per-feed basis, and that feature helps me avoid stress during times when I’ve fallen behind on podcasts.

But with RSS, I find myself hesitant to archive older stuff; I can’t help but worry, “what if there’s something I really should read down there somewhere?”

So I built this tool. It’s designed to be run on a periodic basis (2-4 times per day, maybe). It will mark as read everything in your Feedbin account older than some time period (30 days, by default), and it allows configuring a custom maximum unread “age” per feed.

## Requirements

- Python 3 + [virtualenv](https://docs.python-guide.org/dev/virtualenvs/#lower-level-virtualenv)
- A [Feedbin](https://feedbin.com) account

I know this works on macOS and Ubuntu; it should work pretty much anywhere Python 3 runs.

## Installation

- Clone the repo
- Run `make bootstrap` to create a virtualenv for the project & install depepdencies

### Cron

TKTK: add cron once I've deployed this myself

### Cleanup

`make clean` will remove the virtualenv and cleanup any temporary artifacts (currently, there are none of those).

## Usage

- Activate the virtualenv: `. venv/bin/activate`
- Run the script: `python feedbin_archiver.py [flags]`

At least some flags are needed to make the script do anything useful. Credential configuration is documented in “Configuration,” below.

### Flags

All flags are optional (though if you omit `--dry-run`, no changes will ever be made in your Feedbin account).

#### `--dry-run`

**Boolean. Default: True.**

Dry-run specifies whether the script should actually change anything in your Feedbin account. By default, this is `true`, meaning no changes will be made.

Once you’re confident in your configuration, activate the script with `--dry-fun false`.

#### `--max-age`

**Integer. Default: 30.**

The maximum age for unread entries. Entries older than this will be marked as read.

This argument is ignored when using a rules file (see `--rules-file` below).

#### `--only-feed`

**Integer. Default: none.**

Only archive entries in the given feed. This is useful for eg. debugging or one-off archviing tasks.

#### `--rules-file`

**String (path/filename). Default: none.**

The path to a JSON file describing your per-feed rules. See “Configuration” below for details.

If a rules file is specified, the `--max-age` flag has no effect.

### List Feeds

Run `python feedbin_archiver.py list-feeds` to print a list of your Feedbin feeds, along with their IDs, for use in writing per-feed rules.

The output is grep-able. For example, to find my blog feed, try `python feedbin_archiver.py list-feeds | grep -i "chris dzombak"`

## Configuration

### Credentials

Credentials are supplied via the environment variables `FEEDBIN_ARCHIVER_USERNAME` and `FEEDBIN_ARCHIVER_PASSWORD`.

Optionally, these can be stored in a `.env` file alongside the `feedbin_archiver` script. The script will automatically read environemnt variables from that file. (See `.env.sample` for an example.)

### Rules File

The rules file is a JSON file specifying per-feed maximum entry ages. The file is allowed to contain comments, allowing for clarity & easier maintenance. See `rules.sample.json` for an example.

The file must contain an object with two top-level keys: `max_age` and `feed_specific`.

`max_age` is equivalent to the `--max-age` argument; any entries older than that age will be marked as read, unless they’re in a feed for which you’ve created a custom rule.

`feed_specific` is a list of objects, each of which have two keys, like this:

```javascript
"feed_specific": [
  {
    // Add comment with Feed Name for maintainability
    "feed_id": 450,
    "max_age": 1
  }, // …
]
```

Those feed-specific rules take precedence over `max_age`. This allows you to set a quicker expiration for high-traffic feeds, or set a longer expiration for feeds with entries you really don’t want to miss.

### “Ignore This Feed”

To avoid the archiver marking anything as read in a given feed, specify `999999999` for the feed’s `max_age`. (That is roughly 2.7 million years.)

This is the [maximum](https://docs.python.org/3/library/datetime.html#datetime.timedelta.max) number of days a Python `timedelta` object can represent.

## License

TKTK: decide on license

## Author

Chris Dzombak, [dzombak.com](https://www.dzombak.com)
