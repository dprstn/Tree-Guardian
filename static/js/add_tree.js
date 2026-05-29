

function closeMap() {
    document.getElementById('map-modal').style.display = 'none';
    document.getElementById('loc-status').style.display = 'block';
}

function validateForm() {
    const lat = document.getElementById('lat').value;
    const lng = document.getElementById('lng').value;

    if (!lat || !lng) {
        alert("Please select a location on the map.");
        return false;
    }

    return true;
}