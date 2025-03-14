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

#def most_recent_sunday(date):
#    """Find date of most recent Sunday."""
#    date = pd.to_datetime(date)
#    return date - pd.to_timedelta(date.weekday() + 1, unit='D')

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

#print(df_string_for_graph_2())

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
        
#def change_slider_marks(step):
#    """Custom slider marks"""
#    marks = {}

#    start_date = dt.datetime(2024, 10, 20)
#    end_date = dt.datetime(2025, 2, 24)

#    # convert to timestamp
#    end_timestamp = int(end_date.timestamp())
#    start_timestamp = int(start_date.timestamp())

#    points = start_timestamp

#    while points <= end_timestamp:
#        date_str = dt.datetime.fromtimestamp(points)
#        marks[int(points)] = date_str
#        points += step * 24 * 3600,
#    return marks

def create_sundays_array():
    """Create arrays of Sundays and corresponding NBA week #s."""
    weeks_array = []
    sundays_array = []
    for i in range(-5, 30):
        weeks_array.append(i)
        #sundays_array.append(sunday_lookup(i)+1)
        sundays_array.append(sunday_from_nba_week(i))

    return weeks_array, sundays_array


def make_drilldown_options():
    teams = read_nba_teams_ref()
    drilldown_options = [
        "All Teams"
        ]

    conf_buttons = []
    div_buttons=[]

    conf_set = set()
    div_set = set()

    for index, row in teams.iterrows():
        conf = row['conference']
        div = row['division']
        conf_set.add(conf)
        div_set.add(div)

    for element in conf_set:
        drilldown_options.append(element)
        conf_buttons.append(element)

    for element in div_set:
        drilldown_options.append(element)
        div_buttons.append(element)

    return drilldown_options


#print(teams.team_color1('Cleveland'))

def make_fig(df_piv_rk):
    fig = go.Figure()

    # specifying tick values so 1, not 0, is shown
    def_tickvals = [1, 5, 10, 15, 20, 25, 30]

    team_traces=[]

    for team in df_piv_rk.index:
        ## add conference attributes
        conference = teams.nba_conf(team)
        division = teams.nba_div(team)

        base_hover = f"<b>{team.upper()}</b>"
        
        #print(f"Adding trace for: {team}")
        trace = go.Scatter(
            #x=list(range(0, len(df_piv_rk.columns)+ 1)),
            #x=list(range(1, len(df_piv_rk.columns)+ 1)),
            x=list(range(1, len(df_piv_rk.columns) +1 )),
            y=df_piv_rk.loc[team],
            mode='lines+markers',
            marker=dict(size=6,),

            line=dict(width=2),
            name=teams.nba_abbrname(team),
            opacity = 0.85,
            marker_color=teams.team_color1(team),
            hovertemplate=base_hover,
    
            visible=True,
            showlegend=True,

        )
        fig.add_trace(trace)
        team_traces.append({"team":team, "conference":conference, "division": division})

    weeks_array, sundays_array = create_sundays_array()

    sundays_str = [date.strftime('%b. %d') for date in sundays_array]
    fig.update_layout(
        autosize=True,
        height=620,
        #showlegend=False,
        paper_bgcolor='#f9f9f9',
        plot_bgcolor= 'white',
        template="presentation",
        font_family="IBM Plex Mono",
        margin=dict(
            t=55,
            l=5,
        ),
        xaxis=dict(
            domain=[0.05,0.96],
            range=[start_date, end_date],
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
            #linewidth=2,
        ),
        yaxis=dict(
            title=dict(
                text="<b>Mean Ranking</b>",
                font_size=18,
            ),
            tickfont=dict(
                size=12  
            ),
          
            tickmode = 'array',
            tickvals = def_tickvals,
            range=[30.5,0.5], 
            
            domain=[0.1,1],
            showline=True,
            linecolor='black',
            #linewidth=2,
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

   
        ),
    )
    return fig

# Define date range
start_date = dt.datetime(2024, 10, 20)
#end_date = dt.datetime.today()
end_date = sunday_from_nba_week(df_string_for_graph_2().columns.max())

# Convert to integer timestamps
start_timestamp = int(start_date.timestamp())
end_timestamp = int(end_date.timestamp())

