import os
import sys
import subprocess

# Dash imports
from dash import Dash, dcc, html, callback, Output, Input, State
from datetime import datetime as dt
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Other imports
import support.nba_teams as teams
import glob
from dateutil.parser import parse

WEEK_REFERENCE_PATH = 'Dash_Deploy/support/data/nba_weeks_ref.csv'
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

ranking_filepath = 'Dash_Deploy/support/data/latest_powerrankings.csv'

def read_nba_week():    
    """Read NBA Week from reference file."""
    return pd.read_csv(WEEK_REFERENCE_PATH, parse_dates=['sunday'], dtype={'nba_week': int})

def read_ranking_file(ranking_file):
    """Read NBA Ranking file"""
    rk = pd.read_csv(ranking_file, parse_dates=['date'], date_format="%y%m%d") # 02-Dec-24
    return rk
today = dt.today()

def get_nba_week_no(date=today):
    """Get NBA Week number"""
    wk = read_nba_week()
    nba_week_no = wk[wk['sunday'] <= date].nba_week.max()

    return nba_week_no

def most_recent_sunday(date):
    """Find date of most recent Sunday."""
    date = pd.to_datetime(date)
    #return date
    return date - pd.to_timedelta(date.weekday() + 1, unit='D')

def create_and_merge_rank_week(ranking_file):

    rk = read_ranking_file(ranking_file)
    wk = read_nba_week()

    rk['sunday'] = rk['date'].apply(most_recent_sunday)
    rk['sunday'] = pd.to_datetime(rk['sunday'])
    wk['sunday'] = pd.to_datetime(wk['sunday'])

    df = pd.merge(rk, wk[['sunday', 'nba_week']], on='sunday', how='left')
    return df

#teams_filename = '/Users/keegan/Projects/nba_reference/NBA_Teams.csv'

def read_nba_teams_ref():
    nba_teams_ref = pd.read_csv('Dash_Deploy/support/data/nba_teams_data.csv')
    return nba_teams_ref

#print(read_nba_teams_ref())

def clean_date(raw_date=None):
    """ Get an external-friendly date in format 'Jan 24, 2025'. """
    if raw_date is not None:
        input_date = parse(raw_date)
    else:
        input_date = dt.today()

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

    #print(rk_pt)
    return rk_pt

    #rk_pt will be input for graphs

def df_string_for_graph():
    ranking_file = ranking_filepath
    df = create_season_rks_df(create_and_merge_rank_week(ranking_file))
    rk_pt = create_rk_pt(df)
  
    return rk_pt
    
