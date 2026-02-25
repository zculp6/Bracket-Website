import numpy as np
import pandas as pd
import os

# ---------------------------------------
# TEAM & SEED DATA
# ---------------------------------------

TEAMS = [
    "Alabama", "Alabama St.", "Akron", "American", "Arkansas", "Auburn", "Baylor",
    "Bryant", "BYU", "Clemson", "Colorado St.", "Creighton", "Drake", "Duke", "Florida", "Georgia",
    "Gonzaga", "High Point", "Houston", "Illinois", "Kansas", "Kentucky", "Liberty", "Lipscomb", "Louisville",
    "Marquette", "McNeese St.", "Michigan", "Michigan St.", "Mississippi St.", "Missouri", "Montana", "Mount St. Mary's",
    "New Mexico", "North Carolina", "Oklahoma", "Nebraska Omaha", "Oregon", "Purdue", "Robert Morris",
    "Saint Francis", "Saint Mary's", "SIU Edwardsville", "St. John's", "Tennessee", "Texas", "Texas A&M",
    "Texas Tech", "Troy", "UCLA", "UC San Diego", "Utah St.", "VCU", "Vanderbilt", "Wofford", "Wisconsin",
    "Xavier", "Yale", "UNC Wilmington", "Grand Canyon", "Maryland", "Memphis", "Connecticut", "Norfolk St.", "Arizona",
    "San Diego St.", "Iowa St.", "Mississippi"
]

SEED_REGION_MAPPING = {
    # South Region
    "Auburn": (1, "South"), "Alabama St.": (16, "South"), "Saint Francis": (16, "South"),
    "Louisville": (8, "South"), "Creighton": (9, "South"), "Michigan": (5, "South"),
    "UC San Diego": (12, "South"), "Texas A&M": (4, "South"), "Yale": (13, "South"),
    "Mississippi": (6, "South"), "San Diego St.": (11, "South"), "North Carolina": (11, "South"),
    "Iowa St.": (3, "South"), "Lipscomb": (14, "South"), "Marquette": (7, "South"),
    "New Mexico": (10, "South"), "Michigan St.": (2, "South"), "Bryant": (15, "South"),
    # West Region
    "Florida": (1, "West"), "Norfolk St.": (16, "West"), "Connecticut": (8, "West"),
    "Oklahoma": (9, "West"), "Memphis": (5, "West"), "Colorado St.": (12, "West"),
    "Maryland": (4, "West"), "Grand Canyon": (13, "West"), "Missouri": (6, "West"),
    "Drake": (11, "West"), "Texas Tech": (3, "West"), "UNC Wilmington": (14, "West"),
    "Kansas": (7, "West"), "Arkansas": (10, "West"), "St. John's": (2, "West"),
    "Nebraska Omaha": (15, "West"),
    # East Region
    "Duke": (1, "East"), "American": (16, "East"), "Mount St. Mary's": (16, "East"),
    "Mississippi St.": (8, "East"), "Baylor": (9, "East"), "Oregon": (5, "East"),
    "Liberty": (12, "East"), "Arizona": (4, "East"), "Akron": (13, "East"),
    "BYU": (6, "East"), "VCU": (11, "East"), "Wisconsin": (3, "East"),
    "Montana": (14, "East"), "Saint Mary's": (7, "East"), "Vanderbilt": (10, "East"),
    "Alabama": (2, "East"), "Robert Morris": (15, "East"),
    # Midwest Region
    "Houston": (1, "Midwest"), "SIU Edwardsville": (16, "Midwest"), "Gonzaga": (8, "Midwest"),
    "Georgia": (9, "Midwest"), "Clemson": (5, "Midwest"), "McNeese St.": (12, "Midwest"),
    "Purdue": (4, "Midwest"), "High Point": (13, "Midwest"), "Illinois": (6, "Midwest"),
    "Texas": (11, "Midwest"), "Xavier": (11, "Midwest"), "Kentucky": (3, "Midwest"),
    "Troy": (14, "Midwest"), "UCLA": (7, "Midwest"), "Utah St.": (10, "Midwest"),
    "Tennessee": (2, "Midwest"), "Wofford": (15, "Midwest"),
}

REGION_TO_ROUND_ID = {
    "West":    {"r64": "west_r64",    "r32": "west_r32",    "s16": "west_s16",    "e8": "west_e8"},
    "South":   {"r64": "south_r64",   "r32": "south_r32",   "s16": "south_s16",   "e8": "south_e8"},
    "East":    {"r64": "east_r64",    "r32": "east_r32",    "s16": "east_s16",    "e8": "east_e8"},
    "Midwest": {"r64": "midwest_r64", "r32": "midwest_r32", "s16": "midwest_s16", "e8": "midwest_e8"},
}