#def get_rangeslider_marks(start=start_timestamp, end=end_timestamp, step=7):
#    """Generate timestamp marks of step."""
#    marks = {}
#    current = start
#    while current <= end:
#        date_str = dt.datetime.fromtimestamp(current).strftime('%b. %-d')
#        marks[int(current)] = date_str  
#        current += step * 24 * 3600 
#    return marks
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
        html.Div([
            dcc.Graph( 
                    #figure=make_fig(df_string_for_graph_2()), 
                    id="pr-graph",
            ),
            dcc.Store(id='trace-visibility-store'),
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
                            html.Div(
                                [
                                    html.H5('Select Conference/Division', className="button-label"),
                                    html.Div([
                                        dcc.Dropdown(
                                            make_drilldown_options(),
                                            id='team-dropdown',
                                            className="check-label",
                                            value="All Teams",
                                            clearable=False
                                        ), 
                                    ],id='team-dropdown-div'
                                    )
                                ]
                            ,id="team-dropdown-group", 
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


def drilldown_update_layout(value):
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

@app.callback(
    Output('pr-graph', 'figure'),
    Output('trace-visibility-store', 'data'),
    Input('date-range-slider-wk', 'value'),
    Input('rank-radio', 'value'),
    Input('zone-check', 'value'),
    Input('week-day-check', 'value'),
    Input('team-dropdown', 'value'),
    Input('dot-check', 'value'),
    Input('trace-visibility-store', 'data'),
    Input('pr-graph', 'restyleData'),
    #State('pr-graph', 'restyleData'),
    #State('pr-graph', 'relayoutData')
    State('pr-graph', 'figure')
)


def update_graph(
    date_range_slider, rank_radio, zone_check, week_day_check, team_dropdown, dot_check, visibility_state, restyle_data, current_figure
    ): #, relayout_data):

    # Step 1: Create df
    df = df_string_for_graph_2()
    fig = make_fig(df)
    #print(df)

    if visibility_state is None:
        visibility_state = [True] * len(df.index)

    # Step 2: Set visibility states and trace indices from restyle_data
    if restyle_data:

        if len(restyle_data) >= 2 and isinstance(restyle_data[0], dict) and 'visible' in restyle_data[0]:
            
            visibility_states = restyle_data[0]['visible']
            trace_indices = restyle_data[1]
            
            for i, trace_idx in enumerate(trace_indices):
                if trace_idx < len(visibility_state):
                    visibility_state[trace_idx] = visibility_states[i]

    # Step 3: Apply chart settings (e.g., y-range, x-ticks, etc.)
    chart_settings = set_chart_yrange(rank_radio)
    chart_yrange = chart_settings[0]
    chart_dtick = chart_settings[1]
    chart_tickvals = chart_settings[2]
    title_standoff = chart_settings[3]

    if date_range_slider is None:
        date_range_slider = [nba_week_from_date(dt.datetime(2024, 10, 20)), nba_week_from_date(sunday_from_nba_week(df_string_for_graph_2().columns.max()))]

    start_date = date_range_slider[0]
    end_date = date_range_slider[1]
    fig.update_layout(
        yaxis=dict(
            range=chart_yrange,
            dtick=chart_dtick,
            tickvals=chart_tickvals,
            title_standoff=title_standoff
        ),
        xaxis=dict(
            **set_xticks(week_day_check),  # Apply x-ticks settings
            range=[start_date, end_date]
        )
    )

    # Step 4: Toggle point markers based on dot-check
    if dot_check == ['show']:
        linemode = 'lines+markers'
        fig.update_traces(mode=linemode, marker=dict(size=6))
    else:
        linemode = 'lines'
        fig.update_traces(mode=linemode)

    # Step 5: Update hover template
    for trace in fig.data:
        additional_hover = set_hovertemplate_format(week_day_check)
        trace.hovertemplate += additional_hover + '<extra></extra>'


    # Step 6: Add or remove vrect based on zone_check
    rectangles = zone_check_rect(zone_check)
    if zone_check:
        for rect in rectangles:
            fig.add_hrect(**rect)

    # Step 7: Apply team dropdown filtering
    for trace, vis_update in zip(fig.data, drilldown_update_layout(team_dropdown)):
        trace.visible = vis_update["visible"]

    for i, trace in enumerate(fig.data):
        if i < len(visibility_state):
            trace.visible = visibility_state[i]

    # Return
    return fig, visibility_state


if __name__ == '__main__':
    app.run_server(debug=True, dev_tools_hot_reload=False)