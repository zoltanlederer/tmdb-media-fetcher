"""
TMDB Media Fetcher
Enriches a SQLite media database with cast, director, runtime,
and poster data by calling the TMDB API. Supports resume and logs
unmatched titles to a CSV file.
"""

import sqlite3
import requests
import time
import csv
import os
from datetime import datetime
from config import DB_PATH, TMDB_API_KEY, TMDB_BASE_URL

def setup_database_columns(conn):  # conn is the database connection passed in as a parameter
    """Add enrichment columns to the media table if they don't exist yet."""
    cursor = conn.cursor()  # cursor is the tool that sends SQL commands to the database
    # a list of tuples — each tuple contains the column name and its data type
    columns_to_add = [
        ('poster_path', 'TEXT'),
        ('cast', 'TEXT'),
    ]
    # loop through the list — each tuple is unpacked into column_name and column_type
    for column_name, column_type in columns_to_add:
        try:
            cursor.execute(f'ALTER TABLE media ADD COLUMN {column_name} {column_type}')  # add the new column to the database
            print(f'Column added: {column_name}')
        except sqlite3.OperationalError:
            pass  # column already exists — not a real error, just skip it
    conn.commit()  # save the changes to the database


def get_unenriched_titles(conn):
    """Fetch all rows from the database that haven't been enriched yet."""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM media WHERE poster_path IS NULL') # sends the SQL to the database
    return cursor.fetchall() # collects all the results and returns them as a list of tuples


def find_tmdb_id_by_imdb_id(imdb_id):
    """Look up a TMDB ID using an IMDB ID.

    Returns a tuple (tmdb_id, media_type) if found, or None if not found.
    media_type is either 'movie' or 'tv_show'.
    """
    try:
        params = {'api_key': TMDB_API_KEY, 'external_source': 'imdb_id'}
        response = requests.get(TMDB_BASE_URL + '/find/' + imdb_id, params=params)
        response.raise_for_status() # Raises HTTPError for 4xx/5xx status codes
        data = response.json() # Process data only if successful
        if data['movie_results']:
            return data['movie_results'][0]['id'], 'movie'
        if data['tv_results']:
            return data['tv_results'][0]['id'], 'tv'
        return None
        
    except requests.exceptions.RequestException as error:
        print(f"Something went wrong: {error}")
        return None


def fetch_tmdb_data(tmdb_id, media_type):
    """Fetch movie or TV show data from TMDB including credits in one API call.

    Returns the full API response as a dictionary, or None if the request fails.
    media_type should be either 'movie' or 'tv_show'.
    """
    try:
        media_type_fix = 'tv' if media_type == 'tv_show' else 'movie'
        url = f'{TMDB_BASE_URL}/{media_type_fix}/{tmdb_id}'
        params = {'api_key': TMDB_API_KEY, 'append_to_response': 'credits'}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as error:
        print(f"Something went wrong: {error}")
        return None


def parse_movie_data(data):
    """Extract poster, runtime, description, director and top 10 cast members into a dictionary."""
    try:
        poster = data['poster_path']
        runtime = data['runtime']
        description = data['overview']
        directors = []
        cast = []

        for person in data['credits']['crew']:
            if person['job'] == 'Director':                
                directors.append(person['name'])

        for person in data['credits']['cast'][:10]:
            cast.append(person['name'])

        directors = ', '.join(directors)
        cast = ', '.join(cast)

        return {'poster': poster, 'runtime': runtime, 'description': description, 'cast': cast, 'directors': directors}

    except KeyError as error:
        print(f'Missing field in TMDB response: {error}')
        return None


def parse_tv_data(data):
    """Extract poster, number of seasons and episodes, description, creators and top 10 cast members into a dictionary."""
    try:
        poster = data['poster_path']
        description = data['overview']
        number_of_seasons = data.get('number_of_seasons') # .get() returns None if the key doesn't exist instead of raising a KeyError
        number_of_episodes = data.get('number_of_episodes')
        creators = []
        cast = []

        for person in data.get('created_by', []): # The [] is the default value — if created_by doesn't exist, the loop runs over an empty list and creators stays empty. No crash, no KeyError
            creators.append(person['name'])

        for person in data['credits']['cast'][:10]:
            cast.append(person['name'])

        creators = ', '.join(creators)
        cast = ', '.join(cast)

        return {'poster': poster, 'description': description, 'number_of_seasons': number_of_seasons, 'number_of_episodes': number_of_episodes, 'cast': cast, 'directors': creators}

    except KeyError as error:
        print(f'Missing field in TMDB response: {error}')
        return None
    

