


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
import glob
from dateutil.parser import parse

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

# Print results


#def get_csv(input):
#    if input == 'nba_weeks_ref':
#        path_end = "support/data/nba_weeks_ref.csv" #, parse_dates=['sunday'], dtype={'nba_week': int}"
#    if input == 'latest_powerrankings':
#        path_end = "support/data/latest_powerrankings.csv" # , parse_dates=['date'], date_format='%y%m%d')"
#    if input == 'nba_teams_data':
#        path_end = 'support/data/nba_teams_data.csv'

#    else:
#        path_end is None

#    try:
#        path = path_end
#        csvfile = pd.read_csv(path)
#    except:
#        path = 'Dash_Deploy/' + path_end
#        csvfile = pd.read_csv(path)

#    return csvfile
#def find_latest_file(folder, extension=''):
#    """Find latest file in specified folder."""
#    if extension:
#        file_location = folder+ '/*.' + extension
#    else:
#        file_location = folder + '/*' + extension
#    list_of_files = glob.glob(file_location)

#    if list_of_files:
#        latest_file = max(list_of_files, key=os.path.getctime)
#        #print(latest_file)
#        return latest_file

#    else:
#        return f"Found no files with extension '{extension}' in '{folder}'"

#ranking_filepath = 'Dash_Deploy/support/data/latest_powerrankings.csv'
#ranking_filepath = 'Dash_Deploy/support/data/latest_powerrankings.csv'
#ranking_filepath = get_path('latest_powerrankings')
#ranking_filepath = get_csv('latest_powerrankings')
WEEK_REFERENCE_PATH = find_file('nba_weeks_ref')

def read_nba_week():    
    """Read NBA Week from reference file."""
    return pd.read_csv(WEEK_REFERENCE_PATH, parse_dates=['sunday'], dtype={'nba_week': int})
    #csv_df =  get_csv('nba_weeks_ref')
    #csv_df['sunday'] = pd.to_datetime(csv_df['sunday'])
    #csv_df['nba_week'] = pd.to_numeric(csv_df['nba_week'])

    #return csv_df

def read_ranking_file():
    """Read NBA Ranking file"""
    #rk = get_csv('latest_powerrankings')
    #rk['date'] = pd.to_datetime(rk['date'])
    rk = pd.read_csv(find_file('latest_powerrankings'), parse_dates=['date'], date_format="%y%m%d") # 02-Dec-24
    return rk

today = dt.datetime.today()

def get_nba_week_no(date=today):
    """Get NBA Week number"""
    wk = read_nba_week()
    nba_week_no = wk[wk['sunday'] <= date].nba_week.max()

    return int(nba_week_no)

def most_recent_sunday(date):
    """Find date of most recent Sunday."""
    date = pd.to_datetime(date)
    #return date
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

#print(read_nba_teams_ref())

def clean_date(raw_date=None):
    """ Get an external-friendly date in format 'Jan 24, 2025'. """
    if raw_date is not None:
        input_date = parse(raw_date)
    else:
        input_date = dt.datetime.today()

    parsed_date = input_date.strftime("%b %d, %Y")
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

#print(temp_df.types)


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

print(df_string_for_graph().dtypes)

def get_max_min_week(start='2024-10-20', end=dt.datetime.today()):
    """Get NBA WEEK # for start and end date"""

    return get_nba_week_no(end), get_nba_week_no(start) 

def sunday_lookup(week: int):
    """Lookup date for Sunday of week number."""
    try:
        wk = read_nba_week()
        return (wk.loc[wk['nba_week'] == week, 'sunday']).item()
    except:
        return None
    
### NEED FUNCTION TO SWITCH BETWEEN TICKS AND NOT TICKS
    
def change_slider_marks(step):
    """Custom slider marks"""
    marks = {}

    start_date = dt.datetime(2024, 10, 20)
    end_date = dt.datetime(2025, 2, 24)

    # convert to timestamp
    end_timestamp = int(end_date.timestamp())
    start_timestamp = int(start_date.timestamp())

    points = start_timestamp

    while points <= end_timestamp:
        date_str = dt.datetime.fromtimestamp(points).strftime('%b %d')
        marks[int(points)] = date_str
        points += step * 24 * 3600
    return marks

print(type(change_slider_marks(7)))




print()
#print(df_string_for_graph_2().columns.max())
    

