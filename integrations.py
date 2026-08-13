
import requests
import pandas as pd

SLEEPER = "https://api.sleeper.app/v1"

def sleeper_league(league_id: str):
    return requests.get(f"{SLEEPER}/league/{league_id}", timeout=20).json()

def sleeper_rosters(league_id: str):
    return requests.get(f"{SLEEPER}/league/{league_id}/rosters", timeout=20).json()

def sleeper_users(league_id: str):
    return requests.get(f"{SLEEPER}/league/{league_id}/users", timeout=20).json()

def sleeper_drafts(league_id: str):
    return requests.get(f"{SLEEPER}/league/{league_id}/drafts", timeout=20).json()

# For nflverse, recommended production path:
# pip install nflreadpy
# import nflreadpy as nfl
# weekly = nfl.load_player_stats([2024, 2025])
#
# Confirm the latest nflreadpy function names against its documentation when wiring
# the live version, since the package is actively maintained.
