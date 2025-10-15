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

location = (37.7749, -122.4194)  # Example: San Francisco, CA
searchString = "restaurants"
distance = milesToMeters(15)
businesses = []

response = mapClient.places_nearby(
    location=location,
    radius=distance,
    name=searchString,
    keyword=searchString
)

businesses.extend(response.get('results'))
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

df = pd.DataFrame(businesses)
df['url'] = 'https://www.google.com/maps/place/?q=place_id:' + df['place_id']
df.to_excel('{0}.xlsx'.format(searchString), index=False)