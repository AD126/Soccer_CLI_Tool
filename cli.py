import sqlite3
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_FILE = os.getenv("DB_FILE", "soccer_management.db")

def connect_to_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to the database: {e}")
        sys.exit(1)


def show_teams(conn):
    query = "SELECT Team_ID, Team_Name FROM Team"
    cursor = conn.cursor()
    cursor.execute(query)
    teams = cursor.fetchall()
    print("\nTeams:")
    for team in teams:
        print(f"ID: {team[0]}, Name: {team[1]}")
    print()


def search_players_by_name(conn):
    """Search for players with optional filters and richer context."""

    print("Search players by name. You can refine the results using the optional filters below.")
    raw_input = input(
        "Enter the player name, partial name, or '#PlayerID': ").strip()

    if not raw_input:
        print("Search term cannot be empty.\n")
        return

    cursor = conn.cursor()

    # Detect direct Player_ID queries using prefixes like #1234 or id:1234
    player_id_lookup = None
    if raw_input.lower().startswith("id:"):
        id_part = raw_input[3:].strip()
        if id_part.isdigit():
            player_id_lookup = int(id_part)
    elif raw_input.startswith("#"):
        id_part = raw_input[1:].strip()
        if id_part.isdigit():
            player_id_lookup = int(id_part)
    elif raw_input.isdigit():
        player_id_lookup = int(raw_input)

    conditions = []
    params = []

    if player_id_lookup is not None:
        conditions.append("p.Player_ID = ?")
        params.append(player_id_lookup)
    else:
        tokens = [token for token in raw_input.split() if token]
        for token in tokens:
            conditions.append("p.Player_Name LIKE ?")
            params.append(f"%{token}%")

    position_filter = input("Filter by position (optional): ").strip()
    if position_filter:
        conditions.append("p.Position LIKE ?")
        params.append(f"%{position_filter}%")

    team_filter = input("Filter by team name (optional): ").strip()
    if team_filter:
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM Team_Player_Season tps_team
                JOIN Team t_team ON tps_team.Team_ID = t_team.Team_ID
                WHERE tps_team.Player_ID = p.Player_ID
                  AND t_team.Team_Name LIKE ?
            )
        """)
        params.append(f"%{team_filter}%")

    league_filter = input("Filter by league name (optional): ").strip()
    if league_filter:
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM Team_Player_Season tps_league
                JOIN Team t_league ON tps_league.Team_ID = t_league.Team_ID
                JOIN League l_league ON COALESCE(tps_league.League_ID, t_league.League_ID) = l_league.League_ID
                WHERE tps_league.Player_ID = p.Player_ID
                  AND l_league.League_Name LIKE ?
            )
        """)
        params.append(f"%{league_filter}%")

    season_filter = input(
        "Filter by season start year (optional, e.g., 2022): ").strip()
    if season_filter:
        if not season_filter.isdigit():
            print("Season start year must be numeric.\n")
            return
        season_year = int(season_filter)
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM Team_Player_Season tps_season
                JOIN Season s_season ON tps_season.Season_ID = s_season.Season_ID
                WHERE tps_season.Player_ID = p.Player_ID
                  AND s_season.Year_Start = ?
                  AND s_season.Year_End = ?
            )
        """)
        params.extend([season_year, season_year + 1])

    if not conditions:
        print("Please provide at least a name fragment or a Player ID.\n")
        return

    where_clause = " WHERE " + " AND ".join(conditions)

    count_query = f"""
    SELECT COUNT(DISTINCT p.Player_ID)
    FROM Player p
    {where_clause}
    """
    cursor.execute(count_query, params)
    total_matches = cursor.fetchone()[0]

    if total_matches == 0:
        print("\nNo players matched your search criteria.\n")
        return

    limit = 50

    # Use CTEs to pre-aggregate team and league history for cleaner formatting
    search_query = f"""
    WITH team_history AS (
        SELECT inner_th.Player_ID, GROUP_CONCAT(inner_th.TeamSeason, '; ') AS TeamHistory
        FROM (
            SELECT DISTINCT tps.Player_ID,
                            t.Team_Name || ' (' || s.Year_Start || '/' || s.Year_End || ')' AS TeamSeason
            FROM Team_Player_Season tps
            JOIN Team t ON tps.Team_ID = t.Team_ID
            JOIN Season s ON tps.Season_ID = s.Season_ID
        ) AS inner_th
        GROUP BY inner_th.Player_ID
    ),
    league_history AS (
        SELECT inner_lh.Player_ID, GROUP_CONCAT(inner_lh.LeagueName, '; ') AS Leagues
        FROM (
            SELECT DISTINCT tps.Player_ID,
                            l.League_Name AS LeagueName
            FROM Team_Player_Season tps
            JOIN Team t ON tps.Team_ID = t.Team_ID
            JOIN League l ON COALESCE(tps.League_ID, t.League_ID) = l.League_ID
        ) AS inner_lh
        GROUP BY inner_lh.Player_ID
    )
    SELECT
        p.Player_ID,
        p.Player_Name,
        COALESCE(p.Position, 'N/A') AS Position,
        COALESCE(team_history.TeamHistory, 'No recorded teams') AS TeamHistory,
        COALESCE(league_history.Leagues, 'Unknown') AS Leagues
    FROM Player p
    LEFT JOIN team_history ON p.Player_ID = team_history.Player_ID
    LEFT JOIN league_history ON p.Player_ID = league_history.Player_ID
    {where_clause}
    ORDER BY p.Player_Name COLLATE NOCASE
    LIMIT ?
    """

    query_params = params + [limit]
    cursor.execute(search_query, query_params)
    players = cursor.fetchall()

    width_id = 10
    width_name = 30
    width_pos = 12
    width_team = 45
    width_league = 30

    def truncate(value, width):
        value = value or ""
        return value if len(value) <= width else value[:width - 3] + "..."

    print("\nPlayers Found:")
    header = (f"{'Player ID':<{width_id}}"
              f"{'Name':<{width_name}}"
              f"{'Position':<{width_pos}}"
              f"{'Teams':<{width_team}}"
              f"{'Leagues':<{width_league}}")
    print(header)
    print("-" * (width_id + width_name + width_pos + width_team + width_league))

    for player in players:
        pid, name, position, teams, leagues = player
        line = (f"{str(pid):<{width_id}}"
                f"{truncate(name, width_name):<{width_name}}"
                f"{truncate(position, width_pos):<{width_pos}}"
                f"{truncate(teams, width_team):<{width_team}}"
                f"{truncate(leagues, width_league):<{width_league}}")
        print(line)

    if total_matches > limit:
        print(
            f"\nShowing the first {limit} of {total_matches} matching players. Refine your filters to narrow the results.\n")
    else:
        print()


def show_all_matches(conn):
    query = """
    SELECT 
        m.Match_ID, 
        th.Team_Name AS Home_Team_Name, 
        ta.Team_Name AS Away_Team_Name, 
        m.Date, 
        m.Home_Score, 
        m.Away_Score,
        s.Year_Start,
        s.Year_End
    FROM Match m
    JOIN Team th ON m.Home_Team_ID = th.Team_ID
    JOIN Team ta ON m.Away_Team_ID = ta.Team_ID
    JOIN Season s ON m.Season_ID = s.Season_ID
    """
    cursor = conn.cursor()
    cursor.execute(query)
    matches = cursor.fetchall()

    from datetime import datetime

    width_id = 10
    width_team = 35
    width_date = 12
    width_score = 7
    width_season = 10

    print("\nMatches:")
    header = (f"{'Match ID':<{width_id}}"
              f"{'Home Team':<{width_team}}"
              f"{'Away Team':<{width_team}}"
              f"{'Date':<{width_date}}"
              f"{'Score':<{width_score}}"
              f"{'Season':<{width_season}}")
    print(header)
    print("-" * (width_id + width_team*2 + width_date + width_score + width_season))

    for match in matches:
        match_id = match[0]
        home_team = match[1]
        away_team = match[2]
        date_str = match[3]
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        date_only = dt.strftime("%Y-%m-%d")
        home_score = match[4]
        away_score = match[5]
        year_start = match[6]
        year_end = match[7]
        season_str = f"{year_start}/{year_end}"
        score_str = f"{home_score}-{away_score}"

        line = (f"{str(match_id):<{width_id}}"
                f"{home_team:<{width_team}}"
                f"{away_team:<{width_team}}"
                f"{date_only:<{width_date}}"
                f"{score_str:<{width_score}}"
                f"{season_str:<{width_season}}")
        print(line)
    print()


def view_fixtures_for_season(conn):
    start_year = input(
        "Enter the start year of the season (e.g., 2019 for 2019/2020): ").strip()
    if not start_year.isdigit():
        print("Invalid year. Please enter a numeric year.")
        return
    start_year = int(start_year)

    query = """
    SELECT 
        m.Match_ID, 
        th.Team_Name AS Home_Team_Name, 
        ta.Team_Name AS Away_Team_Name, 
        m.Date, 
        m.Home_Score, 
        m.Away_Score,
        s.Year_Start,
        s.Year_End
    FROM Match m
    JOIN Team th ON m.Home_Team_ID = th.Team_ID
    JOIN Team ta ON m.Away_Team_ID = ta.Team_ID
    JOIN Season s ON m.Season_ID = s.Season_ID
    WHERE s.Year_Start = ? AND s.Year_End = ?
    """
    cursor = conn.cursor()
    cursor.execute(query, (start_year, start_year+1))
    matches = cursor.fetchall()

    if matches:
        print_formatted_matches(matches)
    else:
        print(
            f"No fixtures found for the {start_year}/{start_year+1} season.\n")


def view_fixtures_for_team_season(conn):
    team_name = input("Enter Team Name: ").strip()
    start_year = input(
        "Enter the start year of the season (e.g., 2019 for 2019/2020): ").strip()

    if not start_year.isdigit():
        print("Invalid input. Season Year must be an integer.")
        return

    start_year = int(start_year)

    # Get Team_ID
    c = conn.cursor()
    c.execute("SELECT Team_ID FROM Team WHERE Team_Name LIKE ?",
              (f"%{team_name}%",))
    row = c.fetchone()
    if not row:
        print(f"No team found with the name '{team_name}'")
        return
    team_id = row[0]

    # Get Season_ID
    c.execute("SELECT Season_ID FROM Season WHERE Year_Start=? AND Year_End=?",
              (start_year, start_year+1))
    srow = c.fetchone()
    if not srow:
        print(f"No season found for {start_year}/{start_year+1}.")
        return
    season_id = srow[0]

    query = """
    SELECT Match_ID, th.Team_Name AS Home_Team_Name, ta.Team_Name AS Away_Team_Name, Date, Home_Score, Away_Score, s.Year_Start, s.Year_End
    FROM Match
    JOIN Team th ON Match.Home_Team_ID = th.Team_ID
    JOIN Team ta ON Match.Away_Team_ID = ta.Team_ID
    JOIN Season s ON Match.Season_ID = s.Season_ID
    WHERE (Home_Team_ID = ? OR Away_Team_ID = ?) AND s.Season_ID = ?
    """
    c.execute(query, (team_id, team_id, season_id))
    matches = c.fetchall()

    if matches:
        print_formatted_matches(matches)
    else:
        print(
            f"No fixtures found for '{team_name}' in the {start_year}/{start_year+1} season.\n")


def print_formatted_matches(matches):
    from datetime import datetime
    width_id = 10
    width_team = 20
    width_date = 12
    width_score = 7
    width_season = 10

    print("\nMatches:")
    header = (f"{'Match ID':<{width_id}}"
              f"{'Home Team':<{width_team}}"
              f"{'Away Team':<{width_team}}"
              f"{'Date':<{width_date}}"
              f"{'Score':<{width_score}}"
              f"{'Season':<{width_season}}")
    print(header)
    print("-" * (width_id + width_team*2 + width_date + width_score + width_season))

    for match in matches:
        match_id = match[0]
        home_team = match[1]
        away_team = match[2]
        date_str = match[3]
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        date_only = dt.strftime("%Y-%m-%d")
        home_score = match[4]
        away_score = match[5]
        y_start = match[6]
        y_end = match[7]
        season_str = f"{y_start}/{y_end}"
        score_str = f"{home_score}-{away_score}"

        line = (f"{str(match_id):<{width_id}}"
                f"{home_team:<{width_team}}"
                f"{away_team:<{width_team}}"
                f"{date_only:<{width_date}}"
                f"{score_str:<{width_score}}"
                f"{season_str:<{width_season}}")
        print(line)
    print()


def view_player_teams_last_5_seasons(conn):
    player_name = input("Enter the player's name: ").strip()
    c = conn.cursor()
    c.execute("SELECT Player_ID FROM Player WHERE Player_Name LIKE ?",
              (f"%{player_name}%",))
    row = c.fetchone()
    if not row:
        print(f"No player found with name containing '{player_name}'.")
        return
    player_id = row[0]

    seasons = [2019, 2020, 2021, 2022, 2023]
    c.execute(
        "SELECT Season_ID, Year_Start, Year_End FROM Season WHERE Year_Start IN (2019,2020,2021,2022,2023)")
    season_rows = c.fetchall()
    season_ids = {r[1]: r[0] for r in season_rows}

    team_set = set()
    for s_year in seasons:
        if s_year in season_ids:
            s_id = season_ids[s_year]
            c.execute("""
                SELECT DISTINCT T.Team_Name, S.Year_Start, S.Year_End
                FROM Team_Player_Season TPS
                JOIN Team T ON TPS.Team_ID = T.Team_ID
                JOIN Season S ON TPS.Season_ID = S.Season_ID
                WHERE TPS.Player_ID = ? AND TPS.Season_ID = ?
            """, (player_id, s_id))
            results = c.fetchall()
            for r in results:
                team_set.add((r[0], r[1], r[2]))

    if not team_set:
        print("This player didn't play for any teams in the last 5 seasons.")
        return

    width_team = 25
    width_season = 12
    print("\nTeams the player played for in the last 5 seasons:")
    header = f"{'Team Name':<{width_team}}{'Season':<{width_season}}"
    print(header)
    print("-" * (width_team + width_season))

    for (team_name, y_start, y_end) in team_set:
        season_str = f"{y_start}/{y_end}"
        line = f"{team_name:<{width_team}}{season_str:<{width_season}}"
        print(line)
    print()


def view_player_current_team_2023_24(conn):
    player_name = input("Enter the player's name: ").strip()

    c = conn.cursor()
    c.execute("SELECT Player_ID FROM Player WHERE Player_Name LIKE ?",
              (f"%{player_name}%",))
    row = c.fetchone()
    if not row:
        print(f"No player found with name containing '{player_name}'.")
        return
    player_id = row[0]

    
    c.execute("SELECT Season_ID FROM Season WHERE Year_Start=2023 AND Year_End=2024")
    srow = c.fetchone()
    if not srow:
        print("The 2023/2024 season is not in the database.")
        return
    season_id_2324 = srow[0]

    # Find player's team for that season
    c.execute("""
        SELECT T.Team_Name
        FROM Team_Player_Season TPS
        JOIN Team T ON TPS.Team_ID = T.Team_ID
        WHERE TPS.Player_ID = ? AND TPS.Season_ID = ?
    """, (player_id, season_id_2324))
    row = c.fetchone()

    if not row:
        print("This player does not have a recorded team for the 2023/2024 season.")
    else:
        print(f"In the 2023/2024 season, the player is in: {row[0]}")
    print()


def view_fixtures_for_league_season(conn):
    league_name = input("Enter the league name: ").strip()
    start_year = input(
        "Enter the start year of the season (e.g., 2019 for 2019/2020): ").strip()

    if not start_year.isdigit():
        print("Invalid year.")
        return
    start_year = int(start_year)

    c = conn.cursor()
    # Get League_ID
    c.execute("SELECT League_ID FROM League WHERE League_Name LIKE ?",
              (f"%{league_name}%",))
    lrow = c.fetchone()
    if not lrow:
        print(f"No league found with name containing '{league_name}'.")
        return
    league_id = lrow[0]

    # Get Season_ID
    c.execute("SELECT Season_ID FROM Season WHERE Year_Start=? AND Year_End=?",
              (start_year, start_year+1))
    srow = c.fetchone()
    if not srow:
        print(f"No season found for {start_year}/{start_year+1}.")
        return
    season_id = srow[0]

    # Query matches for the specified league and season
    query = """
    SELECT 
        m.Match_ID, 
        th.Team_Name AS Home_Team_Name, 
        ta.Team_Name AS Away_Team_Name, 
        m.Date, 
        m.Home_Score, 
        m.Away_Score,
        s.Year_Start,
        s.Year_End
    FROM Match m
    JOIN Team th ON m.Home_Team_ID = th.Team_ID
    JOIN Team ta ON m.Away_Team_ID = ta.Team_ID
    JOIN Season s ON m.Season_ID = s.Season_ID
    WHERE m.League_ID = ? AND m.Season_ID = ?
    ORDER BY m.Date DESC
    """
    c.execute(query, (league_id, season_id))
    matches = c.fetchall()

    if not matches:
        print(
            f"No fixtures found for {league_name} in the {start_year}/{start_year+1} season.")
        return

    width_id = 10
    width_team = 35
    width_date = 12
    width_score = 10
    width_season = 12

    print(
        f"\nFixtures for {league_name} in the {start_year}/{start_year+1} season:")
    header = (f"{'Match ID':<{width_id}}"
              f"{'Home Team':<{width_team}}"
              f"{'Away Team':<{width_team}}"
              f"{'Date':<{width_date}}"
              f"{'Score':<{width_score}}"
              f"{'Season':<{width_season}}")
    print(header)
    print("-" * (width_id + width_team*2 + width_date + width_score + width_season))

    for match in matches:
        match_id, home_team, away_team, date_str, home_score, away_score, y_start, y_end = match
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
            date_only = dt.strftime("%Y-%m-%d")
        except ValueError:
            date_only = date_str  # If timezone info is missing

        score_str = f"{home_score}-{away_score}" if home_score is not None and away_score is not None else "N/A"
        season_str = f"{y_start}/{y_end}"

        print(f"{match_id:<10} {home_team:<25} {away_team:<25} {date_only:<12} {score_str:<10} {season_str:<12}")
    print()


def view_teams_in_league_season(conn):
    league_name = input("Enter the league name: ").strip()
    start_year = input(
        "Enter the start year of the season (e.g., 2019 for 2019/2020): ").strip()

    if not start_year.isdigit():
        print("Invalid year.")
        return
    start_year = int(start_year)

    c = conn.cursor()
    c.execute("SELECT League_ID FROM League WHERE League_Name LIKE ?",
              (f"%{league_name}%",))
    lrow = c.fetchone()
    if not lrow:
        print(f"No league found with name containing '{league_name}'.")
        return
    league_id = lrow[0]

    c.execute("SELECT Season_ID FROM Season WHERE Year_Start=? AND Year_End=?",
              (start_year, start_year+1))
    srow = c.fetchone()
    if not srow:
        print(f"No season found for {start_year}/{start_year+1}.")
        return
    season_id = srow[0]

    c.execute("""
        SELECT DISTINCT T.Team_Name
        FROM Team_Player_Season TPS
        JOIN Team T ON TPS.Team_ID = T.Team_ID
        JOIN League L ON T.League_ID = L.League_ID
        WHERE TPS.Season_ID = ? AND L.League_ID = ?
    """, (season_id, league_id))
    teams = c.fetchall()

    if not teams:
        print(
            f"No teams found for {league_name} in the {start_year}/{start_year+1} season.")
        return

    print(
        f"\nTeams in {league_name} for the {start_year}/{start_year+1} season:")
    for t in teams:
        print(t[0])
    print()


def view_team_roster_for_season(conn):
    team_name = input("Enter the Team Name: ").strip()
    start_year = input(
        "Enter the start year of the season (e.g., 2019 for 2019/2020): ").strip()

    if not start_year.isdigit():
        print("Invalid input. Season year must be an integer.")
        return
    start_year = int(start_year)

    c = conn.cursor()
    # Get Team_ID
    c.execute("SELECT Team_ID FROM Team WHERE Team_Name LIKE ?",
              (f"%{team_name}%",))
    trow = c.fetchone()
    if not trow:
        print(f"No team found with the name '{team_name}'.")
        return
    team_id = trow[0]

    # Get Season_ID
    c.execute("SELECT Season_ID FROM Season WHERE Year_Start=? AND Year_End=?",
              (start_year, start_year+1))
    srow = c.fetchone()
    if not srow:
        print(f"No season found for {start_year}/{start_year+1}.")
        return
    season_id = srow[0]

    # Query all players from this team in this season
    query = """
    SELECT p.Player_Name, p.Position
    FROM Team_Player_Season tps
    JOIN Player p ON tps.Player_ID = p.Player_ID
    WHERE tps.Team_ID = ? AND tps.Season_ID = ?
    ORDER BY p.Player_Name
    """
    c.execute(query, (team_id, season_id))
    players = c.fetchall()

    if not players:
        print(
            f"No players found for {team_name} in the {start_year}/{start_year+1} season.")
        return

    # Formatting output
    width_name = 25
    width_pos = 15

    print(f"\nRoster for {team_name} in {start_year}/{start_year+1}:")
    header = f"{'Player Name':<{width_name}}{'Position':<{width_pos}}"
    print(header)
    print("-" * (width_name + width_pos))

    for player in players:
        pname, pos = player
        line = f"{pname:<{width_name}}{pos:<{width_pos}}"
        print(line)
    print()


def view_player_matches_in_season(conn):
    """
    View all matches a player participated in during a specific season.
    """
    player_name = input("Enter the player's name or partial name: ").strip()
    if not player_name:
        print("Player name cannot be empty.")
        return

    c = conn.cursor()
    # Search for players matching the input name
    c.execute("SELECT Player_ID, Player_Name FROM Player WHERE Player_Name LIKE ?",
              (f"%{player_name}%",))
    players = c.fetchall()

    if not players:
        print(f"No players found with name containing '{player_name}'.\n")
        return

    # If multiple players found, let user select the correct one
    if len(players) > 1:
        print("\nMultiple players found:")
        for idx, player in enumerate(players, start=1):
            print(f"{idx}. {player[1]} (Player ID: {player[0]})")
        try:
            selection = int(
                input("Select the player by entering the corresponding number: ").strip())
            if selection < 1 or selection > len(players):
                print("Invalid selection. Returning to main menu.\n")
                return
            selected_player = players[selection - 1]
        except ValueError:
            print("Invalid input. Please enter a number. Returning to main menu.\n")
            return
    else:
        selected_player = players[0]

    player_id = selected_player[0]
    player_full_name = selected_player[1]

    # Prompt for season start year
    season_start_year_input = input(
        "Enter the start year of the season (e.g., 2019 for 2019/2020): ").strip()
    if not season_start_year_input.isdigit():
        print("Invalid year. Please enter a numeric year.\n")
        return
    season_start_year = int(season_start_year_input)

    # Retrieve Season_ID based on start year
    c.execute("SELECT Season_ID, Year_Start, Year_End FROM Season WHERE Year_Start = ? AND Year_End = ?",
              (season_start_year, season_start_year + 1))
    season = c.fetchone()
    if not season:
        print(
            f"No season found for {season_start_year}/{season_start_year + 1}.\n")
        return
    season_id = season[0]
    season_str = f"{season[1]}/{season[2]}"

    # Query to fetch matches the player participated in during the specified season
    query = """
    SELECT 
        m.Match_ID, 
        th.Team_Name AS Home_Team_Name, 
        ta.Team_Name AS Away_Team_Name, 
        m.Date, 
        m.Home_Score, 
        m.Away_Score,
        pmp.Minutes_Played,
        pmp.Goals,
        pmp.Assists
    FROM Player_Match_Participation pmp
    JOIN Match m ON pmp.Match_ID = m.Match_ID
    JOIN Team th ON m.Home_Team_ID = th.Team_ID
    JOIN Team ta ON m.Away_Team_ID = ta.Team_ID
    WHERE pmp.Player_ID = ? AND m.Season_ID = ?
    ORDER BY m.Date DESC
    """
    c.execute(query, (player_id, season_id))
    matches = c.fetchall()

    if not matches:
        print(
            f"\n{player_full_name} did not participate in any matches during the {season_str} season.\n")
        return

    # Define column widths for formatting
    width_id = 10
    width_home = 25
    width_away = 25
    width_date = 12
    width_score = 7
    width_minutes = 15
    width_goals = 7
    width_assists = 9

    # Print header
    header = (f"{'Match ID':<{width_id}}"
              f"{'Home Team':<{width_home}}"
              f"{'Away Team':<{width_away}}"
              f"{'Date':<{width_date}}"
              f"{'Score':<{width_score}}")
    print(f"\nMatches for {player_full_name} in the {season_str} season:")
    print(header)
    print("-" * (width_id + width_home + width_away + width_date +
          width_score + width_minutes + width_goals + width_assists))

    # Iterate and print each match
    for match in matches:
        match_id = match[0]
        home_team = match[1]
        away_team = match[2]
        date_str = match[3]
        home_score = match[4]
        away_score = match[5]
        minutes_played = match[6]
        goals = match[7]
        assists = match[8]

        # Format date
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
            date_formatted = dt.strftime("%Y-%m-%d")
        except ValueError:
            # If timezone info is missing or format is different
            date_formatted = date_str

        score_str = f"{home_score}-{away_score}" if home_score is not None and away_score is not None else "N/A"

        # Print match details
        line = (f"{str(match_id):<{width_id}}"
                f"{home_team:<{width_home}}"
                f"{away_team:<{width_away}}"
                f"{date_formatted:<{width_date}}"
                f"{score_str:<{width_score}}")
        print(line)
    print()


def main():
    conn = connect_to_db()
    while True:
        print("Soccer Management CLI (Enter Choices 1-12)")
        print("1. View all teams")
        print("2. View all teams in a league for a particular season")
        print("3. View a team's roster for a particular season")
        print("4. View all matches")
        print("5. View all fixtures for a particular season")
        print("6. View all fixtures from a particular league for a particular season")
        print("7. View all fixtures for a selected team in a selected season")
        print("8. Search players by name")
        print("9. View all teams a player played for in the last 5 seasons")
        print("10. View a player's current team in the 2023/2024 season")
        print("11. View matches a player participated in during a specific season")
        print("12. Exit (type 'e' or 'q' to exit)")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            show_teams(conn)
        elif choice == "2":
            view_teams_in_league_season(conn)
        elif choice == "3":
            view_team_roster_for_season(conn)
        elif choice == "4":
            show_all_matches(conn)
        elif choice == "5":
            view_fixtures_for_season(conn)
        elif choice == "6":
            view_fixtures_for_league_season(conn)
        elif choice == "7":
            view_fixtures_for_team_season(conn)
        elif choice == "8":
            search_players_by_name(conn)
        elif choice == "9":
            view_player_teams_last_5_seasons(conn)
        elif choice == "10":
            view_player_current_team_2023_24(conn)
        elif choice == "11":
            # view_player_current_team_2023_24(conn)
            view_player_matches_in_season(conn)
        elif choice == "12" or choice.lower() in ["e", "q"]:
            print("Exiting the CLI. Goodbye!")
            conn.close()
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
