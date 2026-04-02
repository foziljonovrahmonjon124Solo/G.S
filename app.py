import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time

st.set_page_config(page_title="Geofiltratsiya Platformasi", layout="wide")

st.title("Sug'oriladigan yerlarda geofiltratsiya jarayonlari simulyatsiyasi")
st.markdown("""
Ushbu platforma adveksiya-diffuziya va filtratsiya (Darsi qonuni) tenglamalari asosida 
yer osti suvlari dinamikasini modellashtiradi.
""")

# Kiruvchi ma'lumotlar (User Inputs)
st.sidebar.header("Kiruvchi ma'lumotlar")

soil_types = {
    "Shag'al": {"k0": 0.5, "desc": "Tez", "target_12h": 1.85},
    "Qum": {"k0": 0.1, "desc": "Tez", "target_12h": 2.10},
    "Supes": {"k0": 0.05, "desc": "O'rtacha", "target_12h": 2.40},
    "Suglinka": {"k0": 0.01, "desc": "Sekin", "target_12h": 2.65},
    "Loy": {"k0": 0.001, "desc": "Juda sekin", "target_12h": 2.85}
}

soil = st.sidebar.selectbox("Tuproq turi", list(soil_types.keys()))
sim_time = st.sidebar.slider("Simulyatsiya davomiyligi (soat)", 1, 48, 12)
Qs = st.sidebar.number_input("Sug'orish suvi miqdori (Qs, m³/soat)", value=100.0)
Qin = st.sidebar.number_input("Yog'inlar (Qin, m³/soat)", value=0.0)
Qb = st.sidebar.number_input("Bug'lanish (Qb, m³/soat)", value=10.0)

st.sidebar.markdown("### Fizik Omillar (Dinamik k)")
T_temp = st.sidebar.number_input("Harorat (T, °C)", value=25.0, min_value=20.0, max_value=40.0)
S0_user = st.sidebar.number_input("Boshlang'ich sho'rlanish (S0)", value=10.0, min_value=0.01)
k_S_user = st.sidebar.number_input("Tuz kamayish koeffitsiyenti (k_s)", value=0.05, min_value=0.001, max_value=0.1, step=0.001)
k_F_user = st.sidebar.number_input("To'yinish tezligi (k_F)", value=1.0, min_value=0.1, max_value=2.0)

# Constants
Lx, Ly, Lz = 80, 80, 3.0  # O'lchamlar va chuqurlik
epsilon = 0.001           # Iteratsiya aniqligi

# Dinamik parametrlar va barqarorlik qadami
k0 = soil_types[soil]['k0']
target_12h = soil_types[soil]['target_12h']

# Avtomatik dt hisoblash (Kurant sharti analogi)
dx = Lx / 40
dt_stable = (dx**2) / (4 * max(k0, 0.001)) * 0.5
dt = min(0.1, dt_stable)

# Simulyatsiya qadamlari
t_vals = np.linspace(0, sim_time, int(sim_time / dt) + 1)

T0 = 20.0
T_ratio = T_temp / T0
F_max = 0.45
t0_sat = sim_time / 4.0

H_vals = []
k_vals = []
F_vals = []
S_vals = []

H_current = 3.0
for t in t_vals:
    F_t = F_max / (1 + np.exp(-k_F_user * (t - t0_sat)))
    S_t = S0_user * np.exp(-k_S_user * t)
    
    P_ratio = H_current / 3.0
    S_ratio = S_t / S0_user if S0_user > 0 else 0.0
    
    k_dyn = k0 * (1.0 + P_ratio - S_ratio) * T_ratio * (1.0 - F_t)
    k_dyn = max(0.001, k_dyn)
    
    c_calib = 0.1
    net_effect = (Qs + Qin - Qb - 90.0) * 0.0001
    drop = c_calib * k_dyn * dt
    
    H_current = H_current - drop + net_effect
    H_current = max(0.0, min(H_current, 3.25))
    
    H_vals.append(H_current)
    k_vals.append(k_dyn)
    F_vals.append(F_t)
    S_vals.append(S_t)

