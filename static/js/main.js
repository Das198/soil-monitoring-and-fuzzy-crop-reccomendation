document.addEventListener('DOMContentLoaded', () => {
    // Referensi Elemen UI Sensor
    const elKelembapan = document.getElementById('val-kelembapan');
    const elSuhu = document.getElementById('val-suhu');
    const elPh = document.getElementById('val-ph');
    const elNitrogen = document.getElementById('val-nitrogen');
    const elFosfor = document.getElementById('val-fosfor');
    const elKalium = document.getElementById('val-kalium');
    const elSalinitas = document.getElementById('val-salinitas');
    
    // Referensi Status & Container
    const elConnDot = document.getElementById('conn-dot');
    const elConnStatus = document.getElementById('conn-status');
    const elLastUpdate = document.getElementById('last-update');
    const cropContainer = document.getElementById('crop-container');
    const expandedContainer = document.getElementById('expanded-container');
    const toggleBtn = document.getElementById('toggle-expand-btn');
    const template = document.getElementById('crop-card-template');

    // Polling Interval (dalam milidetik)
    const POLL_INTERVAL = 5000;

    // State expand/collapse
    let isExpanded = false;
    let allRekomendasiData = [];

    // Toggle expand
    toggleBtn.addEventListener('click', () => {
        isExpanded = !isExpanded;
        if (isExpanded) {
            expandedContainer.classList.add('expanded');
            toggleBtn.innerHTML = 'Sembunyikan <span class="toggle-arrow">▲</span>';
            renderExpandedList(allRekomendasiData);
        } else {
            expandedContainer.classList.remove('expanded');
            toggleBtn.innerHTML = 'Lihat Selengkapnya <span class="toggle-arrow">▼</span>';
            expandedContainer.innerHTML = '';
        }
    });

    async function fetchData() {
        try {
            const response = await fetch('/api/data');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                updateSensorData(data.sensor);
                allRekomendasiData = data.rekomendasi || [];
                updateRecommendations(allRekomendasiData);
                
                const isSensorActive = checkSensorActive(data.sensor ? data.sensor.timestamp : data.timestamp);
                updateConnectionStatus(isSensorActive);
                
                updateTimestamp(data.timestamp);
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        } catch (error) {
            console.error("Gagal mengambil data:", error);
            updateConnectionStatus(false);
        }
    }

    function updateSensorData(sensor) {
        if (!sensor) return;

        animateValue(elKelembapan, parseFloat(elKelembapan.innerText) || 0, sensor.kelembapan_tanah || 0, 500);
        animateValue(elSuhu, parseFloat(elSuhu.innerText) || 0, sensor.suhu || 0, 500);
        animateValue(elPh, parseFloat(elPh.innerText) || 0, sensor.ph_tanah || 0, 500);
        animateValue(elNitrogen, parseFloat(elNitrogen.innerText) || 0, sensor.nitrogen || 0, 500);
        animateValue(elFosfor, parseFloat(elFosfor.innerText) || 0, sensor.fosfor || 0, 500);
        animateValue(elKalium, parseFloat(elKalium.innerText) || 0, sensor.kalium || 0, 500);
        animateValue(elSalinitas, parseFloat(elSalinitas.innerText) || 0, sensor.salinity || 0, 500);
    }

    function checkSensorActive(timestampIso) {
        if (!timestampIso) return false;
        const dataTime = new Date(timestampIso).getTime();
        const now = new Date().getTime();
        return (now - dataTime) < 15000;
    }

    // Konfigurasi medali untuk Top 3
    const MEDALS = [
        { label: '🥇 Terbaik', class: 'medal-gold' },
        { label: '🥈 Terbaik Kedua', class: 'medal-silver' },
        { label: '🥉 Terbaik Ketiga', class: 'medal-bronze' },
    ];

    function updateRecommendations(rekomendasiList) {
        if (!rekomendasiList || rekomendasiList.length === 0) {
            cropContainer.innerHTML = '<div class="loading-text">Data rekomendasi belum tersedia.</div>';
            return;
        }

        cropContainer.innerHTML = '';

        // Render Top 3 dengan medali
        const top3 = rekomendasiList.slice(0, 3);
        top3.forEach((item, index) => {
            const card = buildCropCard(item, MEDALS[index]);
            cropContainer.appendChild(card);
        });

        // Jika expand aktif, refresh juga isinya
        if (isExpanded) {
            renderExpandedList(rekomendasiList);
        }
    }

    function renderExpandedList(rekomendasiList) {
        expandedContainer.innerHTML = '';
        // Semua tanaman (tanpa Top 3 yang sudah tampil)
        const rest = rekomendasiList.slice(3);
        if (rest.length === 0) {
            expandedContainer.innerHTML = '<div class="loading-text" style="grid-column:1/-1">Tidak ada data tambahan.</div>';
            return;
        }
        rest.forEach((item, index) => {
            const card = buildCropCard(item, null, index + 4);
            expandedContainer.appendChild(card);
        });
    }

    function buildCropCard(item, medal = null, rank = null) {
        const clone = template.content.cloneNode(true);
        const cardEl = clone.querySelector('.crop-card');

        // Tambah class medali jika ada
        if (medal) {
            cardEl.classList.add(medal.class);
            const medalLabel = document.createElement('div');
            medalLabel.className = 'medal-label';
            medalLabel.textContent = medal.label;
            cardEl.prepend(medalLabel);
        } else if (rank) {
            // Tambahkan nomor urut untuk tanaman di bawah Top 3
            const rankLabel = document.createElement('div');
            rankLabel.className = 'rank-label';
            rankLabel.textContent = `#${rank}`;
            cardEl.prepend(rankLabel);
        }

        // Set Data Dasar
        clone.querySelector('.crop-name').textContent = item.nama;
        
        const badge = clone.querySelector('.crop-badge');
        badge.textContent = item.status;
        if (item.skor < 60 && item.skor >= 40) {
            badge.classList.add('warning');
        } else if (item.skor < 40) {
            badge.classList.add('danger');
        }

        // Set Skor Persentase & Ring Circle
        const skor = Math.round(item.skor);
        clone.querySelector('.percentage-text').textContent = `${skor}%`;
        
        const circleFill = clone.querySelector('.circle-fill');
        setTimeout(() => {
            circleFill.setAttribute('stroke-dasharray', `${skor}, 100`);
            if (skor < 60 && skor >= 40) {
                circleFill.style.stroke = 'var(--status-low)';
            } else if (skor < 40) {
                circleFill.style.stroke = 'var(--status-high)';
            } else {
                circleFill.style.stroke = 'var(--accent-blue)';
            }
        }, 100);

        // Set Detail Parameter
        const paramGrid = clone.querySelector('.param-grid');
        if (item.details) {
            for (const [paramKey, paramData] of Object.entries(item.details)) {
                let statusClass = 'status-ok';
                if (paramData.status === 'Terlalu Rendah') statusClass = 'status-low';
                if (paramData.status === 'Terlalu Tinggi') statusClass = 'status-high';
                const labelName = paramKey.replace('_tanah', '').replace('_', ' ');
                const paramHTML = `
                    <div class="param-item">
                        <span class="p-name">${labelName}</span>
                        <div class="p-val">
                            <strong>${paramData.value}</strong>
                            <span class="p-status ${statusClass}">${paramData.status}</span>
                        </div>
                    </div>
                `;
                paramGrid.insertAdjacentHTML('beforeend', paramHTML);
            }
        } else {
            paramGrid.innerHTML = '<span style="color:var(--text-muted);font-size:0.8rem">Detail tidak tersedia</span>';
        }

        return clone;
    }

    function updateConnectionStatus(isConnected) {
        if (isConnected) {
            elConnDot.classList.remove('offline');
            elConnStatus.textContent = "Terhubung (Live)";
        } else {
            elConnDot.classList.add('offline');
            elConnStatus.textContent = "Koneksi Terputus";
        }
    }

    function updateTimestamp(isoString) {
        if (!isoString) return;
        const date = new Date(isoString);
        elLastUpdate.textContent = date.toLocaleString('id-ID');
    }

    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            let currentVal = progress * (end - start) + start;
            obj.innerHTML = currentVal.toFixed(1);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    fetchData();
    setInterval(fetchData, POLL_INTERVAL);
});
