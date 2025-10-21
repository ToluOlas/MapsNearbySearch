import googlemaps
import pandas as pd
import time

# distance conversion
def milesToMeters(miles):
    try:
        return miles * 1609.34
    except:
        return 0
    
API_KEY = open("API_KEY.txt", "r").read().strip()
mapClient = googlemaps.Client(API_KEY)

# Search location (latitude, longitude)
location = (51.60747338122455, 0.21888261375406246)
# Search parameters
searchString = "grocery"
# Search radius in meters
distance = milesToMeters(1) 
# List that holds all found businesses
businesses = []

response = mapClient.places_nearby(
    location=location,
    radius=distance,
    name=searchString,
    keyword=searchString
)

businesses.extend(response.get('results'))

print(f"Found {len(businesses)} results.")
#print(businesses[0])

nextPageToken = response.get('next_page_token')

while nextPageToken:
    time.sleep(2)  # Pause to allow token to become valid
    response = mapClient.places_nearby(
        location=location,
        radius=distance,
        name=searchString,
        keyword=searchString,
        page_token=nextPageToken
    )
    businesses.extend(response.get('results'))
    nextPageToken = response.get('next_page_token')

# Save results to excel file
df = pd.DataFrame(businesses)
df['url'] = 'https://www.google.com/maps/place/?q=place_id:' + df['place_id']
df.to_excel('{0}.xlsx'.format("Test "+searchString), index=False)

# Function for getting nearby places
#def getNearbyPlaces(searchString, location, distance):
#    response = mapClient.places_nearby(
#        location=location,
#        radius=distance,
#        name=searchString,
#        keyword=searchString
#    )
#
#    businesses = []
#    businesses.extend(response.get('results'))
#    nextPageToken = response.get('next_page_token')
#
#    while nextPageToken:
#        time.sleep(2)  # Pause to allow token to become valid
#        response = mapClient.places_nearby(
#            location=location,
#            radius=distance,
#            name=searchString,
#            keyword=searchString,
#            page_token=nextPageToken
#        )
#        businesses.extend(response.get('results'))
#        nextPageToken = response.get('next_page_token')
#
#    return businesses