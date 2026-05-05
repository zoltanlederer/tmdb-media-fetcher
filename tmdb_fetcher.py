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

