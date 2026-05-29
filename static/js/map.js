let map;
let marker;

function setMarker(lat, lng) {
    if (marker) {
        map.removeLayer(marker);
    }

    marker = L.marker([lat, lng]).addTo(map);

    document.getElementById('lat').value = lat;
    document.getElementById('lng').value = lng;

    document.getElementById('coords-display').innerText =
        `(${lat.toFixed(4)}, ${lng.toFixed(4)})`;

    document.getElementById('btn-done').disabled = false;
    document.getElementById('btn-done').style.opacity = "1";
    document.getElementById('btn-done').style.cursor = "pointer";
}

function openMap() {
    document.getElementById('btn-done').disabled = true;
    document.getElementById('btn-done').style.opacity = '0.5';
    document.getElementById('map-modal').style.display = 'block';

    let latInput = document.getElementById('lat').value;
    let lngInput = document.getElementById('lng').value;

    let lat = latInput ? parseFloat(latInput) : 51.89;
    let lng = lngInput ? parseFloat(lngInput) : -2.06;


    if (!map) {
        map = L.map('map').setView([lat, lng], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);



        // for edit mode //
         if (latInput && lngInput) {
            setMarker(lat, lng);
         }

         map.on('click', function(e) {
              setMarker(e.latlng.lat, e.latlng.lng);
         });


    } else {
    map.setView([lat, lng], 13);



        if (latInput && lngInput) {
        setMarker(lat, lng);
    }
    }

    setTimeout(() => { map.invalidateSize(); }, 200);
}