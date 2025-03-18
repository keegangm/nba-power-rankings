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

def find_file(file_name):
    file_name = f"{file_name}.csv"
    possible_paths = [
        os.path.join("Dash_Deploy", "support", "data", file_name),
        os.path.join("support", "data", file_name)
    ]

    for file_path in possible_paths:
        if os.path.exists(file_path):
            return file_path  # Return the first found file

    return None  # File not found in either path

WEEK_REFERENCE_PATH = find_file('nba_weeks_ref')

def read_nba_week():    
    """Read NBA Week from reference file."""
    return pd.read_csv(WEEK_REFERENCE_PATH, parse_dates=['sunday'], dtype={'nba_week': int})

def read_ranking_file():
    """Read NBA Ranking file"""
    #rk = get_csv('latest_powerrankings')
    #rk['date'] = pd.to_datetime(rk['date'])
    rk = pd.read_csv(find_file('latest_powerrankings'), parse_dates=['date'], date_format="%y%m%d") # 02-Dec-24
    return rk

us_central_tz = pytz.timezone('US/Central')
today = dt.datetime.now(us_central_tz).date()
#print(today)

def nba_week_from_date(date=today):
    """Get NBA Week number"""
    wk_df = read_nba_week()
    nba_week_no = wk_df[wk_df['sunday'] <= date].nba_week.max()

    return int(nba_week_no)

def most_recent_sunday(date):
    """Find date of most recent Sunday."""
    date = pd.to_datetime(date)
    if date.weekday() == 6:
        return date
    else:
        return date - pd.to_timedelta(date.weekday() + 1, unit='D')

def create_and_merge_rank_week():

    rk = read_ranking_file()
    wk = read_nba_week()

    rk['sunday'] = rk['date'].apply(most_recent_sunday)
    rk['sunday'] = pd.to_datetime(rk['sunday'])
    wk['sunday'] = pd.to_datetime(wk['sunday'])

    df = pd.merge(rk, wk[['sunday', 'nba_week']], on='sunday', how='left')
    return df

def read_nba_teams_ref():
    nba_teams_ref = pd.read_csv(find_file('nba_teams_data'))
    #nba_teams_ref = get_csv('nba_teams_data')
    return nba_teams_ref

def clean_date(raw_date=None):
    """ Get an external-friendly date in format 'Jan 24, 2025'. """
    if raw_date is not None:
        input_date = parse(raw_date)
    else:
        input_date = dt.datetime.now(us_central_tz).date()

    parsed_date = input_date.strftime("%b. %d, %Y")
    return parsed_date

def create_season_rks_df(df: pd.DataFrame):
    """Filter the DataFrame to only include rows with valid NBA weeks."""
    df = df[df['nba_week'].notna()]
    df['nba_week'] = df['nba_week'].astype(int)
    season_rks_df = df[df['nba_week'] > 0]

    return season_rks_df

def create_source_pt(df: pd.DataFrame):
    """Create a pivot table for Sources and Counts of Rankings."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame")
    
    return pd.pivot_table(
            df,
            values=['nba_week'], 
            index=['source'], 
            aggfunc=pd.Series.nunique).rename(
                columns={'nba_week':'rankings_count'}
            )

def create_rk_pt(df: pd.DataFrame):
    """Create a pivot table for Average Ranks and NBA_Weeks."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame")
    
    rk_pt = pd.pivot_table(df, index='teamname', 
                   columns='nba_week',
                   values='ranking')
    rk_pt = rk_pt.round(2)
    
    #rk_pt will be input for graphs
    return rk_pt

def create_filtered_df(df: pd.DataFrame, start_date='2024-10-20',end_date=dt.datetime.today()):
    """Filter the DataFrame to only include rows with specified NBA weeks."""
    
    start_adjust = most_recent_sunday(start_date) # find most recent sunday
    end_adjust = end_date

    df['date'] = pd.to_datetime(df['date'])
    df = df[df['nba_week'].notna()]
    df['nba_week'] = df['nba_week'].astype(int)
    
    filtered_df = df[(df.date >= start_adjust) & (df.date <= end_adjust)]
    
    return filtered_df

def df_string_for_graph():

    df = create_season_rks_df(create_and_merge_rank_week())
    rk_pt = create_rk_pt(df)
  
    return rk_pt

def df_string_for_graph_2(start='2024-10-20', end=dt.datetime.today()):
    ranking_file = find_file('latest_powerrankings')
    df = create_filtered_df(create_and_merge_rank_week(), start, end)
    rk_pt = create_rk_pt(df)
  
    return rk_pt