FF_LEFT_REGIONS  = {"West", "South"}
FF_RIGHT_REGIONS = {"East", "Midwest"}


# ---------------------------------------
# LOAD DATA
# ---------------------------------------

def _load_data():
    base = os.path.dirname(__file__)
    strengths_path = os.path.join(base, "team_strengths_2025.csv")
    history_path   = os.path.join(base, "past_tournament_rounds.csv")

    if not os.path.exists(strengths_path):
        raise FileNotFoundError(f"Missing: {strengths_path}")
    if not os.path.exists(history_path):
        raise FileNotFoundError(f"Missing: {history_path}")

    t_df = pd.read_csv(strengths_path)
    t_df = t_df[t_df['team'].isin(TEAMS)].copy()
    t_df.rename(columns={'team': 'team_names'}, inplace=True)

    seed_region_df = pd.DataFrame.from_dict(
        SEED_REGION_MAPPING, orient='index', columns=['Seed', 'Region']
    ).reset_index().rename(columns={'index': 'team_names'})

    t_df = t_df.merge(seed_region_df, on='team_names', how='left')

    past = pd.read_csv(history_path)
    round_columns = past.columns[1:]
    original = past[round_columns].copy()

    for i in range(len(round_columns) - 1):
        past[round_columns[i + 1]] = original[round_columns[i + 1]] / original[round_columns[i]]
    past.fillna(0, inplace=True)
    past.drop(columns=["Round of 64"], inplace=True)
    past.drop(index=[16, 17, 18], errors='ignore', inplace=True)

    t_df = t_df.merge(past, on='Seed', how='left')

    return t_df, past


# ---------------------------------------
# GAME SIMULATION
# ---------------------------------------

def _simulate_game(team1, team2, mean1, mean2, std1, std2, seed1_prob, seed2_prob, weight):
    r1 = np.clip(np.random.normal(mean1, std1), 0, 1)
    r2 = np.clip(np.random.normal(mean2, std2), 0, 1)

    s1 = weight * r1 + (1 - weight) * seed1_prob
    s2 = weight * r2 + (1 - weight) * seed2_prob

    s1 = np.clip(s1, 1e-6, 1 - 1e-6)
    s2 = np.clip(s2, 1e-6, 1 - 1e-6)

    log_odds1 = np.log(s1 / (1 - s1))
    log_odds2 = np.log(s2 / (1 - s2))

    p = 1 / (1 + np.exp(log_odds2 - log_odds1))
    return team1 if np.random.rand() < p else team2


def _simulate_first_four(t_df, weight):
    losers = []
    grouped = t_df.groupby(['Region', 'Seed'])

    for (region, seed), group in grouped:
        if len(group) == 2:
            t1, t2 = group.iloc[0], group.iloc[1]
            winner = _simulate_game(
                t1['team_names'], t2['team_names'],
                t1['strength'], t2['strength'],
                t1['error'], t2['error'],
                0, 0, weight
            )
            loser = t1['team_names'] if winner != t1['team_names'] else t2['team_names']
            losers.append(loser)

    return t_df[~t_df['team_names'].isin(losers)].copy()


# ---------------------------------------
# FULL TOURNAMENT SIMULATION
# ---------------------------------------

