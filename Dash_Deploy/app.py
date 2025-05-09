import os
import sys
import subprocess

# Dash imports
from dash import Dash, dcc, html, callback, Output, Input, State
import datetime as dt
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go

# Other imports
import support.nba_teams as teams
from dateutil.parser import parse
import pytz
import requests
from io import StringIO
import plotly.io as pio
from plotly.subplots import make_subplots

# import io
from base64 import b64encode


def find_file(file_name):
    """Find file within Dash_Deploy/support/ or support/."""
    file_name = f"{file_name}.csv"
    possible_paths = [
        os.path.join("Dash_Deploy", "support", "data", file_name),
        os.path.join("support", "data", file_name),
    ]

    for file_path in possible_paths:
        if os.path.exists(file_path):
            return file_path  # Return the first found file

    return None  # File not found in either path


WEEK_REFERENCE_PATH = find_file("nba_weeks_ref")


def read_nba_week():
    """Read NBA Week from reference file."""
    return pd.read_csv(
        WEEK_REFERENCE_PATH, parse_dates=["sunday"], dtype={"nba_week": int}
    )


def read_ranking_file():
    """Read NBA Ranking file from GitHub first, then local if unavailable."""

    github_url = "https://raw.githubusercontent.com/keegangm/nba-power-rankings/main/Dash_Deploy/support/data/latest_powerrankings.csv"

    # Start with GitHub
    try:
        response = requests.get(github_url, timeout=5)
        response.raise_for_status()

        csv_content = StringIO(response.text)

        from_github = pd.read_csv(
            csv_content, parse_dates=["date"], date_format="%y%m%d"
        )

        # print("Loaded rankings from GitHub.")
        return from_github
    except (requests.RequestException, pd.errors.ParserError) as e:
        print(f"GitHub fetch failed: {e}. Falling back to local file.")
    # Fallback to local file
    rk = pd.read_csv(
        find_file("latest_powerrankings"), parse_dates=["date"], date_format="%y%m%d"
    )  # 02-Dec-24
    return rk


us_central_tz = pytz.timezone("US/Central")
today = dt.datetime.now(us_central_tz).date()
# print(today)


### add function to calculate latest date in file
def get_max_pr_date():
    """Get date of most recent power rankings set present in 'latest_powerrankings.csv' file."""
    rk = read_ranking_file()
    # print(rk)
    sorted_df = rk.sort_values(by="date", ascending=False)
    max_date = sorted_df.max()["date"]
    return max_date


def nba_week_from_date(date=today):
    """Get NBA Week number"""
    wk_df = read_nba_week()
    nba_week_no = wk_df[wk_df["sunday"] <= date].nba_week.max()

    return int(nba_week_no)


def most_recent_sunday(date):
    """Find date of most recent Sunday."""
    date = pd.to_datetime(date)
    if date.weekday() == 6:
        return date
    else:
        return date - pd.to_timedelta(date.weekday() + 1, unit="D")


def create_and_merge_rank_week():

    rk = read_ranking_file()
    wk = read_nba_week()

    rk["sunday"] = rk["date"].apply(most_recent_sunday)
    rk["sunday"] = pd.to_datetime(rk["sunday"])
    wk["sunday"] = pd.to_datetime(wk["sunday"])

    df = pd.merge(rk, wk[["sunday", "nba_week"]], on="sunday", how="left")
    return df


def read_nba_teams_ref():
    nba_teams_ref = pd.read_csv(find_file("nba_teams_data"))
    # nba_teams_ref = get_csv('nba_teams_data')
    return nba_teams_ref


def clean_date(raw_date=None):
    """Get an external-friendly date in format 'Jan 24, 2025'."""
    if raw_date is not None:
        input_date = parse(raw_date)
    else:
        input_date = dt.datetime.now(us_central_tz).date()

    parsed_date = input_date.strftime("%b. %d, %Y")
    return parsed_date


def create_season_rks_df(df: pd.DataFrame):
    """Filter the DataFrame to only include rows with valid NBA weeks."""
    df = df[df["nba_week"].notna()]
    df["nba_week"] = df["nba_week"].astype(int)
    season_rks_df = df[df["nba_week"] > 0]

    return season_rks_df


