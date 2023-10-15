# Feedbin Auto-Archiver

*Auto-archiving for older unread posts in Feedbin, inspired by Pocket Casts’ configurable auto-archive feature.*

## Motivation

Someone in the microblogging/pro-RSS community — I forget who — recently posted something along the lines of “RSS shouldn’t be a source of stress. It’s okay to just mark it all as read and move on.”

The same is true of podcasts. To help with that, Pocket Casts has an auto-archive feature which is quite configurable on a per-feed basis, and that feature helps me avoid stress during times when I’ve fallen behind on podcasts.

With RSS, I find myself hesitant to mark a long list of entries as read; I can’t help but worry, “what if there’s something I really should read down there somewhere?”

So I built this tool. It’s designed to be run on a periodic basis (2-4 times per day, perhaps). It will mark as read everything in your Feedbin account older than some time period (30 days, by default), and it allows configuring a custom maximum unread “age” per feed.

### See Also

[Instapaper Auto Archiver](https://github.com/cdzombak/instapaper-auto-archiver) performs a similar function, for old unread Instapaper bookmarks.

## Installation (Docker)

Pre-built Docker images are available. [See Docker Hub for details](https://hub.docker.com/r/cdzombak/feedbin-auto-archiver).

No installation is required to use these images under Docker.

## Installation (local Python)

1. Clone the repo and change into the `feedbin-auto-archiver` directory
2. Run `make virtualenv` to create a virtualenv for the project & install dependencies

## Configuration

### Credentials

Credentials are supplied via the environment variables `FEEDBIN_ARCHIVER_USERNAME` and `FEEDBIN_ARCHIVER_PASSWORD`.

#### Docker Configuration

Credentials may be placed in a `.env` file and given to the `docker run` command like:

```shell
docker run --rm --env-file .env cdzombak/feedbin-auto-archiver:1 [OPTIONS]
```

(See `.env.sample` for a sample file.)

Alternatively, credentials may be passed directly to the `docker run` command like:

```shell
docker run --rm -e FEEDBIN_ARCHIVER_USERNAME=myusername -e FEEDBIN_ARCHIVER_PASSWORD=mypassword \
    cdzombak/feedbin-auto-archiver:1 [OPTIONS]
```

#### Local Python Configuration

Your credentials can be stored in a `.env` file alongside the `feedbin_archiver.py` script. The script will automatically read environment variables from that file. (See `.env.sample` for an example.)

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

## Usage

### Docker Usage

Invoke the script with `docker run`. To use a config file, you will need to mount it into the container.

```shell
docker run --rm --env-file .env \
    -v /path/to/my_rules.json:/rules.json \
    cdzombak/feedbin-auto-archiver:1 \
    --rules-file /rules.json [--dry-run false] [OPTIONS]
```

### Local Python Usage

1. Activate the virtualenv: `. venv/bin/activate`
2. Run the script: `python feedbin_archiver.py [OPTIONS]`

Alternatively, invoke the virtualenv's Python interpreter directly:

```shell
venv/bin/python3 feedbin_archiver.py --rules-file /path/to/my_rules.json [--dry-run false] [OPTIONS]
```

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

Only archive entries in the given feed. This is useful for eg. debugging or one-off archiving tasks.

#### `--rules-file`

**String (path/filename). Default: none.**

The path to a JSON file describing your per-feed rules. See “Configuration” below for details.

If a rules file is specified, the `--max-age` flag has no effect.

### List Feeds

Run `python feedbin_archiver.py list-feeds` to print a list of your Feedbin feeds, along with their IDs, for use in writing per-feed rules.

The output is grep-able. For example, to find my blog feed, try `python feedbin_archiver.py list-feeds | grep -i "chris dzombak"`

(For Docker, run `docker run --rm --env-file .env cdzombak/feedbin-auto-archiver:1 list-feeds`.)

### Crontab Example

This is how I’m running this tool on my home server:

```text
# Feedbin Archiver
# Runs every 6 hours == 4x/day
0   */6 *   *   *   docker run --rm --env-file $HOME/.config/feedbin/env -v $HOME/.config/feedbin/archiver_rules.json:/rules.json cdzombak/feedbin-auto-archiver:1 --rules-file /rules.json --dry-run false
```

## License

[MIT License](https://choosealicense.com/licenses/mit/#).

## Author

Chris Dzombak
- [github.com/cdzombak](https://www.github.com/cdzombak)
- [dzombak.com](https://www.dzombak.com)