def simulate_tournament(weight=0.25):
    t_df, past = _load_data()
    t_df = _simulate_first_four(t_df, weight)

    round_names   = ["Round of 64", "Round of 32", "Sweet 16", "Elite 8"]
    round_id_keys = ["r64", "r32", "s16", "e8"]
    standard_order = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]
    regions = ["West", "South", "East", "Midwest"]

    region_teams = {}
    for region in regions:
        r_df = t_df[t_df['Region'] == region].copy()
        ordered = []
        for seed in standard_order:
            match = r_df[r_df['Seed'] == seed]
            if not match.empty:
                ordered.append(match.iloc[0])
        region_teams[region] = ordered

    result = {}
    region_e8_winners = {}

    for region in regions:
        current_teams = region_teams[region]
        round_id_map  = REGION_TO_ROUND_ID[region]

        for round_idx, (round_name, round_key) in enumerate(zip(round_names, round_id_keys)):
            container_id    = round_id_map[round_key]
            round_round_idx = round_idx + 1

            team_entries = []
            winners = []

            for i in range(0, len(current_teams), 2):
                if i + 1 >= len(current_teams):
                    break

                t1 = current_teams[i]
                t2 = current_teams[i + 1]

                try:
                    seed1_prob = past[past['Seed'] == t1['Seed']].iloc[0][past.columns[round_round_idx]]
                    seed2_prob = past[past['Seed'] == t2['Seed']].iloc[0][past.columns[round_round_idx]]
                except (IndexError, KeyError):
                    seed1_prob = seed2_prob = 0.5

                winner_name = _simulate_game(
                    t1['team_names'], t2['team_names'],
                    t1['strength'], t2['strength'],
                    t1['error'], t2['error'],
                    seed1_prob, seed2_prob, weight
                )

                team_entries.append({"seed": int(t1['Seed']), "name": t1['team_names']})
                team_entries.append({"seed": int(t2['Seed']), "name": t2['team_names']})

                winner_row = t1 if winner_name == t1['team_names'] else t2
                winners.append(winner_row)

            result[container_id] = team_entries
            current_teams = winners

        if current_teams:
            region_e8_winners[region] = current_teams[0]

    ff_left_teams  = [region_e8_winners[r] for r in ["West", "South"]  if r in region_e8_winners]
    ff_right_teams = [region_e8_winners[r] for r in ["East", "Midwest"] if r in region_e8_winners]

    result["ff_left"]  = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_left_teams]
    result["ff_right"] = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_right_teams]

    ff_winners = []
    for ff_teams in [ff_left_teams, ff_right_teams]:
        if len(ff_teams) == 2:
            t1, t2 = ff_teams[0], ff_teams[1]
            w_name = _simulate_game(
                t1['team_names'], t2['team_names'],
                t1['strength'], t2['strength'],
                t1['error'], t2['error'],
                0.5, 0.5, weight
            )
            ff_winners.append(t1 if w_name == t1['team_names'] else t2)

    champion = None
    if len(ff_winners) == 2:
        t1, t2 = ff_winners[0], ff_winners[1]
        result["championship"] = [
            {"seed": int(t1['Seed']), "name": t1['team_names']},
            {"seed": int(t2['Seed']), "name": t2['team_names']},
        ]
        champ_name = _simulate_game(
            t1['team_names'], t2['team_names'],
            t1['strength'], t2['strength'],
            t1['error'], t2['error'],
            0.5, 0.5, weight
        )
        champion = champ_name
    else:
        result["championship"] = []

    result["champion"] = champion
    return result


# ---------------------------------------
# CHALK
# ---------------------------------------

def chalk_bracket():
    t_df, _ = _load_data()
    t_df = _simulate_first_four(t_df, weight=0)

    standard_order = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]
    regions = ["West", "South", "East", "Midwest"]
    round_id_keys = ["r64", "r32", "s16", "e8"]

    region_teams = {}
    for region in regions:
        r_df = t_df[t_df['Region'] == region].copy()
        ordered = []
        for seed in standard_order:
            match = r_df[r_df['Seed'] == seed]
            if not match.empty:
                ordered.append(match.iloc[0])
        region_teams[region] = ordered

    result = {}
    region_e8_winners = {}

    for region in regions:
        current_teams = region_teams[region]
        round_id_map  = REGION_TO_ROUND_ID[region]

        for round_key in round_id_keys:
            container_id = round_id_map[round_key]
            team_entries = []
            winners = []

            for i in range(0, len(current_teams), 2):
                if i + 1 >= len(current_teams):
                    break
                t1 = current_teams[i]
                t2 = current_teams[i + 1]

                team_entries.append({"seed": int(t1['Seed']), "name": t1['team_names']})
                team_entries.append({"seed": int(t2['Seed']), "name": t2['team_names']})

                winner = t1 if t1['Seed'] <= t2['Seed'] else t2
                winners.append(winner)

            result[container_id] = team_entries
            current_teams = winners

        if current_teams:
            region_e8_winners[region] = current_teams[0]

    ff_left_teams  = [region_e8_winners[r] for r in ["West", "South"]  if r in region_e8_winners]
    ff_right_teams = [region_e8_winners[r] for r in ["East", "Midwest"] if r in region_e8_winners]

    result["ff_left"]  = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_left_teams]
    result["ff_right"] = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_right_teams]

    ff_winners = []
    for ff_teams in [ff_left_teams, ff_right_teams]:
        if len(ff_teams) == 2:
            winner = ff_teams[0] if ff_teams[0]['Seed'] <= ff_teams[1]['Seed'] else ff_teams[1]
            ff_winners.append(winner)

    if len(ff_winners) == 2:
        t1, t2 = ff_winners[0], ff_winners[1]
        result["championship"] = [
            {"seed": int(t1['Seed']), "name": t1['team_names']},
            {"seed": int(t2['Seed']), "name": t2['team_names']},
        ]
        champion = t1['team_names'] if t1['Seed'] <= t2['Seed'] else t2['team_names']
    else:
        result["championship"] = []
        champion = None

    result["champion"] = champion
    return result


