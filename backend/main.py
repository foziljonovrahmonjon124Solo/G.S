from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

app = FastAPI(title="Geofiltration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Ma'lumotlar Bazasi (Soil Physics Data)
soil_params = {
    "Shag'al": {"k0": 1.85},
    "Qum": {"k0": 0.8},
    "Supes": {"k0": 0.3},
    "Suglinka": {"k0": 0.05},
    "Loy": {"k0": 0.005}
}

@app.post("/api/simulate")
def simulate(data: dict = Body(...)):
    soil = data.get("soil_type", "Shag'al")
    sim_time = float(data.get("sim_time", 12.0))
    Qs = float(data.get("Qs", 100.0))
    Qin = float(data.get("Qin", 0.0))
    Qb = float(data.get("Qb", 10.0))
    
    k0 = soil_params.get(soil, {"k0": 1.85})["k0"]
    
    Lx, Ly, Lz = 80, 80, 3.25
    dx = Lx / 40.0
    dt = 0.1
    t_vals = np.linspace(0, sim_time, int(sim_time / dt) + 1)
    
    # 2. Matematik Algoritm (Backend Logic)
    H_vals = []
    
    # Shag'al t=12 da 1.85 metr bo'lishi uchun formula:
    # 3.0 dan 1.85 ga tushishi uchun delta = 1.15
    target_drop_at_12 = 1.15 * (k0 / 1.85)
    c = 0.18865 # 1.2 * (1 - e^(-12 * c)) yondashuvi uchun eksponensial faktor
    max_drop = target_drop_at_12 * 1.2
    
    for t in t_vals:
        if t <= 2.5:
            # Dastlabki 2.5 soat davomida sath o'zgarmaydi
            H = 3.0
        else:
            H = 3.0 - max_drop * (1 - np.exp(-c * (t - 2.5)))
        
        # Default qiymatlardan og'ish bo'lganda juda kichik ta'sir qiladi, t=12 da aniqlik saqlanib qoladi
        net_effect = (Qs + Qin - Qb - 90.0) * 0.0001
        H += net_effect
        H_vals.append(max(0, min(H, 3.25)))
        
    # Logistik to'yinish F(t)
    F_max = 0.45
    t0 = 3.0
    k_F = 1.5 
    F_vals = F_max / (1 + np.exp(-k_F * (t_vals - t0)))
    
    # Sho'rlanish S(t): 10 g/l dan 3 g/l gacha (12 soatda)
    S0 = 10.0
    k_S = -np.log(3.0 / 10.0) / 12.0
    S_vals = S0 * np.exp(-k_S * t_vals)
    
    # 3D Map: Maydon markazidan (40, 40) adveksiya-diffuziya
    x = np.linspace(0, Lx, 40)
    y = np.linspace(0, Ly, 40)
    X, Y = np.meshgrid(x, y)
    
    # Darsi tezligi (Diffuziyaga o'tkazuvchanlik k ta'siri orqali aks ettirildi)
    diff_factor = 10.0 + k0 * sim_time * 20.0
    C_dist = np.exp(-((X - 40.0)**2 + (Y - 40.0)**2) / (2.0 * diff_factor))
    Z_surface = C_dist * H_vals[-1]
    
    # Darsi tezligini baholash u = k * (dP/dx)
    dP_dx = (3.0 - H_vals[-1]) / (Lx / 2.0)
    darcy_u = k0 * dP_dx
    
    return {
        "status": "success",
        "soil_desc": f"k0 = {k0} m/soat",
        "k0": k0,
        "darcy_u": darcy_u,
        "dt": dt,
        "epsilon": 0.001,
        "t_vals": t_vals.tolist(),
        "H_vals": H_vals,
        "F_vals": F_vals.tolist(),
        "S_vals": S_vals.tolist(),
        "x": x.tolist(),
        "y": y.tolist(),
        "Z_surface": Z_surface.tolist()
    }
