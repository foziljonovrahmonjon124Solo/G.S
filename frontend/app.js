let gpsData = null;

document.addEventListener('DOMContentLoaded', () => {
    if ('Notification' in window && navigator.serviceWorker) {
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }
    
    // GPS Button handler
    const gpsBtn = document.getElementById('getGpsBtn');
    if (gpsBtn) {
        gpsBtn.addEventListener('click', () => {
            if (navigator.geolocation) {
                document.getElementById('gpsStatus').innerText = "📡 Qidirilmoqda...";
                navigator.geolocation.getCurrentPosition(pos => {
                    gpsData = { lat: pos.coords.latitude, lon: pos.coords.longitude };
                    document.getElementById('gpsStatus').innerText = `📍 O'zlashtirildi: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`;
                }, err => {
                    document.getElementById('gpsStatus').innerText = "❌ GPS ruxsati berilmadi yoki xato";
                });
            } else {
                document.getElementById('gpsStatus').innerText = "🚫 Brauzerda GPS mavjud emas";
            }
        });
    }
});

document.getElementById('simForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.querySelector('.primary-btn');
    btn.textContent = "Hisoblanmoqda...";
    btn.disabled = true;

        const payload = {
        soil_type: document.getElementById('soil_type').value,
        sim_time: parseFloat(document.getElementById('sim_time').value),
        Qs: parseFloat(document.getElementById('Qs').value),
        Qin: parseFloat(document.getElementById('Qin').value),
        Qb: parseFloat(document.getElementById('Qb').value),
        T_temp: parseFloat(document.getElementById('T_temp').value),
        S0: parseFloat(document.getElementById('S0').value),
        k_S: parseFloat(document.getElementById('k_S').value),
        k_F: parseFloat(document.getElementById('k_F').value),
        gps: gpsData,
        has_image: document.getElementById('cameraInput').files.length > 0
    };

    try {
        const response = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if(!response.ok) throw new Error("Server xatosi: " + response.statusText);
        
        const data = await response.json();
        if(data.status === 'success') {
            renderCharts(data);
            showAnalytics(data, payload);
            checkAndPushNotifications(data);
        }
    } catch(err) {
        console.error(err);
        alert("Backend API bilan ulanishda xatolik yuz berdi (8000-portda FastAPI ishga tushirilganligini tekshiring).\\nTafsilot: " + err.message);
    } finally {
        btn.textContent = "Simulyatsiyani Boshlash";
        btn.disabled = false;
    }
});

function renderCharts(data) {
    const layoutConfig = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: "'Inter', sans-serif" },
        margin: { t: 50, r: 20, l: 60, b: 50 },
        showlegend: true,
        legend: { font: { color: '#cbd5e1' } }
    };

    // 1. Pressure P(t) Chart (Previously H(t))
    const pTrace = {
        x: data.t_vals,
        y: data.P_vals,
        mode: 'lines',
        name: 'Gidro-Bosim P(t)',
        line: { color: '#3b82f6', width: 3, shape: 'spline' },
        fill: 'tozeroy',
        fillcolor: 'rgba(59, 130, 246, 0.1)'
    };
    
    Plotly.newPlot('chart_h', [pTrace], {
        ...layoutConfig,
        title: { text: "Darsi Gidro-Bosim dinamikasi: P(t) kPa", font: { color: '#f8fafc', size: 16 } },
        xaxis: { title: 'Vaqt (soat)', gridcolor: 'rgba(255,255,255,0.05)', zerolinecolor: 'rgba(255,255,255,0.1)' },
        yaxis: { title: 'Bosim P (kPa)', gridcolor: 'rgba(255,255,255,0.05)', zerolinecolor: 'rgba(255,255,255,0.1)' }
    }, { responsive: true });

    // 2. Dynamics Chart (Saturation and Salinity)
    const fTrace = {
        x: data.t_vals,
        y: data.F_vals,
        mode: 'lines',
        name: "To'yinish (F)",
        line: { color: '#10b981', width: 3, shape: 'spline' }
    };
    const sTrace = {
        x: data.t_vals,
        y: data.S_vals,
        mode: 'lines',
        name: "Sho'rlanish (S)",
        yaxis: 'y2',
        line: { color: '#ef4444', width: 3, shape: 'spline' }
    };
    
    const kTrace = {
        x: data.t_vals,
        y: data.k_vals,
        mode: 'lines',
        name: "k(t)",
        line: { color: '#eab308', width: 2, shape: 'spline', dash: 'dash' }
    };
    
    Plotly.newPlot('chart_dyn', [fTrace, kTrace, sTrace], {
        ...layoutConfig,
        title: { text: 'Dinamik Parametrlar', font: { color: '#f8fafc', size: 18 } },
        xaxis: { title: 'Vaqt (soat)', gridcolor: 'rgba(255,255,255,0.05)', zerolinecolor: 'rgba(255,255,255,0.1)' },
        yaxis: { title: "To'yinish", gridcolor: 'rgba(255,255,255,0.05)', zerolinecolor: 'rgba(255,255,255,0.1)' },
        yaxis2: {
            title: "Sho'rlanish (g/l)",
            overlaying: 'y',
            side: 'right',
            gridcolor: 'rgba(255,255,255,0.05)',
            zerolinecolor: 'rgba(255,255,255,0.1)'
        }
    }, { responsive: true });

    // 3. 3D Concentration Surface Chart
    const surfaceTrace = {
        z: data.Z_surface,
        x: data.x,
        y: data.y,
        type: 'surface',
        colorscale: 'Portland',
        showscale: false
    };
    
    Plotly.newPlot('chart_3d', [surfaceTrace], {
        ...layoutConfig,
        title: { text: "3D Tarqalish Xaritasi (Adveksiya-Diffuziya)", font: { color: '#f8fafc', size: 18 } },
        margin: { t: 50, r: 0, l: 0, b: 0 },
        scene: {
            xaxis: { title: 'X (m)', backgroundcolor: 'rgba(0,0,0,0)', gridcolor: 'rgba(255,255,255,0.1)' },
            yaxis: { title: 'Y (m)', backgroundcolor: 'rgba(0,0,0,0)', gridcolor: 'rgba(255,255,255,0.1)' },
            zaxis: { title: 'Sath (m)', backgroundcolor: 'rgba(0,0,0,0)', gridcolor: 'rgba(255,255,255,0.1)' },
            camera: { eye: {x: 1.5, y: 1.5, z: 1.2} }
        }
    }, { responsive: true });
}