def get_max_min_week(start='2024-10-20', end=dt.datetime.today()):
    """Get NBA WEEK # for start and end date"""

    return nba_week_from_date(end), nba_week_from_date(start) 

def sunday_from_nba_week(week: int):
    """Lookup date for Sunday of week number."""
    try:
        wk = read_nba_week()
        return (wk.loc[wk['nba_week'] == week, 'sunday']).item()
    except:
        return None

def create_sundays_array():
    """Create arrays of Sundays and corresponding NBA week #s."""
    weeks_array = []
    sundays_array = []
    for i in range(-5, 30):
        weeks_array.append(i)
        #sundays_array.append(sunday_lookup(i)+1)
        sundays_array.append(sunday_from_nba_week(i))

    return weeks_array, sundays_array

def make_dropdown_options():
    teams = read_nba_teams_ref()
    dropdown_options = []
    conf_set = set()
    team_set = set()
    div_set = set()

    for index, row in teams.iterrows():
        team = row['teamname']
        conf = row['conference']
        div = row['division']
        team_set.add(team)
        conf_set.add(conf)
        div_set.add(div)

    #dropdown_options.append({"label": "--- Conferences ---", "value": "divider", "disabled": True})

    dropdown_options.append({"label": "--- Conferences ---", "value": "divider", "disabled": True})
    for element in conf_set:
        dropdown_options.append({"label": element, "value": element, "disabled": False})

    dropdown_options.append({"label": "--- Divisions ---", "value": "divider", "disabled": True})

    for element in sorted(div_set):
        dropdown_options.append({"label": element, "value": element, "disabled": False})

    dropdown_options.append({"label": "--- Teams ---", "value": "divider", "disabled": True})
    for element in sorted(team_set):
        dropdown_options.append({"label": element, "value": element, "disabled": False})

    return dropdown_options