# ---------------------------------------
# RANDOM (pure 50/50 coin flip every game)
# ---------------------------------------

def random_bracket():
    t_df, _ = _load_data()
    t_df = _simulate_first_four(t_df, weight=0.5)  # coin flip for First Four too

    standard_order = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]
    regions = ["West", "South", "East", "Midwest"]
    round_id_keys = ["r64", "r32", "s16", "e8"]

    region_teams = {}
    for region in regions:
        r_df = t_df[t_df['Region'] == region].copy()
        ordered = []
        for seed in standard_order:
            match = r_df[r_df['Seed'] == seed]
            if not match.empty:
                ordered.append(match.iloc[0])
        region_teams[region] = ordered

    result = {}
    region_e8_winners = {}

    for region in regions:
        current_teams = region_teams[region]
        round_id_map  = REGION_TO_ROUND_ID[region]

        for round_key in round_id_keys:
            container_id = round_id_map[round_key]
            team_entries = []
            winners = []

            for i in range(0, len(current_teams), 2):
                if i + 1 >= len(current_teams):
                    break
                t1 = current_teams[i]
                t2 = current_teams[i + 1]

                team_entries.append({"seed": int(t1['Seed']), "name": t1['team_names']})
                team_entries.append({"seed": int(t2['Seed']), "name": t2['team_names']})

                # Pure coin flip — no strength, no seed history
                winner = t1 if np.random.rand() < 0.5 else t2
                winners.append(winner)

            result[container_id] = team_entries
            current_teams = winners

        if current_teams:
            region_e8_winners[region] = current_teams[0]

    ff_left_teams  = [region_e8_winners[r] for r in ["West", "South"]  if r in region_e8_winners]
    ff_right_teams = [region_e8_winners[r] for r in ["East", "Midwest"] if r in region_e8_winners]

    result["ff_left"]  = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_left_teams]
    result["ff_right"] = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_right_teams]

    ff_winners = []
    for ff_teams in [ff_left_teams, ff_right_teams]:
        if len(ff_teams) == 2:
            t1, t2 = ff_teams[0], ff_teams[1]
            ff_winners.append(t1 if np.random.rand() < 0.5 else t2)

    if len(ff_winners) == 2:
        t1, t2 = ff_winners[0], ff_winners[1]
        result["championship"] = [
            {"seed": int(t1['Seed']), "name": t1['team_names']},
            {"seed": int(t2['Seed']), "name": t2['team_names']},
        ]
        champion = t1['team_names'] if np.random.rand() < 0.5 else t2['team_names']
    else:
        result["championship"] = []
        champion = None

    result["champion"] = champion
    return result


