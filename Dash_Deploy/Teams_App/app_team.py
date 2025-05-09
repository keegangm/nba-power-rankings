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
import numpy as np

# import io
from base64 import b64encode

external_stylesheets = [
    "assets/style_2.css",
]


### Finding and Reading Ranking Files
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


def get_max_pr_date():
    """Get date of most recent power rankings set present in 'latest_powerrankings.csv' file."""
    rk = read_ranking_file()
    # print(rk)
    sorted_df = rk.sort_values(by="date", ascending=False)
    max_date = sorted_df.max()["date"]
    return max_date


def nba_week_from_date(date=today):
    """Get NBA Week number from date."""
    wk_df = read_nba_week()
    nba_week_no = wk_df[wk_df["sunday"] <= date].nba_week.max()

    return int(nba_week_no)



def most_recent_sunday(date):
    """Find date of most recent Sunday ('round down')."""
    date = pd.to_datetime(date)
    if date.weekday() == 6:
        return date
    else:
        return date - pd.to_timedelta(date.weekday() + 1, unit="D")


def create_and_merge_rank_week():
    """Merge ranking and week files"""
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


df = create_season_rks_df(create_and_merge_rank_week())
#print(df.loc[df['nba_week'] == 1].head())

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


#print(create_rk_pt(df))

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


def df_string_for_graph_2(start="2024-10-20", end="2025-04-13"):
    ranking_file = find_file("latest_powerrankings")
    df = create_filtered_df(create_and_merge_rank_week(), start, end)
    rk_pt = create_rk_pt(df)

    return rk_pt


def df_hi_los(start="2024-10-20", end="2025-04-13"):
    ranking_file = find_file("latest_powerrankings")
    df = create_filtered_df(create_and_merge_rank_week(), start, end)

    grouped_df = df.groupby(["teamname", "nba_week", "sunday"]).agg(
        {"ranking": ["mean", "min", "max"]}
    )

    grouped_df = grouped_df.reset_index()
    grouped_df.columns = [
        "_".join(col).strip() if isinstance(col, tuple) else col
        for col in grouped_df.columns
    ]
    grouped_df = grouped_df.rename(
        columns={"nba_week_": "nba_week", "sunday_": "sunday", "teamname_": "teamname"}
    )

    # rk_pt = create_rk_pt(df)

    return grouped_df


def get_max_min_week(start="2024-10-20", end="2025-04-13"):
    """Get NBA WEEK # for start and end date"""

    return nba_week_from_date(end), nba_week_from_date(start)


def sunday_from_nba_week(week: int):
    """Lookup date for Sunday of week number."""
    try:
        wk = read_nba_week()
        return (wk.loc[wk["nba_week"] == week, "sunday"]).item()
    except:
        return None
    
print(sunday_from_nba_week(1))


def create_sundays_array():
    """Create arrays of Sundays and corresponding NBA week #s."""
    weeks_array = []
    sundays_array = []
    for i in range(1, 30):
        weeks_array.append(i)
        # sundays_array.append(sunday_lookup(i)+1)
        sundays_array.append(sunday_from_nba_week(i))

    return weeks_array, sundays_array


date_strings = [d.strftime("%b. %-d") for d in create_sundays_array()[1]]


def make_team_dropdown_options():
    """Make Dropdown Options"""
    teams = read_nba_teams_ref()
    dropdown_options = []

    team_set = set()

    for index, row in teams.iterrows():
        team = row["teamname"]
        team_set.add(team)

    # dropdown_options.append({"label": "--- Conferences ---", "value": "divider", "disabled": True})

    for element in sorted(team_set):
        dropdown_options.append({"label": element, "value": element, "disabled": False})

    return dropdown_options


# Define date range
start_date = dt.datetime(2024, 10, 20)
# end_date = dt.datetime.today()
end_date = dt.datetime(2025, 4, 13)

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
app = Dash(__name__, external_stylesheets=external_stylesheets)
# buffer - io.StringIO()
server = app.server
app.title = "APP: NBA Power Rankings Viz"

