
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

st.set_page_config(page_title="Fantasy Edge", page_icon="🏈", layout="wide")

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

@st.cache_data
def load_demo():
    return pd.read_csv(DATA / "demo_players.csv")

def fp(row, ppr=1.0, pass_td=4.0):
    return (
        row.get("pass_yds", 0)/25
        + row.get("pass_td", 0)*pass_td
        - row.get("int", 0)*2
        + row.get("rush_yds", 0)/10
        + row.get("rush_td", 0)*6
        + row.get("rec_yds", 0)/10
        + row.get("rec_td", 0)*6
        + row.get("rec", 0)*ppr
        - row.get("fum_lost", 0)*2
    )

def add_scores(df):
    x = df.copy()
    # Opportunity / usage signals
    x["opp_score"] = (
        x["snap_share"] * 28
        + x["route_share"] * 24
        + x["target_share"] * 22
        + x["carry_share"] * 18
        + x["rz_share"] * 8
    )
    x["trend_score"] = (
        x["last3_usage_delta"] * 45
        + x["last3_fp_delta"] * 2.0
        + x["depth_chart_delta"] * 8
    )
    # Regression: positive = likely decline, negative = likely positive correction
    x["regression_score"] = (
        (x["td_rate_z"] * 24)
        + (x["yards_per_touch_z"] * 17)
        + (x["catch_rate_z"] * 10)
        - (x["opp_score"] - x["opp_score"].median()) * 0.45
    )
    # Progression: role growth + age/experience curve + opportunity
    age_bonus = np.select(
        [x["age"] <= 23, x["age"] <= 25, x["age"] <= 28, x["age"] <= 31],
        [15, 11, 6, 1],
        default=-6
    )
    x["progression_score"] = (
        x["trend_score"] * 0.60
        + (x["opp_score"] - x["opp_score"].median()) * 0.55
        + age_bonus
        + x["draft_capital_score"] * 0.22
    )
    x["breakout_probability"] = 1/(1+np.exp(-(x["progression_score"]-8)/17))
    x["decline_probability"] = 1/(1+np.exp(-(x["regression_score"]-8)/16))
    x["model_edge"] = (
        x["projected_ppg"] - x["market_ppg"]
        + x["progression_score"]*0.045
        - x["regression_score"]*0.04
    )
    x["waiver_score"] = (
        x["projected_ppg"] * 3.0
        + x["trend_score"] * 0.40
        + x["progression_score"] * 0.22
        - x["rostered_pct"] * 0.10
        + x["next3_matchup"] * 1.2
    )
    x["draft_score"] = (
        x["projected_ppg"] * 5
        + x["model_edge"] * 5
        + x["progression_score"] * 0.25
        - x["regression_score"] * 0.20
        - x["adp"] * 0.045
    )
    return x

def tier(v):
    if v >= 0.72: return "🔥 Strong"
    if v >= 0.58: return "⬆️ Positive"
    if v <= 0.32: return "🧊 Low"
    return "➡️ Neutral"

st.title("🏈 Fantasy Edge")
st.caption("Draft • Breakout/Regression • Weekly Trends • Waiver Wire")

with st.sidebar:
    st.header("League settings")
    scoring = st.selectbox("Scoring", ["PPR", "Half PPR", "Standard"], index=0)
    teams = st.slider("Teams", 8, 16, 12)
    replacement = st.selectbox("Waiver aggressiveness", ["Conservative", "Balanced", "Aggressive"], index=1)
    st.divider()
    st.header("Data")
    uploaded = st.file_uploader("Upload player CSV (optional)", type=["csv"])
    st.caption("The included demo lets the dashboard run immediately. Replace it with nflverse/Sleeper data when connected.")

df = pd.read_csv(uploaded) if uploaded else load_demo()
df = add_scores(df)

tabs = st.tabs(["Draft Board", "Breakout / Regression", "Waiver Wire", "Weekly Start/Sit", "Player Lab", "Model Notes"])

with tabs[0]:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Players", len(df))
    c2.metric("Best model edge", f"{df.model_edge.max():+.1f} PPG")
    c3.metric("Breakout candidates", int((df.breakout_probability >= .65).sum()))
    c4.metric("Regression flags", int((df.decline_probability >= .65).sum()))
    pos = st.multiselect("Position", sorted(df.position.unique()), default=sorted(df.position.unique()))
    board = df[df.position.isin(pos)].sort_values("draft_score", ascending=False).copy()
    board["Breakout"] = board.breakout_probability.map(lambda x: f"{x:.0%}")
    board["Decline Risk"] = board.decline_probability.map(lambda x: f"{x:.0%}")
    board["Edge"] = board.model_edge.map(lambda x: f"{x:+.1f}")
    st.dataframe(board[["player","position","team","adp","projected_ppg","market_ppg","Edge","Breakout","Decline Risk","draft_score"]],
                 use_container_width=True, hide_index=True)
    st.info("Draft idea: target positive model edge + strong progression; fade extreme efficiency when role/volume does not support it.")

