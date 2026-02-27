import sqlite3
import requests
import time
import sys
import os
from dotenv import load_dotenv

load_dotenv()

DB_FILE = os.getenv("DB_FILE", "soccer_management.db")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "api-football-v1.p.rapidapi.com")

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

# League IDs for top 5 European Leagues
LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61
}

SEASONS = [2019, 2020, 2021, 2022, 2023]


def connect_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def insert_league(league_id, league_name):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT League_ID FROM League WHERE League_ID=?", (league_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO League (League_ID, League_Name) VALUES (?, ?)",
                  (league_id, league_name))
    conn.commit()
    conn.close()


def insert_season(year_start, year_end):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT Season_ID FROM Season WHERE Year_Start=? AND Year_End=?",
              (year_start, year_end))
    row = c.fetchone()
    if row:
        season_id = row[0]
    else:
        c.execute("INSERT INTO Season (Year_Start, Year_End) VALUES (?, ?)",
                  (year_start, year_end))
        season_id = c.lastrowid
    conn.commit()
    conn.close()
    return season_id


def insert_team(team_id, team_name, coach, league_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT Team_ID FROM Team WHERE Team_ID=?", (team_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO Team (Team_ID, Team_Name, Coach, League_ID) VALUES (?, ?, ?, ?)",
                  (team_id, team_name, coach, league_id))
    conn.commit()
    conn.close()


def insert_player(player_id, player_name, position):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT Player_ID FROM Player WHERE Player_ID=?", (player_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO Player (Player_ID, Player_Name, Position) VALUES (?, ?, ?)",
                  (player_id, player_name, position))
    conn.commit()
    conn.close()


def link_player_to_team_season(team_id, player_id, season_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT Team_Player_Season_ID FROM Team_Player_Season WHERE Team_ID=? AND Player_ID=? AND Season_ID=?",
              (team_id, player_id, season_id))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO Team_Player_Season (Team_ID, Player_ID, Season_ID) VALUES (?, ?, ?)",
                  (team_id, player_id, season_id))
    conn.commit()
    conn.close()


def insert_match(match_id, home_team_id, away_team_id, date_str, home_score, away_score, season_id, league_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT Match_ID FROM Match WHERE Match_ID=?", (match_id,))
    row = c.fetchone()
    if not row:
        c.execute("""INSERT INTO Match (Match_ID, Home_Team_ID, Away_Team_ID, Date, Home_Score, Away_Score, Season_ID, League_ID) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (match_id, home_team_id, away_team_id, date_str, home_score, away_score, season_id, league_id))
    conn.commit()
    conn.close()


def get_season_id_for_year(year_start):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT Season_ID FROM Season WHERE Year_Start=? AND Year_End=?",
              (year_start, year_start+1))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def fetch_all_players_for_team_season(team_id, season_year):
    url = "https://api-football-v1.p.rapidapi.com/v3/players"
    page = 1
    all_players = []

    while True:
        params = {"team": team_id, "season": season_year, "page": page}
        r = requests.get(url, headers=headers, params=params)

        if r.status_code != 200:
            print(
                f"Failed to fetch players for team {team_id}, season {season_year}, page {page}. Status code: {r.status_code}")
            break

        data = r.json()
        players = data.get("response", [])
        if not players:
            # No more players on this page
            break

        all_players.extend(players)

        # Check pagination
        paging = data.get("paging", {})
        current_page = paging.get("current", 1)
        total_pages = paging.get("total", 1)

        print(
            f"Fetched page {current_page}/{total_pages} for team {team_id}, season {season_year}: total players so far {len(all_players)}")

        if current_page >= total_pages:
            # No more pages
            break

        page += 1

    return all_players


def fetch_and_insert_players_for_team_season(team_id, season_year, player_data):
    # player_data is the response for a single player from the API
    player_info = player_data["player"]
    player_id = player_info["id"]
    player_name = player_info["name"]

    stats = player_data.get("statistics", [])
    position = "Unknown"
    if stats and len(stats) > 0:
        position = stats[0]["games"].get("position", "Unknown")

    insert_player(player_id, player_name, position)

    season_id = get_season_id_for_year(season_year)
    if not season_id:
        return

    # Player could appear for multiple teams in the season according to stats
    teams_for_season = set()
    for stat_entry in stats:
        stat_team_id = stat_entry["team"]["id"]
        teams_for_season.add(stat_team_id)

    for tid in teams_for_season:
        link_player_to_team_season(tid, player_id, season_id)


def fetch_and_insert_teams_for_league_and_season(league_id, season_year):
    # Insert league info if not present
    league_name = None
    for name, lid in LEAGUES.items():
        if lid == league_id:
            league_name = name
            break
    if league_name is None:
        league_name = f"League_{league_id}"

    insert_league(league_id, league_name)

    url = "https://api-football-v1.p.rapidapi.com/v3/teams"
    params = {"league": league_id, "season": season_year}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        print(
            f"Failed to fetch teams for league {league_id}, season {season_year}, status code: {r.status_code}")
        return []

    data = r.json()
    teams = data.get("response", [])
    team_ids = []
    for t in teams:
        team_info = t["team"]
        tid = team_info["id"]
        tname = team_info["name"]
        coach = "Unknown"
        insert_team(tid, tname, coach, league_id)
        team_ids.append(tid)
    return team_ids


def fetch_and_insert_fixtures_for_league_season(league_id, season_year):
    season_id = insert_season(season_year, season_year+1)
    # Insert league if not present
    league_name = None
    for name, lid in LEAGUES.items():
        if lid == league_id:
            league_name = name
            break
    if league_name is None:
        league_name = f"League_{league_id}"

    insert_league(league_id, league_name)

    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"league": league_id, "season": season_year}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        print(
            f"Failed to fetch fixtures for league {league_id}, season {season_year}, status code: {r.status_code}")
        return

    data = r.json()
    fixtures = data.get("response", [])
    for f in fixtures:
        fixture = f["fixture"]
        teams = f["teams"]
        goals = f["goals"]

        match_id = fixture["id"]
        home_team_id = teams["home"]["id"]
        away_team_id = teams["away"]["id"]
        date_str = fixture["date"]
        home_score = goals["home"]
        away_score = goals["away"]

        insert_match(match_id, home_team_id, away_team_id,
                     date_str, home_score, away_score, season_id, league_id)

        time.sleep(0.2)


def main():
    # Fetch data for each league and season
    for league_name, league_id in LEAGUES.items():
        for year_start in SEASONS:
            print(
                f"Fetching fixtures for {league_name} in the {year_start}/{year_start+1} season...")
            fetch_and_insert_fixtures_for_league_season(league_id, year_start)

            print(
                f"Fetching teams for {league_name} {year_start}/{year_start+1}...")
            season_id = insert_season(year_start, year_start+1)
            team_ids = fetch_and_insert_teams_for_league_and_season(
                league_id, year_start)

            # Fetch players for each team & season with pagination
            for tid in team_ids:
                players = fetch_all_players_for_team_season(tid, year_start)
                for p_data in players:
                    fetch_and_insert_players_for_team_season(
                        tid, year_start, p_data)
                    time.sleep(0.1)

            time.sleep(1)  # A short break between seasons

    print("All requested competitions and seasons have been fetched and inserted.")


if __name__ == "__main__":
    main()