def create_sundays_array():
    """Create arrays of Sundays and corresponding NBA week #s."""
    weeks_array = []
    sundays_array = []
    for i in range(-5, 30):
        weeks_array.append(i)
        sundays_array.append(sunday_lookup(i))

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
            x=list(range(1, len(df_piv_rk.columns)+ 1)),
            y=df_piv_rk.loc[team],
            mode='lines',
            
            line=dict(width=2),
            name=team,
            opacity = 0.85,
            marker_color=teams.team_color1(team),
            hovertemplate=base_hover,
            #hovertemplate=f"<b>{team.upper()}</b>" + '<br><b>date</b>: %{x}<br><b>rank</b>: %{y}<extra></extra>',
            visible=True,
            showlegend=True,
            #legendgroup=team,
        )
        fig.add_trace(trace)
        team_traces.append({"team":team, "conference":conference, "division": division})

    weeks_array, sundays_array = create_sundays_array()

    #print(weeks_array, sundays_array)
    sundays_str = [date.strftime('%Y-%m-%d') for date in sundays_array]
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
            domain=[0.1,0.85],
            tickmode='array',
            tickvals=weeks_array,
            #ticktext=sundays_str,
            #nticks = 5,
            title=dict(
                text="<b>Date</b>",
                font_size=18,
            ),
            
            tickfont=dict(
                size=12  # Adjust tick label size (x-axis)
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
                size=12  # Adjust tick label size (x-axis)
            ),
          
            tickmode = 'array',
            tickvals = def_tickvals,
            range=[30.5,0.5], # manual range — 1 as top, adds top- / bottom-padding for readability
            
            domain=[0.1,1],
            showline=True,
            linecolor='black',
            #linewidth=2,
        ),
        hoverlabel=dict(font=dict(
            family="IBM Plex Mono"
        )),
        legend=dict(
            x=1.08,
            y=1,
            xanchor="right",
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
end_date = dt.datetime.today()

# Convert to integer timestamps
start_timestamp = int(start_date.timestamp())
end_timestamp = int(end_date.timestamp())

def get_marks(start=start_timestamp, end=end_timestamp, step=7):
    """Generate timestamp marks of step."""
    marks = {}
    current = start
    while current <= end:
        date_str = dt.datetime.fromtimestamp(current).strftime('%m-%d')
        marks[int(current)] = date_str  
        current += step * 24 * 3600 
    return marks

def get_marks_wk(start=start_date, end=end_date, step=7):
    """Generate date marks of step."""
    marks = {}
    current = start 
    while current <= end: 
        week_no = get_nba_week_no(current) 
        marks[week_no] = current.strftime('%m-%d')  
        current += timedelta(days=step)  
    return marks


##### APP #####
app = Dash(__name__)
server = app.server
app.title = "NBA Power Rankings Viz"

app.layout = html.Div([
    html.Div([
        html.H1('Visualizing NBA Power Rankings', id='page-title'),
        html.H3(f"Tracking top sports media outlets to map the NBA's ever-shifting landscape.", id='page-subtitle'),
        html.Div(className="shape-sep"),
        html.H5('Created by Keegan Morris', className='byline'),
        ],id='header-div'
    ),
    html.Div([
        html.Div([
            dcc.Graph(
                    figure=make_fig(df_string_for_graph_2()), 
                    id="pr-graph",
            ),
        ],
                id='graph-subdiv',
            ),
        html.Div([
            #html.Div(
            #    html.H5('Select Range'),
            #    id="slider-header-div",
            #),
            html.Div([
                
                dcc.RangeSlider(
                    min=get_nba_week_no(start_date), 
                    max=get_nba_week_no(end_date),
                    step= 1, 
                    value=[get_nba_week_no(start_date), get_nba_week_no(end_date)], 
                    #marks=marks,
                    marks =  get_marks_wk(start_date,end_date, step=14),
                    id='date-range-slider-wk',
                ),
            ],
            id="slider-div",
            ),
        ]),
            #html.Div(id="output-container")
    ], id='graph-div'),
    html.Div([    
        html.Div([
            #html.Details("filters"),
            html.Details([
                html.Summary("Filters"),
            #html.H3(
            #    'Filters',
            #    className='section-head', id='section-head-filters',
            #),
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
                                    html.H5('Mark Points', className="button-label"),
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
                                    html.H5('Select Conference/Division', className="button-label"),
                                    html.Div([
                                        dcc.Dropdown(
                                            make_drilldown_options(),
                                            id='team-dropdown',
                                            className="check-label",
                                            value="All Teams",
                                            clearable=False
                                            #options=[{'label': 'Top & Bottom 5', 'value': 'linear'}],
                                            #value=['zone']
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
            dcc.Markdown('''Created by [Keegan Morris](https://keegan-morris.com/)''',link_target="_blank", id='attrib-markdown'),
            html.P(f"Updated {clean_date()}", id='attrib-date')         
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
            visibility.append(value in [team, conf, div])  # Show only matching traces

    return [{"visible": v} for v in visibility]  # Return a list of individual updates

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
                "type": "rect",  # Define the shape as a rectangle
                "x0": 0,  # Set x-axis start position (you can adjust)
                "x1": 1,  # Set x-axis end position (you can adjust)
                "y0": 26, 
                "y1": 30, 
                "fillcolor": "slategrey", 
                "opacity": 0.25,
                "line": {"color": "royalblue", "width": 2,"dash": 'dot'},  # Border color and width
                "layer": "below"
            },
            {
                # top-5 rect
                "type": "rect",  # Define the shape as a rectangle
                "x0": 0,  # Set x-axis start position (you can adjust)
                "x1": 1,  # Set x-axis end position (you can adjust)
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
        #['dates', 'linear'] is the output if the weeks is selected
        hovertemplate_btmlines = '<br><b>week</b>: %{x}<br><b>rank</b>: %{y}'
    else: 
        hovertemplate_btmlines = '<br><b>date</b>: %{x}<br><b>rank</b>: %{y}'

    return hovertemplate_btmlines

def set_xticks(value):
    """Alternate between date and nba_week # XTick labels."""
    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime('%Y-%m-%d') for date in sundays_array]

    if value == ['dates', 'linear']:
        # Convert sundays_array to strings in the format 'YYYY-MM-DD'
        xticks_set = dict(
        
            title=dict(
                text="<b>Week</b>",
                font_size=18,
            ),
            #title_standoff=73,
            tickmode='array',
            tickvals=weeks_array,  # Use Unix timestamp for tickvals
            ticktext=weeks_array,  # Display string representation of the date
            dtick = 5,
            tickfont=dict(
                size=12  # Adjust tick label size (x-axis)
            ),
            tickangle=0,
        )
    else:
        xticks_set = dict(

            ## REmove year
            #title="<b>Days</b>",
            tickmode='array',
            #font_size=16,
            tickvals=weeks_array,  # Use Unix timestamp for tickvals
            ticktext=sundays_str, 
            dtick = 14, # Display string representation of the date
            tickfont=dict(
                size=12  # Adjust tick label size (x-axis)
            )
        )
    return xticks_set

@app.callback(
    Output('pr-graph','figure'),
    #Output('output-container', 'children'),
    Input('date-range-slider-wk', 'value'),
    Input('rank-radio', 'value'),
    Input('zone-check', 'value'),
    Input('week-day-check', 'value'),
    Input('team-dropdown', 'value'),
    Input('dot-check','value'),

)

def update_graph(date_range_slider, rank_radio, zone_check,week_day_check, team_dropdown, dot_check):

    df = df_string_for_graph_2()

    fig = make_fig(df)

 
    chart_settings = set_chart_yrange(rank_radio)
    chart_yrange = chart_settings[0]
    chart_dtick = chart_settings[1]
    chart_tickvals=chart_settings[2]
    title_standoff=chart_settings[3]

    start_date = date_range_slider[0]
    end_date = date_range_slider[1]
    fig.update_layout(
        yaxis=dict(
            range=chart_yrange,
            dtick=chart_dtick,
            #ytick_size=12px,
            tickvals=chart_tickvals,
            title_standoff=title_standoff
        ),
        xaxis= dict(
            set_xticks(week_day_check),
            range=[start_date, end_date]
            
        )
    )
    #print(dot_check)
    if dot_check == ['show']:
        linemode='lines+markers'
        fig.update_traces(mode = linemode, marker=dict(size=6,))
    else:
        linemode = 'lines'
        fig.update_traces(mode = linemode)
    
    for trace in fig.data:
        additional_hover = set_hovertemplate_format(week_day_check)
        trace.hovertemplate += additional_hover + '<extra></extra>'
    #fig.update_traces(hovertemplate = trace.hovertemplate + set_hovertemplate_format(week_day_check))
    
    for trace, vis_update in zip(fig.data, drilldown_update_layout(team_dropdown)):
        trace.visible = vis_update["visible"]

    rectangles = zone_check_rect(zone_check)

    if zone_check:
        
        for rect in rectangles:
            fig.add_hrect(**rect)

    string_prefix="You have selected: "
    #if date_value is not None:
    #    date_object = date.fromisoformat()
    
    #text = 'You have selected "{}"'.format(date_range_slider0, text-[1])
    text= f"{start_date} to {end_date}"
    
    #return fig, start_end_str
    return fig


# JSON check

import json
from dash.development.base_component import Component

#print(f":::: {app.layout}")
if __name__ == '__main__':
    app.run_server(port=8021, debug=False, dev_tools_hot_reload=False)