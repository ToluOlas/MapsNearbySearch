const METERS_PER_MILE = 1609.34;
const DEFAULT_CENTER = { lat: 51.5074, lng: -0.1278 };

let mapView;

// Both map libraries are wrapped in the same small interface so the search
// logic below doesn't care which provider the server is using.
function createLeafletView(onMapClick) {
  const map = L.map("map").setView([DEFAULT_CENTER.lat, DEFAULT_CENTER.lng], 12);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  let circle;
  let searchMarker;
  let storeMarkers = [];

  map.on("click", (event) => onMapClick(event.latlng.lat, event.latlng.lng));

  return {
    setSearchMarker(center) {
      if (searchMarker) searchMarker.remove();
      searchMarker = L.circleMarker([center.lat, center.lng], {
        radius: 8,
        color: "#ffffff",
        weight: 2,
        fillColor: "#dc2626",
        fillOpacity: 1,
      })
        .bindTooltip("Search location")
        .addTo(map);
    },
    showSearchArea(center, radiusMiles) {
      if (circle) circle.remove();
      circle = L.circle([center.lat, center.lng], {
        radius: radiusMiles * METERS_PER_MILE,
        color: "#2563eb",
        weight: 2,
        fillOpacity: 0.12,
      }).addTo(map);
      map.fitBounds(circle.getBounds());
    },
    showStores(stores) {
      storeMarkers.forEach((marker) => marker.remove());
      storeMarkers = stores.map((store) =>
        L.marker([store.lat, store.lng]).bindPopup(store.name).addTo(map)
      );
      return storeMarkers;
    },
    focusStore(marker) {
      map.setView(marker.getLatLng(), Math.max(map.getZoom(), 15));
      marker.openPopup();
    },
  };
}

function createGoogleView(onMapClick) {
  const map = new google.maps.Map(document.getElementById("map"), {
    center: DEFAULT_CENTER,
    zoom: 12,
    mapTypeControl: true,
  });
  const infoWindow = new google.maps.InfoWindow();

  let circle;
  let searchMarker;
  let storeMarkers = [];

  map.addListener("click", (event) => onMapClick(event.latLng.lat(), event.latLng.lng()));

  return {
    setSearchMarker(center) {
      if (searchMarker) searchMarker.setMap(null);
      searchMarker = new google.maps.Marker({
        position: center,
        map,
        title: "Search location",
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: "#dc2626",
          fillOpacity: 1,
          strokeColor: "#ffffff",
          strokeWeight: 2,
        },
      });
    },
    showSearchArea(center, radiusMiles) {
      if (circle) circle.setMap(null);
      circle = new google.maps.Circle({
        strokeColor: "#2563eb",
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: "#2563eb",
        fillOpacity: 0.12,
        map,
        center,
        radius: radiusMiles * METERS_PER_MILE,
      });
      map.fitBounds(circle.getBounds());
    },
    showStores(stores) {
      storeMarkers.forEach((marker) => marker.setMap(null));
      storeMarkers = stores.map((store) => {
        const marker = new google.maps.Marker({
          position: { lat: store.lat, lng: store.lng },
          map,
          title: store.name,
        });
        marker.addListener("click", () => {
          infoWindow.setContent(store.name);
          infoWindow.open({ map, anchor: marker });
        });
        return marker;
      });
      return storeMarkers;
    },
    focusStore(marker) {
      map.panTo(marker.getPosition());
      if (map.getZoom() < 15) map.setZoom(15);
      google.maps.event.trigger(marker, "click");
    },
  };
}

function initMap() {
  const createView = MAPS_PROVIDER === "google" ? createGoogleView : createLeafletView;
  mapView = createView((lat, lng) => {
    document.getElementById("location-input").value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    mapView.setSearchMarker({ lat, lng });
  });
}

function setStatus(message, isError = false) {
  const status = document.getElementById("status");
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function appendText(parent, tag, text) {
  // textContent rather than innerHTML: store names come from third-party data
  const element = document.createElement(tag);
  element.textContent = text;
  parent.appendChild(element);
  return element;
}

function showResults(stores) {
  const markers = mapView.showStores(stores);
  const list = document.getElementById("results-list");
  list.innerHTML = "";

  stores.forEach((store, index) => {
    const item = document.createElement("li");
    appendText(item, "h3", store.name);
    appendText(item, "p", store.address);

    const details = [`${store.distance_miles} mi away`];
    if (store.rating != null) details.push(`Rating: ${store.rating}`);
    appendText(item, "p", details.join(" · "));

    const link = document.createElement("a");
    link.href = store.maps_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Open in Google Maps";
    link.addEventListener("click", (event) => event.stopPropagation());
    appendText(item, "p", "").appendChild(link);

    item.addEventListener("click", () => mapView.focusStore(markers[index]));
    list.appendChild(item);
  });
}

async function handleSearch(event) {
  event.preventDefault();

  const location = document.getElementById("location-input").value.trim();
  const radiusMiles = Number(document.getElementById("radius-input").value);
  const button = event.target.querySelector("button");

  if (!location) {
    setStatus("Please enter a location.", true);
    return;
  }
  if (!Number.isFinite(radiusMiles) || radiusMiles < minRadiusMiles || radiusMiles > maxRadiusMiles) {
    setStatus(`Radius must be between ${minRadiusMiles} and ${maxRadiusMiles} miles.`, true);
    return;
  }

  button.disabled = true;
  setStatus("Searching…");

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location, radius: radiusMiles }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Search failed.");
    }

    mapView.setSearchMarker(data.center);
    mapView.showSearchArea(data.center, Number(data.radiusMiles));
    showResults(data.results);

    const count = data.results.length;
    const source = data.cached ? " (cached)" : "";
    setStatus(
      count
        ? `Found ${count} store${count === 1 ? "" : "s"}, nearest first${source}.`
        : `No grocery stores found in this area${source}.`
    );
  } catch (error) {
    setStatus(error.message || "Something went wrong.", true);
  } finally {
    button.disabled = false;
  }
}

if (MAPS_PROVIDER !== "google") {
  initMap();
}
document.getElementById("search-form").addEventListener("submit", handleSearch);
