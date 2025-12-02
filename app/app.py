import numpy as np
import pandas as pd
import os
import dotenv
import psycopg
from sqlalchemy import create_engine

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

import plotly.express as px
import plotly.figure_factory as ff

dotenv.load_dotenv()
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

dbms = 'postgresql'
package = 'psycopg'
user = 'postgres'
password = POSTGRES_PASSWORD
host = 'postgres'
port = '5432'
db = 'contrans'

engine = create_engine(f'{dbms}+{package}://{user}:{password}@{host}:{port}/{db}')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Create features that we need, but won't change depending on what the user does
myquery = '''
SELECT *
FROM members
'''
data = pd.read_sql_query(myquery, con=engine)
data2 = data[['full_name', 'state_abbrev', 'district_code', 'party']]
data2['party'] = data2['party'].str[0]
display_name = [n + ' (' + p + ', ' + s + '-' + str(d) + ')'
                for n, s, d, p in 
                zip(data2['full_name'], 
                    data2['state_abbrev'],
                    data2['district_code'],
                    data2['party'])]
display_name = [x.replace('-0', '') for x in display_name]

dropdown_options = [{'label': y, 'value': x} for x, y in zip(data['bioguide_id'], display_name)]

# Define the Dash app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Populate the dashboard layout
app.layout = html.Div(
    [
        html.H1('Know Your Representatives in Congress!'),

        html.Div([
            dcc.Markdown('''If you know your Representative or Senators, 
                         select them in the dropbox box below. If you want 
                         to lookup who your representatives are, check out 
                         [this website](https://www.congress.gov/members/find-your-member).'''),
            dcc.Dropdown(id = 'dropdown', options=dropdown_options, 
                         value='N000188') # Step 1: User input
        ],
                 style={'width':'25%', 'float':'left'}),

        html.Div([
            dcc.Tabs([
                dcc.Tab(label = 'Biographical Information',
                        children = [
                            html.Div([html.Img(id = 'bioimage')], style={'width':'20%', 'float':'left'}),
                            html.Div([dcc.Graph(id = 'biotable')], style={'width':'80%', 'float':'right'})
                        ]),
                dcc.Tab(label = 'How They Vote',
                        children = [
                            dcc.Graph(id='vote_scatter')
                        ]),
                dcc.Tab(label = 'Sponsored Bills',
                        children = []),
                dcc.Tab(label = 'Who is Giving Them Money?',
                        children = [])
            ])
        ],
                 style={'width':'75%', 'float':'right'})


    ]
)


# Define the 'callbacks' -- user input -> output functions

@app.callback([Output(component_id = 'biotable', component_property='figure')], # Output() is step 4 
              [Input(component_id = 'dropdown', component_property = 'value')]) # Input() is step 2

def biotable(b): # Step 3: write a function that turns input into output
    myquery = f'''
        SELECT *
        FROM members
        WHERE bioguide_id = '{b}'
    '''
    member_info = pd.read_sql_query(myquery, con=engine)
    member_info = member_info.drop(['bioguide_id', 'image', 'fec_id', 'bioname', 'icpsr'],
        axis=1)
    return [ff.create_table(member_info.T.reset_index().rename({'index':'',0:''}, axis=1))]

@app.callback([Output(component_id = 'bioimage', component_property='src')], 
              [Input(component_id = 'dropdown', component_property = 'value')])

def bioimage(b):
    
    myquery = f'''
        SELECT image
        FROM members
        WHERE bioguide_id = '{b}'
    '''
    image_url = pd.read_sql_query(myquery, con=engine)['image'][0]
    return [image_url]

@app.callback([Output(component_id = 'vote_scatter', component_property='figure')], 
              [Input(component_id = 'dropdown', component_property = 'value')])

def vote_scatterplot(b):
    myquery = f'''
        SELECT c.comparison_member,
            c.agree,
            m.left_right_ideology,
            m.party
        FROM members m
        INNER JOIN (
            SELECT vc.comparison_member,
                vc.agree
            FROM members m
            INNER JOIN vote_compare vc
                ON m.bioname = vc.bioname
            WHERE m.bioguide_id = '{b}'
        ) c
            ON m.bioname = c.comparison_member

        '''
    vote_data = pd.read_sql_query(myquery, con=engine)
    fig = px.scatter(vote_data,
                 x = 'left_right_ideology',
                 y = 'agree',
                 hover_name = 'comparison_member',
                 color = 'party',
                 color_discrete_map={'Democrat': 'blue','Republican': 'red'})
    return [fig]

# Run the dashboard
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)