def create_source_pt(df: pd.DataFrame):
    """Create a pivot table for Sources and Counts of Rankings."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame")

    return pd.pivot_table(
        df, values=["nba_week"], index=["source"], aggfunc=pd.Series.nunique
    ).rename(columns={"nba_week": "rankings_count"})


def create_rk_pt(df: pd.DataFrame):
    """Create a pivot table for Average Ranks and NBA_Weeks."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame")

    rk_pt = pd.pivot_table(df, index="teamname", columns="nba_week", values="ranking")
    rk_pt = rk_pt.round(2)

    # rk_pt will be input for graphs
    return rk_pt


def create_filtered_df(
    df: pd.DataFrame, start_date="2024-10-20", end_date=dt.datetime.today()
):
    """Filter the DataFrame to only include rows with specified NBA weeks."""

    start_adjust = most_recent_sunday(start_date)  # find most recent sunday
    end_adjust = end_date

    df["date"] = pd.to_datetime(df["date"])
    df = df[df["nba_week"].notna()]
    df["nba_week"] = df["nba_week"].astype(int)

    filtered_df = df[(df.date >= start_adjust) & (df.date <= end_adjust)]

    return filtered_df


def df_string_for_graph():

    df = create_season_rks_df(create_and_merge_rank_week())
    rk_pt = create_rk_pt(df)

    return rk_pt


data_points = len(create_season_rks_df(create_and_merge_rank_week()))


def df_string_for_graph_2(start="2024-10-20", end=dt.datetime.today()):
    ranking_file = find_file("latest_powerrankings")
    df = create_filtered_df(create_and_merge_rank_week(), start, end)
    rk_pt = create_rk_pt(df)

    return rk_pt


def get_max_min_week(start="2024-10-20", end=dt.datetime.today()):
    """Get NBA WEEK # for start and end date"""

    return nba_week_from_date(end), nba_week_from_date(start)


def sunday_from_nba_week(week: int):
    """Lookup date for Sunday of week number."""
    try:
        wk = read_nba_week()
        return (wk.loc[wk["nba_week"] == week, "sunday"]).item()
    except:
        return None


def create_sundays_array():
    """Create arrays of Sundays and corresponding NBA week #s."""
    weeks_array = []
    sundays_array = []
    for i in range(1, 30):
        weeks_array.append(i)
        # sundays_array.append(sunday_lookup(i)+1)
        sundays_array.append(sunday_from_nba_week(i))

    return weeks_array, sundays_array


date_strings = [d.strftime("%b %-d") for d in create_sundays_array()[1]]


def make_dropdown_options():
    teams = read_nba_teams_ref()
    dropdown_options = []
    conf_set = set()
    team_set = set()
    div_set = set()

    for index, row in teams.iterrows():
        team = row["teamname"]
        conf = row["conference"]
        div = row["division"]
        team_set.add(team)
        conf_set.add(conf)
        div_set.add(div)

    # dropdown_options.append({"label": "--- Conferences ---", "value": "divider", "disabled": True})

    dropdown_options.append(
        {"label": "--- Conferences ---", "value": "divider", "disabled": True}
    )
    for element in conf_set:
        dropdown_options.append({"label": element, "value": element, "disabled": False})

    dropdown_options.append(
        {"label": "--- Divisions ---", "value": "divider", "disabled": True}
    )

    for element in sorted(div_set):
        dropdown_options.append({"label": element, "value": element, "disabled": False})

    dropdown_options.append(
        {"label": "--- Teams ---", "value": "divider", "disabled": True}
    )
    for element in sorted(team_set):
        dropdown_options.append({"label": element, "value": element, "disabled": False})

    return dropdown_options


# Define date range
start_date = dt.datetime(2024, 10, 20)
# end_date = dt.datetime.today()
end_date = sunday_from_nba_week(df_string_for_graph_2().columns.max())

# Convert to integer timestamps
start_timestamp = int(start_date.timestamp())
end_timestamp = int(end_date.timestamp())


