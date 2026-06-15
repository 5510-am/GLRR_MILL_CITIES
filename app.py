import streamlit as st
import pandas as pd
import random
from optimizer import optimize_with_constraints

st.set_page_config(layout="wide")
st.title("🏃 GLRR Mill Cities Relay Optimizer")

# -----------------------------
# COURSE PROFILES
# -----------------------------
legs = {
    "Leg1": {"dist": 5.0, "elev": 120, "difficulty": 1.00},
    "Leg2": {"dist": 4.8, "elev": 180, "difficulty": 1.05},
    "Leg3": {"dist": 5.5, "elev": 260, "difficulty": 1.15},
    "Leg4": {"dist": 3.9, "elev": 90,  "difficulty": 0.95},
    "Leg5": {"dist": 5.7, "elev": 220, "difficulty": 1.10}
}

# -----------------------------
# CATEGORIES (5-person only)
# -----------------------------
categories = {
    "CO": {"min_age": 18, "min_female": 2},
    "FO": {"min_age": 18, "min_female": 5},
    "MO": {"min_age": 18, "min_female": 0},
    "CM": {"min_age": 40, "min_female": 2},
}

# -----------------------------
# HELPERS
# -----------------------------
def elevation_adjustment(elev_gain):
    return (elev_gain * 0.3) / 60

def calculate_leg_times(df):
    for leg, d in legs.items():
        df[leg+"_time"] = df["pace"] * d["dist"] * d["difficulty"] + elevation_adjustment(d["elev"])
    return df

def assign_team_tiers(df):
    tt = df.groupby("team")["leg_time"].sum().reset_index().sort_values("leg_time")
    n = len(tt)
    tt["tier"] = ["A" if i < n/3 else "B" if i < 2*n/3 else "C" for i in range(n)]
    return df.merge(tt, on="team")

def assign_team_names(df):
    out = []
    for cat in df["category"].unique():
        for tier in ["A","B","C"]:
            teams = sorted(df[(df["category"]==cat)&(df["tier"]==tier)]["team"].unique())
            for i,t in enumerate(teams,1):
                out.append({"category":cat,"team":t,"team_name":f"{cat}-{tier}{i}"})
    return df.merge(pd.DataFrame(out), on=["category","team"])

def generate_email(df):
    text=""
    for cat in df["category"].unique():
        text+=f"\n==== {cat} ====\n"
        for tier in ["A","B","C"]:
            grp=df[(df["category"]==cat)&(df["tier"]==tier)]
            if len(grp)==0: continue
            text+=f"\n-- {tier} Teams --\n"
            for name,g in grp.groupby("team_name"):
                t=round(g["leg_time"].sum(),1)
                text+=f"\n{name} ({t} min)\n"
                for _,r in g.iterrows():
                    text+=f"{r['leg']}: {r['name']}\n"
    return text

# -----------------------------
# INPUT
# -----------------------------
file = st.file_uploader("Upload CSV (name, pace, age, gender)")

if not file:
    st.stop()

df = pd.read_csv(file)
df["gender"] = df["gender"].str.upper()

selected_categories = st.sidebar.multiselect(
    "Categories", list(categories.keys()), ["CO"]
)

all_results=[]
used=set()

for cat_code in selected_categories:

    st.header(f"🏁 {cat_code}")
    cat=categories[cat_code]

    eligible=df[(df["age"]>=cat["min_age"])].drop(index=list(used),errors="ignore")
    eligible["is_female"]=eligible["gender"]=="F"

    if len(eligible)<5:
        st.warning("Not enough runners")
        continue

    min_female=cat["min_female"]

    max_teams=min(len(eligible)//5, 
        (eligible["is_female"].sum()//min_female if min_female else len(eligible)//5))

    if max_teams==0:
        st.warning("No valid teams possible")
        continue

    num_teams=st.slider(f"{cat_code} Teams",1,max_teams,max_teams,key=cat_code)

    req_total=num_teams*5
    req_f=num_teams*min_female

    eligible=eligible.sort_values("pace")

    sel_f=eligible[eligible["is_female"]].head(req_f)
    rem=eligible.drop(sel_f.index)
    sel_o=rem.head(req_total-req_f)

    selected=pd.concat([sel_f,sel_o])
    used.update(selected.index)

    selected=calculate_leg_times(selected)

    res=optimize_with_constraints(selected,legs,num_teams,min_female)
    res["category"]=cat_code
    all_results.append(res)

# -----------------------------
# OUTPUT
# -----------------------------
if len(all_results)>0:

    final_df=pd.concat(all_results)

    final_df=assign_team_tiers(final_df)
    final_df=assign_team_names(final_df)

    # DISPLAY
    for tier in ["A","B","C"]:
        st.header(f"🏅 {tier} Teams")
        for name,g in final_df[final_df["tier"]==tier].groupby("team_name"):
            st.subheader(name)
            for _,r in g.iterrows():
                st.write(f"{r['leg']} → {r['name']}")

    # EDITOR
    st.header("✏️ Adjust")
    edited=st.data_editor(final_df, use_container_width=True)

    # SWAP
    st.subheader("Swap")
    r1=st.selectbox("Runner 1", edited["name"])
    r2=st.selectbox("Runner 2", edited["name"], key="swap")

    if st.button("Swap"):
        df2=edited.copy()
        i1=df2[df2["name"]==r1].index[0]
        i2=df2[df2["name"]==r2].index[0]
        tmp=df2.loc[i1,["team","leg"]]
        df2.loc[i1,["team","leg"]]=df2.loc[i2,["team","leg"]]
        df2.loc[i2,["team","leg"]]=tmp
        final_df=df2

    # EMAIL
    st.header("📧 Email Export")
    email=generate_email(final_df)
    st.text_area("Copy",email,height=300)