# Define date range
start_date = dt.datetime(2024, 10, 20)
#end_date = dt.datetime.today()
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
    marks[start_week] = start.strftime('%b. %-d')
    marks[end_week] = end.strftime('%b. %-d')

    total_weeks = end_week - start_week

    if total_weeks >= 4:  # Only show intermediates if enough space
        mid1_week = start_week + total_weeks // 3
        mid2_week = start_week + 2 * (total_weeks // 3)

        # Ensure the intermediates aren't duplicates of start or end
        if mid1_week != start_week and mid1_week != end_week:
            mid1_date = start + timedelta(weeks=(mid1_week - start_week))
            marks[mid1_week] = mid1_date.strftime('%b. %-d')

        if mid2_week != start_week and mid2_week != end_week:
            mid2_date = start + timedelta(weeks=(mid2_week - start_week))
            marks[mid2_week] = mid2_date.strftime('%b. %-d')

    # Ensure marks are ordered by week number
    return dict(sorted(marks.items()))

##### APP #####
app = Dash(__name__)
server = app.server
app.title = "NBA Power Rankings Viz"

app.layout = html.Div([
    html.Div([
        html.H1('Visualizing NBA Power Rankings', id='page-title'),
        html.H3(f"Tracking NBA.com, ESPN, BR, and other top outlets to map the NBA's ever-shifting landscape.", id='page-subtitle'),
        html.Div(className="shape-sep"),
        html.H5('Created by Keegan Morris', className='byline'),
        ],id='header-div'
    ),
    html.Div([
        # Comment
        html.Div(
            [
                #html.H5('Select Conference/Division', className="button-label"),
                html.Div([
                    dcc.Checklist(
                        id="all-teams-checkbox",
                        options=[{'label': '  All Teams', 'value': 'all'}],
                        value=['all'],

                    ),
                    dcc.Dropdown(
                        make_dropdown_options(),
                        id='team-dropdown',
                        className="check-label",
                        value=['West','East'],
                        #clearable=False,
                        multi=True,
                        disabled=False,
                    ), 
                    dcc.Store(id='previous-all-teams-checkbox', data=[]),
                ],id='team-dropdown-select-div'
                )
            ]
        ,id="team-dropdown-group", 
        className="button-grp"
        ),
    ],id="team-dropdown-div"),
    html.Div([ 
        html.Div([
            dcc.Graph(
                    #figure=make_fig(df_string_for_graph_2()), 
                    id="pr-graph",
            ),
            dcc.Store(id='trace-visibility-store', data=[True] * 30),
        ],
                id='graph-subdiv',
            ),
        html.Div([
            html.Div([
                dcc.RangeSlider(
                    step=1,
                    id='date-range-slider-wk',
                    min=nba_week_from_date(start_date),
                    max=nba_week_from_date(end_date),
                    marks=get_datemarks_from_wk(start=start_date, end=end_date),
                    tooltip={"always_visible": True, "placement": "bottom",'transform':'getSundayByNBAWeek'},
                ),

            ],
            id="slider-div",
            ),
        ]),
    ], id='graph-div'),
    html.Div([    
        html.Div([
            html.Details([
                html.Summary("Filters"),
                html.Div(className="button-array-html",
                        children=[
                            
                            html.Div([
                                html.H5('Filter by Range', id="range-header", className="button-label"),
                                dcc.RadioItems(
                                    [
                                        {'label':'1-30', 'value': 'def-range'}, 
                                        {'label': 'Top 5', 'value': 'bot-5'},
                                        {'label': 'Bottom 5', 'value': 'top-5'}, 
                                    ], 
                                    'def-range', 
                                    id="rank-radio",
                                    labelStyle={'display':'inline-block'},
                                    className="radio-label"
                                ),
                                html.P('1-30 is default', id="note1", className="footnote")
                            ],id="rank-range", className="button-grp"),
                            html.Div(
                                [
                                    html.H5('Highlighting', className="button-label"),
                                    html.Div([
                                        dcc.Checklist(
                                            id='zone-check',
                                            className="check-label",
                                            options=[{'label': 'Top & Bottom 5', 'value': 'linear'}],
                                            value=['zone']
                                        ), 
                                    ],
                                    )
                                ]
                            ,id="zone-highlights", 
                            className="button-grp"
                            ),
                            html.Div(
                                [
                                    html.H5('Update XTicks Labels', className="button-label"),
                                    html.Div([
                                        dcc.Checklist(
                                            id='week-day-check',
                                            className="check-label",
                                            options=[{'label': 'Display Weeks', 'value': 'linear'}],
                                            value=['dates']
                                        ), 
                                    ],
                                    )
                                ]
                            ,id="xticks-labels", 
                            className="button-grp"
                            ),
                            html.Div(
                                [
                                    html.H5('Show Point Markers', className="button-label"),
                                    html.Div([
                                        dcc.Checklist(
                                            id='dot-check',
                                            className="check-label",
                                            options=[{'label': 'Show Marks', 'value': 'show'}],
                                            value=['show']
                                        ), 
                                    ],
                                    )
                                ]
                            ,id="show-dots", 
                            className="button-grp"
                            ),
                            ]
                    ,id="button_groups"
                    ),],
                    id='lower-section'),]),
    ]),
    html.Div(
        id="text-attribution",
        children=[
            html.A(f"keegan-morris.com", href="https://keegan-morris.com/2025/02/25/dash-deploy-power-rankings/", target="_blank", id='attrib-url'),
            html.P(f"updated {clean_date()}", id='attrib-date'),
    ]),
])


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
    options ={
        "bot-5": {
            "yrange": [5.5,0.5],
            'dtick':1,
            "tickvals": [1,2,3,4,5],
            'title_standoff': 22.8,
        },
        "top-5": {
            "yrange": [30.5,25.5],
            'dtick':1,
            "tickvals": [30,29,28,27,26],
            'title_standoff': 12,
            },
        "def-range": {
            "yrange": [30.5,0.5],
            'dtick': 5,
            'tickvals': [1, 5, 10, 15, 20, 25, 30],
            'title_standoff': 12,
        }
    } 
    settings = options.get(value, options[value])
    return settings['yrange'], settings['dtick'], settings['tickvals'], settings['title_standoff']

def zone_check_rect(value):
    """Enable top-5 and bottom-5 highlight zones from checkbox input."""
    if value == ['zone', 'linear']:
        r_dict = [
        {
                # bottom-5 rect
                "type": "rect",
                "x0": 0,
                "x1": 1, 
                "y0": 26, 
                "y1": 30, 
                "fillcolor": "slategrey", 
                "opacity": 0.25,
                "line": {"color": "royalblue", "width": 2,"dash": 'dot'},  # Border color and width
                "layer": "below"
            },
            {
                # top-5 rect
                "type": "rect", 
                "x0": 0, 
                "x1": 1, 
                "y0": 1, 
                "y1": 5, 
                "fillcolor": "slategrey", 
                "opacity": 0.25,
                "line": {"color": "royalblue", "width": 2, "dash": 'dot'},  # Border color and width
                "layer": "below"
            }
        ]
    else:
        r_dict = []

    return r_dict

def set_hovertemplate_format(value):
    if value == ['dates', 'linear']:
        hovertemplate_btmlines = '<br><b>week</b>: %{x}<br><b>rank</b>: %{y}'
    else: 
        hovertemplate_btmlines = '<br><b>date</b>: %{x}<br><b>rank</b>: %{y}'

    return hovertemplate_btmlines

def set_xticks(value):
    """Alternate between date and nba_week # XTick labels."""
    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime('%b. %-d') for date in sundays_array]

    if value == ['dates', 'linear']:
        # Convert sundays_array to strings in the format 'YYYY-MM-DD'
        xticks_set = dict(
        
            title=dict(
                text="<b>Week</b>",
                font_size=18,
            ),
            tickmode='array',
            tickvals=weeks_array,  
            ticktext=weeks_array, 
            dtick = 5,
            tickfont=dict(
                size=12  
            ),
            tickangle=0,
        )
    else:
        xticks_set = dict(


            tickmode='array',
            tickvals=weeks_array, 
            ticktext=sundays_str, 
            dtick = 14,
            tickfont=dict(
                size=12
            )
        )
    return xticks_set



