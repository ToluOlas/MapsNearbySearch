import math
import os
import re
import time
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / "API_KEY.txt"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Public Overpass servers are free but can be slow or busy, so fall back to a mirror
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
# The OpenStreetMap services reject requests without an identifying User-Agent
OSM_HEADERS = {"User-Agent": "MapsNearbySearch/0.1 (grocery price comparison prototype)"}
GROCERY_SHOP_TYPES = "supermarket|grocery|greengrocer"

METERS_PER_MILE = 1609.34
MAX_RADIUS_MILES = 25.0
MIN_RADIUS_MILES = 0.5
COORDINATES_PATTERN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")

app = Flask(__name__)


def load_api_key():
    """Return a Google Maps key if one is configured, otherwise None (use OpenStreetMap)."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key and KEY_FILE.exists():
        api_key = KEY_FILE.read_text(encoding="utf-8").strip()
    return api_key if api_key.startswith("AIza") else None


API_KEY = load_api_key()
PROVIDER = "google" if API_KEY else "osm"
UPSTREAM_ERRORS = (requests.RequestException,)

if PROVIDER == "google":
    import googlemaps

    CLIENT = googlemaps.Client(API_KEY)
    UPSTREAM_ERRORS += (
        googlemaps.exceptions.ApiError,
        googlemaps.exceptions.TransportError,
        googlemaps.exceptions.Timeout,
    )


def validate_radius(radius_value):
    try:
        radius_miles = float(radius_value)
    except (TypeError, ValueError):
        raise ValueError(f"Radius must be a number between {MIN_RADIUS_MILES} and {MAX_RADIUS_MILES} miles.")

    if radius_miles < MIN_RADIUS_MILES or radius_miles > MAX_RADIUS_MILES:
        raise ValueError(f"Radius must be between {MIN_RADIUS_MILES} and {MAX_RADIUS_MILES} miles.")

    return radius_miles


def parse_coordinates(text):
    """Accept "lat, lng" input (e.g. from a map click) without a geocoding call."""
    match = COORDINATES_PATTERN.match(text)
    if not match:
        return None

    lat, lng = float(match.group(1)), float(match.group(2))
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return lat, lng
    return None


def geocode_location(location_name):
    coordinates = parse_coordinates(location_name)
    if coordinates:
        return coordinates

    if PROVIDER == "google":
        geocode_result = CLIENT.geocode(location_name)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return float(location["lat"]), float(location["lng"])
    else:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": location_name, "format": "jsonv2", "limit": 1},
            headers=OSM_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        geocode_result = response.json()
        if geocode_result:
            return float(geocode_result[0]["lat"]), float(geocode_result[0]["lon"])

    raise ValueError("Location could not be found. Please try a more specific place name.")


def distance_miles(origin, lat, lng):
    lat1, lng1, lat2, lng2 = map(math.radians, (origin[0], origin[1], lat, lng))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def make_store(center, name, address, lat, lng, rating=None, place_id=None):
    if place_id:
        maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    else:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

    return {
        "name": name,
        "address": address,
        "rating": rating,
        "place_id": place_id,
        "lat": lat,
        "lng": lng,
        "distance_miles": round(distance_miles(center, lat, lng), 2),
        "maps_url": maps_url,
    }


def google_nearby_stores(center, radius_miles, search_string="grocery"):
    params = {
        "location": center,
        "radius": int(radius_miles * METERS_PER_MILE),
        "name": search_string,
        "keyword": search_string,
    }
    response = CLIENT.places_nearby(**params)
    places = response.get("results", [])
    next_page_token = response.get("next_page_token")

    while next_page_token:
        # Google needs a moment before a page token becomes valid
        time.sleep(2)
        response = CLIENT.places_nearby(**params, page_token=next_page_token)
        places.extend(response.get("results", []))
        next_page_token = response.get("next_page_token")

    stores = []
    for place in places:
        location = place.get("geometry", {}).get("location", {})
        if "lat" not in location:
            continue
        stores.append(
            make_store(
                center,
                name=place.get("name", "Unknown place"),
                address=place.get("vicinity", "No address provided"),
                lat=location["lat"],
                lng=location["lng"],
                rating=place.get("rating"),
                place_id=place.get("place_id"),
            )
        )
    return stores


def format_osm_address(tags):
    street = " ".join(part for part in (tags.get("addr:housenumber"), tags.get("addr:street")) if part)
    parts = [part for part in (street, tags.get("addr:city"), tags.get("addr:postcode")) if part]
    return ", ".join(parts) or "No address listed"


def osm_nearby_stores(center, radius_miles):
    query = f"""
        [out:json][timeout:25];
        nwr["shop"~"^({GROCERY_SHOP_TYPES})$"](around:{int(radius_miles * METERS_PER_MILE)},{center[0]},{center[1]});
        out center tags;
    """
    for url in OVERPASS_URLS:
        try:
            response = requests.post(url, data={"data": query}, headers=OSM_HEADERS, timeout=(10, 45))
            response.raise_for_status()
            elements = response.json()["elements"]
            break
        except (requests.RequestException, ValueError, KeyError) as exc:
            last_error = exc
    else:
        raise requests.RequestException(f"All Overpass servers failed (last error: {last_error})")

    stores = []
    for element in elements:
        # Nodes carry their own coordinates; ways and relations get a computed center
        point = element if element["type"] == "node" else element.get("center")
        if not point:
            continue
        tags = element.get("tags", {})
        stores.append(
            make_store(
                center,
                name=tags.get("name") or tags.get("brand") or "Unnamed store",
                address=format_osm_address(tags),
                lat=point["lat"],
                lng=point["lon"],
            )
        )
    return stores


@app.get("/")
def index():
    return render_template(
        "index.html",
        provider=PROVIDER,
        api_key=API_KEY or "",
        min_radius=MIN_RADIUS_MILES,
        max_radius=MAX_RADIUS_MILES,
    )


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
        if PROVIDER == "google":
            stores = google_nearby_stores(center, radius_miles)
        else:
            stores = osm_nearby_stores(center, radius_miles)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except UPSTREAM_ERRORS as exc:
        # e.g. REQUEST_DENIED from Google, or a busy/rate-limited OpenStreetMap server
        return jsonify({"error": f"Map data service error, please try again: {exc}"}), 502

    stores.sort(key=lambda store: store["distance_miles"])
    return jsonify(
        {
            "center": {"lat": center[0], "lng": center[1]},
            "radiusMiles": radius_miles,
            "results": stores,
        }
    )


if __name__ == "__main__":
    print(f"Map data provider: {'Google Maps' if PROVIDER == 'google' else 'OpenStreetMap (no API key)'}")
    app.run(debug=True)