with tabs[1]:
    left,right = st.columns(2)
    with left:
        st.subheader("🚀 Breakout / progression")
        b = df.sort_values("breakout_probability", ascending=False).head(15).copy()
        b["Probability"] = b.breakout_probability.map(lambda x: f"{x:.0%}")
        st.dataframe(b[["player","position","team","Probability","progression_score","trend_score","opp_score"]],
                     use_container_width=True, hide_index=True)
    with right:
        st.subheader("📉 Regression / decline")
        r = df.sort_values("decline_probability", ascending=False).head(15).copy()
        r["Probability"] = r.decline_probability.map(lambda x: f"{x:.0%}")
        st.dataframe(r[["player","position","team","Probability","regression_score","td_rate_z","yards_per_touch_z"]],
                     use_container_width=True, hide_index=True)

with tabs[2]:
    max_rostered = st.slider("Only show players rostered ≤", 5, 95, 65, format="%d%%")
    waiver = df[df.rostered_pct <= max_rostered].sort_values("waiver_score", ascending=False).copy()
    budget_mult = {"Conservative":0.65,"Balanced":1.0,"Aggressive":1.35}[replacement]
    waiver["FAAB %"] = np.clip(
        (waiver.waiver_score - waiver.waiver_score.quantile(.35))*0.75*budget_mult, 1, 45
    ).round().astype(int)
    waiver["Trend"] = waiver.breakout_probability.map(tier)
    st.dataframe(waiver[["player","position","team","rostered_pct","projected_ppg","last3_fp_delta",
                         "next3_matchup","Trend","FAAB %","waiver_score"]],
                 use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Weekly start/sit")
    st.caption("Weekly score emphasizes recent usage, recent fantasy production, matchup and baseline projection.")
    w = df.copy()
    w["weekly_score"] = (
        w.projected_ppg*3.3 + w.last3_fp_delta*2.2 + w.last3_usage_delta*18 +
        w.next3_matchup*1.4 - w.regression_score*0.09
    )
    positions = st.multiselect("Positions", ["QB","RB","WR","TE"], default=["RB","WR","TE"], key="weekly_positions")
    w = w[w.position.isin(positions)].sort_values("weekly_score", ascending=False)
    st.dataframe(w[["player","position","team","projected_ppg","last3_fp_delta","last3_usage_delta",
                    "next3_matchup","weekly_score"]], use_container_width=True, hide_index=True)

with tabs[4]:
    name = st.selectbox("Player", sorted(df.player.unique()))
    p = df[df.player == name].iloc[0]
    a,b,c,d = st.columns(4)
    a.metric("Projection", f"{p.projected_ppg:.1f} PPG")
    b.metric("vs Market", f"{p.model_edge:+.1f}")
    c.metric("Breakout", f"{p.breakout_probability:.0%}")
    d.metric("Decline risk", f"{p.decline_probability:.0%}")
    st.write({
        "Opportunity score": round(float(p.opp_score),1),
        "Trend score": round(float(p.trend_score),1),
        "Progression score": round(float(p.progression_score),1),
        "Regression score": round(float(p.regression_score),1),
        "Next 3 matchup": round(float(p.next3_matchup),1),
        "ADP": round(float(p.adp),1),
    })
    if p.model_edge > 1.5 and p.breakout_probability > .60:
        st.success("MODEL CALL: BUY / TARGET")
    elif p.decline_probability > .65 and p.model_edge < 0:
        st.error("MODEL CALL: FADE / SELL HIGH")
    else:
        st.warning("MODEL CALL: HOLD / PRICE DEPENDENT")

with tabs[5]:
    st.markdown("""
### What the scores mean

**Progression model**
Rewards expanding snaps, routes, targets/carries, red-zone work, depth-chart movement,
recent fantasy improvement, youth/experience curve, and draft capital.

**Regression model**
Flags unsustainably high touchdown rates or efficiency when opportunity does not support
the production. Negative regression scores can identify players producing *below* their
underlying role.

**Weekly model**
Moves away from preseason priors as the season progresses and emphasizes recent volume,
recent efficiency, role changes, and upcoming matchup.

### Production version
For a real league, connect:
1. **nflverse / nflreadpy** — historical weekly stats, play-by-play, rosters and advanced inputs.
2. **Sleeper API** — league settings, rosters, draft picks and ownership.
3. Optional injury/news and betting-market inputs.
4. Retrain models each week using only information that was available before that week
   to avoid data leakage.
""")