function showAnalytics(data, payload) {
    const card = document.getElementById('analytics');
    const text = document.getElementById('analysis-text');
    card.style.display = 'block';
    
    // Formatting with nice typography
    text.innerHTML = `
        <strong>Tanlangan Muhit:</strong> <span style="color:var(--text-primary)">${data.detected_soil || payload.soil_type} ${data.ai_confidence ? '(AI Orqali topildi, ishontirish: ' + Math.round(data.ai_confidence*100) + '%)' : ''}</span><br>
        <strong>Dastlabki (k0):</strong> <span style="color:var(--text-primary)">${data.k0} m/soat</span> | 
        <strong>Joriy Dinamik k:</strong> <span style="color:var(--text-primary)">${data.k_vals[data.k_vals.length-1].toFixed(2)} m/soat</span><br>
        <strong>Harorat Ta'siri:</strong> <span style="color:var(--text-primary)">T=${payload.T_temp}°C (Darsi modeli bo'yicha)</span><br>
        <strong>Eng Zich Konsentratsiya (C):</strong> <span style="color:var(--text-primary)">${Math.max(...data.Z_surface.flat()).toFixed(3)} (Konveksiya-Diffuziya)</span><br><br>
        <em>P(t) bosimi va parametrlar (P, S, T, F) dinamik omiliga ko'ra hisoblangan <strong>k(t)</strong> yordamida ilmiy arxitektura chizildi.</em>
    `;
}

function checkAndPushNotifications(data) {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;

    function sendPush(title, body) {
        navigator.serviceWorker.ready.then(reg => {
            reg.showNotification(title, {
                body: body,
                icon: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzNiODJmNiI+PHBhdGggZD0iTTEyIDMuMThMMiAuNzY0djIwLjQ3MkwxMiAyNEwyMiAyMS4yMzZWMS43NjVMMTIgMy4xOHoiLz48L3N2Zz4=',
                badge: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzNiODJmNiI+PHBhdGggZD0iTTEyIDMuMThMMiAuNzY0djIwLjQ3MkwxMiAyNEwyMiAyMS4yMzZWMS43NjVMMTIgMy4xOHoiLz48L3N2Zz4=',
                vibrate: [200, 100, 200]
            });
        });
    }

    const minH = Math.min(...data.H_vals);
    const maxF = Math.max(...data.F_vals);
    const dropAmount = 3.0 - minH;

    // Condition 1: Infiltration reaches groundwater
    if (dropAmount > 0.05) {
        sendPush("💧 Infiltratsiya Oqimi", "Infiltratsiya oqimi yer osti suvlariga yetib bordi! Sub-sath tezligi o'zgardi.");
    }
    
    // Condition 2: Critical depth
    if (minH <= 1.85) {
        setTimeout(() => sendPush("⚠️ Kritik Suv Sathi", `Diqqat: Suv sathi kritik chuqurlikka (1.85 m dan past) ekanligi qayd etildi (${minH.toFixed(2)} m).`), 1500);
    }
    
    // Condition 3: Max Saturation
    if (maxF >= 0.40) {
        setTimeout(() => sendPush("🚨 Maksimal To'yinish", `Tuproq to'yinish darajasi deyarli maksimal qiymatida (F = ${maxF.toFixed(2)}). Gapingiz zudlik bilan kerak!`), 3000);
    }
}