# ---------------------------------------
# PROBABILISTIC BY SEED
# ---------------------------------------
def random_probabilistic_bracket():
    # Load team data and historical counts
    t_df, past = _load_data()
    t_df = _simulate_first_four(t_df, weight=0.5)

    standard_order = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]
    regions = ["West", "South", "East", "Midwest"]
    round_id_keys = ["r64", "r32", "s16", "e8"]

    # Prepare teams by region and seed order
    region_teams = {}
    for region in regions:
        r_df = t_df[t_df['Region'] == region].copy()
        ordered = []
        for seed in standard_order:
            match = r_df[r_df['Seed'] == seed]
            if not match.empty:
                ordered.append(match.iloc[0])
        region_teams[region] = ordered

    result = {}
    region_e8_winners = {}

    # Simulate each region
    for region in regions:
        current_teams = region_teams[region]
        round_id_map = REGION_TO_ROUND_ID[region]

        for round_idx, round_key in enumerate(round_id_keys):
            container_id = round_id_map[round_key]
            round_prob_col = past.columns[round_idx]  # column like "Round of 64"
            team_entries = []
            winners = []

            # Simulate games pairwise
            for i in range(0, len(current_teams), 2):
                if i + 1 >= len(current_teams):
                    break
                t1 = current_teams[i]
                t2 = current_teams[i + 1]

                team_entries.append({"seed": int(t1['Seed']), "name": t1['team_names']})
                team_entries.append({"seed": int(t2['Seed']), "name": t2['team_names']})

                # Get historical counts summed across all tournaments
                try:
                    count1 = past.loc[past['Seed'] == t1['Seed'], round_prob_col].sum()
                    count2 = past.loc[past['Seed'] == t2['Seed'], round_prob_col].sum()
                    # Compute probability of t1 winning
                    p_win_t1 = count1 / (count1 + count2) if (count1 + count2) > 0 else 0.5
                except (IndexError, KeyError):
                    p_win_t1 = 0.5

                # Randomly select winner based on probability
                winner = t1 if np.random.rand() < p_win_t1 else t2
                winners.append(winner)

            # Store results for this round
            result[container_id] = team_entries
            current_teams = winners

        # Keep Elite 8 winner for Final Four
        if current_teams:
            region_e8_winners[region] = current_teams[0]

    # Set up Final Four
    ff_left_teams  = [region_e8_winners[r] for r in ["West", "South"]  if r in region_e8_winners]
    ff_right_teams = [region_e8_winners[r] for r in ["East", "Midwest"] if r in region_e8_winners]

    result["ff_left"]  = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_left_teams]
    result["ff_right"] = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_right_teams]

    # Final Four games (you can later also weight these by historical counts)
    ff_winners = []
    for ff_teams in [ff_left_teams, ff_right_teams]:
        if len(ff_teams) == 2:
            t1, t2 = ff_teams
            # Use equal probability for Final Four / Championship
            ff_winners.append(t1 if np.random.rand() < 0.5 else t2)

    # Championship game
    if len(ff_winners) == 2:
        t1, t2 = ff_winners
        result["championship"] = [
            {"seed": int(t1['Seed']), "name": t1['team_names']},
            {"seed": int(t2['Seed']), "name": t2['team_names']},
        ]
        champion = t1['team_names'] if np.random.rand() < 0.5 else t2['team_names']
    else:
        result["championship"] = []
        champion = None

    result["champion"] = champion
    return result

# ---------------------------------------
# BY RANKING (deterministic, highest strength wins)
# ---------------------------------------

def ranking_bracket():
    t_df, _ = _load_data()
    t_df = _simulate_first_four(t_df, weight=1.0)

    standard_order = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]
    regions = ["West", "South", "East", "Midwest"]
    round_id_keys = ["r64", "r32", "s16", "e8"]

    region_teams = {}
    for region in regions:
        r_df = t_df[t_df['Region'] == region].copy()
        ordered = []
        for seed in standard_order:
            match = r_df[r_df['Seed'] == seed]
            if not match.empty:
                ordered.append(match.iloc[0])
        region_teams[region] = ordered

    result = {}
    region_e8_winners = {}

    for region in regions:
        current_teams = region_teams[region]
        round_id_map  = REGION_TO_ROUND_ID[region]

        for round_key in round_id_keys:
            container_id = round_id_map[round_key]
            team_entries = []
            winners = []

            for i in range(0, len(current_teams), 2):
                if i + 1 >= len(current_teams):
                    break
                t1 = current_teams[i]
                t2 = current_teams[i + 1]

                team_entries.append({"seed": int(t1['Seed']), "name": t1['team_names']})
                team_entries.append({"seed": int(t2['Seed']), "name": t2['team_names']})

                winner = t1 if t1['strength'] >= t2['strength'] else t2
                winners.append(winner)

            result[container_id] = team_entries
            current_teams = winners

        if current_teams:
            region_e8_winners[region] = current_teams[0]

    ff_left_teams  = [region_e8_winners[r] for r in ["West", "South"]  if r in region_e8_winners]
    ff_right_teams = [region_e8_winners[r] for r in ["East", "Midwest"] if r in region_e8_winners]

    result["ff_left"]  = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_left_teams]
    result["ff_right"] = [{"seed": int(t['Seed']), "name": t['team_names']} for t in ff_right_teams]

    ff_winners = []
    for ff_teams in [ff_left_teams, ff_right_teams]:
        if len(ff_teams) == 2:
            t1, t2 = ff_teams[0], ff_teams[1]
            ff_winners.append(t1 if t1['strength'] >= t2['strength'] else t2)

    if len(ff_winners) == 2:
        t1, t2 = ff_winners[0], ff_winners[1]
        result["championship"] = [
            {"seed": int(t1['Seed']), "name": t1['team_names']},
            {"seed": int(t2['Seed']), "name": t2['team_names']},
        ]
        champion = t1['team_names'] if t1['strength'] >= t2['strength'] else t2['team_names']
    else:
        result["championship"] = []
        champion = None

    result["champion"] = champion
    return result