def get_datemarks_from_wk(start=start_date, end=end_date, step=7):
    """Generate date marks with start, end, and up to 2 evenly spaced intermediates."""
    marks = {}

    start_week = nba_week_from_date(start)
    end_week = nba_week_from_date(end)

    # Always include the first and last weeks
    marks[start_week] = start.strftime("%b. %-d")
    marks[end_week] = end.strftime("%b. %-d")

    total_weeks = end_week - start_week

    if total_weeks >= 4:  # Only show intermediates if enough space
        mid1_week = start_week + total_weeks // 3
        mid2_week = start_week + 2 * (total_weeks // 3)

        # Ensure the intermediates aren't duplicates of start or end
        if mid1_week != start_week and mid1_week != end_week:
            mid1_date = start + timedelta(weeks=(mid1_week - start_week))
            marks[mid1_week] = mid1_date.strftime("%b. %-d")

        if mid2_week != start_week and mid2_week != end_week:
            mid2_date = start + timedelta(weeks=(mid2_week - start_week))
            marks[mid2_week] = mid2_date.strftime("%b. %-d")

    # Ensure marks are ordered by week number
    return dict(sorted(marks.items()))


##### APP #####
app = Dash(__name__)
# buffer - io.StringIO()
server = app.server
app.title = "DEV: NBA Power Rankings Viz"

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("Visualizing NBA Power Rankings", id="page-title"),
                html.H3(
                    f"Tracking NBA.com, ESPN, BR, and other top sources to make sense of the league's glorious chaos.",
                    id="page-subtitle",
                ),
                # html.Div(className="shape-sep"),
                html.Hr(),
                html.H5("Created by Keegan Morris", className="byline"),
            ],
            id="header-div",
        ),
        html.Div(
            [
                # Comment
                html.Div(
                    [
                        # html.H5('Select Conference/Division', className="button-label"),
                        html.Div(
                            [
                                html.Div(id="graph-title"),
                                html.Div(
                                    [
                                        dcc.Checklist(
                                            id="all-teams-checkbox",
                                            options=[
                                                {"label": "  All Teams", "value": "all"}
                                            ],
                                            value=["all"],
                                        ),
                                        dcc.Dropdown(
                                            make_dropdown_options(),
                                            id="team-dropdown",
                                            className="check-label",
                                            value=["West", "East"],
                                            # clearable=False,
                                            multi=True,
                                            disabled=False,
                                        ),
                                    ],
                                    id="team-dropdown-subdiv",
                                    className="button-grp",
                                ),
                                dcc.Store(id="previous-all-teams-checkbox", data=[]),
                            ],
                            id="team-dropdown-select-div",
                        )
                    ],
                    id="graph-header",
                ),
                # ],
                # id="team-dropdown-div"),
                # html.Div([
                html.Div(
                    [
                        dcc.Graph(
                            # figure=make_fig(df_string_for_graph_2()),
                            id="pr-graph",
                        ),
                        dcc.Store(id="trace-visibility-store", data=[True] * 30),
                    ],
                    id="graph-subdiv",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.RangeSlider(
                                    step=1,
                                    id="date-range-slider-wk",
                                    min=nba_week_from_date(start_date),
                                    max=nba_week_from_date(end_date),
                                    marks=get_datemarks_from_wk(
                                        start=start_date, end=end_date
                                    ),
                                    tooltip={
                                        "always_visible": True,
                                        "placement": "bottom",
                                        "transform": "getSundayByNBAWeek",
                                    },
                                ),
                            ],
                            id="slider-div",
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.RadioItems(
                                    [
                                        {
                                            "label": "Default View",
                                            "value": "def-view",
                                        },
                                        {
                                            "label": "His/Lows",
                                            "value": "his-los",
                                        },
                                        {
                                            "label": "Ranking vs Record",
                                            "value": "record",
                                        },
                                        {
                                            "label": "Rises/Drops",
                                            "value": "rises",
                                        },
                                    ],id='graph-layouts-options', value='def-view',
                                ),
                                html.Div(id='view-output')
                            ],
                            id="graph-layouts",
                            
                        ),
                    ]
                ),
            ],
            id="graph-div",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Details(
                            [
                                html.Summary("Filters"),
                                html.Div(
                                    className="button-array-html",
                                    children=[
                                        html.Div(
                                            [
                                                html.H5(
                                                    "Display Range",
                                                    id="range-header",
                                                    className="button-label",
                                                ),
                                                dcc.RadioItems(
                                                    [
                                                        {
                                                            "label": "Full Range*",
                                                            "value": "def-range",
                                                        },
                                                        {
                                                            "label": "Top 5",
                                                            "value": "bot-5",
                                                        },
                                                        {
                                                            "label": "Bottom 5",
                                                            "value": "top-5",
                                                        },
                                                    ],
                                                    "def-range",
                                                    id="rank-radio",
                                                    labelStyle={
                                                        "display": "inline-block"
                                                    },
                                                    className="radio-label",
                                                ),
                                                html.P(
                                                    "*default",
                                                    id="note1",
                                                    className="footnote",
                                                ),
                                            ],
                                            id="rank-range",
                                            className="button-grp",
                                        ),
                                        html.Div(
                                            [
                                                html.H5(
                                                    "Update XTicks Labels",
                                                    className="button-label",
                                                ),
                                                html.Div(
                                                    [
                                                        dcc.Checklist(
                                                            id="week-day-check",
                                                            className="check-label",
                                                            options=[
                                                                {
                                                                    "label": "Display Weeks",
                                                                    "value": "linear",
                                                                }
                                                            ],
                                                            value=["dates"],
                                                        ),
                                                    ],
                                                ),
                                            ],
                                            id="xticks-labels",
                                            className="button-grp",
                                        ),
                                        html.Div(
                                            [
                                                html.H5(
                                                    "Mark Scatter Points",
                                                    className="button-label",
                                                ),
                                                html.Div(
                                                    [
                                                        dcc.Checklist(
                                                            id="dot-check",
                                                            className="check-label",
                                                            options=[
                                                                {
                                                                    "label": "Show Marks",
                                                                    "value": "show",
                                                                }
                                                            ],
                                                            value=[],
                                                        ),
                                                    ],
                                                ),
                                            ],
                                            id="show-dots",
                                            className="button-grp",
                                        ),
                                    ],
                                    id="button_groups",
                                ),
                            ],
                            id="lower-section",
                        ),
                    ]
                ),
            ]
        ),
        html.Div(
            id="text-attribution",
            children=[
                html.A(
                    f"keegan-morris.com",
                    href="https://keegan-morris.com/2025/02/25/dash-deploy-power-rankings/",
                    target="_blank",
                    id="attrib-url",
                ),
                html.P(
                    f"data updated {clean_date(str(get_max_pr_date()))} ({data_points} observations)",
                    id="attrib-date",
                ),
                # html.P(f"", id='observations'),
            ],
        ),
    ]
)