def sunday_lookup(week: int):
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
        
        #print(f"Adding trace for: {team}")
        trace = go.Scatter(
            x=list(range(1, len(df_piv_rk.columns)+ 1)),
            y=df_piv_rk.loc[team],
            mode='lines',
            line=dict(width=2),
            name=team,
            opacity = 0.85,
            marker_color=teams.team_color1(team),
            hovertemplate=f"<b>{team.upper()}</b>" + '<br><b>date</b>: %{x}<br><b>rank</b>: %{y}<extra></extra>',
            visible=True,
            showlegend=True,
            #legendgroup=team,
        )
        fig.add_trace(trace)
        team_traces.append({"team":team, "conference":conference, "division": division})

    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime('%Y-%m-%d') for date in sundays_array]
    fig.update_layout(
        autosize=True,
        height=420,
        paper_bgcolor='#f9f9f9',
        plot_bgcolor= 'white',
        template="presentation",
        font_family="IBM Plex Mono",
        margin=dict(
            t=55,
            l=5,
        ),
        xaxis=dict(
            domain=[0.1,0.95],
            tickmode='array',
            tickvals=weeks_array,
            ticktext=sundays_str,
            dtick = 5,
            title=dict(
                text="<b>Date</b>"
            ),
            
            tickfont=dict(
                size=13  # Adjust tick label size (x-axis)
            ),
            tickangle=65,
            showline=True,
            linecolor='black',
            #linewidth=2,
        ),
        yaxis=dict(
            title=dict(
                text="<b>Mean Ranking</b>"
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
            x=0.99,
            y=1,
            #itemwidth=420,
            title = dict(
                text="<b>NBA Teams</b>",
                ),
                #xanchor='center'),
            xanchor='left',
            yanchor="top",
            font=dict(
                size=12,
                weight='normal',

            )
        ),
    )
    return fig


app = Dash(__name__)
server = app.server
app.title = "NBA Power Rankings Viz"

app.layout = html.Div([
    html.Div([
        html.H1('Visualizing NBA Power Rankings', id='page-title'),
        html.H3(f"Pulling data from top sports media outlets to trace the ever-changing fortunes of NBA teams.", id='subtitle'),],id='page-header'
    ),
    html.Div(
        html.Div(
            dcc.Graph(id="pr-graph", figure=make_fig(df_string_for_graph())),
            id='graph-subdiv'
            ),
        id='graph-div',
    ),
    html.Div([    
        html.Div(
            html.H3(
                'Filters',
                className='section-head', id='section-head-filters',
            ),
        ),
        html.Div(className="button-array",
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
            ),],id='lower-section'),
    html.Div(id="text-attribution",
             children=[
                 dcc.Markdown('''Created by [Keegan Morris](https://keegan-morris.com/)''',link_target="_blank", id='attrib-markdown'),
                 html.P(f"Updated {clean_date()}", id='attrib-date')
             ]),
], id='super-div')

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

def set_xticks(value):
    """Alternate between date and nba_week # XTick labels."""
    weeks_array, sundays_array = create_sundays_array()
    sundays_str = [date.strftime('%Y-%m-%d') for date in sundays_array]

    if value == ['dates', 'linear']:
        # Convert sundays_array to strings in the format 'YYYY-MM-DD'
        xticks_set = dict(
        
            title="<b>Weeks</b>",
            title_standoff=73,
            tickmode='array',
            tickvals=weeks_array,  # Use Unix timestamp for tickvals
            ticktext=weeks_array,  # Display string representation of the date
            dtick = 5,
            tickfont=dict(
                size=18  # Adjust tick label size (x-axis)
            ),
            tickangle=0,
            
        )
    else:
        xticks_set = dict(
            #title="<b>Days</b>",
            tickmode='array',
            tickvals=weeks_array,  # Use Unix timestamp for tickvals
            ticktext=sundays_str,  # Display string representation of the date
            tickfont=dict(
                size=12  # Adjust tick label size (x-axis)
            )
        )
    return xticks_set

@app.callback(
    Output('pr-graph','figure'),
    Input('rank-radio', 'value'),
    Input('zone-check', 'value'),
    Input('week-day-check', 'value'),
    Input('team-dropdown', 'value')


)

def update_graph(rank_radio, zone_check,week_day_check, team_dropdown):
    fig = make_fig(df_string_for_graph())

    chart_settings = set_chart_yrange(rank_radio)
    chart_yrange = chart_settings[0]
    chart_dtick = chart_settings[1]
    chart_tickvals=chart_settings[2]
    title_standoff=chart_settings[3]

    fig.update_layout(
        yaxis=dict(
            range=chart_yrange,
            dtick=chart_dtick,
            tickvals=chart_tickvals,
            title_standoff=title_standoff
        ),
        xaxis= set_xticks(week_day_check)
    )
    
    for trace, vis_update in zip(fig.data, drilldown_update_layout(team_dropdown)):
        trace.visible = vis_update["visible"]

    rectangles = zone_check_rect(zone_check)

    if zone_check:
        
        for rect in rectangles:
            fig.add_hrect(**rect)

    return fig

if __name__ == '__main__':
    app.run_server(debug=True, dev_tools_hot_reload=False)