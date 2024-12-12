// MAP JS
// Map initialization and management
class RestaurantMap {
  constructor() {
    this.map = null;
    this.markers = [];
  }

  initialize() {
    // Initialize the map only if it hasn't been initialized yet
    if (!this.map && document.getElementById("map")) {
      this.map = L.map("map").setView([55.6845, 12.564148], 12);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 20,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(this.map);

      // Load markers immediately after initialization
      this.loadMarkers();
    }
  }

  loadMarkers() {
    // Fetch restaurant coordinates from the API
    fetch("/coordinates")
      .then((response) => response.json())
      .then((coordinates) => {
        // Clear existing markers
        this.clearMarkers();

        // Add new markers
        coordinates.forEach((coord) => {
          const marker = L.marker(JSON.parse(coord.coordinates)).addTo(
            this.map
          );
          marker.bindPopup(`
                        <a href="/restaurant/${coord.restaurant_fk}" 
                           class="text-c-tealblue:-5 text-95 d-flex flex-col" hover="text-c-tealblue:-12">
                           ${coord.user_name}
                           <span class="text-85 text-c-gray:-5">${coord.address}</span>
                        </a>
                    `);
          this.markers.push(marker);
        });
      })
      .catch((error) => {
        console.error("Error loading markers:", error);
      });
  }

  clearMarkers() {
    this.markers.forEach((marker) => marker.remove());
    this.markers = [];
  }

  // Method to refresh map size when tab is switched
  refreshSize() {
    if (this.map) {
      setTimeout(() => {
        this.map.invalidateSize();
      }, 100);
    }
  }
}

// Initialize map when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("map")) {
    window.restaurantMap = new RestaurantMap();
    window.restaurantMap.initialize();
  }
});