def dropdown_update_layout(value):
    teams = read_nba_teams_ref()

    # List to hold visibility settings for each trace
    visibility = []

    for _, row in teams.iterrows():
        team = row["teamname"]
        conf = row["conference"]
        div = row["division"]

        # Determine visibility per trace
        if value == "All Teams":
            visibility.append(True)  # Show all traces
        else:
            visibility.append(value in [team, conf, div])

    return [{"visible": v} for v in visibility]


def set_chart_yrange(value):
    """Update chart y_range based from radio button input."""
    options = {
        "bot-5": {
            "yrange": [5.5, 0.5],
            "dtick": 1,
            "tickvals": [1, 3, 5],
            "title_standoff": 22.8,
        },
        "top-5": {
            "yrange": [30.5, 25.5],
            "dtick": 1,
            "tickvals": [30, 28, 26],
            "title_standoff": 12,
        },
        "def-range": {
            "yrange": [30.5, 0.5],
            "dtick": 5,
            "tickvals": [1, 10, 20, 30],
            "title_standoff": 12,
        },
    }
    settings = options.get(value, options[value])
    return (
        settings["yrange"],
        settings["dtick"],
        settings["tickvals"],
        settings["title_standoff"],
    )


def set_hovertemplate_format(value):
    """Set appropriate hover template format based on display mode."""
    if "linear" in value:
        hovertemplate_btmlines = "<br><b>week</b>: %{x}<br><b>rank</b>: %{y}"
    else:
        date = sunday_from_nba_week(value)
        customdata = date
        hovertemplate_btmlines = "<br><b>date</b>: %{text}<br><b>rank</b>: %{y}"
        # date = sunday_from_nba_week(value)
    return hovertemplate_btmlines


def set_xticks(value):
    """Alternate between date and nba_week # XTick labels."""
    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime("%b. %-d") for date in sundays_array]

    if value == ["dates", "linear"]:
        # Convert sundays_array to strings in the format 'YYYY-MM-DD'
        xticks_set = dict(
            title=dict(
                text="<b>Week</b>",
                font_size=18,
            ),
            tickmode="array",
            tickvals=weeks_array[::4],
            ticktext=weeks_array[::4],
            # dtick = 10,
            tickfont=dict(size=12),
            tickangle=0,
        )
    else:

        xticks_set = dict(
            tickmode="array",
            tickvals=weeks_array[::4],
            ticktext=sundays_str[::4],
            # dtick = 20,
            tickfont=dict(size=12),
        )
    return xticks_set


