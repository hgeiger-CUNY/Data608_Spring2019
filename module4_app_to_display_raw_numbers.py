#Import modules.

import dash
import dash_core_components as dcc
import dash_html_components as html

import pandas as pd
import numpy as np

#Query to count trees per each unique combination of borough, health, stewardship, and species.
#Then, there will be 4,565 results, but limited to 1,000 results at a time. So read in pages 1-5 to get everything.

soql_url = ('https://data.cityofnewyork.us/resource/nwxe-4ae8.json?' +\
        '$select=spc_common,boroname,health,steward,count(tree_id)' +\
        '&$group=spc_common,boroname,health,steward').replace(' ', '%20')

pg1 = pd.read_json(soql_url)
pg2 = pd.read_json(soql_url + '&$offset=1000')
pg3 = pd.read_json(soql_url + '&$offset=2000')
pg4 = pd.read_json(soql_url + '&$offset=3000')
pg5 = pd.read_json(soql_url + '&$offset=4000')

counts = pd.concat([pg1,pg2,pg3,pg4,pg5])

counts = counts.dropna() #Remove rows missing information.

#From Dash documentation.

def generate_table(dataframe,max_rows=counts.shape[0] + 1):
	return html.Table(
		#Header
		[html.Tr([html.Th(col) for col in dataframe.columns])] +
		
		# Body
		[html.Tr([
			html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
		]) for i in range(min(len(dataframe), max_rows))]
	)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
	html.H1(children='Tree Health in NYC - a Dash App'),
	html.H2(children='Select species and borough.'),
	dcc.Dropdown(id='dropdown1', options=[
		{'label': i, 'value': i} for i in counts.spc_common.unique()
	],value='London planetree',multi=False, placeholder='Filter by species.'),
	dcc.Dropdown(id='dropdown2', options=[
		{'label': j, 'value': j} for j in counts.boroname.unique()
	],value='Queens',multi=False, placeholder='Filter by borough.'),
	html.H4(children='Raw numbers of trees'),
	html.Div(id='table-container')
])

@app.callback(
	dash.dependencies.Output('table-container', 'children'),
	[dash.dependencies.Input('dropdown1', 'value'),
	dash.dependencies.Input('dropdown2', 'value')])
def display_table(dropdown1_value,dropdown2_value):
	return generate_table(counts[(counts['spc_common'] == dropdown1_value) & (counts['boroname'] == dropdown2_value)])

if __name__ == '__main__':
	app.run_server(debug=True)
