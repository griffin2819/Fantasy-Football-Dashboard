import streamlit as st
import pandas as pd
import numpy as np
import requests, re, unicodedata, json, time
import concurrent.futures
from pathlib import Path

st.set_page_config(page_title="Fantasy Edge V6.8 — Tested Regret Winner", page_icon="🏈", layout="wide")
STATE = Path("fantasy_edge_state.json")

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b","",s)
    return re.sub(r"[^a-z0-9]","",s)

def load_state():
    default={
        "teams":12,"ppr":1.0,"pass_td":4,"faab":100,
        "my_team":[],"taken":[],"injury_overrides":{},
        "roster_slots":{"QB":1,"RB":2,"WR":2,"TE":1,"FLEX":2,"K":1,"DL":1,"DB":1,"BENCH":6},
        "mock":{"draft_slot":1,"rounds":17,"randomness":12},
        "idp":{"solo":1.5,"assist":0.75,"sack":4.0,"tfl":2.0,"qb_hit":0.0,
               "int":7.0,"pd":2.0,"ff":4.0,"fr":4.0,"def_td":12.0,"safety":8.0}
    }
    if STATE.exists():
        try:
            saved=json.loads(STATE.read_text())
            default.update({k:v for k,v in saved.items() if k not in ["idp","roster_slots","mock"]})
            default["idp"].update(saved.get("idp",{}))
            default["roster_slots"].update(saved.get("roster_slots",{}))
            default["mock"].update(saved.get("mock",{}))
        except: pass
    return default

def exact_roster_rounds(slots):
    """Total draft rounds implied by the exact roster template."""
    return int(sum(max(int(slots.get(p,0)),0) for p in ["QB","RB","WR","TE","FLEX","K","DL","DB","BENCH"]))

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

@st.cache_data(ttl=86400)
def sleeper_players():
    # Used only as a live NFL player directory, not as the fantasy-league source.
    r=requests.get("https://api.sleeper.app/v1/players/nfl",timeout=6)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=86400, show_spinner="Updating NFL statistics...")
def nfl_history():
    try:
        import nflreadpy as nfl
        raw=nfl.load_player_stats([2023,2024,2025]).to_pandas()
        if "season_type" in raw:
            raw=raw[raw.season_type.eq("REG")]

        name="player_display_name" if "player_display_name" in raw else "player_name"
        if "position" not in raw:
            return pd.DataFrame()

        # Keep offensive + defensive positions.
        allowed=["QB","RB","WR","TE","DL","DE","DT","NT","EDGE","DB","CB","S","FS","SS"]
        raw=raw[raw.position.isin(allowed)].copy()
        raw["_g"]=1

        # Ensure all needed columns exist.
        offensive_cols=["passing_yards","passing_tds","interceptions","rushing_yards","rushing_tds",
                        "receptions","receiving_yards","receiving_tds","targets","carries"]
        defensive_cols=["def_tackles_solo","def_tackles_with_assist","def_sacks","def_tackles_for_loss",
                        "def_qb_hits","def_interceptions","def_pass_defended","def_fumbles_forced",
                        "def_fumble_recovery_opp","def_tds","def_safety"]
        for c in offensive_cols+defensive_cols:
            if c not in raw: raw[c]=0

        raw["fantasy_points_ppr"]=(
            raw.passing_yards.fillna(0)/25 + raw.passing_tds.fillna(0)*4
            - raw.interceptions.fillna(0)*2 + raw.rushing_yards.fillna(0)/10
            + raw.rushing_tds.fillna(0)*6 + raw.receptions.fillna(0)
            + raw.receiving_yards.fillna(0)/10 + raw.receiving_tds.fillna(0)*6
        )

        agg={"fantasy_points_ppr":"sum","_g":"sum"}
        for c in offensive_cols+defensive_cols:
            agg[c]="sum"

        x=raw.groupby(["season",name,"position"],dropna=False).agg(agg).reset_index().rename(columns={name:"player"})
        x["games"]=x["_g"].clip(lower=1)
        if x.games.median()<=2: x["games"]=17
        x["ppr_ppg"]=x.fantasy_points_ppr/x.games
        x["key"]=x.player.map(norm)
        x["position_group"]=x["position"].map(position_group)
        return x
    except Exception as e:
        st.session_state["hist_error"]=str(e)
        return pd.DataFrame()

@st.cache_data(ttl=21600, show_spinner="Updating 2026 consensus rankings...")
def market_rankings(ppr):
    """Latest FantasyPros expert-consensus rankings via nflverse/DynastyProcess."""
    try:
        import nflreadpy as nfl
        try:
            raw = nfl.load_ff_rankings("draft").to_pandas()
        except TypeError:
            raw = nfl.load_ff_rankings().to_pandas()
        if raw.empty or "player" not in raw.columns or "ecr" not in raw.columns:
            return pd.DataFrame()
        raw = raw.copy()
        raw["ecr"] = pd.to_numeric(raw["ecr"], errors="coerce")
        raw = raw[raw.ecr.notna()]
        raw["key"] = raw.player.map(norm)
        raw["page"] = raw.get("page_type", pd.Series("", index=raw.index)).fillna("").astype(str).str.lower()
        raw["etype"] = raw.get("ecr_type", pd.Series("", index=raw.index)).fillna("").astype(str).str.lower()
        raw["pos_raw"] = raw.get("pos", pd.Series("", index=raw.index)).fillna("").astype(str)

        # Prefer overall redraft pages matching league reception scoring.
        score = pd.Series(0.0, index=raw.index)
        score += raw.page.str.contains("overall", regex=False).astype(float) * 5
        score += (~raw.page.str.contains("dynasty", regex=False)).astype(float) * 2
        score += (~raw.page.str.contains("week", regex=False)).astype(float) * 2
        if ppr == 1.0:
            score += (raw.page.str.contains("ppr", regex=False) & ~raw.page.str.contains("half", regex=False)).astype(float) * 5
        elif ppr == 0.5:
            score += (raw.page.str.contains("half", regex=False)).astype(float) * 5
        else:
            score += (~raw.page.str.contains("ppr", regex=False)).astype(float) * 3
        # IDP pages are useful for defenders, but not for offensive overall rank.
        is_idp_page = raw.page.str.contains("idp", regex=False)
        raw["page_score"] = score

        raw["consensus_pos"]=raw["pos_raw"].map(position_group)
        out=[]
        for (key,cpos),g in raw.groupby(["key","consensus_pos"], dropna=False):
            defender = cpos in ["DL","DB"]
            gg = g.copy()
            if defender and is_idp_page.loc[gg.index].any():
                gg = gg[is_idp_page.loc[gg.index]]
            elif not defender:
                non_idp = ~is_idp_page.loc[gg.index]
                if non_idp.any(): gg = gg[non_idp]
            mx = gg.page_score.max()
            gg = gg[gg.page_score.eq(mx)]
            row = gg.sort_values("ecr").iloc[0]
            out.append({"key":key,"consensus_pos":cpos,"consensus_rank":float(row.ecr),"consensus_page":row.page})
        return pd.DataFrame(out)
    except Exception as e:
        st.session_state["market_error"] = str(e)
        return pd.DataFrame()

def position_group(pos):
    if pos in ["DE","DT","NT","EDGE","DL"]: return "DL"
    if pos in ["CB","S","FS","SS","DB"]: return "DB"
    return pos

def canonical_position(raw_pos):
    p=str(raw_pos or "").upper().strip()
    aliases={"HB":"RB","FB":"RB","NT":"DL","DT":"DL","DE":"DL","EDGE":"DL","CB":"DB","S":"DB","FS":"DB","SS":"DB"}
    return aliases.get(p,p)

def validate_position(player, pos):
    """Canonicalize the source position only; never infer position from a player's name."""
    return canonical_position(pos)


# --- Fantasy Edge v9.1 production layer (v9.08 certified) ---
V9_BOARD = Path("production_board.csv")
V9_CONFIG = Path("engine_config.csv")

@st.cache_data
def load_v9_production():
    """Load the certified v9.1 production board and round-specific engine weights."""
    if not V9_BOARD.exists():
        return pd.DataFrame(), {"default":(16.0,2.0,.2,.5), "rounds":{}}
    pb=pd.read_csv(V9_BOARD)
    # V6.19 cornerstone pool certification: never silently ship without current
    # first/second-round anchors. This protects dropdown + recommendation pool.
    _cornerstones=["CeeDee Lamb","Kenneth Walker III","Justin Jefferson","Saquon Barkley",
                   "Brock Bowers","Ashton Jeanty","Drake London","A.J. Brown","Nico Collins"]
    _missing_cornerstones=[_p for _p in _cornerstones if _p not in set(pb["Player"].astype(str))]
    if _missing_cornerstones:
        raise RuntimeError("Production player pool missing cornerstone players: "+", ".join(_missing_cornerstones))
    pb["key"]=pb["Player"].map(norm)
    # Backward-compatible v9.1 hotfix: derive Base_live_score from certified board fields if absent.
    if "Base_live_score" not in pb.columns:
        def _z9(s):
            s=pd.to_numeric(s,errors="coerce")
            sd=s.std(ddof=0)
            return (s-s.mean())/(sd if pd.notna(sd) and sd!=0 else 1.0)
        pb["Base_live_score"]=(0.55*_z9(pb["Draft_score"])
                               +0.30*_z9(pb["VORP"])
                               +0.15*_z9(-pd.to_numeric(pb["Market_pick"],errors="coerce")))
    cfg={"default":(16.0,2.0,.2,.5), "rounds":{}}
    if V9_CONFIG.exists():
        ec=pd.read_csv(V9_CONFIG)
        vals=dict(zip(ec["Field"].astype(str),ec["Value"].astype(str)))
        def _weights(v):
            try: return tuple(float(x.strip()) for x in str(v).strip("()").split(","))
            except: return None
        d=_weights(vals.get("Default_weights"))
        if d and len(d)==4: cfg["default"]=d
        for k,v in vals.items():
            m=re.fullmatch(r"Round_(\d+)_weights",k)
            w=_weights(v)
            if m and w and len(w)==4: cfg["rounds"][int(m.group(1))]=w
    return pb,cfg

def attach_v9_production(board):
    """Attach certified player signals without disturbing the rest of the dashboard."""
    pb,_=load_v9_production()
    if pb.empty: return board
    keep=pb[["key","Market_pick","VORP","Draft_score","Model_rank","Base_live_score"]].drop_duplicates("key")
    keep=keep.rename(columns={
        "Market_pick":"v9_market_pick","VORP":"v9_vorp","Draft_score":"v9_draft_score",
        "Model_rank":"v9_model_rank","Base_live_score":"v9_base_live_score"})
    return board.merge(keep,on="key",how="left")

def v9_live_rank(avail, round_no, current_pick, roster_counts):
    """Certified v9.08 translation used by the v9.1 live draft assistant."""
    pb,cfg=load_v9_production()
    x=avail.copy()
    if pb.empty or "v9_base_live_score" not in x:
        x["v9_live_score"]=_safe_num_series(x,"draft_score",0.0)
        return x
    # Frozen champion round/player and position priors reconstructed from production board rank/timing.
    # Player identity prior is represented by the certified static base score; round overrides control
    # the dynamic translation exactly as certified in v9.08.
    pw,posw,tw,nw=cfg["rounds"].get(int(round_no),cfg["default"])
    mp=pd.to_numeric(x["v9_market_pick"],errors="coerce").fillna(pd.to_numeric(x["market_pick"],errors="coerce"))
    delta=float(current_pick)-mp
    timing=np.where(delta>=0,np.minimum(delta/18.0,1.5),np.maximum(delta/24.0,-1.5))
    base=pd.to_numeric(x["v9_base_live_score"],errors="coerce")
    fallback=(pd.to_numeric(x["draft_score"],errors="coerce").rank(pct=True)-.5)*2
    base=base.fillna(fallback)
    # Use model-rank percentile as a stable player-prior proxy for players on the certified board.
    mr=pd.to_numeric(x["v9_model_rank"],errors="coerce")
    player_prior=(1-(mr-1)/max(len(pb)-1,1)).clip(0,1).fillna(0)
    # Position prior from the currently available certified board at this round.
    pos_counts=pb["Position"].value_counts(normalize=True).to_dict()
    position_prior=x["position"].map(pos_counts).fillna(0)
    need=[]
    caps={"QB":(1,2),"RB":(2,99),"WR":(2,99),"TE":(1,2),"K":(1,1),"DL":(1,1),"DB":(1,1)}
    for p in x["position"]:
        lo,hi=caps.get(p,(0,99)); cnt=int(roster_counts.get(p,0))
        need.append(1.0 if cnt<lo else 0.0)
    x["v9_live_score"]=base+pw*player_prior+posw*position_prior+tw*timing+nw*np.asarray(need)
    x["v9_market_pick_effective"]=mp
    return x


def _v944_add_idp_display_metrics(x):
    """Add position-relative IDP metrics without overwriting raw projection/VORP/model_rank."""
    y=x.copy()
    if "idp_impact_score" not in y.columns:
        y["idp_impact_score"]=np.nan
    if "idp_external_rank" not in y.columns:
        y["idp_external_rank"]=np.nan

    y["display_projection"]=pd.to_numeric(y.get("projection",np.nan),errors="coerce")
    y["display_vorp"]=pd.to_numeric(y.get("vorp",np.nan),errors="coerce")
    y["display_model_rank"]=pd.to_numeric(y.get("model_rank",np.nan),errors="coerce")

    mask=y["position"].astype(str).str.upper().isin(["DL","DB"])
    # For IDP, show the score/rank actually used by the IDP mechanism.
    y.loc[mask,"display_projection"]=pd.to_numeric(y.loc[mask,"idp_impact_score"],errors="coerce")
    y.loc[mask,"display_vorp"]=pd.to_numeric(y.loc[mask,"roster_opportunity_adj"],errors="coerce")
    y.loc[mask,"display_model_rank"]=pd.to_numeric(y.loc[mask,"idp_external_rank"],errors="coerce")
    return y

def _marginal_roster_multiplier(pos, counts, slots):
    """How much of a player's raw value is realistically usable on this roster."""
    pos=str(pos)
    have=int(counts.get(pos,0))

    if pos=="RB":
        # RB1/RB2 starters, RB3/RB4 useful FLEX/depth, RB5+ sharply diminished.
        return [1.00,1.00,0.88,0.72,0.48,0.28,0.16][min(have,6)]
    if pos=="WR":
        # WR1/WR2 starters; WR3-WR5 remain useful in 2-FLEX; WR6+ diminished.
        return [1.00,1.00,0.92,0.82,0.68,0.46,0.28][min(have,6)]
    if pos=="TE":
        return 1.00 if have<1 else 0.38 if have==1 else 0.15
    if pos=="QB":
        return 1.00 if have<1 else 0.34 if have==1 else 0.10
    if pos=="K":
        return 1.00 if have<1 else 0.0
    if pos in ("DL","DB"):
        # Required starter is full value. First/second impact backup still useful.
        return 1.00 if have<1 else 0.78 if have==1 else 0.55 if have==2 else 0.30
    return 1.0


def _add_marginal_roster_value(x, roster, slots):
    """Add usable VORP / marginal roster value without overwriting raw VORP."""
    y=x.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}

    raw_vorp=_safe_num_series(y,"vorp",0.0)
    raw_proj=_safe_num_series(y,"projection",0.0)

    mult=y["position"].map(lambda p:_marginal_roster_multiplier(p,counts,slots)).astype(float)
    y["roster_value_multiplier"]=mult
    y["usable_vorp"]=raw_vorp*mult

    # Projection contributes only modestly to marginal value; VORP is primary.
    y["marginal_roster_value"]=(
        y["usable_vorp"]*2.4 +
        np.maximum(raw_proj,0.0)*0.12*mult
    )

    # Late-bench startability/upside proxy: reward candidates with enough projection
    # and usable VORP to plausibly enter the lineup; discount pure roster-cloggers.
    proj_rank=y.groupby("position")["projection"].rank(pct=True,ascending=True).fillna(0.5)
    vorp_rank=y.groupby("position")["vorp"].rank(pct=True,ascending=True).fillna(0.5)
    y["bench_startability"]=np.clip(0.55*proj_rank+0.45*vorp_rank,0.0,1.0)
    y["marginal_roster_value"]*=np.where(
        y["position"].isin(["RB","WR"]) & (mult<0.60),
        0.65+0.35*y["bench_startability"],
        1.0
    )
    return y

def _portfolio_depth_penalty(pos, counts):
    """Penalty for redundant bench concentration; starters/FLEX remain largely untouched."""
    pos=str(pos); have=int(counts.get(pos,0))
    if pos=="RB":
        return 0.0 if have<=3 else 2.0 if have==4 else 8.0 if have==5 else 14.0
    if pos=="WR":
        return 0.0 if have<=4 else 5.0 if have==5 else 10.0
    if pos=="QB":
        return 0.0 if have==0 else 7.0
    if pos=="TE":
        return 0.0 if have==0 else 6.0
    if pos=="K":
        return 0.0 if have==0 else 1000.0
    return 0.0


def _add_cross_position_bench_value(x, roster, slots):
    """Compare each deep-bench candidate to the best other-position use of that bench slot."""
    y=x.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    if "marginal_roster_value" not in y.columns:
        y=_add_marginal_roster_value(y,roster,slots)

    y["portfolio_depth_penalty"]=y["position"].map(lambda p:_portfolio_depth_penalty(p,counts)).astype(float)
    y["portfolio_value"]=pd.to_numeric(y["marginal_roster_value"],errors="coerce").fillna(0.0)-y["portfolio_depth_penalty"]

    # Best alternative at another position = opportunity cost of this bench slot.
    best_by_pos=y.groupby("position")["portfolio_value"].max().to_dict()
    alt=[]
    for _,row in y.iterrows():
        others=[v for p,v in best_by_pos.items() if p!=row.position and pd.notna(v)]
        alt.append(max(others) if others else 0.0)
    y["best_other_position_value"]=alt
    y["value_over_next_roster_slot"]=y["portfolio_value"]-y["best_other_position_value"]
    return y


def _benchmark_candidate_prefilter(avail, current_pick, per_position=12, overall_market=55):
    """
    Lossless-for-practical-draft benchmark prefilter:
    retain the market front plus leaders at every position by projection, VORP,
    draft score, and IDP quality. The exact production scorer chooses from this set.
    """
    if avail is None or len(avail)==0:
        return avail
    x=avail.copy()
    keep=set()

    market=_safe_num_series(x,"market_pick",999.0)
    if "consensus_rank" in x.columns:
        market=pd.to_numeric(x["consensus_rank"],errors="coerce").fillna(market)
    keep.update(market.nsmallest(min(int(overall_market),len(x))).index)

    for p in x["position"].astype(str).unique():
        pm=x["position"].astype(str).eq(p)
        xp=x.loc[pm]
        if xp.empty:
            continue
        for col,ascending in [("projection",False),("vorp",False),("draft_score",False),
                              ("idp_impact_score",False),("idp_external_rank",True)]:
            if col not in xp.columns:
                continue
            vals=pd.to_numeric(xp[col],errors="coerce")
            vals=vals.sort_values(ascending=ascending,na_position="last")
            keep.update(vals.head(min(int(per_position),len(vals))).index)

    return x.loc[x.index.isin(keep)].copy()


def prepare_user_draft_candidates(avail, roster, round_no, current_pick, slot, teams, slots, randomness):
    """Single pre-ranking pipeline used by both Live Draft Mode and Mock Draft Lab."""
    x=avail.copy()

    # Same injury/availability policy in both modes.
    if "injury_severity" in x.columns:
        x=x[pd.to_numeric(x["injury_severity"],errors="coerce").fillna(0)<3].copy()

    total_rounds=exact_roster_rounds(slots)
    x=draft_eligibility(x,roster,int(round_no),int(total_rounds),slots)
    if x.empty:
        return x, None

    # Same roster context columns in both modes.
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    x["_construction_bonus"]=0.0

    _rb=int(counts.get("RB",0))
    _wr=int(counts.get("WR",0))
    _te=int(counts.get("TE",0))
    _rnd=int(round_no)

    # WR/TE starter-shell pressure.
    if _wr<2:
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=7.0
    elif _wr==2:
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=3.0
    elif _wr==3:
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=1.0
    elif _wr>=4:
        # WR5+ is bench value, not a construction target.
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=0.0

    if _te<1 and _rnd>=4:
        x.loc[x.position.eq("TE"),"_construction_bonus"]+=2.5

    # RB marginal utility: RB1/RB2 are starters, RB3 can be a FLEX,
    # but RB4 before the WR/TE shell is built is effectively premature depth.
    if _rb>=2 and _rnd<=6:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=3.0
    if _rb>=3 and _rnd<=7:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=8.0
    if _rb>=4:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=7.0

    # Once RB5 is already rostered, RB6 carries a strong diminishing-return penalty.
    # The corresponding impact-IDP bonus is applied later, AFTER IDP evidence/tier fields exist.
    if _rb>=5:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=28.0
        x.loc[x.position.eq("RB"),"rb6_depth_penalty"]=-28.0
    if _wr>=5:
        x.loc[x.position.eq("WR"),"_construction_bonus"]-=20.0
        x.loc[x.position.eq("WR"),"wr6_depth_penalty"]=-20.0

    if _rb>=6:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=5000.0
        x.loc[x.position.eq("RB"),"deep_skill_hard_cap"]=True
    if _wr>=6:
        x.loc[x.position.eq("WR"),"_construction_bonus"]-=5000.0
        x.loc[x.position.eq("WR"),"deep_skill_hard_cap"]=True

    _qb=int(counts.get("QB",0))
    if _qb>=2 and _te>=1:
        x.loc[x.position.eq("TE"),"_construction_bonus"]-=32.0
        x.loc[x.position.eq("TE"),"second_backup_penalty"]=-32.0
    if _te>=2 and _qb>=1:
        x.loc[x.position.eq("QB"),"_construction_bonus"]-=32.0
        x.loc[x.position.eq("QB"),"second_backup_penalty"]=-32.0

    # Hard early-shell guard: do not take RB4 in rounds 1-6 while a required WR/TE
    # starter is still missing, unless no viable starter-position alternatives exist.
    _starter_shell_missing=(_wr<2) or (_te<1)
    if _rnd<=6 and _rb>=3 and _starter_shell_missing:
        _alternatives=x[
            x.position.isin(["WR","TE"]) &
            (
                ((x.position=="WR") & (_wr<2)) |
                ((x.position=="TE") & (_te<1))
            )
        ]
        if len(_alternatives):
            _ap=pd.to_numeric(_alternatives.get("projection",np.nan),errors="coerce")
            _av=pd.to_numeric(_alternatives.get("vorp",np.nan),errors="coerce")
            _viable=(_ap.notna() & _av.notna() & (_ap>0))
            if _viable.any():
                x.loc[x.position.eq("RB"),"_construction_bonus"]-=1000.0
                x.loc[x.position.eq("RB"),"early_rb_surplus_blocked"]=True

    if "early_rb_surplus_blocked" not in x.columns:
        x["early_rb_surplus_blocked"]=False
    if "impact_idp_depth_bonus" not in x.columns:
        x["impact_idp_depth_bonus"]=0.0
    if "rb6_depth_penalty" not in x.columns:
        x["rb6_depth_penalty"]=0.0
    if "wr6_depth_penalty" not in x.columns:
        x["wr6_depth_penalty"]=0.0
    if "deep_skill_hard_cap" not in x.columns:
        x["deep_skill_hard_cap"]=False
    if "second_backup_penalty" not in x.columns:
        x["second_backup_penalty"]=0.0
    x["early_rb_surplus_blocked"]=x["early_rb_surplus_blocked"].fillna(False).astype(bool)

    # Surplus-depth discipline while required slots are still open.
    _min_req,_fixed_def,_flex_extra=_minimum_required_picks_remaining(counts,slots)
    if _min_req>0:
        if int(counts.get("QB",0))>=int(slots.get("QB",1)):
            x.loc[x.position.eq("QB"),"_construction_bonus"]-=22.0
        if int(counts.get("TE",0))>=int(slots.get("TE",1)):
            x.loc[x.position.eq("TE"),"_construction_bonus"]-=18.0

        # If one required IDP position is missing, a backup at the other IDP
        # position cannot crowd it out.
        if int(counts.get("DB",0))<int(slots.get("DB",1)) and int(counts.get("DL",0))>=int(slots.get("DL",1)):
            x.loc[x.position.eq("DL"),"_construction_bonus"]-=30.0
            x.loc[x.position.eq("DB"),"_construction_bonus"]+=12.0
        if int(counts.get("DL",0))<int(slots.get("DL",1)) and int(counts.get("DB",0))>=int(slots.get("DB",1)):
            x.loc[x.position.eq("DB"),"_construction_bonus"]-=30.0
            x.loc[x.position.eq("DL"),"_construction_bonus"]+=12.0

    x["roster_need"]=x.position.map(lambda p: roster_need_for_mock(roster,p,slots))
    _sim_mode=("_sim_precomputed_idp" in x.columns and x["_sim_precomputed_idp"].fillna(False).astype(bool).all())
    _delta_cap=18 if _sim_mode else 64
    x["roster_delta"]=_candidate_roster_delta_df(roster,x,slots,exact_cap=_delta_cap)

    # Fantasy Edge marginal roster value: raw VORP is not equally usable at RB6/WR6/QB2/etc.
    x=_add_marginal_roster_value(x,roster,slots)
    x=_add_cross_position_bench_value(x,roster,slots)

    next_pick=next_user_pick(int(current_pick),int(slot),int(teams),int(total_rounds))
    x,_local=v939_shared_candidate_rank(
        x,roster,int(round_no),int(current_pick),next_pick,slots,int(randomness)
    )
    return x,next_pick


def _safe_num_series(df, name, default=0.0):
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").fillna(float(default))
    return pd.Series(float(default), index=df.index, dtype=float)


def _position_depth_after_pick(roster, pos):
    counts = roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    counts = dict(counts)
    p = str(pos)
    counts[p] = int(counts.get(p, 0)) + 1
    return counts


def _starter_flex_improvement(pos, counts, slots):
    """Continuous lineup value; no preferred 4-RB/5-WR template."""
    p = str(pos)
    have = int(counts.get(p, 0))
    need = int(slots.get(p, 0))

    if have < need:
        return 8.0

    if p in ("RB", "WR", "TE"):
        skill_have = int(counts.get("RB", 0)) + int(counts.get("WR", 0)) + int(counts.get("TE", 0))
        skill_need = (
            int(slots.get("RB", 0)) + int(slots.get("WR", 0)) +
            int(slots.get("TE", 0)) + int(slots.get("FLEX", 0))
        )
        if skill_have < skill_need:
            return 5.0

    # Smooth marginal decline after starter/FLEX usefulness is satisfied.
    depth = max(have - need, 0)
    curves = {
        "RB": [2.8, 2.0, 1.2, 0.3, -1.5, -3.5, -5.5],
        "WR": [3.0, 2.3, 1.6, 0.8, -0.8, -2.6, -4.5],
        "TE": [1.2, -1.5, -3.5],
        "QB": [0.8, -2.0, -4.0],
        "DL": [0.8, -1.2, -4.0],
        "DB": [0.8, -1.2, -4.0],
        "K": [-100.0, -100.0],
    }
    vals = curves.get(p, [0.0])
    return float(vals[min(depth, len(vals)-1)])


def _market_survival_probability(market_pick, current_pick, next_pick):
    """
    Smooth probability that a player survives until next turn.
    < 0.2 = strong urgency, > 0.7 = likely wait.
    """
    span = max(float(next_pick) - float(current_pick), 1.0)
    margin = float(market_pick) - float(next_pick)
    # logistic centered around next_pick; 6-pick temperature keeps this smooth
    return float(1.0 / (1.0 + np.exp(-margin / 6.0)))


def _same_position_next_turn_value(x, idx, current_pick, next_pick):
    """Expected best same-position value at next turn."""
    pos = str(x.at[idx, "position"])
    pool = x[x["position"].astype(str).eq(pos)].drop(index=idx, errors="ignore").copy()
    if pool.empty:
        return 0.0, 12.0, 0.0

    evals = _safe_num_series(pool, "evaluation_score", 0.0)
    unified = _safe_num_series(pool, "unified_pick_score", 0.0)
    base = np.maximum(evals, unified)

    market = _safe_num_series(pool, "market_pick", np.nan)
    if "market_pick" not in pool.columns and "consensus_rank" in pool.columns:
        market = _safe_num_series(pool, "consensus_rank", float(next_pick)+20)
    market = market.fillna(float(next_pick)+20)

    surv = market.map(lambda mp: _market_survival_probability(mp, current_pick, next_pick))
    expected = base * surv

    if len(expected):
        j = expected.idxmax()
        next_val = float(expected.loc[j])
        raw_next = float(base.loc[j])
        best_surv = float(surv.loc[j])
    else:
        next_val = raw_next = best_surv = 0.0

    current_val = float(max(
        pd.to_numeric(pd.Series([x.at[idx, "evaluation_score"]]), errors="coerce").fillna(0).iloc[0],
        pd.to_numeric(pd.Series([x.at[idx, "unified_pick_score"]]), errors="coerce").fillna(0).iloc[0],
    ))
    loss = float(np.clip(current_val - next_val, 0.0, 14.0))
    return next_val, loss, best_surv


def _cross_position_opportunity_cost(x, idx):
    """
    Best competing use of the same roster slot across other positions.
    This is the key anti-template mechanism.
    """
    pos = str(x.at[idx, "position"])
    score = _safe_num_series(x, "unified_pick_score", 0.0)
    other = x["position"].astype(str).ne(pos)
    if not other.any():
        return 0.0
    best_other = float(score[other].max())
    mine = float(score.loc[idx])
    return float(np.clip(best_other - mine, -10.0, 14.0))


def _tier_cliff_value(x, candidate_idx):
    pos = str(x.at[candidate_idx, "position"])
    pool = x[x["position"].astype(str).eq(pos)].copy()
    if len(pool) < 2:
        return 0.0

    score = _safe_num_series(pool, "unified_pick_score", 0.0)
    pool = pool.assign(_tier_score=score).sort_values("_tier_score", ascending=False)
    loc = np.where(pool.index.to_numpy() == candidate_idx)[0]
    if len(loc) == 0:
        return 0.0
    i = int(loc[0])
    if i >= len(pool)-1:
        return 0.0
    cliff = float(pool.iloc[i]["_tier_score"] - pool.iloc[i+1]["_tier_score"])
    return float(np.clip(cliff, 0.0, 10.0))


def _future_roster_portfolio_value(pos, counts, slots):
    """
    Score the roster after the candidate is added.
    No fixed roster target; only saturation and flexibility.
    """
    after = dict(counts)
    p = str(pos)
    after[p] = int(after.get(p, 0)) + 1

    rb, wr = int(after.get("RB", 0)), int(after.get("WR", 0))
    qb, te = int(after.get("QB", 0)), int(after.get("TE", 0))
    dl, db = int(after.get("DL", 0)), int(after.get("DB", 0))
    idp = dl + db

    value = 0.0
    # Flexibility reward while still filling usable offensive depth.
    skill = rb + wr + te
    skill_required = int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+int(slots.get("FLEX",0))
    if skill <= skill_required + 2:
        value += 1.0

    # Smooth saturation penalties.
    if rb >= 5: value -= 1.3 * (rb - 4)
    if wr >= 6: value -= 1.1 * (wr - 5)
    if qb >= 2: value -= 1.8 * (qb - 1)
    if te >= 2: value -= 1.4 * (te - 1)

    # IDP: 2 is normal, 3 can be good, 4+ is poor for this 17-player format.
    if idp == 3: value += 0.4
    if idp >= 4: value -= 6.0 + 3.0 * (idp - 4)

    return float(value)


def _live_opportunity_optimizer(x, roster, slots, current_pick, next_pick, top_n=20):
    """
    Final Live/Mock optimizer:
      current player value
      + lineup improvement
      + tier cliff
      + next-turn replacement loss
      + future roster portfolio value
      - cross-position opportunity cost
      - reach risk
    """
    y = x.copy()
    if y.empty:
        return y

    counts = roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    base = _safe_num_series(y, "unified_pick_score", 0.0)

    y["opportunity_score"] = base.astype(float)
    for col in [
        "lineup_improvement_component","tier_cliff_component","replacement_loss_component",
        "next_turn_survival_component","cross_position_cost_component","future_roster_component",
        "reach_risk_component"
    ]:
        y[col] = 0.0

    market = _safe_num_series(y, "market_pick", float(next_pick)+20)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market = _safe_num_series(y, "consensus_rank", float(next_pick)+20)

    serious = y.nlargest(min(int(top_n), len(y)), "opportunity_score").index

    for idx in serious:
        p = str(y.at[idx, "position"])

        lineup = _starter_flex_improvement(p, counts, slots)
        cliff = _tier_cliff_value(y, idx)
        _, replacement_loss, replacement_survival = _same_position_next_turn_value(
            y, idx, current_pick, next_pick
        )
        cross_cost = _cross_position_opportunity_cost(y, idx)
        future = _future_roster_portfolio_value(p, counts, slots)

        surv = _market_survival_probability(float(market.loc[idx]), current_pick, next_pick)
        urgency = (1.0 - surv) * 5.5

        reach = max(float(market.loc[idx]) - float(current_pick), 0.0)
        reach_risk = min(reach, 48.0) * 0.10

        y.at[idx, "lineup_improvement_component"] = lineup
        y.at[idx, "tier_cliff_component"] = cliff
        y.at[idx, "replacement_loss_component"] = replacement_loss
        y.at[idx, "next_turn_survival_component"] = surv
        y.at[idx, "cross_position_cost_component"] = cross_cost
        y.at[idx, "future_roster_component"] = future
        y.at[idx, "reach_risk_component"] = reach_risk

        y.at[idx, "opportunity_score"] += (
            lineup +
            0.85 * cliff +
            1.20 * replacement_loss +
            urgency +
            future -
            0.85 * max(cross_cost, 0.0) -
            reach_risk
        )

    # Recommendation confidence and challenger gap.
    ranked = y["opportunity_score"].sort_values(ascending=False)
    gap = float(ranked.iloc[0] - ranked.iloc[1]) if len(ranked) >= 2 else 8.0
    y["recommendation_confidence"] = np.clip(50.0 + gap * 6.5, 50.0, 99.0)
    y["challenger_gap"] = gap

    return y



def _objective_player_shortlist(x, top_n=15):
    """
    Stage 1: player-only shortlist.
    Uses projection, VORP, market value, model quality, injury/role and IDP talent.
    No roster need, saturation or bench-shape logic is allowed here.
    """
    y=x.copy()
    if y.empty:
        return y

    proj=_safe_num_series(y,"projection",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    market=_safe_num_series(y,"market_pick",999.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",999.0)

    raw_model=_safe_num_series(y,"draft_score",0.0)
    injury=_safe_num_series(y,"injury_penalty",0.0)
    role=_safe_num_series(y,"role_score",0.0)

    pos=y["position"].astype(str)
    proj_pct=proj.groupby(pos).rank(pct=True,method="average")
    vorp_pct=vorp.groupby(pos).rank(pct=True,method="average")
    market_pct=1.0-market.rank(pct=True,method="average")
    model_pct=raw_model.rank(pct=True,method="average")
    role_pct=role.groupby(pos).rank(pct=True,method="average") if "role_score" in y.columns else pd.Series(0.5,index=y.index)

    y["player_shortlist_score"]=100.0*(
        0.34*proj_pct.fillna(0.5) +
        0.32*vorp_pct.fillna(0.5) +
        0.15*market_pct.fillna(0.5) +
        0.12*model_pct.fillna(0.5) +
        0.07*role_pct.fillna(0.5)
    ) - np.clip(injury,0,30)*1.2

    idp=pos.isin(["DL","DB"])
    if idp.any():
        impact=_safe_num_series(y,"idp_impact_score",0.0)
        tier=_safe_num_series(y,"idp_quality_tier",5.0)
        ext=_safe_num_series(y,"idp_external_rank",50.0)
        impact_pct=impact.groupby(pos).rank(pct=True,method="average")
        ext_pct=1.0-ext.groupby(pos).rank(pct=True,method="average")
        tier_support=np.clip(1.0-(tier-1.0)/4.0,0,1)
        idp_quality=100.0*(0.52*impact_pct.fillna(0.5)+0.28*tier_support+0.20*ext_pct.fillna(0.5))
        y.loc[idp,"player_shortlist_score"]=0.62*y.loc[idp,"player_shortlist_score"]+0.38*idp_quality[idp]

    keep=set(y.nlargest(min(int(top_n),len(y)),"player_shortlist_score").index.tolist())
    for p in pos.dropna().unique():
        pm=pos.eq(p)
        keep.update(y.loc[pm].nlargest(min(3,int(pm.sum())),"player_shortlist_score").index.tolist())

    y["stage1_shortlisted"]=y.index.isin(keep)
    return y


def _future_pick_value(pool, counts, slots, future_pick, prior_pick, excluded=None):
    """Expected best usable roster value at a future turn."""
    q=pool.drop(index=list(excluded or []),errors="ignore").copy()
    if q.empty:
        return 0.0, None

    market=_safe_num_series(q,"market_pick",float(future_pick)+20)
    if "market_pick" not in q.columns and "consensus_rank" in q.columns:
        market=_safe_num_series(q,"consensus_rank",float(future_pick)+20)

    base=_safe_num_series(q,"player_shortlist_score",50.0)
    survival=market.map(lambda mp:_market_survival_probability(mp,prior_pick,future_pick))

    lineup=np.asarray([
        _starter_flex_improvement(p,counts,slots)
        for p in q["position"].astype(str)
    ],dtype=float)
    future=np.asarray([
        _future_roster_portfolio_value(p,counts,slots)
        for p in q["position"].astype(str)
    ],dtype=float)

    expected=0.74*base + 2.2*lineup + 1.2*future
    expected=expected*survival.to_numpy(dtype=float)

    if not np.isfinite(expected).any():
        return 0.0,None
    i=int(np.nanargmax(expected))
    return float(expected[i]),q.index[i]


def _two_pick_rollout_value(x, idx, roster, slots, current_pick, next_pick):
    """
    Stage 2 rollout: estimate the portfolio after this pick plus the next two user turns.
    Lightweight enough for live use; only top contenders receive a rollout.
    """
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    p=str(x.at[idx,"position"])
    after=dict(counts)
    after[p]=int(after.get(p,0))+1

    gap=max(int(next_pick)-int(current_pick),1)
    next2=int(next_pick)+gap

    first,first_idx=_future_pick_value(
        x,after,slots,int(next_pick),int(current_pick),excluded=[idx]
    )
    after2=dict(after)
    excluded=[idx]
    if first_idx is not None:
        p2=str(x.at[first_idx,"position"])
        after2[p2]=int(after2.get(p2,0))+1
        excluded.append(first_idx)

    second,_=_future_pick_value(
        x,after2,slots,int(next2),int(next_pick),excluded=excluded
    )

    # Future picks are discounted; current selection remains authoritative.
    return float(0.34*first + 0.20*second)


def _room_run_pressure(x, current_pick, next_pick):
    """
    Adaptive draft-room pressure by position.
    If the available board is being depleted ahead of market expectation, urgency rises.
    """
    y=x.copy()
    pos=y["position"].astype(str)
    market=_safe_num_series(y,"market_pick",999.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",999.0)

    pressure=pd.Series(0.0,index=y.index,dtype=float)
    span=max(int(next_pick)-int(current_pick),1)

    for p in pos.dropna().unique():
        pm=pos.eq(p)
        if not pm.any():
            continue
        likely_before_next=((market[pm]>=float(current_pick)) & (market[pm]<float(next_pick))).sum()
        available_now=int(pm.sum())
        # More players likely to disappear before next turn => more urgency.
        pr=float(np.clip(likely_before_next/max(min(available_now,8),1),0,1))*4.5
        pressure.loc[pm]=pr
    return pressure


def _candidate_stability(y, finalists, trials=24):
    """
    Perturb projection/VORP/market slightly. Stability is how often the same candidate wins.
    Deterministic seed from candidate count keeps rerenders stable.
    """
    if len(finalists)==0:
        return pd.Series(0.0,index=y.index)
    rng=np.random.default_rng(7000+len(y))
    base=_safe_num_series(y,"final_pick_value",-1e9)
    proj=_safe_num_series(y,"projection",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    market=_safe_num_series(y,"market_pick",999.0)
    wins={idx:0 for idx in finalists}

    for _ in range(int(trials)):
        perturb=(
            rng.normal(0,0.55,len(y)) +
            rng.normal(0,0.10,len(y))*proj.to_numpy(float) +
            rng.normal(0,0.18,len(y))*vorp.to_numpy(float) -
            rng.normal(0,0.015,len(y))*market.to_numpy(float)
        )
        vals=base.to_numpy(float)+perturb
        mask=np.array([idx in finalists for idx in y.index],dtype=bool)
        vals=np.where(mask,vals,-1e12)
        win_idx=y.index[int(np.nanargmax(vals))]
        if win_idx in wins:
            wins[win_idx]+=1

    out=pd.Series(0.0,index=y.index,dtype=float)
    for idx,n in wins.items():
        out.loc[idx]=n/max(int(trials),1)
    return out


def _two_stage_live_optimizer(x, roster, slots, current_pick, next_pick):
    """
    Player Value -> Candidate Shortlist -> Strategic Opportunity -> 2-pick Rollout
    -> Challenger Check -> FINAL PICK.
    """
    y=_objective_player_shortlist(x,top_n=15)
    if y.empty:
        return y

    # Stage 2 opportunity logic is only run on shortlisted players.
    strategic=_live_opportunity_optimizer(
        y[y["stage1_shortlisted"]].copy(),
        roster,slots,current_pick,next_pick,top_n=20
    )

    y["opportunity_score"]=-1e9
    y["rollout_value"]=0.0
    y["final_pick_value"]=-1e9
    y["recommendation_confidence"]=50.0
    y["challenger_gap"]=0.0

    for c in [
        "lineup_improvement_component","tier_cliff_component","replacement_loss_component",
        "next_turn_survival_component","cross_position_cost_component","future_roster_component",
        "reach_risk_component"
    ]:
        if c not in y.columns:
            y[c]=0.0
        if c in strategic.columns:
            y.loc[strategic.index,c]=strategic[c]

    y.loc[strategic.index,"opportunity_score"]=strategic["opportunity_score"]

    # Draft-room adaptation enters only at Stage 2.
    room_pressure=_room_run_pressure(y,current_pick,next_pick)
    y["room_run_pressure_component"]=room_pressure

    # Only the top five strategy candidates need the expensive rollout.
    finalists=strategic.nlargest(min(5,len(strategic)),"opportunity_score").index
    for idx in finalists:
        rv=_two_pick_rollout_value(y,idx,roster,slots,current_pick,next_pick)
        y.at[idx,"rollout_value"]=rv
        y.at[idx,"final_pick_value"]=(
            float(y.at[idx,"opportunity_score"])+rv+
            float(room_pressure.loc[idx])
        )

    # Non-finalists retain opportunity score but cannot beat finalists by missing rollout.
    other=strategic.index.difference(finalists)
    y.loc[other,"final_pick_value"]=y.loc[other,"opportunity_score"]

    ranked=y.loc[strategic.index,"final_pick_value"].sort_values(ascending=False)
    if len(ranked)>=2:
        gap=float(ranked.iloc[0]-ranked.iloc[1])
    else:
        gap=8.0
    # Candidate stability test: recommendations that flip under small data perturbations
    # should display lower confidence.
    stability=_candidate_stability(y,list(finalists),trials=24)
    y["candidate_stability"]=stability
    leader_stability=float(stability.loc[ranked.index[0]]) if len(ranked) else 0.0

    conf=float(np.clip(42.0+gap*4.8+leader_stability*35.0,45.0,99.0))
    y.loc[strategic.index,"recommendation_confidence"]=conf
    y.loc[strategic.index,"challenger_gap"]=gap

    # Best same-position and cross-position challenger values for auditability.
    leader=ranked.index[0] if len(ranked) else None
    y["best_same_position_challenger"]=np.nan
    y["best_cross_position_challenger"]=np.nan
    if leader is not None:
        lp=str(y.at[leader,"position"])
        same=strategic[strategic["position"].astype(str).eq(lp)].drop(index=leader,errors="ignore")
        cross=strategic[strategic["position"].astype(str).ne(lp)]
        same_v=float(y.loc[same.index,"final_pick_value"].max()) if len(same) else np.nan
        cross_v=float(y.loc[cross.index,"final_pick_value"].max()) if len(cross) else np.nan
        y.loc[strategic.index,"best_same_position_challenger"]=same_v
        y.loc[strategic.index,"best_cross_position_challenger"]=cross_v

    return y



def _base_player_value_engine(x):
    """One normalized player-value authority, independent of roster shape."""
    y=x.copy()
    pos=y["position"].astype(str)
    proj=_safe_num_series(y,"projection",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    market=_safe_num_series(y,"market_pick",999.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",999.0)
    model=_safe_num_series(y,"draft_score",0.0)
    injury=_safe_num_series(y,"injury_penalty",0.0)

    proj_pct=proj.groupby(pos).rank(pct=True,method="average")
    vorp_pct=vorp.groupby(pos).rank(pct=True,method="average")
    market_pct=1.0-market.rank(pct=True,method="average")
    model_pct=model.rank(pct=True,method="average")

    # Projection/VORP are the primary player-quality authority.
    base=100.0*(0.40*proj_pct.fillna(.5)+0.42*vorp_pct.fillna(.5)+
                0.10*market_pct.fillna(.5)+0.08*model_pct.fillna(.5))

    # Absolute VORP anchor prevents a mediocre player from becoming a top choice
    # solely because he ranks well inside a weak positional pool.
    _abs_vorp=np.clip((vorp+2.0)/14.0,0.0,1.0)
    y["absolute_vorp_anchor"]=(_abs_vorp-0.50)*10.0
    base+=y["absolute_vorp_anchor"]
    base-=np.clip(injury,0,30)*1.25

    # IDP is position-relative: impact/tier/external rank supplement projection/VORP.
    idp=pos.isin(["DL","DB"])
    if idp.any():
        impact=_safe_num_series(y,"idp_impact_score",0.0)
        tier=_safe_num_series(y,"idp_quality_tier",5.0)
        ext=_safe_num_series(y,"idp_external_rank",50.0)
        impact_pct=impact.groupby(pos).rank(pct=True,method="average")
        ext_pct=1.0-ext.groupby(pos).rank(pct=True,method="average")
        tier_pct=np.clip(1.0-(tier-1.0)/4.0,0,1)
        idp_rel=100.0*(.48*impact_pct.fillna(.5)+.30*tier_pct+.22*ext_pct.fillna(.5))
        base.loc[idp]=.58*base.loc[idp]+.42*idp_rel.loc[idp]

    y["base_player_value"]=base
    return y


def _marginal_slot_value(pos, counts, slots):
    """Value of consuming the next roster slot; no target roster counts."""
    p=str(pos); have=int(counts.get(p,0)); req=int(slots.get(p,0))
    if have < req:
        return 9.0
    if p in ("RB","WR","TE"):
        skill=sum(int(counts.get(q,0)) for q in ("RB","WR","TE"))
        starter_skill=int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+int(slots.get("FLEX",0))
        if skill < starter_skill:
            return 5.5

    # Smooth diminishing utility only; not a prescribed roster template.
    depth=max(have-req,0)
    curve={
        # V6.8: RB5/WR5 remain legal, but their marginal utility must beat
        # genuine cross-position alternatives instead of receiving an automatic
        # positive depth bump. This is a soft value curve, not a roster target.
        "RB":[3.0,2.1,0.25,-1.4,-3.0,-4.8,-6.5],
        "WR":[3.2,2.4,0.45,-1.2,-2.8,-4.5,-6.2],
        "TE":[1.4,-1.2,-3.2],
        "QB":[1.0,-1.8,-3.8],
        "DL":[1.0,-1.0,-3.8],
        "DB":[1.0,-1.0,-3.8],
        "K":[-100.0,-100.0],
    }.get(p,[0.0])
    return float(curve[min(depth,len(curve)-1)])


def _survival_wait_cost(y, idx, current_pick, next_pick):
    """(1-P(survive)) × positional replacement drop."""
    p=str(y.at[idx,"position"])
    market=_safe_num_series(y,"market_pick",float(next_pick)+20)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",float(next_pick)+20)

    survive=_market_survival_probability(float(market.loc[idx]),current_pick,next_pick)
    pool=y[y["position"].astype(str).eq(p)].drop(index=idx,errors="ignore")
    mine=float(y.at[idx,"base_player_value"])
    repl=float(pool["base_player_value"].max()) if len(pool) else max(mine-12.0,0.0)
    drop=max(mine-repl,0.0)
    return float((1.0-survive)*drop), float(survive)


def _room_position_pressure(y,current_pick,next_pick):
    """Live board depletion proxy, calculated only from the current available board."""
    pos=y["position"].astype(str)
    market=_safe_num_series(y,"market_pick",float(next_pick)+20)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",float(next_pick)+20)
    out=pd.Series(0.0,index=y.index,dtype=float)
    for p in pos.unique():
        pm=pos.eq(p)
        soon=((market[pm]>=float(current_pick)) & (market[pm]<float(next_pick))).sum()
        depth=min(int(pm.sum()),10)
        out.loc[pm]=float(np.clip(soon/max(depth,1),0,1))*4.0
    return out


def _single_authority_strategy(y,roster,slots,round_no,current_pick,next_pick):
    """All roster/market strategy enters here, after base player value."""
    z=_base_player_value_engine(y)
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    room=_room_position_pressure(z,current_pick,next_pick)

    z["marginal_slot_value"]=0.0
    z["wait_cost"]=0.0
    z["survival_probability"]=0.0
    z["room_pressure"]=room
    z["strategic_pick_value"]=-1e9
    _cross_slot=np.clip(_safe_num_series(z,"value_over_next_roster_slot",0.0),-8.0,8.0)
    z["cross_slot_value"]=_cross_slot
    _market_raw=_safe_num_series(z,"market_pick",float(current_pick)+12.0)
    _model_market=pd.to_numeric(z["model_rank"],errors="coerce").fillna(_market_raw) if "model_rank" in z.columns else _market_raw.copy()
    _offense=~z["position"].astype(str).isin(["DL","DB","K"])
    _market=_market_raw.copy()
    _market.loc[_offense]=0.90*_market_raw.loc[_offense]+0.10*_model_market.loc[_offense]
    _reach_ahead=np.maximum(_market-float(current_pick)-6.0,0.0)
    _reach_cost=np.minimum(_reach_ahead,45.0)*0.58
    z["strategic_reach_cost"]=_reach_cost
    _ropp=_safe_num_series(z,"roster_opportunity_adj",0.0)
    _late_factor=0.0 if int(round_no)<=10 else min(2.0,0.35*(int(round_no)-10))
    _late_negative_cost=np.maximum(-_ropp-1.0,0.0)*(1.2+_late_factor)
    z["late_roster_opp_cost"]=_late_negative_cost

    # Prospective Draft-Value economics: reward players available at/after market
    # and charge for reaches. This mirrors the benchmark's realized value economics
    # so the optimizer improves the metric rather than learning about it afterward.
    _market_delta=float(current_pick)-_market
    _market_value_component=pd.Series(
        np.where(
            _market_delta>=0.0,
            np.minimum(_market_delta,30.0)*0.28,
            np.maximum(_market_delta,-28.0)*0.68
        ),
        index=z.index,dtype=float
    )
    z["prospective_market_value"]=_market_value_component

    # Direct opportunity-loss estimate. Negative roster opportunity and being
    # inferior to another-position bench use are charged before rollout.
    _cross_loss=np.maximum(-_cross_slot,0.0)
    _opp_loss=np.maximum(-_ropp,0.0)
    _prospective_opp_cost=1.15*_opp_loss + 0.85*_cross_loss
    z["prospective_opportunity_cost"]=_prospective_opp_cost

    # Explicit player-quality anchor used by FINAL PICK.
    _qvorp=_safe_num_series(z,"vorp",0.0).rank(pct=True,method="average")
    _qproj=_safe_num_series(z,"projection",0.0).groupby(z["position"].astype(str)).rank(pct=True,method="average")
    _quality_anchor=10.0*(0.68*_qvorp.fillna(.5)+0.32*_qproj.fillna(.5)-0.50)
    z["final_quality_anchor"]=_quality_anchor

    # Preserve the roster-construction work produced by prepare_user_draft_candidates.
    _construction_context=np.clip(_safe_num_series(z,"_construction_bonus",0.0),-30.0,18.0)
    z["final_construction_context"]=_construction_context

    # V6.8 adaptive portfolio regret. This is deliberately soft: it never blocks
    # a position. It simply makes the next redundant bench slot pay for the
    # opportunity it consumes, allowing a truly superior RB5/WR5/QB2/TE2 to win.
    def _portfolio_regret_for_pos(_p):
        _p=str(_p); _have=int(counts.get(_p,0))
        if _p in ("RB","WR"):
            _other="WR" if _p=="RB" else "RB"
            if _have < 4:
                return 0.0
            _pen=2.25 + 1.65*max(_have-4,0)
            if int(counts.get(_other,0)) <= 3:
                _pen += 1.25
            return float(_pen)
        if _p=="QB" and _have>=1:
            return 2.2 if int(round_no)<=11 else 1.0
        if _p=="TE" and _have>=1:
            return 2.0 if int(round_no)<=11 else 0.9
        if _p in ("DL","DB") and (int(counts.get("DL",0))+int(counts.get("DB",0)))>=2:
            return 1.0
        return 0.0
    z["portfolio_regret_cost"]=z["position"].map(_portfolio_regret_for_pos).astype(float)

    # Candidate pool: best overall plus best at every position.
    keep=set(z.nlargest(min(15,len(z)),"base_player_value").index)
    for p in z["position"].astype(str).unique():
        pm=z["position"].astype(str).eq(p)
        keep.update(z.loc[pm].nlargest(min(3,int(pm.sum())),"base_player_value").index)
    z["single_authority_shortlist"]=z.index.isin(keep)

    for idx in keep:
        p=str(z.at[idx,"position"])
        marginal=_marginal_slot_value(p,counts,slots)
        wait,survive=_survival_wait_cost(z,idx,current_pick,next_pick)

        # IDP extras receive no special bonus. Required DL/DB receive ordinary starter value.
        idp_total=int(counts.get("DL",0))+int(counts.get("DB",0))
        idp_pen=0.0
        if p in ("DL","DB") and idp_total>=3:
            idp_pen=100.0  # roster-size guard only

        z.at[idx,"marginal_slot_value"]=marginal
        z.at[idx,"wait_cost"]=wait
        z.at[idx,"survival_probability"]=survive
        z.at[idx,"strategic_pick_value"]=(
            float(z.at[idx,"base_player_value"])+
            2.0*marginal+
            1.35*wait+
            float(room.loc[idx])+
            1.70*float(_cross_slot.loc[idx])+
            1.15*float(_quality_anchor.loc[idx])+
            0.45*float(_construction_context.loc[idx])+
            float(_market_value_component.loc[idx])-
            float(_reach_cost.loc[idx])-
            float(_late_negative_cost.loc[idx])-
            float(_prospective_opp_cost.loc[idx])-
            float(z.at[idx,"portfolio_regret_cost"])-
            idp_pen
        )
    return z


def _branch_future_value(y,counts,slots,from_pick,to_pick,excluded,rng):
    """One lightweight stochastic future-board branch; vectorized for benchmark speed."""
    q=y.drop(index=list(excluded),errors="ignore")
    if q.empty:
        return 0.0,None

    market=_safe_num_series(q,"market_pick",float(to_pick)+20).to_numpy(dtype=float)
    if "market_pick" not in q.columns and "consensus_rank" in q.columns:
        market=_safe_num_series(q,"consensus_rank",float(to_pick)+20).to_numpy(dtype=float)
    base=_safe_num_series(q,"base_player_value",0.0).to_numpy(dtype=float)

    # Exact same logistic survival equation as _market_survival_probability, vectorized.
    margin=market-float(to_pick)
    probs=1.0/(1.0+np.exp(-margin/6.0))
    alive=rng.random(len(q)) < probs
    if not alive.any():
        alive[int(np.nanargmax(probs))]=True

    positions=q["position"].astype(str).to_numpy()
    unique_pos=np.unique(positions)
    marginal_map={p:2.0*_marginal_slot_value(p,counts,slots) for p in unique_pos}
    marginal=np.fromiter((marginal_map[p] for p in positions),dtype=float,count=len(positions))

    utility=base+marginal
    utility=np.where(alive,utility,-1e9)
    j=int(np.nanargmax(utility))
    return float(utility[j]),q.index[j]



def _multi_branch_rollout(y,idx,roster,slots,current_pick,next_pick,branches=10):
    """10 plausible board continuations through the next two user turns."""
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    p=str(y.at[idx,"position"])
    counts=dict(counts); counts[p]=int(counts.get(p,0))+1
    gap=max(int(next_pick)-int(current_pick),1)
    next2=int(next_pick)+gap
    rng=np.random.default_rng(9000+int(current_pick)*17+int(idx)%997)
    vals=[]
    for _ in range(int(branches)):
        v1,j1=_branch_future_value(y,counts,slots,current_pick,next_pick,[idx],rng)
        c2=dict(counts); ex=[idx]
        if j1 is not None:
            p2=str(y.at[j1,"position"]); c2[p2]=int(c2.get(p2,0))+1; ex.append(j1)
        v2,_=_branch_future_value(y,c2,slots,next_pick,next2,ex,rng)
        vals.append(.34*v1+.20*v2)
    return float(np.mean(vals)) if vals else 0.0


def _v610_take_now_wait_score(y, idx, current_pick, next_pick):
    """Expected advantage of taking a player now instead of waiting one turn.

    Positive = take-now urgency. Negative = value is likely replaceable/waitable.
    Uses market survival plus same-position replacement value, so this is a
    forward-looking decision term rather than a generic reach penalty.
    """
    if next_pick is None or int(next_pick) <= int(current_pick):
        return 0.0
    # V6.11 snake-turn correctness: when our next selection is immediately
    # adjacent, no opponent can take the player between our two picks. Do not
    # manufacture take-now urgency from stale market ADP in that zero-opponent gap.
    if int(next_pick)-int(current_pick) <= 1:
        return 0.0
    market=_safe_num_series(y,"market_pick",float(next_pick)+20.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",float(next_pick)+20.0)
    survive=_market_survival_probability(float(market.loc[idx]),current_pick,next_pick)
    mine=float(y.at[idx,"base_player_value"]) if "base_player_value" in y.columns else float(_safe_num_series(y,"unified_pick_score",0.0).loc[idx])
    pool=y[y["position"].astype(str).eq(str(y.at[idx,"position"]))].drop(index=idx,errors="ignore")
    if len(pool):
        pv=_safe_num_series(pool,"base_player_value",0.0)
        repl=float(pv.max())
    else:
        repl=max(mine-10.0,0.0)
    replacement_drop=max(mine-repl,0.0)
    # If likely gone, lock in the unique value. If likely to survive, waiting has value.
    urgency=(1.0-survive)*(1.6+0.85*replacement_drop)
    wait_credit=survive*min(max(float(market.loc[idx])-float(current_pick),0.0),30.0)*0.055
    # Onesie positions are especially costly to reach on when the market projects
    # survival to our next turn; preserve capital for RB/WR/FLEX value instead.
    p=str(y.at[idx,"position"])
    onesie_wait=0.0
    if p in ("QB","TE") and float(market.loc[idx]) >= float(next_pick)-2.0:
        onesie_wait=2.4*survive
    return float(np.clip(urgency-wait_credit-onesie_wait,-4.0,8.0))


def _v610_dynamic_bench_competition(y, idx, roster, slots):
    """Make every optional bench slot compete across positions on usable value."""
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    p=str(y.at[idx,"position"])
    have=int(counts.get(p,0)); need=int(slots.get(p,0))
    # Required starters are handled by construction/lineup logic, not bench competition.
    is_optional=have>=need
    if p in ("RB","WR","TE"):
        skill_have=sum(int(counts.get(q,0)) for q in ("RB","WR","TE"))
        skill_need=sum(int(slots.get(q,0)) for q in ("RB","WR","TE"))+int(slots.get("FLEX",0))
        if skill_have < skill_need:
            is_optional=False
    if not is_optional:
        return 0.0

    mrv=_safe_num_series(y,"marginal_roster_value",0.0)
    cross=_safe_num_series(y,"cross_position_bench_value",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    mine=0.58*float(mrv.loc[idx])+0.27*float(cross.loc[idx])+0.15*float(vorp.loc[idx])
    optional=[]
    for j in y.index:
        q=str(y.at[j,"position"]); qhave=int(counts.get(q,0)); qneed=int(slots.get(q,0))
        qopt=qhave>=qneed
        if q in ("RB","WR","TE"):
            sh=sum(int(counts.get(k,0)) for k in ("RB","WR","TE"))
            sn=sum(int(slots.get(k,0)) for k in ("RB","WR","TE"))+int(slots.get("FLEX",0))
            if sh < sn: qopt=False
        if qopt:
            optional.append(0.58*float(mrv.loc[j])+0.27*float(cross.loc[j])+0.15*float(vorp.loc[j]))
    best=max(optional) if optional else mine
    gap=mine-best
    # Reward the best optional use; punish redundant depth that loses clearly.
    return float(np.clip(0.75*gap,-6.0,3.0))


def _v610_roster_regret_audit(roster, slots):
    """Post-draft harmful-decision audit used by certification/champion scoring."""
    if roster is None or len(roster)==0:
        return {"harmful_regret_count":99,"major_reach_count":99,"early_backup_count":99,"starter_vorp":0.0,"bench_upside":0.0}
    r=roster.copy()
    for c in ["vorp","projection","consensus_rank","mock_pick","marginal_roster_value"]:
        if c not in r.columns: r[c]=np.nan
        r[c]=pd.to_numeric(r[c],errors="coerce")
    reaches=(r["consensus_rank"]-r["mock_pick"]).fillna(0.0)
    raw_major=int((reaches>24).sum())
    if "avoidable_reach" in r.columns:
        avoid=r["avoidable_reach"].fillna(False).astype(bool)
    else:
        avoid=pd.Series(True,index=r.index,dtype=bool)
    major=int(((reaches>24) & avoid).sum())
    harmful=int(((reaches>18) & avoid & (r["vorp"].fillna(0)<2.0)).sum())
    early_backup=0
    for p in ("QB","TE"):
        q=r[r.position.astype(str).eq(p)].sort_values("mock_pick")
        if len(q)>=2 and float(q.iloc[1]["mock_pick"])<120:
            early_backup+=1; harmful+=1
    req={"QB":int(slots.get("QB",1)),"RB":int(slots.get("RB",2)),"WR":int(slots.get("WR",2)),"TE":int(slots.get("TE",1)),"K":int(slots.get("K",1)),"DL":int(slots.get("DL",1)),"DB":int(slots.get("DB",1))}
    used=set(); starter_vorp=0.0
    for p,n in req.items():
        if n<=0: continue
        idx=r[r.position.astype(str).eq(p)]["vorp"].fillna(0).nlargest(n).index
        used.update(idx.tolist()); starter_vorp+=float(r.loc[idx,"vorp"].fillna(0).sum())
    flex_pool=r.loc[~r.index.isin(used) & r.position.astype(str).isin(["RB","WR","TE"]),"vorp"].fillna(0)
    flex_n=int(slots.get("FLEX",0)); flex_idx=flex_pool.nlargest(flex_n).index
    used.update(flex_idx.tolist()); starter_vorp+=float(r.loc[flex_idx,"vorp"].fillna(0).sum())
    bench=r.loc[~r.index.isin(used)].copy()
    bench_upside=float(np.clip(bench["vorp"].fillna(0).clip(-2,10).sum(),-10,60))
    return {"harmful_regret_count":int(harmful),"major_reach_count":int(major),"raw_major_reach_count":int(raw_major),"early_backup_count":int(early_backup),"starter_vorp":float(starter_vorp),"bench_upside":bench_upside}


def _v610_champion_score(result):
    """Multi-objective promotion score. Legality/construction are non-negotiable."""
    if not bool(result.get("legal_roster",False)) or float(result.get("construction",0))<99.999:
        return -1000.0
    return float(
        0.28*float(result.get("model_edge",0))+
        0.25*float(result.get("draft_value",0))+
        0.20*float(result.get("positional_advantage",0))+
        0.12*float(result.get("grade",0))+
        0.08*min(float(result.get("starter_vorp",0)),70.0)+
        0.03*min(float(result.get("bench_upside",0)),30.0)-
        1.10*float(result.get("opportunity_penalty",0))-
        1.75*float(result.get("harmful_regret_count",0))-
        0.75*float(result.get("major_reach_count",0))
    )


def _single_authority_final(y,roster,slots,round_no,current_pick,next_pick,compute_stability=True,rollout_branches=10):
    """
    Single source of truth:
    Base Player Value -> Strategic Pick Value -> 10-branch rollout
    -> regret/challenger test -> FINAL PICK.
    """
    z=_single_authority_strategy(y,roster,slots,int(round_no),current_pick,next_pick)
    contenders=z[z["single_authority_shortlist"]].nlargest(min(5,int(z["single_authority_shortlist"].sum())),"strategic_pick_value").index

    z["rollout_value"]=0.0
    z["final_pick_value"]=z["strategic_pick_value"]
    for idx in contenders:
        rv=_multi_branch_rollout(z,idx,roster,slots,current_pick,next_pick,branches=max(int(rollout_branches),1))
        z.at[idx,"rollout_value"]=rv
        z.at[idx,"final_pick_value"]=float(z.at[idx,"strategic_pick_value"])+rv

    # V6.8 Tested Regret Winner: regret now changes FINAL PICK. For each serious
    # candidate, measure the value package sacrificed at another position when
    # that challenger is unlikely to survive the turn. This prevents rollout/timing
    # from selecting redundant depth unless the player advantage really clears it.
    z["challenger_regret_cost"]=0.0
    z["take_now_wait_component"]=0.0
    z["dynamic_bench_component"]=0.0
    _short=z["single_authority_shortlist"].fillna(False).astype(bool)
    _mrv=_safe_num_series(z,"marginal_roster_value",0.0)
    _vorp=_safe_num_series(z,"vorp",0.0)
    _ropp2=_safe_num_series(z,"roster_opportunity_adj",0.0)
    _market2=_safe_num_series(z,"market_pick",float(current_pick)+20.0)
    for _idx in list(z.index[_short]):
        _p=str(z.at[_idx,"position"])
        _alts=_short & (~z["position"].astype(str).eq(_p))
        if not bool(_alts.any()):
            continue
        _alt_idx=z.loc[_alts,"strategic_pick_value"].idxmax()
        _mrv_gap=max(float(_mrv.loc[_alt_idx]-_mrv.loc[_idx]),0.0)
        _vorp_gap=max(float(_vorp.loc[_alt_idx]-_vorp.loc[_idx]),0.0)
        _ropp_gap=max(float(_ropp2.loc[_alt_idx]-_ropp2.loc[_idx]),0.0)
        _alt_survive=_market_survival_probability(float(_market2.loc[_alt_idx]),current_pick,next_pick)
        _urgency=0.35+0.65*(1.0-float(_alt_survive))
        _depth_mult=1.0
        _have=int((roster.position.astype(str)==_p).sum()) if roster is not None and len(roster) else 0
        if _p in ("RB","WR") and _have>=4: _depth_mult=1.35
        elif _p in ("QB","TE") and _have>=1: _depth_mult=1.15
        _cost=_depth_mult*_urgency*(0.70*_mrv_gap+0.45*_vorp_gap+0.30*_ropp_gap)
        z.at[_idx,"challenger_regret_cost"]=float(np.clip(_cost,0.0,12.0))
        z.at[_idx,"take_now_wait_component"]=_v610_take_now_wait_score(z,_idx,current_pick,next_pick)
        z.at[_idx,"dynamic_bench_component"]=_v610_dynamic_bench_competition(z,_idx,roster,slots)
    z.loc[_short,"final_pick_value"]=(
        z.loc[_short,"final_pick_value"]
        - z.loc[_short,"challenger_regret_cost"]
        + 0.35*z.loc[_short,"take_now_wait_component"]
        + 0.30*z.loc[_short,"dynamic_bench_component"]
    )

    ranked=z.loc[_short,"final_pick_value"].sort_values(ascending=False)
    gap=float(ranked.iloc[0]-ranked.iloc[1]) if len(ranked)>=2 else 10.0
    z["expected_regret"]=0.0
    if len(ranked):
        best=float(ranked.iloc[0])
        z.loc[ranked.index,"expected_regret"]=best-z.loc[ranked.index,"final_pick_value"]

    # Stability uses the same final authority.
    finalists=list(contenders)
    if compute_stability:
        stability=_candidate_stability(z,finalists,trials=24)
        lead_stab=float(stability.loc[ranked.index[0]]) if len(ranked) else 0.0
    else:
        # Stability only changes displayed confidence; it never changes FINAL PICK.
        stability=pd.Series(0.0,index=z.index,dtype=float)
        lead_stab=0.0
    z["candidate_stability"]=stability
    z["challenger_gap"]=gap
    z["recommendation_confidence"]=float(np.clip(42.0+4.5*gap+35.0*lead_stab,45,99))
    return z


def v939_shared_candidate_rank(avail, roster, round_no, current_pick, next_pick, slots, randomness=6):
    """One authoritative scoring pipeline for Draft Mode and Mock Draft Lab."""
    # On the user's final draft turn there is no future snake pick. Normalize None
    # to the current pick so wait/survival urgency becomes effectively neutral.
    if next_pick is None:
        next_pick=int(current_pick)
    else:
        next_pick=int(next_pick)
    x=avail.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}

    # Compute IDP evidence first so all downstream gates can use it.
    _idp_mask=x["position"].astype(str).str.upper().isin(["DL","DB"])
    _reuse_sim_idp=(
        "_sim_precomputed_idp" in x.columns and
        bool(x["_sim_precomputed_idp"].fillna(False).astype(bool).all()) and
        all(_c in x.columns for _c in ["idp_impact_score","idp_external_rank","idp_eligible","idp_quality_tier"])
    )
    if not _reuse_sim_idp:
        x["idp_impact_score"]=np.nan
        x["idp_external_rank"]=np.nan
        x["idp_eligible"]=pd.Series(pd.NA,index=x.index,dtype="boolean")
    else:
        x["idp_eligible"]=x["idp_eligible"].fillna(False).astype("boolean")
    x["roster_completion_blocked"]=False
    x["extra_idp_blocked"]=False
    x["deep_offense_blocked_for_idp"]=False
    x["bench_diversification_blocked"]=False
    x["extra_idp_opportunity_loss"]=False

    if _idp_mask.any() and not _reuse_sim_idp:
        _idp_rows=x.loc[_idp_mask]
        _idp_scores=_idp_rows.apply(_v935_idp_impact_score,axis=1)
        x.loc[_idp_mask,"idp_impact_score"]=[v[0] for v in _idp_scores]
        x.loc[_idp_mask,"idp_eligible"]=pd.Series(
            [bool(v[1]) for v in _idp_scores],
            index=_idp_rows.index,dtype="boolean"
        )
        x.loc[_idp_mask,"idp_external_rank"]=_idp_rows.apply(_v936_external_idp_rank,axis=1)
    _overlay=x.get("id",pd.Series("",index=x.index)).astype(str).str.match(r"^v9\d+:")
    _er=pd.to_numeric(x["idp_external_rank"],errors="coerce")
    _fb=((_overlay & x["position"].eq("DL") & _er.notna() & (_er<=15)) |
         (_overlay & x["position"].eq("DB") & _er.notna() & (_er<=20)))
    x.loc[_fb,"idp_eligible"]=pd.Series(True,index=x.index[_fb],dtype="boolean")
    _floor=np.where(x["position"].eq("DL"),np.maximum(5.5,16.0-_er*0.60),np.maximum(5.0,14.0-_er*0.42))
    _cur=pd.to_numeric(x["idp_impact_score"],errors="coerce").fillna(0)
    x.loc[_fb,"idp_impact_score"]=np.maximum(_cur[_fb],_floor[_fb])
    x["idp_consensus_fallback"]=_fb
    if not _reuse_sim_idp:
        x["idp_quality_tier"]=np.nan
        x["idp_quality_evidence"]=np.nan
        if _idp_mask.any():
            _q=x.loc[_idp_mask].apply(_v941_idp_quality,axis=1)
            x.loc[_idp_mask,"idp_quality_tier"]=[v[0] for v in _q]
            x.loc[_idp_mask,"idp_quality_evidence"]=[v[1] for v in _q]
    elif "idp_quality_evidence" not in x.columns:
        x["idp_quality_evidence"]=np.nan

    # IDP quality is computed above. Extra-IDP timing is decided only by the
    # two-stage opportunity/rollout optimizer below; no pre-score IDP bonus is applied here.
    x=v9_live_rank(x,int(round_no),int(current_pick),counts)
    x["evaluation_score"]=pd.to_numeric(x["v9_live_score"],errors="coerce").fillna(-1e9)
    x["evaluation_score"]-=_safe_num_series(x,"injury_penalty",0.0)

    # Stage-1 player evaluation stays roster-agnostic.
    # Roster construction, saturation and cross-position opportunity are handled
    # only by the final two-stage optimizer below.

    x=roster_opportunity_adjustment(x,roster,int(round_no),int(current_pick),slots)
    # Do not inject roster opportunity into Stage-1 player quality.
    x=apply_v931_idp_opportunity_gate(x,roster,int(round_no))
    x=apply_v932_exact_league_construction(x,roster,int(round_no),exact_roster_rounds(slots),slots)

    # Hard roster-completion authority. This is the final safety layer used by
    # both Live Draft and Mock Draft Lab.
    _rounds=exact_roster_rounds(slots)
    _counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _min_now,_,_=_minimum_required_picks_remaining(_counts,slots)
    _picks_left=int(_rounds)-int(round_no)+1

    if _min_now>0:
        _after_min=[]
        for _p in x["position"].astype(str):
            _after=dict(_counts)
            _after[_p]=int(_after.get(_p,0))+1
            _m,_,_=_minimum_required_picks_remaining(_after,slots)
            _after_min.append(_m)
        x["minimum_required_after_pick"]=_after_min

        _remaining_after=max(int(_rounds)-int(round_no),0)
        _strands=pd.to_numeric(x["minimum_required_after_pick"],errors="coerce")>_remaining_after
        x.loc[_strands,"evaluation_score"]-=5000.0
        x.loc[_strands,"roster_completion_blocked"]=True

        if _picks_left<=_min_now:
            _does_not_reduce=pd.to_numeric(x["minimum_required_after_pick"],errors="coerce")>=_min_now
            x.loc[_does_not_reduce,"evaluation_score"]-=5000.0
            x.loc[_does_not_reduce,"roster_completion_blocked"]=True

    # Deep-offense vs impact-IDP competition is handled continuously by the
    # final opportunity optimizer; no non-legality hard block is applied here.

    # V6.9 cost-aware same-position Pareto dominance.
    # Quality authority must not hard-block a cheaper market option merely because
    # a slightly better player exists 15-25 picks later. A player is hard-dominated
    # only when the superior same-position alternative is also similarly priced.
    _proj_all=pd.to_numeric(x.get("projection",np.nan),errors="coerce")
    _vorp_all=pd.to_numeric(x.get("vorp",np.nan),errors="coerce")
    _market_all=_safe_num_series(x,"market_pick",999.0)
    if "market_pick" not in x.columns and "consensus_rank" in x.columns:
        _market_all=_safe_num_series(x,"consensus_rank",999.0)
    x["same_pos_dominated"]=False
    x["same_pos_soft_dominated"]=False
    x["same_pos_quality_gap"]=0.0

    for _p in ("QB","RB","WR","TE"):
        _idxp=list(x.index[x["position"].eq(_p)])
        if len(_idxp)<2:
            continue
        for _i in _idxp:
            _pi=float(_proj_all.loc[_i]) if pd.notna(_proj_all.loc[_i]) else -np.inf
            _vi=float(_vorp_all.loc[_i]) if pd.notna(_vorp_all.loc[_i]) else -np.inf
            _mi=float(_market_all.loc[_i]) if pd.notna(_market_all.loc[_i]) else 999.0
            _others=[j for j in _idxp if j!=_i]
            _dom=[]
            for _j in _others:
                _pj=float(_proj_all.loc[_j]) if pd.notna(_proj_all.loc[_j]) else -np.inf
                _vj=float(_vorp_all.loc[_j]) if pd.notna(_vorp_all.loc[_j]) else -np.inf
                if (_pj>=_pi and _vj>=_vi and ((_pj-_pi)>=0.20 or (_vj-_vi)>=0.20)):
                    _dom.append(_j)
            if not _dom:
                continue
            _best=max(_dom,key=lambda j:(float(_vorp_all.loc[j])+0.4*float(_proj_all.loc[j])))
            _gap=max(0.0,float(_proj_all.loc[_best])-_pi)*1.5 + max(0.0,float(_vorp_all.loc[_best])-_vi)*2.5
            x.at[_i,"same_pos_quality_gap"]=_gap
            _dm=float(_market_all.loc[_best]) if pd.notna(_market_all.loc[_best]) else 999.0
            if _dm <= _mi + 8.0:
                x.at[_i,"same_pos_dominated"]=True
                x.at[_i,"evaluation_score"]-=min(40.0,8.0+2.0*_gap)
            else:
                # Dominator is materially more expensive/later: keep the cheaper
                # player eligible and apply only a bounded quality tax.
                x.at[_i,"same_pos_soft_dominated"]=True
                x.at[_i,"evaluation_score"]-=min(6.0,1.25*_gap)

    # v9.50 RB quality authority: among available RBs, projection and VORP carry
    # more weight than ADP/faller noise. This is rank-relative and player-agnostic.
    _rb=x["position"].eq("RB")
    if _rb.any():
        _rp=pd.to_numeric(x.loc[_rb,"projection"],errors="coerce")
        _rv=pd.to_numeric(x.loc[_rb,"vorp"],errors="coerce")
        _proj_pct=_rp.rank(pct=True,method="average")
        _vorp_pct=_rv.rank(pct=True,method="average")
        _rb_quality=(0.42*_proj_pct + 0.58*_vorp_pct)
        x.loc[_rb,"rb_quality_score"]=_rb_quality*100.0
        x.loc[_rb,"evaluation_score"]+=(_rb_quality-0.50)*16.0

    # Negative roster opportunity is an authoritative cost.
    _ropp=_safe_num_series(x,"roster_opportunity_adj",0.0)
    _neg_ropp=_ropp < -3.0
    x.loc[_neg_ropp,"evaluation_score"]-=np.minimum(24.0,(-_ropp[_neg_ropp]-3.0)*1.35)

    # A strongly negative bench-IDP fit is never a FINAL PICK after required DL/DB are filled.
    _idp_counts2=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _both_idp_filled=(
        int(_idp_counts2.get("DL",0))>=int(slots.get("DL",1)) and
        int(_idp_counts2.get("DB",0))>=int(slots.get("DB",1))
    )
    if _both_idp_filled:
        _bad_idp_fit=x["position"].isin(["DL","DB"]) & (_ropp<-5.0)
        x.loc[_bad_idp_fit,"evaluation_score"]-=5000.0

    # v9.45 quality authority: roster/market urgency decides WHEN, not WHO.
    _off=~x["position"].isin(["DL","DB","K"])
    _vorp=pd.to_numeric(x.get("vorp",np.nan),errors="coerce")
    _mr=pd.to_numeric(x.get("model_rank",np.nan),errors="coerce")
    _profile=x.get("profile",pd.Series("",index=x.index)).astype(str).str.lower()
    _bad_off=_off & ((_vorp < 0) | _profile.str.contains("decline",na=False))
    x.loc[_bad_off,"evaluation_score"]-=14.0 + np.minimum(10.0,(-_vorp[_bad_off]).clip(lower=0)*3.0)
    x.loc[_off & (_mr>1000),"evaluation_score"]-=8.0

    # IDP talent is independent of roster urgency: quality controls WHICH DL/DB.
    for _p in ("DL","DB"):
        _pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if _pm.any():
            _impact=pd.to_numeric(x.loc[_pm,"idp_impact_score"],errors="coerce").fillna(-99)
            _ext=pd.to_numeric(x.loc[_pm,"idp_external_rank"],errors="coerce")
            _tier=pd.to_numeric(x.loc[_pm,"idp_quality_tier"],errors="coerce").fillna(5)
            _talent=(0.75*_impact) + (6-_tier)*2.5 + np.where(_ext.notna(),np.maximum(0,25-_ext)*0.18,0)
            x.loc[_pm,"evaluation_score"] += _talent
            x.loc[_pm,"idp_talent_score"] = _talent
            _ordered=x.loc[_pm].copy()
            _ordered["_talent_tmp"]=_talent
            _ordered=_ordered.sort_values(["idp_quality_tier","_talent_tmp"],ascending=[True,False])
            if len(_ordered):
                _best_idx=_ordered.index[0]
                _best_tier=float(pd.to_numeric(pd.Series([_ordered.iloc[0]["idp_quality_tier"]]),errors="coerce").fillna(5).iloc[0])
                _second_tier=float(pd.to_numeric(pd.Series([_ordered.iloc[1]["idp_quality_tier"]]),errors="coerce").fillna(5).iloc[0]) if len(_ordered)>1 else 5.0
                if _best_tier<=2 and _second_tier>_best_tier:
                    x.at[_best_idx,"evaluation_score"]+=5.0
                    x.at[_best_idx,"idp_dropoff_bonus"]=5.0

    # v9.47 strict IDP positional authority.
    # Roster urgency can decide WHEN to draft DL/DB, but cannot make a lower-quality
    # defender beat an available elite defender at the same position.
    x["idp_quality_blocked"]=False
    x["elite_idp_bonus"]=0.0
    x["elite_idp_quota_blocked"]=False
    for _p in ("DL","DB"):
        _pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if not _pm.any():
            continue

        _tiers=pd.to_numeric(x.loc[_pm,"idp_quality_tier"],errors="coerce").fillna(5.0)
        _exts=pd.to_numeric(x.loc[_pm,"idp_external_rank"],errors="coerce")
        _talents=pd.to_numeric(x.loc[_pm,"idp_talent_score"],errors="coerce").fillna(-99.0)

        _best_tier=float(_tiers.min())
        _valid_ext=_exts.dropna()
        _best_ext=float(_valid_ext.min()) if len(_valid_ext) else np.nan
        _best_talent=float(_talents.max())

        # If Tier 1/2 exists, Tier 3+ becomes context only.
        if _best_tier<=2:
            _tier_all=pd.to_numeric(x["idp_quality_tier"],errors="coerce").fillna(5.0)
            _blocked=_pm & (_tier_all>=3)
            x.loc[_blocked,"evaluation_score"]-=1000.0
            x.loc[_blocked,"idp_quality_blocked"]=True

        # Strong elite-rank authority.
        _elite_cut=6 if _p=="DL" else 8
        _rank_gap=5 if _p=="DL" else 7
        if pd.notna(_best_ext) and _best_ext<=_elite_cut:
            _all_ext=pd.to_numeric(x["idp_external_rank"],errors="coerce")
            _all_talent=_safe_num_series(x,"idp_talent_score",-99.0)
            _lower=_pm & _all_ext.notna() & (_all_ext>=_best_ext+_rank_gap) & (_all_talent<_best_talent+6.0)
            x.loc[_lower,"evaluation_score"]-=1000.0
            x.loc[_lower,"idp_quality_blocked"]=True

    # v9.49 elite-IDP quota.
    # Goal: finish the draft with at least ONE elite defender, while still letting
    # value/timing decide whether that elite player is DL or DB.
    _roster_elite=False
    if roster is not None and len(roster):
        _r=roster.copy()
        if "idp_quality_tier" in _r.columns:
            _rt=pd.to_numeric(_r["idp_quality_tier"],errors="coerce")
            _rp=_r["position"].astype(str).str.upper().isin(["DL","DB"])
            _roster_elite=bool((_rp & (_rt<=2)).any())

    _elite_avail=(
        x["position"].isin(["DL","DB"]) &
        x["idp_eligible"].fillna(False).astype(bool) &
        (pd.to_numeric(x["idp_quality_tier"],errors="coerce")<=2)
    )

    if (not _roster_elite) and _elite_avail.any():
        # Escalating value pressure: pursue elite IDP before the final two rounds.
        _elite_bonus=0.0
        if int(round_no)>=10: _elite_bonus=4.0
        if int(round_no)>=12: _elite_bonus=9.0
        if int(round_no)>=14: _elite_bonus=18.0
        x.loc[_elite_avail,"evaluation_score"]+=_elite_bonus
        x.loc[_elite_avail,"elite_idp_bonus"]=_elite_bonus

        # By Round 15, if an elite defender still exists, do not spend the pick on
        # a non-required bench luxury. Required K/TE/DL/DB completion remains exempt.
        if int(round_no)>=15:
            _counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
            _required_open={
                "TE":int(_counts.get("TE",0))<int(slots.get("TE",0)),
                "K":int(_counts.get("K",0))<int(slots.get("K",0)),
                "DL":int(_counts.get("DL",0))<int(slots.get("DL",0)),
                "DB":int(_counts.get("DB",0))<int(slots.get("DB",0)),
            }
            _bench_luxury=~x["position"].isin(["DL","DB"])
            # Exempt any currently unfilled required position.
            for _p,_open in _required_open.items():
                if _open:
                    _bench_luxury &= ~x["position"].eq(_p)
            x.loc[_bench_luxury,"evaluation_score"]-=1000.0
            x.loc[_bench_luxury,"elite_idp_quota_blocked"]=True

    # Fantasy Edge deep-bench competition.
    # Once RB5 or WR6 territory is reached, compare directly against the best remaining
    # eligible impact defender. Deep offense must clearly beat that defender on marginal value.
    # Deep-offense vs extra-IDP competition is owned by the single-authority
    # marginal-slot / strategic-value engine below. The obsolete hard block that
    # depended on marginal_roster_value has been removed so Live/Mock/Simulation
    # do not require a legacy column that is not part of the final authority.

    # Fantasy Edge extra-IDP quality guard.
    # After both required IDP starters are filled, a bench DL/DB must be an actual
    # impact option. Strongly negative roster opportunity cannot be overridden by name/rank.
    _idp_counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _required_idp_filled=(
        int(_idp_counts.get("DL",0))>=int(slots.get("DL",1)) and
        int(_idp_counts.get("DB",0))>=int(slots.get("DB",1))
    )
    if _required_idp_filled:
        _idp_mask_extra=x["position"].isin(["DL","DB"]) & x["idp_eligible"].fillna(False).astype(bool)
        _idp_ropp=_safe_num_series(x,"roster_opportunity_adj",0.0)
        _idp_tier=_safe_num_series(x,"idp_quality_tier",5.0)

        # Backup defender must be Tier 1-2 AND have acceptable roster opportunity.
        _elite_extra_ok=_idp_mask_extra & (_idp_tier<=2) & (_idp_ropp>=-18.0)
        _bad_extra=_idp_mask_extra & (~_elite_extra_ok)
        x.loc[_bad_extra,"evaluation_score"]-=5000.0
        x.loc[_bad_extra,"extra_idp_blocked"]=True

    # Fantasy Edge best-available IDP comparison.
    # Rank DL and DB *within the actually available pool* using the same inputs that drive
    # recommendations, so Brian Branch (or any other defender) must beat other available
    # same-position options rather than winning from a fixed name/rank prior.
    x["idp_available_rank"]=np.nan
    x["idp_available_score"]=np.nan
    x["idp_scarcity_cliff"]=0.0
    x["idp_scarcity_bonus"]=0.0

    for _p in ("DL","DB"):
        _pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if not _pm.any():
            continue

        _impact=pd.to_numeric(x.loc[_pm,"idp_impact_score"],errors="coerce").fillna(0.0)
        _talent=pd.to_numeric(x.loc[_pm,"idp_talent_score"],errors="coerce").fillna(0.0)
        _tier=pd.to_numeric(x.loc[_pm,"idp_quality_tier"],errors="coerce").fillna(5.0)
        _ext=pd.to_numeric(x.loc[_pm,"idp_external_rank"],errors="coerce")
        _proj=pd.to_numeric(x.loc[_pm,"projection"],errors="coerce").fillna(0.0)
        _vorp=pd.to_numeric(x.loc[_pm,"vorp"],errors="coerce").fillna(0.0)

        # Available-player composite:
        # fantasy impact and talent dominate; tier/external rank stabilize sparse rows;
        # projection/VORP provide direct scoring support where present.
        _ext_support=np.where(_ext.notna(),np.maximum(0.0,30.0-_ext)*0.22,0.0)
        _avail_score=(
            0.36*_impact +
            0.30*_talent +
            (6.0-_tier)*1.9 +
            _ext_support +
            0.18*_proj +
            0.45*np.maximum(_vorp,0.0)
        )

        x.loc[_pm,"idp_available_score"]=_avail_score
        x.loc[_pm,"idp_available_rank"]=pd.Series(
            _avail_score,index=x.index[_pm]
        ).rank(method="min",ascending=False)

        # Dynamic same-position scarcity: quantify the cliff from IDP1 to IDP2/3.
        _ranked_scores=pd.Series(_avail_score,index=x.index[_pm]).sort_values(ascending=False)
        if len(_ranked_scores)>=2:
            _cliff=float(_ranked_scores.iloc[0]-_ranked_scores.iloc[1])
        else:
            _cliff=6.0
        _best_idx=_ranked_scores.index[0]
        x.at[_best_idx,"idp_scarcity_cliff"]=_cliff
        if _cliff>=2.5:
            x.at[_best_idx,"evaluation_score"]+=min(8.0,2.0+_cliff*1.25)
            x.at[_best_idx,"idp_scarcity_bonus"]=min(8.0,2.0+_cliff*1.25)

        # Same-position authority: if an available defender trails the best option
        # by a meaningful amount, roster need cannot make him FINAL PICK instead.
        _best=float(np.nanmax(_avail_score))
        _gap=_best-_avail_score
        _clearly_worse=_gap>=4.0
        if np.any(_clearly_worse):
            _bad_idx=x.index[_pm][_clearly_worse]
            x.loc[_bad_idx,"evaluation_score"]-=18.0

        # Top-3 available defenders get a modest positive nudge, preserving timing logic.
        _ranks=pd.to_numeric(x.loc[_pm,"idp_available_rank"],errors="coerce")
        x.loc[_pm & x.index.isin(_ranks.index[_ranks<=3]),"evaluation_score"]+=4.0

    # Evidence authority after all roster construction: ineligible IDPs cannot be FINAL PICK.
    bad=x["position"].isin(["DL","DB"]) & (~x["idp_eligible"].fillna(False).astype(bool))
    x.loc[bad,"evaluation_score"]-=1000.0
    # v9.41 positional-quality dominance.
    # This fixes "last required DL/DB => any positive depth player becomes #1".
    for _p in ("DL","DB"):
        pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if pm.any():
            best_tier=pd.to_numeric(x.loc[pm,"idp_quality_tier"],errors="coerce").min()
            if pd.notna(best_tier):
                worse=pm & (pd.to_numeric(x["idp_quality_tier"],errors="coerce") >= best_tier+2)
                x.loc[worse,"evaluation_score"]-=45.0

    _ropp_final=_safe_num_series(x,"roster_opportunity_adj",0.0)
    _good_fit=x[_ropp_final>=0]
    if len(_good_fit):
        _best_good=float(pd.to_numeric(_good_fit["evaluation_score"],errors="coerce").max())
        _badfit=(_ropp_final<=-5) & (pd.to_numeric(x["evaluation_score"],errors="coerce")<=_best_good+12.0)
        x.loc[_badfit,"evaluation_score"]-=1000.0

    cr=_safe_num_series(x,"market_pick",float(current_pick))
    local,ready,survive=execution_choice(
        x.evaluation_score.to_numpy(float),cr.to_numpy(float),
        int(current_pick),next_pick,int(randomness)
    )
    x["survival_next"]=survive
    x["timing_ready"]=ready
    x["evaluation_rank"]=x.evaluation_score.rank(method="min",ascending=False)

    reach=np.maximum(cr-float(current_pick),0)  # player normally goes later = true reach
    fall=np.maximum(float(current_pick)-cr,0)   # player fell past market = value
    x["true_reach_picks"]=reach
    x["faller_value_picks"]=fall
    x["execution_score"]=x.evaluation_score.copy()

    # If a player is likely to survive, preserve the current pick for a scarcer option.
    x.loc[~x.timing_ready,"execution_score"]-=x.loc[~x.timing_ready,"survival_next"]*np.minimum(reach[~x.timing_ready],36)*.55

    # Hard reach protection: 24+ picks ahead of market needs a major evaluation edge.
    _best_eval=float(pd.to_numeric(x["evaluation_score"],errors="coerce").max()) if len(x) else -1e9
    _big_reach=(reach>=24)
    _insufficient_edge=pd.to_numeric(x["evaluation_score"],errors="coerce") < (_best_eval+4.0)
    x.loc[_big_reach & _insufficient_edge,"execution_score"]-=35.0

    # Falling past market is good, but only a modest timing bonus so late bench names
    # cannot overwhelm marginal roster value.
    x["execution_score"]+=.018*np.minimum(fall,48.0)
    # ------------------------------------------------------------------
    # Unified FINAL PICK layer shared by Live Draft and Interactive Mock.
    # Existing evaluation_score remains the mature player model. This final layer
    # adds transparent roster marginal value, snake-turn urgency and reach cost.
    # ------------------------------------------------------------------
    _uc=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _upos=x["position"].astype(str)

    def _uc_num(name,default=0.0):
        if name in x.columns:
            return pd.to_numeric(x[name],errors="coerce").fillna(float(default))
        return pd.Series(float(default),index=x.index,dtype=float)

    _proj=_uc_num("projection",0.0)
    _vorp=_uc_num("vorp",0.0)
    _eval=_uc_num("evaluation_score",-999.0)
    _market=_uc_num("market_pick",999.0)
    if "market_pick" not in x.columns and "consensus_rank" in x.columns:
        _market=_uc_num("consensus_rank",999.0)

    # Preserve the mature engine as the majority of player value while making
    # projection and VORP explicit enough to prevent unexplained same-position leaps.
    _player_value=0.74*_eval + 0.16*_vorp + 0.10*_proj

    _roster_value=np.zeros(len(x),dtype=float)
    for _p,_default_need in [("QB",1),("RB",2),("WR",2),("TE",1),("K",1),("DL",1),("DB",1)]:
        _have=int(_uc.get(_p,0))
        if _have < int(slots.get(_p,_default_need)):
            _roster_value += np.where(_upos.eq(_p),7.0,0.0)

    _rb=int(_uc.get("RB",0)); _wr=int(_uc.get("WR",0))
    if _rb>=4: _roster_value += np.where(_upos.eq("RB"),-4.0,0.0)
    if _rb>=5: _roster_value += np.where(_upos.eq("RB"),-8.0,0.0)
    if _wr>=5: _roster_value += np.where(_upos.eq("WR"),-6.0,0.0)

    # Snake-turn urgency: candidates unlikely to survive to the user's next turn
    # receive a bounded bonus. This is never a legality override.
    _next_gap=max(int(next_pick)-int(current_pick),1)
    _survival_margin=_market-float(current_pick)
    _next_turn_risk=np.clip((_next_gap-_survival_margin)/max(_next_gap,1),0,1)*6.0

    # Continuous reach cost.
    _reach=np.maximum(_market-float(current_pick),0.0)
    _reach_cost=np.minimum(_reach,48.0)*0.14

    # Controlled IDP portfolio: 1 DL + 1 DB required; third IDP is purely merit-based.
    _idp=_upos.isin(["DL","DB"])
    _idp_total=int(_uc.get("DL",0))+int(_uc.get("DB",0))
    _tier=_uc_num("idp_quality_tier",5.0)
    _impact=_uc_num("idp_impact_score",0.0)
    _eligible=x["idp_eligible"].fillna(False).astype(bool) if "idp_eligible" in x.columns else pd.Series(False,index=x.index)
    _impact_idp=_idp & _eligible & (_tier<=2)
    _idp_marginal=np.zeros(len(x),dtype=float)

    if _idp_total<2:
        _idp_marginal += np.where(_impact_idp,3.5+np.minimum(_impact,15.0)*0.10,0.0)
    elif _idp_total==2 and int(round_no)>=11:
        # Third IDP receives no structural bonus. Quality, scarcity, opportunity cost
        # and rollout value must make it win naturally.
        _idp_marginal += 0.0
    elif _idp_total>=3:
        # Fourth IDP is effectively prohibited for this 17-player roster.
        _idp_marginal += np.where(_idp,-80.0,0.0)

    x["player_value_component"]=_player_value
    x["roster_value_component"]=_roster_value
    x["next_turn_risk_component"]=_next_turn_risk
    x["reach_cost_component"]=_reach_cost
    x["idp_marginal_component"]=_idp_marginal
    x["unified_pick_score"]=_player_value+_roster_value+_next_turn_risk+_idp_marginal-_reach_cost

    # Same-position projection/VORP sanity guard.
    x["same_position_value_guard"]=False
    for _p in x["position"].dropna().astype(str).unique():
        _m=_upos.eq(_p)
        if int(_m.sum())<2:
            continue
        _best_proj=float(_proj[_m].max())
        _best_vorp=float(_vorp[_m].max())
        _dominated=_m & (_proj < _best_proj-1.5) & (_vorp < _best_vorp-1.0)
        if _dominated.any() and (_m & ~_dominated).any():
            _best_good=float(x.loc[_m & ~_dominated,"unified_pick_score"].max())
            _weak=_dominated & (x["unified_pick_score"] < _best_good+4.0)
            x.loc[_weak,"unified_pick_score"]-=8.0
            x.loc[_weak,"same_position_value_guard"]=True

    # Absolute post-pick roster feasibility gate.
    _counts_now=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _remaining_after=max(int(exact_roster_rounds(slots))-int(round_no),0)

    def _min_required_after(_after):
        fixed={p:max(int(slots.get(p,0))-int(_after.get(p,0)),0) for p in ["QB","RB","WR","TE","K","DL","DB"]}
        skill_need=int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+int(slots.get("FLEX",0))
        skill_have=int(_after.get("RB",0))+int(_after.get("WR",0))+int(_after.get("TE",0))
        flex_extra=max(skill_need-skill_have-(fixed["RB"]+fixed["WR"]+fixed["TE"]),0)
        return int(sum(fixed.values())+flex_extra)

    x["post_pick_feasible"]=True
    for _p in ["QB","RB","WR","TE","K","DL","DB"]:
        _pm=x["position"].astype(str).eq(_p)
        if _pm.any():
            _after=dict(_counts_now); _after[_p]=int(_after.get(_p,0))+1
            if _min_required_after(_after)>_remaining_after:
                x.loc[_pm,"post_pick_feasible"]=False

    if int(_counts_now.get("DL",0))+int(_counts_now.get("DB",0))>=3:
        x.loc[x["position"].isin(["DL","DB"]),"post_pick_feasible"]=False

    # Single authoritative Live/Mock decision engine.
    x=_single_authority_final(
        x,roster,slots,int(round_no),int(current_pick),int(next_pick),
        compute_stability=not _reuse_sim_idp,
        rollout_branches=3 if _reuse_sim_idp else 10
    )

    # FINAL PICK has one authority plus non-negotiable quality/legality gates.
    x["execution_score"]=x["final_pick_value"]
    _hard_block=~x["post_pick_feasible"]
    for _flag in ["roster_completion_blocked","same_pos_dominated","idp_quality_blocked","extra_idp_blocked","deep_skill_hard_cap"]:
        if _flag in x.columns:
            _hard_block |= x[_flag].fillna(False).astype(bool)
    _idp_now=int(_counts_now.get("DL",0))+int(_counts_now.get("DB",0))
    if _idp_now>=3:
        _hard_block |= x["position"].isin(["DL","DB"])
    _mrv=_safe_num_series(x,"marginal_roster_value",0.0)
    _vorp=_safe_num_series(x,"vorp",0.0)
    _proj=_safe_num_series(x,"projection",0.0)
    _ropp=_safe_num_series(x,"roster_opportunity_adj",0.0)

    for _p in ["RB","WR"]:
        _have=int(_counts_now.get(_p,0))
        if _have>=5:
            _pm=x["position"].astype(str).eq(_p) & (~_hard_block)
            _alt=(~x["position"].astype(str).eq(_p)) & (~_hard_block)
            if _pm.any() and _alt.any():
                _best_alt_mrv=float(_mrv[_alt].max())
                _best_alt_vorp=float(_vorp[_alt].max())
                _best_alt_proj=float(_proj[_alt].max())
                _premium=(
                    (_mrv >= _best_alt_mrv+1.25) &
                    ((_vorp >= _best_alt_vorp+0.60) | (_proj >= _best_alt_proj+1.0)) &
                    (_ropp >= -1.5)
                )
                _hard_block |= _pm & (~_premium)

    _minimum_now,_,_=_minimum_required_picks_remaining(_counts_now,slots)
    x["cross_position_dominated"]=False
    if _minimum_now==0:
        _candidate_mask=~_hard_block
        _indices=list(x.index[_candidate_mask])
        for _idx in _indices:
            _others=_candidate_mask.copy()
            _others.loc[_idx]=False
            if not _others.any():
                continue
            _dom=(
                (_mrv[_others] >= float(_mrv.loc[_idx])+1.0) &
                (_vorp[_others] >= float(_vorp.loc[_idx])+0.40) &
                (_proj[_others] >= float(_proj.loc[_idx])+0.50) &
                (_ropp[_others] >= float(_ropp.loc[_idx]))
            )
            if bool(_dom.any()):
                x.at[_idx,"cross_position_dominated"]=True
        _hard_block |= x["cross_position_dominated"].fillna(False).astype(bool)

    if int(round_no)>=11:
        _nonnegative=(~_hard_block) & (_ropp>=0.0)
        if _nonnegative.any():
            _hard_block |= (~_hard_block) & (_ropp<-5.0)

        # V6.14 late optional quality floor: once a position's required starter
        # count is satisfied, do not spend a bench spot on negative VORP when a
        # legal nonnegative-VORP alternative exists. Required completion is exempt.
        _counts_late=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
        _required_pos=pd.Series(False,index=x.index,dtype=bool)
        for _p in ["QB","RB","WR","TE","K","DL","DB"]:
            if int(_counts_late.get(_p,0)) < int(slots.get(_p,0)):
                _required_pos |= x["position"].astype(str).eq(_p)
        _optional=(~_hard_block) & (~_required_pos)
        _good_optional=_optional & (_vorp>=0.0) & (_ropp>=-2.0)
        if _good_optional.any():
            _hard_block |= _optional & (_vorp<0.0)

    # Market-efficient reach guard. Avoid paying 18+ picks ahead of market when
    # another legal candidate has comparable VORP/marginal value and is priced
    # near the current pick. This directly attacks avoidable Draft Value loss.
    _market_final=_safe_num_series(x,"market_pick",float(current_pick)+20.0)
    _reach_gap=_market_final-float(current_pick)
    x["raw_reach_gap"]=_reach_gap
    x["avoidable_reach"]=False
    _legal_now=~_hard_block
    _near_market=_legal_now & (_reach_gap<=12.0)
    if _near_market.any():
        for _idx in list(x.index[_legal_now & (_reach_gap>=13.0)]):
            _similar=(
                _near_market &
                (_vorp >= float(_vorp.loc[_idx])-0.90) &
                (_mrv >= float(_mrv.loc[_idx])-1.75) &
                (_ropp >= float(_ropp.loc[_idx])-1.00)
            )
            if bool(_similar.any()):
                x.at[_idx,"avoidable_reach"]=True
                _hard_block.loc[_idx]=True

    # V6.18 draft-day status guard: DND/IR/NFI-level statuses must be true
    # hard exclusions, not merely a clipped score penalty.
    _injury_exec=_safe_num_series(x,"injury_penalty",0.0)
    _status_hard=_injury_exec>=900.0
    x["status_hard_blocked"]=_status_hard
    _hard_block |= _status_hard

    x["final_quality_blocked"]=_hard_block
    x.loc[_hard_block,"execution_score"]=-1e12

    # Final challenger test: a candidate cannot win on timing/rollout alone when
    # another legal player offers a clearly superior value package.
    _legal_value=~x["final_quality_blocked"]
    _mrv_final=_safe_num_series(x,"marginal_roster_value",0.0)
    _vorp_final=_safe_num_series(x,"vorp",0.0)
    _proj_final=_safe_num_series(x,"projection",0.0)
    _market_final2=_safe_num_series(x,"market_pick",float(current_pick)+20.0)
    _ropp_cmp=_safe_num_series(x,"roster_opportunity_adj",0.0)
    x["value_challenger_blocked"]=False

    _legal_indices=list(x.index[_legal_value])
    for _idx in _legal_indices:
        _others=_legal_value.copy()
        _others.loc[_idx]=False
        if not _others.any():
            continue
        _challenger=(
            _others &
            (_mrv_final >= float(_mrv_final.loc[_idx])+1.5) &
            (_vorp_final >= float(_vorp_final.loc[_idx])+0.5) &
            (_ropp_cmp >= float(_ropp_cmp.loc[_idx])-0.5) &
            (_market_final2 <= float(_market_final2.loc[_idx])+10.0)
        )
        if bool(_challenger.any()):
            x.at[_idx,"value_challenger_blocked"]=True
            x.at[_idx,"execution_score"]-=750.0

    _ropp_final=_safe_num_series(x,"roster_opportunity_adj",0.0)
    _feasible_now=~x["final_quality_blocked"]
    if (_feasible_now & (_ropp_final>=0)).any():
        _luxury_cut=-3.0 if int(round_no)>=11 else -6.0
        _bad_luxury=_feasible_now & (_ropp_final<_luxury_cut)
        x.loc[_bad_luxury,"execution_score"]-=325.0

    x=_v944_add_idp_display_metrics(x)

    return x.sort_values("execution_score",ascending=False), local


def make_board(players, hist, market, ppr, pass_td, idp, teams, slots):
    rows=[]
    for pid,p in players.items():
        rawpos=p.get("position")
        grp=canonical_position(rawpos)
        if grp not in ["QB","RB","WR","TE","K","DL","DB"] or p.get("active") is False: continue
        name=p.get("full_name") or " ".join([p.get("first_name") or "",p.get("last_name") or ""]).strip()
        if not name: continue
        rows.append({"id":str(pid),"player":name,"key":norm(name),"position":grp,"raw_position":rawpos,
                     "team":p.get("team") or "FA","age":p.get("age"),"exp":p.get("years_exp"),
                     "injury":p.get("injury_status")})
    b=pd.DataFrame(rows)
    if b.empty: return b

    if hist.empty:
        b["last_ppg"]=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"K":8.5,"DL":6,"DB":5.5})
        b["prior_ppg"]=b.last_ppg*.9
        for c in ["opp_pg","td_rate_z","eff_z","growth_z","opp_z","idp_vol_z","bigplay_z"]:
            b[c]=0.
    else:
        h=hist.copy()
        if "position_group" not in h.columns:
            h["position_group"]=h["position"].map(position_group)
        yr=int(h.season.max())
        cur=h[h.season.eq(yr)].copy()
        prev=h[h.season.eq(yr-1)][["key","position_group","ppr_ppg"]].rename(columns={"ppr_ppg":"prior_off_ppg"})
        cur=cur.merge(prev,on=["key","position_group"],how="left")

        # Offensive features.
        cur["opp_pg"]=(cur.targets.fillna(0)+cur.carries.fillna(0))/cur.games
        touches=(cur.receptions.fillna(0)+cur.carries.fillna(0)).clip(lower=1)
        cur["td_rate"]=(cur.receiving_tds.fillna(0)+cur.rushing_tds.fillna(0))/touches
        cur["eff"]=(cur.receiving_yards.fillna(0)+cur.rushing_yards.fillna(0))/touches

        # IDP fantasy points using user scoring.
        cur["idp_points"]=(
            cur.def_tackles_solo.fillna(0)*idp["solo"]
            + cur.def_tackles_with_assist.fillna(0)*idp["assist"]
            + cur.def_sacks.fillna(0)*idp["sack"]
            + cur.def_tackles_for_loss.fillna(0)*idp["tfl"]
            + cur.def_qb_hits.fillna(0)*idp["qb_hit"]
            + cur.def_interceptions.fillna(0)*idp["int"]
            + cur.def_pass_defended.fillna(0)*idp["pd"]
            + cur.def_fumbles_forced.fillna(0)*idp["ff"]
            + cur.def_fumble_recovery_opp.fillna(0)*idp["fr"]
            + cur.def_tds.fillna(0)*idp["def_td"]
            + cur.def_safety.fillna(0)*idp["safety"]
        )
        cur["idp_ppg"]=cur.idp_points/cur.games
        cur["idp_volume"]=(cur.def_tackles_solo.fillna(0)+cur.def_tackles_with_assist.fillna(0)+
                           cur.def_sacks.fillna(0)*2+cur.def_pass_defended.fillna(0))/cur.games
        cur["bigplay_rate"]=(cur.def_sacks.fillna(0)+cur.def_interceptions.fillna(0)+
                             cur.def_fumbles_forced.fillna(0)+cur.def_tds.fillna(0))/cur.games

        # Prior IDP season from raw h.
        prv=h[h.season.eq(yr-1)].copy()
        prv["prior_idp_points"]=(
            prv.def_tackles_solo.fillna(0)*idp["solo"] + prv.def_tackles_with_assist.fillna(0)*idp["assist"]
            + prv.def_sacks.fillna(0)*idp["sack"] + prv.def_tackles_for_loss.fillna(0)*idp["tfl"]
            + prv.def_qb_hits.fillna(0)*idp["qb_hit"] + prv.def_interceptions.fillna(0)*idp["int"]
            + prv.def_pass_defended.fillna(0)*idp["pd"] + prv.def_fumbles_forced.fillna(0)*idp["ff"]
            + prv.def_fumble_recovery_opp.fillna(0)*idp["fr"] + prv.def_tds.fillna(0)*idp["def_td"]
            + prv.def_safety.fillna(0)*idp["safety"]
        )
        prv["prior_idp_ppg"]=prv.prior_idp_points/prv.games
        if "position_group" not in prv.columns:
            prv["position_group"]=prv["position"].map(position_group)
        cur=cur.merge(prv[["key","position_group","prior_idp_ppg"]],on=["key","position_group"],how="left")

        cur["last_ppg"]=np.where(cur.position.isin(["DL","DB"]),cur.idp_ppg,cur.ppr_ppg)
        cur["prior_ppg"]=np.where(cur.position.isin(["DL","DB"]),cur.prior_idp_ppg,cur.prior_off_ppg)
        cur["prior_ppg"]=pd.to_numeric(cur["prior_ppg"],errors="coerce")
        cur["prior_ppg"]=cur.prior_ppg.fillna(cur.last_ppg*.88)
        cur["growth"]=cur.last_ppg-cur.prior_ppg

        for c in ["td_rate","eff","growth","opp_pg","idp_volume","bigplay_rate"]:
            sd=cur[c].std()
            cur[c+"_z"]=(cur[c]-cur[c].median())/(sd if pd.notna(sd) and sd else 1)

        keep=["key","position_group","last_ppg","prior_ppg","opp_pg","td_rate_z","eff_z","growth_z","opp_pg_z",
              "idp_volume_z","bigplay_rate_z"]
        cur=cur[keep].rename(columns={"opp_pg_z":"opp_z","idp_volume_z":"idp_vol_z","bigplay_rate_z":"bigplay_z"})
        b=b.merge(cur,left_on=["key","position"],right_on=["key","position_group"],how="left")
        b.drop(columns=["position_group"],inplace=True,errors="ignore")

        base=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"K":8.5,"DL":6,"DB":5.5})
        b["last_ppg"]=b.last_ppg.fillna(base)
        b["prior_ppg"]=b.prior_ppg.fillna(b.last_ppg*.9)
        for c in ["opp_pg","td_rate_z","eff_z","growth_z","opp_z","idp_vol_z","bigplay_z"]:
            b[c]=b[c].fillna(0)

    if market is not None and not market.empty:
        b=b.merge(market[["key","consensus_pos","consensus_rank","consensus_page"]],
                  left_on=["key","position"],right_on=["key","consensus_pos"],how="left")
        b.drop(columns=["consensus_pos"],inplace=True,errors="ignore")
    else:
        b["consensus_rank"]=np.nan
        b["consensus_page"]=""

    b["age"]=pd.to_numeric(b.age,errors="coerce")
    b["exp"]=pd.to_numeric(b.exp,errors="coerce").fillna(0)
    young=np.select([b.age<=22,b.age<=24,b.age<=26,b.age<=29],[16,12,7,2],default=-5)
    early=np.select([b.exp<=1,b.exp<=2,b.exp<=4],[10,7,3],default=0)

    is_idp=b.position.isin(["DL","DB"])
    # Offensive progression/regression.
    b["progression"]=50+b.growth_z*14+b.opp_z*11+young+early
    b["regression"]=50+b.td_rate_z*18+b.eff_z*10-b.opp_z*12
    # IDP: tackle/pressure volume is more repeatable; big-play spikes are more regression-prone.
    b.loc[is_idp,"progression"]=50+b.loc[is_idp,"growth_z"]*12+b.loc[is_idp,"idp_vol_z"]*15+young[is_idp]+early[is_idp]
    b.loc[is_idp,"regression"]=50+b.loc[is_idp,"bigplay_z"]*20-b.loc[is_idp,"idp_vol_z"]*12

    b["breakout"]=1/(1+np.exp(-(b.progression-55)/13))
    b["decline"]=1/(1+np.exp(-(b.regression-60)/12))

    # "Breakout" is reserved for genuinely ascending/early-career players.
    young_breakout=(b.age.fillna(99)<=26) & (b.exp<=4)
    b["profile"]="Stable / neutral"
    b.loc[b.decline>=.68,"profile"]="Decline risk"
    b.loc[(b.decline>=.50)&(b.decline<.68),"profile"]="High variance"
    b.loc[young_breakout & (b.breakout>=.67),"profile"]="Breakout target"
    b.loc[young_breakout & (b.breakout.between(.55,.67, inclusive="left")),"profile"]="Ascending"
    b.loc[(~young_breakout) & (b.breakout>=.65) & (b.decline<.50),"profile"]="Veteran upside"

    base=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"K":8.5,"DL":6,"DB":5.5})
    b["projection"]=(b.last_ppg*.70+b.prior_ppg*.20+base*.10+b.growth_z*.50).clip(lower=1)

    # v9.50 kicker valuation: K has no nflverse fantasy-history feed in this build,
    # so do NOT leave every kicker at the same 8.5 projection.
    # Use the live market ordering already attached to the board as a conservative
    # relative projection proxy. This creates real separation without inventing a
    # player-name whitelist.
    _km=b.position.eq("K")
    if _km.any():
        # make_board has consensus_rank at this stage; market_pick is attached later.
        # Use consensus rank when available and fall back to deterministic row order.
        if "consensus_rank" in b.columns:
            _kmarket=pd.to_numeric(b.loc[_km,"consensus_rank"],errors="coerce")
        else:
            _kmarket=pd.Series(np.nan,index=b.index[_km],dtype=float)

        _fallback=pd.Series(
            np.arange(1,int(_km.sum())+1,dtype=float),
            index=b.index[_km]
        )
        # Missing K consensus values sort behind known market-ranked kickers.
        if _kmarket.notna().any():
            _max_known=float(_kmarket.max())
            _kmarket=_kmarket.fillna(_max_known + _fallback)
        else:
            _kmarket=_fallback

        _krank=_kmarket.rank(method="min",ascending=True,na_option="bottom")
        _kn=max(int(_km.sum()),1)
        _kpct=1.0-((_krank-1.0)/max(_kn-1,1))
        b.loc[_km,"projection"]=7.35 + 2.15*_kpct

    skill=b.position.isin(["RB","WR","TE"])
    b.loc[skill,"projection"] += (ppr-1.0)*np.clip(b.loc[skill,"opp_pg"]*.55,1,8)
    if pass_td!=4:
        qb=b.position.eq("QB"); b.loc[qb,"projection"] += (pass_td-4)*1.5

    b["draft_score"]=b.projection*5+b.progression*.18-b.regression*.12
    b["waiver_score"]=b.projection*4+b.progression*.23-b.regression*.10

    # Value Over Replacement Player (VORP): raw points above a realistic replacement starter.
    flex=float(slots.get("FLEX",0))
    # FLEX demand is distributed mostly to WR/RB in PPR, with a small TE share.
    replacement_slots={
        "QB":max(teams*int(slots.get("QB",1)),teams),
        "RB":max(int(round(teams*(float(slots.get("RB",2))+flex*.38))),teams),
        "WR":max(int(round(teams*(float(slots.get("WR",2))+flex*.55))),teams),
        "TE":max(int(round(teams*(float(slots.get("TE",1))+flex*.07))),teams),
        "K":max(teams*int(slots.get("K",1)),teams),
        "DL":max(teams*int(slots.get("DL",1)),teams),
        "DB":max(teams*int(slots.get("DB",1)),teams)
    }
    repl={}
    for pos,n in replacement_slots.items():
        vals=b.loc[b.position.eq(pos),"projection"].sort_values(ascending=False).reset_index(drop=True)
        idx=min(max(int(n)-1,0),len(vals)-1) if len(vals) else 0
        repl[pos]=float(vals.iloc[idx]) if len(vals) else 0.0
    b["replacement_ppg"]=b.position.map(repl).fillna(0)
    b["vorp"]=b.projection-b.replacement_ppg

    # v9.50: kicker VORP is position-relative, using the 12-team replacement line.
    # This prevents every K from displaying 0.0 VORP.
    _km=b.position.eq("K")
    if _km.any():
        _kvals=pd.to_numeric(b.loc[_km,"projection"],errors="coerce").sort_values(ascending=False)
        _krep_idx=min(max(int(teams)-1,0),len(_kvals)-1)
        _krep=float(_kvals.iloc[_krep_idx]) if len(_kvals) else 7.35
        b.loc[_km,"replacement_ppg"]=_krep
        b.loc[_km,"vorp"]=pd.to_numeric(b.loc[_km,"projection"],errors="coerce")-_krep

    # Pure model score before market consensus: this is where we intentionally disagree with consensus.
    scarcity=b.position.map({"QB":0.0,"RB":0.9,"WR":1.35,"TE":0.35,"K":-1.25,"DL":-0.35,"DB":-0.45}).fillna(0)
    b["pure_model_score"]=b.vorp*9+b.projection*1.6+b.progression*.12-b.regression*.10+scarcity
    b["model_rank"]=b.pure_model_score.rank(method="min",ascending=False)

    # Weekly-updated expert consensus acts as a reality check, not the engine.
    if b.consensus_rank.notna().any():
        maxrank=max(float(b.consensus_rank.max()),250.0)
        b["consensus_strength"]=(100*(1-np.log(b.consensus_rank.clip(lower=1))/np.log(maxrank))).clip(0,100)
    else:
        b["consensus_strength"]=50.0
    b["consensus_strength"]=b.consensus_strength.fillna(45.0)
    b["draft_score"]=b.pure_model_score+b.consensus_strength*.10
    b["consensus_edge"]=b.consensus_rank-b.model_rank

    # Confidence rises when we have history + consensus and falls with current injury flags.
    hist_conf=np.where(b.last_ppg.notna(),.20,0)
    market_conf=np.where(b.consensus_rank.notna(),.20,0)
    injury_pen=np.where(b.injury.fillna("").isin(["Out","IR","PUP"]),.25,0)
    agreement=np.where(b.consensus_rank.notna(), np.clip(1-np.abs(b.consensus_edge)/60,0,1)*.15, .05)
    b["confidence"]=(.40+hist_conf+market_conf+agreement-injury_pen).clip(.30,.95)
    # Stable identity guardrail: keep the canonical Sleeper position attached to each player ID.
    b["position"]=[validate_position(pl,pos) for pl,pos in zip(b.player,b.position)]
    b["identity_key"]=b["id"].astype(str)+"|"+b["position"].astype(str)
    return b.sort_values("draft_score",ascending=False).reset_index(drop=True)


def snake_pick(round_no, slot, teams):
    return (round_no-1)*teams + (slot if round_no % 2 else teams-slot+1)

def next_user_pick(current_overall, slot, teams, rounds):
    picks=[snake_pick(r,slot,teams) for r in range(1,rounds+1)]
    return next((p for p in picks if p>current_overall), None)

def survival_probability(consensus_rank, next_pick, randomness=12):
    if pd.isna(consensus_rank) or next_pick is None:
        return np.nan
    # Smooth probability that a player with consensus rank survives to a future pick.
    scale=max(float(randomness),4.0)
    z=(float(consensus_rank)-float(next_pick))/scale
    return float(1/(1+np.exp(-z)))


def survival_probability_array(market_pick, next_pick, randomness=12):
    """Probability a player remains available until our next snake-draft pick."""
    x=np.asarray(market_pick,dtype=float)
    if next_pick is None:
        return np.zeros_like(x,dtype=float)
    scale=max(float(randomness)*1.15,5.0)
    z=(x-float(next_pick))/scale
    return 1/(1+np.exp(-z))


def late_survival_probability_array_empirical(market_pick, next_pick, slot, round_no):
    """V7.54 challenger-only empirical R11+ survival lookup.

    Frozen from V7.53 calibration. Uses slot + round + market-minus-next-pick band,
    with clipping and simple backoff. This does NOT change the live V7.50 champion.
    """
    x=np.asarray(market_pick,dtype=float)
    if next_pick is None:
        return np.zeros_like(x,dtype=float)

    # Cell values are empirical rates from V7.53, clipped to avoid 0/1 certainty.
    # Keys: (slot, round, band), where band is deep (<-60), mid [-60,-40), other (>=-40).
    cell={
        (1,11,"deep"):.0761,(1,11,"mid"):.2500,
        (1,12,"deep"):.9500,(1,12,"mid"):.9500,
        (1,13,"deep"):.0700,
        (1,14,"mid"):.9500,(1,14,"other"):.9500,

        (3,11,"deep"):.1071,(3,11,"mid"):.2667,
        (3,12,"deep"):.6316,(3,12,"mid"):.7500,(3,12,"other"):.0500,
        (3,13,"deep"):.0800,
        (3,14,"mid"):.9500,

        (7,11,"deep"):.5000,(7,11,"mid"):.4167,
        (7,12,"deep"):.2041,(7,12,"other"):.0500,
        (7,13,"deep"):.2700,
        (7,14,"deep"):.9500,

        (12,11,"mid"):.9500,
        (12,12,"deep"):.0500,
        (12,13,"deep"):.9500,(12,13,"mid"):.9500,
        (12,14,"deep"):.9500,
    }

    # Slot-round backoff from V7.53.
    sr={
        (1,11):.0900,(1,12):.9500,(1,13):.0700,(1,14):.9500,
        (3,11):.1313,(3,12):.6300,(3,13):.0800,(3,14):.9500,
        (7,11):.4200,(7,12):.2020,(7,13):.2700,(7,14):.9500,
        (12,11):.9500,(12,12):.0500,(12,13):.9500,(12,14):.9500,
    }

    # Global distance-band backoff from V7.53.
    gb={"deep":.4191,"mid":.8560,"other":.2500}

    d=x-float(next_pick)
    out=np.zeros_like(x,dtype=float)
    for i,val in enumerate(d):
        if not np.isfinite(val):
            out[i]=.50
            continue
        band="deep" if val < -60 else "mid" if val < -40 else "other"
        key=(int(slot),int(round_no),band)
        if key in cell:
            p=cell[key]
        elif (int(slot),int(round_no)) in sr:
            # Blend slot-round backoff with global distance behavior.
            p=.70*sr[(int(slot),int(round_no))]+.30*gb[band]
        else:
            p=gb[band]
        out[i]=float(np.clip(p,.05,.95))
    return out


def execution_choice_with_survival(eval_score, market_pick, current_pick, next_pick, survival):
    """Same V7.50 execution architecture, but supplied a calibrated survival array."""
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    surv=np.asarray(survival,dtype=float)
    reach=np.maximum(mp-float(current_pick),0)
    fall=np.maximum(float(current_pick)-mp,0)
    ready=(fall>=5) | (reach<6) | (surv<.50) | np.isnan(mp)

    n=min(24,len(ev))
    if n<=0:
        return None,ready,surv
    top=np.argpartition(-ev,n-1)[:n] if n<len(ev) else np.arange(len(ev))
    ready_top=top[ready[top]]
    if len(ready_top):
        j=int(ready_top[np.argmax(ev[ready_top]+.035*fall[ready_top])])
        return j,ready,surv

    timing_cost=surv[top]*np.minimum(reach[top],36.0)*.42
    j=int(top[np.argmax(ev[top]-timing_cost)])
    return j,ready,surv


def market_timing_state(market_pick,current_pick,next_pick,randomness=12):
    """Execution state. Player evaluation is handled separately from pick timing."""
    if pd.isna(market_pick):
        return "DRAFT NOW",np.nan
    mp=float(market_pick); cur=float(current_pick)
    surv=survival_probability(mp,next_pick,randomness)
    if cur-mp >= 5:
        return "VALUE FALLER",surv
    reach=mp-cur
    # If we are meaningfully ahead of market and the target is more likely than not
    # to make it back, preserve the target rather than spending this pick early.
    if next_pick is not None and reach>=6 and pd.notna(surv) and surv>=.50:
        return "WAIT / TARGET NEXT PICK",surv
    return "DRAFT NOW",surv


def execution_choice(eval_score, market_pick, current_pick, next_pick, randomness=12):
    """Choose who to draft NOW without changing the underlying player evaluation.

    The model's favorite players remain model targets. Pick execution selects the
    highest-evaluated target whose market window is open. If every good target is a
    WAIT, it chooses the least-cost early pick instead of blindly reaching for #1.
    """
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    surv=survival_probability_array(mp,next_pick,randomness)
    reach=np.maximum(mp-float(current_pick),0)
    fall=np.maximum(float(current_pick)-mp,0)
    ready=(fall>=5) | (reach<6) | (surv<.50) | np.isnan(mp)
    # Only compare realistic model targets, not the full player universe.
    n=min(24,len(ev))
    if n<=0: return None,ready,surv
    top=np.argpartition(-ev,n-1)[:n] if n<len(ev) else np.arange(len(ev))
    ready_top=top[ready[top]]
    if len(ready_top):
        # Evaluation controls the selection among players whose timing window is open.
        j=int(ready_top[np.argmax(ev[ready_top]+.035*fall[ready_top])])
        return j,ready,surv
    # Emergency fallback: all top targets are early. Pay the smallest timing cost
    # while still respecting model evaluation.
    timing_cost=surv[top]*np.minimum(reach[top],36.0)*.42
    j=int(top[np.argmax(ev[top]-timing_cost)])
    return j,ready,surv


def dynamic_faller_threshold(current_pick, teams=12, rounds=15):
    """Round-aware minimum market fall required for a Faller Intercept.

    Early rounds protect elite model conviction.
    Middle rounds become progressively more willing to harvest market value.
    Late rounds aggressively capture model-compatible fallers.
    """
    teams=max(int(teams),1)
    round_no=max(1,int((int(current_pick)-1)//teams)+1)
    if round_no<=3:
        return 14.0, 12, 8.0   # frozen V7.15 early-round rule
    if round_no<=6:
        # V7.16 surgical mid-round discipline: modestly widen the model-compatible
        # band and lower the fall/improvement thresholds without becoming ADP-led.
        return 9.0, 18, 4.0
    if round_no<=10:
        return 8.0, 18, 4.0    # frozen V7.15 R7-10 rule
    # Frozen V7.15 late-round value harvest.
    return 4.0, 28, 2.0


def early_wr_scarcity_choice(eval_score, market_pick, position_code, current_pick, next_pick, normal_choice, teams=12, randomness=12, max_eval_deficit=10.0, max_wr_survival=.52):
    """R1-3 only: scarce market-priority WR intercept; underlying evaluation stays frozen."""
    ev=np.asarray(eval_score,dtype=float); mp=np.asarray(market_pick,dtype=float); pc=np.asarray(position_code,dtype=int)
    normal=int(normal_choice); rnd=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    diag={"wr_scarcity":False,"wr_survival":np.nan,"eval_deficit":np.nan,"market_advantage":np.nan,"wr_index":None}
    if rnd>3 or next_pick is None or len(ev)==0 or pc[normal]==2: return normal,False,diag
    wr=np.flatnonzero(pc==2)
    if not len(wr): return normal,False,diag
    wi=int(wr[np.argmax(ev[wr])]); deficit=float(ev[normal]-ev[wi])
    wmp=float(mp[wi]) if np.isfinite(mp[wi]) else np.nan; nmp=float(mp[normal]) if np.isfinite(mp[normal]) else np.nan
    surv=survival_probability(wmp,next_pick,randomness) if np.isfinite(wmp) else np.nan
    adv=nmp-wmp if np.isfinite(nmp) and np.isfinite(wmp) else np.nan
    diag.update({"wr_survival":surv,"eval_deficit":deficit,"market_advantage":adv,"wr_index":wi})
    if pd.isna(surv) or surv>max_wr_survival or deficit>max_eval_deficit or pd.isna(adv) or adv<0: return normal,False,diag
    diag["wr_scarcity"]=True
    return wi,True,diag


def late_slot_wr_conflict_choice(eval_score, market_pick, position_code, draft_score, vorp,
                                current_pick, next_pick, normal_choice, draft_slot,
                                teams=12, randomness=12, enabled=False,
                                max_eval_deficit=8.0, max_wr_survival=.35,
                                min_draftscore_advantage=.5, require_vorp_driver=True,
                                eligible_slots=(7,12)):
    """R4-6, Picks 7/12 only: diagnostic WR conflict intercept.

    The live champion never calls this with enabled=True. A calibration variant may
    replace an RB/TE normal choice with the best evaluated WR only when:
    - draft slot is 7 or 12
    - round is 4-6
    - normal choice is RB or TE
    - WR is within a controlled FE evaluation deficit
    - WR has low survival probability to next pick
    - selected RB/TE's player/draft-score advantage is positive
    - VORP contribution to that player-score advantage is positive
    """
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    pc=np.asarray(position_code,dtype=int)
    ds=np.asarray(draft_score,dtype=float)
    vp=np.asarray(vorp,dtype=float)
    normal=int(normal_choice)
    rnd=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)

    diag={
        "ls_wr_intercept":False,"wr_index":None,"eval_deficit":np.nan,
        "wr_survival":np.nan,"draftscore_advantage":np.nan,
        "vorp_component_advantage":np.nan
    }
    if (not enabled) or int(draft_slot) not in list(eligible_slots) or rnd<4 or rnd>6:
        return normal,False,diag
    if normal<0 or normal>=len(ev) or pc[normal] not in [1,3]:
        return normal,False,diag

    wr=np.flatnonzero(pc==2)
    if not len(wr):
        return normal,False,diag

    wi=int(wr[np.argmax(ev[wr])])
    deficit=float(ev[normal]-ev[wi])
    wmp=float(mp[wi]) if np.isfinite(mp[wi]) else np.nan
    surv=survival_probability(wmp,next_pick,randomness) if np.isfinite(wmp) else np.nan

    # Exact FE-evaluation contribution from player/draft score.
    ds_adv=.38*float(ds[normal]-ds[wi])
    # VORP is weighted 9x in the frozen champion, then 0.38 in pick evaluation.
    vorp_adv=.38*9.0*float(vp[normal]-vp[wi])

    diag.update({
        "wr_index":wi,"eval_deficit":deficit,"wr_survival":surv,
        "draftscore_advantage":ds_adv,"vorp_component_advantage":vorp_adv
    })

    if pd.isna(surv) or surv>float(max_wr_survival):
        return normal,False,diag
    if deficit>float(max_eval_deficit):
        return normal,False,diag
    if ds_adv<float(min_draftscore_advantage):
        return normal,False,diag
    if require_vorp_driver and vorp_adv<=0:
        return normal,False,diag

    diag["ls_wr_intercept"]=True
    return wi,True,diag


def pick12_faller_activation_snapshot(eval_score, market_pick, position_code, current_pick, next_pick, normal_choice,
                                       randomness=12, min_fall=7.0, max_eval_deficit=8.0,
                                       min_normal_reach=4.0, max_normal_survival=.55):
    ev=np.asarray(eval_score,dtype=float); mp=np.asarray(market_pick,dtype=float); pos=np.asarray(position_code)
    normal=int(normal_choice)
    out={"rbte":False,"reach_pass":False,"faller_exists":False,"eval_pass":False,"survival_pass":False,
         "full_trigger":False,"trigger_no_survival":False,"trigger_no_reach":False,
         "normal_reach":np.nan,"normal_survival":np.nan,"best_faller_amount":np.nan,
         "best_faller_eval_deficit":np.nan,"best_faller_position":"","best_faller_market_pick":np.nan}
    if len(ev)==0 or normal_choice is None: return out
    if int(pos[normal]) not in [1,3]: return out
    out["rbte"]=True
    nr=max(float(mp[normal])-float(current_pick),0.0) if np.isfinite(mp[normal]) else 0.0
    ns=survival_probability(float(mp[normal]),next_pick,randomness) if np.isfinite(mp[normal]) else np.nan
    out["normal_reach"]=nr; out["normal_survival"]=ns
    out["reach_pass"]=bool(nr>=float(min_normal_reach))
    fall=np.maximum(float(current_pick)-mp,0.0)
    raw=np.flatnonzero(np.isfinite(mp) & (fall>=float(min_fall)))
    out["faller_exists"]=bool(len(raw))
    if len(raw):
        # best market faller first, then report whether it is model-compatible
        fi=int(raw[int(np.argmax(fall[raw]))])
        deficit=max(float(ev[normal]-ev[fi]),0.0)
        out["best_faller_amount"]=float(fall[fi])
        out["best_faller_eval_deficit"]=deficit
        out["best_faller_position"]={0:"QB",1:"RB",2:"WR",3:"TE"}.get(int(pos[fi]),str(int(pos[fi])))
        out["best_faller_market_pick"]=float(mp[fi])
        compatible=raw[(float(np.nanmax(ev))-ev[raw])<=float(max_eval_deficit)]
        out["eval_pass"]=bool(len(compatible))
    out["survival_pass"]=bool(pd.notna(ns) and float(ns)<=float(max_normal_survival))
    out["full_trigger"]=bool(out["rbte"] and out["reach_pass"] and out["faller_exists"] and out["eval_pass"] and out["survival_pass"])
    out["trigger_no_survival"]=bool(out["rbte"] and out["reach_pass"] and out["faller_exists"] and out["eval_pass"])
    out["trigger_no_reach"]=bool(out["rbte"] and out["faller_exists"] and out["eval_pass"] and out["survival_pass"])
    return out


def pick12_faller_need_choice(eval_score, market_pick, position_code, current_pick, next_pick, normal_choice,
                              teams=12, randomness=12, enabled=False, min_fall=7.0,
                              max_eval_deficit=8.0, min_normal_reach=4.0, max_normal_survival=.55):
    """Calibration-only Pick-12 R4-6 faller-vs-need execution rule.

    It does not prefer WR by position. It may take the best model-compatible market
    faller before a normal RB/TE reach when the RB/TE still has a reasonable chance
    to survive to the next Pick-12 turn.
    """
    ev=np.asarray(eval_score,dtype=float); mp=np.asarray(market_pick,dtype=float)
    pos=np.asarray(position_code)
    normal=int(normal_choice)
    diag={"trigger":False,"faller_index":None,"faller_amount":0.0,"eval_deficit":np.nan,
          "normal_reach":0.0,"normal_survival":np.nan}
    if not enabled or normal_choice is None or len(ev)==0:
        return normal,False,diag
    rnd=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    if rnd<4 or rnd>6 or int(pos[normal]) not in [1,3]:
        return normal,False,diag

    normal_reach=max(float(mp[normal])-float(current_pick),0.0) if np.isfinite(mp[normal]) else 0.0
    normal_surv=survival_probability(float(mp[normal]),next_pick,randomness) if np.isfinite(mp[normal]) else np.nan
    diag["normal_reach"]=normal_reach; diag["normal_survival"]=normal_surv
    if normal_reach<float(min_normal_reach):
        return normal,False,diag
    if pd.isna(normal_surv) or float(normal_surv)>float(max_normal_survival):
        return normal,False,diag

    fall=np.maximum(float(current_pick)-mp,0.0)
    valid=np.isfinite(mp) & (fall>=float(min_fall))
    if not np.any(valid):
        return normal,False,diag

    # Keep the faller model-compatible; no positional forcing.
    best=float(np.nanmax(ev))
    valid &= (best-ev)<=float(max_eval_deficit)
    cand=np.flatnonzero(valid)
    if not len(cand):
        return normal,False,diag

    # Prioritize open draft-window value, then FE evaluation.
    score=.55*fall[cand] + .45*(ev[cand]-best)
    fi=int(cand[int(np.argmax(score))])
    deficit=max(float(ev[normal]-ev[fi]),0.0)
    diag.update({"faller_index":fi,"faller_amount":float(fall[fi]),"eval_deficit":deficit})
    if fi==normal or deficit>float(max_eval_deficit):
        return normal,False,diag

    diag["trigger"]=True
    return fi,True,diag


def faller_intercept_choice(eval_score, market_pick, current_pick, normal_choice,
                            teams=12, rounds=15, min_fall=None, model_band=None,
                            improvement_required=None):
    """Dynamic, model-compatible market faller override.

    The threshold changes by draft stage rather than using one fixed rule.
    A faller still must remain inside Fantasy Edge's model-compatible target band.
    """
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    if len(ev)==0 or normal_choice is None:
        return normal_choice,False,0.0

    auto_min,auto_band,auto_improve=dynamic_faller_threshold(current_pick,teams,rounds)
    min_fall=float(auto_min if min_fall is None else min_fall)
    model_band=int(auto_band if model_band is None else model_band)
    improvement_required=float(auto_improve if improvement_required is None else improvement_required)

    fall=np.maximum(float(current_pick)-mp,0)
    valid=np.isfinite(mp) & (fall>=min_fall)
    normal=int(normal_choice)
    normal_fall=float(fall[normal]) if np.isfinite(fall[normal]) else 0.0

    if not np.any(valid):
        return normal,False,normal_fall

    n=min(model_band,len(ev))
    top=np.argpartition(-ev,n-1)[:n] if n<len(ev) else np.arange(len(ev))
    cand=top[valid[top]]
    if len(cand)==0:
        return normal,False,normal_fall

    # Model compatibility remains important, but larger fallers gain increasingly
    # more weight instead of all fallers above the minimum being treated similarly.
    ev_top=ev[top]
    spread=max(float(np.nanstd(ev_top)),1.0)
    best_eval=float(np.nanmax(ev_top))
    compatibility=(ev[cand]-best_eval)/spread

    excess=np.maximum(fall[cand]-min_fall,0)
    round_no=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    if round_no>=11:
        # Frozen V7.15 late-round harvest scoring.
        fall_value=.46*fall[cand] + .055*(excess**1.40)
        intercept_score=fall_value + 1.45*compatibility
    elif 4<=round_no<=6:
        # V7.16: modest mid-round value boost, still keeping model compatibility
        # stronger than in late rounds.
        fall_value=.36*fall[cand] + .040*(excess**1.35)
        intercept_score=fall_value + 1.85*compatibility
    else:
        # Frozen V7.15 behavior for R1-3 and R7-10.
        fall_value=.32*fall[cand] + .035*(excess**1.35)
        intercept_score=fall_value + 2.0*compatibility
    best_cand=int(cand[int(np.argmax(intercept_score))])

    # Require the faller to improve market value enough over the normal execution
    # choice for the current draft stage.
    round_no=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    if round_no>=11:
        normal_reach=max(float(mp[normal])-float(current_pick),0) if np.isfinite(mp[normal]) else 0.0
        required=max(min_fall,normal_fall+improvement_required)
        # Frozen V7.15 late-round anti-reach safeguard.
        if normal_reach>=4.0:
            required=min_fall
        if float(fall[best_cand]) >= required:
            return best_cand,True,float(fall[best_cand])
    elif 4<=round_no<=6:
        # V7.16 mid-round anti-reach safeguard: weaker than late rounds.
        # If the normal choice is a 6+ pick reach and a model-compatible 9+ pick
        # faller exists, the faller only needs to clear the normal R4-6 threshold.
        normal_reach=max(float(mp[normal])-float(current_pick),0) if np.isfinite(mp[normal]) else 0.0
        required=max(min_fall,normal_fall+improvement_required)
        if normal_reach>=6.0:
            required=min_fall
        if float(fall[best_cand]) >= required:
            return best_cand,True,float(fall[best_cand])
    else:
        # Frozen V7.15 behavior for R1-3 and R7-10.
        if float(fall[best_cand]) >= max(min_fall,normal_fall+improvement_required):
            return best_cand,True,float(fall[best_cand])
    return normal,False,normal_fall
def roster_need_for_mock(roster_df, pos, slots):
    """Marginal roster value: each additional player is worth less once usable depth is filled."""
    counts=roster_df.position.value_counts().to_dict() if len(roster_df) else {}
    have=int(counts.get(pos,0))
    direct=max(int(slots.get(pos,0))-have,0)
    flex_used=max(0,sum(counts.get(p,0) for p in ["RB","WR","TE"])-
                    sum(int(slots.get(p,0)) for p in ["RB","WR","TE"]))
    flex_need=max(int(slots.get("FLEX",0))-flex_used,0)

    if direct>0:
        base=11.0+min(direct,2)*2.0
        if pos=="WR": base+=2.0
        return base

    if pos=="WR":
        if flex_need>0: return 8.0
        if have==2: return 6.0
        if have==3: return 4.0
        if have==4: return 0.5
        return -5.0
    if pos=="RB":
        if flex_need>0 and have<3: return 5.0
        if have==2: return 3.0
        if have==3: return 0.5
        if have==4: return -3.5
        return -10.0
    if pos=="TE": return -10.0 if have>=1 else 0.0
    if pos=="QB": return -14.0 if have>=1 else 0.0
    if pos in ["DL","DB"]:
        return -12.0 if have>=int(slots.get(pos,1)) else -1.0
    return -3.0

def _small_roster_utility_df(roster, slots):
    """Expected final-roster utility for a small drafted roster DataFrame.

    Starters receive full value, FLEX receives near-starter value, and bench players
    receive diminishing insurance/upside value. This evaluates the players actually
    on the roster rather than prescribing a fixed QB/RB/WR/TE bench recipe.
    """
    if roster is None or len(roster)==0:
        return 0.0
    r=roster.copy()
    r["_base_value"]=r["projection"].fillna(0)+0.70*r["vorp"].fillna(0).clip(lower=-5)
    used=set(); total=0.0
    # Required position starters.
    for pos in ["QB","RB","WR","TE","DL","DB"]:
        n=max(int(slots.get(pos,0)),0)
        px=r[r.position.eq(pos)].sort_values("_base_value",ascending=False)
        for idx,row in px.head(n).iterrows():
            used.add(idx)
            total += float(row.projection)*1.00 + float(row.vorp)*0.90
    # FLEX from remaining RB/WR/TE.
    flex_n=max(int(slots.get("FLEX",0)),0)
    flex=r[(~r.index.isin(used)) & r.position.isin(["RB","WR","TE"])].sort_values("_base_value",ascending=False)
    for idx,row in flex.head(flex_n).iterrows():
        used.add(idx)
        total += float(row.projection)*0.92 + float(row.vorp)*0.75
    # Bench: value depends on actual player quality with diminishing depth utility.
    bench=r[~r.index.isin(used)].sort_values("_base_value",ascending=False)
    depth={"QB":0,"RB":0,"WR":0,"TE":0,"DL":0,"DB":0}
    bench_mult={"QB":[.14,.03],"RB":[.25,.15,.08,.03],"WR":[.40,.30,.20,.11,.06],
                "TE":[.16,.04],"DL":[.06],"DB":[.06]}
    for _,row in bench.iterrows():
        p=row.position; d=depth.get(p,0); arr=bench_mult.get(p,[.05])
        mult=arr[d] if d<len(arr) else .02
        total += mult*(float(row.projection)+0.55*max(float(row.vorp),0))
        depth[p]=d+1
    return float(total)


def _candidate_roster_delta_df(roster, candidates, slots, exact_cap=72):
    """Fast V7.3 marginal roster utility with bounded exact evaluation."""
    if candidates is None or len(candidates)==0:
        return np.array([],dtype=float)
    current=_small_roster_utility_df(roster,slots)
    c=candidates
    proj=pd.to_numeric(c["projection"],errors="coerce").fillna(0).to_numpy(float)
    vorp=pd.to_numeric(c["vorp"],errors="coerce").fillna(0).to_numpy(float)
    ds=pd.to_numeric(c["draft_score"],errors="coerce").fillna(-1e9).to_numpy(float)
    cr=pd.to_numeric(c["consensus_rank"],errors="coerce").fillna(999).to_numpy(float)
    approx=.10*proj+.08*np.maximum(vorp,0)
    out=approx.copy()
    n=min(int(exact_cap),len(c))
    k1=max(1,n//3); k2=max(1,n//3)
    a=np.argpartition(-ds,min(k1-1,len(ds)-1))[:k1]
    b=np.argpartition(cr,min(k2-1,len(cr)-1))[:k2]
    pi=[]; posarr=c["position"].astype(str).to_numpy()
    per=max(2,n//18)
    for pname in ["QB","RB","WR","TE","DL","DB"]:
        loc=np.flatnonzero(posarr==pname)
        if loc.size:
            take=min(per,loc.size)
            best=loc[np.argpartition(-ds[loc],min(take-1,loc.size-1))[:take]]
            pi.extend(best.tolist())
    short=np.unique(np.concatenate([a,b,np.asarray(pi,dtype=int)]))
    if len(short)>n:
        composite=(-ds[short])+0.05*cr[short]
        short=short[np.argsort(composite)[:n]]
    for j in short:
        row=c.iloc[int(j)]
        temp=pd.concat([roster,row.to_frame().T],ignore_index=True) if len(roster) else row.to_frame().T
        out[int(j)]=_small_roster_utility_df(temp,slots)-current
    return out
def _minimum_required_picks_remaining(counts, slots):
    """Minimum picks needed to complete fixed starters plus FLEX."""
    fixed_positions=["QB","RB","WR","TE","K","DL","DB"]
    fixed_def={p:max(int(slots.get(p,0))-int(counts.get(p,0)),0) for p in fixed_positions}

    required_skill=(
        int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+
        int(slots.get("FLEX",0))
    )
    have_skill=int(counts.get("RB",0))+int(counts.get("WR",0))+int(counts.get("TE",0))
    fixed_skill_def=fixed_def["RB"]+fixed_def["WR"]+fixed_def["TE"]
    flex_extra=max(required_skill-have_skill-fixed_skill_def,0)
    return int(sum(fixed_def.values())+flex_extra), fixed_def, int(flex_extra)


def _candidate_keeps_roster_feasible(roster, candidate_pos, round_no, rounds, slots):
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    after=dict(counts)
    after[candidate_pos]=int(after.get(candidate_pos,0))+1
    remaining_after=max(int(rounds)-int(round_no),0)
    minimum_after,_,_=_minimum_required_picks_remaining(after,slots)
    return minimum_after<=remaining_after


def draft_eligibility(avail, roster, round_no, rounds, slots):
    """Hard legality plus mathematical end-of-draft roster feasibility."""
    a=avail.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}

    qb=int(counts.get("QB",0)); te=int(counts.get("TE",0))
    dl=int(counts.get("DL",0)); db=int(counts.get("DB",0)); k=int(counts.get("K",0))
    total_idp=dl+db

    # Required-position depletion guard. If an unfilled required position is down
    # to two available players, take that requirement now rather than risk a
    # mathematically legal but practically impossible late roster.
    _required_open=[
        p for p in ["QB","RB","WR","TE","K","DL","DB"]
        if int(counts.get(p,0)) < int(slots.get(p,0))
    ]
    _critical=[]
    for _p in _required_open:
        _n=int((a["position"].astype(str)==_p).sum())
        if 0 < _n <= 2:
            _critical.append((_n,_p))
    if _critical:
        _critical.sort()
        _critical_pos=_critical[0][1]
        _critical_pool=a[a["position"].astype(str).eq(_critical_pos)]
        if len(_critical_pool):
            a=_critical_pool.copy()

    # Allow normal depth, including exactly one extra impact IDP.
    if int(slots.get("QB",1))<=1 and qb>=2:
        a=a[~a.position.eq("QB")]
    if int(slots.get("TE",1))<=1 and te>=2:
        a=a[~a.position.eq("TE")]
    if dl>=2:
        a=a[~a.position.eq("DL")]
    if db>=2:
        a=a[~a.position.eq("DB")]
    # Required starters are 1 DL + 1 DB. Allow at most ONE extra impact defender.
    if total_idp>=3:
        a=a[~a.position.isin(["DL","DB"])]
    if k>=max(int(slots.get("K",1)),1):
        a=a[~a.position.eq("K")]

    if int(round_no)<=7:
        offense=a[~a.position.isin(["DL","DB"])]
        if len(offense)>=5:
            a=offense

    # Candidate-level feasibility. A pick is illegal if it leaves too few future
    # picks to finish all required starters and both FLEX slots.
    if len(a):
        feasible=a["position"].map(
            lambda p:_candidate_keeps_roster_feasible(
                roster,str(p),int(round_no),int(rounds),slots
            )
        )
        a=a[feasible].copy()

    # Exact completion boundary: only a pick that reduces the minimum remaining
    # requirement may be selected.
    minimum_now,_,_=_minimum_required_picks_remaining(counts,slots)
    picks_left=int(rounds)-int(round_no)+1
    if len(a) and minimum_now>0 and picks_left<=minimum_now:
        reducers=[]
        for ix,row in a.iterrows():
            after=dict(counts)
            p=str(row.position)
            after[p]=int(after.get(p,0))+1
            after_min,_,_=_minimum_required_picks_remaining(after,slots)
            if after_min<minimum_now:
                reducers.append(ix)
        # Exact completion boundary: if no candidate reduces the remaining requirement,
        # there is no legal candidate.
        a=a.loc[reducers].copy()

    # Late-bench diversification authority.
    # Once the core offense is deep (5 RB + 5 WR) and required starters are covered,
    # reserve a remaining bench opportunity for a qualifying impact DL/DB.
    counts_now=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    core_filled=(
        int(counts_now.get("QB",0))>=int(slots.get("QB",1)) and
        int(counts_now.get("RB",0))>=int(slots.get("RB",2)) and
        int(counts_now.get("WR",0))>=int(slots.get("WR",2)) and
        int(counts_now.get("TE",0))>=int(slots.get("TE",1)) and
        int(counts_now.get("DL",0))>=int(slots.get("DL",1)) and
        int(counts_now.get("DB",0))>=int(slots.get("DB",1))
    )
    deep_offense=(int(counts_now.get("RB",0))>=5 and int(counts_now.get("WR",0))>=5)
    total_idp=int(counts_now.get("DL",0))+int(counts_now.get("DB",0))
    if core_filled and deep_offense and total_idp<3 and len(a):
        # Do not hard-force a defender here; scorer will require actual impact quality.
        # But prevent both RB6 and WR6 from consuming the final diversification window.
        picks_left=int(rounds)-int(round_no)+1
        if picks_left<=3:
            a=a[~((a.position.eq("RB")) | (a.position.eq("WR")))].copy() if a.position.isin(["DL","DB"]).any() else a

    # If all required starters/FLEX are already complete, soft depth/saturation
    # rules are not allowed to create an empty candidate set. Rebuild from the
    # original available pool using only true roster hard caps.
    if len(a)==0:
        minimum_now,_,_=_minimum_required_picks_remaining(counts,slots)
        if minimum_now==0:
            a=avail.copy()
            if int(slots.get("QB",1))<=1 and qb>=2:
                a=a[~a.position.eq("QB")]
            if int(slots.get("TE",1))<=1 and te>=2:
                a=a[~a.position.eq("TE")]
            if total_idp>=3:
                a=a[~a.position.isin(["DL","DB"])]
            if k>=max(int(slots.get("K",1)),1):
                a=a[~a.position.eq("K")]

    return a


def grade_mock(roster, teams, slots):
    def _gnum(name, default=0.0):
        if name in roster.columns:
            return pd.to_numeric(roster[name],errors="coerce").fillna(float(default))
        return pd.Series(float(default),index=roster.index,dtype=float)
    """Grade the mock on *realized* draft advantage, not a cosmetic score boost.

    v9.42 changes:
    - Honors the exact league: 1 TE is required; FLEX may also use RB/WR/TE.
    - Model Edge measures what the draft actually captured: market value at cost, model conviction
      at cost, VORP/projection quality, and roster construction.
    - DL/DB rows with obviously non-comparable global model ranks no longer poison Model Edge;
      shallow-IDP quality is judged by projection/market support and the shared IDP authority layer.
    - Reaches are penalized asymmetrically; falling past market is rewarded but capped so one late
      pick cannot inflate the entire grade.
    """
    if roster is None or len(roster)==0:
        return {"score":0,"grade":"F","starter":0,"value":0,"penalty":100,
                "draft_value":0,"construction":0,"positional_advantage":0,
                "model_edge_score":0,"opportunity_penalty":0}

    r=roster.copy()
    for c in ["projection","vorp","model_rank","consensus_rank","mock_pick"]:
        if c in r.columns: r[c]=pd.to_numeric(r[c],errors="coerce")
    counts=r.position.value_counts().to_dict()

    # Exact required starters: TE is required in this league.
    req={p:max(int(slots.get(p,d)),0) for p,d in
         {"QB":1,"RB":2,"WR":2,"TE":1,"K":1,"DL":1,"DB":1}.items()}
    flex_n=max(int(slots.get("FLEX",0)),0)

    # Realized market value: positive means we drafted the player AFTER consensus cost.
    # Reaches hurt faster than fallers help; both are capped for robustness.
    if "mock_pick" in r.columns:
        market_delta=r.mock_pick-r.consensus_rank
    else:
        market_delta=r.consensus_rank-r.model_rank
    market_delta=market_delta.where(r.consensus_rank.notna())
    market_points=np.where(market_delta.notna(),
        np.where(market_delta>=0, np.minimum(market_delta,36.0)*0.42,
                 np.maximum(market_delta,-30.0)*0.62), 0.0)

    # Model conviction realized at cost. Global offensive ranks are useful here, but the legacy
    # DL/DB global rank scale is not comparable (e.g. quality IDPs can be rank 500+ / 2000+).
    # For IDP, use market-supported positional quality rather than that broken cross-position rank.
    model_delta=(r.mock_pick-r.model_rank) if "mock_pick" in r.columns else (r.consensus_rank-r.model_rank)
    is_idp=r.position.isin(["DL","DB"])
    valid_model=(~is_idp) & r.model_rank.notna() & (r.model_rank<400)
    conviction=np.zeros(len(r),dtype=float)
    md=model_delta.to_numpy(dtype=float)
    vm=valid_model.to_numpy(dtype=bool)
    conviction[vm]=np.where(md[vm]>=0,np.minimum(md[vm],42.0)*0.24,np.maximum(md[vm],-35.0)*0.34)

    # Player-quality support: VORP is the primary cross-position signal. Projection adds a small
    # within-roster quality signal; IDP zero-VORP is neutral rather than an automatic failure.
    vorp=r.vorp.fillna(0).clip(-3,12)

    # Use roster-adjusted usable VORP when available so RB6/WR6/QB2 do not inflate Model Edge.
    if "usable_vorp" in r.columns:
        usable_vorp=pd.to_numeric(r["usable_vorp"],errors="coerce").fillna(vorp).clip(-3,12)
    else:
        usable_vorp=vorp
    vorp_points=(usable_vorp*0.72).to_numpy(dtype=float)
    proj=r.projection.fillna(0)
    quality=np.zeros(len(r),dtype=float)
    off=(~is_idp).to_numpy(dtype=bool)
    quality[off]=np.clip((proj.to_numpy(dtype=float)[off]-10.0)*0.12,-1.0,1.6)
    # Shallow IDP: reward credible market support + usable projection, without inventing VORP.
    idpm=is_idp.to_numpy(dtype=bool)
    cr=r.consensus_rank.to_numpy(dtype=float)
    pr=proj.to_numpy(dtype=float)
    quality[idpm]=np.where(np.isfinite(cr[idpm]),np.clip((130.0-cr[idpm])/55.0,-1.0,1.4),-0.5)
    quality[idpm]+=np.clip((pr[idpm]-5.0)*0.35,-0.5,1.0)

    pick_edge=market_points+conviction+vorp_points+quality
    avg_pick_edge=float(np.nanmean(pick_edge)) if len(pick_edge) else 0.0

    # Fantasy Edge calibration:
    # 100/100 is achievable, but only through repeated quality decisions rather than
    # a cosmetic score boost. Reward consistency across the whole roster.
    _clean_pick=((market_delta.fillna(-999)>=-5) & (vorp>=0)).astype(float)
    _clean_rate=float(_clean_pick.mean()) if len(_clean_pick) else 0.0
    _value_rate=float((market_delta.fillna(-999)>=0).mean()) if len(r) else 0.0

    # Base edge comes from realized per-pick advantage. Consistency adds at most 4 points:
    # 2.5 for avoiding bad-value/negative-VORP picks and 1.5 for repeatedly beating market.
    _consistency_bonus=2.5*_clean_rate + 1.5*_value_rate
    model_edge=float(np.clip(58.0+2.15*avg_pick_edge+_consistency_bonus,35,100))

    # Draft value is primarily realized market value + VORP, not model-vs-market disagreement.
    avg_market=float(np.nanmean(np.clip(market_delta.fillna(0),-30,36))) if len(r) else 0.0
    avg_vorp=float(usable_vorp.mean()) if len(r) else 0.0
    draft_value=float(np.clip(62+0.62*avg_market+2.0*avg_vorp,35,100))
    # Realized pick economics: Draft Value should respond to the actual roster,
    # not remain almost static across simulations.
    _rv=_gnum("vorp",0.0)
    _rp=_gnum("projection",0.0)
    if "roster_opportunity" in roster.columns:
        _ro=pd.to_numeric(roster["roster_opportunity"],errors="coerce").fillna(0.0)
    elif "roster_opportunity_adj" in roster.columns:
        _ro=pd.to_numeric(roster["roster_opportunity_adj"],errors="coerce").fillna(0.0)
    else:
        _ro=pd.Series(0.0,index=roster.index,dtype=float)
    realized_pick_economics=float(np.clip(
        0.55*np.nanmean(np.clip(_rv,-10,35))+
        0.035*np.nanmean(np.clip(_rp,0,400))+
        0.30*np.nanmean(np.clip(_ro,-10,15)),
        -5,12
    ))
    draft_value=float(np.clip(draft_value+realized_pick_economics,0,100))
    # V6.16: preserve the legacy market-timing-only value for transparency.
    raw_market_draft_value=float(draft_value)

    construction=100.0
    for p,v in req.items():
        construction-=16*max(v-counts.get(p,0),0)
    # FLEX is filled by the best remaining RB/WR/TE after nominal RB/WR/TE starters.
    skill=r[r.position.isin(["RB","WR","TE"])].copy()
    nominal=req["RB"]+req["WR"]+req["TE"]
    flex_available=max(len(skill)-nominal,0)
    construction-=14*max(flex_n-flex_available,0)
    # Healthy depth targets for this exact six-bench build with one required TE.
    rb,wr=counts.get("RB",0),counts.get("WR",0)
    if rb+wr+counts.get("TE",0)<6: construction-=5*(6-(rb+wr+counts.get("TE",0)))
    qb,te,dl,db=[counts.get(p,0) for p in ["QB","TE","DL","DB"]]
    construction-=12*max(qb-2,0)+10*max(te-2,0)
    # V6.11: one merit-earned backup IDP is legal bench construction. Penalize
    # only a fourth defender or excessive same-position defensive depth.
    _idp_total=dl+db
    construction-=7*max(_idp_total-3,0)
    construction-=4*max(dl-2,0)+4*max(db-2,0)
    construction=float(np.clip(construction,0,100))

    # Starter VORP: exact positional starters, then FLEX from remaining RB/WR/TE.
    starter=0.0; used=set()
    for p in ["QB","RB","WR","TE","K","DL","DB"]:
        n=req[p]
        if n<=0: continue
        idx=r[r.position.eq(p)].vorp.nlargest(n).index
        used.update(idx.tolist()); starter+=float(r.loc[idx,"vorp"].sum())
    flex_pool=r.loc[~r.index.isin(used) & r.position.isin(["RB","WR","TE"]),"vorp"]
    starter+=float(flex_pool.nlargest(flex_n).sum())
    positional=float(np.clip(50+starter*.78,35,100))

    # Opportunity cost: redundant depth, unnecessary early QB2/TE2, and
    # contextually avoidable reaches. Raw ADP reach cost is retained separately
    # so the dashboard remains transparent.
    opp=0.0; raw_opp=0.0; seen={"QB":0,"TE":0}
    ordered=r.sort_values("mock_pick") if "mock_pick" in r.columns else r
    for _idx,row in ordered.iterrows():
        p=row.position
        if p in seen:
            seen[p]+=1
            if seen[p]>=2 and float(row.get("mock_pick",999))<120:
                opp+=4; raw_opp+=4
        crv=row.get("consensus_rank",np.nan); pk=row.get("mock_pick",np.nan)
        if pd.notna(crv) and pd.notna(pk):
            reach=float(crv)-float(pk)  # positive = drafted ahead of market
            if reach>18:
                _reach_cost=min(8,(reach-18)*.12)
                raw_opp+=_reach_cost
                _avoidable=bool(row.get("avoidable_reach",True))
                if _avoidable:
                    opp+=_reach_cost

    # Portfolio/reach diagnostics. Contextual rate drives decision-quality
    # penalty; raw rate is reported separately.
    _reach_series=(r.consensus_rank-r.mock_pick) if "mock_pick" in r.columns else pd.Series(0,index=r.index)
    _raw_big_reach_rate=float((_reach_series>24).mean()) if len(r) else 0.0
    if "avoidable_reach" in r.columns:
        _avoid_flag=r["avoidable_reach"].fillna(False).astype(bool)
        _big_reach_rate=float(((_reach_series>24) & _avoid_flag).mean()) if len(r) else 0.0
    else:
        _big_reach_rate=_raw_big_reach_rate
    _redundant_depth=max(counts.get("RB",0)-5,0)+max(counts.get("WR",0)-5,0)+max(counts.get("QB",0)-2,0)+max(counts.get("TE",0)-2,0)
    _double_backup=int(counts.get("QB",0)>=2 and counts.get("TE",0)>=2)
    _portfolio_penalty=min(10.0,3.5*_redundant_depth + 2.5*_double_backup)
    _reach_penalty=min(8.0,12.0*_big_reach_rate)

    _idp_total=int(counts.get("DL",0))+int(counts.get("DB",0))
    _diversification_penalty=0.0
    if counts.get("RB",0)>=6 and counts.get("WR",0)>=6 and _idp_total<=2:
        _diversification_penalty=6.0

    opp+=_portfolio_penalty+_reach_penalty+_diversification_penalty
    raw_opp+=_portfolio_penalty+min(8.0,12.0*_raw_big_reach_rate)+_diversification_penalty

    # V6.16 calibrated Draft Value: draft capital is still the majority signal,
    # but a draft is also valuable when that capital converts into starter advantage,
    # usable bench upside, and low opportunity waste. Keep raw_market_draft_value
    # alongside this score so the dashboard cannot hide pure ADP efficiency.
    _bench_value_score=float(np.clip(70.0+2.0*float(np.clip(
        r.loc[~r.index.isin(used),"vorp"].fillna(0).clip(-2,10).sum(),-10,15
    )),35,100))
    _capital_efficiency=float(np.clip(100.0-5.0*float(opp),0,100))
    draft_value=float(np.clip(
        0.70*raw_market_draft_value +
        0.15*positional +
        0.10*_bench_value_score +
        0.05*_capital_efficiency,
        0,100
    ))

    # Interpretable quality composite.
    model_edge=float(np.clip(
        0.42*draft_value +
        0.30*construction +
        0.20*positional +
        8.0*_clean_rate -
        0.45*float(opp),
        0,100
    ))

    # Overall grade uses the same economics without double-counting opportunity loss.
    score=float(np.clip(.34*draft_value+.30*construction+.22*positional+.14*model_edge-0.35*opp,0,100))
    _construction_edge_penalty=0.0
    _draft_value_edge_penalty=0.0
    _positional_edge_penalty=0.0
    _opportunity_edge_penalty=0.0
    grade="A+" if score>=94 else "A" if score>=90 else "A-" if score>=86 else "B+" if score>=82 else "B" if score>=78 else "B-" if score>=74 else "C+" if score>=70 else "C" if score>=65 else "C-" if score>=60 else "D" if score>=55 else "F"
    return {"score":score,"grade":grade,"starter":starter,"value":avg_market,"penalty":max(0,100-construction),
            "draft_value":draft_value,"raw_market_draft_value":raw_market_draft_value,
            "construction":construction,"positional_advantage":positional,
            "model_edge_score":model_edge,"opportunity_penalty":opp,
            "raw_opportunity_penalty":raw_opp,"starter_vorp":starter,
            "clean_pick_rate":_clean_rate,"market_win_rate":_value_rate,
            "big_reach_rate":_big_reach_rate,"raw_big_reach_rate":_raw_big_reach_rate,"portfolio_penalty":_portfolio_penalty,"diversification_penalty":_diversification_penalty,"construction_edge_penalty":_construction_edge_penalty,"draft_value_edge_penalty":_draft_value_edge_penalty,"positional_edge_penalty":_positional_edge_penalty,"opportunity_edge_penalty":_opportunity_edge_penalty}

def _injury_severity(status):
    x=str(status or "").strip().lower()
    if x in ["ir","pup","nfi","reserve/ir","reserve/pup"]: return 3
    if x in ["out","suspended","susp"]: return 2
    if x in ["doubtful","questionable","q","d"]: return 1
    return 0


# --- Fantasy Edge v9.2 live injury overlay ---
def _injury_overlay_penalty(status):
    x=str(status or "").strip().lower()
    if x in ["do not draft","dnr","avoid"]: return 999.0
    if x in ["ir","reserve/ir","nfi","reserve/nfi"]: return 999.0
    if x in ["pup","reserve/pup"]: return 3.5
    if x in ["out","o","suspended","susp"]: return 2.5
    if x in ["doubtful","d"]: return 1.25
    if x in ["questionable","q"]: return 0.9
    return 0.0

def _injury_overlay_severity(status):
    p=_injury_overlay_penalty(status)
    if p>=900: return 3
    if p>=2.5: return 2
    if p>0: return 1
    return 0

def apply_v92_injury_overlay(board,state):
    """Overlay Sleeper injury status with user-controlled manual overrides."""
    b=board.copy()
    overrides=state.get("injury_overrides",{}) or {}
    b["injury_auto"]=b.get("injury",pd.Series("",index=b.index)).fillna("").astype(str)
    effective=[]
    source=[]
    for _,r in b.iterrows():
        ov=overrides.get(norm(r["player"]))
        if ov and str(ov).upper()!="AUTO":
            effective.append("" if str(ov).upper()=="CLEAR" else str(ov))
            source.append("Manual")
        else:
            effective.append(str(r["injury_auto"] or ""))
            source.append("Sleeper")
    b["injury_effective"]=effective
    b["injury_source"]=source
    b["injury"]=b["injury_effective"]
    b["injury_penalty"]=b["injury_effective"].map(_injury_overlay_penalty).astype(float)
    b["injury_severity"]=b["injury_effective"].map(_injury_overlay_severity).astype(int)
    return b


# --- Fantasy Edge v9.24 dynamic roster opportunity cost ---

def _v934_num(row, *keys):
    for k in keys:
        if k in row.index:
            v = pd.to_numeric(pd.Series([row.get(k, np.nan)]), errors="coerce").iloc[0]
            if pd.notna(v):
                return float(v)
    return np.nan

_V937_IDP_DB_CONSENSUS = {'Brian Branch': 1, 'Nick Emmanwori': 2, 'Kyle Hamilton': 3, 'Derwin James': 4, 'Nick Cross': 5, 'Jessie Bates': 6, 'Antoine Winfield Jr.': 7, 'Tykee Smith': 8, 'Cooper DeJean': 9, 'Devon Witherspoon': 10, 'DeShon Elliott': 11, 'Xavier McKinney': 12, 'Budda Baker': 13, 'Julian Love': 14, 'Christian Gonzalez': 20, 'Sauce Gardner': 25, 'Pat Surtain II': 30, 'Denzel Ward': 35}

_V936_IDP_DL_CONSENSUS = {
    "Myles Garrett": 1,
    "Maxx Crosby": 3,
    "Aidan Hutchinson": 4,
    "Brian Burns": 5,
    "Will Anderson Jr.": 6,
    "Danielle Hunter": 7,
    "T.J. Watt": 9,
    "Nick Bosa": 12,
    "Trey Hendrickson": 13,
    "Micah Parsons": 15,
    "Jeffery Simmons": 16,
    "Andrew Van Ginkel": 8,
    "Nik Bonitto": 10,
    "Tuli Tuipulotu": 11,
}

def _v936_external_idp_rank(row):
    name=str(row.get("player", row.get("Player",""))).strip()
    pos=str(row.get("position", row.get("Position",""))).upper()
    if pos=="DB":
        return _V937_IDP_DB_CONSENSUS.get(name, np.nan)
    if pos=="DL":
        return _V936_IDP_DL_CONSENSUS.get(name, np.nan)
    return np.nan


@st.cache_data(show_spinner=False)
def _v938_unified_player_universe(board):
    """Canonical Draft/Mock lobby universe with complete IDP market proxies."""
    if board is None or len(board)==0:
        return board
    x=board.copy()
    if "key" not in x.columns:
        x["key"]=x["player"].astype(str).map(norm)

    overlays=[]
    for name,rank in _V936_IDP_DL_CONSENSUS.items():
        overlays.append((name,"DL",int(rank)))
    for name,rank in _V937_IDP_DB_CONSENSUS.items():
        overlays.append((name,"DB",int(rank)))

    def _proxy(pos,rank):
        if pos=="DL":
            market=float(np.clip(100.0+4.0*rank,101.0,184.0))
            proj=float(max(4.8,10.0-0.28*(rank-1)))
            repl=6.2
        else:
            market=float(np.clip(108.0+3.6*rank,110.0,186.0))
            proj=float(max(4.8,9.2-0.20*(rank-1)))
            repl=5.9
        vorp=float(proj-repl)
        model_rank=float(market-max(0.0,min(18.0,vorp*3.0)))
        base=float(7.0+max(0.0,22.0-rank)*0.55+max(vorp,0)*1.5)
        strength=float(max(52.0,88.0-rank*1.25))
        return market,proj,vorp,model_rank,base,strength

    rows=[]
    existing_keys=set(x["key"].astype(str))
    for name,pos,rank in overlays:
        key=norm(name)
        market,proj,vorp,model_rank,base,strength=_proxy(pos,rank)

        if key in existing_keys:
            mask=x["key"].astype(str).eq(key)
            updates={
                "position":pos,"raw_position":pos,
                "market_pick":market,"consensus_rank":market,
                "model_rank":model_rank,"projection":proj,"vorp":vorp,
                "consensus_strength":strength,"pure_model_score":base,
                "draft_score":base,"confidence":0.78,
                "v9_market_pick":market,"v9_vorp":vorp,
                "v9_draft_score":base,"v9_model_rank":model_rank,
                "v9_base_live_score":base,
            }
            for col,val in updates.items():
                if col in x.columns:
                    x.loc[mask,col]=val
            continue

        d={c:np.nan for c in x.columns}
        d.update({
            "id":"v948:"+key,"player":name,"key":key,
            "position":pos,"raw_position":pos,"team":"NFL",
            "age":np.nan,"exp":np.nan,"injury":"",
            "last_ppg":proj,"prior_ppg":proj,"opp_pg":proj,
            "td_rate_z":0.0,"eff_z":0.0,"growth_z":0.0,"opp_z":0.0,
            "idp_vol_z":0.0,"bigplay_z":0.0,
            "projection":proj,"vorp":vorp,"replacement_ppg":proj-vorp,
            "progression":0.0,"regression":0.0,"scarcity":0.0,
            "consensus_strength":strength,"consensus_rank":market,
            "market_pick":market,"model_rank":model_rank,
            "pure_model_score":base,"draft_score":base,"confidence":0.78,
            "identity_key":"v948:"+key+"|"+pos,
            "v9_market_pick":market,"v9_vorp":vorp,
            "v9_draft_score":base,"v9_model_rank":model_rank,
            "v9_base_live_score":base,
        })
        rows.append(d)

    if rows:
        x=pd.concat([x,pd.DataFrame(rows)],ignore_index=True,sort=False)
    return x.drop_duplicates(subset=["key"],keep="first").reset_index(drop=True)


def _v941_idp_quality(row):
    """Independent positional-quality support; never sufficient alone for eligibility."""
    pos=str(row.get("position","")).upper()
    ext=_v936_external_idp_rank(row)
    proj=_v934_num(row,"projection","proj","fantasy_points","projected_points")
    vorp=_v934_num(row,"vorp","v9_vorp","VORP")
    market=_v934_num(row,"market_pick","adp","consensus_pick","consensus_rank")
    evidence=0
    if pd.notna(proj) and proj>0: evidence+=1
    if pd.notna(vorp) and vorp>0: evidence+=1
    if pd.notna(market): evidence+=1
    # tier is support, not authority
    if pd.notna(ext):
        if pos=="DL":
            tier = 1 if ext<=6 else 2 if ext<=15 else 3 if ext<=30 else 4
        else:
            tier = 1 if ext<=8 else 2 if ext<=20 else 3 if ext<=40 else 4
    else:
        tier=5
    return tier,evidence

def _v935_idp_impact_score(row):
    """IDP impact with independent-evidence gating; duplicated fallback rank/market
    cannot manufacture confidence. No hard-coded player names."""
    pos = str(row.get("position","")).upper()
    if pos not in ("DL","DB"):
        return np.nan, False, 0

    vorp = _v934_num(row, "vorp", "VORP")
    proj = _v934_num(row, "projection", "proj", "fantasy_points", "points")
    market = _v934_num(row, "market_pick", "adp", "consensus_pick")
    rank = _v934_num(row, "consensus_rank", "rank", "model_rank")
    ext_rank = _v936_external_idp_rank(row)
    snaps = _v934_num(row, "snap_share", "snaps_pct", "snap_pct")
    tackles = _v934_num(row, "tackles", "total_tackles", "combined_tackles")
    sacks = _v934_num(row, "sacks")
    tfl = _v934_num(row, "tfl", "tackles_for_loss")
    pressures = _v934_num(row, "pressures", "qb_pressures")
    ints = _v934_num(row, "interceptions", "ints")
    ff = _v934_num(row, "forced_fumbles", "ff")
    pdff = _v934_num(row, "passes_defended", "pass_deflections", "pd")

    # Independent evidence = meaningful player-specific signal, not mere presence.
    # Zero VORP is neutral/missing support, not positive evidence.
    independent = 0
    production = [tackles, sacks, tfl, pressures, ints, ff, pdff]
    if pd.notna(vorp) and abs(vorp) > 1e-9: independent += 1
    if pd.notna(proj) and proj > 0: independent += 1
    if pd.notna(snaps) and snaps > 0: independent += 1
    if any(pd.notna(v) and v > 0 for v in production): independent += 1
    if pd.notna(ext_rank):
        independent += 1

    # Market/rank can support ordering, but only one combined market-family signal
    # and it cannot make an otherwise unsupported IDP eligible.
    market_support = int(
        (pd.notna(market) and market > 0) or
        (pd.notna(rank) and rank > 0)
    )

    score = 0.0
    if pd.notna(vorp) and abs(vorp) > 1e-9:
        score += 7.0 * max(vorp, -1.0)
    if pd.notna(proj) and proj > 0:
        score += min(proj, 250.0) * 0.035
    if pd.notna(snaps) and snaps > 0:
        score += max(0.0, snaps) * (0.06 if snaps <= 1.5 else 0.0008)
    for val, wt in [(tackles,.08),(sacks,1.1),(tfl,.45),(pressures,.12),
                    (ints,1.25),(ff,1.1),(pdff,.22)]:
        if pd.notna(val) and val > 0:
            score += val * wt
    if pd.notna(ext_rank):
        if pos=="DB":
            score += max(0.0, 40.0 - float(ext_rank)) * 0.55
        else:
            score += max(0.0, 18.0 - float(ext_rank)) * 1.15
    if pos=="DL":
        if pd.notna(sacks) and sacks>0: score += sacks*.35
        if pd.notna(pressures) and pressures>0: score += pressures*.05
    else:
        if pd.notna(tackles) and tackles>0: score += tackles*.03
        if pd.notna(ints) and ints>0: score += ints*.30

    # Market is deliberately only a modest tie-breaker after independent support.
    if independent:
        if pd.notna(market) and market > 0:
            score += max(0.0, 180.0-market) * 0.010
        if pd.notna(rank) and rank > 0:
            score += max(0.0, 250.0-rank) * 0.006

    strong_single = (
        (pd.notna(vorp) and vorp >= 1.0) or
        (pd.notna(proj) and proj > 0) or
        any(pd.notna(v) and v > 0 for v in production)
    )
    # v9.40: external prior is only a tie-breaker/support signal.
    # It can never, by itself, make an IDP eligible.
    eligible = independent >= 2 or strong_single
    evidence = independent + market_support
    return float(score), bool(eligible), int(evidence)

# Backward-compatible name used by the rest of the app.
def _v934_idp_impact_score(row):
    return _v935_idp_impact_score(row)

def roster_opportunity_adjustment(df, roster, round_no, current_pick, slots):
    """
    Temporary roster-construction overlay.
    Negative values = opportunity-cost penalty.
    Positive values = roster-need bonus.
    The frozen player board is not modified.
    """
    x=df.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    rnd=int(round_no)
    cur=int(current_pick)

    adjustments=[]
    reasons=[]
    for _,r in x.iterrows():
        pos=str(r.get("position",""))
        adj=0.0
        why=[]

        rb=counts.get("RB",0)
        wr=counts.get("WR",0)
        qb=counts.get("QB",0)
        te=counts.get("TE",0)
        dl=counts.get("DL",0)
        db=counts.get("DB",0)

        # WR foundation pressure: avoid entering the middle/late draft too thin at WR.
        if pos=="WR":
            if rnd<=8 and wr<2:
                adj += 6.0
                why.append("WR foundation need")
            elif rnd<=9 and wr<3:
                adj += 4.0
                why.append("WR depth need")
            elif rnd<=11 and wr<4:
                adj += 2.0
                why.append("WR depth")

        # RB saturation: increasingly expensive once the roster is already deep.
        if pos=="RB":
            if rb>=5:
                adj -= 10.0
                why.append("RB6+ saturation")
            elif rb>=4:
                adj -= 6.0
                why.append("RB5 opportunity cost")
            elif rb>=3 and rnd<=9 and wr<3:
                adj -= 3.5
                why.append("RB4 vs WR need")

        # v9.26 QB2 opportunity-cost correction for standard 1-QB builds.
        if pos=="QB" and qb>=1:
            qb_rows=roster[roster.position.eq("QB")] if roster is not None and len(roster) else pd.DataFrame()
            early_qb1=False
            elite_qb1=False
            if len(qb_rows):
                if "mock_round" in qb_rows.columns:
                    early_qb1=pd.to_numeric(qb_rows["mock_round"],errors="coerce").min() <= 6
                elif "draft_round" in qb_rows.columns:
                    early_qb1=pd.to_numeric(qb_rows["draft_round"],errors="coerce").min() <= 6
                if "model_rank" in qb_rows.columns:
                    elite_qb1=pd.to_numeric(qb_rows["model_rank"],errors="coerce").min() <= 36
                if "vorp" in qb_rows.columns:
                    elite_qb1=elite_qb1 or (pd.to_numeric(qb_rows["vorp"],errors="coerce").max() >= 35)

            if early_qb1 or elite_qb1:
                if rnd<=12:
                    adj -= 18.0
                    why.append("QB2 blocked by early/elite QB1")
                elif rnd<=14:
                    adj -= 10.0
                    why.append("QB2 high opportunity cost")
                else:
                    adj -= 5.0
                    why.append("late QB2 after strong QB1")
            else:
                if rnd<=10:
                    adj -= 12.0
                    why.append("QB2 after QB1")
                elif rnd<=13:
                    adj -= 10.0
                    why.append("QB2 opportunity cost")
                else:
                    adj -= 7.0
                    why.append("late QB2 must beat bench alternatives")

        # v9.29 WR foundation + RB saturation correction.
        # Prevent RB4+ accumulation from crowding out a thin WR room.
        if pos=="WR":
            if rnd>=7 and wr<4:
                adj += 12.0
                why.append("WR foundation priority")
            if rnd>=10 and wr<5:
                adj += 9.0
                why.append("WR bench-depth priority")

        if pos=="RB":
            if rb>=4 and wr<4:
                adj -= 18.0
                why.append("RB saturation vs thin WR")
            elif rb>=5 and wr<5:
                adj -= 14.0
                why.append("RB saturation vs WR depth")
            elif rb>=6:
                adj -= 20.0
                why.append("extreme RB saturation")

        # v9.44 required TE1 construction.
        # TE remains value-sensitive early, but cannot be left unfilled late.
        if pos=="TE" and te<1:
            if rnd>=13:
                adj += 16.0
                why.append("required TE still open")
            elif rnd>=9:
                adj += 8.0
                why.append("TE1 roster need")
            elif rnd>=6:
                adj += 3.0
                why.append("TE1 value window")

        # v9.30 onesie-value gate.
        # QB2/TE2 must clear actual model-value evidence; being far past ADP alone is insufficient.
        _v930_vorp = pd.to_numeric(pd.Series([r.get("vorp", np.nan)]), errors="coerce").iloc[0]
        _v930_cons = pd.to_numeric(pd.Series([r.get("consensus_rank", r.get("rank", np.nan))]), errors="coerce").iloc[0]

        if pos=="QB" and qb>=1:
            if pd.isna(_v930_vorp) or _v930_vorp < 2.0:
                adj -= 22.0
                why.append("QB2 fails exceptional-value gate")
            elif rnd<=12:
                adj -= 8.0
                why.append("QB2 exceptional value but early")

        if pos=="TE" and te>=1:
            if pd.isna(_v930_vorp) or _v930_vorp < 2.0:
                adj -= 18.0
                why.append("TE2 fails exceptional-value gate")
            elif rnd<=11:
                adj -= 7.0
                why.append("TE2 exceptional value but early")

        # v9.27.1 coordinated TE2 opportunity cost.
        # Preserve the existing v9.26 QB2 logic unchanged. TE2 now competes
        # more directly with unfinished WR/RB bench depth, but remains a soft penalty.
        offense_depth_thin = (wr < (4 if rnd<=12 else 5)) or (rb < (4 if rnd<=11 else 5))
        if pos=="TE" and te>=1:
            if rnd<=10 and offense_depth_thin:
                adj -= 18.0
                why.append("TE2 vs unfinished WR/RB depth")
            elif rnd<=12 and offense_depth_thin:
                adj -= 11.0
                why.append("TE2 opportunity cost vs depth")
            else:
                adj -= 7.0
                why.append("TE2 must beat bench alternatives")

        # Delay IDP if core offense is still materially incomplete.
        core_offense_incomplete = (wr<4) or (qb<1) or (te<1)
        if pos in ["DL","DB"] and rnd<=12 and core_offense_incomplete:
            if pos=="DB":
                adj -= 9.0
                why.append("DB vs unfinished offense")
            else:
                adj -= 7.0
                why.append("DL vs unfinished offense")

        # v9.34 dedicated IDP impact mechanism.
        if pos in ["DL","DB"]:
            _idp_score, _idp_eligible, _idp_evidence = _v934_idp_impact_score(r)
            _idp_vorp = _v934_num(r, "vorp", "VORP")
            if not _idp_eligible:
                adj -= 75.0
                why.append("IDP insufficient evidence")
            else:
                adj += min(max(_idp_score, -10.0), 20.0)
                why.append(f"IDP impact {_idp_score:.1f}")
            if pd.notna(_idp_vorp) and _idp_vorp <= 0 and _idp_score < 8.0:
                adj -= 30.0
                why.append("IDP zero-VORP without impact support")
            _idp_market = _v934_num(r, "market_pick", "adp", "consensus_pick")
            _idp_rank = _v934_num(r, "consensus_rank", "rank", "model_rank")
            if pos=="DB" and pd.isna(_idp_market) and pd.isna(_idp_rank):
                adj -= 28.0
                why.append("DB lacks independent market support")

        # Harder pressure against early DB specifically; DB is usually replaceable.
        if pos=="DB" and rnd<=10:
            adj -= 4.0
            why.append("early DB cost")

        # V6.11 consolidated IDP depth economics. Required DL/DB starters still
        # receive normal discipline, but a Tier 1-2 IDP3 is not triple-taxed by
        # starter-filled + depth + exact-construction penalties.
        _tier_depth=pd.to_numeric(pd.Series([r.get("idp_quality_tier",np.nan)]),errors="coerce").iloc[0]
        _impact_depth=pd.to_numeric(pd.Series([r.get("idp_impact_score",np.nan)]),errors="coerce").iloc[0]
        _elite_depth=(pd.notna(_tier_depth) and _tier_depth<=2) or (pd.notna(_impact_depth) and _impact_depth>=8.0)
        _idp_count_now=dl+db
        if pos=="DL" and dl>=1:
            adj -= 4.0 if (_idp_count_now>=2 and _elite_depth and rnd>=11) else 22.0
            why.append("elite DL3 bench competition" if (_idp_count_now>=2 and _elite_depth and rnd>=11) else "DL starter already filled")
        if pos=="DB" and db>=1:
            adj -= 4.0 if (_idp_count_now>=2 and _elite_depth and rnd>=11) else 22.0
            why.append("elite DB3 bench competition" if (_idp_count_now>=2 and _elite_depth and rnd>=11) else "DB starter already filled")

        # v9.27.1 conditional IDP2 opportunity cost.
        # A second defender is optional depth, not a required roster target.
        # If offensive depth is still thin, discourage IDP2. Once offense is healthy
        # and the draft is late, allow a strong second defender to win naturally.
        idp_count=dl+db
        if pos in ["DL","DB"] and idp_count>=2:
            # A third defender is a value-responsive bench option only.
            _tier=pd.to_numeric(pd.Series([r.get("idp_quality_tier",np.nan)]),errors="coerce").iloc[0]
            _impact=pd.to_numeric(pd.Series([r.get("idp_impact_score",np.nan)]),errors="coerce").iloc[0]
            _elite_extra=(pd.notna(_tier) and _tier<=2) or (pd.notna(_impact) and _impact>=8.0)
            if offense_depth_thin:
                adj -= 4.0 if _elite_extra and rnd>=11 else 14.0
                why.append("elite IDP3 vs depth competition" if _elite_extra and rnd>=11 else "IDP3 vs offensive depth")
            elif rnd<=12:
                adj -= 10.0
                why.append("IDP3 too early")
            elif _elite_extra:
                adj += 2.5
                why.append("elite late IDP3 value")
            else:
                adj -= 8.0
                why.append("non-impact IDP3")
        elif pos in ["DL","DB"] and idp_count>=1:
            if offense_depth_thin:
                adj -= 8.0
                why.append("IDP2 vs offensive depth")
            elif rnd<=11:
                adj -= 4.0
                why.append("early IDP2 opportunity cost")
            else:
                adj += 0.5
                why.append("late IDP2 neutral")

        # Guarantee starter needs near the end.
        picks_left=max(0, int(slots.get("QB",0)+slots.get("RB",0)+slots.get("WR",0)+slots.get("TE",0)+
                              slots.get("DL",0)+slots.get("DB",0)+slots.get("FLEX",0)+slots.get("K",0)) - len(roster))
        missing_required=0
        for p in ["QB","RB","WR","TE","DL","DB"]:
            missing_required += max(int(slots.get(p,0))-int(counts.get(p,0)),0)
        if picks_left<=missing_required+1:
            if counts.get(pos,0) < int(slots.get(pos,0)):
                adj += 10.0
                why.append("required starter urgency")

        # Extreme-faller relief: preserve the ability to take truly unusual value.
        mp=pd.to_numeric(pd.Series([r.get("market_pick",np.nan)]),errors="coerce").iloc[0]
        if pd.notna(mp):
            fall=max(cur-float(mp),0.0)
            if fall>=24 and adj<0:
                adj *= 0.35
                why.append("extreme-faller relief")
            elif fall>=16 and adj<0:
                adj *= 0.60
                why.append("faller relief")

        adjustments.append(float(adj))
        reasons.append("; ".join(why) if why else "balanced")

    x["roster_opportunity_adj"]=adjustments
    x["roster_opportunity_note"]=reasons
    return x


def apply_v932_exact_league_construction(df, roster, round_no, rounds, slots):
    """Exact user league shape: 1 QB, 2 RB, 2 WR, 2 FLEX, 1 K, 1 DL, 1 DB, 6 bench.
    K is reserved for the endgame and ranked with market-derived projection plus position-relative VORP.
    """
    x=df.copy()
    if x.empty or "evaluation_score" not in x.columns:
        return x
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    rnd=int(round_no); total=int(rounds)
    qb,rb,wr,te,dl,db=[int(counts.get(p,0)) for p in ["QB","RB","WR","TE","DL","DB"]]
    flex_eligible=rb+wr+te
    # Two FLEX means six RB/WR/TE starter-quality bodies are required before pure depth.
    for idx,r in x.iterrows():
        pos=str(r.get("position","")); adj=0.0; why=[]
        if pos in ["RB","WR","TE"]:
            if flex_eligible < 6:
                adj += 4.5
                why.append("2-FLEX starter construction")
            if pos=="WR" and wr<2: adj += 4.0
            if pos=="RB" and rb<2: adj += 3.0
        # Strong QB2/TE2 suppression: bench backups must beat real FLEX/depth opportunity cost.
        if pos=="QB" and qb>=1:
            adj -= 16.0 if rnd<=14 else 8.0
            why.append("1-QB league QB2 bench tax")
        if pos=="TE" and te>=1 and flex_eligible>=6:
            adj -= 8.0
            why.append("TE2 must win FLEX/bench opportunity cost")
        # Kicker is mandatory, but preserve upside bench capital until the endgame.
        if pos=="K":
            k=int(counts.get("K",0))
            if k>=1:
                adj -= 50.0
                why.append("kicker slot already filled")
            elif rnd < total:
                adj -= 24.0
                why.append("required K reserved for final round")
            else:
                adj += 80.0
                why.append("final-round required kicker")
        # Do not force IDP before the offensive starting shell is built.
        if pos in ["DL","DB"] and flex_eligible<6 and rnd<=12:
            adj -= 8.0
            why.append("finish 2-FLEX offensive shell first")
        # V6.11: extra IDP is optional but merit-based. Tier 1-2 impact defenders
        # may compete with offensive bench depth; replacement extras keep the full tax.
        if pos in ("DL","DB") and ((pos=="DL" and dl>=1) or (pos=="DB" and db>=1)):
            _tier_v=pd.to_numeric(pd.Series([r.get("idp_quality_tier",5)]),errors="coerce").fillna(5).iloc[0]
            _vorp_v=pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0]
            if float(_tier_v)<=2 and float(_vorp_v)>=1.0 and rnd>=11:
                adj -= 4.0
                why.append("impact IDP3 bench competition")
            else:
                adj -= 30.0
                why.append("replacement extra IDP bench tax")
        if adj:
            x.at[idx,"evaluation_score"]=float(x.at[idx,"evaluation_score"])+adj
            if "roster_opportunity_adj" in x.columns:
                x.at[idx,"roster_opportunity_adj"]=float(x.at[idx,"roster_opportunity_adj"])+adj
            if "roster_opportunity_note" in x.columns and why:
                old=str(x.at[idx,"roster_opportunity_note"])
                x.at[idx,"roster_opportunity_note"]=(old+"; "+"; ".join(why)).strip("; ")
    return x



def apply_v933_context_quality_gate(df, roster, round_no, current_pick):
    """Context-card only gate: stop shallow-league IDPs from camping above useful offensive challengers.
    Does NOT change FINAL PICK evaluation_score.
    """
    x=df.copy()
    if x.empty:
        return x
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    x["context_score"]=pd.to_numeric(x["evaluation_score"],errors="coerce").fillna(-999.0)
    for idx,r in x.iterrows():
        if str(r.get("position","")) not in ["DL","DB"]:
            continue
        pos=str(r.get("position"))
        vorp=float(pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
        mp=pd.to_numeric(pd.Series([r.get("market_pick",np.nan)]),errors="coerce").iloc[0]
        _impact,_eligible,_evidence=_v934_idp_impact_score(r)
        penalty=0.0
        if not _eligible: penalty += 45.0
        if _impact < 6.0: penalty += 18.0
        # Exact league starts only one DL and one DB; an IDP context target must be actionable,
        # not merely a high raw model score.
        if int(round_no)<=10: penalty += 18.0
        elif int(round_no)<=12: penalty += 10.0
        elif int(round_no)<=14: penalty += 5.0
        if vorp < 1.50: penalty += 8.0
        # If market says the defender should still be there later, suppress repeated WAIT cards.
        if pd.notna(mp) and float(mp)-float(current_pick) >= 18: penalty += 10.0
        if pd.notna(mp) and float(mp)-float(current_pick) >= 36: penalty += 8.0
        # Never feature a second player at an already-filled one-IDP position.
        if int(counts.get(pos,0))>=1: penalty += 40.0
        x.at[idx,"context_score"]-=penalty
    return x

def apply_v931_idp_opportunity_gate(df, roster, round_no):
    """Compare IDPs directly with the best remaining offensive value after roster adjustments."""
    x=df.copy()
    if "evaluation_score" not in x.columns or x.empty:
        return x
    off=x[~x.position.isin(["DL","DB"])]
    if off.empty:
        return x
    best_off=float(pd.to_numeric(off.evaluation_score,errors="coerce").max())
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    depth_thin=(counts.get("WR",0)<5) or (counts.get("RB",0)<4)
    idp_mask=x.position.isin(["DL","DB"])
    for idx,r in x.loc[idp_mask].iterrows():
        score=float(pd.to_numeric(pd.Series([r.get("evaluation_score",-999)]),errors="coerce").fillna(-999).iloc[0])
        vorp=float(pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
        _impact,_eligible,_evidence=_v934_idp_impact_score(r)
        penalty=0.0
        note=[]
        if not _eligible:
            penalty += 35.0
            note.append("fails IDP evidence gate")
        if _impact < 6.0:
            penalty += 12.0
            note.append("below IDP impact floor")
        if vorp < 0.75:
            penalty += 14.0
            note.append("fails IDP replacement-level gate")
        if depth_thin and int(round_no)<=15 and score < best_off-4.0:
            penalty += min(10.0, max(0.0,(best_off-score-4.0)*0.35))
            note.append("offensive opportunity cost")
        if penalty:
            x.at[idx,"evaluation_score"]=score-penalty
            old=str(x.at[idx,"roster_opportunity_note"]) if "roster_opportunity_note" in x.columns else ""
            x.at[idx,"roster_opportunity_note"]=(old+"; "+"; ".join(note)).strip("; ")
            if "roster_opportunity_adj" in x.columns:
                x.at[idx,"roster_opportunity_adj"]=float(x.at[idx,"roster_opportunity_adj"])-penalty
    # v9.40 evidence authority: failed IDP evidence cannot be rescued by roster need.
    if "idp_eligible" in x.columns:
        bad=x["position"].isin(["DL","DB"]) & (~x["idp_eligible"].fillna(False).astype(bool))
        x.loc[bad,"evaluation_score"]-=100.0
    return x


def _market_pick_series(df, teams):
    """V7.59 live/default champion market transform, certified by V7.58."""
    cr=pd.to_numeric(df["consensus_rank"],errors="coerce")
    out=cr.copy()
    idp=df["position"].isin(["DL","DB"])
    transformed=float(teams)*8 + (cr.loc[idp].fillna(40)-1)*2.0
    cap=cr.loc[idp].fillna(40) + float(teams)*8
    out.loc[idp]=np.minimum(transformed,cap)
    return out

def _board_with_vorp_variant(board, teams, slots, flex_alloc=None, vorp_weight=9.0):
    """Hypothetical valuation board used only by V7.29 matched calibration."""
    b=board.copy()
    teams=max(int(teams),1)
    flex=float(slots.get("FLEX",1))
    alloc={"RB":.38,"WR":.55,"TE":.07} if flex_alloc is None else {
        "RB":float(flex_alloc["RB"]),"WR":float(flex_alloc["WR"]),"TE":float(flex_alloc["TE"])
    }
    replacement_slots={
        "QB":max(teams*int(slots.get("QB",1)),teams),
        "RB":max(int(round(teams*(float(slots.get("RB",2))+flex*alloc["RB"]))),teams),
        "WR":max(int(round(teams*(float(slots.get("WR",2))+flex*alloc["WR"]))),teams),
        "TE":max(int(round(teams*(float(slots.get("TE",1))+flex*alloc["TE"]))),teams),
        "DL":max(teams*int(slots.get("DL",1)),teams),
        "DB":max(teams*int(slots.get("DB",1)),teams)
    }
    repl={}
    for p,n in replacement_slots.items():
        vals=pd.to_numeric(b.loc[b.position.eq(p),"projection"],errors="coerce").dropna().sort_values(ascending=False).reset_index(drop=True)
        repl[p]=float(vals.iloc[min(max(int(n)-1,0),len(vals)-1)]) if len(vals) else 0.0
    b["replacement_ppg"]=b.position.map(repl).fillna(0)
    b["vorp"]=pd.to_numeric(b.projection,errors="coerce").fillna(0)-b.replacement_ppg
    scarcity=b.position.map({"QB":0.0,"RB":0.9,"WR":1.35,"TE":0.35,"K":-1.25,"DL":-0.35,"DB":-0.45}).fillna(0)
    b["pure_model_score"]=(
        b.vorp*float(vorp_weight)
        +pd.to_numeric(b.projection,errors="coerce").fillna(0)*1.6
        +pd.to_numeric(b.progression,errors="coerce").fillna(0)*.12
        -pd.to_numeric(b.regression,errors="coerce").fillna(0)*.10
        +scarcity
    )
    b["model_rank"]=b.pure_model_score.rank(method="min",ascending=False)
    b["draft_score"]=b.pure_model_score+pd.to_numeric(b.consensus_strength,errors="coerce").fillna(45)*.10
    b["consensus_edge"]=b.consensus_rank-b.model_rank
    b.attrs["replacement_slots"]=replacement_slots
    return b


def _fast_benchmark_pool(board, teams=12):
    """Convert the static draft board to NumPy arrays once per benchmark run."""
    pool=board[board.position.isin(["QB","RB","WR","TE","DL","DB"])].copy().reset_index(drop=True)
    pos_names=np.array(["QB","RB","WR","TE","DL","DB"],dtype=object)
    pos_map={p:i for i,p in enumerate(pos_names)}
    pos_code=pool.position.map(pos_map).to_numpy(dtype=np.int8)
    consensus=pd.to_numeric(pool.consensus_rank,errors="coerce").to_numpy(dtype=float)
    market_pick=_market_pick_series(pool,teams).to_numpy(dtype=float)
    model_rank=pd.to_numeric(pool.model_rank,errors="coerce").to_numpy(dtype=float)
    draft_score=pd.to_numeric(pool.draft_score,errors="coerce").fillna(-1e9).to_numpy(dtype=float)
    projection=pd.to_numeric(pool.projection,errors="coerce").fillna(0).to_numpy(dtype=float)
    vorp=pd.to_numeric(pool.vorp,errors="coerce").fillna(0).to_numpy(dtype=float)
    replacement_ppg=pd.to_numeric(pool.replacement_ppg,errors="coerce").fillna(0).to_numpy(dtype=float)
    # Diagnostic replacement ranks by position, derived from the league's frozen
    # V7.24 replacement demand assumptions. These are not used in drafting.
    flex=float(1.0)
    replacement_demand={
        "QB":max(int(teams*1),int(teams)),
        "RB":max(int(round(teams*(2.0+flex*.38))),int(teams)),
        "WR":max(int(round(teams*(2.0+flex*.55))),int(teams)),
        "TE":max(int(round(teams*(1.0+flex*.07))),int(teams)),
        "DL":max(int(teams*1),int(teams)),
        "DB":max(int(teams*1),int(teams))
    }
    replacement_rank=np.array([replacement_demand.get(str(p),int(teams)) for p in pool.position],dtype=float)
    progression=pd.to_numeric(pool.progression,errors="coerce").fillna(0).to_numpy(dtype=float)
    regression=pd.to_numeric(pool.regression,errors="coerce").fillna(0).to_numpy(dtype=float)
    consensus_strength=pd.to_numeric(pool.consensus_strength,errors="coerce").fillna(45).to_numpy(dtype=float)
    pure_model_score=pd.to_numeric(pool.pure_model_score,errors="coerce").fillna(0).to_numpy(dtype=float)
    scarcity=np.array([{"QB":0.0,"RB":0.9,"WR":1.35,"TE":0.35,"K":-1.25,"DL":-0.35,"DB":-0.45}.get(str(p),0.0)
                       for p in pool.position],dtype=float)
    injury=np.array([_injury_severity(x) for x in pool.injury],dtype=np.int8)
    confidence=pd.to_numeric(pool.confidence,errors="coerce").fillna(.65).clip(.30,.95).to_numpy(dtype=float)
    return {"pool":pool,"pos_names":pos_names,"pos_code":pos_code,"consensus":consensus,
            "market_pick":market_pick,"model_rank":model_rank,"draft_score":draft_score,
            "projection":projection,"vorp":vorp,"replacement_ppg":replacement_ppg,
            "replacement_rank":replacement_rank,
            "progression":progression,"regression":regression,
            "consensus_strength":consensus_strength,"pure_model_score":pure_model_score,
            "scarcity":scarcity,"injury":injury,"confidence":confidence}


def _fast_roster_utility(fast, selected, slots, te_starter_vorp_mult=.90):
    """Small-array roster utility used by the benchmark engine."""
    if len(selected)==0: return 0.0
    idx=np.asarray(selected,dtype=int)
    pos=fast["pos_code"][idx]; proj=fast["projection"][idx]; vorp=fast["vorp"][idx]
    base=proj+0.70*np.clip(vorp,-5,None)
    used=np.zeros(len(idx),dtype=bool); total=0.0
    # Required starters by position.
    for code,pname in enumerate(["QB","RB","WR","TE","DL","DB"]):
        n=max(int(slots.get(pname,0)),0)
        loc=np.flatnonzero(pos==code)
        if not len(loc) or n<=0: continue
        order=loc[np.argsort(base[loc])[::-1]]
        take=order[:n]; used[take]=True
        _starter_vorp_mult=float(te_starter_vorp_mult) if pname=="TE" else .90
        total += float(np.sum(proj[take]+_starter_vorp_mult*vorp[take]))
    # FLEX from unused RB/WR/TE.
    flex_n=max(int(slots.get("FLEX",0)),0)
    loc=np.flatnonzero((~used)&np.isin(pos,[1,2,3]))
    if len(loc) and flex_n>0:
        order=loc[np.argsort(base[loc])[::-1]]; take=order[:flex_n]; used[take]=True
        total += float(np.sum(.92*proj[take]+.75*vorp[take]))
    # Bench insurance/upside utility.
    mults={0:[.14,.03],1:[.25,.15,.08,.03],2:[.40,.30,.20,.11,.06],3:[.16,.04],4:[.06],5:[.06]}
    for code in range(6):
        loc=np.flatnonzero((~used)&(pos==code))
        if not len(loc): continue
        order=loc[np.argsort(base[loc])[::-1]]
        for d,j in enumerate(order):
            arr=mults[code]; m=arr[d] if d<len(arr) else .02
            total += float(m*(proj[j]+.55*max(vorp[j],0)))
    return float(total)


def _fast_roster_role_snapshot(fast, selected, candidate, slots):
    """Diagnostic-only explanation of how one candidate is valued by roster utility."""
    before=[int(x) for x in selected]
    cand=int(candidate)
    after=before+[cand]

    current=_fast_roster_utility(fast,before,slots)
    new=_fast_roster_utility(fast,after,slots)
    delta=float(new-current)

    idx=np.asarray(after,dtype=int)
    pos=fast["pos_code"][idx]
    proj=fast["projection"][idx]
    vorp=fast["vorp"][idx]
    base=proj+0.70*np.clip(vorp,-5,None)
    used=np.zeros(len(idx),dtype=bool)
    roles=np.array(["bench"]*len(idx),dtype=object)

    for code,pname in enumerate(["QB","RB","WR","TE","DL","DB"]):
        n=max(int(slots.get(pname,0)),0)
        loc=np.flatnonzero(pos==code)
        if not len(loc) or n<=0:
            continue
        order=loc[np.argsort(base[loc])[::-1]]
        take=order[:n]
        used[take]=True
        roles[take]="starter"

    flex_n=max(int(slots.get("FLEX",0)),0)
    loc=np.flatnonzero((~used)&np.isin(pos,[1,2,3]))
    if len(loc) and flex_n>0:
        order=loc[np.argsort(base[loc])[::-1]]
        take=order[:flex_n]
        used[take]=True
        roles[take]="flex"

    j=len(idx)-1
    cand_role=str(roles[j])
    pcode=int(pos[j])
    pname=["QB","RB","WR","TE","DL","DB"][pcode]
    counts_before={name:int(np.sum(fast["pos_code"][before]==code)) if len(before) else 0
                   for code,name in enumerate(["QB","RB","WR","TE","DL","DB"])}

    direct_slots=int(slots.get(pname,0))
    direct_missing=max(direct_slots-counts_before.get(pname,0),0)
    flex_eligible=pname in ["RB","WR","TE"]

    if cand_role=="starter":
        role_proj=float(proj[j])
        role_vorp=.90*float(vorp[j])
    elif cand_role=="flex":
        role_proj=.92*float(proj[j])
        role_vorp=.75*float(vorp[j])
    else:
        mults={0:[.14,.03],1:[.25,.15,.08,.03],2:[.40,.30,.20,.11,.06],3:[.16,.04],4:[.06],5:[.06]}
        same_bench=np.flatnonzero((roles=="bench")&(pos==pcode))
        order=same_bench[np.argsort(base[same_bench])[::-1]]
        depth=list(order).index(j) if j in list(order) else 0
        arr=mults[pcode]
        mult=arr[depth] if depth<len(arr) else .02
        role_proj=mult*float(proj[j])
        role_vorp=mult*.55*max(float(vorp[j]),0)

    return {
        "utility_before":float(current),
        "utility_after":float(new),
        "utility_delta":delta,
        "role":cand_role,
        "position":pname,
        "projection":float(proj[j]),
        "vorp":float(vorp[j]),
        "replacement_ppg":float(fast["replacement_ppg"][cand]),
        "role_projection_component":float(role_proj),
        "role_vorp_component":float(role_vorp),
        "role_component_sum":float(role_proj+role_vorp),
        "direct_missing_before":int(direct_missing),
        "flex_eligible":bool(flex_eligible),
        "QB_before":counts_before["QB"],"RB_before":counts_before["RB"],
        "WR_before":counts_before["WR"],"TE_before":counts_before["TE"],
    }


def _fast_candidate_deltas(fast, selected, candidates, slots, exact_cap=56, te_starter_vorp_mult=.90):
    """Exact V7.3 utility on a bounded shortlist chosen from model + market value."""
    cand=np.asarray(candidates,dtype=int)
    if cand.size==0: return cand,np.array([],dtype=float)
    n=min(int(exact_cap),cand.size)
    ds=fast["draft_score"][cand]
    cr=fast["market_pick"][cand]
    cr2=np.where(np.isnan(cr),999.0,cr)
    k1=max(1,n//3); k2=max(1,n//3)
    ai=np.argpartition(-ds,min(k1-1,cand.size-1))[:k1]
    bi=np.argpartition(cr2,min(k2-1,cand.size-1))[:k2]
    # Reserve shortlist space for the best available players at each position.
    pi=[]
    pc=fast["pos_code"][cand]
    per=max(2,n//18)
    for code in range(6):
        loc=np.flatnonzero(pc==code)
        if loc.size:
            take=min(per,loc.size)
            best=loc[np.argpartition(-ds[loc],min(take-1,loc.size-1))[:take]]
            pi.extend(best.tolist())
    local=np.unique(np.concatenate([ai,bi,np.asarray(pi,dtype=int)]))
    if local.size>n:
        composite=(-ds[local])+0.05*cr2[local]
        local=local[np.argsort(composite)[:n]]
    short=cand[local]
    current=_fast_roster_utility(fast,selected,slots,te_starter_vorp_mult=te_starter_vorp_mult)
    delta=np.asarray([_fast_roster_utility(fast,selected+[int(c)],slots,te_starter_vorp_mult=te_starter_vorp_mult)-current for c in short],dtype=float)
    return short,delta

def independent_draft_grade_components(draft, teams=12):
    """Independent diagnostic components; excludes FE projection/VORP/regression/draft_score/utility weights."""
    if draft is None or len(draft)==0:
        return {"overall":0.0,"market_value":0.0,"starter_completion":0.0,"roster_balance":0.0,
                "availability":0.0,"avg_market_delta":0.0,"avg_reach":0.0,"avg_faller":0.0,
                "big_reaches":0,"missing_starters":6}
    d=draft.copy()
    market=pd.to_numeric(d.get("market_pick",d.get("consensus_rank")),errors="coerce")
    pick=pd.to_numeric(d["mock_pick"],errors="coerce")
    delta=(pick-market).fillna(0)
    market_value=float(.70*delta.clip(-18,18).mean())
    avg_reach=float(np.maximum(market-pick,0).fillna(0).mean())
    avg_faller=float(np.maximum(pick-market,0).fillna(0).mean())
    big_reaches=int(((market-pick)>=18).fillna(False).sum())
    counts=d.position.value_counts().to_dict()
    missing=sum(max(n-counts.get(p,0),0) for p,n in {"QB":1,"RB":2,"WR":2,"TE":1,"DL":1,"DB":1}.items())
    starter_completion=float(-8*missing)
    balance=0.0
    if counts.get("RB",0)<3: balance-=3
    if counts.get("WR",0)<3: balance-=3
    if counts.get("QB",0)>2: balance-=2*(counts["QB"]-2)
    if counts.get("TE",0)>2: balance-=1.5*(counts["TE"]-2)
    inj=d.injury.fillna("").astype(str).str.lower()
    availability=float(-8*inj.isin(["ir","pup","nfi","reserve/ir","reserve/pup"]).sum()-4*inj.isin(["out","suspended","susp"]).sum())
    overall=float(np.clip(70+market_value+starter_completion+balance+availability,0,100))
    return {"overall":overall,"market_value":market_value,"starter_completion":starter_completion,
            "roster_balance":float(balance),"availability":availability,"avg_market_delta":float(delta.mean()),
            "avg_reach":avg_reach,"avg_faller":avg_faller,"big_reaches":big_reaches,"missing_starters":int(missing)}

def independent_draft_grade(draft, teams=12):
    return independent_draft_grade_components(draft,teams)["overall"]


def draft_phase(round_no):
    r=int(round_no)
    if r<=3: return "R1-3"
    if r<=6: return "R4-6"
    if r<=10: return "R7-10"
    return "R11+"

def independent_phase_metrics(draft):
    """Pick-level independent market/timing attribution by draft phase.

    Uses only mock pick, market pick, round, position and model rank metadata for
    descriptive diagnostics. It does not feed back into draft decisions.
    """
    if draft is None or len(draft)==0:
        return pd.DataFrame(columns=[
            "Phase","Picks","Avg_market_delta","Avg_reach","Avg_faller",
            "Big_reaches","Avg_model_rank","QB","RB","WR","TE","DL","DB"
        ])

    d=draft.copy()
    d["mock_pick"]=pd.to_numeric(d["mock_pick"],errors="coerce")
    d["mock_round"]=pd.to_numeric(d["mock_round"],errors="coerce").fillna(0).astype(int)
    d["market_pick_num"]=pd.to_numeric(d.get("market_pick",d.get("consensus_rank")),errors="coerce")
    d["model_rank_num"]=pd.to_numeric(d.get("model_rank"),errors="coerce")
    d["Phase"]=d.mock_round.map(draft_phase)
    d["market_delta"]=(d.mock_pick-d.market_pick_num).fillna(0)   # + = faller captured
    d["reach"]=np.maximum(d.market_pick_num-d.mock_pick,0).fillna(0)
    d["faller"]=np.maximum(d.mock_pick-d.market_pick_num,0).fillna(0)
    d["big_reach"]=(d.reach>=18).astype(int)

    rows=[]
    for phase in ["R1-3","R4-6","R7-10","R11+"]:
        g=d[d.Phase.eq(phase)]
        counts=g.position.value_counts().to_dict() if len(g) else {}
        rows.append({
            "Phase":phase,
            "Picks":int(len(g)),
            "Avg_market_delta":float(g.market_delta.mean()) if len(g) else 0.0,
            "Avg_reach":float(g.reach.mean()) if len(g) else 0.0,
            "Avg_faller":float(g.faller.mean()) if len(g) else 0.0,
            "Big_reaches":int(g.big_reach.sum()) if len(g) else 0,
            "Avg_model_rank":float(g.model_rank_num.mean()) if len(g) and g.model_rank_num.notna().any() else np.nan,
            "QB":int(counts.get("QB",0)),"RB":int(counts.get("RB",0)),
            "WR":int(counts.get("WR",0)),"TE":int(counts.get("TE",0)),
            "DL":int(counts.get("DL",0)),"DB":int(counts.get("DB",0))
        })
    return pd.DataFrame(rows)

def _room_profile(name):
    return {
      "Consensus":(.95,0.0,0.0),
      "ADP-heavy":(.45,0.0,0.0),
      "Chaotic":(1.85,0.0,0.0),
      "Positional runs":(1.00,1.0,0.0),
      "Sharp/value":(.70,0.0,1.0)
    }.get(name,(1.0,0.0,0.0))

def simulate_mock_fast_pick7_recovery_trace(fast,teams,slot,rounds,slots,randomness=12,seed=None,room_profile="Consensus",intercept_enabled=False):
    out=simulate_mock_fast(
        fast,teams,slot,rounds,slots,randomness,True,seed,room_profile,
        late_wr_enabled=bool(intercept_enabled),late_wr_eval_deficit=8.0,
        late_wr_survival=.35,late_wr_slots=(7,)
    )
    keep=[c for c in ["mock_pick","mock_round","player","position","team","market_pick","market_delta","faller","reach","value"] if c in out.columns]
    return out,out[keep].copy()


def mid_round_pipeline_audit_snapshot(fast, candidate_idx, delta, edge, eval_score, chosen_global,
                                      current_pick, next_pick, randomness=12):
    """Diagnostic-only R4-6 decision audit. Never changes the selected player."""
    cand=np.asarray(candidate_idx,dtype=int)
    delta=np.asarray(delta,dtype=float)
    edge=np.asarray(edge,dtype=float)
    ev=np.asarray(eval_score,dtype=float)
    pool=fast["pool"]; pos=fast["pos_code"]; market=fast["market_pick"]
    model_rank=fast["model_rank"]; projection=fast["projection"]; vorp=fast["vorp"]
    replacement_ppg=fast["replacement_ppg"]; replacement_rank=fast["replacement_rank"]; progression=fast["progression"]
    regression=fast["regression"]; consensus_strength=fast["consensus_strength"]
    pure_model_score=fast["pure_model_score"]; scarcity=fast["scarcity"]
    draft_score=fast["draft_score"]
    chosen_global=int(chosen_global)

    loc=np.flatnonzero(cand==chosen_global)
    chosen_eval=float(ev[int(loc[0])]) if len(loc) else np.nan
    cmp=float(market[chosen_global]) if np.isfinite(market[chosen_global]) else np.nan
    cmr=float(model_rank[chosen_global]) if np.isfinite(model_rank[chosen_global]) else np.nan

    snap={
        "MR_Audit":1,
        "MR_Selected_player":str(pool.iloc[chosen_global].player),
        "MR_Selected_position":str(pool.iloc[chosen_global].position),
        "MR_Selected_eval":chosen_eval,
        "MR_Selected_market_pick":cmp,
        "MR_Selected_model_rank":cmr,
        "MR_Selected_projection":float(projection[chosen_global]),
        "MR_Selected_vorp":float(vorp[chosen_global]),
        "MR_Selected_reach":max(cmp-float(current_pick),0) if np.isfinite(cmp) else np.nan,
        "MR_Selected_faller":max(float(current_pick)-cmp,0) if np.isfinite(cmp) else np.nan,
        "MR_Selected_survival_est":survival_probability(cmp,next_pick,randomness) if np.isfinite(cmp) else np.nan,
        "MR_Market_best_player":"",
        "MR_Market_best_position":"",
        "MR_Market_best_pick":np.nan,
        "MR_Market_best_eval":np.nan,
        "MR_Market_best_survival_est":np.nan,
        "MR_Market_best_survived_actual":np.nan,
        "MR_Market_best_idx":None,
        "MR_Eval_best_player":"",
        "MR_Eval_best_position":"",
        "MR_Eval_best_market_pick":np.nan,
        "MR_Eval_best_score":np.nan,
        "MR_Eval_gap_selected_vs_market_best":np.nan,
        "MR_Market_gap_selected_vs_market_best":np.nan,
        "MR_Passed_faller_player":"",
        "MR_Passed_faller_position":"",
        "MR_Passed_faller_amount":0.0,
        "MR_Passed_faller_eval_gap":np.nan,
        "MR_Passed_faller_survival_est":np.nan,
        "MR_Passed_faller_survived_actual":np.nan,
        "MR_Passed_faller_idx":None,
        "MR42_Faller_draftscore_gap":np.nan,
        "MR42_Faller_rosterutility_gap":np.nan,
        "MR42_Faller_marketedge_gap":np.nan,
        "MR42_Faller_injury_gap":np.nan,
        "MR42_Faller_idp_penalty_gap":np.nan,
        "MR42_Faller_residual_noise_gap":np.nan,
        "MR42_Faller_vorp_gap":np.nan,
        "MR42_Faller_projection_gap":np.nan,
        "MR42_Faller_progression_gap":np.nan,
        "MR42_Faller_regression_gap":np.nan,
        "MR42_Faller_scarcity_gap":np.nan,
        "MR42_Faller_consensus_gap":np.nan,
        "MR42_Faller_component_sum":np.nan,
        "MR42_Faller_position":"",
        "MR43_TE_architecture_audit":0,
        "MR43_Selected_role":"",
        "MR43_Faller_role":"",
        "MR43_Selected_utility_delta":np.nan,
        "MR43_Faller_utility_delta":np.nan,
        "MR43_Utility_delta_gap":np.nan,
        "MR43_Selected_role_proj":np.nan,
        "MR43_Selected_role_vorp":np.nan,
        "MR43_Faller_role_proj":np.nan,
        "MR43_Faller_role_vorp":np.nan,
        "MR43_Selected_replacement_ppg":np.nan,
        "MR43_Faller_replacement_ppg":np.nan,
        "MR43_Replacement_gap":np.nan,
        "MR43_Selected_direct_missing":np.nan,
        "MR43_Faller_direct_missing":np.nan,
        "MR43_QB_before":np.nan,
        "MR43_RB_before":np.nan,
        "MR43_WR_before":np.nan,
        "MR43_TE_before":np.nan,
        "MR_Chosen_draftscore_component":np.nan,
        "MR_Chosen_rosterdelta_component":np.nan,
        "MR_Chosen_edge_component":np.nan,
        "MR_MarketBest_draftscore_component":np.nan,
        "MR_MarketBest_rosterdelta_component":np.nan,
        "MR_MarketBest_edge_component":np.nan,
        "MR_ComponentGap_draftscore":np.nan,
        "MR_ComponentGap_rosterdelta":np.nan,
        "MR_ComponentGap_edge":np.nan,
        "MR_Primary_component_driver":"",
        "MR_Positional_conflict":0,
        "MR_Conflict_alt_player":"",
        "MR_Conflict_alt_position":"",
        "MR_Conflict_eval_gap":np.nan,
        "MR_Conflict_draftscore_gap":np.nan,
        "MR_Conflict_rosterdelta_gap":np.nan,
        "MR_Conflict_edge_gap":np.nan,
        "MR_Conflict_market_gap":np.nan,
        "MR_Conflict_projection_raw_gap":np.nan,
        "MR_Conflict_replacement_raw_gap":np.nan,
        "MR_Conflict_vorp_raw_gap":np.nan,
        "MR_Conflict_progression_raw_gap":np.nan,
        "MR_Conflict_regression_raw_gap":np.nan,
        "MR_Conflict_scarcity_raw_gap":np.nan,
        "MR_Conflict_consensus_strength_raw_gap":np.nan,
        "MR_Conflict_vorp_component_gap":np.nan,
        "MR_Conflict_projection_component_gap":np.nan,
        "MR_Conflict_progression_component_gap":np.nan,
        "MR_Conflict_regression_component_gap":np.nan,
        "MR_Conflict_scarcity_component_gap":np.nan,
        "MR_Conflict_consensus_component_gap":np.nan,
        "MR_Conflict_pure_model_gap":np.nan,
        "MR_DraftScore_primary_driver":"",
        "MR28_Chosen_replacement_rank":np.nan,
        "MR28_Alt_replacement_rank":np.nan,
        "MR28_Base_replacement_gap":np.nan,
        "MR28_Base_vorp_gap":np.nan,
        "MR28_Alt_vorp_gap_flex_45_45_10":np.nan,
        "MR28_Alt_vorp_gap_flex_33_60_07":np.nan,
        "MR28_Alt_vorp_gap_flex_30_60_10":np.nan,
        "MR28_Alt_vorp_gap_equal_flex":np.nan,
        "MR28_Alt_vorp_gap_vorp7":np.nan,
        "MR28_Alt_vorp_gap_vorp6":np.nan,
    }

    if not len(cand):
        return snap

    # Highest FE evaluation candidate.
    ej=int(np.argmax(ev)); eg=int(cand[ej])
    snap.update({
        "MR_Eval_best_player":str(pool.iloc[eg].player),
        "MR_Eval_best_position":str(pool.iloc[eg].position),
        "MR_Eval_best_market_pick":float(market[eg]) if np.isfinite(market[eg]) else np.nan,
        "MR_Eval_best_score":float(ev[ej]),
    })

    # Earliest market-ranked candidate.
    cm=np.where(np.isnan(market[cand]),9999.0,market[cand])
    mj=int(np.argmin(cm)); mg=int(cand[mj])
    mmp=float(market[mg]) if np.isfinite(market[mg]) else np.nan
    msurv=survival_probability(mmp,next_pick,randomness) if np.isfinite(mmp) else np.nan
    snap.update({
        "MR_Market_best_player":str(pool.iloc[mg].player),
        "MR_Market_best_position":str(pool.iloc[mg].position),
        "MR_Market_best_pick":mmp,
        "MR_Market_best_eval":float(ev[mj]),
        "MR_Market_best_survival_est":msurv,
        "MR_Market_best_idx":mg,
        "MR_Eval_gap_selected_vs_market_best":chosen_eval-float(ev[mj]),
        "MR_Market_gap_selected_vs_market_best":cmp-mmp if np.isfinite(cmp) and np.isfinite(mmp) else np.nan,
    })

    # Exact V7.24 evaluation decomposition: chosen minus market-best.
    cj=int(loc[0]) if len(loc) else None
    if cj is not None:
        chosen_ds=.38*float(draft_score[chosen_global])
        chosen_rd=3.60*float(delta[cj])
        chosen_ed=.18*float(edge[cj])
        market_ds=.38*float(draft_score[mg])
        market_rd=3.60*float(delta[mj])
        market_ed=.18*float(edge[mj])
        gaps={
            "player_model/draft_score":chosen_ds-market_ds,
            "roster_marginal_utility":chosen_rd-market_rd,
            "model-vs-market_edge":chosen_ed-market_ed
        }
        snap.update({
            "MR_Chosen_draftscore_component":chosen_ds,
            "MR_Chosen_rosterdelta_component":chosen_rd,
            "MR_Chosen_edge_component":chosen_ed,
            "MR_MarketBest_draftscore_component":market_ds,
            "MR_MarketBest_rosterdelta_component":market_rd,
            "MR_MarketBest_edge_component":market_ed,
            "MR_ComponentGap_draftscore":gaps["player_model/draft_score"],
            "MR_ComponentGap_rosterdelta":gaps["roster_marginal_utility"],
            "MR_ComponentGap_edge":gaps["model-vs-market_edge"],
            "MR_Primary_component_driver":max(gaps,key=gaps.get)
        })

        # Focused conflict from V7.25: selected RB/TE while best WR/QB is available.
        if pos[chosen_global] in [1,3]:
            altloc=np.flatnonzero(np.isin(pos[cand],[0,2]))
            if len(altloc):
                # Compare against the strongest FE-evaluated WR/QB, not a forced market clone.
                aj=int(altloc[np.argmax(ev[altloc])]); ag=int(cand[aj])
                amp=float(market[ag]) if np.isfinite(market[ag]) else np.nan
                # Decompose the exact draft-score gap:
                # draft_score = VORP*9 + projection*1.6 + progression*.12
                #               - regression*.10 + scarcity + consensus_strength*.10
                vorp_raw=float(vorp[chosen_global]-vorp[ag])
                proj_raw=float(projection[chosen_global]-projection[ag])
                repl_raw=float(replacement_ppg[chosen_global]-replacement_ppg[ag])
                prog_raw=float(progression[chosen_global]-progression[ag])
                reg_raw=float(regression[chosen_global]-regression[ag])
                scarcity_raw=float(scarcity[chosen_global]-scarcity[ag])
                cons_raw=float(consensus_strength[chosen_global]-consensus_strength[ag])

                components={
                    "VORP":9.0*vorp_raw,
                    "projection":1.6*proj_raw,
                    "progression":.12*prog_raw,
                    "regression":-.10*reg_raw,
                    "positional_scarcity":scarcity_raw,
                    "consensus_reality_check":.10*cons_raw
                }
                primary=max(components,key=components.get)

                # V7.28 replacement/VORP baseline audit.
                base_gap=float(replacement_ppg[chosen_global]-replacement_ppg[ag])
                base_vorp_gap=float(vorp[chosen_global]-vorp[ag])

                scenarios={
                    "45_45_10":{"RB":.45,"WR":.45,"TE":.10},
                    "33_60_07":{"RB":.33,"WR":.60,"TE":.07},
                    "30_60_10":{"RB":.30,"WR":.60,"TE":.10},
                    "equal":{"RB":1/3,"WR":1/3,"TE":1/3},
                }
                alt_vorp={}
                for skey,alloc in scenarios.items():
                    repl_map,_dem=_diagnostic_replacement_ppg(pool,int(max(1,len(pool)//max(len(pool.position.unique()),1))),alloc)
                    cp=str(pool.iloc[chosen_global].position); ap=str(pool.iloc[ag].position)
                    cv=float(projection[chosen_global]-repl_map.get(cp,0.0))
                    av=float(projection[ag]-repl_map.get(ap,0.0))
                    alt_vorp[skey]=cv-av

                snap.update({
                    "MR_Positional_conflict":1,
                    "MR_Conflict_alt_player":str(pool.iloc[ag].player),
                    "MR_Conflict_alt_position":str(pool.iloc[ag].position),
                    "MR_Conflict_eval_gap":chosen_eval-float(ev[aj]),
                    "MR_Conflict_draftscore_gap":.38*float(draft_score[chosen_global]-draft_score[ag]),
                    "MR_Conflict_rosterdelta_gap":3.60*float(delta[cj]-delta[aj]),
                    "MR_Conflict_edge_gap":.18*float(edge[cj]-edge[aj]),
                    "MR_Conflict_market_gap":cmp-amp if np.isfinite(cmp) and np.isfinite(amp) else np.nan,
                    "MR_Conflict_projection_raw_gap":proj_raw,
                    "MR_Conflict_replacement_raw_gap":repl_raw,
                    "MR_Conflict_vorp_raw_gap":vorp_raw,
                    "MR_Conflict_progression_raw_gap":prog_raw,
                    "MR_Conflict_regression_raw_gap":reg_raw,
                    "MR_Conflict_scarcity_raw_gap":scarcity_raw,
                    "MR_Conflict_consensus_strength_raw_gap":cons_raw,
                    "MR_Conflict_vorp_component_gap":.38*components["VORP"],
                    "MR_Conflict_projection_component_gap":.38*components["projection"],
                    "MR_Conflict_progression_component_gap":.38*components["progression"],
                    "MR_Conflict_regression_component_gap":.38*components["regression"],
                    "MR_Conflict_scarcity_component_gap":.38*components["positional_scarcity"],
                    "MR_Conflict_consensus_component_gap":.38*components["consensus_reality_check"],
                    "MR_Conflict_pure_model_gap":float(pure_model_score[chosen_global]-pure_model_score[ag]),
                    "MR_DraftScore_primary_driver":primary,
                    "MR28_Chosen_replacement_rank":float(replacement_rank[chosen_global]),
                    "MR28_Alt_replacement_rank":float(replacement_rank[ag]),
                    "MR28_Base_replacement_gap":base_gap,
                    "MR28_Base_vorp_gap":base_vorp_gap,
                    "MR28_Alt_vorp_gap_flex_45_45_10":float(alt_vorp["45_45_10"]),
                    "MR28_Alt_vorp_gap_flex_33_60_07":float(alt_vorp["33_60_07"]),
                    "MR28_Alt_vorp_gap_flex_30_60_10":float(alt_vorp["30_60_10"]),
                    "MR28_Alt_vorp_gap_equal_flex":float(alt_vorp["equal"]),
                    "MR28_Alt_vorp_gap_vorp7":base_vorp_gap*(7.0/9.0),
                    "MR28_Alt_vorp_gap_vorp6":base_vorp_gap*(6.0/9.0),
                })

    # Best passed faller: most picks past market among non-selected candidates.
    falls=float(current_pick)-market[cand]
    falls=np.where(np.isnan(falls),-9999.0,falls)
    falls[cand==chosen_global]=-9999.0
    fj=int(np.argmax(falls))
    if falls[fj] > 0:
        fg=int(cand[fj]); fmp=float(market[fg])
        fsurv=survival_probability(fmp,next_pick,randomness)
        total_gap=chosen_eval-float(ev[fj])
        cj=int(loc[0]) if len(loc) else None
        if cj is not None:
            ds_gap=.38*float(draft_score[chosen_global]-draft_score[fg])
            ru_gap=3.60*float(delta[cj]-delta[fj])
            edge_gap=.18*float(edge[cj]-edge[fj])

            # Injury contribution exactly as used by eval_score.
            def _inj_pen(code):
                return 12.0 if int(code)==2 else 2.5 if int(code)==1 else 0.0
            injury_gap=_inj_pen(fast["injury"][fg])-_inj_pen(fast["injury"][chosen_global])

            # Early IDP penalty contribution. R4-6 only in this audit.
            rnd=max(1,int((int(current_pick)-1)//max(12,1))+1)
            idp_c=(8-rnd)*2.2 if rnd<=7 and int(pos[chosen_global]) in [4,5] else 0.0
            idp_f=(8-rnd)*2.2 if rnd<=7 and int(pos[fg]) in [4,5] else 0.0
            idp_gap=idp_f-idp_c

            vorp_gap=.38*9.0*float(vorp[chosen_global]-vorp[fg])
            proj_gap=.38*1.6*float(projection[chosen_global]-projection[fg])
            prog_gap=.38*.12*float(progression[chosen_global]-progression[fg])
            reg_gap=.38*(-.10)*float(regression[chosen_global]-regression[fg])
            scarcity_gap=.38*float(scarcity[chosen_global]-scarcity[fg])
            cons_gap=.38*.10*float(consensus_strength[chosen_global]-consensus_strength[fg])

            known=ds_gap+ru_gap+edge_gap+injury_gap+idp_gap
            residual=total_gap-known
            component_sum=vorp_gap+proj_gap+prog_gap+reg_gap+scarcity_gap+cons_gap
        else:
            ds_gap=ru_gap=edge_gap=injury_gap=idp_gap=residual=np.nan
            vorp_gap=proj_gap=prog_gap=reg_gap=scarcity_gap=cons_gap=component_sum=np.nan

        snap.update({
            "MR_Passed_faller_player":str(pool.iloc[fg].player),
            "MR_Passed_faller_position":str(pool.iloc[fg].position),
            "MR_Passed_faller_amount":float(falls[fj]),
            "MR_Passed_faller_eval_gap":total_gap,
            "MR_Passed_faller_survival_est":fsurv,
            "MR_Passed_faller_idx":fg,
            "MR42_Faller_draftscore_gap":ds_gap,
            "MR42_Faller_rosterutility_gap":ru_gap,
            "MR42_Faller_marketedge_gap":edge_gap,
            "MR42_Faller_injury_gap":injury_gap,
            "MR42_Faller_idp_penalty_gap":idp_gap,
            "MR42_Faller_residual_noise_gap":residual,
            "MR42_Faller_vorp_gap":vorp_gap,
            "MR42_Faller_projection_gap":proj_gap,
            "MR42_Faller_progression_gap":prog_gap,
            "MR42_Faller_regression_gap":reg_gap,
            "MR42_Faller_scarcity_gap":scarcity_gap,
            "MR42_Faller_consensus_gap":cons_gap,
            "MR42_Faller_component_sum":component_sum,
            "MR42_Faller_position":str(pool.iloc[fg].position),
        })
    return snap


def _diagnostic_replacement_ppg(pool, teams, flex_alloc):
    """Return per-position replacement PPG under a hypothetical FLEX allocation.
    Diagnostic only; does not affect V7.24 drafting.
    """
    alloc={"RB":float(flex_alloc.get("RB",.38)),
           "WR":float(flex_alloc.get("WR",.55)),
           "TE":float(flex_alloc.get("TE",.07))}
    demand={
        "QB":max(int(teams),int(teams)),
        "RB":max(int(round(teams*(2.0+alloc["RB"]))),int(teams)),
        "WR":max(int(round(teams*(2.0+alloc["WR"]))),int(teams)),
        "TE":max(int(round(teams*(1.0+alloc["TE"]))),int(teams)),
        "DL":max(int(teams),int(teams)),
        "DB":max(int(teams),int(teams))
    }
    out={}
    for p,n in demand.items():
        vals=pd.to_numeric(pool.loc[pool.position.eq(p),"projection"],errors="coerce").dropna().sort_values(ascending=False).reset_index(drop=True)
        out[p]=float(vals.iloc[min(max(n-1,0),len(vals)-1)]) if len(vals) else 0.0
    return out,demand


def mid_round_pipeline_summary(draft):
    if draft is None or len(draft)==0 or "MR_Audit" not in draft.columns:
        return {}
    d=draft[pd.to_numeric(draft.MR_Audit,errors="coerce").fillna(0).eq(1)].copy()
    if d.empty: return {}

    market_pos=d.MR_Market_best_position.value_counts(normalize=True)
    selected_pos=d.MR_Selected_position.value_counts(normalize=True)
    faller_pos=d.MR_Passed_faller_position.value_counts(normalize=True)

    out={
        "MR_Audit_picks":int(len(d)),
        "MR_avg_selected_reach":float(pd.to_numeric(d.MR_Selected_reach,errors="coerce").mean()),
        "MR_avg_selected_faller":float(pd.to_numeric(d.MR_Selected_faller,errors="coerce").mean()),
        "MR_avg_market_gap_vs_market_best":float(pd.to_numeric(d.MR_Market_gap_selected_vs_market_best,errors="coerce").mean()),
        "MR_avg_eval_edge_vs_market_best":float(pd.to_numeric(d.MR_Eval_gap_selected_vs_market_best,errors="coerce").mean()),
        "MR_market_best_survival_actual":float(pd.to_numeric(d.MR_Market_best_survived_actual,errors="coerce").mean()),
        "MR_passed_faller_amount":float(pd.to_numeric(d.MR_Passed_faller_amount,errors="coerce").mean()),
        "MR_passed_faller_eval_gap":float(pd.to_numeric(d.MR_Passed_faller_eval_gap,errors="coerce").mean()),
        "MR_passed_faller_survival_actual":float(pd.to_numeric(d.MR_Passed_faller_survived_actual,errors="coerce").mean()),
        "MR_avg_component_draftscore_gap":float(pd.to_numeric(d.MR_ComponentGap_draftscore,errors="coerce").mean()),
        "MR_avg_component_rosterdelta_gap":float(pd.to_numeric(d.MR_ComponentGap_rosterdelta,errors="coerce").mean()),
        "MR_avg_component_edge_gap":float(pd.to_numeric(d.MR_ComponentGap_edge,errors="coerce").mean()),
        "MR_positional_conflict_rate":float(pd.to_numeric(d.MR_Positional_conflict,errors="coerce").mean()),
    }
    for p in ["QB","RB","WR","TE"]:
        out[f"MR_Selected_{p}_share"]=float(selected_pos.get(p,0))
        out[f"MR_MarketBest_{p}_share"]=float(market_pos.get(p,0))
        out[f"MR_PassedFaller_{p}_share"]=float(faller_pos.get(p,0))

    drivers=d.MR_Primary_component_driver.value_counts(normalize=True)
    for name in ["player_model/draft_score","roster_marginal_utility","model-vs-market_edge"]:
        safe=name.replace("/","_").replace("-","_")
        out[f"MR_driver_{safe}"]=float(drivers.get(name,0))

    conflict=d[pd.to_numeric(d.MR_Positional_conflict,errors="coerce").fillna(0).eq(1)]
    out["MR_conflict_count"]=int(len(conflict))
    out["MR_conflict_eval_gap"]=float(pd.to_numeric(conflict.MR_Conflict_eval_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_draftscore_gap"]=float(pd.to_numeric(conflict.MR_Conflict_draftscore_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_rosterdelta_gap"]=float(pd.to_numeric(conflict.MR_Conflict_rosterdelta_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_edge_gap"]=float(pd.to_numeric(conflict.MR_Conflict_edge_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_market_gap"]=float(pd.to_numeric(conflict.MR_Conflict_market_gap,errors="coerce").mean()) if len(conflict) else np.nan

    # V7.27 player/draft-score internals.
    for col,key in [
        ("MR_Conflict_projection_raw_gap","MR27_projection_raw_gap"),
        ("MR_Conflict_replacement_raw_gap","MR27_replacement_raw_gap"),
        ("MR_Conflict_vorp_raw_gap","MR27_vorp_raw_gap"),
        ("MR_Conflict_progression_raw_gap","MR27_progression_raw_gap"),
        ("MR_Conflict_regression_raw_gap","MR27_regression_raw_gap"),
        ("MR_Conflict_scarcity_raw_gap","MR27_scarcity_raw_gap"),
        ("MR_Conflict_consensus_strength_raw_gap","MR27_consensus_strength_raw_gap"),
        ("MR_Conflict_vorp_component_gap","MR27_vorp_component_gap"),
        ("MR_Conflict_projection_component_gap","MR27_projection_component_gap"),
        ("MR_Conflict_progression_component_gap","MR27_progression_component_gap"),
        ("MR_Conflict_regression_component_gap","MR27_regression_component_gap"),
        ("MR_Conflict_scarcity_component_gap","MR27_scarcity_component_gap"),
        ("MR_Conflict_consensus_component_gap","MR27_consensus_component_gap"),
        ("MR_Conflict_pure_model_gap","MR27_pure_model_gap"),
    ]:
        out[key]=float(pd.to_numeric(conflict[col],errors="coerce").mean()) if len(conflict) else np.nan

    driver_counts=conflict.MR_DraftScore_primary_driver.value_counts(normalize=True) if len(conflict) else pd.Series(dtype=float)
    for name in ["VORP","projection","progression","regression","positional_scarcity","consensus_reality_check"]:
        out[f"MR27_driver_{name}"]=float(driver_counts.get(name,0))

    for col,key in [
        ("MR28_Chosen_replacement_rank","MR28_chosen_replacement_rank"),
        ("MR28_Alt_replacement_rank","MR28_alt_replacement_rank"),
        ("MR28_Base_replacement_gap","MR28_base_replacement_gap"),
        ("MR28_Base_vorp_gap","MR28_base_vorp_gap"),
        ("MR28_Alt_vorp_gap_flex_45_45_10","MR28_vorp_gap_45_45_10"),
        ("MR28_Alt_vorp_gap_flex_33_60_07","MR28_vorp_gap_33_60_07"),
        ("MR28_Alt_vorp_gap_flex_30_60_10","MR28_vorp_gap_30_60_10"),
        ("MR28_Alt_vorp_gap_equal_flex","MR28_vorp_gap_equal"),
        ("MR28_Alt_vorp_gap_vorp7","MR28_vorp_gap_weight7"),
        ("MR28_Alt_vorp_gap_vorp6","MR28_vorp_gap_weight6"),
    ]:
        out[key]=float(pd.to_numeric(conflict[col],errors="coerce").mean()) if len(conflict) else np.nan

    if len(conflict):
        altmix=conflict.MR_Conflict_alt_position.value_counts(normalize=True)
        out["MR_conflict_alt_WR_share"]=float(altmix.get("WR",0))
        out["MR_conflict_alt_QB_share"]=float(altmix.get("QB",0))
    else:
        out["MR_conflict_alt_WR_share"]=0.0
        out["MR_conflict_alt_QB_share"]=0.0
    return out


def simulate_mock_fast(fast, teams, slot, rounds, slots, randomness=12, model_user=True, seed=None,
                       room_profile="Consensus", wr_eval_deficit=10.0, wr_survival=.52, wr_enabled=True,
                       late_wr_enabled=False, late_wr_eval_deficit=8.0, late_wr_survival=.35,
                       late_wr_slots=(7,12), p12_dual_damp_enabled=False,
                       p12_player_weight=1.0, p12_roster_weight=1.0,
                       p12_faller_need_enabled=False, p12_faller_min=7.0,
                       p12_faller_eval_deficit=8.0, p12_need_reach=4.0,
                       p12_need_survival=.55, p12_te_utility_dedup_enabled=False,
                       p12_te_starter_vorp_mult=.90,
                       p12_te_gap_conditional_enabled=False,
                       p12_te_gap_threshold=55.97,
                       late_empirical_survival_enabled=False,
                       late_force_faller_round=0,
                       r7_dominance_override_enabled=True,
                       r5_dominance_override_enabled=False,
                       r2_dominance_override_enabled=False,
                       r3_dominance_override_enabled=False,
                       r11_13_offense_dominance_override_enabled=False,
                       late_sequence_variant="champion",
                       r2_generic_adaptation_enabled=True,
                       r4_generic_adaptation_enabled=False,
                       r3_causal_probe_enabled=False,
                       r3_qb_opportunity_cost_enabled=True):
    """NumPy benchmark engine. Decision rules match simulate_mock; Pandas is used only for the final 15-row roster."""
    rng=np.random.default_rng(seed)
    pool=fast["pool"]; pos=fast["pos_code"]; consensus=fast["consensus"]
    market_pick=fast["market_pick"]; injury=fast["injury"]; confidence=fast["confidence"]
    model_rank=fast["model_rank"]; draft_score=fast["draft_score"]
    n=len(pool)
    room_noise,room_run,room_value=_room_profile(room_profile)
    fallback=model_rank+rng.normal(0,8*room_noise,n)
    sim_cons=np.where(np.isnan(market_pick),fallback,market_pick)
    alive=np.ones(n,dtype=bool)
    counts=np.zeros(6,dtype=np.int16)
    user_idx=[]; user_pick=[]; user_round=[]; drafted_order=[]
    user_mr_diag=[]
    pending_market_idx=None; pending_market_diag=None
    pending_faller_idx=None; pending_faller_diag=None
    total=int(teams)*int(rounds)
    qb,rb,wr,te,dl,db=0,1,2,3,4,5

    for overall in range(1,total+1):
        round_no=(overall-1)//int(teams)+1
        pir=(overall-1)%int(teams)+1
        owner=pir if round_no%2 else int(teams)-pir+1
        idx=np.flatnonzero(alive)
        if idx.size==0: break

        if owner==int(slot):
            if pending_market_idx is not None and pending_market_diag is not None:
                user_mr_diag[pending_market_diag]["MR_Market_best_survived_actual"]=1.0 if alive[int(pending_market_idx)] else 0.0
                pending_market_idx=None; pending_market_diag=None
            if pending_faller_idx is not None and pending_faller_diag is not None:
                user_mr_diag[pending_faller_diag]["MR_Passed_faller_survived_actual"]=1.0 if alive[int(pending_faller_idx)] else 0.0
                pending_faller_idx=None; pending_faller_diag=None
            eligible=np.ones(idx.size,dtype=bool)
            eligible &= injury[idx] < 3  # IR/PUP/NFI are unavailable in draft recommendations.
            # Legal maximums only.
            if int(slots.get("QB",1))<=1 and counts[qb]>=2: eligible &= pos[idx]!=qb
            if int(slots.get("TE",1))<=1 and counts[te]>=2: eligible &= pos[idx]!=te
            if counts[dl]>=max(int(slots.get("DL",1)),1): eligible &= pos[idx]!=dl
            if counts[db]>=max(int(slots.get("DB",1)),1): eligible &= pos[idx]!=db
            if round_no<=7 and np.count_nonzero(~np.isin(pos[idx],[dl,db]))>=5:
                eligible &= ~np.isin(pos[idx],[dl,db])

            # Guarantee required starters only when picks are running out.
            missing_codes=[]
            for code,pname in enumerate(["QB","RB","WR","TE","DL","DB"]):
                missing_codes.extend([code]*max(int(slots.get(pname,0))-int(counts[code]),0))
            user_picks_left=int(rounds)-int(round_no)+1
            if missing_codes and user_picks_left<=len(missing_codes):
                force=np.isin(pos[idx],np.asarray(list(set(missing_codes)),dtype=int))
                if np.any(force): eligible &= force
            eidx=idx[eligible]
            if eidx.size==0: eidx=idx

            if model_user:
                # Core V7.3 architecture: actual marginal expected final-roster utility.
                _te_util_mult=.90
                if bool(p12_te_utility_dedup_enabled) and int(slot)==12 and 4<=round_no<=6:
                    _te_util_mult=float(p12_te_starter_vorp_mult)
                elif int(slot)==12 and 4<=round_no<=6:
                    # V7.50 PROMOTED CHAMPION RULE — frozen exactly from V7.47/V7.48/V7.49.
                    # Baseline .90 must select TE and the most-passed market faller's
                    # evaluation gap must be >= 55.97 before TE starter utility uses .30.
                    _base_sidx,_base_delta=_fast_candidate_deltas(
                        fast,user_idx,eidx,slots,exact_cap=56,te_starter_vorp_mult=.90
                    )
                    _base_cr=np.where(np.isnan(market_pick[_base_sidx]),float(overall),market_pick[_base_sidx])
                    _base_edge=np.clip(_base_cr-model_rank[_base_sidx],-24,24)
                    _base_edge=np.where(np.isin(pos[_base_sidx],[dl,db]),_base_edge*.45,_base_edge)
                    _base_noise=rng.normal(
                        0,(1.0-confidence[_base_sidx])*float(randomness)*0.30,size=_base_sidx.size
                    )
                    _base_eval=(0.38*draft_score[_base_sidx] + 3.60*_base_delta + 0.18*_base_edge)
                    _base_eval-=np.where(
                        injury[_base_sidx]==2,12.0,np.where(injury[_base_sidx]==1,2.5,0.0)
                    )
                    _base_eval+=_base_noise
                    if round_no<=7:
                        _base_eval-=np.where(
                            np.isin(pos[_base_sidx],[dl,db]),(8-round_no)*2.2,0
                        )
                    _base_nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                    _base_choice,_,_=execution_choice(
                        _base_eval,_base_cr,overall,_base_nxt,randomness
                    )
                    _base_global=int(_base_sidx[_base_choice])
                    _base_pos=str(pool.iloc[_base_global].position)
                    _falls=float(overall)-market_pick[_base_sidx]
                    _falls=np.where(np.isnan(_falls),-9999.0,_falls)
                    _falls[_base_choice]=-9999.0
                    _fj=int(np.argmax(_falls)) if len(_falls) else -1
                    _passed_gap=np.nan
                    if _fj>=0 and _falls[_fj]>0:
                        _passed_gap=float(_base_eval[_base_choice]-_base_eval[_fj])
                    if _base_pos=="TE" and pd.notna(_passed_gap) and _passed_gap>=55.97:
                        _te_util_mult=.30
                sidx,delta=_fast_candidate_deltas(fast,user_idx,eidx,slots,exact_cap=56,te_starter_vorp_mult=_te_util_mult)
                cr=np.where(np.isnan(market_pick[sidx]),float(overall),market_pick[sidx])
                edge=np.clip(cr-model_rank[sidx],-24,24)
                edge=np.where(np.isin(pos[sidx],[dl,db]),edge*.45,edge)

                # V7.9 PLAYER EVALUATION: who do we believe is best, independent of when to draft him?
                _eval_noise=rng.normal(0,(1.0-confidence[sidx])*float(randomness)*0.30,size=sidx.size)
                eval_score=(0.38*draft_score[sidx] + 3.60*delta + 0.18*edge)
                eval_score-=np.where(injury[sidx]==2,12.0,np.where(injury[sidx]==1,2.5,0.0))
                eval_score+=_eval_noise
                if round_no<=7:
                    eval_score-=np.where(np.isin(pos[sidx],[dl,db]),(8-round_no)*2.2,0)

                # V7.9 PICK EXECUTION: among our model targets, whose draft window is actually open now?
                nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                if bool(late_empirical_survival_enabled) and round_no>=11:
                    _late_surv=late_survival_probability_array_empirical(
                        cr,nxt,int(slot),int(round_no)
                    )
                    local_choice,_,_=execution_choice_with_survival(
                        eval_score,cr,overall,nxt,_late_surv
                    )
                else:
                    local_choice,_,_=execution_choice(eval_score,cr,overall,nxt,randomness)

                # V7.48.1 FIXED frozen discriminator.
                # First evaluate the normal .90 path using the real NumPy market arrays.
                # The feature is the same diagnostic used in V7.47:
                # selected TE evaluation minus the MOST-PASSED market faller's evaluation.
                if bool(p12_te_gap_conditional_enabled) and int(slot)==12 and 4<=round_no<=6:
                    _baseline_choice=int(local_choice)
                    _baseline_global=int(sidx[_baseline_choice])
                    _baseline_pos=str(pool.iloc[_baseline_global].position)

                    _falls=float(overall)-market_pick[sidx]
                    _falls=np.where(np.isnan(_falls),-9999.0,_falls)
                    _falls[_baseline_choice]=-9999.0
                    _fj=int(np.argmax(_falls)) if len(_falls) else -1

                    _passed_gap=np.nan
                    if _fj>=0 and _falls[_fj]>0:
                        _passed_gap=float(eval_score[_baseline_choice]-eval_score[_fj])

                    if _baseline_pos=="TE" and pd.notna(_passed_gap) and _passed_gap>=float(p12_te_gap_threshold):
                        # Recompute only marginal roster utility with TE starter VORP=.30.
                        # Candidate set, market edge, injury adjustment, and random noise stay identical.
                        _sidx30,_delta30=_fast_candidate_deltas(
                            fast,user_idx,eidx,slots,exact_cap=56,te_starter_vorp_mult=.30
                        )
                        # _fast_candidate_deltas is deterministic and should return the same shortlist,
                        # but remap defensively if its order ever changes.
                        _map30={int(g):float(d) for g,d in zip(_sidx30,_delta30)}
                        _delta30_aligned=np.asarray([_map30.get(int(g),float(delta[k])) for k,g in enumerate(sidx)],dtype=float)
                        eval_score=(0.38*draft_score[sidx] + 3.60*_delta30_aligned + 0.18*edge)
                        eval_score-=np.where(injury[sidx]==2,12.0,np.where(injury[sidx]==1,2.5,0.0))
                        eval_score+=_eval_noise
                        if round_no<=7:
                            eval_score-=np.where(np.isin(pos[sidx],[dl,db]),(8-round_no)*2.2,0)
                        delta=_delta30_aligned
                        local_choice,_,_=execution_choice(eval_score,cr,overall,nxt,randomness)

                # V7.39 calibration-only Pick-12 dual-driver damping.
                if bool(p12_dual_damp_enabled) and int(slot)==12 and 4<=round_no<=6 and int(pos[sidx][local_choice]) in [1,3]:
                    _wr=np.flatnonzero(pos[sidx]==2)
                    if len(_wr):
                        _wi=int(_wr[np.argmax(eval_score[_wr])])
                        _normal=int(local_choice)
                        _ds_gap=.38*float(draft_score[sidx][_normal]-draft_score[sidx][_wi])
                        _ru_gap=3.60*float(delta[_normal]-delta[_wi])
                        if _ds_gap>0 and _ru_gap>0:
                            _adj=np.asarray(eval_score,dtype=float).copy()
                            _adj[_normal]-=(1.0-float(p12_player_weight))*_ds_gap
                            _adj[_normal]-=(1.0-float(p12_roster_weight))*_ru_gap
                            local_choice=int(np.argmax(_adj))
                if wr_enabled:
                    local_choice,wr_scarcity,wr_diag=early_wr_scarcity_choice(
                        eval_score,cr,pos[sidx],overall,nxt,local_choice,
                        teams=int(teams),randomness=randomness,
                        max_eval_deficit=float(wr_eval_deficit),
                        max_wr_survival=float(wr_survival)
                    )
                else:
                    wr_scarcity=False
                    wr_diag={}
                local_choice,late_wr_intercept,late_wr_diag=late_slot_wr_conflict_choice(
                    eval_score,cr,pos[sidx],draft_score[sidx],fast["vorp"][sidx],
                    overall,nxt,local_choice,int(slot),teams=int(teams),randomness=randomness,
                    enabled=bool(late_wr_enabled),
                    max_eval_deficit=float(late_wr_eval_deficit),
                    max_wr_survival=float(late_wr_survival),
                    eligible_slots=late_wr_slots
                )
                local_choice,p12_faller_need,p12_faller_diag=pick12_faller_need_choice(
                    eval_score,cr,pos[sidx],overall,nxt,local_choice,
                    teams=int(teams),randomness=randomness,
                    enabled=bool(p12_faller_need_enabled),
                    min_fall=float(p12_faller_min),
                    max_eval_deficit=float(p12_faller_eval_deficit),
                    min_normal_reach=float(p12_need_reach),
                    max_normal_survival=float(p12_need_survival)
                )
                local_choice,_,_=faller_intercept_choice(
                    eval_score,cr,overall,local_choice,
                    teams=int(teams),rounds=int(rounds)
                )

                # V7.55 diagnostic counterfactual only:
                # at one specified late round, if V7.50 is reaching >=15 and a >=10-pick
                # passed market faller exists, force that faller. All subsequent picks
                # return to untouched V7.50 logic.
                if int(late_force_faller_round)==int(round_no) and round_no>=11:
                    _normal=int(local_choice)
                    _normal_reach=max(float(cr[_normal])-float(overall),0.0) if np.isfinite(cr[_normal]) else 0.0
                    _fall_amt=float(overall)-cr
                    _fall_amt=np.where(np.isnan(_fall_amt),-9999.0,_fall_amt)
                    _fall_amt[_normal]=-9999.0
                    _fj=int(np.argmax(_fall_amt)) if len(_fall_amt) else -1
                    if _normal_reach>=15.0 and _fj>=0 and float(_fall_amt[_fj])>=10.0:
                        local_choice=int(_fj)

                # V7.84 challenger-only R11-13 offense-only deep-faller dominance override.
                # Generic: no player, offensive position, draft slot, or room hard-coding.
                _r784_would_trigger=False
                _r784_best_global=None
                _r784_normal_global=None
                if 11<=round_no<=13:
                    _r84_normal=int(local_choice)
                    _r84_normal_global=int(sidx[_r84_normal])
                    _r784_normal_global=_r84_normal_global
                    _r84_market=float(cr[_r84_normal]) if np.isfinite(cr[_r84_normal]) else np.nan
                    _r84_delta=(_r84_market-float(overall)) if np.isfinite(_r84_market) else np.nan

                    if np.isfinite(_r84_delta) and _r84_delta < -30.0:
                        _r84_ids=eidx[eidx!=_r84_normal_global]
                        if len(_r84_ids):
                            _r84_off=_r84_ids[
                                ~pool.iloc[_r84_ids].position.isin(["DL","DB"]).to_numpy()
                            ]
                            if len(_r84_off):
                                _r84_dom=_r84_off[
                                    (draft_score[_r84_off] > draft_score[_r84_normal_global])
                                    & (fast["vorp"][_r84_off] > fast["vorp"][_r84_normal_global])
                                ]
                                if len(_r84_dom):
                                    _r84_ord=np.lexsort((
                                        np.where(np.isnan(market_pick[_r84_dom]),1e9,market_pick[_r84_dom]),
                                        -draft_score[_r84_dom]
                                    ))
                                    _r784_best_global=int(_r84_dom[_r84_ord[0]])
                                    _r784_would_trigger=True
                                    if bool(r11_13_offense_dominance_override_enabled):
                                        _r84_match=np.where(sidx==_r784_best_global)[0]
                                        if len(_r84_match):
                                            local_choice=int(_r84_match[0])

                # V7.91 challenger-only Round-2 generic adaptation rule.
                # Frozen pre-registered signature from V7.90:
                # alive+eligible alternative, BOTH higher frozen draft score and VORP,
                # effective market distance <=10 picks. No room/player/position/slot hard-coding.
                _r791_would_trigger=False
                _r791_best_global=None
                _r791_normal_global=None
                if round_no==2:
                    _r91_normal=int(local_choice)
                    _r91_normal_global=int(sidx[_r91_normal])
                    _r791_normal_global=_r91_normal_global
                    _r91_ids=eidx[eidx!=_r91_normal_global]
                    if len(_r91_ids):
                        _r91_market=np.where(np.isnan(market_pick[_r91_ids]),model_rank[_r91_ids],market_pick[_r91_ids])
                        _r91_distance=_r91_market-float(overall)
                        _r91_ok=(
                            (draft_score[_r91_ids] > draft_score[_r91_normal_global]) &
                            (fast["vorp"][_r91_ids] > fast["vorp"][_r91_normal_global]) &
                            (_r91_distance <= 10.0)
                        )
                        _r91_dom=_r91_ids[_r91_ok]
                        if len(_r91_dom):
                            _r91_ord=np.lexsort((
                                np.where(np.isnan(market_pick[_r91_dom]),1e9,market_pick[_r91_dom]),
                                -draft_score[_r91_dom]
                            ))
                            _r791_best_global=int(_r91_dom[_r91_ord[0]])
                            _r791_would_trigger=True
                            if bool(r2_generic_adaptation_enabled):
                                _r91_match=np.where(sidx==_r791_best_global)[0]
                                if len(_r91_match):
                                    local_choice=int(_r91_match[0])

                # V7.98 challenger-only Round-4 generic adaptation rule.
                # Pre-registered from V7.97: no room/player/position/slot hard-coding.
                # Trigger if a genuinely alive+eligible alternative has BOTH higher
                # frozen draft score and higher VORP, and effective market distance <=10.
                _r798_would_trigger=False
                _r798_best_global=None
                _r798_normal_global=None
                if round_no==4:
                    _r98_normal=int(local_choice)
                    _r98_normal_global=int(sidx[_r98_normal])
                    _r798_normal_global=_r98_normal_global
                    _r98_ids=eidx[eidx!=_r98_normal_global]

                    if len(_r98_ids):
                        _r98_market=np.where(np.isnan(market_pick[_r98_ids]),model_rank[_r98_ids],market_pick[_r98_ids])
                        _r98_distance=_r98_market-float(overall)
                        _r98_ok=(
                            (draft_score[_r98_ids] > draft_score[_r98_normal_global]) &
                            (fast["vorp"][_r98_ids] > fast["vorp"][_r98_normal_global]) &
                            (_r98_distance <= 10.0)
                        )
                        _r98_dom=_r98_ids[_r98_ok]
                        if len(_r98_dom):
                            _r98_ord=np.lexsort((
                                np.where(np.isnan(market_pick[_r98_dom]),1e9,market_pick[_r98_dom]),
                                -draft_score[_r98_dom]
                            ))
                            _r798_best_global=int(_r98_dom[_r98_ord[0]])
                            _r798_would_trigger=True
                            if bool(r4_generic_adaptation_enabled):
                                _r98_match=np.where(sidx==_r798_best_global)[0]
                                if len(_r98_match):
                                    local_choice=int(_r98_match[0])

                # V8.02 challenger-only Round-3 QB opportunity-cost rule.
                # Generic: only when the normal Round-3 selection is QB.
                # Alternative must be genuinely alive+eligible, non-QB,
                # BOTH higher frozen draft score and VORP, and within <=10 effective market picks.
                # No player, room, slot, or alternative-position hard-coding.
                _r802_would_trigger=False
                _r802_best_global=None
                _r802_normal_global=None

                if round_no==3:
                    _r802_normal=int(local_choice)
                    _r802_normal_global=int(sidx[_r802_normal])
                    _r802_normal_pos=str(pool.iloc[_r802_normal_global].position)

                    if _r802_normal_pos=="QB":
                        _r802_ids=eidx[eidx!=_r802_normal_global]
                        if len(_r802_ids):
                            _r802_nonqb=_r802_ids[
                                (pool.iloc[_r802_ids].position.astype(str)!="QB").to_numpy()
                            ]
                            if len(_r802_nonqb):
                                _r802_market=np.where(
                                    np.isnan(market_pick[_r802_nonqb]),
                                    model_rank[_r802_nonqb],
                                    market_pick[_r802_nonqb]
                                )
                                _r802_distance=_r802_market-float(overall)
                                _r802_ok=(
                                    (draft_score[_r802_nonqb] > draft_score[_r802_normal_global]) &
                                    (fast["vorp"][_r802_nonqb] > fast["vorp"][_r802_normal_global]) &
                                    (_r802_distance <= 10.0)
                                )
                                _r802_dom=_r802_nonqb[_r802_ok]

                                if len(_r802_dom):
                                    _r802_ord=np.lexsort((
                                        np.where(np.isnan(market_pick[_r802_dom]),1e9,market_pick[_r802_dom]),
                                        -draft_score[_r802_dom]
                                    ))
                                    _r802_best_global=int(_r802_dom[_r802_ord[0]])
                                    _r802_would_trigger=True

                                    if bool(r3_qb_opportunity_cost_enabled):
                                        _r802_match=np.where(sidx==_r802_best_global)[0]
                                        if len(_r802_match):
                                            local_choice=int(_r802_match[0])

                # V8.00 causal-probe-only Round-3 generic fork.
                # Same generic signature used for causal testing:
                # alive+eligible alternative, BOTH higher frozen draft score and VORP,
                # effective market distance <=10. No player/room/position/slot hard-coding.
                _r800_would_trigger=False
                _r800_best_global=None
                _r800_normal_global=None
                if round_no==3:
                    _r800_normal=int(local_choice)
                    _r800_normal_global=int(sidx[_r800_normal])
                    _r800_normal_global=int(_r800_normal_global)
                    _r800_ids=eidx[eidx!=_r800_normal_global]

                    if len(_r800_ids):
                        _r800_market=np.where(np.isnan(market_pick[_r800_ids]),model_rank[_r800_ids],market_pick[_r800_ids])
                        _r800_distance=_r800_market-float(overall)
                        _r800_ok=(
                            (draft_score[_r800_ids] > draft_score[_r800_normal_global]) &
                            (fast["vorp"][_r800_ids] > fast["vorp"][_r800_normal_global]) &
                            (_r800_distance <= 10.0)
                        )
                        _r800_dom=_r800_ids[_r800_ok]
                        if len(_r800_dom):
                            _r800_ord=np.lexsort((
                                np.where(np.isnan(market_pick[_r800_dom]),1e9,market_pick[_r800_dom]),
                                -draft_score[_r800_dom]
                            ))
                            _r800_best_global=int(_r800_dom[_r800_ord[0]])
                            _r800_would_trigger=True
                            if bool(r3_causal_probe_enabled):
                                _r800_match=np.where(sidx==_r800_best_global)[0]
                                if len(_r800_match):
                                    local_choice=int(_r800_match[0])

                # V7.80 challenger-only Round-3 true-board dominance override.
                # Generic: no player, position, slot, or room hard-coding.
                _r780_would_trigger=False
                _r780_best_global=None
                _r780_normal_global=None
                if round_no==3:
                    _r3_normal=int(local_choice)
                    _r3_normal_global=int(sidx[_r3_normal])
                    _r780_normal_global=_r3_normal_global
                    _r3_normal_market=float(cr[_r3_normal]) if np.isfinite(cr[_r3_normal]) else np.nan
                    _r3_normal_reach=(_r3_normal_market-float(overall)) if np.isfinite(_r3_normal_market) else np.nan

                    if np.isfinite(_r3_normal_reach) and _r3_normal_reach>10.0:
                        _r3_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r3_legal=(injury[eidx] < 3) & (_r3_market <= float(overall)+10.0)
                        _r3_ids=eidx[_r3_legal]
                        _r3_ids=_r3_ids[_r3_ids!=_r3_normal_global]

                        if len(_r3_ids):
                            _r3_dom=_r3_ids[
                                (draft_score[_r3_ids] > draft_score[_r3_normal_global])
                                & (fast["vorp"][_r3_ids] > fast["vorp"][_r3_normal_global])
                            ]
                            if len(_r3_dom):
                                _r3_ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_r3_dom]),1e9,market_pick[_r3_dom]),
                                    -draft_score[_r3_dom]
                                ))
                                _r780_best_global=int(_r3_dom[_r3_ord[0]])
                                _r780_would_trigger=True
                                if bool(r3_dominance_override_enabled):
                                    _r3_match=np.where(sidx==_r780_best_global)[0]
                                    if len(_r3_match):
                                        local_choice=int(_r3_match[0])

                # V7.77 challenger-only Round-2 true-board dominance override.
                # Generic: no player, position, slot, or room hard-coding.
                _r777_would_trigger=False
                _r777_best_global=None
                _r777_normal_global=None
                if round_no==2:
                    _r2_normal=int(local_choice)
                    _r2_normal_global=int(sidx[_r2_normal])
                    _r777_normal_global=_r2_normal_global
                    _r2_normal_market=float(cr[_r2_normal]) if np.isfinite(cr[_r2_normal]) else np.nan
                    _r2_normal_reach=(_r2_normal_market-float(overall)) if np.isfinite(_r2_normal_market) else np.nan
                    if np.isfinite(_r2_normal_reach) and _r2_normal_reach>10.0:
                        _r2_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r2_legal=(injury[eidx] < 3) & (_r2_market <= float(overall)+10.0)
                        _r2_ids=eidx[_r2_legal]
                        _r2_ids=_r2_ids[_r2_ids!=_r2_normal_global]
                        if len(_r2_ids):
                            _r2_dom=_r2_ids[
                                (draft_score[_r2_ids] > draft_score[_r2_normal_global])
                                & (fast["vorp"][_r2_ids] > fast["vorp"][_r2_normal_global])
                            ]
                            if len(_r2_dom):
                                _r2_ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_r2_dom]),1e9,market_pick[_r2_dom]),
                                    -draft_score[_r2_dom]
                                ))
                                _r777_best_global=int(_r2_dom[_r2_ord[0]])
                                _r777_would_trigger=True
                                if bool(r2_dominance_override_enabled):
                                    _r2_match=np.where(sidx==_r777_best_global)[0]
                                    if len(_r2_match):
                                        local_choice=int(_r2_match[0])

                # V7.71 challenger-only Round-5 dominance override.
                # No hard-coded player or slot. Fires only when the normal champion choice:
                # - is Round 5,
                # - reaches >10 picks versus effective market,
                # - and a truly alive+eligible, market-respecting alternative has
                #   BOTH higher frozen draft score and higher VORP.
                _r771_would_trigger=False
                _r771_best_global=None
                _r771_normal_global=None
                if round_no==5:
                    _r5_normal=int(local_choice)
                    _r5_normal_global=int(sidx[_r5_normal])
                    _r771_normal_global=_r5_normal_global
                    _r5_normal_market=float(cr[_r5_normal]) if np.isfinite(cr[_r5_normal]) else np.nan
                    _r5_normal_reach=(_r5_normal_market-float(overall)) if np.isfinite(_r5_normal_market) else np.nan

                    if np.isfinite(_r5_normal_reach) and _r5_normal_reach>10.0:
                        _r5_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r5_legal=(injury[eidx] < 3) & (_r5_market <= float(overall)+10.0)
                        _r5_ids=eidx[_r5_legal]
                        _r5_ids=_r5_ids[_r5_ids!=_r5_normal_global]

                        if len(_r5_ids):
                            _r5_dom=_r5_ids[
                                (draft_score[_r5_ids] > draft_score[_r5_normal_global])
                                & (fast["vorp"][_r5_ids] > fast["vorp"][_r5_normal_global])
                            ]
                            if len(_r5_dom):
                                _r5_ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_r5_dom]),1e9,market_pick[_r5_dom]),
                                    -draft_score[_r5_dom]
                                ))
                                _r771_best_global=int(_r5_dom[_r5_ord[0]])
                                _r771_would_trigger=True
                                if bool(r5_dominance_override_enabled):
                                    _r5_match=np.where(sidx==_r771_best_global)[0]
                                    if len(_r5_match):
                                        local_choice=int(_r5_match[0])

                # V7.67 production Round-7 dominance rule (promoted unchanged from V7.64-V7.66).
                # Compute the exact trigger once. V7.67 keeps it exposed diagnostically
                # so unchanged matched drafts can skip an unnecessary challenger rerun.
                _r766_would_trigger=False
                _r766_best_global=None
                _r766_normal_global=None
                if round_no==7:
                    _normal=int(local_choice)
                    _normal_global=int(sidx[_normal])
                    _r766_normal_global=_normal_global
                    _normal_market=float(cr[_normal]) if np.isfinite(cr[_normal]) else np.nan
                    _normal_reach=(_normal_market-float(overall)) if np.isfinite(_normal_market) else np.nan

                    if np.isfinite(_normal_reach) and _normal_reach>10.0:
                        _r7_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r7_legal=(injury[eidx] < 3) & (_r7_market <= float(overall)+10.0)
                        _r7_ids=eidx[_r7_legal]
                        _r7_ids=_r7_ids[_r7_ids!=_normal_global]

                        if len(_r7_ids):
                            _dom=_r7_ids[
                                (draft_score[_r7_ids] > draft_score[_normal_global])
                                & (fast["vorp"][_r7_ids] > fast["vorp"][_normal_global])
                            ]
                            if len(_dom):
                                _ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_dom]),1e9,market_pick[_dom]),
                                    -draft_score[_dom]
                                ))
                                _r766_best_global=int(_dom[_ord[0]])
                                _r766_would_trigger=True
                                if bool(r7_dominance_override_enabled):
                                    _match=np.where(sidx==_r766_best_global)[0]
                                    if len(_match):
                                        local_choice=int(_match[0])

                # V7.86 experimental late-sequence forcing.
                # Champion/default remains OFF->OFF->OFF->DB->DL for R11-15.
                # Variants only constrain broad OFF/DB/DL class by round; player choice inside the class
                # is still determined by the frozen engine's current local scores.
                if 11<=round_no<=15 and str(late_sequence_variant)!="champion":
                    _seq_map={
                        "db13": {11:"OFF",12:"OFF",13:"DB",14:"OFF",15:"DL"},
                        "db12": {11:"OFF",12:"DB",13:"OFF",14:"OFF",15:"DL"},
                    }
                    _target=_seq_map.get(str(late_sequence_variant),{}).get(int(round_no))
                    if _target:
                        _classes=np.array([
                            ("DB" if str(pool.iloc[int(g)].position)=="DB"
                             else ("DL" if str(pool.iloc[int(g)].position)=="DL" else "OFF"))
                            for g in sidx
                        ],dtype=object)
                        _cand=np.where(_classes==_target)[0]
                        if len(_cand):
                            # Stay inside the frozen engine: select best current eval_score among target-class options.
                            _best_local=int(_cand[int(np.argmax(eval_score[_cand]))])
                            local_choice=_best_local

                chosen=int(sidx[int(local_choice)])
                mr_diag={}

                # V8.06.3 exact true-board audit: eidx is the actual alive+eligible board
                # after all opponent selections preceding this user pick.
                _r8063_ids=eidx[eidx!=int(chosen)]
                if len(_r8063_ids):
                    _r8063_order=np.lexsort((
                        np.where(np.isnan(market_pick[_r8063_ids]),1e9,market_pick[_r8063_ids]),
                        -draft_score[_r8063_ids]
                    ))
                    _r8063_top=_r8063_ids[_r8063_order[:5]]
                else:
                    _r8063_top=np.asarray([],dtype=int)

                mr_diag.update({
                    "R8063_Audit":1,
                    "R8063_Actual_available_count":int(len(eidx)),
                    "R8063_QB_count_pre":int(counts[qb]),
                    "R8063_RB_count_pre":int(counts[rb]),
                    "R8063_WR_count_pre":int(counts[wr]),
                    "R8063_TE_count_pre":int(counts[te]),
                    "R8063_DL_count_pre":int(counts[dl]),
                    "R8063_DB_count_pre":int(counts[db]),
                })
                for _k in range(5):
                    if _k < len(_r8063_top):
                        _g=int(_r8063_top[_k])
                        _m=float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan
                        mr_diag.update({
                            f"R8063_Alt{_k+1}_player":str(pool.iloc[_g].player),
                            f"R8063_Alt{_k+1}_position":str(pool.iloc[_g].position),
                            f"R8063_Alt{_k+1}_market_pick":_m,
                            f"R8063_Alt{_k+1}_market_distance":(_m-float(overall)) if np.isfinite(_m) else np.nan,
                            f"R8063_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                            f"R8063_Alt{_k+1}_projection":float(fast["projection"][_g]),
                            f"R8063_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                            f"R8063_Alt{_k+1}_draft_score":float(draft_score[_g]),
                        })
                    else:
                        for _fld in ["market_pick","market_distance","model_rank","projection","vorp","draft_score"]:
                            mr_diag[f"R8063_Alt{_k+1}_{_fld}"]=np.nan
                        mr_diag[f"R8063_Alt{_k+1}_player"]=""
                        mr_diag[f"R8063_Alt{_k+1}_position"]=""

                # V7.89 measurement-only: R1-4 board-depletion snapshot.
                # Captures the best available frozen-score/VORP options at the exact user pick.
                if 1<=round_no<=4:
                    _r89_ids=eidx[eidx!=int(chosen)]
                    if len(_r89_ids):
                        _r89_score_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r89_ids]),1e9,market_pick[_r89_ids]),
                            -draft_score[_r89_ids]
                        ))
                        _r89_vorp_order=np.argsort(-fast["vorp"][_r89_ids])
                        _r89_best_score=int(_r89_ids[_r89_score_order[0]])
                        _r89_best_vorp=int(_r89_ids[_r89_vorp_order[0]])
                    else:
                        _r89_best_score=None
                        _r89_best_vorp=None

                    mr_diag.update({
                        "R789_Audit":1,
                        "R789_Actual_available_count":int(len(eidx)),
                        "R789_Best_score_player":str(pool.iloc[_r89_best_score].player) if _r89_best_score is not None else "",
                        "R789_Best_score_position":str(pool.iloc[_r89_best_score].position) if _r89_best_score is not None else "",
                        "R789_Best_score_market_pick":float(market_pick[_r89_best_score]) if _r89_best_score is not None and np.isfinite(market_pick[_r89_best_score]) else np.nan,
                        "R789_Best_score_vorp":float(fast["vorp"][_r89_best_score]) if _r89_best_score is not None else np.nan,
                        "R789_Best_score_draft_score":float(draft_score[_r89_best_score]) if _r89_best_score is not None else np.nan,

                        "R789_Best_vorp_player":str(pool.iloc[_r89_best_vorp].player) if _r89_best_vorp is not None else "",
                        "R789_Best_vorp_position":str(pool.iloc[_r89_best_vorp].position) if _r89_best_vorp is not None else "",
                        "R789_Best_vorp_market_pick":float(market_pick[_r89_best_vorp]) if _r89_best_vorp is not None and np.isfinite(market_pick[_r89_best_vorp]) else np.nan,
                        "R789_Best_vorp_vorp":float(fast["vorp"][_r89_best_vorp]) if _r89_best_vorp is not None else np.nan,
                        "R789_Best_vorp_draft_score":float(draft_score[_r89_best_vorp]) if _r89_best_vorp is not None else np.nan,
                    })

                if round_no==3:
                    mr_diag.update({
                        "R800_Would_trigger":1 if _r800_would_trigger else 0,
                        "R800_Normal_player":str(pool.iloc[int(_r800_normal_global)].player) if _r800_normal_global is not None else "",
                        "R800_Alt_player":str(pool.iloc[int(_r800_best_global)].player) if _r800_best_global is not None else "",
                        "R800_Alt_position":str(pool.iloc[int(_r800_best_global)].position) if _r800_best_global is not None else "",
                    })

                if round_no==3:
                    mr_diag.update({
                        "R802_Would_trigger":1 if _r802_would_trigger else 0,
                        "R802_Normal_player":str(pool.iloc[int(_r802_normal_global)].player) if _r802_normal_global is not None else "",
                        "R802_Alt_player":str(pool.iloc[int(_r802_best_global)].player) if _r802_best_global is not None else "",
                        "R802_Alt_position":str(pool.iloc[int(_r802_best_global)].position) if _r802_best_global is not None else "",
                    })

                # V7.99 measurement-only: Round-3 downstream mechanism audit.
                # Captures true-board alternatives and the post-R1-2 roster state.
                if round_no==3:
                    _r99_ids=eidx[eidx!=int(chosen)]
                    if len(_r99_ids):
                        _r99_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r99_ids]),1e9,market_pick[_r99_ids]),
                            -draft_score[_r99_ids]
                        ))
                        _r99_top=_r99_ids[_r99_order[:5]]
                    else:
                        _r99_top=np.asarray([],dtype=int)

                    mr_diag.update({
                        "R799_Audit":1,
                        "R799_QB_count_pre":int(counts[qb]),
                        "R799_RB_count_pre":int(counts[rb]),
                        "R799_WR_count_pre":int(counts[wr]),
                        "R799_TE_count_pre":int(counts[te]),
                        "R799_DL_count_pre":int(counts[dl]),
                        "R799_DB_count_pre":int(counts[db]),
                    })

                    for _k in range(5):
                        if _k < len(_r99_top):
                            _g=int(_r99_top[_k])
                            _m=float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan
                            mr_diag.update({
                                f"R799_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R799_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R799_Alt{_k+1}_market_pick":_m,
                                f"R799_Alt{_k+1}_market_distance":(_m-float(overall)) if np.isfinite(_m) else np.nan,
                                f"R799_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R799_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R799_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R799_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R799_Alt{_k+1}_player":"",
                                f"R799_Alt{_k+1}_position":"",
                                f"R799_Alt{_k+1}_market_pick":np.nan,
                                f"R799_Alt{_k+1}_market_distance":np.nan,
                                f"R799_Alt{_k+1}_model_rank":np.nan,
                                f"R799_Alt{_k+1}_projection":np.nan,
                                f"R799_Alt{_k+1}_vorp":np.nan,
                                f"R799_Alt{_k+1}_draft_score":np.nan,
                            })

                # V7.96 measurement-only: Round-4 true-board failure mechanism audit.
                if round_no==4:
                    _r4_ids=eidx[eidx!=int(chosen)]
                    if len(_r4_ids):
                        _r4_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r4_ids]),1e9,market_pick[_r4_ids]),
                            -draft_score[_r4_ids]
                        ))
                        _r4_top=_r4_ids[_r4_order[:5]]
                    else:
                        _r4_top=np.asarray([],dtype=int)

                    _pre_counts={p:int(counts[p]) for p in range(len(counts))}
                    mr_diag.update({
                        "R796_Audit":1,
                        "R796_Actual_available_count":int(len(eidx)),
                        "R796_QB_count_pre":int(counts[qb]),
                        "R796_RB_count_pre":int(counts[rb]),
                        "R796_WR_count_pre":int(counts[wr]),
                        "R796_TE_count_pre":int(counts[te]),
                        "R796_DL_count_pre":int(counts[dl]),
                        "R796_DB_count_pre":int(counts[db]),
                    })

                    for _k in range(5):
                        if _k < len(_r4_top):
                            _g=int(_r4_top[_k])
                            _m=float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan
                            mr_diag.update({
                                f"R796_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R796_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R796_Alt{_k+1}_market_pick":_m,
                                f"R796_Alt{_k+1}_market_distance":(_m-float(overall)) if np.isfinite(_m) else np.nan,
                                f"R796_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R796_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R796_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R796_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R796_Alt{_k+1}_player":"",
                                f"R796_Alt{_k+1}_position":"",
                                f"R796_Alt{_k+1}_market_pick":np.nan,
                                f"R796_Alt{_k+1}_market_distance":np.nan,
                                f"R796_Alt{_k+1}_model_rank":np.nan,
                                f"R796_Alt{_k+1}_projection":np.nan,
                                f"R796_Alt{_k+1}_vorp":np.nan,
                                f"R796_Alt{_k+1}_draft_score":np.nan,
                            })

                if round_no==5:
                    mr_diag.update({
                        "R771_Would_trigger":1 if _r771_would_trigger else 0,
                        "R771_Normal_player":str(pool.iloc[int(_r771_normal_global)].player) if _r771_normal_global is not None else "",
                        "R771_Best_alt_player":str(pool.iloc[int(_r771_best_global)].player) if _r771_best_global is not None else "",
                    })

                if round_no==4:
                    _r4_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                    _r4_legal=(injury[eidx] < 3) & (_r4_market <= float(overall)+10.0)
                    _r4_ids=eidx[_r4_legal]
                    _r4_ids=_r4_ids[_r4_ids!=int(chosen)]
                    if len(_r4_ids):
                        _r4_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r4_ids]),1e9,market_pick[_r4_ids]),
                            -draft_score[_r4_ids]
                        ))
                        _r4_top=_r4_ids[_r4_order[:5]]
                    else:
                        _r4_top=np.asarray([],dtype=int)

                    mr_diag.update({
                        "R769_Audit":1,
                        "R769_Actual_available_count":int(len(eidx)),
                        "R769_Market_respecting_count":int(len(_r4_ids)),
                    })
                    for _k in range(5):
                        if _k < len(_r4_top):
                            _g=int(_r4_top[_k])
                            mr_diag.update({
                                f"R769_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R769_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R769_Alt{_k+1}_market_pick":float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan,
                                f"R769_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R769_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R769_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R769_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R769_Alt{_k+1}_player":"",
                                f"R769_Alt{_k+1}_position":"",
                                f"R769_Alt{_k+1}_market_pick":np.nan,
                                f"R769_Alt{_k+1}_model_rank":np.nan,
                                f"R769_Alt{_k+1}_projection":np.nan,
                                f"R769_Alt{_k+1}_vorp":np.nan,
                                f"R769_Alt{_k+1}_draft_score":np.nan,
                            })

                # V7.70 measurement-only: true Round-5 board after all opponent picks.
                if round_no==5:
                    _r5_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                    _r5_legal=(injury[eidx] < 3) & (_r5_market <= float(overall)+10.0)
                    _r5_ids=eidx[_r5_legal]
                    _r5_ids=_r5_ids[_r5_ids!=int(chosen)]
                    if len(_r5_ids):
                        _r5_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r5_ids]),1e9,market_pick[_r5_ids]),
                            -draft_score[_r5_ids]
                        ))
                        _r5_top=_r5_ids[_r5_order[:5]]
                    else:
                        _r5_top=np.asarray([],dtype=int)
                    mr_diag.update({
                        "R770_Audit":1,
                        "R770_Actual_available_count":int(len(eidx)),
                        "R770_Market_respecting_count":int(len(_r5_ids)),
                    })
                    for _k in range(5):
                        if _k < len(_r5_top):
                            _g=int(_r5_top[_k])
                            mr_diag.update({
                                f"R770_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R770_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R770_Alt{_k+1}_market_pick":float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan,
                                f"R770_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R770_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R770_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R770_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R770_Alt{_k+1}_player":"",
                                f"R770_Alt{_k+1}_position":"",
                                f"R770_Alt{_k+1}_market_pick":np.nan,
                                f"R770_Alt{_k+1}_model_rank":np.nan,
                                f"R770_Alt{_k+1}_projection":np.nan,
                                f"R770_Alt{_k+1}_vorp":np.nan,
                                f"R770_Alt{_k+1}_draft_score":np.nan,
                            })

                if round_no==7:
                    mr_diag.update({
                        "R766_Would_trigger":1 if _r766_would_trigger else 0,
                        "R766_Normal_player":str(pool.iloc[int(_r766_normal_global)].player) if _r766_normal_global is not None else "",
                        "R766_Best_alt_player":str(pool.iloc[int(_r766_best_global)].player) if _r766_best_global is not None else "",
                    })

                # V7.63 diagnostic-only: capture the TRUE Round-7 board state after all opponent picks.
                # eidx is the actual alive+eligible player set at this exact user pick.
                if round_no==7:
                    _r7_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                    _r7_legal=(injury[eidx] < 3) & (_r7_market <= float(overall)+10.0)
                    _r7_ids=eidx[_r7_legal]
                    _r7_ids=_r7_ids[_r7_ids!=int(chosen)]
                    if len(_r7_ids):
                        _r7_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r7_ids]),1e9,market_pick[_r7_ids]),
                            -draft_score[_r7_ids]
                        ))
                        _r7_top=_r7_ids[_r7_order[:5]]
                    else:
                        _r7_top=np.asarray([],dtype=int)

                    mr_diag.update({
                        "R763_Audit":1,
                        "R763_Actual_available_count":int(len(eidx)),
                        "R763_Market_respecting_count":int(len(_r7_ids)),
                    })
                    for _k in range(5):
                        if _k < len(_r7_top):
                            _g=int(_r7_top[_k])
                            mr_diag.update({
                                f"R763_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R763_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R763_Alt{_k+1}_market_pick":float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan,
                                f"R763_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R763_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R763_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R763_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R763_Alt{_k+1}_player":"",
                                f"R763_Alt{_k+1}_position":"",
                                f"R763_Alt{_k+1}_market_pick":np.nan,
                                f"R763_Alt{_k+1}_model_rank":np.nan,
                                f"R763_Alt{_k+1}_projection":np.nan,
                                f"R763_Alt{_k+1}_vorp":np.nan,
                                f"R763_Alt{_k+1}_draft_score":np.nan,
                            })

                if 4<=round_no<=6 or round_no>=11:
                    _existing_diag=dict(mr_diag)
                    mr_diag=mid_round_pipeline_audit_snapshot(
                        fast,sidx,delta,edge,eval_score,chosen,overall,nxt,randomness
                    )
                    mr_diag.update(_existing_diag)
                    if int(slot)==12 and str(mr_diag.get("MR_Selected_position",""))=="TE" and str(mr_diag.get("MR_Passed_faller_position",""))=="WR":
                        _fg=mr_diag.get("MR_Passed_faller_idx",None)
                        if _fg is not None:
                            _sel=_fast_roster_role_snapshot(fast,user_idx,chosen,slots)
                            _fal=_fast_roster_role_snapshot(fast,user_idx,int(_fg),slots)
                            mr_diag.update({
                                "MR43_TE_architecture_audit":1,
                                "MR43_Selected_role":_sel["role"],
                                "MR43_Faller_role":_fal["role"],
                                "MR43_Selected_utility_delta":_sel["utility_delta"],
                                "MR43_Faller_utility_delta":_fal["utility_delta"],
                                "MR43_Utility_delta_gap":_sel["utility_delta"]-_fal["utility_delta"],
                                "MR43_Selected_role_proj":_sel["role_projection_component"],
                                "MR43_Selected_role_vorp":_sel["role_vorp_component"],
                                "MR43_Faller_role_proj":_fal["role_projection_component"],
                                "MR43_Faller_role_vorp":_fal["role_vorp_component"],
                                "MR43_Selected_replacement_ppg":_sel["replacement_ppg"],
                                "MR43_Faller_replacement_ppg":_fal["replacement_ppg"],
                                "MR43_Replacement_gap":_sel["replacement_ppg"]-_fal["replacement_ppg"],
                                "MR43_Selected_direct_missing":_sel["direct_missing_before"],
                                "MR43_Faller_direct_missing":_fal["direct_missing_before"],
                                "MR43_QB_before":_sel["QB_before"],
                                "MR43_RB_before":_sel["RB_before"],
                                "MR43_WR_before":_sel["WR_before"],
                                "MR43_TE_before":_sel["TE_before"],
                            })
            else:
                # Consensus baseline unchanged.
                mr_diag={}
                ce=eidx[injury[eidx]<3]
                if ce.size==0: ce=eidx
                noise=rng.normal(0,float(randomness)/3,ce.size)
                cr=np.where(np.isnan(market_pick[ce]),model_rank[ce],market_pick[ce])
                inj_cost=np.where(injury[ce]==2,28.0,np.where(injury[ce]==1,5.0,0.0))
                chosen=int(ce[int(np.argmin(cr+noise+inj_cost))])

            if 'mr_diag' not in locals(): mr_diag={}
            user_idx.append(chosen); user_pick.append(overall); user_round.append(round_no); user_mr_diag.append(mr_diag)
            if model_user and (4<=round_no<=6 or round_no>=11):
                if mr_diag.get("MR_Market_best_idx") is not None and int(mr_diag["MR_Market_best_idx"])!=int(chosen):
                    pending_market_idx=int(mr_diag["MR_Market_best_idx"]); pending_market_diag=len(user_mr_diag)-1
                if mr_diag.get("MR_Passed_faller_idx") is not None:
                    pending_faller_idx=int(mr_diag["MR_Passed_faller_idx"]); pending_faller_diag=len(user_mr_diag)-1
            counts[pos[chosen]]+=1
        else:
            # Same bounded-consensus opponent logic, without DataFrame allocation/sort.
            opp_idx=idx[injury[idx]<3]
            if opp_idx.size==0: opp_idx=idx
            base=sim_cons[opp_idx]
            window=max(18,min(45,int(16+overall*.12)))
            cand_mask=base<=overall+window
            cidx=opp_idx[cand_mask]
            if cidx.size==0:
                k=min(30,opp_idx.size)
                part=np.argpartition(base,k-1)[:k] if k<opp_idx.size else np.arange(opp_idx.size)
                cidx=opp_idx[part]
            sd=np.clip(4+sim_cons[cidx]/35,4,10)*room_noise
            opp=sim_cons[cidx]+rng.normal(0,sd)
            if room_value:
                agreement=np.clip(sim_cons[cidx]-model_rank[cidx],-20,20)
                opp-=.12*agreement
            if room_run and drafted_order:
                recent=[pos[x] for x in drafted_order[-4:]]
                vals,cts=np.unique(recent,return_counts=True)
                if len(cts) and int(np.max(cts))>=2:
                    run_code=int(vals[np.argmax(cts)])
                    opp-=np.where(pos[cidx]==run_code,3.0,0.0)
            opp+=np.where(injury[cidx]==2,28.0,np.where(injury[cidx]==1,5.0,0.0))
            if round_no<=7:
                opp+=np.where(np.isin(pos[cidx],[dl,db]),(8-round_no)*2.5,0)
            chosen=int(cidx[int(np.argmin(opp))])
        alive[chosen]=False
        drafted_order.append(chosen)

    if pending_market_idx is not None and pending_market_diag is not None:
        user_mr_diag[pending_market_diag]["MR_Market_best_survived_actual"]=1.0 if alive[int(pending_market_idx)] else 0.0
    if pending_faller_idx is not None and pending_faller_diag is not None:
        user_mr_diag[pending_faller_diag]["MR_Passed_faller_survived_actual"]=1.0 if alive[int(pending_faller_idx)] else 0.0
    roster=pool.iloc[user_idx].copy()
    roster["mock_pick"]=user_pick; roster["mock_round"]=user_round
    roster["market_pick"]=market_pick[user_idx]
    if len(user_mr_diag)==len(roster):
        md=pd.DataFrame(user_mr_diag,index=roster.index)
        for col in md.columns: roster[col]=md[col]
    return roster


def simulate_mock(board, teams, slot, rounds, slots, randomness=12, model_user=True, seed=None):
    """Original reference engine retained for interactive/debug use."""
    rng=np.random.default_rng(seed)
    pool=board.copy()
    pool=pool[pool.position.isin(["QB","RB","WR","TE","DL","DB"])].copy().reset_index(drop=True)
    pool["sim_consensus"]=pool.consensus_rank
    fallback=pool.model_rank + rng.normal(0,8,len(pool))
    pool["sim_consensus"]=pool.sim_consensus.fillna(fallback)
    alive=np.ones(len(pool),dtype=bool)
    user_rows=[]
    total=teams*rounds

    for overall in range(1,total+1):
        round_no=(overall-1)//teams+1
        pick_in_round=(overall-1)%teams+1
        owner_slot=pick_in_round if round_no%2 else teams-pick_in_round+1
        avail=pool.iloc[np.flatnonzero(alive)].copy()
        if avail.empty: break

        if owner_slot==slot:
            roster=pd.DataFrame(user_rows) if user_rows else board.iloc[0:0].copy()
            avail=draft_eligibility(avail,roster,round_no,rounds,slots)
            if avail.empty: avail=pool.iloc[np.flatnonzero(alive)].copy()
            avail["_construction_bonus"]=0.0
            rc=roster.position.value_counts().to_dict() if len(roster) else {}
            if rc.get("WR",0)<3: avail.loc[avail.position.eq("WR"),"_construction_bonus"]+=5.0
            elif rc.get("WR",0)==3: avail.loc[avail.position.eq("WR"),"_construction_bonus"]+=4.0
            elif rc.get("WR",0)==4: avail.loc[avail.position.eq("WR"),"_construction_bonus"]+=1.0
            if rc.get("RB",0)>=4: avail.loc[avail.position.eq("RB"),"_construction_bonus"]-=4.0
            if rc.get("RB",0)>=5: avail.loc[avail.position.eq("RB"),"_construction_bonus"]-=8.0
            avail["need"]=avail.position.map(lambda p: roster_need_for_mock(roster,p,slots))
            if model_user:
                avail["sim_score"]=avail.draft_score+avail["need"]+avail["_construction_bonus"]-np.maximum(overall-avail.consensus_rank.fillna(overall),0)*.08
                if round_no<=7: avail.loc[avail.position.isin(["DL","DB"]),"sim_score"] -= (8-round_no)*2.2
                counts=roster.position.value_counts().to_dict() if len(roster) else {}
                if counts.get("QB",0)>=1: avail.loc[avail.position.eq("QB"),"sim_score"] -= 10 if round_no<=10 else 5
                if counts.get("TE",0)>=1: avail.loc[avail.position.eq("TE"),"sim_score"] -= 8 if round_no<=10 else 3
                choice=avail.sort_values("sim_score",ascending=False).iloc[0]
            else:
                noise=rng.normal(0,randomness/3,len(avail)); avail["baseline"]=avail.sim_consensus+noise-avail["need"]*.25
                choice=avail.sort_values("baseline").iloc[0]
            rec=choice.to_dict(); rec["mock_pick"]=overall; rec["mock_round"]=round_no; user_rows.append(rec)
        else:
            base=avail.sim_consensus.fillna(avail.model_rank); window=max(18,min(45,int(16+overall*.12)))
            cand=avail[base<=overall+window].copy()
            if cand.empty: cand=avail.nsmallest(min(30,len(avail)),"sim_consensus")
            sd=np.clip(4+cand.sim_consensus.fillna(overall)/35,4,10); noise=rng.normal(0,sd)
            cand["opp_score"]=cand.sim_consensus.fillna(cand.model_rank)+noise
            if round_no<=7: cand.loc[cand.position.isin(["DL","DB"]),"opp_score"] += (8-round_no)*2.5
            choice=cand.sort_values("opp_score").iloc[0]
        alive[int(choice.name)]=False
    return pd.DataFrame(user_rows)


@st.cache_data(show_spinner=False)
def _fast_local_draft_board():
    """
    Cold-start-safe board built entirely from the packaged certified production board.
    No external request is required for the initial dashboard render.
    """
    pb,_=load_v9_production()
    if pb is None or pb.empty:
        return pd.DataFrame()

    repl={"QB":16.0,"RB":8.2,"WR":7.6,"TE":5.6,"DL":6.2,"DB":5.9,"K":8.1}
    x=pd.DataFrame({
        "player":pb["Player"].astype(str),
        "position":pb["Position"].astype(str).map(canonical_position),
        "market_pick":pd.to_numeric(pb["Market_pick"],errors="coerce"),
        "consensus_rank":pd.to_numeric(pb["Market_pick"],errors="coerce"),
        "vorp":pd.to_numeric(pb["VORP"],errors="coerce").fillna(0.0),
        "draft_score":pd.to_numeric(pb["Draft_score"],errors="coerce").fillna(0.0),
        "model_rank":pd.to_numeric(pb["Model_rank"],errors="coerce"),
    })
    x["key"]=x["player"].map(norm)
    x["raw_position"]=x["position"]
    x["team"]="NFL"
    x["projection"]=x.apply(
        lambda r: float(repl.get(str(r["position"]),0.0))+float(r["vorp"]),axis=1
    )
    x["replacement_ppg"]=x["position"].map(repl).fillna(0.0)
    x["last_ppg"]=x["projection"]
    x["prior_ppg"]=x["projection"]
    x["opp_pg"]=x["projection"]
    x["progression"]=0.0
    x["regression"]=0.0
    x["scarcity"]=0.0
    x["pure_model_score"]=x["draft_score"]
    x["consensus_strength"]=(
        100.0*(1.0-np.log(x["consensus_rank"].clip(lower=1))/
               np.log(max(float(x["consensus_rank"].max()),250.0)))
    ).clip(0,100).fillna(45.0)
    x["confidence"]=0.78
    x["injury"]=""
    x["injury_severity"]=0
    x["injury_penalty"]=0.0
    x["role_score"]=0.0
    x["profile"]="Stable / neutral"
    x["age"]=np.nan
    x["exp"]=np.nan
    x["breakout"]=0.0
    x["decline"]=0.0
    x["waiver_score"]=x["projection"]*4.0+x["progression"]*.23-x["regression"]*.10
    x["display_projection"]=x["projection"]
    x["display_vorp"]=x["vorp"]
    x["display_model_rank"]=x["model_rank"]
    x["id"]="local:"+x["key"]
    x["identity_key"]=x["id"]+"|"+x["position"]

    kickers=[
        ("Brandon Aubrey","DAL"),("Ka'imi Fairbairn","HOU"),("Cameron Dicker","LAC"),
        ("Jason Myers","SEA"),("Cam Little","JAC"),("Eddy Pineiro","SF"),
        ("Evan McPherson","CIN"),("Tyler Loop","BAL"),("Chase McLaughlin","TB"),
        ("Harrison Mevis","LAR"),("Andy Borregales","NE"),("Cairo Santos","CHI"),
        ("Chris Boswell","PIT"),("Jake Bates","DET"),("Harrison Butker","KC"),
        ("Will Reichard","MIN"),("Wil Lutz","DEN"),("Charlie Smyth","NO"),
        ("Jake Elliott","PHI"),("Blake Grupe","IND"),("Tyler Bass","BUF"),
        ("Joey Slye","TEN"),("Chad Ryland","ARI"),("Nick Folk","ATL"),
        ("Zane Gonzalez","MIA"),
    ]
    n=len(kickers)
    projections=[]
    for rank in range(1,n+1):
        pct=1.0-(rank-1)/max(n-1,1)
        projections.append(7.35+2.15*pct)
    k12_proj=projections[min(11,n-1)]

    krows=[]
    for rank,((name,team),proj) in enumerate(zip(kickers,projections),1):
        vorp=float(proj-k12_proj)
        market=float(150+rank*1.8)
        ds=float(28.0-rank*0.35+vorp*4.0)
        krows.append({
            "player":name,"position":"K","raw_position":"K","team":team,
            "market_pick":market,"consensus_rank":market,"vorp":vorp,
            "draft_score":ds,"model_rank":float(160+rank),
            "key":norm(name),"projection":proj,"replacement_ppg":k12_proj,
            "last_ppg":proj,"prior_ppg":proj,"opp_pg":proj,
            "progression":0.0,"regression":0.0,"scarcity":-1.25,
            "pure_model_score":ds,"consensus_strength":max(50.0,88-rank),
            "confidence":0.76,"injury":"","injury_severity":0,
            "injury_penalty":0.0,"role_score":0.0,"profile":"Stable / neutral",
            "age":np.nan,"exp":np.nan,"breakout":0.0,"decline":0.0,
            "waiver_score":proj*4.0,"display_projection":proj,
            "display_vorp":vorp,"display_model_rank":float(160+rank),
            "id":"local-k:"+norm(name),"identity_key":"local-k:"+norm(name)+"|K",
        })

    x=pd.concat([x,pd.DataFrame(krows)],ignore_index=True,sort=False)
    x=attach_v9_production(x)
    x=_v938_unified_player_universe(x)
    return x.drop_duplicates(subset=["key"],keep="first").reset_index(drop=True)


state=load_state()
state["teams"]=12
# v9.44.1: authoritative league template. This intentionally overrides stale saved
# roster settings from older builds so Mock Draft Lab always reflects the real league.
state["roster_slots"]={
    "QB":1,"RB":2,"WR":2,"TE":1,"FLEX":2,"K":1,"DL":1,"DB":1,"BENCH":6
}
state["mock"]["rounds"]=17

st.title("🏈 Fantasy Edge")
st.caption("Unified live-draft and mock-draft engine • 12-team snake • exact league construction")
st.caption("Fantasy Edge draft engine")
st.caption("⚡ Fast local startup active • external refresh is optional")

with st.sidebar:
    st.header("Yahoo league settings")
    teams=12
    st.number_input("Teams",12,12,12,disabled=True,help="Locked to your 12-team Yahoo league.")
    scoring=st.selectbox("Reception scoring",["PPR","Half PPR","Standard"],
                         index=0 if state["ppr"]==1 else 1 if state["ppr"]==.5 else 2)
    ppr={"PPR":1.0,"Half PPR":.5,"Standard":0.0}[scoring]
    pass_td=st.selectbox("Passing TD", [4,6], index=0 if int(state["pass_td"])==4 else 1)
    faab=st.number_input("FAAB budget",0,1000,int(state["faab"]))

    st.divider()
    st.subheader("IDP scoring")
    st.caption("Enter Yahoo's points for each defensive stat.")
    idp=state["idp"]
    idp["solo"]=st.number_input("Solo tackle",0.0,10.0,float(idp["solo"]),0.5)
    idp["assist"]=st.number_input("Assisted tackle",0.0,10.0,float(idp["assist"]),0.5)
    idp["sack"]=st.number_input("Sack",0.0,20.0,float(idp["sack"]),0.5)
    idp["tfl"]=st.number_input("Tackle for loss",0.0,10.0,float(idp["tfl"]),0.5)
    idp["qb_hit"]=st.number_input("QB hit",0.0,10.0,float(idp["qb_hit"]),0.5)
    idp["int"]=st.number_input("Interception",0.0,20.0,float(idp["int"]),0.5)
    idp["pd"]=st.number_input("Pass defended",0.0,10.0,float(idp["pd"]),0.5)
    idp["ff"]=st.number_input("Forced fumble",0.0,10.0,float(idp["ff"]),0.5)
    idp["fr"]=st.number_input("Fumble recovery",0.0,10.0,float(idp["fr"]),0.5)
    idp["def_td"]=st.number_input("Defensive TD",0.0,20.0,float(idp["def_td"]),0.5)
    idp["safety"]=st.number_input("Safety",0.0,10.0,float(idp["safety"]),0.5)

    st.divider()
    st.subheader("Starting roster")
    slots=state["roster_slots"]
    r1,r2=st.columns(2)
    slots["QB"]=r1.number_input("QB",0,4,int(slots["QB"]))
    slots["RB"]=r2.number_input("RB",0,6,int(slots["RB"]))
    slots["WR"]=r1.number_input("WR",0,6,int(slots["WR"]))
    slots["TE"]=r2.number_input("TE",0,4,int(slots["TE"]))
    slots["FLEX"]=r1.number_input("FLEX (RB/WR/TE)",0,4,int(slots["FLEX"]))
    slots["K"]=r2.number_input("Kicker",0,2,int(slots.get("K",1)))
    slots["DL"]=r1.number_input("DL",0,4,int(slots["DL"]))
    slots["DB"]=r2.number_input("DB",0,4,int(slots["DB"]))
    slots["BENCH"]=r1.number_input("Bench",0,10,int(slots.get("BENCH",6)))
    st.caption("League profile: 1 QB • 2 RB • 2 WR • 2 FLEX • 1 K • 1 DL • 1 DB • 6 bench. Kicker is reserved for the final roster slot and ranked by differentiated projection, market signal, and K-specific VORP.")

    state.update({"teams":teams,"ppr":ppr,"pass_td":pass_td,"faab":faab,"idp":idp,"roster_slots":slots})
    if st.button("Save all scoring settings"):
        save_state(state); st.success("Saved")

# Fast startup: render from the certified local board immediately.
_refresh_live=st.sidebar.checkbox(
    "Refresh external NFL data",
    value=False,
    help="Off = fastest/reliable startup using the packaged certified board. "
         "Turn on only when you want a full external data rebuild."
)

if _refresh_live:
    with st.spinner("Refreshing external NFL data…"):
        try:
            players=sleeper_players()
            hist=nfl_history()
            market=market_rankings(ppr)
            board=make_board(players,hist,market,ppr,pass_td,idp,teams,state["roster_slots"])
            board["market_pick"]=_market_pick_series(board,teams)
            board=attach_v9_production(board)
            board=_v938_unified_player_universe(board)
            board=apply_v92_injury_overlay(board,state)
            st.sidebar.success("External board refreshed")
        except Exception:
            st.sidebar.warning("External refresh failed; using certified local board.")
            players=pd.DataFrame()
            hist=pd.DataFrame()
            market=pd.DataFrame()
            board=_fast_local_draft_board()
            board=apply_v92_injury_overlay(board,state)
else:
    players=pd.DataFrame()
    hist=pd.DataFrame()
    market=pd.DataFrame()
    board=_fast_local_draft_board()
    board=apply_v92_injury_overlay(board,state)

if board is None or board.empty:
    st.error("Fantasy Edge could not load the local player board.")
    st.stop()

# V6.21 UI master-pool repair: production_board.csv is authoritative for player
# identity. Merge any production player missing from the runtime board so external
# refreshes/caches cannot silently remove draftable players from Draft Mode.
try:
    _pb_master,_cfg_master=load_v9_production()
    _runtime_keys=set(board["player"].astype(str).map(norm))
    _missing_pb=_pb_master[~_pb_master["key"].astype(str).isin(_runtime_keys)].copy()
    if len(_missing_pb):
        _rows=[]
        for _,_r in _missing_pb.iterrows():
            _name=str(_r["Player"]); _pos=canonical_position(_r["Position"])
            _market=float(pd.to_numeric(pd.Series([_r.get("Market_pick",999)]),errors="coerce").fillna(999).iloc[0])
            _vorp=float(pd.to_numeric(pd.Series([_r.get("VORP",0)]),errors="coerce").fillna(0).iloc[0])
            _draft=float(pd.to_numeric(pd.Series([_r.get("Draft_score",0)]),errors="coerce").fillna(0).iloc[0])
            _model=float(pd.to_numeric(pd.Series([_r.get("Model_rank",999)]),errors="coerce").fillna(999).iloc[0])
            # V6.22 projection repair: Draft_score is a ranking score, NOT fantasy
            # points. Reconstruct a PPG-scale projection from the runtime position
            # replacement level + certified VORP. This keeps restored players on
            # the same scale as native players.
            _pos_runtime=board[board["position"].astype(str).eq(_pos)].copy()
            if len(_pos_runtime) and "projection" in _pos_runtime.columns and "vorp" in _pos_runtime.columns:
                _repl_series=(pd.to_numeric(_pos_runtime["projection"],errors="coerce")
                              -pd.to_numeric(_pos_runtime["vorp"],errors="coerce")).replace([np.inf,-np.inf],np.nan).dropna()
                _replacement=float(_repl_series.median()) if len(_repl_series) else np.nan
            else:
                _replacement=np.nan
            _fallback_repl={"QB":16.0,"RB":8.2,"WR":7.6,"TE":7.8,"K":7.0,"DL":6.2,"DB":5.9}
            if not np.isfinite(_replacement) or _replacement<0 or _replacement>30:
                _replacement=float(_fallback_repl.get(_pos,7.5))
            _projection=float(_replacement+_vorp)

            _rows.append({
                "id":"production:"+norm(_name),"player":_name,"key":norm(_name),
                "position":_pos,"raw_position":_pos,"team":"NFL",
                "projection":_projection,"vorp":_vorp,"replacement_ppg":_replacement,
                "draft_score":_draft,
                "model_rank":_model,"consensus_rank":_market,"market_pick":_market,
                "confidence":0.80,"injury":"","injury_penalty":0.0,
                "v9_market_pick":_market,"v9_vorp":_vorp,
                "v9_draft_score":_draft,"v9_model_rank":_model,
                "v9_base_live_score":float(_r.get("Base_live_score",_draft)),
            })
        board=pd.concat([board,pd.DataFrame(_rows)],ignore_index=True,sort=False)
    board=board.drop_duplicates(subset=["player"],keep="first").reset_index(drop=True)
    # Projection sanity certification: normal fantasy PPG values should never
    # resemble 0-100 Draft_score values.
    _proj_check=pd.to_numeric(board.get("projection",pd.Series(dtype=float)),errors="coerce")
    _bad_proj=board[_proj_check>40]["player"].astype(str).tolist() if len(board) else []
    if _bad_proj:
        raise RuntimeError("Projection scale contamination detected: "+", ".join(_bad_proj[:12]))
except Exception as _pool_merge_error:
    st.sidebar.error("Production player-pool merge failed: "+str(_pool_merge_error))

# Every Streamlit tab body executes, even when the tab is not selected.
# Guarantee the minimum board schema for ALL tabs before rendering any of them.
_board_schema_defaults={
    "player":"","position":"","raw_position":"","team":"NFL",
    "projection":0.0,"vorp":0.0,"draft_score":0.0,"model_rank":999.0,
    "consensus_rank":np.nan,"market_pick":np.nan,
    "profile":"Stable / neutral","confidence":0.50,
    "breakout":0.0,"decline":0.0,"progression":0.0,"regression":0.0,
    "waiver_score":0.0,"injury":"","injury_source":"Local",
    "injury_effective":"","injury_severity":0,"injury_penalty":0.0,
    "display_projection":0.0,"display_vorp":0.0,"display_model_rank":999.0,
}
for _col,_default in _board_schema_defaults.items():
    if _col not in board.columns:
        board[_col]=_default

all_names=board["player"].astype(str).tolist()
state["my_team"]=[x for x in state.get("my_team",[]) if x in all_names]
state["taken"]=[x for x in state.get("taken",[]) if x in all_names]

tabs=st.tabs(["⚙️ League Setup","🎯 Draft Mode","🧪 Mock Draft Lab","🧲 Waiver Wire","🛡️ IDP Board","📈 Breakout / Regression","👤 My Team","🔎 Player Lab"])

def _snake_owner(overall_pick, teams):
    rnd=max(1,(int(overall_pick)-1)//int(teams)+1)
    within=(int(overall_pick)-1)%int(teams)+1
    return within if rnd%2==1 else int(teams)-within+1


def _sim_opponent_pick_fast(avail, opp_counts, rnd, randomness, rng):
    """Fast opponent simulation; user picks still use the full Fantasy Edge engine."""
    if avail.empty:
        return None

    # Opponents do not need the expensive Fantasy Edge candidate pipeline.
    # Restrict to the market-relevant front of the board plus any required IDP/K candidates.
    fallback=_safe_num_series(avail,"model_rank",999.0)
    if "consensus_rank" in avail.columns:
        market=pd.to_numeric(avail["consensus_rank"],errors="coerce").fillna(fallback)
    else:
        market=fallback.copy()

    # Most realistic opponent choices come from the top market band.
    front_idx=market.nsmallest(min(90,len(avail))).index
    need_pos=[]
    if rnd>=9 and int(opp_counts.get("DL",0))<1: need_pos.append("DL")
    if rnd>=10 and int(opp_counts.get("DB",0))<1: need_pos.append("DB")
    if rnd>=14 and int(opp_counts.get("K",0))<1: need_pos.append("K")
    extra_idx=avail.index[avail.position.isin(need_pos)] if need_pos else pd.Index([])
    idx=front_idx.union(extra_idx)
    a=avail.loc[idx].copy()

    # Preserve a minimal league-wide tail at scarce required positions. This does
    # not reserve a named player for the user; it prevents the lightweight
    # opponent model from unrealistically vacuuming an entire required position.
    # The packaged certification board is compact, so preserve a realistic
    # replacement-level tail that would exist in the actual Yahoo room.
    # These are NOT reserved named targets; they simply prevent the lightweight
    # opponent model from consuming the entire position universe.
    _scarce_floor={"QB":2,"RB":6,"WR":8,"TE":2,"K":2,"DL":2,"DB":2}
    for _p,_floor in _scarce_floor.items():
        _remaining=int((avail["position"].astype(str)==_p).sum())
        if _remaining<=_floor:
            a=a[~a["position"].astype(str).eq(_p)].copy()
    if a.empty:
        a=avail.loc[front_idx].copy()

    _amodel=_safe_num_series(a,"model_rank",999.0)
    if "consensus_rank" in a.columns:
        base=pd.to_numeric(a["consensus_rank"],errors="coerce").fillna(_amodel)
    else:
        base=_amodel
    score=base.to_numpy(dtype=float)+rng.normal(0,max(float(randomness),1.0),len(a))
    pos=a["position"].astype(str).to_numpy()

    # Vectorized roster-needs adjustments.
    if rnd<=7:
        score += np.where(np.isin(pos,["DL","DB"]),25.0,0.0)
    if rnd>=9 and int(opp_counts.get("DL",0))<1:
        score += np.where(pos=="DL",-7.0,0.0)
    if rnd>=10 and int(opp_counts.get("DB",0))<1:
        score += np.where(pos=="DB",-7.0,0.0)
    if rnd>=14 and int(opp_counts.get("K",0))<1:
        score += np.where(pos=="K",-8.0,0.0)

    if int(opp_counts.get("QB",0))>=1: score += np.where(pos=="QB",12.0,0.0)
    if int(opp_counts.get("TE",0))>=1: score += np.where(pos=="TE",8.0,0.0)
    if int(opp_counts.get("K",0))>=1: score += np.where(pos=="K",100.0,0.0)
    if int(opp_counts.get("DL",0))>=1: score += np.where(pos=="DL",5.0,0.0)
    if int(opp_counts.get("DB",0))>=1: score += np.where(pos=="DB",5.0,0.0)

    return a.iloc[int(np.argmin(score))]




@st.cache_data(show_spinner=False)
def _prepare_fast_sim_board(board):
    """
    Precompute IDP evidence once for automated simulations.
    This keeps the 100-draft test fast while avoiding neutral/missing IDP defaults.
    """
    y=board.copy()
    if "position" not in y.columns and "Position" in y.columns:
        y["position"]=y["Position"].map(canonical_position)
    if "player" not in y.columns and "Player" in y.columns:
        y["player"]=y["Player"].astype(str)

    # Align certified-board names where necessary.
    alias_pairs={
        "projection":["projection","proj","fantasy_points","projected_points"],
        "vorp":["vorp","VORP","v9_vorp"],
        "model_rank":["model_rank","Model_rank","v9_model_rank"],
        "consensus_rank":["consensus_rank","market_pick","Market_pick","v9_market_pick"],
        "market_pick":["market_pick","Market_pick","consensus_rank","v9_market_pick"],
    }
    for target,candidates in alias_pairs.items():
        if target not in y.columns:
            for c in candidates:
                if c in y.columns:
                    y[target]=y[c]
                    break

    y["idp_external_rank"]=np.nan
    y["idp_impact_score"]=np.nan
    y["idp_quality_tier"]=np.nan
    y["idp_eligible"]=False

    mask=y["position"].astype(str).str.upper().isin(["DL","DB"])
    if mask.any():
        rows=y.loc[mask].copy()
        y.loc[mask,"idp_external_rank"]=rows.apply(_v936_external_idp_rank,axis=1)

        impact=rows.apply(_v935_idp_impact_score,axis=1)
        y.loc[mask,"idp_impact_score"]=[v[0] for v in impact]
        y.loc[mask,"idp_eligible"]=[bool(v[1]) for v in impact]

        quality=rows.apply(_v941_idp_quality,axis=1)
        y.loc[mask,"idp_quality_tier"]=[v[0] for v in quality]

        # Consensus-backed fallback used by production scoring for strong known IDPs.
        er=pd.to_numeric(y.loc[mask,"idp_external_rank"],errors="coerce")
        pos=y.loc[mask,"position"].astype(str)
        fallback=((pos.eq("DL") & er.notna() & (er<=15)) |
                  (pos.eq("DB") & er.notna() & (er<=20)))
        if fallback.any():
            idx=fallback.index[fallback]
            y.loc[idx,"idp_eligible"]=True
            floor=np.where(
                y.loc[idx,"position"].eq("DL"),
                np.maximum(5.5,16.0-pd.to_numeric(y.loc[idx,"idp_external_rank"],errors="coerce")*0.60),
                np.maximum(5.0,14.0-pd.to_numeric(y.loc[idx,"idp_external_rank"],errors="coerce")*0.42)
            )
            current=pd.to_numeric(y.loc[idx,"idp_impact_score"],errors="coerce").fillna(0.0)
            y.loc[idx,"idp_impact_score"]=np.maximum(current.to_numpy(),floor)

    y["_sim_precomputed_idp"]=True
    return y


def _fast_sim_user_pick(avail, roster_rows, rnd, overall, slot, teams, slots, randomness, rng):
    """
    Simulation-only scorer that mirrors current Fantasy Edge decision principles.
    Optional numeric columns are always expanded to index-aligned Series.
    Live Draft and Interactive Mock remain unchanged.
    """
    if avail.empty:
        return None

    a=avail.copy()

    def _num_col(name, default=0.0):
        if name in a.columns:
            return pd.to_numeric(a[name],errors="coerce").fillna(float(default))
        return pd.Series(float(default),index=a.index,dtype=float)

    counts={}
    if roster_rows:
        for rr in roster_rows:
            p=str(rr.get("position",""))
            counts[p]=counts.get(p,0)+1

    proj=_num_col("projection",0.0)
    vorp=_num_col("vorp",0.0)
    model_rank=_num_col("model_rank",999.0)
    if "consensus_rank" in a.columns:
        market=pd.to_numeric(a["consensus_rank"],errors="coerce").fillna(model_rank)
    else:
        market=model_rank.copy()

    score=(proj*0.85)+(vorp*3.2)-np.minimum(market,300)*0.025
    pos=a["position"].astype(str)

    rounds=int(sum(int(v) for k,v in slots.items() if k!="FLEX") + int(slots.get("FLEX",0)))
    remaining_after=max(rounds-int(rnd),0)

    def min_required(after):
        fixed={p:max(int(slots.get(p,0))-int(after.get(p,0)),0)
               for p in ["QB","RB","WR","TE","K","DL","DB"]}
        required_skill=(
            int(slots.get("RB",0))+int(slots.get("WR",0))+
            int(slots.get("TE",0))+int(slots.get("FLEX",0))
        )
        have_skill=int(after.get("RB",0))+int(after.get("WR",0))+int(after.get("TE",0))
        fixed_skill=fixed["RB"]+fixed["WR"]+fixed["TE"]
        flex_extra=max(required_skill-have_skill-fixed_skill,0)
        return int(sum(fixed.values())+flex_extra)

    feasible=np.ones(len(a),dtype=bool)
    for p in ["QB","RB","WR","TE","K","DL","DB"]:
        idx=np.where(pos.to_numpy()==p)[0]
        if len(idx):
            after=dict(counts)
            after[p]=after.get(p,0)+1
            if min_required(after)>remaining_after:
                feasible[idx]=False

    rb=counts.get("RB",0); wr=counts.get("WR",0); te=counts.get("TE",0)
    qb=counts.get("QB",0); dl=counts.get("DL",0); db=counts.get("DB",0); k=counts.get("K",0)

    score += np.where((pos=="WR") & (wr<2),7.0,0.0)
    score += np.where((pos=="TE") & (te<1) & (rnd>=4),2.5,0.0)

    if rb>=2 and rnd<=6: score += np.where(pos=="RB",-3.0,0.0)
    if rb>=3 and rnd<=7: score += np.where(pos=="RB",-8.0,0.0)
    if rb>=4: score += np.where(pos=="RB",-5.5,0.0)
    if rb>=5: score += np.where(pos=="RB",-22.0,0.0)

    if wr>=5: score += np.where(pos=="WR",-8.0,0.0)
    if qb>=1: score += np.where(pos=="QB",-12.0,0.0)
    if te>=1: score += np.where(pos=="TE",-9.0,0.0)
    if k>=1: feasible &= (pos!="K").to_numpy()

    if dl>=1 and db<1:
        score += np.where(pos=="DB",14.0,0.0)
        score += np.where(pos=="DL",-20.0,0.0)
    if db>=1 and dl<1:
        score += np.where(pos=="DL",14.0,0.0)
        score += np.where(pos=="DB",-20.0,0.0)

    idp=pos.isin(["DL","DB"])
    tier=_num_col("idp_quality_tier",5.0)
    impact=_num_col("idp_impact_score",0.0)
    talent=_num_col("idp_talent_score",0.0)
    idp_ropp=_num_col("roster_opportunity_adj",0.0)

    impact_idp=idp & (tier<=2) & (idp_ropp>=-5.0)
    score += np.where(impact_idp,0.20*impact+0.16*talent+5.0,0.0)

    total_idp=dl+db

    # Controlled marginal-value IDP portfolio.
    # Required DL/DB are protected. A third impact defender is optional and must
    # clearly beat redundant bench offense. A fourth defender is not drafted.
    if dl>=1 and db>=1:
        if total_idp>=3:
            feasible &= (~idp).to_numpy()
        elif rnd>=11 and impact_idp.any():
            best_idp=float(np.nanmax(np.where(impact_idp,score,-1e9)))
            deep_offense=(
                ((pos=="RB") & (rb>=3)) |
                ((pos=="WR") & (wr>=3)) |
                ((pos=="QB") & (qb>=1)) |
                ((pos=="TE") & (te>=1))
            )
            best_off=float(np.nanmax(np.where(deep_offense,score,-1e9))) if deep_offense.any() else -1e9
            required_edge=6.5+rng.normal(0,2.0)
            if best_idp <= best_off+required_edge:
                feasible &= (~idp).to_numpy()

        feasible &= (~(idp & ((tier>2) | (idp_ropp<-5.0)))).to_numpy()

    true_reach=np.maximum(market-float(overall),0.0)
    faller=np.maximum(float(overall)-market,0.0)
    score -= np.minimum(true_reach,40.0)*0.20
    score += np.minimum(faller,48.0)*0.02

    score += rng.normal(0,max(float(randomness),1.0)*0.10,len(a))
    score=np.where(feasible,score,-1e9)

    if not np.isfinite(score).any():
        return None
    return a.iloc[int(np.nanargmax(score))]




def _sim_user_pick_same_engine(avail,roster,round_no,current_pick,slot,teams,slots,randomness=6):
    """Automated user picks use the exact Live/Interactive-Mock preparation pipeline."""
    # V6.11 Merit Depth Champion: certification uses the exact same currently
    # available player pool as Live Draft / Interactive Mock. Do not let a
    # benchmark-only prefilter choose the champion.
    sim_avail=avail.copy()
    ranked,next_pick=prepare_user_draft_candidates(
        sim_avail,roster.copy(),int(round_no),int(current_pick),
        int(slot),int(teams),slots,int(randomness)
    )

    # The benchmark prefilter is only a speed optimization. If it accidentally
    # removes every legal completion candidate, retry the exact production
    # pipeline on the full currently available pool.
    if ranked is None or len(ranked)==0:
        ranked,next_pick=prepare_user_draft_candidates(
            avail.copy(),roster.copy(),int(round_no),int(current_pick),
            int(slot),int(teams),slots,int(randomness)
        )

    if ranked is None or len(ranked)==0:
        counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
        remaining={p:int((avail["position"].astype(str)==p).sum()) for p in ["QB","RB","WR","TE","K","DL","DB"]}
        minimum_now,fixed_def,flex_extra=_minimum_required_picks_remaining(counts,slots)

        # Benchmark-only compact-pool recovery. In a real Yahoo room, RB/WR depth
        # extends well beyond the certified board. If the benchmark's compact pool
        # has exhausted both RB and WR after all requirements are complete, choose
        # the best remaining non-K/non-extra-IDP depth player rather than crash.
        if minimum_now==0 and remaining.get("RB",0)==0 and remaining.get("WR",0)==0:
            recovery=avail.copy()
            # Never create K2 or a fourth IDP in recovery.
            if int(counts.get("K",0))>=1:
                recovery=recovery[recovery["position"].astype(str)!="K"]
            _idp_total=int(counts.get("DL",0))+int(counts.get("DB",0))
            if _idp_total>=3:
                recovery=recovery[~recovery["position"].astype(str).isin(["DL","DB"])]

            # Prefer TE3 over QB3 if those are the only realistic compact-board
            # depth options; rank by the same production value fields.
            if len(recovery):
                recovery=recovery.copy()
                recovery["_recovery_score"]=(
                    _safe_num_series(recovery,"draft_score",0.0) +
                    1.5*_safe_num_series(recovery,"vorp",0.0) +
                    0.25*_safe_num_series(recovery,"projection",0.0)
                )
                _te=recovery[recovery["position"].astype(str).eq("TE")]
                _qb=recovery[recovery["position"].astype(str).eq("QB")]
                if len(_te):
                    return _te.sort_values("_recovery_score",ascending=False).iloc[0]
                if len(_qb):
                    return _qb.sort_values("_recovery_score",ascending=False).iloc[0]

        raise RuntimeError(
            f"No eligible production candidate | round={int(round_no)} overall={int(current_pick)} "
            f"roster={counts} missing_fixed={fixed_def} flex_extra={flex_extra} "
            f"minimum_required={minimum_now} requirements_complete={minimum_now==0} remaining_pool={remaining}"
        )
    return ranked.iloc[0]



def simulate_current_fantasy_edge_once(board, teams, slot, rounds, slots, randomness, seed):
    """Fast simulation: exact Fantasy Edge logic for user picks + lightweight realistic opponents."""
    rng=np.random.default_rng(int(seed))

    # Certification counters MUST exist before the first simulated user pick.
    production_engine_user_picks=0
    user_pick_count=0
    unavailable_user_picks=0

    # Build availability once, then drop one selected row per pick.
    avail=board.copy()
    if "_sim_key" not in avail.columns:
        avail["_sim_key"]=np.arange(len(avail),dtype=int)
    avail=avail.set_index("_sim_key",drop=False)

    user_rows=[]
    opp_counts={i:{} for i in range(1,int(teams)+1)}

    for overall in range(1,int(teams)*int(rounds)+1):
        if avail.empty:
            break
        rnd=max(1,(overall-1)//int(teams)+1)
        owner=_snake_owner(overall,int(teams))

        if int(owner)==int(slot):
            roster=pd.DataFrame(user_rows) if user_rows else board.iloc[0:0].copy()

            # Ultra-fast simulation scorer mirrors the current Fantasy Edge principles.
            # Live Draft + Interactive Mock still use the exact full production engine.
            choice=_sim_user_pick_same_engine(
                avail.reset_index(drop=True),roster,int(rnd),int(overall),
                int(slot),int(teams),slots,int(randomness)
            )
            production_engine_user_picks+=1
            user_pick_count+=1

            if choice is None:
                continue
            choice=choice.copy()

            _choice_name=str(choice.get("player",""))
            if _choice_name not in set(avail["player"].astype(str)):
                unavailable_user_picks+=1
                raise RuntimeError(f"Production engine recommended unavailable player: {_choice_name}")
            row=choice.to_dict()
            row["mock_round"]=rnd
            row["mock_pick"]=overall
            user_rows.append(row)

            # Drop by unique player key rather than rebuilding availability from board.
            pname=str(choice.player)
            hit=avail.index[avail.player.astype(str).eq(pname)]
            if len(hit):
                avail=avail.drop(hit[0])

        else:
            oc=opp_counts.setdefault(int(owner),{})
            choice=_sim_opponent_pick_fast(avail,oc,rnd,randomness,rng)
            if choice is not None:
                p=str(choice.position)
                oc[p]=int(oc.get(p,0))+1
                avail=avail.drop(choice.name)

    roster=pd.DataFrame(user_rows)
    if roster.empty:
        return None

    g=grade_mock(roster,int(teams),slots)
    c=roster.position.value_counts().to_dict()
    required_ok=all([
        c.get("QB",0)>=int(slots.get("QB",1)),
        c.get("RB",0)>=int(slots.get("RB",2)),
        c.get("WR",0)>=int(slots.get("WR",2)),
        c.get("TE",0)>=int(slots.get("TE",1)),
        c.get("K",0)>=int(slots.get("K",1)),
        c.get("DL",0)>=int(slots.get("DL",1)),
        c.get("DB",0)>=int(slots.get("DB",1)),
    ])

    _audit=_v610_roster_regret_audit(roster,slots)
    _result={
        "grade":float(g.get("score",np.nan)),
        "model_edge":float(g.get("model_edge_score",np.nan)),
        "draft_value":float(g.get("draft_value",np.nan)),
        "raw_market_draft_value":float(g.get("raw_market_draft_value",g.get("draft_value",np.nan))),
        "construction":float(g.get("construction",np.nan)),
        "positional_advantage":float(g.get("positional_advantage",np.nan)),
        "opportunity_penalty":float(g.get("opportunity_penalty",np.nan)),
        "raw_opportunity_penalty":float(g.get("raw_opportunity_penalty",g.get("opportunity_penalty",np.nan))),
        "RB":int(c.get("RB",0)),"WR":int(c.get("WR",0)),
        "QB":int(c.get("QB",0)),"TE":int(c.get("TE",0)),
        "K":int(c.get("K",0)),"DL":int(c.get("DL",0)),"DB":int(c.get("DB",0)),
        "IDP_total":int(c.get("DL",0))+int(c.get("DB",0)),
        "extra_IDP":max(int(c.get("DL",0))+int(c.get("DB",0))-2,0),
        "legal_roster":bool(required_ok),
        "production_engine_user_picks":int(production_engine_user_picks),
        "user_pick_count":int(user_pick_count),
        "production_engine_usage":float(production_engine_user_picks/max(user_pick_count,1)),
        "unavailable_user_picks":int(unavailable_user_picks),
        "duplicate_user_players":int(len(roster["player"])-roster["player"].nunique()) if "player" in roster.columns else 0,
        "roster_size":int(len(roster)),
        "expected_roster_size":int(exact_roster_rounds(slots)),
        "certified_expected_roster":bool(len(roster)==int(exact_roster_rounds(slots))),
        "starter_vorp":float(_audit["starter_vorp"]),
        "bench_upside":float(_audit["bench_upside"]),
        "harmful_regret_count":int(_audit["harmful_regret_count"]),
        "major_reach_count":int(_audit["major_reach_count"]),
        "raw_major_reach_count":int(_audit.get("raw_major_reach_count",_audit["major_reach_count"])),
        "early_backup_count":int(_audit["early_backup_count"]),
        "drafted_players":" | ".join([f"{int(rr.get('mock_pick',0))}:{rr.get('player','')}({rr.get('position','')},mkt={rr.get('consensus_rank','')})" for rr in user_rows]),
    }
    _result["champion_score"]=_v610_champion_score(_result)
    return _result


with tabs[0]:
    st.subheader("Set your Yahoo roster and taken players")
    my=st.multiselect("Players on MY Yahoo team",all_names,default=state["my_team"])
    taken=st.multiselect("All players already rostered/taken in Yahoo",all_names,default=list(dict.fromkeys(state["taken"]+my)))
    if st.button("💾 Save roster & taken players"):
        state["my_team"]=my; state["taken"]=list(dict.fromkeys(taken+my)); save_state(state); st.success("Saved")
    st.download_button("⬇️ Backup my league state",json.dumps(state,indent=2),
                       file_name="fantasy_edge_yahoo_state.json",mime="application/json")
    restore=st.file_uploader("Restore saved league state",type=["json"])
    if restore and st.button("Restore backup"):
        STATE.write_bytes(restore.getvalue()); st.success("Restored. Refresh the page.")

with tabs[1]:
    st.subheader("Live Draft Assistant")
    st.success("✅ Live and Mock use the same player pool, eligibility, roster construction, injury rules, timing, and recommendation engine.")
    _pool_check_names=set(board["player"].astype(str))
    _pool_check=["CeeDee Lamb","Kenneth Walker III"]
    st.caption("Player-pool check: "+", ".join([f"{_n} ✓" if _n in _pool_check_names else f"{_n} MISSING" for _n in _pool_check]))
    live_slot=st.number_input("Your Yahoo draft slot (for pick-timing estimates)",1,int(teams),min(int(state.get("mock",{}).get("draft_slot",1)),int(teams)),key="v761_live_slot")

    with st.expander("🚑 Live Injury Center", expanded=False):
        st.caption("Automated status: Sleeper NFL player feed, cached up to 24 hours. Manual overrides always take priority.")
        if st.button("🔄 Refresh injury feed now", key="v92_refresh_injuries"):
            sleeper_players.clear()
            st.success("Injury feed cache cleared. Reloading current Sleeper player statuses.")
            st.rerun()

        flagged=board[board["injury_effective"].fillna("").astype(str).str.strip()!=""].copy()

        # Keep the default Injury Center focused ONLY on players who are actually
        # present on the certified v9 production board. The "Show all" toggle can
        # still expose the complete Sleeper injury/status feed.
        certified_keys=set()
        try:
            pb_v92,_=load_v9_production()
            if not pb_v92.empty and "key" in pb_v92.columns:
                certified_keys=set(pb_v92["key"].dropna().astype(str))
        except Exception:
            certified_keys=set()

        draft_relevant=flagged["key"].astype(str).isin(certified_keys)
        relevant_flagged=flagged[draft_relevant].copy()
        show_all_injuries=st.toggle(
            "Show all injured/status players",
            value=False,
            key="v92_show_all_injuries",
            help="Off = injured/status players on the certified v9 production board only. Turn on to inspect the full Sleeper feed."
        )
        display_flagged=flagged if show_all_injuries else relevant_flagged

        if len(display_flagged):
            display_flagged["Penalty"]=display_flagged["injury_penalty"].map(
                lambda v:"DO NOT DRAFT" if v>=900 else f"-{v:.0f}"
            )
            display_flagged=display_flagged.sort_values(
                ["injury_penalty","player"],ascending=[False,True]
            )
            st.caption(
                f"Showing {len(display_flagged)} "
                + ("injured/status players." if show_all_injuries else "certified-board injured/status players.")
            )
            st.dataframe(
                display_flagged[["player","position","team","injury_effective","injury_source","Penalty"]]
                .rename(columns={"injury_effective":"Status","injury_source":"Source"})
                .head(100),
                use_container_width=True,hide_index=True
            )
        else:
            if len(flagged) and not show_all_injuries:
                st.caption("No injured/status players from the certified production board right now. Turn on “Show all” to inspect the full feed.")
            else:
                st.caption("No injury designations are currently attached to players on the board.")

        st.markdown("**Manual injury override**")
        injury_player=st.selectbox("Player",[""]+board["player"].sort_values().tolist(),key="v92_injury_player")
        injury_status=st.selectbox(
            "Override status",
            ["AUTO","CLEAR","QUESTIONABLE","DOUBTFUL","OUT","PUP","IR","DO NOT DRAFT"],
            key="v92_injury_status"
        )
        csave,cclear=st.columns(2)
        if csave.button("💾 Save injury override",use_container_width=True) and injury_player:
            ovs=dict(state.get("injury_overrides",{}) or {})
            k=norm(injury_player)
            if injury_status=="AUTO":
                ovs.pop(k,None)
            else:
                ovs[k]=injury_status
            state["injury_overrides"]=ovs
            save_state(state)
            st.success(f"{injury_player}: {injury_status}")
            st.rerun()
        if cclear.button("Clear all manual overrides",use_container_width=True):
            state["injury_overrides"]={}
            save_state(state)
            st.success("Manual injury overrides cleared.")
            st.rerun()

    x=board[~board["player"].isin(set(state["taken"]))].copy()

    myb=board[board["player"].isin(state["my_team"])].copy()
    counts=myb.position.value_counts().to_dict()
    slots=state["roster_slots"]

    live_round=max(1,int(len(state["taken"])//max(int(teams),1))+1)
    current_overall=max(1,len(state["taken"])+1)
    _randomness=int(state.get("mock",{}).get("randomness",6))

    x,live_next=prepare_user_draft_candidates(
        x,myb,live_round,current_overall,int(live_slot),int(teams),slots,_randomness
    )
    if x.empty:
        st.warning("No eligible players remain under the current roster rules.")
        st.stop()

    cr=pd.to_numeric(x["market_pick"],errors="coerce").fillna(current_overall)
    local,ready,survive=execution_choice(
        x.evaluation_score.to_numpy(float),cr.to_numpy(float),
        current_overall,live_next,state.get("mock",{}).get("randomness",6)
    )
    intercept_local,intercepted,intercept_fall=faller_intercept_choice(
        x.evaluation_score.to_numpy(float),cr.to_numpy(float),current_overall,local,
        teams=int(teams),rounds=exact_roster_rounds(slots)
    )
    dyn_min_fall,dyn_band,dyn_improve=dynamic_faller_threshold(current_overall,int(teams),exact_roster_rounds(slots))


    st.caption(f"Dynamic Faller Intercept this round: {dyn_min_fall:.0f}+ picks past market • top {dyn_band} model targets • {dyn_improve:.0f}-pick improvement required"
               + (" • LATE-ROUND VALUE HARVEST ACTIVE" if live_round>=11 else ""))
    # v9.43 kicker requirement: K is a real ranked candidate and the final roster slot is protected.
    _v943_kicker_needed = int(slots.get("K",1)) > int((myb.position=="K").sum() if len(myb) else 0)
    if _v943_kicker_needed and int(live_round)>=15:
        st.info("🦵 KICKER REQUIREMENT ACTIVE: 1 K is still required. The engine will preserve the final pick for K and rank available kickers from current market data.")

    # Two-track dashboard: evaluation and execution are intentionally separate.
    context_pool=apply_v933_context_quality_gate(x,myb,live_round,current_overall)
    model_targets=context_pool.sort_values("context_score",ascending=False).head(8).copy()
    draft_now=x[x.timing_ready].sort_values("execution_score",ascending=False).head(5).copy()
    if draft_now.empty:
        draft_now=x.head(5).copy()

    if len(model_targets):
        mt=model_targets.iloc[0]
        mt_action,mt_surv=market_timing_state(mt.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        st.info(f"🎯 MODEL CONTEXT: {mt.player} ({mt.position}, {mt.team}) — {mt_action}")
        mp="—" if pd.isna(mt.market_pick) else f"#{int(round(mt.market_pick))}"
        sv="—" if pd.isna(mt_surv) else f"{mt_surv:.0%}"
        st.caption(f"Model evaluation #{int(mt.evaluation_rank) if pd.notna(mt.evaluation_rank) else 999} • market {mp} • chance available next pick {sv} • current #{current_overall} → next {('#'+str(live_next)) if live_next else '—'}")

    if intercepted and intercept_local is not None and 0 <= int(intercept_local) < len(cr):
        # Context only; do not let positional intercept indexing control the final pick.
        pass
    if len(draft_now):
        dn=draft_now.iloc[0]
        dn_action,dn_surv=market_timing_state(dn.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        st.success(f"🏆 FINAL PICK: {dn.player} ({dn.position}, {dn.team}) — {dn_action}")
        st.caption(f"Authoritative roster-adjusted recommendation • evaluation #{int(dn.evaluation_rank) if pd.notna(dn.evaluation_rank) else 999} • market {('—' if pd.isna(dn.market_pick) else '#'+str(int(round(dn.market_pick))))}")

    # Persistent target queue: automatically track high-evaluation players we intentionally pass on.
    if "v761_target_queue" not in st.session_state:
        st.session_state.v761_target_queue={}
    queue=st.session_state.v761_target_queue
    available_names=set(x.player)
    for name in list(queue):
        if name not in available_names:
            queue.pop(name,None)
    for _,r in model_targets.iterrows():
        action,surv=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        if action=="WAIT / TARGET NEXT PICK":
            queue[r.player]={"market_pick":None if pd.isna(r.market_pick) else float(r.market_pick),
                             "evaluation_rank":int(r.evaluation_rank) if pd.notna(r.evaluation_rank) else 999,"position":r.position,"team":r.team}
    # Remove queue players whose timing window has opened; they are now DRAFT NOW targets.
    for name in list(queue):
        rr=x[x.player.eq(name)]
        if len(rr):
            r=rr.iloc[0]
            action,_=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
            if action!="WAIT / TARGET NEXT PICK":
                queue.pop(name,None)
    st.session_state.v761_target_queue=queue

    if queue:
        qrows=[]
        for name,data in queue.items():
            rr=x[x.player.eq(name)]
            if not len(rr): continue
            r=rr.iloc[0]
            action,surv=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
            qrows.append({"Target":name,"Pos":r.position,"Model target #":int(r.evaluation_rank) if pd.notna(r.evaluation_rank) else 999,
                          "Market pick":"—" if pd.isna(r.market_pick) else int(round(r.market_pick)),
                          "Chance survives":"—" if pd.isna(surv) else f"{surv:.0%}","Status":action})
        if qrows:
            st.markdown("### 🎯 Target Queue")
            st.caption("Players Fantasy Edge likes but is intentionally waiting on. They leave the queue when their draft window opens or another team takes them.")
            st.dataframe(pd.DataFrame(qrows).sort_values("Model target #"),use_container_width=True,hide_index=True)

    st.markdown("**Best remaining by position**")
    poscols=st.columns(3)
    for i,pos in enumerate(["RB","WR","QB","TE","DL","DB"]):
        px=x[x["position"].eq(pos)]
        if len(px):
            r=px.iloc[0]
            with poscols[i%3]:
                _rp=float(pd.to_numeric(pd.Series([r.get("projection",0)]),errors="coerce").fillna(0).iloc[0])
                _rv=float(pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
                st.caption(f"**{pos}: {r.get('player','Unknown')}** — {_rp:.1f} PPG, VORP {_rv:+.1f}")

    pos=st.multiselect("Position",["QB","RB","WR","TE","DL","DB"],default=["QB","RB","WR","TE","DL","DB"],key="draftpos")
    show=x[x.position.isin(pos)].copy()
    show["Profile"]=show["profile"] if "profile" in show.columns else "Stable / neutral"
    show["Confidence"]=(show["confidence"] if "confidence" in show.columns else pd.Series(0.50,index=show.index)).map(lambda v:f"{float(v):.0%}")
    show["Market pick"]=(show["market_pick"] if "market_pick" in show.columns else pd.Series(np.nan,index=show.index)).map(lambda v:"—" if pd.isna(v) else int(round(v)))
    show["Action"]=[market_timing_state(mp,current_overall,live_next,state.get("mock",{}).get("randomness",6))[0] for mp in (show["market_pick"] if "market_pick" in show.columns else pd.Series(np.nan,index=show.index))]
    show["Survives next"]=(show["survival_next"] if "survival_next" in show.columns else pd.Series(np.nan,index=show.index)).map(lambda v:"—" if pd.isna(v) else f"{float(v):.0%}")
    show["Model target #"]=pd.to_numeric(show["evaluation_rank"],errors="coerce").fillna(len(show)+1).round().astype("Int64")
    show["Faller picks"]=np.maximum(current_overall-pd.to_numeric(show["market_pick"] if "market_pick" in show.columns else pd.Series(np.nan,index=show.index),errors="coerce"),0)
    show["Faller picks"]=show["Faller picks"].map(lambda v:"—" if pd.isna(v) or v<1 else f"+{v:.0f}")
    def _v934_public_reason(rr):
        p=str(rr.get("position",""))
        counts_now=myb.position.value_counts().to_dict() if myb is not None and len(myb) else {}
        if p in ["DL","DB"]:
            impact,eligible,evidence=_v934_idp_impact_score(rr)
            if counts_now.get(p,0)<1:
                return f"{p} starter need • impact {impact:.1f}" if eligible else f"{p} starter need • low evidence"
            return f"Optional {p} depth • impact {impact:.1f}" if eligible else f"Optional {p} depth • low evidence"
        if p=="QB" and counts_now.get("QB",0)>=1: return "QB2 bench value"
        if p=="TE" and counts_now.get("TE",0)>=1: return "TE2/FLEX value"
        if p=="WR": return "WR/FLEX depth"
        if p=="RB": return "RB/FLEX depth"
        return "Roster fit / value"
    show["Recommendation reason"]=show.apply(_v934_public_reason,axis=1)
    _draft_display_defaults={
        "team":"NFL","projection":0.0,"vorp":0.0,
        "idp_external_rank":np.nan,"idp_impact_score":np.nan,
        "roster_opportunity_adj":0.0,"injury":"","injury_source":"Local",
        "profile":"Stable / neutral","confidence":0.50,"survival_next":np.nan,
        "evaluation_rank":np.nan,"market_pick":np.nan,
    }
    for _c,_default in _draft_display_defaults.items():
        if _c not in show.columns:
            show[_c]=_default
    st.dataframe(
        show[["player","position","team","Model target #","Action","Market pick","Faller picks",
              "Survives next","projection","vorp","idp_external_rank","idp_impact_score","roster_opportunity_adj","Recommendation reason",
              "Profile","Confidence","injury","injury_source"]]
        .rename(columns={
            "injury":"Injury","injury_source":"Injury source",
            "idp_external_rank":"IDP rank","idp_impact_score":"IDP impact","usable_vorp":"Usable VORP","marginal_roster_value":"Marginal roster value","bench_startability":"Bench startability","tier_cliff_component":"Tier cliff","replacement_loss_component":"Next-turn loss","lineup_improvement_component":"Lineup gain","next_turn_survival_component":"Survival %","cross_position_cost_component":"Opportunity cost","future_roster_component":"Future roster","rollout_value":"2-pick rollout","final_pick_value":"Final pick value","challenger_gap":"Challenger gap","room_run_pressure_component":"Room pressure","candidate_stability":"Stability","base_player_value":"Base value","marginal_slot_value":"Marginal slot","wait_cost":"Wait cost","survival_probability":"Next-pick survival","strategic_pick_value":"Strategic value","rollout_value":"Rollout","expected_regret":"Expected regret","recommendation_confidence":"Confidence %","value_over_next_roster_slot":"Value over next slot","idp_available_rank":"Available IDP rank","idp_available_score":"Available IDP score","roster_opportunity_adj":"Roster opp."
        }).head(120),
        use_container_width=True,hide_index=True
    )

    st.markdown("### Record the latest pick")
    # V6.20: recording a real Yahoo pick must use the FULL available master pool,
    # not the position-filtered recommendation table. The old selector inherited
    # `show`, so unchecked position filters could make elite players disappear.
    _record_pool=board[~board["player"].isin(state.get("taken",[]))].copy()
    _record_names=sorted(_record_pool["player"].astype(str).drop_duplicates().tolist(),key=str.lower)
    _record_search=st.text_input("Search player to record",key="v621_record_search",placeholder="Type CeeDee, Walker, etc.")
    if _record_search.strip():
        _q=_record_search.strip().lower()
        _record_options=[_n for _n in _record_names if _q in _n.lower()]
    else:
        _record_options=_record_names
    pick=st.selectbox("Player selected",[""]+_record_options,key="v621_record_pick")
    pick_owner=st.radio("Who drafted him?",["Opponent","Mine"],horizontal=True,key="v91_pick_owner")
    opponent_team=st.text_input("Opponent team (optional)",key="v91_opponent_team") if pick_owner=="Opponent" else ""
    if st.button("➕ Record draft pick",type="primary") and pick:
        if pick_owner=="Mine":
            state["my_team"]=list(dict.fromkeys(state["my_team"]+[pick]))
        state["taken"]=list(dict.fromkeys(state["taken"]+[pick]))
        log=state.get("draft_log",[])
        prow=board[board["player"].eq(pick)]
        ppos=str(prow.iloc[0].position) if len(prow) else ""
        log.append({"overall_pick":len(state["taken"]),"round":live_round,"owner":pick_owner,
                    "team":("My Team" if pick_owner=="Mine" else opponent_team),
                    "player":pick,"position":ppos})
        state["draft_log"]=log
        save_state(state); st.rerun()

    if state.get("draft_log"):
        with st.expander("📋 Live draft log",expanded=False):
            logdf=pd.DataFrame(state["draft_log"])
            st.dataframe(logdf.tail(30),use_container_width=True,hide_index=True)
            st.download_button("⬇️ Download draft log",logdf.to_csv(index=False).encode("utf-8"),
                               "fantasy_edge_live_draft_log.csv","text/csv")

    # v9.1 draft correction controls
    st.markdown("### Draft controls")
    undo_col, reset_col = st.columns(2)

    if undo_col.button("↩️ Undo Last Pick", use_container_width=True):
        log=list(state.get("draft_log",[]))
        if not log:
            st.warning("There are no recorded picks to undo.")
        else:
            last=log.pop()
            player=last.get("player")
            owner=last.get("owner")

            # Remove one occurrence from taken.
            taken=list(state.get("taken",[]))
            if player in taken:
                taken.remove(player)
            state["taken"]=taken

            # If it was my pick, also remove one occurrence from my roster.
            if owner=="Mine":
                mine=list(state.get("my_team",[]))
                if player in mine:
                    mine.remove(player)
                state["my_team"]=mine

            state["draft_log"]=log
            save_state(state)
            st.success(f"Undid last pick: {player or 'unknown player'}")
            st.rerun()

    if "confirm_reset_draft_v91" not in st.session_state:
        st.session_state.confirm_reset_draft_v91=False

    if reset_col.button("🗑️ Reset Entire Draft", use_container_width=True):
        st.session_state.confirm_reset_draft_v91=True

    if st.session_state.confirm_reset_draft_v91:
        st.warning("This will clear every recorded Mine/Opponent pick and your current draft roster.")
        c_yes,c_no=st.columns(2)
        if c_yes.button("✅ Yes, reset draft", type="primary", use_container_width=True):
            state["taken"]=[]
            state["my_team"]=[]
            state["draft_log"]=[]
            # Clear older live-draft queues if present so a new draft is truly clean.
            st.session_state.pop("v761_target_queue",None)
            st.session_state.confirm_reset_draft_v91=False
            save_state(state)
            st.success("Draft reset. All players are available again.")
            st.rerun()
        if c_no.button("Cancel reset", use_container_width=True):
            st.session_state.confirm_reset_draft_v91=False
            st.rerun()

with tabs[2]:
    st.subheader("🧪 Mock Draft Lab")
    st.caption("12-team SNAKE draft: practice the exact turn order, test Fantasy Edge against consensus, and measure whether the model actually creates value.")
    st.success("🔒 Live Draft and Mock Draft Lab use the same player pool and recommendation logic.")

    m=state["mock"]
    c1,c2,c3=st.columns(3)
    slot=c1.number_input("Your draft slot",1,12,min(int(m.get("draft_slot",1)),12))
    rounds=17
    c2.number_input(
        "Rounds",min_value=17,max_value=17,value=17,disabled=True,
        key="v9441_exact_rounds",
        help="Locked to your exact 17-player roster."
    )
    randomness=c3.slider("Draft-room randomness",4,30,int(m.get("randomness",12)),
                         help="Higher values make computer teams deviate more from consensus.")
    state["mock"]={"draft_slot":int(slot),"rounds":int(rounds),"randomness":int(randomness)}

    mode=st.radio("Test mode",["Interactive mock","Automated 100-draft test"],horizontal=True)
    st.caption("Snake order check: R1 runs 1→12, R2 runs 12→1, then alternates every round.")
    st.caption("Exact league construction: 1 QB • 2 RB • 2 WR • 1 TE • 2 FLEX • 1 K • 1 DL • 1 DB • 6 Bench • 17 rounds.")
    if st.button("Set validation preset: Pick 7 • 17 rounds • randomness 6",key="v731_validation_preset"):
        state["mock"]={"draft_slot":7,"rounds":17,"randomness":6}
        save_state(state)
        st.success("Validation preset saved. Refresh once if the visible controls have not updated.")

    if mode=="Interactive mock":
        if "mock_drafted" not in st.session_state:
            st.session_state.mock_drafted=[]
            st.session_state.mock_user=[]
            st.session_state.mock_overall=1
            st.session_state.mock_opp_rosters={i:[] for i in range(1,13)}

        a,b=st.columns(2)
        if a.button("Start / reset mock"):
            st.session_state.mock_drafted=[]
            st.session_state.mock_user=[]
            st.session_state.mock_overall=1
            st.session_state.mock_opp_rosters={i:[] for i in range(1,13)}
            st.rerun()
        if b.button("Auto-draft opponents until my next pick"):
            drafted=st.session_state.mock_drafted
            overall=st.session_state.mock_overall
            rng=np.random.default_rng(overall+int(slot))
            while overall<=int(teams)*int(rounds):
                rnd=(overall-1)//int(teams)+1
                pir=(overall-1)%int(teams)+1
                owner=pir if rnd%2 else int(teams)-pir+1
                if owner==int(slot): break
                avail=board[~board["player"].isin(drafted)].copy()
                if avail.empty: break
                fallback=avail.model_rank
                base=avail.consensus_rank.fillna(fallback)
                noise=rng.normal(0,int(randomness),len(avail))
                avail["opp"]=base+noise

                # Opponent roster realism: each computer team also needs QB/RB/WR/TE/K/DL/DB.
                if "mock_opp_rosters" not in st.session_state:
                    st.session_state.mock_opp_rosters={i:[] for i in range(1,13)}
                opp_names=st.session_state.mock_opp_rosters.get(int(owner),[])
                opp_roster=board[board["player"].isin(opp_names)]
                oc=opp_roster.position.value_counts().to_dict() if len(opp_roster) else {}

                # Keep IDP out of premium rounds, then create realistic late need.
                if rnd<=7:
                    avail.loc[avail.position.isin(["DL","DB"]),"opp"]+=25.0
                if rnd>=9 and oc.get("DL",0)<1:
                    avail.loc[avail.position.eq("DL"),"opp"]-=7.0
                if rnd>=10 and oc.get("DB",0)<1:
                    avail.loc[avail.position.eq("DB"),"opp"]-=7.0
                if rnd>=14 and oc.get("K",0)<1:
                    avail.loc[avail.position.eq("K"),"opp"]-=8.0

                # Avoid duplicate onesies/depth excess.
                if oc.get("QB",0)>=1:
                    avail.loc[avail.position.eq("QB"),"opp"]+=12.0
                if oc.get("TE",0)>=1:
                    avail.loc[avail.position.eq("TE"),"opp"]+=8.0
                if oc.get("K",0)>=1:
                    avail.loc[avail.position.eq("K"),"opp"]+=100.0
                if oc.get("DL",0)>=1:
                    avail.loc[avail.position.eq("DL"),"opp"]+=5.0
                if oc.get("DB",0)>=1:
                    avail.loc[avail.position.eq("DB"),"opp"]+=5.0

                choice=avail.sort_values("opp").iloc[0]
                drafted.append(choice.player)
                st.session_state.mock_opp_rosters.setdefault(int(owner),[]).append(str(choice.player))
                drafted=list(dict.fromkeys(drafted))
                overall+=1
            st.session_state.mock_drafted=drafted
            st.session_state.mock_overall=overall
            st.rerun()

        overall=st.session_state.mock_overall
        if overall<=int(teams)*int(rounds):
            rnd=(overall-1)//int(teams)+1
            pir=(overall-1)%int(teams)+1
            owner=pir if rnd%2 else int(teams)-pir+1
            st.info(f"Overall pick {overall} • Round {rnd} • {'YOU ARE ON THE CLOCK' if owner==int(slot) else f'Team {owner} is picking'}")

            if owner==int(slot):
                avail=board[~board["player"].isin(st.session_state.mock_drafted)].copy()
                roster=pd.DataFrame(st.session_state.mock_user) if st.session_state.mock_user else board.iloc[0:0].copy()

                avail,nxt=prepare_user_draft_candidates(
                    avail,roster,rnd,overall,int(slot),int(teams),state["roster_slots"],randomness
                )
                if avail.empty:
                    st.warning("No eligible available players remain for this pick.")
                    st.stop()

                cr=pd.to_numeric(avail["market_pick"],errors="coerce").fillna(overall)
                local,ready,survive=execution_choice(
                    avail.evaluation_score.to_numpy(float),cr.to_numpy(float),
                    overall,nxt,randomness
                )
                intercept_local,intercepted,intercept_fall=faller_intercept_choice(
                    avail.evaluation_score.to_numpy(float),cr.to_numpy(float),overall,local,
                    teams=int(teams),rounds=int(rounds)
                )
                # v9.23.1 availability integrity: preserve player identity BEFORE sorting.
                # intercept_local is positional to the pre-sort available pool and must never
                # be reused as an iloc after the dataframe is reordered.
                intercept_player=None
                if intercepted and intercept_local is not None and 0 <= int(intercept_local) < len(avail):
                    intercept_player=str(avail.iloc[int(intercept_local)].player)
                avail["survival_next"]=survive
                avail["timing_ready"]=ready
                # Execution score is only for ordering the UI; player evaluation remains visible separately.
                # v9.39: execution_score is shared with Draft Mode; no mock-only reranking.
                avail["live"]=avail["execution_score"]
                avail=avail.sort_values("execution_score",ascending=False)
                nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                avail["evaluation_rank"]=avail.evaluation_score.rank(method="min",ascending=False)
                context_pool=apply_v933_context_quality_gate(avail,roster,rnd,overall)
                model_top=context_pool.sort_values("context_score",ascending=False).head(8).copy()
                now_top=avail[avail.timing_ready].sort_values("execution_score",ascending=False).head(8).copy()
                if now_top.empty: now_top=avail.head(8).copy()
                mt=model_top.iloc[0]
                mt_action,mt_surv=market_timing_state(mt.market_pick,overall,nxt,randomness)
                st.info(f"🎯 MODEL CONTEXT: {mt.player} — {mt_action}")

                available_names=set(avail.player.astype(str))
                intercept_row=None
                if intercepted and intercept_player and intercept_player in available_names:
                    rr=avail[avail.player.astype(str).eq(intercept_player)]
                    if len(rr):
                        intercept_row=rr.iloc[0]

                if intercept_row is not None:
                    st.info(f"💎 FALLER CONTEXT: {intercept_row.player} — {intercept_fall:.0f} picks past market")
                else:
                    intercepted=False
                # v9.31: exactly one authoritative recommendation. Context cards never
                # replace the roster-adjusted, timing-ready FINAL PICK.
                dn=now_top.iloc[0]
                dn_action,dn_surv=market_timing_state(dn.market_pick,overall,nxt,randomness)
                st.success(f"🏆 FINAL PICK: {dn.player} — {dn_action}")
                if nxt:
                    st.caption(f"Current pick #{overall} • next pick #{nxt}. FINAL PICK is authoritative; model/faller cards are context only.")
                top=now_top.copy()
                actions=[market_timing_state(mp,overall,nxt,randomness) for mp in top.market_pick]
                top["Action"]=[a[0] for a in actions]
                top["Survives to next pick"]=["—" if pd.isna(a[1]) else f"{a[1]:.0%}" for a in actions]
                top["Market pick"]=top.market_pick.map(lambda v:"—" if pd.isna(v) else int(round(v)))
                st.dataframe(
                    top[["player","position","team","evaluation_rank","Action","Market pick",
                         "Survives to next pick","projection","vorp","usable_vorp","marginal_roster_value","bench_startability","value_over_next_roster_slot","tier_cliff_component","replacement_loss_component","lineup_improvement_component","next_turn_survival_component","cross_position_cost_component","future_roster_component","rollout_value","final_pick_value","challenger_gap","room_run_pressure_component","candidate_stability","base_player_value","marginal_slot_value","wait_cost","survival_probability","strategic_pick_value","rollout_value","expected_regret","recommendation_confidence",
                         "idp_available_rank","idp_available_score","idp_scarcity_cliff",
                         "roster_opportunity_adj","roster_opportunity_note","profile"]]
                    .rename(columns={
                        "idp_external_rank":"IDP rank","idp_impact_score":"IDP impact","usable_vorp":"Usable VORP","marginal_roster_value":"Marginal roster value","value_over_next_roster_slot":"Value over next slot","idp_available_rank":"Available IDP rank","idp_available_score":"Available IDP score","roster_opportunity_adj":"Roster opp.",
                        "roster_opportunity_note":"Roster reason"
                    }),
                    use_container_width=True,hide_index=True
                )
                # v9.23.1: one authoritative pool controls table, intercept and selector.
                available_names=set(avail.player.astype(str))
                pick_options=[str(p) for p in top.player.tolist() if str(p) in available_names]
                final_name=str(dn.player)
                if final_name in available_names:
                    pick_options=[final_name]+[p for p in pick_options if p!=final_name]
                # Remove duplicates while preserving recommendation order.
                pick_options=list(dict.fromkeys(pick_options))

                if not pick_options:
                    st.warning("No eligible available players remain for this pick.")
                else:
                    choice=st.selectbox("Your mock pick",pick_options)
                    if st.button("Draft this player"):
                        # Final integrity gate immediately before committing the pick.
                        current_available=board[
                            (~board["player"].isin(st.session_state.mock_drafted))
                            & (board.injury_severity<3)
                        ].copy()
                        if choice not in set(current_available.player.astype(str)):
                            st.error(f"{choice} is no longer available. Refreshing the mock board.")
                            st.rerun()
                        # Re-run the FULL available pool so comparative rules remain authoritative
                        # at commit time (same-position dominance, IDP rank, scarcity, portfolio value).
                        _commit_pool,_=prepare_user_draft_candidates(
                            current_available,roster,rnd,overall,int(slot),int(teams),state["roster_slots"],randomness
                        )
                        _commit=_commit_pool[_commit_pool.player.astype(str).eq(str(choice))].copy()
                        if _commit.empty:
                            st.error(f"{choice} is no longer eligible under the live draft rules.")
                            st.rerun()
                        row=_commit.iloc[0].to_dict()
                        row["mock_pick"]=overall; row["mock_round"]=rnd
                        st.session_state.mock_user.append(row)
                        st.session_state.mock_drafted=list(dict.fromkeys(st.session_state.mock_drafted+[choice]))
                        st.session_state.mock_overall=overall+1
                        st.rerun()
            else:
                st.caption("Tap “Auto-draft opponents until my next pick” to advance quickly.")
        else:
            st.success("Mock draft complete.")

        roster=pd.DataFrame(st.session_state.mock_user) if st.session_state.mock_user else pd.DataFrame()
        if len(roster):
            g=grade_mock(roster,int(teams),state["roster_slots"])
            st.markdown("### Live mock grade")
            x1,x2,x3=st.columns(3)
            x1.metric("Grade",g["grade"],f"{g['score']:.0f}/100")
            x2.metric("Starter VORP",f"{g['starter']:+.1f}")
            x3.metric("Avg value vs market",f"{g['value']:+.1f} spots")
            st.markdown("#### Grade breakdown")
            a,b,c,d=st.columns(4)
            a.metric("Draft Value",f"{g['draft_value']:.0f}/100")
            b.metric("Roster Construction",f"{g['construction']:.0f}/100")
            c.metric("Positional Advantage",f"{g['positional_advantage']:.0f}/100")
            d.metric("Model Edge",f"{g['model_edge_score']:.0f}/100")
            st.caption(
                f"Model Edge quality: {g.get('clean_pick_rate',0):.0%} clean picks • "
                f"{g.get('market_win_rate',0):.0%} drafted at/after market • "
                f"{g.get('big_reach_rate',0):.0%} big reaches • "
                f"{g.get('portfolio_penalty',0):.1f} portfolio penalty."
            )
            if g.get("opportunity_penalty",0)>0:
                st.caption(f"Opportunity-cost adjustment: -{g['opportunity_penalty']:.1f}")
            if g.get("penalty",0)>0:
                st.warning(f"Roster-construction penalty: -{g['penalty']:.0f} grade points")
            counts=roster.position.value_counts().to_dict()
            st.caption("Roster build: " + " • ".join(f"{p} {counts.get(p,0)}" for p in ["QB","RB","WR","TE","DL","DB"]))
            _show=roster.copy()
            for _c,_raw in [("display_projection","projection"),("display_vorp","vorp"),("display_model_rank","model_rank")]:
                if _c not in _show.columns: _show[_c]=_show.get(_raw,np.nan)
            st.dataframe(
                _show[["mock_round","mock_pick","player","position","display_projection","display_vorp","display_model_rank","consensus_rank","profile"]]
                .rename(columns={"display_projection":"Model/IDP score","display_vorp":"VORP / roster impact","display_model_rank":"Model / IDP rank"}),
                use_container_width=True,hide_index=True
            )

    else:
        st.markdown("### 🧪 Automated 100-Draft Test")
        st.caption(
            "This uses the same Fantasy Edge candidate preparation, roster balance, saturation, "
            "projection/VORP, kicker, IDP, reach, timing, marginal roster value, bench optimizer, "
            "and FINAL PICK execution-score logic used by the interactive mock."
        )

        st.info(
            "⚡ Fast simulation mode: your 17 picks use the full Fantasy Edge engine. "
            "Opponent picks use a lightweight market/roster model so 100 drafts finish much faster."
        )
        target_sims=100
        _benchmark_build="FE-V6.11-MERIT-IDP-SNAKE-WAIT-20260827"
        if st.session_state.get("fe_benchmark_build")!=_benchmark_build:
            st.session_state.fe1000_results=[]
            st.session_state.fe1000_next_seed=910000
            st.session_state.fe_benchmark_failures=[]
            st.session_state.fe_benchmark_build=_benchmark_build

        batch_size=st.selectbox(
            "Drafts per run batch",
            options=[1,2,4,8],
            index=0,
            help="Drafts run in parallel. 4 is the recommended Streamlit Cloud batch size after profiling; larger batches may contend for CPU."
        )

        if "fe1000_results" not in st.session_state:
            st.session_state.fe1000_results=[]
        if "fe1000_next_seed" not in st.session_state:
            st.session_state.fe1000_next_seed=910000
        if "fe_benchmark_failures" not in st.session_state:
            st.session_state.fe_benchmark_failures=[]

        done=len(st.session_state.fe1000_results)
        st.progress(min(done/target_sims,1.0))
        st.caption(f"Completed {done:,} / {target_sims:,} automated drafts.")
        st.caption("Failed seeds are retried automatically on the next Run; successful drafts are kept.")
        if st.session_state.get("fe_benchmark_failures"):
            _fails=st.session_state.fe_benchmark_failures
            st.error(f"Benchmark engine failures: {len(_fails)}. Press Run again to retry failed seeds; completed drafts are preserved.")
            with st.expander("Show benchmark failures", expanded=True):
                for _f in _fails[-8:]:
                    st.code(f"seed {_f.get('seed')}: {_f.get('error')}",language=None)
        if st.session_state.get("fe_last_batch_seconds"):
            _secs=float(st.session_state["fe_last_batch_seconds"])
            _rate=float(st.session_state.get("fe_last_batch_rate",0.0))
            _remaining=max(target_sims-done,0)
            _eta=(_remaining/_rate) if _rate>0 else 0.0
            st.caption(f"Last batch: {_secs:.1f}s • {_rate:.2f} drafts/sec • estimated remaining runtime: {_eta/60:.1f} min")

        a,b=st.columns(2)
        run=a.button(
            "▶️ Run / continue 100-draft test",
            type="primary",
            disabled=done>=target_sims,
            key="fe1000_run"
        )
        reset=b.button("Reset simulation test",key="fe1000_reset")

        if reset:
            st.session_state.fe1000_results=[]
            st.session_state.fe1000_next_seed=910000
            st.session_state.fe_benchmark_failures=[]
            st.session_state.pop("fe_last_batch_seconds",None)
            st.session_state.pop("fe_last_batch_rate",None)
            st.rerun()

        if run:
            remaining=target_sims-len(st.session_state.fe1000_results)
            this_batch=min(int(batch_size),remaining)
            prog=st.progress(0)
            status=st.empty()
            started=time.perf_counter()

            # Prepare once per click. Every worker receives the same immutable prepared board.
            _sim_board=_prepare_fast_sim_board(board)
            _seed0=int(st.session_state.fe1000_next_seed)

            # Retry prior failed seeds first; successful drafts are preserved.
            _prior_failures=list(st.session_state.get("fe_benchmark_failures",[]))
            _retry_seeds=[]
            for _f in _prior_failures:
                try:
                    _retry_seeds.append(int(_f.get("seed")))
                except Exception:
                    pass
            _retry_seeds=list(dict.fromkeys(_retry_seeds))
            _retry_seeds=_retry_seeds[:this_batch]
            _fresh_needed=max(this_batch-len(_retry_seeds),0)
            _fresh_seeds=list(range(_seed0,_seed0+_fresh_needed))
            _seeds=_retry_seeds+_fresh_seeds

            # Failures being retried are removed now; any seed that fails again will be re-added.
            if _retry_seeds:
                _retry_set=set(_retry_seeds)
                st.session_state.fe_benchmark_failures=[
                    _f for _f in _prior_failures
                    if int(_f.get("seed",-1)) not in _retry_set
                ]

            def _run_one_sim(_seed):
                return _seed,simulate_current_fantasy_edge_once(
                    _sim_board,int(teams),int(slot),int(rounds),
                    state["roster_slots"],int(randomness),int(_seed)
                )

            # The production candidate engine is pandas/numpy heavy and benefits from overlapping
            # independent drafts. Cap workers to avoid overwhelming Streamlit Cloud memory/CPU.
            _workers=1
            _finished=[]
            _errors=[]
            with concurrent.futures.ThreadPoolExecutor(max_workers=_workers) as _pool:
                _future_map={_pool.submit(_run_one_sim,_seed):_seed for _seed in _seeds}
                for _n,_future in enumerate(concurrent.futures.as_completed(_future_map),start=1):
                    _seed=_future_map[_future]
                    try:
                        _seed,result=_future.result()
                        if result is not None:
                            _finished.append((_seed,result))
                        else:
                            _errors.append((_seed,"Simulation returned no result"))
                    except Exception as _exc:
                        _errors.append((_seed,f"{type(_exc).__name__}: {_exc}"))
                    prog.progress(_n/max(this_batch,1))
                    status.caption(
                        f"Finished {_n}/{this_batch} this batch • "
                        f"{len(st.session_state.fe1000_results)+len(_finished):,}/{target_sims:,} total"
                    )

            # Keep deterministic seed/result ordering even though workers finish out of order.
            _finished.sort(key=lambda x:x[0])
            if _errors:
                st.session_state.fe_benchmark_failures.extend(
                    [{"seed":int(_seed),"error":str(_err)} for _seed,_err in _errors]
                )
            for _seed,result in _finished:
                result["simulation"]=len(st.session_state.fe1000_results)+1
                result["seed"]=int(_seed)
                st.session_state.fe1000_results.append(result)

            st.session_state.fe1000_next_seed=_seed0+_fresh_needed
            _elapsed=max(time.perf_counter()-started,0.001)
            st.session_state["fe_last_batch_seconds"]=_elapsed
            st.session_state["fe_last_batch_rate"]=max(len(_finished),1)/_elapsed
            if _errors:
                st.session_state["fe_last_batch_error_count"]=len(_errors)
            else:
                st.session_state.pop("fe_last_batch_error_count",None)
            st.rerun()

        sim_df=pd.DataFrame(st.session_state.fe1000_results)
        if len(sim_df):
            st.markdown("### Simulation results")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Drafts completed",f"{len(sim_df):,}")
            c2.metric("Average grade",f"{sim_df.grade.mean():.1f}")
            c3.metric("Average Model Edge",f"{sim_df.model_edge.mean():.1f}/100")
            c4.metric("Legal roster rate",f"{sim_df.legal_roster.mean():.1%}")
            if all(c in sim_df.columns for c in ["starter_vorp","harmful_regret_count","champion_score"]):
                q1,q2,q3,q4=st.columns(4)
                q1.metric("Avg Starter VORP",f"{pd.to_numeric(sim_df.starter_vorp,errors='coerce').mean():.1f}")
                q2.metric("Harmful regret / draft",f"{pd.to_numeric(sim_df.harmful_regret_count,errors='coerce').mean():.2f}")
                q3.metric("Major reaches / draft",f"{pd.to_numeric(sim_df.major_reach_count,errors='coerce').mean():.2f}")
                q4.metric("Champion score",f"{pd.to_numeric(sim_df.champion_score,errors='coerce').mean():.1f}")

            d1,d2,d3,d4=st.columns(4)
            d1.metric("Avg RB",f"{sim_df.RB.mean():.2f}")
            d2.metric("Avg WR",f"{sim_df.WR.mean():.2f}")
            d3.metric("Avg IDP",f"{sim_df.IDP_total.mean():.2f}")
            d4.metric("3+ IDP drafts",f"{(sim_df.IDP_total>=3).mean():.1%}")

            st.markdown("#### Construction distribution")
            construction_summary=pd.DataFrame({
                "Metric":[
                    "6+ RB drafts","6+ WR drafts","Only 2 IDPs",
                    "3+ IDPs","4 IDPs","Invalid required roster"
                ],
                "Rate":[
                    float((sim_df.RB>=6).mean()),
                    float((sim_df.WR>=6).mean()),
                    float((sim_df.IDP_total<=2).mean()),
                    float((sim_df.IDP_total>=3).mean()),
                    float((sim_df.IDP_total>=4).mean()),
                    float((~sim_df.legal_roster).mean()),
                ]
            })
            construction_summary["Rate"]=construction_summary["Rate"].map(lambda v:f"{v:.1%}")
            st.dataframe(construction_summary,use_container_width=True,hide_index=True)

            st.markdown("#### Score distribution")
            st.dataframe(
                sim_df[[c for c in ["simulation","grade","model_edge","draft_value","construction",
                        "positional_advantage","opportunity_penalty","starter_vorp","bench_upside",
                        "harmful_regret_count","major_reach_count","champion_score",
                        "RB","WR","DL","DB","IDP_total","legal_roster"] if c in sim_df.columns]]
                .tail(100),
                use_container_width=True,hide_index=True
            )

            if len(sim_df)>=target_sims:
                _cert={
                    "100% legal rosters": bool(sim_df["legal_roster"].fillna(False).all()),
                    "100% production-engine user picks": bool((pd.to_numeric(sim_df["production_engine_usage"],errors="coerce").fillna(0)>=0.999).all()),
                    "0 unavailable-player recommendations": bool((pd.to_numeric(sim_df["unavailable_user_picks"],errors="coerce").fillna(999)==0).all()),
                    "0 duplicate user players": bool((pd.to_numeric(sim_df["duplicate_user_players"],errors="coerce").fillna(999)==0).all()),
                    "Exact configured roster size": bool(
                        (pd.to_numeric(sim_df["roster_size"],errors="coerce").fillna(0) ==
                         pd.to_numeric(sim_df["expected_roster_size"],errors="coerce").fillna(-1)).all()
                    ),
                    "100% TE completion": bool((pd.to_numeric(sim_df["TE"],errors="coerce").fillna(0)>=1).all()),
                    "100% K completion": bool((pd.to_numeric(sim_df["K"],errors="coerce").fillna(0)>=1).all()),
                    "100% DL completion": bool((pd.to_numeric(sim_df["DL"],errors="coerce").fillna(0)>=1).all()),
                    "100% DB completion": bool((pd.to_numeric(sim_df["DB"],errors="coerce").fillna(0)>=1).all()),
                    "0 drafts with 4+ IDPs": bool((pd.to_numeric(sim_df["IDP_total"],errors="coerce").fillna(99)<=3).all()),
                    "0 production-engine exceptions": bool(len(st.session_state.get("fe_benchmark_failures",[]))==0),
                    "Average Construction >= 94": bool(pd.to_numeric(sim_df["construction"],errors="coerce").mean()>=94.0),
                    "Average Opportunity Penalty <= 6": bool(pd.to_numeric(sim_df["opportunity_penalty"],errors="coerce").mean()<=6.0),
                    "Average Draft Value >= 85": bool(pd.to_numeric(sim_df["draft_value"],errors="coerce").mean()>=85.0),
                    "Average Model Edge >= 82": bool(pd.to_numeric(sim_df["model_edge"],errors="coerce").mean()>=82.0),
                    "Average Opportunity Penalty <= 4": bool(pd.to_numeric(sim_df["opportunity_penalty"],errors="coerce").mean()<=4.0),
                    "0 harmful-regret decisions": bool((pd.to_numeric(sim_df.get("harmful_regret_count",0),errors="coerce").fillna(99)==0).all()),
                    "0 major reaches": bool((pd.to_numeric(sim_df.get("major_reach_count",0),errors="coerce").fillna(99)==0).all()),
                    "Average Starter VORP >= 34": bool(pd.to_numeric(sim_df.get("starter_vorp",0),errors="coerce").mean()>=34.0),
                    "No RB7+ rosters": bool((pd.to_numeric(sim_df["RB"],errors="coerce").fillna(99)<=6).all()),
                    "No WR7+ rosters": bool((pd.to_numeric(sim_df["WR"],errors="coerce").fillna(99)<=6).all()),
                }
                st.markdown("### Certification")
                st.dataframe(pd.DataFrame({"Check":list(_cert.keys()),"Pass":list(_cert.values())}),use_container_width=True,hide_index=True)
                if all(_cert.values()):
                    st.success("100-draft certification PASSED. Results are safe to use for tuning.")
                else:
                    st.error("100-draft certification FAILED. Do not tune weights from this run.")

        st.caption(
            "Fantasy Edge simulation tools use the current roster construction, value, timing, "
            "IDP, kicker, reach, and bench-optimization rules above."
        )

with tabs[3]:
    st.subheader("Yahoo waiver candidates")
    _waiver_board=board.copy()
    if "waiver_score" not in _waiver_board.columns:
        _wp=pd.to_numeric(_waiver_board["projection"],errors="coerce").fillna(0.0)
        _wg=pd.to_numeric(_waiver_board["progression"],errors="coerce").fillna(0.0)
        _wr=pd.to_numeric(_waiver_board["regression"],errors="coerce").fillna(0.0)
        _waiver_board["waiver_score"]=_wp*4+_wg*.23-_wr*.10
    x=_waiver_board[~_waiver_board["player"].isin(set(state["taken"]))].sort_values("waiver_score",ascending=False).copy()
    x["Breakout"]=x["breakout"].map(lambda v:f"{float(v):.0%}")
    if len(x):
        x["Suggested FAAB"]=np.clip((x.waiver_score-x.waiver_score.quantile(.35))*.7,1,35)/100*faab
        x["Suggested FAAB"]=pd.to_numeric(x["Suggested FAAB"],errors="coerce").fillna(0).round().astype(int)
    st.dataframe(x[["player","position","team","projection","Breakout","injury","Suggested FAAB","waiver_score"]].head(100),
                 use_container_width=True,hide_index=True)

with tabs[4]:
    st.subheader("🛡️ Defensive Lineman & Defensive Back board")
    st.caption("DL emphasizes sacks/pressure plus tackle volume. DB emphasizes tackle floor plus interceptions/pass breakups, while discounting unsustainable big-play spikes.")
    x=board[board["position"].isin(["DL","DB"]) & ~board["player"].isin(set(state["taken"]))].copy()
    idppos=st.radio("IDP position",["Both","DL","DB"],horizontal=True)
    if idppos!="Both": x=x[x["position"].eq(idppos)]
    x["Breakout"]=x["breakout"].map(lambda v:f"{float(v):.0%}")
    x["Regression"]=x["decline"].map(lambda v:f"{float(v):.0%}")
    st.dataframe(x[["player","position","raw_position","team","projection","vorp","Breakout","Regression","injury","draft_score"]].head(80),
                 use_container_width=True,hide_index=True)

with tabs[5]:
    a,b=st.columns(2)
    with a:
        st.subheader("🚀 Breakout")
        x=board.sort_values("breakout",ascending=False).head(35).copy(); x["Probability"]=x["breakout"].map(lambda v:f"{float(v):.0%}")
        st.dataframe(x[["player","position","team","Probability","projection","progression"]],use_container_width=True,hide_index=True)
    with b:
        st.subheader("📉 Regression")
        x=board.sort_values("decline",ascending=False).head(35).copy(); x["Probability"]=x["decline"].map(lambda v:f"{float(v):.0%}")
        st.dataframe(x[["player","position","team","Probability","projection","regression"]],use_container_width=True,hide_index=True)

with tabs[6]:
    x=board[board["player"].isin(state["my_team"])].copy()
    if x.empty: st.info("Add your Yahoo roster under League Setup.")
    else:
        x["Breakout"]=x.breakout.map(lambda v:f"{v:.0%}"); x["Regression"]=x.decline.map(lambda v:f"{v:.0%}")
        st.dataframe(x[["player","position","team","projection","Breakout","Regression","injury"]],
                     use_container_width=True,hide_index=True)

with tabs[7]:
    name=st.selectbox("Player",all_names)
    p=board[board["player"].eq(name)].iloc[0]
    a,b,c,d=st.columns(4)
    a.metric("Projected PPG",f"{p.projection:.1f}")
    b.metric("Last PPG",f"{p.last_ppg:.1f}")
    c.metric("Profile",p.profile)
    d.metric("Confidence",f"{p.confidence:.0%}")
    st.write({"Team":p.team,"Position":p.position,"Listed position":p.raw_position,
              "Progression score":round(float(p.progression),1),"Regression score":round(float(p.regression),1),
              "Model rank":int(p.model_rank),"Consensus rank":None if pd.isna(p.consensus_rank) else int(p.consensus_rank),
              "Yahoo status":"My team" if name in state["my_team"] else "Taken" if name in state["taken"] else "Available"})

if hist.empty and "hist_error" in st.session_state:
    st.warning("Historical nflverse data did not load, so conservative position baselines are temporarily being used.")

if isinstance(market,pd.DataFrame) and market.empty and "market_error" in st.session_state:
    st.warning("Current consensus rankings did not load, so the app is temporarily using the statistical model without the consensus reality-check layer.")