app.layout = html.Div(
    [
        html.Div(
            [
                # Comment
                html.Div(
                    [
                        # html.H5('Select Conference/Division', className="button-label"),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H3(id="graph-title"),
                                        html.H5(id="graph-subtitle"),
                                    ],
                                    id="title-div",
                                ),
                                html.Div(
                                    [
                                        dcc.Dropdown(
                                            make_team_dropdown_options(),
                                            id="team-dropdown",
                                            className="check-label",
                                            value="Los Angeles Lakers",
                                            # clearable=False,
                                            # multi=True,
                                            disabled=False,
                                        ),
                                    ],
                                    id="team-dropdown-subdiv",
                                    className="button-grp",
                                ),
                                # dcc.Store(id="previous-all-teams-checkbox", data=[]),
                            ],
                            id="team-dropdown-select-div",
                        )
                    ],
                    id="graph-header",
                ),
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
                                dcc.RadioItems(
                                    [
                                        {
                                            "label": "Default View",
                                            "value": "def-view",
                                        },
                                        {
                                            "label": "Weekly Highs/Lows",
                                            "value": "his-los",
                                        },
                                        {
                                            "label": "Ranking vs Record",
                                            "value": "record",
                                        },
                                        # {
                                        #    "label": "Rises/Drops",
                                        #    "value": "rises",
                                        # },
                                    ],
                                    id="graph-layouts-options",
                                    value="def-view",
                                ),
                                html.Div(id="view-output"),
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
                                html.Summary("Filters"),
                                html.Div(
                                    className="button-array-html",
                                    children=[
                                        html.Div(
                                            [
                                                html.H5(
                                                    "Y-Axis Bounds",
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
                                        # html.Div(
                                        #    [
                                        #        html.H5(
                                        #            "Update XTicks Labels",
                                        #            className="button-label",
                                        #        ),
                                        #        html.Div(
                                        #            [
                                        #                dcc.Checklist(
                                        #                    id="week-day-check",
                                        #                    className="check-label",
                                        #                    options=[
                                        #                        {
                                        #                            "label": "Display Weeks",
                                        #                            "value": "linear",
                                        #                        }
                                        #                    ],
                                        #                    value=["dates"],
                                        #                ),
                                        #            ],
                                        #        ),
                                        #    ],
                                        #    id="xticks-labels",
                                        #    className="button-grp",
                                        # ),
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


def show_title(team_input, graph_layout_view):
    """Show selected teams ('All Teams' or otherwise) based on graph filters."""
    if graph_layout_view == "def-view":
        return team_input, "Power Rankings Performance by Week"
    elif graph_layout_view == "record":
        return team_input, "Power Rankings vs. 20-Game Rolling Record"
    else:
        return team_input, "Power Rankings Spread by Week"


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
    games_df = pd.read_csv("250408games_df.csv")
    games_df = games_df.reset_index()
    games_df["most_recent_sunday"] = games_df["date"].apply(
        lambda x: most_recent_sunday(pd.to_datetime(x))
    )
    weekly_summary = (
        games_df.groupby(["team_name_abbr", "most_recent_sunday"])[
            ["rolling_20", "rolling_10", "rolling_15"]
        ]
        .mean()
        .reset_index()
    )
    # week_lookup = wk.set_index('sunday')['nba_week'].to_dict()
    weekly_summary["nba_week"] = weekly_summary["most_recent_sunday"].map(
        nba_week_from_date
    )
    return weekly_summary


weekly_summary = create_weekly_summary()


def hex_to_rgba(hex_color, alpha=1.0):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def create_hi_graph(team):
    """Create graph for highs and lows for individual team."""
    df = df_hi_los()
    df["sunday"] = df["sunday"] - pd.to_timedelta(-7, unit="D")
    df = df.loc[df["teamname"] == team]

    base_hover = f"<b>{team.upper()}</b>"

    color = teams.team_color1(team)

    fig = go.Figure()

    ## His and Lows
    x = df["nba_week"].tolist() + df["nba_week"].iloc[::-1].tolist()
    y_upper = df["ranking_max"].tolist()
    y_lower = df["ranking_min"].iloc[::-1].tolist()  # reversed
    y = y_upper + y_lower

    ## Normal Trace
    fig.add_trace(
        go.Scatter(
            x=df["nba_week"],
            y=round(df["ranking_mean"], 2),
            line=dict(color=color),
            name="Mean Rank",
            text=date_strings[:-1],
            customdata=list(zip(df["ranking_max"], df["ranking_min"])),
            hovertemplate=(
                f"{base_hover}<br>"
                "<b>date:</b> %{text}<br>"
                "<b>mean rank:</b> %{y}<br>"
                "<b>best rank:</b> %{customdata[1]}<br>"
                "<b>worst rank:</b> %{customdata[0]}<br><extra></extra>"
            ),
        )
    )

    ## Min-Max Range Trace
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            fill="toself",
            fillcolor=hex_to_rgba(color, 0.2),
            line=dict(color="rgba(0,0,0,0)"),  # transparent line
            hoverinfo="skip",
            name="Min-Max Range",
        )
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Week",
        yaxis_title="Ranking",
        showlegend=False,
        # hovermode="x unified",
    )

    return fig

#def create_record_graph(team):
#    pass

#    df = df_hi_los()
#    df["sunday"] = df["sunday"] - pd.to_timedelta(-7, unit="D")
#    #df = df.loc[df["teamname"] == team]

def parse_date_format(date):
    pass

def create_record_graph(team):
    df = df_hi_los()
    df["sunday"] = df["sunday"] - pd.to_timedelta(-7, unit="D")
    df = df.loc[df["teamname"] == team]

    base_hover = f"<b>{team.upper()}</b>"

    color = teams.team_color1(team)

    fig = make_subplots(specs=[[{'secondary_y': True}]])

    if team != "Charlotte Hornets":
        weekly_summary_filtered = weekly_summary.loc[
            weekly_summary["team_name_abbr"] == teams.nba_abbrname(team)
        ]
    else:
        weekly_summary_filtered = weekly_summary.loc[
            weekly_summary["team_name_abbr"] == "CHO"
        ]
    fig.add_trace(
        go.Scatter(
            x=df['nba_week'],           
            y=round(df["ranking_mean"], 2),
            line=dict(width=3),
            marker=dict(
                size=6,
            ),
            name=teams.nba_abbrname(team),
            opacity=0.85,
            marker_color=teams.team_color1(team),
            customdata=list(zip(date_strings, df.columns)),
            text=date_strings,
            hovertemplate=(
                f"{base_hover}<br>"
                "<b>date:</b> %{text}<br>"
                "<b>mean rank:</b> %{y}<br><extra></extra>"
            )
        )
    ),
    if team in ("Brooklyn Nets", "San Antonio Spurs"):
        roll_color = "slategrey"
    else:
        roll_color = "black"

    # print(weekly_summary_filtered)
    fig.add_trace(
        go.Scatter(
            x=weekly_summary_filtered["nba_week"],
            y=round(weekly_summary_filtered["rolling_20"], 2),
            # mode='lines+markers',
            # mode="lines+text",
            # text="Win% over last 20 gms",
            text=date_strings,  # Adjust text to match previous column
            line=dict(color=roll_color, dash="dot", width=1.5),  # width=4),
            hovertemplate=(
                f"<b>Win% (last 20 gms): {teams.nba_abbrname(team)}</b><br>"
                "<b>date:</b> %{text}<br>"
                "<b>win%:</b> %{y}<extra></extra>"
            ),
        ),
        secondary_y=True,
    ),

    fig.update_layout(
        template="plotly_white",
        # template="presentation",
        font_family="JetBrains Mono",
        #    xaxis_title="Week",
        #    yaxis_title="Ranking",
        yaxis=dict(range=(30, 0)),  # since lower rankings are better
        showlegend=False,
        #    width=800,
        #    hovermode="x unified",
        # hovermode='x unified',
        yaxis2=dict(
            title=dict(
                text=f"<b>Rolling Team Win%<br>(last 20 gms)</b>",
                font_size=18,
            ),
            range=(0, 1),
            tickvals=[1, 0.5, 0],
            tickfont=dict(size=12),
            # size=12,
            # tickmode="sync"
        ),
    )
    return fig


"""
def create_record_graph(team):
    """
"""Create graph for PR vs running record for individual team."""
"""
    df = df_string_for_graph_2()
    df = df.reset_index()
    df = df.loc[df["teamname"] == team]
    print(df)

    base_hover = f"<b>{team.upper()}</b>"
    # print(weekly_summary)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if team != "Charlotte Hornets":
        weekly_summary_filtered = weekly_summary.loc[
            weekly_summary["team_name_abbr"] == teams.nba_abbrname(team)
        ]
    else:
        weekly_summary_filtered = weekly_summary.loc[
            weekly_summary["team_name_abbr"] == "CHO"
        ]
    # Main line (mean)
    fig.add_trace(
        go.Scatter(
            x=df.columns,  # Weeks
            y=df.loc[team],  
            # mode="lines+markers",
            line=dict(width=3),
            marker=dict(
                size=6,
            ),
            name=teams.nba_abbrname(team),
            opacity=0.85,
            marker_color=teams.team_color1(team),
            customdata=list(zip(date_strings, df.columns)),
            text=date_strings,
            hovertemplate=(
                f"{base_hover}<br>"
                "<b>date:</b> %{customdata[0]}<br>"
                "<b>rank:</b> %{y}<br><extra></extra>"
            ),
            visible=True,
            # showlegend=True,
        )
    )

    if team in ("Brooklyn Nets", "San Antonio Spurs"):
        roll_color = "slategrey"
    else:
        roll_color = "black"

    # print(weekly_summary_filtered)
    fig.add_trace(
        go.Scatter(
            x=weekly_summary_filtered["nba_week"],
            y=round(weekly_summary_filtered["rolling_20"], 2),
            # mode='lines+markers',
            # mode="lines+text",
            # text="Win% over last 20 gms",
            text=date_strings,  # Adjust text to match previous column
            line=dict(color=roll_color, dash="dot", width=1.5),  # width=4),
            hovertemplate=(
                f"<b>Win% (last 20 gms): {teams.nba_abbrname(team)}</b><br>"
                "<b>date:</b> %{text}<br>"
                "<b>win%:</b> %{y}<extra></extra>"
            ),
        ),
        secondary_y=True,
    ),

    fig.update_layout(
        template="plotly_white",
        # template="presentation",
        font_family="JetBrains Mono",
        #    xaxis_title="Week",
        #    yaxis_title="Ranking",
        yaxis=dict(range=(30, 0)),  # since lower rankings are better
        showlegend=False,
        #    width=800,
        #    hovermode="x unified",
        # hovermode='x unified',
        yaxis2=dict(
            title=dict(
                text=f"<b>Rolling Team Win%<br>(last 20 gms)</b>",
                font_size=18,
            ),
            range=(0, 1),
            tickvals=[1, 0.5, 0],
            tickfont=dict(size=12),
            # size=12,
            # tickmode="sync"
        ),
    )

    return fig
"""


def create_rises_graph(team):
    """Create graph for rises and falls for individual team."""
    # pass
    # print("rises")

#df = df_string_for_graph_2()
#df = df.reset_index()
#print(df)

def normal_graph(team):

    df = df_hi_los()
    df["sunday"] = df["sunday"] - pd.to_timedelta(-7, unit="D")
    df = df.loc[df["teamname"] == team]

    base_hover = f"<b>{team.upper()}</b>"

    color = teams.team_color1(team)

    fig = make_subplots(specs=[[{'secondary_y': True}]])

    fig.add_trace(
        go.Scatter(
            x=df['nba_week'],           
            y=round(df["ranking_mean"], 2),
            line=dict(width=3),
            marker=dict(
                size=6,
            ),
            name=teams.nba_abbrname(team),
            opacity=0.85,
            marker_color=teams.team_color1(team),
            customdata=list(zip(date_strings, df.columns)),
            text=date_strings,
            hovertemplate=(
                f"{base_hover}<br>"
                "<b>date:</b> %{text}<br>"
                "<b>mean rank:</b> %{y}<br><extra></extra>"
            )
        )
    ),
    return fig


def choose_team_graph(radio_options, team):
    if team == []:
        team = "Los Angeles Lakers"
    # print(radio_options)
    """Choose what individual team graph to display based on radio input."""
    if radio_options == "record":
        try:
            return create_record_graph(team)
        except:
            return create_record_graph("Los Angeles Lakers")
        # return normal_graph(team)
    if radio_options == "his-los":
        try:
            return create_hi_graph(team)
        except:
            return create_hi_graph("Los Angeles Lakers")
    # if radio_options == "rises":
    #    try:
    #        return create_rises_graph(team)
    #    except:
    else:
        try:
            return normal_graph(team)
        except:
            return normal_graph("Los Angeles Lakers")


@app.callback(
    Output("pr-graph", "figure"),
    Output("graph-title", "children"),
    Output("graph-subtitle", "children"),
    # Output("view-output", "children"),
    Input("date-range-slider-wk", "value"),
    Input("rank-radio", "value"),
    # Input("week-day-check", "value"),
    Input("team-dropdown", "value"),
    Input("graph-layouts-options", "value"),
    Input("dot-check", "value"),
    # State("pr-graph", "figure"),
)
def update_graph(
    date_range_slider,
    rank_radio,
    # week_day_check,
    team_dropdown,
    graph_layouts_options,
    dot_check,
    # figure,
):

    team = team_dropdown

    # Step 1: Create df
    df = df_string_for_graph_2()
    df = df.reset_index()
    df = df.loc[df["teamname"] == team]

    chart_settings = set_chart_yrange(rank_radio)
    chart_yrange = chart_settings[0]
    chart_dtick = chart_settings[1]
    chart_tickvals = chart_settings[2]
    try:
        graph_title, graph_subtitle = show_title(team, graph_layouts_options)
        # print(graph_title)
    except:
        graph_title = "Power Rankings: Los Angeles Lakers"
    """
    #print(team_dropdown)
    print(df.head())
    #filtered_df = df_string_for_graph_subset(team_dropdown)
    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime("%b. %-d") for date in sundays_array]
    """

    fig = choose_team_graph(graph_layouts_options, team)

    start_week, end_week = date_range_slider_set(date_range_slider)
    """
    # Update layout for better visualization
    """
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
            r=65,
        ),
        xaxis=dict(
            domain=[0.05, 0.97],
            range=[start_week, end_week],
            autorange=False,
            tickmode="array",
            # tickvals=weeks_array,
            # ticktext=sundays_str,
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
            # dtick=chart_dtick,
            tickvals=chart_tickvals,
            # title_standoff=title_standoff
            title=dict(
                text="<b>Mean Rank</b>",
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

    # hovertemplate_btmlines = "<br><b>date</b>: %{text}<br><b>rank</b>: %{y}"
    # fig.data[0].hovertemplate += hovertemplate_btmlines + "<extra></extra>"

    # fig.update_traces(hovertemplate = trace.hovertemplate + set_hovertemplate_format(week_day_check))
    fig.update_layout(
        yaxis=dict(
            range=chart_yrange,
            dtick=chart_dtick,
            tickvals=chart_tickvals,
            # title_standoff=title_standoff
        ),
        xaxis=dict(
            **set_xticks("linear"),  # Apply x-ticks settings
        ),
    )

    return (
        fig,
        graph_title,
        graph_subtitle,
    )  # , [trace.visible for trace in fig.data], dropdown_disabled, graph_title, graph_layouts_options


if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_hot_reload=False)
