# TMDB Media Fetcher

Python CLI tool that enriches a SQLite media database via the TMDB API. Adds missing metadata — cast, directors, runtime, poster path, and description — to an existing database of 3,000+ movies and TV shows. Supports rate limiting and resume so the batch process can be safely interrupted and continued.

## Requirements

- Python 3.x
- requests

## Installation

#### Clone the repo:
```bash
git clone https://github.com/zoltanlederer/tmdb-media-fetcher.git
cd tmdb-media-fetcher
```

#### Create and activate a virtual environment:

Mac/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows
```bash
python3 -m venv .venv
.venv\Scripts\activate
```

#### Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Copy `config.example.py` to `config.py`. Then edit `config.py` and fill in your TMDB API key and the path to your SQLite database.  
You can get a free API key at [themoviedb.org](https://www.themoviedb.org/settings/api).

> **Note:** This script expects an existing SQLite database with a `media` table. It was built as part of a media library pipeline — see [sql-movie-explorer](https://github.com/zoltanlederer/sql-movie-explorer) for the project that creates the database.

## Usage

```bash
python3 tmdb_fetcher.py
```

## Examples

```bash
python3 tmdb_fetcher.py   

Titles to enrich: 3459
[1/3459] Enriched: Godzilla vs. Kong
[2/3459] Enriched: Transformers: Rise of the Beasts
[3/3459] Enriched: Ant-Man and the Wasp
[4/3459] Enriched: F9: The Fast Saga
[5/3459] Enriched: Blue Planet II
...
[3456/3459] Enriched: Magnum P.I.
[3457/3459] Enriched: God Friended Me
[3458/3459] Enriched: The King of Kings
[3459/3459] Enriched: Jumanji: The Next Level
Done.
```

#### unmatched.csv sample:
| title | reason | timestamp |
|-------|------|---------------|
| Spider-Man | fetch_failed | 2026-05-09 15:46:43 |
| A Charlie Brown Christmas | parse_failed | 2026-05-09 15:47:45 |
| Die Hart | no_match | 2026-05-09 15:53:37 |


## Credits
[The Movie Database (TMDB) API](https://www.themoviedb.org)