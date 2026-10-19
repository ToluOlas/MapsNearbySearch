import time

import googlemaps
import pandas as pd

MIN_RADIUS_MILES = 0.5
MAX_RADIUS_MILES = 25.0


def miles_to_meters(miles):
    try:
        miles = float(miles)
        if miles < MIN_RADIUS_MILES or miles > MAX_RADIUS_MILES:
            raise ValueError(f"Radius must be between {MIN_RADIUS_MILES} and {MAX_RADIUS_MILES} miles.")
        return miles * 1609.34
    except (TypeError, ValueError):
        raise ValueError(f"Please enter a number between {MIN_RADIUS_MILES} and {MAX_RADIUS_MILES} miles.")


def geocode_location(map_client, location_name):
    geocode_result = map_client.geocode(location_name)
    if not geocode_result:
        raise ValueError("Location could not be found. Try a more specific place name.")

    geometry = geocode_result[0]["geometry"]["location"]
    return float(geometry["lat"]), float(geometry["lng"])


def get_nearby_places(search_string, location, distance, map_client):
    businesses = []

    response = map_client.places_nearby(
        location=location,
        radius=distance,
        name=search_string,
        keyword=search_string
    )

    businesses.extend(response.get('results'))
    next_page_token = response.get('next_page_token')

    while next_page_token:
        time.sleep(2)
        response = map_client.places_nearby(
            location=location,
            radius=distance,
            name=search_string,
            keyword=search_string,
            page_token=next_page_token
        )
        businesses.extend(response.get('results'))
        next_page_token = response.get('next_page_token')

    return businesses


def main():
    api_key = open("API_KEY.txt", "r").read().strip()
    map_client = googlemaps.Client(api_key)

    search_string = "grocery"

    while True:
        location_name = input("Enter a location to search: ").strip()
        if location_name:
            try:
                location = geocode_location(map_client, location_name)
                break
            except ValueError as exc:
                print(f"Location error: {exc}")

    while True:
        radius_input = input(f"Enter search radius in miles ({MIN_RADIUS_MILES}-{MAX_RADIUS_MILES}): ").strip()
        try:
            distance = miles_to_meters(radius_input)
            break
        except ValueError as exc:
            print(f"Invalid radius: {exc}")

    businesses = get_nearby_places(search_string, location, distance, map_client)
    print(f"Found {len(businesses)} results near {location_name}.")

    df = pd.DataFrame(businesses)
    if not df.empty and 'place_id' in df.columns:
        df['url'] = 'https://www.google.com/maps/place/?q=place_id:' + df['place_id']
    df.to_excel(f"Test {search_string} {location_name}.xlsx", index=False)


if __name__ == "__main__":
    main()