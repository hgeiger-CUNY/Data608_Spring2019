#Import modules.

import pandas as pd

from flask import Flask, jsonify

#Start app.

app = Flask(__name__)

#Start by simply getting health levels (across all boroughs) per species, for all species.
#Then, can just select from here for the species chosen by the user.

soql_url = ('https://data.cityofnewyork.us/resource/nwxe-4ae8.json?' +\
	'$select=spc_common,health,count(tree_id)' +\
	'&$group=spc_common,health').replace(' ', '%20')

counts = pd.read_json(soql_url)

counts = counts.dropna() #Remove rows missing information.

#Accept species name from the URL name.
#Then return counts per health level in JSON format.

@app.route('/species/<string:name>')
def return_species(name):
	counts_of_interest = counts[counts['spc_common'] == name]
	return jsonify(pd.Series(counts_of_interest.count_tree_id.values,index=counts_of_interest.health).to_dict())

#Run app.

if __name__ == '__main__':
    app.run(debug=True)
