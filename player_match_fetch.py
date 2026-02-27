import sqlite3
import requests
import time
import sys
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
DB_FILE = os.getenv("DB_FILE", "soccer_management.db")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "api-football-v1.p.rapidapi.com")

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

# Setup logging
logging.basicConfig(filename='populate_player_match_participation.log', 
                    level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

def connect_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        sys.exit(1)

def fetch_lineups(match_id):
    """
    Fetch lineups for a given match using the /fixtures/lineups endpoint.
    """
    url = f"https://{RAPIDAPI_HOST}/v3/fixtures/lineups"
    params = {"fixture": match_id}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            logging.warning(f"Failed to fetch lineups for Match_ID {match_id}. Status code: {response.status_code}")
            return None
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Request exception for Match_ID {match_id}: {e}")
        return None

def insert_player_match_participation(conn, match_id, player_id, minutes_played=90, goals=0, assists=0):
    """
    Insert a record into Player_Match_Participation table.
    Defaults minutes_played to 90 as lineups imply full match participation.
    Goals and assists are set to 0 due to lack of detailed statistics.
    """
    try:
        cursor = conn.cursor()
        # Check if the record already exists
        cursor.execute("""
            SELECT Player_Match_ID FROM Player_Match_Participation
            WHERE Match_ID = ? AND Player_ID = ?
        """, (match_id, player_id))
        row = cursor.fetchone()
        if row:
            logging.info(f"Record already exists for Match_ID {match_id}, Player_ID {player_id}. Skipping.")
            return
        
        # Insert the new record
        cursor.execute("""
            INSERT INTO Player_Match_Participation (Match_ID, Player_ID, Minutes_Played, Goals, Assists)
            VALUES (?, ?, ?, ?, ?)
        """, (match_id, player_id, minutes_played, goals, assists))
        conn.commit()
        logging.info(f"Inserted Player_Match_Participation for Match_ID {match_id}, Player_ID {player_id}.")
    except sqlite3.Error as e:
        logging.error(f"SQLite error while inserting for Match_ID {match_id}, Player_ID {player_id}: {e}")

def process_match(conn, match_id):
    """
    Process a single match to populate Player_Match_Participation.
    """
    logging.info(f"Processing Match_ID {match_id}")
    data = fetch_lineups(match_id)
    if not data:
        logging.warning(f"No data returned for Match_ID {match_id}")
        return

    response = data.get("response", [])
    if not response:
        logging.warning(f"No response data for Match_ID {match_id}")
        return

    for team_entry in response:
        # Extract players from startXI and substitutes
        for player_group in ["startXI", "substitutes"]:
            players = team_entry.get(player_group, [])
            for player_entry in players:
                player_info = player_entry.get("player", {})
                player_id = player_info.get("id")
                if not player_id:
                    logging.warning(f"Player ID missing in Match_ID {match_id}, Team {team_entry.get('team', {}).get('name')}. Skipping player entry.")
                    continue
                # Insert with default statistics
                insert_player_match_participation(conn, match_id, player_id)
    # Respect API rate limits
    time.sleep(0.2)  # Adjust based on API's rate limit policy

def main():
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch all Match_IDs that are not yet processed
    cursor.execute("""
        SELECT Match_ID FROM Match
        WHERE Match_ID NOT IN (SELECT DISTINCT Match_ID FROM Player_Match_Participation)
    """)
    matches = cursor.fetchall()

    total_matches = len(matches)
    logging.info(f"Total matches to process: {total_matches}")
    print(f"Total matches to process: {total_matches}")

    for idx, (match_id,) in enumerate(matches, start=1):
        print(f"Processing match {idx}/{total_matches}: Match_ID = {match_id}")
        logging.info(f"Processing match {idx}/{total_matches}: Match_ID = {match_id}")
        process_match(conn, match_id)

    conn.close()
    logging.info("Player_Match_Participation table has been populated.")
    print("Player_Match_Participation table has been populated.")

if __name__ == "__main__":
    main()