def df_string_for_graph_subset(team_input):
    applicable_teams = set()
    df = df_string_for_graph_2()

    # Check if "All Teams" is selected (case-insensitive)
    if any(i.lower() == 'all teams' for i in team_input):
        return df  # Return the entire DataFrame

    for i in team_input:
        team = teams.find_team(i)
        if team:
            applicable_teams.add(team)
        # Handle conferences
        elif i in ['East', 'West']:
            applicable_teams.update(t for t in df.index if teams.nba_conf(t) == i)
        # Handle divisions
        elif i in ['Southwest', 'Southeast', 'Atlantic', 'Pacific', 'Northwest', 'Central']:
            applicable_teams.update(t for t in df.index if teams.nba_div(t) == i)

    # Filter the DataFrame to include only rows where the index (teamname) is in applicable_teams
    filtered_df = df[df.index.isin(applicable_teams)]
    return filtered_df

def date_range_slider_set(slider):
    #print(slider==None)
    if slider is None:
        start_date = .85
        end_date = nba_week_from_date(sunday_from_nba_week(df_string_for_graph_2().columns.max())) +.15
        #print(end_date)
    else:
        # Ensure slider is a tuple or list with two elements
        if isinstance(slider, (tuple, list)) and len(slider) == 2:
            start_date, end_date = slider
        else:
            # Fallback to default values if slider is invalid
            start_date = 1
            end_date = nba_week_from_date(sunday_from_nba_week(df_string_for_graph_2().columns.max())) + .15

    return start_date, end_date

