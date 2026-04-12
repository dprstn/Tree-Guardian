let map;
let marker;

function openMap() {
    document.getElementById('btn-done').disabled = true;
    document.getElementById('btn-done').style.opacity = '0.5';
    document.getElementById('map-modal').style.display = 'block';

    if (!map) {
        map = L.map('map').setView([51.89, -2.06], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        map.on('click', function(e) {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;

            if (marker) { map.removeLayer(marker); }
            marker = L.marker([lat, lng]).addTo(map);

            document.getElementById('lat').value = lat;
            document.getElementById('lng').value = lng;

            document.getElementById('coords-display').innerText =
                `(${lat.toFixed(4)}, ${lng.toFixed(4)})`;

            document.getElementById('btn-done').disabled = false;
            document.getElementById('btn-done').style.opacity = "1";
            document.getElementById('btn-done').style.cursor = "pointer";

        });
    }

    setTimeout(() => { map.invalidateSize(); }, 200);
}