import streamlit as st
import pandas as pd
import numpy as np
import random
from optimizer import optimize_with_constraints

st.set_page_config(layout="wide")

st.title("🏃 GLRR Mill Cities Relay Optimizer")

# -----------------------------
# CONFIG
# -----------------------------
legs = {
    "Leg1": 5.0,
    "Leg2": 4.8,
    "Leg3": 5.5,
    "Leg4": 3.9,
    "Leg5": 5.7
}

team_names = [
    "Negative Splitters",
    "Miles & Smiles",
    "Pace Cadets",
    "Relay Rebels",
    "Draft Dodgers"
]

# -----------------------------
# LOAD DATA (CSV UPLOAD)
# -----------------------------
uploaded_file = st.file_uploader("Upload runner CSV (name,pace)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
else:
    st.stop()

# -----------------------------
# PREP DATA
# -----------------------------
for leg, dist in legs.items():
    df[leg+"_time"] = df["pace"] * dist

num_teams = st.sidebar.slider("Number of Teams", 1, max(1,len(df)//5), len(df)//5)

# -----------------------------
# OPTIMIZE BUTTON
# -----------------------------
if "results" not in st.session_state:
    st.session_state.results = None

if st.button("⚖️ Optimize Teams"):
    results = optimize_with_constraints(df, legs, num_teams, [])
    st.session_state.results = results

# -----------------------------
# DISPLAY RESULTS
# -----------------------------
if st.session_state.results is not None:

    results = st.session_state.results

    st.header("📊 Team Assignments")

    for t in results["team"].unique():
        team_df = results[results["team"] == t]

        st.markdown(f"### 🟦 {random.choice(team_names)} (Team {t})")

        total = team_df["leg_time"].sum()
        st.caption(f"Total Time: {round(total,1)} min")

        for _, r in team_df.iterrows():
            st.write(f"{r['leg']} → {r['name']} ({round(r['leg_time'],1)} min)")

    # -----------------------------
    # EDIT MODE
    # -----------------------------
    st.header("✏️ Edit Assignments")

    edited = st.data_editor(results, use_container_width=True)

    # Swap tool
    st.subheader("🔁 Quick Swap")

    r1 = st.selectbox("Runner 1", edited["name"])
    r2 = st.selectbox("Runner 2", edited["name"], key="r2")

    if st.button("Swap Runners"):
        i1 = edited[edited["name"] == r1].index[0]
        i2 = edited[edited["name"] == r2].index[0]

        edited.loc[i1, ["team","leg"]] = edited.loc[i2, ["team","leg"]]
        edited.loc[i2, ["team","leg"]] = edited.loc[i1, ["team","leg"]]

        st.session_state.results = edited

    # -----------------------------
    # TEAM BALANCE
    # -----------------------------
    st.header("📊 Team Balance")

    team_times = edited.groupby("team")["leg_time"].sum()

    st.bar_chart(team_times)

    spread = team_times.max() - team_times.min()
    st.metric("Time Spread", f"{round(spread,1)} min")

    # -----------------------------
    # EMAIL EXPORT
    # -----------------------------
    def format_email(df):
        txt = ""
        for t in df["team"].unique():
            txt += f"\nTeam {t}\n"
            for _, r in df[df["team"]==t].iterrows():
                txt += f"{r['leg']}: {r['name']}\n"
        return txt

    st.text_area("📧 Copy for Email", format_email(edited))

    # -----------------------------
    # DOWNLOAD
    # -----------------------------
    csv = edited.to_csv(index=False).encode()
    st.download_button("Download CSV", csv, "relay_teams.csv")

# -----------------------------
# EXPLAINABILITY
# -----------------------------
with st.expander("🧠 How Teams Are Built"):
    st.write("""
    - Teams are balanced using mathematical optimization  
    - Total team times are minimized for fairness  
    - Each team has one runner per leg  
    - Manual edits override optimization  
    """)