@app.callback(
    Output('pr-graph', 'figure'),
    Output('trace-visibility-store', 'data'),
    Output('team-dropdown', 'disabled'),
    Input('date-range-slider-wk', 'value'),
    Input('rank-radio', 'value'),
    Input('zone-check', 'value'),
    Input('week-day-check', 'value'),
    Input('all-teams-checkbox', 'value'),
    Input('team-dropdown', 'value'),
    Input('dot-check','value'),
    Input('pr-graph','restyleData'),
    State('trace-visibility-store', 'data'),
    #State('pr-graph', 'figure')
)
def update_graph(
    date_range_slider, 
    rank_radio, 
    zone_check,
    week_day_check, 
    all_teams_checkbox,
    team_dropdown, 
    dot_check,
    restyle_data,
    visibility_state
):
    print(restyle_data)

    # Step 1: Create df
    df = df_string_for_graph_2()

    chart_settings = set_chart_yrange(rank_radio)
    chart_yrange = chart_settings[0]
    chart_dtick = chart_settings[1]
    chart_tickvals = chart_settings[2]
    #title_standoff = chart_settings[3]

    filtered_df = df_string_for_graph_subset(team_dropdown)
    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime('%b. %-d') for date in sundays_array]

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

    for team in filtered_df.index:
        base_hover = f"<b>{team.upper()}</b>"

        fig.add_trace(
            go.Scatter(
                x=filtered_df.columns,  # Weeks
                y=filtered_df.loc[team],  # Rankings
                mode='lines+markers',
                line=dict(width=2),
                marker=dict(size=6,),
                name=teams.nba_abbrname(team),
                opacity = 0.85,
                marker_color=teams.team_color1(team),
                hovertemplate=base_hover,
                visible=True,
                showlegend=True,
            )
        )

    # Step 3: Handle legend interactions (update visibility_state)
    if restyle_data:
        # restyle_data is a list of dictionaries
        for update in restyle_data:
            if 'visible' in update:
                # Update visibility_state based on restyleData
                new_visibility = update['visible']
                if isinstance(new_visibility, list):
                    # If multiple traces are updated, apply the changes
                    visibility_state = new_visibility
                elif isinstance(new_visibility, bool):
                    # If a single trace is updated, find the corresponding trace and update its visibility
                    trace_index = update.get('index', 0)  # Default to the first trace if index is not provided
                    if isinstance(trace_index, list):
                        # If multiple indices are provided, update all of them
                        for idx in trace_index:
                            visibility_state[idx] = new_visibility
                    else:
                        # If a single index is provided, update it
                        visibility_state[trace_index] = new_visibility

    # Step 4: Initialize visibility_state if it's None or invalid
    if visibility_state is None or len(visibility_state) != len(fig.data):
        visibility_state = [True] * len(fig.data)  # Default to all traces visible

    # Step 5: Apply team dropdown filtering
    for trace, vis_update in zip(fig.data, dropdown_update_layout(team_dropdown)):
        trace.visible = vis_update["visible"]

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
        paper_bgcolor='#f9f9f9',
        plot_bgcolor= 'white',
        template="presentation",
        font_family="IBM Plex Mono",
        margin=dict(
            t=25,
            l=15,
        ),
        xaxis=dict(
            domain=[0.05,0.97],
            range=[start_week, end_week],
            autorange=False,
            tickmode='array',
            tickvals=weeks_array,
            ticktext=sundays_str,
            title=dict(
                text="<b>Date</b>",
                font_size=18,
            ),
            
            
            tickfont=dict(
                size=12  
            ),
            tickangle=70,
            showline=True,
            linecolor='black',
        ),
        
        yaxis=dict(
            domain= [0,1],
            range=chart_yrange,
            dtick=chart_dtick,
            tickvals=chart_tickvals,
            #title_standoff=title_standoff
            title=dict(
                text="<b>Mean Ranking</b>",
                font_size=18,
            ),
            tickfont=dict(
                size=12  
            ),
        ),
        hoverlabel=dict(font=dict(
            family="IBM Plex Mono"
        )),
        legend=dict(
            x=1,
            y=1,
            xanchor="left",
            yanchor="top",
            #itemwidth=420,
            orientation='v',
            title = dict(
                text="<b>NBA Teams</b>",
       
                ),
                #xanchor='center'),
            #xanchor='left',
            font=dict(
                size=12,
                weight='normal',

            ),
            traceorder="normal",
            #bordercolor="Black",
            #borderwidth=2,
            entrywidth=70,
        )
    )

    if dot_check == ['show']:
        linemode = 'lines+markers'
        fig.update_traces(mode=linemode, marker=dict(size=6))
    else:
        linemode = 'lines'
        fig.update_traces(mode = linemode)

    for trace in fig.data:
        additional_hover = set_hovertemplate_format(week_day_check)
        trace.hovertemplate += additional_hover + '<extra></extra>'
    #fig.update_traces(hovertemplate = trace.hovertemplate + set_hovertemplate_format(week_day_check))
    
    fig.update_layout(
        yaxis=dict(
            range=chart_yrange,
            dtick=chart_dtick,
            tickvals=chart_tickvals,
            #title_standoff=title_standoff
        ),
        xaxis=dict(
            **set_xticks(week_day_check),  # Apply x-ticks settings
        )
    )

    # Step 6: Add or remove vrect based on zone_check
    rectangles = zone_check_rect(zone_check)
    if zone_check:
        for rect in rectangles:
            fig.add_hrect(**rect)

    
    
    return fig, [trace.visible for trace in fig.data], dropdown_disabled


if __name__ == '__main__':
    app.run_server(debug=True, dev_tools_hot_reload=False)


"""
#CSS
# X Make Inactive options grey
# X Top Bar
# [] Visual improvements for dropdown so long queries don't make it tall


# [] RESTORE "STORE" f'n so filtering during trace focus does not change selex

"""