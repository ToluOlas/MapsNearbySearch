import pandas as pd
import re

dfs = pd.read_excel("Test grocery.xlsx")

print(dfs.head())
print(f"Total records: {len(dfs)}")
#print(dfs['name'].tolist())
#print((dfs['geometry'])[0])

for i in range(len(dfs)):
    #remove all non numerical (or related) characters, except commas
    dfs.loc[i, 'geometry'] = re.sub(r'[^0-9\.\-\,]', '', dfs['geometry'][i])

    #values split by commas
    firstComma = dfs.loc[i, 'geometry'].find(',')
    secondComma = dfs.loc[i, 'geometry'].find(',', firstComma + 1)

    #extract lat and long
    name = dfs.loc[i, 'name']
    lat = dfs.loc[i, 'geometry'][:firstComma]
    lng = dfs.loc[i, 'geometry'][firstComma + 1:secondComma]

    print(f"{name} | Latitude: {lat}, Longitude: {lng}")


#dfs.loc[0, 'geometry'] = dfs['geometry'][0].replace(' ', '')
#print(dfs['geometry'][0])

#for i in range(len(dfs)):
#    dfs.loc[i, 'geometry'] = dfs.loc[i, 'geometry'].replace(' ', '')

    #first set of curly braces
#    start = dfs.loc[i, 'geometry'].find('{') + 1
#    end = dfs.loc[i, 'geometry'].find('}')
#    dfs.loc[i, 'geometry'] = dfs.loc[i, 'geometry'][start:end]

#    print(dfs['geometry'][i])

#for i in range(len(dfs)):
#    dfs['geometry'][i] = dfs['geometry'][i].replace(' ', '')

#    #get everything inside the first set of curly braces
#    start = dfs['geometry'][i].find('{') + 1
#    end = dfs['geometry'][i].find('}')
#    dfs['geometry'][i] = dfs['geometry'][i][start:end]

#    print(dfs['geometry'][i])