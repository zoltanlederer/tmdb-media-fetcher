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
    media_type is either 'movie' or 'tv'.
    """
    try:
        params = {'api_key': TMDB_API_KEY, 'external_source': 'imdb_id'}
        response = requests.get(TMDB_BASE_URL + '/find/' + imdb_id, params=params)
        response.raise_for_status()
        data = response.json()
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
    media_type should be either 'movie' or 'tv'.
    """
    try:
        url = f'{TMDB_BASE_URL}/{media_type}/{tmdb_id}'
        print(url)
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
        number_of_seasons = data['number_of_seasons']
        number_of_episodes = data['number_of_episodes']
        creators = []
        cast = []

        for person in data['created_by']:
            creators.append(person['name'])

        for person in data['credits']['cast'][:10]:
            cast.append(person['name'])

        creators = ', '.join(creators)
        cast = ', '.join(cast)

        return {'poster': poster, 'description': description, 'number_of_seasons': number_of_seasons, 'number_of_episodes': number_of_episodes, 'cast': cast, 'directors': creators}

    except KeyError as error:
        print(f'Missing field in TMDB response: {error}')
        return None
    

# def update_databse(conn, imdb_id, data):
#     """  """



def main():
    """ Connects the functions """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # return rows as dictionaries instead of tuple
    setup_database_columns(conn)
    titles = get_unenriched_titles(conn)
    print(f'Titles to enrich: {len(titles)}')
    print(dict(titles[0]))

    # tmdb_id, media_type = find_tmdb_id_by_imdb_id('tt0108778') # TV
    # print(tmdb_id, media_type)
    # data = fetch_tmdb_data(tmdb_id, media_type)
    # if media_type == 'movie':
    #     extra_data = parse_movie_data(data) # Movie
    # elif media_type == 'tv':
    #     extra_data = parse_tv_data(data) # TV
    
    # print(extra_data)

main()

# tmdb_id, media_type = find_tmdb_id_by_imdb_id('tt0415856') # Movie


# print(tmdb_id, media_type)




# data['credits']['crew'][0][]