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
    
    T_temp = float(data.get("T_temp", 25.0))
    S0_user = float(data.get("S0", 10.0))
    k_S_user = float(data.get("k_S", 0.05))
    k_F_user = float(data.get("k_F", 1.0))
    
    k0 = soil_params.get(soil, {"k0": 1.85})["k0"]
    
    Lx, Ly, Lz = 80, 80, 3.25
    dx = Lx / 40.0
    dt = 0.1
    t_vals = np.linspace(0, sim_time, int(sim_time / dt) + 1)
    
    # 2. Matematik Algoritm (Backend Logic)
    H_vals = []
    k_vals = []
    F_vals = []
    S_vals = []
    
    T0 = 20.0
    T_ratio = T_temp / T0
    F_max = 0.45
    t0_sat = sim_time / 4.0
    
    H_current = 3.0
    
    for t in t_vals:
        # Logistik to'yinish F(t)
        F_t = F_max / (1 + np.exp(-k_F_user * (t - t0_sat)))
        
        # Sho'rlanish darajasi S(t)
        S_t = S0_user * np.exp(-k_S_user * t)
        
        # Bosim nisbati (P/P0 ~ H/H0)
        P_ratio = H_current / 3.0
        
        # S nisbati S/S0
        S_ratio = S_t / S0_user if S0_user > 0 else 0.0
        
        # Dinamik filtratsiya koeffitsiyenti formulasi
        # k(x,y,z,t) = k0 * (1 + P/P0 - S/S0) * (T/T0) * (1 - F)
        k_dyn = k0 * (1.0 + P_ratio - S_ratio) * T_ratio * (1.0 - F_t)
        k_dyn = max(0.001, k_dyn) # Musbat ushlab turish
        
        # Suv sathi o'zgarishini modellashtirish
        c_calib = 0.1 # Realistik pasayish faktori
        net_effect = (Qs + Qin - Qb - 90.0) * 0.0001
        
        drop = c_calib * k_dyn * dt
        H_current = H_current - drop + net_effect
        H_current = max(0.0, min(H_current, 3.25))
        
        H_vals.append(H_current)
        k_vals.append(k_dyn)
        F_vals.append(F_t)
        S_vals.append(S_t)
    
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
        "k_vals": k_vals,
        "F_vals": F_vals,
        "S_vals": S_vals,
        "x": x.tolist(),
        "y": y.tolist(),
        "Z_surface": Z_surface.tolist()
    }
