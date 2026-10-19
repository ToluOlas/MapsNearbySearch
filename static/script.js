let map;
let circle;
let markers = [];
let searchMarker;

function initMap() {
  const defaultCenter = { lat: 51.5074, lng: -0.1278 };
  map = new google.maps.Map(document.getElementById("map"), {
    center: defaultCenter,
    zoom: 12,
    mapTypeControl: true,
  });

  map.addListener("click", (event) => {
    const latLng = event.latLng;
    const lat = latLng.lat();
    const lng = latLng.lng();

    if (searchMarker) {
      searchMarker.setMap(null);
    }

    searchMarker = new google.maps.Marker({
      position: { lat, lng },
      map,
      title: "Selected location",
    });

    document.getElementById("location-input").value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    setMapCenter({ lat, lng }, 12);
  });

  setMapCenter(defaultCenter, 12);
}

function setMapCenter(center, zoom = 12) {
  map.setCenter(center);
  map.setZoom(zoom);
}

function clearMarkers() {
  markers.forEach((marker) => marker.setMap(null));
  markers = [];
}

function drawSearchCircle(center, radiusMiles) {
  if (circle) {
    circle.setMap(null);
  }

  circle = new google.maps.Circle({
    strokeColor: "#4285F4",
    strokeOpacity: 0.8,
    strokeWeight: 2,
    fillColor: "#4285F4",
    fillOpacity: 0.15,
    map,
    center,
    radius: radiusMiles * 1609.34,
  });
}

function showResults(results) {
  clearMarkers();

  const list = document.getElementById("results-list");
  list.innerHTML = "";

  results.forEach((place) => {
    const marker = new google.maps.Marker({
      position: { lat: place.lat, lng: place.lng },
      map,
      title: place.name,
    });

    markers.push(marker);

    const listItem = document.createElement("li");
    listItem.innerHTML = `
      <h3>${place.name}</h3>
      <p>${place.address}</p>
      <p>Rating: ${place.rating ?? "N/A"}</p>
      <p><a href="${place.maps_url}" target="_blank" rel="noreferrer">Open in Google Maps</a></p>
    `;
    list.appendChild(listItem);
  });
}

async function handleSearch(event) {
  event.preventDefault();

  const location = document.getElementById("location-input").value.trim();
  const radius = document.getElementById("radius-input").value.trim();

  if (!location) {
    alert("Please enter a location.");
    return;
  }

  const radiusNum = Number(radius);
  if (!Number.isFinite(radiusNum) || radiusNum < 0.5 || radiusNum > maxRadiusMiles) {
    alert(`Radius must be between 0.5 and ${maxRadiusMiles} miles.`);
    return;
  }

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location, radius: radiusNum }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Search failed.");
    }

    const center = data.center;
    const radiusMiles = Number(data.radiusMiles);

    if (searchMarker) {
      searchMarker.setMap(null);
    }

    searchMarker = new google.maps.Marker({
      position: center,
      map,
      title: "Search location",
    });

    setMapCenter(center, 12);
    drawSearchCircle(center, radiusMiles);
    showResults(data.results);
  } catch (error) {
    alert(error.message || "Something went wrong.");
  }
}

document.getElementById("search-form").addEventListener("submit", handleSearch);
