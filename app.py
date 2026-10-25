import os
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request
import googlemaps

BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / "API_KEY.txt"


def load_api_key():
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key and KEY_FILE.exists():
        api_key = KEY_FILE.read_text(encoding="utf-8").strip()

    if not api_key.startswith("AIza"):
        raise SystemExit(
            "No valid Google Maps API key found.\n"
            "Set the GOOGLE_MAPS_API_KEY environment variable, or put the key in API_KEY.txt.\n"
            "The key needs the Maps JavaScript API, Geocoding API and Places API enabled."
        )
    return api_key


API_KEY = load_api_key()
CLIENT = googlemaps.Client(API_KEY)

app = Flask(__name__)
MAX_RADIUS_MILES = 25.0
MIN_RADIUS_MILES = 0.5


def validate_radius(radius_value):
    try:
        radius_miles = float(radius_value)
    except (TypeError, ValueError):
        raise ValueError(f"Radius must be a number between {MIN_RADIUS_MILES} and {MAX_RADIUS_MILES} miles.")

    if radius_miles < MIN_RADIUS_MILES or radius_miles > MAX_RADIUS_MILES:
        raise ValueError(f"Radius must be between {MIN_RADIUS_MILES} and {MAX_RADIUS_MILES} miles.")

    return radius_miles


def geocode_location(location_name):
    geocode_result = CLIENT.geocode(location_name)
    if not geocode_result:
        raise ValueError("Location could not be found. Please try a more specific place name.")

    location = geocode_result[0]["geometry"]["location"]
    return float(location["lat"]), float(location["lng"])


def get_nearby_places(location, radius_miles, search_string="grocery"):
    radius_meters = int(radius_miles * 1609.34)
    businesses = []

    response = CLIENT.places_nearby(
        location=location,
        radius=radius_meters,
        name=search_string,
        keyword=search_string,
    )

    businesses.extend(response.get("results", []))
    next_page_token = response.get("next_page_token")

    while next_page_token:
        time.sleep(2)
        response = CLIENT.places_nearby(
            location=location,
            radius=radius_meters,
            name=search_string,
            keyword=search_string,
            page_token=next_page_token,
        )
        businesses.extend(response.get("results", []))
        next_page_token = response.get("next_page_token")

    return businesses


@app.get("/")
def index():
    return render_template("index.html", api_key=API_KEY, max_radius=MAX_RADIUS_MILES)


@app.post("/api/search")
def search():
    payload = request.get_json(silent=True) or {}
    location_name = (payload.get("location") or "").strip()
    radius_value = payload.get("radius")

    if not location_name:
        return jsonify({"error": "Location is required."}), 400

    try:
        radius_miles = validate_radius(radius_value)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        center = geocode_location(location_name)
        places = get_nearby_places(center, radius_miles, "grocery")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except googlemaps.exceptions.ApiError as exc:
        # e.g. REQUEST_DENIED when the key lacks Geocoding/Places access
        return jsonify({"error": f"Google Maps API error: {exc}"}), 502
    except (googlemaps.exceptions.TransportError, googlemaps.exceptions.Timeout) as exc:
        return jsonify({"error": f"Could not reach Google Maps: {exc}"}), 502

    results = []
    for place in places:
        geometry = place.get("geometry", {}).get("location", {})
        results.append(
            {
                "name": place.get("name", "Unknown place"),
                "address": place.get("vicinity", "No address provided"),
                "rating": place.get("rating"),
                "place_id": place.get("place_id"),
                "lat": geometry.get("lat"),
                "lng": geometry.get("lng"),
                "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id')}",
            }
        )

    return jsonify(
        {
            "center": {"lat": center[0], "lng": center[1]},
            "radiusMiles": radius_miles,
            "results": results,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
