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
host = 'localhost'
port = '5432'
db = 'contrans'

engine = create_engine(f'{dbms}+{package}://{user}:{password}@{host}:{port}/{db}')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Define the Dash app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Populate the dashboard layout
app.layout = html.Div(
    [
        html.H1('Know Your Representatives in Congress!'),

        html.Div([
            dcc.Markdown('Dropdown goes here')
        ],
                 style={'width':'25%', 'float':'left'}),

        html.Div([
            dcc.Tabs([
                dcc.Tab(label = 'Biographical Information',
                        children = []),
                dcc.Tab(label = 'How They Vote',
                        children = []),
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

# Run the dashboard
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)



