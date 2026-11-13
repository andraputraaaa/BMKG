document.addEventListener('DOMContentLoaded', function() {
    const defaultCenter = [-2.5489, 118.0149];
    const defaultZoom = 5;
    
    const map = L.map('map', { preferCanvas: true }).setView(defaultCenter, defaultZoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | BMKG IBF EWS',
        maxZoom: 19
    }).addTo(map);

    let cityMarkersGroup = L.layerGroup().addTo(map);
    let masterEWSData = [];

    // State Filter Active
    let activeProvFilter = 'ALL';
    let activeRiskFilter = 'ALL';

    // 1. JAM REAL-TIME (WIB)
    function startRealTimeClock() {
        const clockElem = document.getElementById('live-clock');
        if (!clockElem) return;

        setInterval(() => {
            const now = new Date();
            const timeString = now.toLocaleTimeString('id-ID', { hour12: false }) + ' WIB';
            const dateString = now.toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric', month: 'short' });
            clockElem.innerHTML = `${dateString}, ${timeString}`;
        }, 1000);
    }
    startRealTimeClock();

    // 2. FUNGSI UTAMA RENDER MARKER DENGAN COMBINED FILTER
    function renderEWSMarkers() {
        cityMarkersGroup.clearLayers();

        let filteredData = masterEWSData;
        
        // Filter 1: Provinsi
        if (activeProvFilter !== 'ALL' && activeProvFilter !== '0000' && activeProvFilter !== '') {
            const targetProv = String(activeProvFilter).trim();
            filteredData = filteredData.filter(item => {
                const itemProv = String(item.province_code || '').trim();
                return itemProv === targetProv || itemProv.startsWith(targetProv.substring(0, 2));
            });
        }

        // Filter 2: Tingkat Risiko IBF
        if (activeRiskFilter !== 'ALL') {
            filteredData = filteredData.filter(item => {
                const status = (item.ibf_status ? item.ibf_status.status : '').toUpperCase();
                return status === activeRiskFilter;
            });
        }

        let bounds = [];
        let highRiskCount = 0;

        filteredData.forEach(item => {
            let coords = null;
            if (item.coordinates && item.coordinates.length === 2 && item.coordinates[0] && item.coordinates[1]) {
                coords = [parseFloat(item.coordinates[0]), parseFloat(item.coordinates[1])];
            } else if (item.weather && item.weather.lat && item.weather.lon) {
                coords = [parseFloat(item.weather.lat), parseFloat(item.weather.lon)];
            }

            if (!coords) return;

            bounds.push(coords);
            const ibf = item.ibf_status || {};
            const scores = ibf.scores || { hazard: 1, exposure: 1, vulnerability: 1, risk_index: 1 };
            const color = ibf.color || ibf.color_code || "#00FF00";
            const status = ibf.status || ibf.risk_level || "AMAN";
            const action = ibf.action || ibf.rekomendasi || "Kondisi aman terkendali.";
            const cityName = item.region || item.city || "Kota/Kabupaten";

            const windSpeed = item.weather ? (item.weather.wind_speed || item.weather.wind || 0) : 0;
            const rainfall = item.weather ? (item.weather.rainfall || item.weather.rain || 0) : 0;
            const windStatus = ibf.wind_status || "Lemah / Normal";
            const rainStatus = ibf.rain_status || "Ringan / Cerah";

            if (status === 'AWAS' || status === 'SIAGA' || color === '#FF0000' || color === '#FFA500') {
                highRiskCount++;
            }

            const cityMarker = L.circleMarker(coords, {
                radius: 7,
                fillColor: color,
                color: "#1e293b",
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: 0.9
            });

            const popupContent = `
                <div style="font-family: Arial, sans-serif; min-width:250px; color:#2c3e50;">
                    <h4 style="margin-bottom:6px; border-bottom:2px solid ${color}; padding-bottom:3px; color:#1e293b;">${cityName}</h4>
                    
                    <p style="margin:4px 0;"><b>Status IBF:</b> 
                        <span style="background:${color}; color:${color==='#FFFF00'?'#000':'#fff'}; padding:2px 6px; border-radius:3px; font-weight:bold;">
                            ${status}
                        </span>
                    </p>

                    <div style="background:#f8f9fa; border:1px solid #e9ecef; padding:6px; border-radius:4px; margin:8px 0; font-size:0.82rem;">
                        <b>Detail Skor Matriks Risiko (RI):</b><br>
                        • Hazard (H): <b>${scores.hazard}</b>/3<br>
                        • Exposure (E): <b>${scores.exposure}</b>/3<br>
                        • Vulnerability (V): <b>${scores.vulnerability}</b>/3<br>
                        <span style="color:#d35400;"><b>→ Risk Index (H×E×V): ${scores.risk_index}</b></span>
                    </div>

                    <p style="margin:3px 0; font-size:0.85rem;">
                        <b>Kecepatan Angin:</b> ${windSpeed} knot <br>
                        <small style="color:#64748b;"><i>(${windStatus})</i></small>
                    </p>
                    <p style="margin:3px 0; font-size:0.85rem;">
                        <b>Curah Hujan (RR):</b> ${rainfall} mm/jam <br>
                        <small style="color:#64748b;"><i>(${rainStatus})</i></small>
                    </p>
                    <p style="margin:3px 0; font-size:0.85rem;"><b>Kepadatan Penduduk:</b> ${item.population ? (item.population.kepadatan || 1000) : 1000} jiwa/km²</p>
                    <p style="margin:3px 0; font-size:0.85rem;"><b>Tutupan Lahan:</b> ${item.land_cover ? item.land_cover.land_type : '-'}</p>
                    
                    <hr style="margin:6px 0;">
                    <p style="margin:4px 0; font-size:0.82rem; color:#e11d48;"><b>Rekomendasi:</b> ${action}</p>
                </div>
            `;

            cityMarker.bindPopup(popupContent);

            cityMarker.on('mouseover', function() {
                this.setStyle({ radius: 10, weight: 2.5 });
            });
            cityMarker.on('mouseout', function() {
                this.setStyle({ radius: 7, weight: 1.5 });
            });

            cityMarkersGroup.addLayer(cityMarker);
        });

        // Update Ringkasan Sidebar
        const summaryElem = document.getElementById('summary-content');
        if (summaryElem) {
            summaryElem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center p-2 bg-light rounded mb-2">
                    <span class="small text-muted">Wilayah Tampil:</span>
                    <span class="fw-bold text-dark">${filteredData.length} Wilayah</span>
                </div>
                <div class="d-flex justify-content-between align-items-center p-2 bg-danger-subtle rounded text-danger">
                    <span class="small fw-semibold">Status SIAGA / AWAS:</span>
                    <span class="fw-bold fs-6">${highRiskCount} Wilayah</span>
                </div>
            `;
        }

        if (activeProvFilter !== 'ALL' && bounds.length > 0) {
            map.flyToBounds(bounds, { padding: [50, 50], maxZoom: 9, duration: 1.0 });
        }
    }

    // 3. FETCH DATA DARI FLASK API
    function fetchMasterData() {
        fetch('/api/ibf-ews-data?province_code=ALL')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(res => {
                const timestampElem = document.getElementById('data-timestamp');
                if (timestampElem) {
                    const now = new Date();
                    const fetchTime = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
                    timestampElem.innerHTML = `Diperbarui: <b>${fetchTime} WIB</b>`;
                }

                if (res.success && res.data) {
                    masterEWSData = res.data;
                    renderEWSMarkers();
                } else {
                    throw new Error(res.message || 'API mengembalikan data tidak valid');
                }
            })
            .catch(err => console.error("Error fetching Master IBF Data:", err));
    }

    fetchMasterData();
    setInterval(fetchMasterData, 10 * 60 * 1000);

    // 4. LIVE SEARCH AUTOCOMPLETE
    const searchInput = document.getElementById('search-region');
    const searchResults = document.getElementById('search-results');

    if (searchInput && searchResults) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase().trim();
            searchResults.innerHTML = '';

            if (query.length < 2) {
                searchResults.classList.add('d-none');
                return;
            }

            const matches = masterEWSData.filter(item => {
                const cityName = (item.region || item.city || '').toLowerCase();
                const provName = (item.province || '').toLowerCase();
                return cityName.includes(query) || provName.includes(query);
            }).slice(0, 8);

            if (matches.length === 0) {
                searchResults.innerHTML = `<div class="list-group-item list-group-item-action disabled small py-2">Wilayah tidak ditemukan</div>`;
            } else {
                matches.forEach(item => {
                    const cityName = item.region || item.city || 'Kota';
                    const provName = item.province || '';
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'list-group-item list-group-item-action small py-2 text-start';
                    btn.innerHTML = `<b>${cityName}</b> <span class="text-muted small">(${provName})</span>`;
                    
                    btn.addEventListener('click', function() {
                        searchInput.value = cityName;
                        searchResults.classList.add('d-none');

                        let coords = null;
                        if (item.coordinates && item.coordinates.length === 2) {
                            coords = [parseFloat(item.coordinates[0]), parseFloat(item.coordinates[1])];
                        }

                        if (coords) {
                            map.flyTo(coords, 10, { duration: 1.2 });
                            cityMarkersGroup.eachLayer(layer => {
                                const latLng = layer.getLatLng();
                                if (Math.abs(latLng.lat - coords[0]) < 0.01 && Math.abs(latLng.lng - coords[1]) < 0.01) {
                                    layer.openPopup();
                                }
                            });
                        }
                    });
                    searchResults.appendChild(btn);
                });
            }
            searchResults.classList.remove('d-none');
        });

        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.add('d-none');
            }
        });
    }

    // 5. LISTEN FILTER TINGKAT RISIKO
    const riskFilterButtons = document.querySelectorAll('[data-risk-filter]');
    riskFilterButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            riskFilterButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            activeRiskFilter = this.getAttribute('data-risk-filter');
            renderEWSMarkers();
        });
    });

    // 6. LISTEN DROPDOWN PROVINSI
    const selectProv = document.getElementById('select-province');
    if (selectProv) {
        selectProv.addEventListener('change', function(e) {
            activeProvFilter = e.target.value;
            if (activeProvFilter === 'ALL') {
                map.flyTo(defaultCenter, defaultZoom, { duration: 1.0 });
            }
            renderEWSMarkers();
        });
    }

    // 7. BUTTON VIEW SATU INDONESIA
    const btnNational = document.getElementById('btn-national-view');
    if (btnNational) {
        btnNational.addEventListener('click', function() {
            if (selectProv) selectProv.value = 'ALL';
            activeProvFilter = 'ALL';
            map.flyTo(defaultCenter, defaultZoom, { duration: 1.0 });
            renderEWSMarkers();
        });
    }

});