def df_string_for_graph_subset(team_input):
    """Filter dataframe based on input."""
    applicable_teams = set()
    df = df_string_for_graph_2()

    # Check if "All Teams" is selected (case-insensitive)
    if any(i.lower() == "all teams" for i in team_input):
        return df  # Return the entire DataFrame

    for i in team_input:
        team = teams.find_team(i)
        if team:
            applicable_teams.add(team)
        # Handle conferences
        elif i in ["East", "West"]:
            applicable_teams.update(t for t in df.index if teams.nba_conf(t) == i)
        # Handle divisions
        elif i in [
            "Southwest",
            "Southeast",
            "Atlantic",
            "Pacific",
            "Northwest",
            "Central",
        ]:
            applicable_teams.update(t for t in df.index if teams.nba_div(t) == i)

    # Filter the DataFrame to include only rows where the index (teamname) is in applicable_teams
    filtered_df = df[df.index.isin(applicable_teams)]
    return filtered_df


def show_title(team_input, checkbox):
    """Show selected teams ('All Teams' or otherwise) based on graph filters."""
    if checkbox:
        return "Power Rankings: All Teams"
    elif all(conference in team_input for conference in ["West", "East"]):
        return "Power Rankings: All Teams"
    elif all(
        division in team_input
        for division in [
            "Atlantic",
            "Central",
            "Southeast",
            "Southwest",
            "Pacific",
            "Northwest",
        ]
    ):
        return "Power Rankings: All Teams"
    elif team_input == []:
        return "No Input"
    elif len(team_input) > 1:
        return "Power Rankings: Multiple Teams"
    else:
        return " ".join(["Power Rankings:", team_input[0]])


def date_range_slider_set(slider):
    # print(slider==None)
    if slider is None:
        start_date = 0.85
        end_date = (
            nba_week_from_date(
                sunday_from_nba_week(df_string_for_graph_2().columns.max())
            )
            + 0.15
        )
        # print(end_date)
    else:
        # Ensure slider is a tuple or list with two elements
        if isinstance(slider, (tuple, list)) and len(slider) == 2:
            start_date, end_date = slider
        else:
            # Fallback to default values if slider is invalid
            start_date = 1
            end_date = (
                nba_week_from_date(
                    sunday_from_nba_week(df_string_for_graph_2().columns.max())
                )
                + 0.15
            )

    return start_date, end_date

def create_weekly_summary():
    games_df = pd.read_csv('250408games_df.csv')
    games_df = games_df.reset_index()
    games_df['most_recent_sunday'] = games_df['date'].apply(lambda x: most_recent_sunday(pd.to_datetime(x)))
    weekly_summary = games_df.groupby(['team_name_abbr','most_recent_sunday'])[['rolling_20', 'rolling_10', 'rolling_15']].mean().reset_index()

    return weekly_summary

print(create_weekly_summary())

def create_hi_graph(filtered_df):
    """Create graph for highs and lows for individual team."""
    #pass
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=filtered_df['nba_week_'],
        y=round(filtered_df['ranking_mean'],2),
        #line=dict(color=color),
        name='Mean Ranking'
    ))
    
    x = filtered_df['nba_week_'].tolist() + filtered_df['nba_week_'].iloc[::-1].tolist()
    y_upper = filtered_df['ranking_max'].tolist()
    y_lower = filtered_df['ranking_min'].iloc[::-1].tolist()  # reversed
    y = y_upper + y_lower

    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        fill='toself',
        #fillcolor=hex_to_rgba(color, 0.2),
        line=dict(color='rgba(0,0,0,0)'),  # transparent line
        hoverinfo='skip',
        name='Min-Max Range'
    ))

    # Optional: Adjust layout
    fig.update_layout(
        template='plotly_white',
        title=f'NBA Power Rankings Visualized: <span style="color: {color};">{team}</span><br><span style="color: gray;font-size: .8em">Highs and Lows of Weekly Rankings</span>',
        xaxis_title='Week',
        yaxis_title='Ranking',
        yaxis=dict(range=(30,1)),  # since lower rankings are better
        showlegend=False,
        width=800,
        hovermode='x unified',

        #hovermode='x unified'
    )
    
    return fig



