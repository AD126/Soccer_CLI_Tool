-- Drop tables if they already exist (optional, for convenience during development)
DROP TABLE IF EXISTS Player_Match_Participation;
DROP TABLE IF EXISTS Team_Player_Season;
DROP TABLE IF EXISTS Match;
DROP TABLE IF EXISTS Season;
DROP TABLE IF EXISTS Player;
DROP TABLE IF EXISTS Team;
DROP TABLE IF EXISTS League;

-- Create the League table first
CREATE TABLE League (
    League_ID INTEGER PRIMARY KEY,
    League_Name TEXT NOT NULL
);

-- Create the Team table
CREATE TABLE Team (
    Team_ID INTEGER PRIMARY KEY,
    Team_Name TEXT NOT NULL,
    League_ID INTEGER NOT NULL,
    FOREIGN KEY (League_ID) REFERENCES League(League_ID)
);

-- Create the Player table
-- No League_ID here, as player's league can be derived from the team they play for in a given season
CREATE TABLE Player (
    Player_ID INTEGER PRIMARY KEY,
    Player_Name TEXT NOT NULL,
    Position TEXT
);

-- Create the Season table
CREATE TABLE Season (
    Season_ID INTEGER PRIMARY KEY,
    Year_Start INTEGER NOT NULL,
    Year_End INTEGER NOT NULL
);

-- Create the Match table
CREATE TABLE Match (
    Match_ID INTEGER PRIMARY KEY,
    Home_Team_ID INTEGER NOT NULL,
    Away_Team_ID INTEGER NOT NULL,
    Date TEXT NOT NULL,
    Home_Score INTEGER,
    Away_Score INTEGER,
    Season_ID INTEGER NOT NULL,
    League_ID INTEGER NOT NULL,
    FOREIGN KEY (Home_Team_ID) REFERENCES Team(Team_ID),
    FOREIGN KEY (Away_Team_ID) REFERENCES Team(Team_ID),
    FOREIGN KEY (Season_ID) REFERENCES Season(Season_ID),
    FOREIGN KEY (League_ID) REFERENCES League(League_ID)
);

-- Create the Team_Player_Season table (associative entity)
-- This links a player to a team for a particular season, allowing queries like:
-- "Which players are on Team X in Season Y?" or "Which teams has Player Z played for?"
CREATE TABLE Team_Player_Season (
    Team_Player_Season_ID INTEGER PRIMARY KEY,
    Team_ID INTEGER NOT NULL,
    Player_ID INTEGER NOT NULL,
    Season_ID INTEGER NOT NULL,
    League_ID INTEGER,
    FOREIGN KEY (Team_ID) REFERENCES Team(Team_ID),
    FOREIGN KEY (Player_ID) REFERENCES Player(Player_ID),
    FOREIGN KEY (Season_ID) REFERENCES Season(Season_ID),
    FOREIGN KEY (League_ID) REFERENCES League(League_ID)
);

-- Create the Player_Match_Participation table (associative entity)
-- This links a player to a match and can store stats like minutes played, goals, and assists.
CREATE TABLE Player_Match_Participation (
    Player_Match_ID INTEGER PRIMARY KEY,
    Match_ID INTEGER NOT NULL,
    Player_ID INTEGER NOT NULL,
    Minutes_Played INTEGER,
    Goals INTEGER DEFAULT 0,
    Assists INTEGER DEFAULT 0,
    FOREIGN KEY (Match_ID) REFERENCES Match(Match_ID),
    FOREIGN KEY (Player_ID) REFERENCES Player(Player_ID)
);
