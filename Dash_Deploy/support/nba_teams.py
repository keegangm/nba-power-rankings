# nba_teams.py

# DONE: modules
import os
import pandas as pd

# DONE: import 'NBA_Teams.csv' file
base_dir = os.path.dirname(__file__)  # Gets the directory of the current script
csv_path = os.path.join(base_dir, "data", "nba_teams_data.csv")
df = pd.read_csv(csv_path)

# define find_team() method for agnostic search term
def find_team(query, property_name='teamname') -> str:
    """ Return desired property_name for teamname query in almost any form. """
    query = query.lower()
    matching_teams = df[(df['aliases'].str.contains(query, case=False)) | 
                        (df['teamname'].str.contains(query, case=False)) |
                        (df['abbrev'].str.contains(query, case=False))
                        ]
    if not matching_teams.empty:
        return matching_teams[property_name].iloc[0]
    return None

def find_team_colors(team_qry: str, color_rank=1):
    """ Match team input to team color scheme. """
    matching_team = find_team(team_qry, 'teamname')

    if matching_team:
        
        if color_rank in [1,2,3] or isinstance(color_rank, str):
            
            if color_rank == 1:
                color_1 = df.loc[df['teamname'] == matching_team, 'color_1'].iloc[0]
                return f"{color_1}"
            
            if color_rank == 2:
                color_2 = df.loc[df['teamname'] == matching_team, 'color_2'].iloc[0]
                return f"{color_2}"
                #return f"The {matching_team}'s secondary color is {color_2}"
            
            if color_rank == 3:
                color_3 = df.loc[df['teamname'] == matching_team, 'color_3'].iloc[0]
                #msg = (f"{matching_team} tertiary color:{color_3}")
                return f"{color_3}"
                #return f"The {matching_team}'s tertiary color is {color_3}"
            
            elif color_rank.lower() == "all":
                color_2 = df.loc[df['teamname'] == matching_team, 'color_2'].iloc[0]
                color_1 = df.loc[df['teamname'] == matching_team, 'color_1'].iloc[0]
                color_3 = df.loc[df['teamname'] == matching_team, 'color_3'].iloc[0]
                return color_1, color_2, color_3
            
            else:
                return "No corresponding color value found"
            
        else:
            return "No corresponding color value found"
        
    else:
        #print("No Match Found")
        return None
# DONE: define nba_tmname()


# DONE: define nba_tmname()
# derive team name (e.g. 'Utah Jazz') from inputs including abbreviation ('UTA') or aliases ('Utah', 'Jazz')
def nba_tmname(query):
    """ Find full team name for NBA team. """
    return find_team(query, 'teamname')

# DONE: define nba_abbrname()
# derive team abbreviation (e.g. 'UTA') from inputs team name ('Utah Jazz') or aliases ('Utah', 'Jazz')
def nba_abbrname(query):
    """ Find abbreviation for NBA team. """
    return find_team(query, 'abbrev')


def nba_conf(query):
    """ Find Conference for NBA team. """
    return find_team(query, 'conference')

def nba_div(query):
    """ Find Division for NBA team. """
    return find_team(query, 'division')

def nba_arena(query):
    """ Find Arena for NBA team. """
    return find_team(query, 'arena')

def nba_city(query):
    """Find City for NBA team. """
    return find_team(query, 'location')

def team_color1(query):
    """ Find primary color for NBA team. """
    return find_team_colors(query, 1)

def team_color2(query):
    """ Find secondary color for NBA team. """
    return find_team_colors(query, 2)

def team_color3(query):
    """ Find tertiary color for NBA team. """
    team = find_team(query, 'teamname')
    return find_team_colors(query, 3)

def team_color_all(query):
    """ Find any color (1, 2, 3) for NBA team. """
    team = find_team(query, 'teamname')
    return find_team_colors(query, 'all')

def main(query):
    """List all data items for NBA team. """
    team = find_team(query, 'teamname')
    location = nba_city(team)
    abbr = nba_abbrname(team)
    colors = find_team_colors(team, 'all')
    arena = nba_arena(team)
    conference = nba_conf(team)
    division = nba_div(team)
    print(f"{team} ({abbr})\n{location}\nconference: {conference}\ndivision: {division}\ncolors: {colors}\narena: {arena}")


if __name__ == "__main__":
    main('Warriors')