def create_record_graph():
    """Create graph for PR vs running record for individual team."""
    fig= make_subplots(specs=[[{'secondary_y': True}]])

    team = input_df['teamname'].min()

    if team != 'Brooklyn Nets':
        color2= teams.team_color2(team)
    else:
        color2 = teams.team_color3(team)



    weekly_summary_filtered = weekly_summary.loc[weekly_summary['team_name_abbr'] == teams.nba_abbrname(team)]
    fig.add_trace(go.Scatter(
        x=weekly_summary_filtered['nba_week'],
        y=round(weekly_summary_filtered['rolling_15'],2),
        #mode='lines+markers',
        line=dict(color=color2, dash='dot'),# width=4),

    ), secondary_y=True,),
    
    
    # Main line (mean)
    fig.add_trace(go.Scatter(
        x=input_df['nba_week'],
        y=round(input_df['ranking_mean'],2),
        line=dict(color=color),
        name='Mean Ranking'
    ))


    fig.update_layout(
        title=f'NBA Power Rankings Visualized: <span style="color: {color};">{team}</span><br><span style="font-size: 0.8em; color: gray;">Power Rankings Performance vs. Running Win % (last 15 games)</span>',
        template='plotly_white',
        xaxis_title='Week',
        yaxis_title='Ranking',
        yaxis=dict(range=(30,0)),  # since lower rankings are better
        showlegend=False,
        width=800,
        hovermode='x unified',
        #hovermode='x unified'
        yaxis2=dict(
            range=(0,1),
            tickmode='sync'
        )

    )

    return fig

def create_rises_graph():
    """Create graph for rises and falls for individual team."""
    #pass
    print('rises')


def choose_team_graph(radio_options):
    """Choose what individual team graph to display based on radio input."""
    if radio_options == 'record':
        return create_record_graph()
    if radio_options == 'his-los':
        return create_hi_graph()
    if radio_options == 'rises':
        return create_rises_graph()
    else:
        # Return normal graph
        pass

