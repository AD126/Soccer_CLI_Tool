# ⚽ Soccer Management CLI

A command-line tool for exploring European football data across the top 5 leagues, built with Python and SQLite.

## 📋 Overview

This project provides a Soccer Management Database accessible through an interactive CLI. It covers **5 major European leagues** — Premier League, La Liga, Serie A, Bundesliga, and Ligue 1 — across the **2019/2020 through 2023/2024 seasons**.

Data is sourced from the [API-Football](https://www.api-football.com/) API and stored locally in an SQLite database.

## 🎬 Demo

[▶ Watch the YouTube demonstration](https://youtu.be/MvEsqwmPo9g)

## ✨ Features

The CLI offers 11 interactive queries:

| # | Feature |
|---|---------|
| 1 | View all teams |
| 2 | View all teams in a league for a particular season |
| 3 | View a team's roster for a particular season |
| 4 | View all matches |
| 5 | View all fixtures for a particular season |
| 6 | View all fixtures from a particular league for a particular season |
| 7 | View all fixtures for a selected team in a selected season |
| 8 | Search players by name (with optional filters for position, team, league, season) |
| 9 | View all teams a player played for in the last 5 seasons |
| 10 | View a player's current team in the 2023/2024 season |
| 11 | View matches a player participated in during a specific season |

## 🗄️ Database Schema

The database uses 7 tables with the following relationships:

```
League ──┬── Team
         │
Season ──┼── Match (Home_Team, Away_Team, League, Season)
         │
Player ──┼── Team_Player_Season (links players to teams per season)
         │
         └── Player_Match_Participation (player stats per match)
```

See [`schema.sql`](schema.sql) for the full schema definition.

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- `python-dotenv` — for loading environment variables

### Installation

```bash
# Clone the repo
git clone https://github.com/AD126/Soccer_CLI_Tool.git
cd Soccer_CLI_Tool

# Install dependencies
pip install python-dotenv requests
```

### Environment Setup

Create a `.env` file in the project root with the following variables:

```env
RAPIDAPI_KEY=your_api_key_here
RAPIDAPI_HOST=api-football-v1.p.rapidapi.com
DB_FILE=soccer_management.db
```

> You'll need a [RapidAPI](https://rapidapi.com/) key with access to the API-Football endpoint to populate the database.

### Populate the Database

```bash
# Initialize the database schema
sqlite3 soccer_management.db < schema.sql

# Fetch and insert league, team, player, and match data
python3 fetch_data_other.py

# Fetch and insert player match participation data
python3 player_match_fetch.py
```

### Run the CLI

```bash
python3 cli.py
```

## 📁 Project Structure

```
├── cli.py                  # Interactive command-line interface
├── fetch_data_other.py     # Fetches leagues, teams, players, and matches from API
├── player_match_fetch.py   # Fetches player match participation (lineups) from API
├── schema.sql              # SQLite database schema
├── readme.txt              # Original project readme
├── .env                    # API keys and config (not tracked in git)
└── .gitignore              # Git ignore rules
```

## 👤 Author

**Ammtoje Dahbia**  
