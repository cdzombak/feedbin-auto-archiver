# Feedbin Auto-Archiver

*Auto-archiving for older unread posts in Feedbin, inspired by Pocket Casts’ configurable auto-archive feature.*

## Motivation

Someone in the microblogging/pro-RSS community — I forget who — recently posted something along the lines of “RSS shouldn’t be a source of stress. It’s okay to just mark it all as read and move on.”

The same is true of podcasts. To help with that, Pocket Casts has an auto-archive feature which is quite configurable on a per-feed basis, and that feature helps me avoid stress during times when I’ve fallen behind on podcasts.

With RSS, I find myself hesitant to mark a long list of entries as read; I can’t help but worry, “what if there’s something I really should read down there somewhere?”

So I built this tool. It's designed to be run on a periodic basis (2-4 times per day, perhaps). It will mark as read everything in your Feedbin account older than some time period (30 days, by default), and it allows configuring custom archiving rules both per-feed and by feed title patterns using regular expressions.

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

The rules file is a JSON file specifying per-feed maximum entry ages and entry count limits. The file is allowed to contain comments, allowing for clarity & easier maintenance. See `rules.sample.json` for an example.

#### Rule Types

The file supports two types of rules:

1. **Feed-specific rules** (`feed_specific`): Rules that apply to specific feed IDs
2. **Title regex rules** (`title_regex`): Rules that apply to feeds whose titles match regex patterns

Both rule types support two parameters:
- `max_age`: Archive entries older than this many days
- `keep_n`: Keep only the N most recent entries (archive the rest)

#### Rule Prioritization

**When multiple rules apply to a feed, the system uses the MOST AGGRESSIVE values** (smallest `max_age` and `keep_n`) across all matching rules. This ensures maximum archiving efficiency.

For example, if a feed matches both a feed-specific rule (`max_age: 7`) and a title regex rule (`max_age: 3`), the system will use `max_age: 3`.

#### Configuration Structure

```javascript
{
  "max_age": 30,  // Global default (overrides --max-age argument)
  
  // Rules for specific feed IDs
  "feed_specific": [
    {
      "feed_id": 450,
      "max_age": 7        // Archive after 7 days
    },
    {
      "feed_id": 789,
      "keep_n": 5         // Keep only 5 recent entries
    }
  ],
  
  // Rules based on feed title patterns
  "title_regex": [
    {
      "title_regex": "Daily",
      "max_age": 3        // Archive daily feeds after 3 days
    },
    {
      "title_regex": "Newsletter",
      "keep_n": 2         // Keep only 2 recent newsletter entries
    },
    {
      "title_regex": "(Breaking|Alert)",
      "max_age": 1        // Archive breaking news after 1 day
    }
  ]
}
```

Both `feed_specific` and `title_regex` sections are optional - you can use either or both as needed.

#### Title Regex Examples

Title regex rules use standard regular expression patterns to match feed titles. Here are some practical examples:

```javascript
"title_regex": [
  {
    "title_regex": "Daily",
    "max_age": 3                    // Any feed with "Daily" in the title
  },
  {
    "title_regex": "(?i)newsletter$",
    "keep_n": 2                     // Case-insensitive match for feeds ending with "newsletter"
  },
  {
    "title_regex": "(Breaking|Alert|Urgent)",
    "max_age": 1                    // Feeds containing any of these words
  },
  {
    "title_regex": "^Tech\\s+",
    "max_age": 5                    // Feeds starting with "Tech " (escaped space)
  },
  {
    "title_regex": "\\b(Blog|RSS)\\b",
    "keep_n": 10                    // Word boundaries ensure exact word matches
  }
]
```

Common regex patterns:
- `^pattern` - Matches feeds starting with "pattern"
- `pattern$` - Matches feeds ending with "pattern"  
- `(?i)pattern` - Case-insensitive matching
- `(word1|word2)` - Matches either "word1" or "word2"
- `\\b` - Word boundary (prevents partial word matches)

### "Ignore This Feed"

To avoid the archiver marking anything as read in a given feed, specify `999999999` for the feed’s `max_age`. (That is roughly 2.7 million years.)

This is the [maximum](https://docs.python.org/3/library/datetime.html#datetime.timedelta.max) number of days a Python `timedelta` object can represent.

## Usage

### Docker Usage

Invoke the script with `docker run`. To use a rules file, you will need to mount it into the container.

```shell
docker run --rm --env-file .env \
    -v /path/to/my_rules.json:/rules.json \
    cdzombak/feedbin-auto-archiver:1 \
    --rules-file /rules.json [--dry-run false] [OPTIONS]
```

### Local Python Usage

1. Activate the virtualenv: `. venv/bin/activate`
2. Run the script: `python feedbin_archiver.py --rules-file /path/to/my_rules.json [--dry-run false] [OPTIONS]`

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

Run `python feedbin_archiver.py list-feeds` to print a list of your Feedbin feeds, along with their IDs and titles. This is useful for:
- Finding feed IDs for `feed_specific` rules
- Understanding feed title patterns for writing `title_regex` rules

The output is grep-able. For example, to find feeds containing "newsletter", try `python feedbin_archiver.py list-feeds | grep -i newsletter`

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