@app.callback(
    Output("pr-graph", "figure"),
    Output("trace-visibility-store", "data"),
    Output("team-dropdown", "disabled"),
    Output("graph-title", "children"),
    Output("view-output", "children"),
    Input("date-range-slider-wk", "value"),
    Input("rank-radio", "value"),
    Input("week-day-check", "value"),
    Input("all-teams-checkbox", "value"),
    Input("team-dropdown", "value"),
    Input("graph-layouts-options", "value"),
    Input("dot-check", "value"),
    Input("pr-graph", "restyleData"),
    State("trace-visibility-store", "data"),
    State("pr-graph", "figure"),
)
def update_graph(
    date_range_slider,
    rank_radio,
    week_day_check,
    all_teams_checkbox,
    team_dropdown,
    graph_layouts_options,
    dot_check,
    restyle_data,
    visibility_state,
    figure,
):
    
    

    # Step 1: Create df
    df = df_string_for_graph_2()

    chart_settings = set_chart_yrange(rank_radio)
    chart_yrange = chart_settings[0]
    chart_dtick = chart_settings[1]
    chart_tickvals = chart_settings[2]

    graph_title = show_title(team_dropdown, all_teams_checkbox)
    filtered_df = df_string_for_graph_subset(team_dropdown)
    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime("%b. %-d") for date in sundays_array]

    # if checkbox selected
    if all_teams_checkbox:
        # DROPDOWN IS INACTIVE
        dropdown_disabled = True
        filtered_df = df_string_for_graph_2()
    else:
        dropdown_disabled = False

    if isinstance(team_dropdown, list):
        selected_teams = team_dropdown

    fig = go.Figure()
    
    teams_no = len(filtered_df.index)
    #print(teams_no)
    
    if teams_no == 1:
        fig = create_hi_graph(filtered_df)
        #return fig

    else: 
        for team in filtered_df.index:

            base_hover = f"<b>{team.upper()}</b>"

            fig.add_trace(
                go.Scatter(
                    x=filtered_df.columns,  # Weeks
                    y=filtered_df.loc[team],  # Rankings
                    mode="lines+markers",
                    line=dict(width=2),
                    marker=dict(
                        size=6,
                    ),
                    name=teams.nba_abbrname(team),
                    opacity=0.85,
                    marker_color=teams.team_color1(team),
                    text=date_strings,
                    hovertemplate=base_hover,
                    visible=True,
                    showlegend=True,
                )
            )

    # Step 3: Handle legend interactions (update visibility_state)
    if restyle_data:
        if isinstance(restyle_data[0], dict) and "visible" in restyle_data[0]:
            new_visibility = restyle_data[0]["visible"]
            trace_indices = restyle_data[1]

            for i, trace_idx in enumerate(trace_indices):
                if trace_idx < len(visibility_state):
                    visibility_state[trace_idx] = new_visibility[i]

    # Step 4: Initialize visibility_state if it's None or invalid
    if visibility_state is None or len(visibility_state) != len(fig.data):
        visibility_state = [True] * len(fig.data)  # Default to all traces visible

    # Step 5: Apply team dropdown filtering
    dropdown_visibility = dropdown_update_layout(team_dropdown)
    for i, trace in enumerate(fig.data):
        trace.visible = dropdown_visibility[i]["visible"] and visibility_state[i]

    # Step 6: Reapply the visibility state to preserve legend-selected traces
    if visibility_state and len(visibility_state) == len(fig.data):
        for i, trace in enumerate(fig.data):
            trace.visible = visibility_state[i]
    else:
        # If visibility_state is invalid, ensure all traces are visible
        for trace in fig.data:
            trace.visible = True

    start_week, end_week = date_range_slider_set(date_range_slider)
    # Update layout for better visualization
    fig.update_layout(
        autosize=True,
        height=620,
        xaxis_title="Week",
        yaxis_title="Ranking",
        legend_title="Teams",
        # paper_bgcolor='#FBFBFB',
        plot_bgcolor="white",
        template="presentation",
        font_family="JetBrains Mono",
        margin=dict(
            t=45,
            l=45,
            r=105,
        ),
        xaxis=dict(
            domain=[0.05, 0.97],
            range=[start_week, end_week],
            autorange=False,
            tickmode="array",
            tickvals=weeks_array,
            ticktext=sundays_str,
            title=dict(
                text="<b>Date</b>",
                # family="JetBrains M",
                font_size=18,
            ),
            tickfont=dict(family="JetBrains Mono", size=12),
            # tickangle=70,
            showline=True,
            linecolor="black",
        ),
        yaxis=dict(
            domain=[0, 1],
            range=chart_yrange,
            dtick=chart_dtick,
            tickvals=chart_tickvals,
            # title_standoff=title_standoff
            title=dict(
                text="<b>Mean Ranking</b>",
                font_size=18,
            ),
            tickfont=dict(size=12, family="JetBrains Mono"),
        ),
        hoverlabel=dict(font=dict(family="JetBrains Mono")),
        legend=dict(
            x=1,
            y=1,
            xanchor="left",
            yanchor="top",
            # itemwidth=420,
            orientation="v",
            title=dict(
                text="<b>NBA Teams</b>",
            ),
            # xanchor='center'),
            # xanchor='left',
            font=dict(
                size=12,
                weight="normal",
            ),
            traceorder="normal",
            # bordercolor="Black",
            # borderwidth=2,
            entrywidth=70,
        ),
    )

    if dot_check == ["show"]:
        linemode = "lines+markers"
        fig.update_traces(mode=linemode, marker=dict(size=6))
    else:
        linemode = "lines"
        fig.update_traces(mode=linemode)

    for trace in fig.data:
        additional_hover = set_hovertemplate_format(week_day_check)
        trace.hovertemplate += additional_hover + "<extra></extra>"
    # fig.update_traces(hovertemplate = trace.hovertemplate + set_hovertemplate_format(week_day_check))

    fig.update_layout(
        yaxis=dict(
            range=chart_yrange,
            dtick=chart_dtick,
            tickvals=chart_tickvals,
            # title_standoff=title_standoff
        ),
        xaxis=dict(
            **set_xticks(week_day_check),  # Apply x-ticks settings
        ),
    )

    #pio.write_html(fig, file="nba_plot.html", full_html=False)
    return fig, [trace.visible for trace in fig.data], dropdown_disabled, graph_title, graph_layouts_options


if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_hot_reload=False)