def update_database(conn, imdb_id, media_type, data):
    """Write enriched TMDB data back into the database for a single title.
    Handles movies and TV shows separately as they have different fields.
    """
    if media_type == 'movie':
        update_statement = 'UPDATE media SET poster_path = ?, `cast` = ?, directors = ?, runtime_mins = ?, description = ? WHERE imdb_id = ?'
        params = (data['poster'], data['cast'], data['directors'], data['runtime'], data['description'], imdb_id)
    elif media_type == 'tv_show':
        update_statement = 'UPDATE media SET poster_path = ?, `cast` = ?, directors = ?, number_of_seasons = ?, number_of_episodes = ?, description = ? WHERE imdb_id = ?'
        params = (data['poster'], data['cast'], data['directors'], data['number_of_seasons'], data['number_of_episodes'], data['description'], imdb_id)
    cursor = conn.cursor()
    cursor.execute(update_statement, params) # execute a parameterised query — values passed as a tuple, ? as placeholders
    conn.commit() # permanently save the changes to the database


def log_unmatched(title, reason):
    """Log a title that couldn't be enriched to unmatched.csv, including the reason and timestamp."""
    try:
        file_exists = os.path.exists('./data/unmatched.csv')
        with open('./data/unmatched.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)            
            if not file_exists:
                writer.writerow(['title', 'reason', 'timestamp']) # write header row only when the file is created for the first time    
            writer.writerow([title, reason, datetime.now()])
    except PermissionError:
        print(f'Permission denied. Could not write to unmatched.csv')
    except OSError as error:
        print(f'Could not create file: {error}')
    except Exception:
        print('Something went wrong while writing the file.')


def main():
    """Main function — loops through unenriched titles and enriches them via the TMDB API."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # return rows as dictionaries instead of tuple
    setup_database_columns(conn) # Add enrichment columns to the media table if they don't exist yet
    titles = get_unenriched_titles(conn) # Fetch all rows from the database that haven't been enriched yet
    print(f'Titles to enrich: {len(titles)}')

    for index, title in enumerate(titles, start=1):
        if title['tmdb_id'] is not None:
            data = fetch_tmdb_data(title['tmdb_id'], title['type']) # fetch movie or TV show data from TMDB including credits in one API call.
            if data is None:
                log_unmatched(title['title'], 'fetch_failed') # log a title that couldn't be enriched to unmatched.csv
                continue # skips the rest of the loop for that title and moves to the next one
        elif title['imdb_id'] is not None:
            result = find_tmdb_id_by_imdb_id(title['imdb_id'])
            if result is None:
                log_unmatched(title['title'], 'no_match')
                continue
            tmdb_id, media_type = result
            data = fetch_tmdb_data(tmdb_id, media_type)
            if data is None:
                log_unmatched(title['title'], 'fetch_failed')
                continue # skips the rest of the loop for that title and moves to the next one
        else:
            log_unmatched(title['title'], 'no_match')
            continue

        if title['type'] == 'movie':
            extra_data = parse_movie_data(data) # extract the extra/missing information from the data
            if extra_data is None:
                log_unmatched(title['title'], 'parse_failed')
                continue
        elif title['type'] == 'tv_show':
            extra_data = parse_tv_data(data) # extract the extra/missing information from the data
            if extra_data is None:
                log_unmatched(title['title'], 'parse_failed')
                continue

        time.sleep(0.25) # wait 250ms between calls
        
        update_database(conn, title['imdb_id'], title['type'], extra_data) # write enriched TMDB data back into the database for a single title
        print(f"[{index}/{len(titles)}] Enriched: {title['title']}")

    conn.close() # Close the connection safely
    print("Done.") 

main()