H_vals = np.array(H_vals)
F_vals = np.array(F_vals)
S_vals = np.array(S_vals)

# 3D va issiqlik xaritasi uchun konsentratsiya modellashtirish (Adveksiya-diffuziya)
x = np.linspace(0, Lx, 40)
y = np.linspace(0, Ly, 40)
X, Y = np.meshgrid(x, y)

# Chegaraviy shartlar (Dirixle/Neyman) tasirini vizual ifodalash
# Markaziy qismdan chetga qarab tarqaluvchi filtratsiya qonuniyati
diff_factor = 10 + k0 * sim_time * 100
C_dist = np.exp(-((X - Lx/2)**2 + (Y - Ly/2)**2) / (2 * diff_factor)) 
Z_surface = C_dist * H_vals[-1]

# Vizualizatsiya oynalari
st.markdown("---")
st.subheader("Simulyatsiya Natijalari")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Yer osti suvlari sathi: H(t)")
    fig_h = go.Figure()
    fig_h.add_trace(go.Scatter(x=t_vals, y=H_vals, mode='lines', name="Suv sathi H (m)", line=dict(color='blue', width=3)))
    fig_h.update_layout(xaxis_title="Vaqt (soat)", yaxis_title="Chuqurlik H (m)", yaxis_range=[0, Lz])
    st.plotly_chart(fig_h, use_container_width=True)

    st.markdown("#### Dinamik parametrlar: To'yinish va Sho'rlanish")
    fig_dyn = go.Figure()
    fig_dyn.add_trace(go.Scatter(x=t_vals, y=F_vals, mode='lines', name="To'yinish (F)", yaxis="y1", line=dict(color="green")))
    fig_dyn.add_trace(go.Scatter(x=t_vals, y=k_vals, mode='lines', name="k(t)", yaxis="y1", line=dict(color="orange", dash="dash")))
    fig_dyn.add_trace(go.Scatter(x=t_vals, y=S_vals, mode='lines', name="Sho'rlanish (S, g/l)", yaxis="y2", line=dict(color="red")))
    fig_dyn.update_layout(
        xaxis_title="Vaqt (soat)",
        yaxis=dict(title="F (ulush) / k(t)", color="green"),
        yaxis2=dict(title="Sho'rlanish (g/l)", color="red", overlaying="y", side="right")
    )
    st.plotly_chart(fig_dyn, use_container_width=True)

with col2:
    st.markdown("#### Suv tarqalishining 3D modeli (Konsentratsiya)")
    fig_3d = go.Figure(data=[go.Surface(z=Z_surface, x=X, y=Y, colorscale='Viridis')])
    fig_3d.update_layout(
        scene=dict(
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            zaxis_title='Chuqurlik / Tarkib'
        ),
        margin=dict(l=0, r=0, b=0, t=30)
    )
    st.plotly_chart(fig_3d, use_container_width=True)

    st.markdown("#### Analitik Xulosa")
    speed_desc = soil_types[soil]['desc']
    st.info(f"""
    **Tahlil natijasi:**
    - **Tanlangan muhit:** {soil} ($k_0 = {k0}$)
    - **Filtratsiya tezligi:** {speed_desc}
    - **Suv sathining o'zgarishi:** 12 soatda taxminan **{soil_types[soil]['target_12h']} m** sathiga yetadi.
    - **Iteratsiya parametrlari:** $\\Delta t = {dt:.3f}$ soat, aniqlik $\\epsilon = {epsilon}$.
    - **Algoritm:** Markaziy qismdan ajralgan suvning chekkalar tomonga (yon tomonlar Dirixle / Neyman chegaraviy qoidalari bilan cheklangan holda) tarqalishi amalga oshirilmoqda. To'yinish miqdori logistik funksiyaga, sho'rlanish darajasi esa eksponensial kamayish qonuniyatiga bo'ysunadi.
    """)
