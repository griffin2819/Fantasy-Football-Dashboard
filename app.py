import streamlit as st
import pandas as pd
import numpy as np
import requests, re, unicodedata, json, time
from pathlib import Path

st.set_page_config(page_title="Fantasy Edge — Yahoo IDP", page_icon="🏈", layout="wide")
STATE = Path("fantasy_edge_state.json")

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b","",s)
    return re.sub(r"[^a-z0-9]","",s)

def load_state():
    default={
        "teams":12,"ppr":1.0,"pass_td":4,"faab":100,
        "my_team":[],"taken":[],
        "roster_slots":{"QB":1,"RB":2,"WR":2,"TE":1,"FLEX":1,"DL":1,"DB":1},
        "mock":{"draft_slot":1,"rounds":15,"randomness":12},
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

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

@st.cache_data(ttl=86400)
def sleeper_players():
    # Used only as a live NFL player directory, not as the fantasy-league source.
    r=requests.get("https://api.sleeper.app/v1/players/nfl",timeout=30)
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

def make_board(players, hist, market, ppr, pass_td, idp, teams, slots):
    rows=[]
    for pid,p in players.items():
        rawpos=p.get("position")
        grp=canonical_position(rawpos)
        if grp not in ["QB","RB","WR","TE","DL","DB"] or p.get("active") is False: continue
        name=p.get("full_name") or " ".join([p.get("first_name") or "",p.get("last_name") or ""]).strip()
        if not name: continue
        rows.append({"id":str(pid),"player":name,"key":norm(name),"position":grp,"raw_position":rawpos,
                     "team":p.get("team") or "FA","age":p.get("age"),"exp":p.get("years_exp"),
                     "injury":p.get("injury_status")})
    b=pd.DataFrame(rows)
    if b.empty: return b

    if hist.empty:
        b["last_ppg"]=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"DL":6,"DB":5.5})
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

        base=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"DL":6,"DB":5.5})
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

    base=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"DL":6,"DB":5.5})
    b["projection"]=(b.last_ppg*.70+b.prior_ppg*.20+base*.10+b.growth_z*.50).clip(lower=1)

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

    # Pure model score before market consensus: this is where we intentionally disagree with consensus.
    scarcity=b.position.map({"QB":0.0,"RB":0.9,"WR":1.35,"TE":0.35,"DL":-0.35,"DB":-0.45}).fillna(0)
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
def draft_eligibility(avail, roster, round_no, rounds, slots):
    """Only enforce legality and end-of-draft starter completion; bench shape stays dynamic."""
    a=avail.copy()
    counts=roster.position.value_counts().to_dict() if len(roster) else {}
    qb=counts.get("QB",0); te=counts.get("TE",0); dl=counts.get("DL",0); db=counts.get("DB",0)

    # Reasonable maximums, not target counts.
    if int(slots.get("QB",1))<=1 and qb>=2: a=a[~a.position.eq("QB")]
    if int(slots.get("TE",1))<=1 and te>=2: a=a[~a.position.eq("TE")]
    if dl>=max(int(slots.get("DL",1)),1): a=a[~a.position.eq("DL")]
    if db>=max(int(slots.get("DB",1)),1): a=a[~a.position.eq("DB")]

    # Shallow IDP stays out of premium rounds unless the offensive pool is exhausted.
    if round_no<=7:
        offense=a[~a.position.isin(["DL","DB"])]
        if len(offense)>=5: a=offense

    # Only hard construction rule: finish every required non-FLEX starter.
    missing=[]
    for p in ["QB","RB","WR","TE","DL","DB"]:
        need=max(int(slots.get(p,0))-int(counts.get(p,0)),0)
        missing.extend([p]*need)
    user_picks_left=int(rounds)-int(round_no)+1
    if missing and user_picks_left<=len(missing):
        forced=a[a.position.isin(set(missing))]
        if len(forced): a=forced
    return a
def grade_mock(roster, teams, slots):
    if roster is None or len(roster)==0:
        return {"score":0,"grade":"F","starter":0,"value":0,"penalty":100,
                "draft_value":0,"construction":0,"positional_advantage":0,"model_edge_score":0,"opportunity_penalty":0}
    r=roster.copy(); counts=r.position.value_counts().to_dict()
    req={p:max(int(slots.get(p,d)),1) for p,d in {"QB":1,"RB":2,"WR":2,"TE":1,"DL":1,"DB":1}.items()}
    edge=(r.consensus_rank.fillna(r.model_rank)-r.model_rank).clip(-20,20)
    avg=float(edge.mean())
    draft_value=float(np.clip(70+avg,35,94))
    construction=100.0
    for p,v in req.items(): construction-=16*max(v-counts.get(p,0),0)
    qb,rb,wr,te,dl,db=[counts.get(p,0) for p in ["QB","RB","WR","TE","DL","DB"]]
    construction-=7*max(4-wr,0); construction-=5*max(4-rb,0)
    if wr<4: construction-=6*max(rb-5,0)
    construction-=12*max(qb-2,0)+10*max(te-2,0)
    construction-=7*max(dl-req["DL"],0)+7*max(db-req["DB"],0)
    construction=float(np.clip(construction,0,100))
    starter=0.0
    for p in ["QB","TE","DL","DB"]:
        starter+=float(r.loc[r.position.eq(p),"vorp"].nlargest(req[p]).sum())
    starter+=float(r[r.position.isin(["RB","WR"])]["vorp"].nlargest(req["RB"]+req["WR"]+max(int(slots.get("FLEX",1)),0)).sum())
    positional=float(np.clip(48+starter*.72,35,94))
    conf=float(r["confidence"].mean()) if "confidence" in r.columns else .75
    model_edge=float(np.clip(56+avg*.65+(conf-.75)*20,35,90))
    opp=0.0; seen={"QB":0,"TE":0}
    ordered=r.sort_values("mock_pick") if "mock_pick" in r.columns else r
    for _,row in ordered.iterrows():
        p=row.position
        if p in seen:
            seen[p]+=1
            if seen[p]>=2 and float(row.get("mock_pick",999))<120: opp+=4
        cr=row.get("consensus_rank",np.nan)
        if pd.notna(cr):
            ahead=max(float(cr)-float(row.get("mock_pick",cr)),0)
            if ahead>20: opp+=min(7,(ahead-20)*.10)
    score=float(np.clip(.28*draft_value+.32*construction+.24*positional+.16*model_edge-opp,0,97))
    grade="A+" if score>=94 else "A" if score>=90 else "A-" if score>=86 else "B+" if score>=82 else "B" if score>=78 else "B-" if score>=74 else "C+" if score>=70 else "C" if score>=65 else "C-" if score>=60 else "D" if score>=55 else "F"
    return {"score":score,"grade":grade,"starter":starter,"value":avg,"penalty":max(0,100-construction),
            "draft_value":draft_value,"construction":construction,"positional_advantage":positional,
            "model_edge_score":model_edge,"opportunity_penalty":opp}

def _injury_severity(status):
    x=str(status or "").strip().lower()
    if x in ["ir","pup","nfi","reserve/ir","reserve/pup"]: return 3
    if x in ["out","suspended","susp"]: return 2
    if x in ["doubtful","questionable","q","d"]: return 1
    return 0


def _market_pick_series(df, teams):
    """Put offensive overall ECR and IDP-page ECR onto one approximate pick scale."""
    cr=pd.to_numeric(df["consensus_rank"],errors="coerce")
    out=cr.copy()
    idp=df["position"].isin(["DL","DB"])
    out.loc[idp]=float(teams)*8 + (cr.loc[idp].fillna(40)-1)*2.0
    return out

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
    injury=np.array([_injury_severity(x) for x in pool.injury],dtype=np.int8)
    confidence=pd.to_numeric(pool.confidence,errors="coerce").fillna(.65).clip(.30,.95).to_numpy(dtype=float)
    return {"pool":pool,"pos_names":pos_names,"pos_code":pos_code,"consensus":consensus,
            "market_pick":market_pick,"model_rank":model_rank,"draft_score":draft_score,
            "projection":projection,"vorp":vorp,"injury":injury,"confidence":confidence}


def _fast_roster_utility(fast, selected, slots):
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
        total += float(np.sum(proj[take]+0.90*vorp[take]))
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


def _fast_candidate_deltas(fast, selected, candidates, slots, exact_cap=56):
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
    current=_fast_roster_utility(fast,selected,slots)
    delta=np.asarray([_fast_roster_utility(fast,selected+[int(c)],slots)-current for c in short],dtype=float)
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

def simulate_mock_fast(fast, teams, slot, rounds, slots, randomness=12, model_user=True, seed=None,
                       room_profile="Consensus", wr_eval_deficit=10.0, wr_survival=.52, wr_enabled=True):
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
    total=int(teams)*int(rounds)
    qb,rb,wr,te,dl,db=0,1,2,3,4,5

    for overall in range(1,total+1):
        round_no=(overall-1)//int(teams)+1
        pir=(overall-1)%int(teams)+1
        owner=pir if round_no%2 else int(teams)-pir+1
        idx=np.flatnonzero(alive)
        if idx.size==0: break

        if owner==int(slot):
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
                sidx,delta=_fast_candidate_deltas(fast,user_idx,eidx,slots,exact_cap=56)
                cr=np.where(np.isnan(market_pick[sidx]),float(overall),market_pick[sidx])
                edge=np.clip(cr-model_rank[sidx],-24,24)
                edge=np.where(np.isin(pos[sidx],[dl,db]),edge*.45,edge)

                # V7.9 PLAYER EVALUATION: who do we believe is best, independent of when to draft him?
                eval_score=(0.38*draft_score[sidx] + 3.60*delta + 0.18*edge)
                eval_score-=np.where(injury[sidx]==2,12.0,np.where(injury[sidx]==1,2.5,0.0))
                eval_score+=rng.normal(0,(1.0-confidence[sidx])*float(randomness)*0.30,size=sidx.size)
                if round_no<=7:
                    eval_score-=np.where(np.isin(pos[sidx],[dl,db]),(8-round_no)*2.2,0)

                # V7.9 PICK EXECUTION: among our model targets, whose draft window is actually open now?
                nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                local_choice,_,_=execution_choice(eval_score,cr,overall,nxt,randomness)
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
                local_choice,_,_=faller_intercept_choice(
                    eval_score,cr,overall,local_choice,
                    teams=int(teams),rounds=int(rounds)
                )
                chosen=int(sidx[int(local_choice)])
            else:
                # Consensus baseline unchanged.
                ce=eidx[injury[eidx]<3]
                if ce.size==0: ce=eidx
                noise=rng.normal(0,float(randomness)/3,ce.size)
                cr=np.where(np.isnan(market_pick[ce]),model_rank[ce],market_pick[ce])
                inj_cost=np.where(injury[ce]==2,28.0,np.where(injury[ce]==1,5.0,0.0))
                chosen=int(ce[int(np.argmin(cr+noise+inj_cost))])

            user_idx.append(chosen); user_pick.append(overall); user_round.append(round_no)
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

    roster=pool.iloc[user_idx].copy()
    roster["mock_pick"]=user_pick; roster["mock_round"]=user_round
    roster["market_pick"]=market_pick[user_idx]
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

state=load_state()

st.title("🏈 Fantasy Edge V7.24 — 10/52 Champion Validation")
st.caption("V7.24 • calibrated 10/52 Early-WR rule • clean champion validation")
st.caption("Build ID: V7.24-1052CV-20260814")

with st.sidebar:
    st.header("Yahoo league settings")
    teams=st.number_input("Teams",8,20,int(state["teams"]))
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
    slots["FLEX"]=r1.number_input("FLEX",0,4,int(slots["FLEX"]))
    slots["DL"]=r2.number_input("DL",0,4,int(slots["DL"]))
    slots["DB"]=r1.number_input("DB",0,4,int(slots["DB"]))

    state.update({"teams":teams,"ppr":ppr,"pass_td":pass_td,"faab":faab,"idp":idp,"roster_slots":slots})
    if st.button("Save all scoring settings"):
        save_state(state); st.success("Saved")

players=sleeper_players()
hist=nfl_history()
market=market_rankings(ppr)
board=make_board(players,hist,market,ppr,pass_td,idp,teams,state["roster_slots"])
board["market_pick"]=_market_pick_series(board,teams)
board["injury_severity"]=board.injury.map(_injury_severity)
all_names=board.player.tolist()
state["my_team"]=[x for x in state.get("my_team",[]) if x in all_names]
state["taken"]=[x for x in state.get("taken",[]) if x in all_names]

tabs=st.tabs(["⚙️ League Setup","🎯 Draft Mode","🧪 Mock Draft Lab","🧲 Waiver Wire","🛡️ IDP Board","📈 Breakout / Regression","👤 My Team","🔎 Player Lab"])

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
    st.subheader("Live roster-aware draft assistant")
    live_slot=st.number_input("Your Yahoo draft slot (for pick-timing estimates)",1,int(teams),min(int(state.get("mock",{}).get("draft_slot",1)),int(teams)),key="v724_live_slot")
    x=board[(~board.player.isin(set(state["taken"]))) & (board.injury_severity<3)].copy()

    # Roster-aware need score.
    myb=board[board.player.isin(state["my_team"])].copy()
    counts=myb.position.value_counts().to_dict()
    slots=state["roster_slots"]
    flex_filled=max(0, sum(counts.get(p,0) for p in ["RB","WR","TE"])-sum(slots.get(p,0) for p in ["RB","WR","TE"]))
    flex_need=max(int(slots.get("FLEX",0))-flex_filled,0)
    def need_bonus(pos):
        return roster_need_for_mock(myb,pos,slots)

    # Approximate current round from number of players marked taken.
    live_round=max(1,int(len(state["taken"])//max(int(teams),1))+1)
    x=draft_eligibility(x,myb,live_round,18,slots)
    x["_construction_bonus"]=0.0
    if counts.get("WR",0)<3: x.loc[x.position.eq("WR"),"_construction_bonus"]+=5.0
    elif counts.get("WR",0)==3: x.loc[x.position.eq("WR"),"_construction_bonus"]+=4.0
    elif counts.get("WR",0)==4: x.loc[x.position.eq("WR"),"_construction_bonus"]+=1.0
    if counts.get("RB",0)>=4: x.loc[x.position.eq("RB"),"_construction_bonus"]-=4.0
    if counts.get("RB",0)>=5: x.loc[x.position.eq("RB"),"_construction_bonus"]-=8.0
    x["roster_need"]=x.position.map(need_bonus)
    live_delta=_candidate_roster_delta_df(myb,x,slots,exact_cap=64)
    x["roster_delta"]=live_delta
    current_overall=max(1,len(state["taken"])+1)
    cr=x.market_pick.fillna(current_overall)
    edge=np.clip(cr-x.model_rank,-24,24)
    edge=np.where(x.position.isin(["DL","DB"]),edge*.45,edge)
    live_next=next_user_pick(current_overall,int(live_slot),int(teams),18)

    # PLAYER EVALUATION — who Fantasy Edge believes is best.
    x["evaluation_score"]=(.38*x.draft_score+3.60*live_delta+.18*edge)
    x["evaluation_score"]-=np.where(x.injury_severity==2,12.0,np.where(x.injury_severity==1,2.5,0.0))

    # PICK EXECUTION — who is worth spending THIS pick on.
    local,ready,survive=execution_choice(x.evaluation_score.to_numpy(float),cr.to_numpy(float),current_overall,live_next,state.get("mock",{}).get("randomness",6))
    intercept_local,intercepted,intercept_fall=faller_intercept_choice(
        x.evaluation_score.to_numpy(float),cr.to_numpy(float),current_overall,local,
        teams=int(teams),rounds=18
    )
    dyn_min_fall,dyn_band,dyn_improve=dynamic_faller_threshold(current_overall,int(teams),18)
    x["survival_next"]=survive
    x["timing_ready"]=ready
    x["evaluation_rank"]=x.evaluation_score.rank(method="min",ascending=False)
    reach=np.maximum(cr-current_overall,0)
    fall=np.maximum(current_overall-cr,0)
    x["execution_score"]=x.evaluation_score.copy()
    x.loc[~x.timing_ready,"execution_score"]-=x.loc[~x.timing_ready,"survival_next"]*np.minimum(reach[~x.timing_ready],36)*.42
    x["execution_score"]+=.035*fall
    x=x.sort_values("execution_score",ascending=False)

    st.caption(f"Dynamic Faller Intercept this round: {dyn_min_fall:.0f}+ picks past market • top {dyn_band} model targets • {dyn_improve:.0f}-pick improvement required"
               + (" • LATE-ROUND VALUE HARVEST ACTIVE" if live_round>=11 else ""))
    # Two-track dashboard: evaluation and execution are intentionally separate.
    model_targets=x.sort_values("evaluation_score",ascending=False).head(8).copy()
    draft_now=x[x.timing_ready].sort_values("evaluation_score",ascending=False).head(5).copy()
    if draft_now.empty:
        draft_now=x.head(5).copy()

    if len(model_targets):
        mt=model_targets.iloc[0]
        mt_action,mt_surv=market_timing_state(mt.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        st.info(f"🎯 #1 MODEL TARGET: {mt.player} ({mt.position}, {mt.team}) — {mt_action}")
        mp="—" if pd.isna(mt.market_pick) else f"#{int(round(mt.market_pick))}"
        sv="—" if pd.isna(mt_surv) else f"{mt_surv:.0%}"
        st.caption(f"Model evaluation #{int(mt.evaluation_rank)} • market {mp} • chance available next pick {sv} • current #{current_overall} → next {('#'+str(live_next)) if live_next else '—'}")

    if intercepted:
        fi=x.iloc[int(intercept_local)]
        st.success(f"💎 FALLER INTERCEPT: {fi.player} ({fi.position}, {fi.team}) — {intercept_fall:.0f} picks past market")
        st.caption(f"Dynamic override triggered because the fall is large enough for this draft stage and the player remains model-compatible. Model target #{int(fi.evaluation_rank)} • market #{int(round(fi.market_pick)) if pd.notna(fi.market_pick) else '—'}")
    elif len(draft_now):
        dn=draft_now.iloc[0]
        dn_action,dn_surv=market_timing_state(dn.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        if dn_action=="VALUE FALLER":
            st.success(f"💎 DRAFT NOW — VALUE FALLER: {dn.player} ({dn.position}, {dn.team})")
        else:
            st.success(f"✅ DRAFT NOW: {dn.player} ({dn.position}, {dn.team})")
        st.caption(f"Model target #{int(dn.evaluation_rank)} • market {('—' if pd.isna(dn.market_pick) else '#'+str(int(round(dn.market_pick))))} • timing window is open")

    # Persistent target queue: automatically track high-evaluation players we intentionally pass on.
    if "v724_target_queue" not in st.session_state:
        st.session_state.v724_target_queue={}
    queue=st.session_state.v724_target_queue
    available_names=set(x.player)
    for name in list(queue):
        if name not in available_names:
            queue.pop(name,None)
    for _,r in model_targets.iterrows():
        action,surv=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        if action=="WAIT / TARGET NEXT PICK":
            queue[r.player]={"market_pick":None if pd.isna(r.market_pick) else float(r.market_pick),
                             "evaluation_rank":int(r.evaluation_rank),"position":r.position,"team":r.team}
    # Remove queue players whose timing window has opened; they are now DRAFT NOW targets.
    for name in list(queue):
        rr=x[x.player.eq(name)]
        if len(rr):
            r=rr.iloc[0]
            action,_=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
            if action!="WAIT / TARGET NEXT PICK":
                queue.pop(name,None)
    st.session_state.v724_target_queue=queue

    if queue:
        qrows=[]
        for name,data in queue.items():
            rr=x[x.player.eq(name)]
            if not len(rr): continue
            r=rr.iloc[0]
            action,surv=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
            qrows.append({"Target":name,"Pos":r.position,"Model target #":int(r.evaluation_rank),
                          "Market pick":"—" if pd.isna(r.market_pick) else int(round(r.market_pick)),
                          "Chance survives":"—" if pd.isna(surv) else f"{surv:.0%}","Status":action})
        if qrows:
            st.markdown("### 🎯 Target Queue")
            st.caption("Players Fantasy Edge likes but is intentionally waiting on. They leave the queue when their draft window opens or another team takes them.")
            st.dataframe(pd.DataFrame(qrows).sort_values("Model target #"),use_container_width=True,hide_index=True)

    st.markdown("**Best remaining by position**")
    poscols=st.columns(3)
    for i,pos in enumerate(["RB","WR","QB","TE","DL","DB"]):
        px=x[x.position.eq(pos)]
        if len(px):
            r=px.iloc[0]
            with poscols[i%3]:
                st.caption(f"**{pos}: {r.player}** — {r.projection:.1f} PPG, VORP {r.vorp:+.1f}")

    pos=st.multiselect("Position",["QB","RB","WR","TE","DL","DB"],default=["QB","RB","WR","TE","DL","DB"],key="draftpos")
    show=x[x.position.isin(pos)].copy()
    show["Profile"]=show.profile
    show["Confidence"]=show.confidence.map(lambda v:f"{v:.0%}")
    show["Market pick"]=show.market_pick.map(lambda v:"—" if pd.isna(v) else int(round(v)))
    show["Action"]=[market_timing_state(mp,current_overall,live_next,state.get("mock",{}).get("randomness",6))[0] for mp in show.market_pick]
    show["Survives next"] = show.survival_next.map(lambda v:"—" if pd.isna(v) else f"{v:.0%}")
    show["Model target #"]=show.evaluation_rank.astype(int)
    show["Faller picks"]=np.maximum(current_overall-pd.to_numeric(show.market_pick,errors="coerce"),0)
    show["Faller picks"]=show["Faller picks"].map(lambda v:"—" if pd.isna(v) or v<1 else f"+{v:.0f}")
    st.dataframe(show[["player","position","team","Model target #","Action","Market pick","Faller picks","Survives next","projection","vorp","Profile","Confidence","injury"]].head(120),use_container_width=True,hide_index=True)

    pick=st.selectbox("Latest drafted player",[""]+show.player.tolist())
    c1,c2=st.columns(2)
    if c1.button("✅ Draft to MY team") and pick:
        state["my_team"]=list(dict.fromkeys(state["my_team"]+[pick]))
        state["taken"]=list(dict.fromkeys(state["taken"]+[pick]))
        save_state(state); st.rerun()
    if c2.button("Opponent drafted") and pick:
        state["taken"]=list(dict.fromkeys(state["taken"]+[pick]))
        save_state(state); st.rerun()

with tabs[2]:
    st.subheader("🧪 Mock Draft Lab")
    st.caption("Practice the draft, test Fantasy Edge against consensus, and measure whether the model actually creates value.")

    m=state["mock"]
    c1,c2,c3=st.columns(3)
    slot=c1.number_input("Your draft slot",1,int(teams),min(int(m.get("draft_slot",1)),int(teams)))
    rounds=c2.number_input("Rounds",8,25,int(m.get("rounds",15)))
    randomness=c3.slider("Draft-room randomness",4,30,int(m.get("randomness",12)),
                         help="Higher values make computer teams deviate more from consensus.")
    state["mock"]={"draft_slot":int(slot),"rounds":int(rounds),"randomness":int(randomness)}

    mode=st.radio("Test mode",["Interactive mock","Auto simulation / benchmark"],horizontal=True)
    st.caption("V7.24 promotes the fully calibrated 10/52 Early-WR rule as the sole champion candidate. No calibration matrix or additional model changes are active.")
    if st.button("Set validation preset: Pick 7 • 15 rounds • randomness 6",key="v731_validation_preset"):
        state["mock"]={"draft_slot":7,"rounds":15,"randomness":6}
        save_state(state)
        st.success("Validation preset saved. Refresh once if the visible controls have not updated.")

    if mode=="Interactive mock":
        if "mock_drafted" not in st.session_state:
            st.session_state.mock_drafted=[]
            st.session_state.mock_user=[]
            st.session_state.mock_overall=1

        a,b=st.columns(2)
        if a.button("Start / reset mock"):
            st.session_state.mock_drafted=[]
            st.session_state.mock_user=[]
            st.session_state.mock_overall=1
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
                avail=board[~board.player.isin(drafted)].copy()
                if avail.empty: break
                fallback=avail.model_rank
                base=avail.consensus_rank.fillna(fallback)
                noise=rng.normal(0,int(randomness),len(avail))
                avail["opp"]=base+noise
                avail.loc[avail.position.isin(["DL","DB"]),"opp"] += max(0,55-overall)*.35
                choice=avail.sort_values("opp").iloc[0]
                drafted.append(choice.player)
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
                avail=board[(~board.player.isin(st.session_state.mock_drafted)) & (board.injury_severity<3)].copy()
                roster=pd.DataFrame(st.session_state.mock_user) if st.session_state.mock_user else board.iloc[0:0].copy()
                avail=draft_eligibility(avail,roster,rnd,int(rounds),state["roster_slots"])
                if avail.empty:
                    avail=board[(~board.player.isin(st.session_state.mock_drafted)) & (board.injury_severity<3)].copy()
                avail["_construction_bonus"]=avail.get("_construction_bonus",0)
                avail["need"]=avail.position.map(lambda p: roster_need_for_mock(roster,p,state["roster_slots"]))
                delta=_candidate_roster_delta_df(roster,avail,state["roster_slots"],exact_cap=56)
                cr=avail.market_pick.fillna(overall)
                edge=np.clip(cr-avail.model_rank,-24,24)
                edge=np.where(avail.position.isin(["DL","DB"]),edge*.45,edge)
                nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                avail["evaluation_score"]=(.38*avail.draft_score+3.60*delta+.18*edge)
                avail["evaluation_score"]-=np.where(avail.injury_severity==2,12.0,np.where(avail.injury_severity==1,2.5,0.0))
                local,ready,survive=execution_choice(avail.evaluation_score.to_numpy(float),cr.to_numpy(float),overall,nxt,randomness)
                intercept_local,intercepted,intercept_fall=faller_intercept_choice(
                    avail.evaluation_score.to_numpy(float),cr.to_numpy(float),overall,local,
                    teams=int(teams),rounds=int(rounds)
                )
                avail["survival_next"]=survive
                avail["timing_ready"]=ready
                # Execution score is only for ordering the UI; player evaluation remains visible separately.
                avail["live"]=avail.evaluation_score.copy()
                reach=np.maximum(cr-overall,0)
                avail.loc[~avail.timing_ready,"live"]-=avail.loc[~avail.timing_ready,"survival_next"]*np.minimum(reach[~avail.timing_ready],36)*.42
                if rnd<=7:
                    avail.loc[avail.position.isin(["DL","DB"]),"live"] -= (8-rnd)*2.2
                rc=roster.position.value_counts().to_dict() if len(roster) else {}
                if rc.get("QB",0)>=1:
                    avail.loc[avail.position.eq("QB"),"live"] -= 10 if rnd<=10 else 5
                if rc.get("TE",0)>=1:
                    avail.loc[avail.position.eq("TE"),"live"] -= 8 if rnd<=10 else 3
                avail=avail.sort_values("live",ascending=False)
                nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                avail["evaluation_rank"]=avail.evaluation_score.rank(method="min",ascending=False)
                model_top=avail.sort_values("evaluation_score",ascending=False).head(8).copy()
                now_top=avail[avail.timing_ready].sort_values("evaluation_score",ascending=False).head(8).copy()
                if now_top.empty: now_top=avail.head(8).copy()
                mt=model_top.iloc[0]
                mt_action,mt_surv=market_timing_state(mt.market_pick,overall,nxt,randomness)
                st.info(f"🎯 #1 MODEL TARGET: {mt.player} — {mt_action}")

                if intercepted:
                    intercept_row=avail.iloc[int(intercept_local)]
                    st.success(f"💎 FALLER INTERCEPT: {intercept_row.player} — {intercept_fall:.0f} picks past market")
                    dn=intercept_row
                else:
                    dn=now_top.iloc[0]
                    dn_action,dn_surv=market_timing_state(dn.market_pick,overall,nxt,randomness)
                    st.success(f"✅ DRAFT THIS PICK: {dn.player}" if dn_action!="VALUE FALLER" else f"💎 DRAFT THIS PICK — VALUE FALLER: {dn.player}")
                if nxt:
                    st.caption(f"Current pick #{overall} • next pick #{nxt}. Model target, pick timing and faller intercept are evaluated separately.")
                top=now_top.copy()
                actions=[market_timing_state(mp,overall,nxt,randomness) for mp in top.market_pick]
                top["Action"]=[a[0] for a in actions]
                top["Survives to next pick"]=["—" if pd.isna(a[1]) else f"{a[1]:.0%}" for a in actions]
                top["Market pick"]=top.market_pick.map(lambda v:"—" if pd.isna(v) else int(round(v)))
                st.dataframe(top[["player","position","team","evaluation_rank","Action","Market pick","Survives to next pick","projection","vorp","profile"]],use_container_width=True,hide_index=True)
                pick_options=top.player.tolist()
                if intercepted:
                    intercept_name=avail.iloc[int(intercept_local)].player
                    pick_options=[intercept_name]+[p for p in pick_options if p!=intercept_name]
                choice=st.selectbox("Your mock pick",pick_options)
                if st.button("Draft this player"):
                    row=board[board.player.eq(choice)].iloc[0].to_dict()
                    row["mock_pick"]=overall; row["mock_round"]=rnd
                    st.session_state.mock_user.append(row)
                    st.session_state.mock_drafted.append(choice)
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
            x3.metric("Avg model edge",f"{g['value']:+.1f} spots")
            st.markdown("#### Grade breakdown")
            a,b,c,d=st.columns(4)
            a.metric("Draft Value",f"{g['draft_value']:.0f}/100")
            b.metric("Roster Construction",f"{g['construction']:.0f}/100")
            c.metric("Positional Advantage",f"{g['positional_advantage']:.0f}/100")
            d.metric("Model Edge",f"{g['model_edge_score']:.0f}/100")
            if g.get("opportunity_penalty",0)>0:
                st.caption(f"Opportunity-cost adjustment: -{g['opportunity_penalty']:.1f}")
            if g.get("penalty",0)>0:
                st.warning(f"Roster-construction penalty: -{g['penalty']:.0f} grade points")
            counts=roster.position.value_counts().to_dict()
            st.caption("Roster build: " + " • ".join(f"{p} {counts.get(p,0)}" for p in ["QB","RB","WR","TE","DL","DB"]))
            st.dataframe(roster[["mock_round","mock_pick","player","position","projection","vorp","model_rank","consensus_rank","profile"]],use_container_width=True,hide_index=True)

    else:
        sims=st.slider("Simulations per strategy",10,200,50,10)
        if st.button("▶️ Run benchmark"):
            model_scores=[]; base_scores=[]; model_rosters=[]; base_rosters=[]
            prog=st.progress(0); status=st.empty(); started=time.perf_counter()
            fast=_fast_benchmark_pool(board,int(teams))
            update_every=max(1,min(5,int(sims)//10 or 1))
            max_runtime=30.0
            completed=0
            for i in range(int(sims)):
                if i>0 and (time.perf_counter()-started)>max_runtime:
                    status.warning(f"Safety cutoff reached after {completed} simulation pairs. Results below use completed runs.")
                    break
                mr=simulate_mock_fast(fast,int(teams),int(slot),int(rounds),state["roster_slots"],int(randomness),True,1000+i)
                br=simulate_mock_fast(fast,int(teams),int(slot),int(rounds),state["roster_slots"],int(randomness),False,5000+i)
                mg=grade_mock(mr,int(teams),state["roster_slots"]); bg=grade_mock(br,int(teams),state["roster_slots"])
                model_scores.append(mg["score"]); base_scores.append(bg["score"])
                model_rosters.append(mr); base_rosters.append(br)
                done=i+1; completed=done
                if done==1 or done%update_every==0 or done==int(sims):
                    elapsed=time.perf_counter()-started; eta=(elapsed/done)*(int(sims)-done)
                    prog.progress(done/int(sims))
                    status.caption(f"Completed {done}/{int(sims)} simulation pairs • {elapsed:.1f}s elapsed • ~{eta:.0f}s remaining")
            if completed==int(sims):
                status.caption(f"Completed {completed}/{int(sims)} simulation pairs in {time.perf_counter()-started:.1f}s")
            model_scores=np.array(model_scores); base_scores=np.array(base_scores)
            wins=float((model_scores>base_scores).mean())
            lift=float(model_scores.mean()-base_scores.mean())
            st.markdown("### Benchmark results")
            q1,q2,q3=st.columns(3)
            q1.metric("Fantasy Edge win rate",f"{wins:.0%}")
            q2.metric("Average grade score",f"{model_scores.mean():.1f}",f"{lift:+.1f} vs consensus")
            q3.metric("Consensus baseline",f"{base_scores.mean():.1f}")
            st.caption("A 'win' means Fantasy Edge's simulated roster scored higher on the same grading framework than the consensus-based baseline. This is a preseason strategy test, not proof of future NFL results.")
            result=pd.DataFrame({"Simulation":np.arange(1,int(sims)+1),"Fantasy Edge":model_scores,"Consensus baseline":base_scores})
            st.line_chart(result.set_index("Simulation"))
            # V7 diagnostic layer: explain where the frozen model wins/loses versus consensus.
            diag_rows=[]
            for sim_i,(mr,br,ms,bs) in enumerate(zip(model_rosters,base_rosters,model_scores,base_scores),start=1):
                m=mr.copy(); b=br.copy()
                m["Simulation"]=sim_i; b["Simulation"]=sim_i
                m["strategy"]="Fantasy Edge"; b["strategy"]="Consensus"
                m["sim_grade"]=float(ms); b["sim_grade"]=float(bs)
                diag_rows.extend([m,b])
            diag=pd.concat(diag_rows,ignore_index=True)
            diag["rank_edge"]=pd.to_numeric(diag["consensus_rank"],errors="coerce")-pd.to_numeric(diag["model_rank"],errors="coerce")
            diag["reach_vs_consensus"]=pd.to_numeric(diag["mock_pick"],errors="coerce")-pd.to_numeric(diag["consensus_rank"],errors="coerce")

            st.markdown("### 🔬 V7.24 robustness report")
            st.caption("V7.5 keeps V7.4 positional marginal utility but stress-tests it with availability protection, normalized IDP market timing and confidence-scaled near-tie variation. Projections and grading remain frozen.")

            # Data-integrity checks use stable Sleeper player IDs + canonical positions.
            duplicate_identity=int(board["identity_key"].duplicated().sum()) if "identity_key" in board.columns else 0
            duplicate_name_pos=int(board.duplicated(["key","position"]).sum())
            bad_raw=int((board["position"]!=board["raw_position"].map(canonical_position)).sum())
            di1,di2,di3=st.columns(3)
            di1.metric("Duplicate player identities",duplicate_identity)
            di2.metric("Duplicate name+position rows",duplicate_name_pos)
            di3.metric("Position-source mismatches",bad_raw)
            st.caption("These diagnostics do not change the model. They show where Fantasy Edge differs from the consensus control so we can make the next model change from evidence rather than guesswork.")

            md=diag[diag.strategy.eq("Fantasy Edge")].copy(); bd=diag[diag.strategy.eq("Consensus")].copy()
            pos_order=["QB","RB","WR","TE","DL","DB"]
            mpos=md.position.value_counts().reindex(pos_order,fill_value=0)/float(sims)
            bpos=bd.position.value_counts().reindex(pos_order,fill_value=0)/float(sims)
            pos_report=pd.DataFrame({"Position":pos_order,"Fantasy Edge avg drafted":[mpos[p] for p in pos_order],"Consensus avg drafted":[bpos[p] for p in pos_order]})
            pos_report["Difference"]=pos_report["Fantasy Edge avg drafted"]-pos_report["Consensus avg drafted"]
            st.markdown("#### Average roster construction")
            st.dataframe(pos_report.round(2),use_container_width=True,hide_index=True)

            patterns=(md.groupby("Simulation")["position"].value_counts().unstack(fill_value=0)
                      .reindex(columns=["QB","RB","WR","TE","DL","DB"],fill_value=0))
            unique_patterns=len(patterns.drop_duplicates())
            pattern_share=float(patterns.value_counts(normalize=True).iloc[0]) if len(patterns) else 0.0
            dv1,dv2=st.columns(2)
            dv1.metric("Unique roster constructions",unique_patterns)
            dv2.metric("Most common construction",f"{pattern_share:.0%} of mocks")

            # Round-level comparison: projection/VORP and consensus/model reach characteristics.
            def round_summary(d,prefix):
                g=d.groupby("mock_round").agg(
                    projection=("projection","mean"), vorp=("vorp","mean"),
                    rank_edge=("rank_edge","mean"), reach=("reach_vs_consensus","mean")
                ).reset_index()
                return g.rename(columns={c:f"{prefix}_{c}" for c in ["projection","vorp","rank_edge","reach"]})
            rg=round_summary(md,"FE").merge(round_summary(bd,"Consensus"),on="mock_round",how="outer").sort_values("mock_round")
            rg["VORP_delta"]=rg["FE_vorp"]-rg["Consensus_vorp"]
            rg["Projection_delta"]=rg["FE_projection"]-rg["Consensus_projection"]
            st.markdown("#### Where Fantasy Edge gains/loses by round")
            st.dataframe(rg.round(2),use_container_width=True,hide_index=True)

            # Repeated selections and model disagreement profile.
            pick_freq=(md.groupby(["player","position"]).agg(
                Times_drafted=("Simulation","nunique"), Avg_round=("mock_round","mean"), Avg_pick=("mock_pick","mean"),
                Avg_projection=("projection","mean"), Avg_VORP=("vorp","mean"), Avg_rank_edge=("rank_edge","mean"),
                Consensus_rank=("consensus_rank","mean"), Model_rank=("model_rank","mean")
            ).reset_index())
            pick_freq["Draft_rate"]=pick_freq.Times_drafted/float(sims)
            unique_players=int(md.player.nunique())
            top_concentration=float(pick_freq.Draft_rate.max()) if len(pick_freq) else 0.0
            inj_text=md.get("injury",pd.Series("",index=md.index)).fillna("").astype(str).str.lower()
            severe_injury_rate=float(inj_text.isin(["ir","pup","nfi","reserve/ir","reserve/pup"]).mean())
            out_pick_rate=float(inj_text.isin(["out","suspended","susp"]).mean())
            rv1,rv2,rv3,rv4=st.columns(4)
            rv1.metric("Unique players drafted",unique_players)
            rv2.metric("Top-player concentration",f"{top_concentration:.0%}")
            rv3.metric("IR/PUP/NFI picks",f"{severe_injury_rate:.1%}")
            rv4.metric("OUT/Suspended picks",f"{out_pick_rate:.1%}")

            round_var=(md.groupby("mock_round").agg(
                Unique_players=("player","nunique"),
                Most_common_share=("player",lambda x:x.value_counts(normalize=True).iloc[0])
            ).reset_index())
            round_var["Most_common_share"]=round_var.Most_common_share.map(lambda x:f"{x:.0%}")
            st.markdown("#### Pick variance by round")
            st.dataframe(round_var,use_container_width=True,hide_index=True)

            pos_round=pd.crosstab(md.mock_round,md.position)
            for p in ["QB","RB","WR","TE","DL","DB"]:
                if p not in pos_round.columns: pos_round[p]=0
            st.markdown("#### Position selections by round")
            st.dataframe(pos_round[["QB","RB","WR","TE","DL","DB"]],use_container_width=True)

            st.markdown("#### Most repeated Fantasy Edge selections")
            st.dataframe(pick_freq.sort_values(["Times_drafted","Avg_round"],ascending=[False,True]).head(25).round(2),use_container_width=True,hide_index=True)

            st.markdown("#### Biggest model-vs-consensus disagreements actually drafted")
            disagreements=pick_freq[pick_freq.Times_drafted>=max(2,int(sims*.08))].copy()
            st.dataframe(disagreements.reindex(disagreements.Avg_rank_edge.abs().sort_values(ascending=False).index).head(25).round(2),use_container_width=True,hide_index=True)

            # Structural flags: quantify the exact issues we have been watching.
            flags=[]
            for sim_i,r in md.groupby("Simulation"):
                c=r.position.value_counts()
                flags.append({
                    "Simulation":sim_i,"WR_le_3":int(c.get("WR",0)<=3),"RB_ge_6":int(c.get("RB",0)>=6),
                    "QB2_plus":int(c.get("QB",0)>=2),"TE2_plus":int(c.get("TE",0)>=2),
                    "Missing_DL":int(c.get("DL",0)<int(state["roster_slots"].get("DL",1))),
                    "Early_IDP":int(((r.position.isin(["DL","DB"])) & (r.mock_round<=7)).any()),
                    "grade":float(r.sim_grade.iloc[0])
                })
            flags=pd.DataFrame(flags)
            flag_report=pd.DataFrame({
                "Diagnostic":["3 or fewer WR","6+ RB","2+ QB","2+ TE","Missing required DL","IDP in rounds 1-7"],
                "Fantasy Edge frequency":[flags.WR_le_3.mean(),flags.RB_ge_6.mean(),flags.QB2_plus.mean(),flags.TE2_plus.mean(),flags.Missing_DL.mean(),flags.Early_IDP.mean()]
            })
            st.markdown("#### Roster-construction warning rates")
            st.dataframe(flag_report.assign(**{"Fantasy Edge frequency":flag_report["Fantasy Edge frequency"].map(lambda x:f"{x:.0%}")}),use_container_width=True,hide_index=True)

            # Component-level grading comparison.
            mgrades=pd.DataFrame([grade_mock(r,int(teams),state["roster_slots"]) for r in model_rosters])
            bgrades=pd.DataFrame([grade_mock(r,int(teams),state["roster_slots"]) for r in base_rosters])
            components=["draft_value","construction","positional_advantage","model_edge_score","opportunity_penalty"]
            comp=pd.DataFrame({"Component":components,"Fantasy Edge":[mgrades[c].mean() for c in components],"Consensus":[bgrades[c].mean() for c in components]})
            comp["Difference"]=comp["Fantasy Edge"]-comp["Consensus"]
            st.markdown("#### Grade-component comparison")
            st.dataframe(comp.round(2),use_container_width=True,hide_index=True)

            # Compact diagnosis generated from measured gaps only.
            issues=[]
            if wins<.5: issues.append(f"Fantasy Edge wins only {wins:.0%} of paired simulations")
            if lift<0: issues.append(f"average grade trails consensus by {abs(lift):.1f} points")
            if flags.WR_le_3.mean()>=.35: issues.append(f"WR depth is thin in {flags.WR_le_3.mean():.0%} of Fantasy Edge drafts")
            if flags.RB_ge_6.mean()>=.35: issues.append(f"6+ RB builds occur in {flags.RB_ge_6.mean():.0%} of drafts")
            if flags.QB2_plus.mean()>=.35: issues.append(f"QB2 is drafted in {flags.QB2_plus.mean():.0%} of drafts")
            if flags.TE2_plus.mean()>=.35: issues.append(f"TE2 is drafted in {flags.TE2_plus.mean():.0%} of drafts")
            if flags.Missing_DL.mean()>0: issues.append(f"required DL is missing in {flags.Missing_DL.mean():.0%} of drafts")
            if severe_injury_rate>0: issues.append(f"IR/PUP/NFI players account for {severe_injury_rate:.1%} of selections")
            if pattern_share>=.80: issues.append(f"one roster construction still appears in {pattern_share:.0%} of simulations")
            if top_concentration>=.98: issues.append("at least one player is selected in nearly every simulation")
            worst=comp.sort_values("Difference").iloc[0]
            issues.append(f"largest grading-component deficit is {worst.Component}: {worst.Difference:+.1f}")
            st.markdown("#### Diagnostic summary")
            for issue in issues: st.write("• "+issue)

            csv=diag.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download V7.16 diagnostic CSV",csv,"fantasy_edge_v7_16_diagnostics.csv","text/csv")


        st.markdown("### 🧪 V7.24 10/52 independent validation")
        st.info("This is the clean 10/52 champion-validation build. All non-WR logic remains frozen from the stable model.")
        st.caption("Persistent test workspace: results stay available after Streamlit reruns and do not require rerunning the regular benchmark.")

        if "v724_independent_results" not in st.session_state:
            st.session_state.v724_independent_results=None
        st.caption("Independent test status: " + ("results saved" if isinstance(st.session_state.get("v724_independent_results"),pd.DataFrame) else "ready to run"))
        if "v724_independent_summary" not in st.session_state:
            st.session_state.v724_independent_summary=None

        iv_slots=st.multiselect("Draft slots",[1,3,5,7,9,12],default=[1,3,7,12],key="v724_slots")
        iv_rooms=st.multiselect(
            "Room profiles",
            ["Consensus","ADP-heavy","Chaotic","Positional runs","Sharp/value"],
            default=["Consensus","ADP-heavy","Chaotic","Positional runs","Sharp/value"],
            key="v724_rooms"
        )
        iv_sims=st.number_input("Simulations per slot × room",5,50,10,5,key="v724_sims")

        run_col,clear_col=st.columns(2)
        run_iv=run_col.button("Run independent stress test",type="primary",key="v724_run")
        clear_iv=clear_col.button("Clear independent results",key="v724_clear")

        if clear_iv:
            st.session_state.v724_independent_results=None
            st.session_state.v724_independent_summary=None
            st.rerun()

        if run_iv:
            if not iv_slots or not iv_rooms:
                st.warning("Select at least one draft slot and one room profile.")
            else:
                rows=[]
                total=max(1,len(iv_slots)*len(iv_rooms)*int(iv_sims))
                done=0
                prog=st.progress(0)
                status_iv=st.empty()
                fast_iv=_fast_benchmark_pool(board,int(teams))
                started_iv=time.perf_counter()

                for ds in iv_slots:
                    for room_name in iv_rooms:
                        for j in range(int(iv_sims)):
                            seed=910000+int(ds)*10000+j*31+sum(ord(c) for c in room_name)
                            fe=simulate_mock_fast(
                                fast_iv,int(teams),int(ds),int(rounds),state["roster_slots"],
                                float(randomness),True,seed,room_name
                            )
                            co=simulate_mock_fast(
                                fast_iv,int(teams),int(ds),int(rounds),state["roster_slots"],
                                float(randomness),False,seed,room_name
                            )
                            fc=independent_draft_grade_components(fe,int(teams))
                            cc=independent_draft_grade_components(co,int(teams))
                            fg=fc["overall"]; cg=cc["overall"]
                            row={
                                "Draft_slot":ds,"Room":room_name,"Simulation":j+1,
                                "Fantasy_Edge_grade":fg,"Consensus_grade":cg,"Difference":fg-cg,"Fantasy_Edge_win":fg>cg,
                                "FE_market_value":fc["market_value"],"Consensus_market_value":cc["market_value"],
                                "Market_value_difference":fc["market_value"]-cc["market_value"],
                                "FE_starter_completion":fc["starter_completion"],"Consensus_starter_completion":cc["starter_completion"],
                                "Starter_completion_difference":fc["starter_completion"]-cc["starter_completion"],
                                "FE_roster_balance":fc["roster_balance"],"Consensus_roster_balance":cc["roster_balance"],
                                "Roster_balance_difference":fc["roster_balance"]-cc["roster_balance"],
                                "FE_availability":fc["availability"],"Consensus_availability":cc["availability"],
                                "Availability_difference":fc["availability"]-cc["availability"],
                                "FE_avg_market_delta":fc["avg_market_delta"],"Consensus_avg_market_delta":cc["avg_market_delta"],
                                "FE_avg_reach":fc["avg_reach"],"Consensus_avg_reach":cc["avg_reach"],
                                "FE_avg_faller":fc["avg_faller"],"Consensus_avg_faller":cc["avg_faller"],
                                "FE_big_reaches":fc["big_reaches"],"Consensus_big_reaches":cc["big_reaches"],
                                "FE_missing_starters":fc["missing_starters"],"Consensus_missing_starters":cc["missing_starters"]
                            }

                            # V7.14 diagnostic-only round/phase attribution.
                            early_fe=fe[pd.to_numeric(fe.mock_round,errors="coerce").fillna(99)<=3]
                            row["V724_R1_3_WR_count"]=int((early_fe.position=="WR").sum())
                            row["V724_R1_3_QB_count"]=int((early_fe.position=="QB").sum())
                            row["V724_R1_3_RB_count"]=int((early_fe.position=="RB").sum())
                            wr_early=early_fe[early_fe.position=="WR"]
                            row["V724_R1_3_WR_market_delta"]=float((pd.to_numeric(wr_early.mock_pick,errors="coerce")-pd.to_numeric(wr_early.market_pick,errors="coerce")).mean()) if len(wr_early) else np.nan
                            fep=independent_phase_metrics(fe).set_index("Phase")
                            cop=independent_phase_metrics(co).set_index("Phase")
                            phase_key={"R1-3":"R1_3","R4-6":"R4_6","R7-10":"R7_10","R11+":"R11_plus"}
                            for phase,key in phase_key.items():
                                for metric in ["Avg_market_delta","Avg_reach","Avg_faller","Big_reaches","Avg_model_rank",
                                               "QB","RB","WR","TE","DL","DB"]:
                                    fv=float(fep.loc[phase,metric]) if phase in fep.index and pd.notna(fep.loc[phase,metric]) else np.nan
                                    cv=float(cop.loc[phase,metric]) if phase in cop.index and pd.notna(cop.loc[phase,metric]) else np.nan
                                    row[f"FE_{key}_{metric}"]=fv
                                    row[f"Consensus_{key}_{metric}"]=cv
                                    if metric in ["Avg_market_delta","Avg_reach","Avg_faller","Big_reaches"]:
                                        row[f"{key}_{metric}_difference"]=fv-cv
                            rows.append(row)
                            done+=1
                            prog.progress(done/total)
                            if done==1 or done%10==0 or done==total:
                                status_iv.caption(f"Independent test: {done}/{total} paired simulations")

                iv=pd.DataFrame(rows)
                st.session_state.v724_independent_results=iv
                st.session_state.v724_independent_summary={
                    "tests":len(iv),
                    "seconds":time.perf_counter()-started_iv,
                    "slots":list(iv_slots),
                    "rooms":list(iv_rooms),
                    "sims":int(iv_sims)
                }
                status_iv.success(f"Independent test complete: {len(iv)} paired simulations.")
                prog.empty()

        # Render persisted results OUTSIDE the run-button block.
        iv_saved=st.session_state.get("v724_independent_results")
        if isinstance(iv_saved,pd.DataFrame) and len(iv_saved):
            meta=st.session_state.get("v724_independent_summary") or {}
            st.success(
                f"Saved independent results: {len(iv_saved)} paired tests"
                + (f" • {meta.get('seconds',0):.1f}s" if meta else "")
            )
            a,b,c,d=st.columns(4)
            a.metric("Independent FE win rate",f"{iv_saved.Fantasy_Edge_win.mean():.0%}")
            b.metric("Independent FE grade",f"{iv_saved.Fantasy_Edge_grade.mean():.2f}")
            c.metric("Independent consensus",f"{iv_saved.Consensus_grade.mean():.2f}")
            d.metric("Independent advantage",f"{iv_saved.Difference.mean():+.2f}")

            stress=iv_saved.groupby(["Draft_slot","Room"]).agg(
                FE_grade=("Fantasy_Edge_grade","mean"),
                Consensus_grade=("Consensus_grade","mean"),
                Advantage=("Difference","mean"),
                FE_win_rate=("Fantasy_Edge_win","mean"),
                Tests=("Simulation","count")
            ).reset_index()
            stress["FE_win_rate"]=stress.FE_win_rate.map(lambda x:f"{x:.0%}")
            st.dataframe(stress.round(2),use_container_width=True,hide_index=True)

            st.markdown("#### Why Fantasy Edge wins or loses")
            component_df=pd.DataFrame([
                {"Independent component":"Market value / reach","Average FE advantage":iv_saved.Market_value_difference.mean()},
                {"Independent component":"Starter completion","Average FE advantage":iv_saved.Starter_completion_difference.mean()},
                {"Independent component":"Roster balance","Average FE advantage":iv_saved.Roster_balance_difference.mean()},
                {"Independent component":"Availability","Average FE advantage":iv_saved.Availability_difference.mean()}
            ])
            st.dataframe(component_df.round(2),use_container_width=True,hide_index=True)
            c1,c2,c3,c4=st.columns(4)
            c1.metric("FE avg reach",f"{iv_saved.FE_avg_reach.mean():.1f} picks")
            c2.metric("Consensus avg reach",f"{iv_saved.Consensus_avg_reach.mean():.1f} picks")
            c3.metric("FE avg faller",f"{iv_saved.FE_avg_faller.mean():.1f} picks")
            c4.metric("Consensus avg faller",f"{iv_saved.Consensus_avg_faller.mean():.1f} picks")
            c5,c6=st.columns(2)
            c5.metric("FE big reaches",f"{iv_saved.FE_big_reaches.mean():.1f}/draft")
            c6.metric("Consensus big reaches",f"{iv_saved.Consensus_big_reaches.mean():.1f}/draft")
            faller_gap=float(iv_saved.FE_avg_faller.mean()-iv_saved.Consensus_avg_faller.mean())
            st.caption(f"Faller-capture gap: {faller_gap:+.1f} picks per selection vs consensus. V7.13 specifically targets this gap without relaxing early-round reach discipline.")


            st.markdown("### 🏆 V7.24 10/52 Champion Validation")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("R1-3 WR picks/draft",f"{iv_saved.V724_R1_3_WR_count.mean():.2f}","V7.16: 0.12")
            c2.metric("R1-3 QB picks/draft",f"{iv_saved.V724_R1_3_QB_count.mean():.2f}")
            c3.metric("R1-3 RB picks/draft",f"{iv_saved.V724_R1_3_RB_count.mean():.2f}","V7.16: 1.83")
            c4.metric("Early WR market delta",f"{iv_saved.V724_R1_3_WR_market_delta.mean():+.2f}")
            st.caption("Champion candidate: no WR quota/projection boost. R1-3 intercept requires WR within 10 evaluation points, market priority, and ≤52% survival.")
            st.markdown("### 🧭 V7.14 Round-by-Round Value Attribution")
            phase_rows=[]
            phase_map=[
                ("R1-3","R1_3"),
                ("R4-6","R4_6"),
                ("R7-10","R7_10"),
                ("R11+","R11_plus")
            ]
            for label,key in phase_map:
                phase_rows.append({
                    "Phase":label,
                    "FE market delta":iv_saved[f"FE_{key}_Avg_market_delta"].mean(),
                    "Consensus market delta":iv_saved[f"Consensus_{key}_Avg_market_delta"].mean(),
                    "Market gap":iv_saved[f"{key}_Avg_market_delta_difference"].mean(),
                    "FE reach":iv_saved[f"FE_{key}_Avg_reach"].mean(),
                    "Consensus reach":iv_saved[f"Consensus_{key}_Avg_reach"].mean(),
                    "FE faller":iv_saved[f"FE_{key}_Avg_faller"].mean(),
                    "Consensus faller":iv_saved[f"Consensus_{key}_Avg_faller"].mean(),
                    "FE big reaches":iv_saved[f"FE_{key}_Big_reaches"].mean(),
                    "Consensus big reaches":iv_saved[f"Consensus_{key}_Big_reaches"].mean()
                })
            phase_df=pd.DataFrame(phase_rows)
            st.dataframe(phase_df.round(2),use_container_width=True,hide_index=True)

            # V7.15 reference for the phase this release targets.
            current_r46=phase_df[phase_df["Phase"].eq("R4-6")].iloc[0]
            mr1,mr2,mr3=st.columns(3)
            mr1.metric("R4-6 market gap",f"{current_r46['Market gap']:+.2f}","V7.15 reference: -6.76")
            mr2.metric("R4-6 FE reach",f"{current_r46['FE reach']:.2f}","V7.15 reference: 4.18")
            mr3.metric("R4-6 FE faller",f"{current_r46['FE faller']:.2f}","V7.15 reference: 4.01")

            # Identify the phase responsible for the largest remaining market-value deficit.
            worst_phase=phase_df.sort_values("Market gap").iloc[0]
            best_phase=phase_df.sort_values("Market gap",ascending=False).iloc[0]
            p1,p2,p3,p4=st.columns(4)
            p1.metric("Worst phase",str(worst_phase["Phase"]),f'{worst_phase["Market gap"]:+.2f} market gap')
            p2.metric("Best phase",str(best_phase["Phase"]),f'{best_phase["Market gap"]:+.2f} market gap')
            p3.metric("Worst-phase FE reach",f'{worst_phase["FE reach"]:.1f}')
            p4.metric("Worst-phase FE faller",f'{worst_phase["FE faller"]:.1f}')

            # Position mix by phase helps explain whether a market deficit is linked to position timing.
            pos_rows=[]
            for label,key in phase_map:
                r={"Phase":label}
                for posname in ["QB","RB","WR","TE","DL","DB"]:
                    r[f"FE {posname}"]=iv_saved[f"FE_{key}_{posname}"].mean()
                    r[f"Consensus {posname}"]=iv_saved[f"Consensus_{key}_{posname}"].mean()
                pos_rows.append(r)
            st.markdown("#### Position mix by phase")
            st.dataframe(pd.DataFrame(pos_rows).round(2),use_container_width=True,hide_index=True)

            # Slot × phase matrix isolates where the remaining gap lives.
            slot_phase=[]
            for ds,grp in iv_saved.groupby("Draft_slot"):
                for label,key in phase_map:
                    slot_phase.append({
                        "Draft slot":int(ds),
                        "Phase":label,
                        "Market gap":grp[f"{key}_Avg_market_delta_difference"].mean(),
                        "FE reach":grp[f"FE_{key}_Avg_reach"].mean(),
                        "FE faller":grp[f"FE_{key}_Avg_faller"].mean()
                    })
            st.markdown("#### Slot × phase attribution")
            st.dataframe(pd.DataFrame(slot_phase).round(2),use_container_width=True,hide_index=True)

            r46_row=phase_df[phase_df["Phase"].eq("R4-6")].iloc[0]
            st.info(
                f"V7.16 surgical target — R4-6: market gap {r46_row['Market gap']:+.2f}, "
                f"FE reach {r46_row['FE reach']:.2f}, FE faller {r46_row['FE faller']:.2f}. "
                "R1-3, R7-10 and R11+ are frozen; improvement should come primarily from R4-6."
            )

            by_room=iv_saved.groupby("Room").agg(
                Grade_gap=("Difference","mean"),Market_gap=("Market_value_difference","mean"),
                Starter_gap=("Starter_completion_difference","mean"),Balance_gap=("Roster_balance_difference","mean"),
                Availability_gap=("Availability_difference","mean"),FE_avg_reach=("FE_avg_reach","mean"),
                FE_big_reaches=("FE_big_reaches","mean")).reset_index()
            st.markdown("#### Failure components by room")
            st.dataframe(by_room.round(2),use_container_width=True,hide_index=True)


            room_phase_rows=[]
            for room_name,grp in iv_saved.groupby("Room"):
                for label,key in [("R1-3","R1_3"),("R4-6","R4_6"),("R7-10","R7_10"),("R11+","R11_plus")]:
                    room_phase_rows.append({
                        "Room":room_name,
                        "Phase":label,
                        "Market gap":grp[f"{key}_Avg_market_delta_difference"].mean(),
                        "FE reach":grp[f"FE_{key}_Avg_reach"].mean(),
                        "FE faller":grp[f"FE_{key}_Avg_faller"].mean()
                    })
            st.markdown("#### Room × phase attribution")
            st.dataframe(pd.DataFrame(room_phase_rows).round(2),use_container_width=True,hide_index=True)

            by_slot=iv_saved.groupby("Draft_slot").agg(
                Grade_gap=("Difference","mean"),Market_gap=("Market_value_difference","mean"),
                Starter_gap=("Starter_completion_difference","mean"),Balance_gap=("Roster_balance_difference","mean"),
                Availability_gap=("Availability_difference","mean"),FE_avg_reach=("FE_avg_reach","mean"),
                FE_big_reaches=("FE_big_reaches","mean")).reset_index()
            st.markdown("#### Failure components by draft slot")
            st.dataframe(by_slot.round(2),use_container_width=True,hide_index=True)

            comp_map={"Market value / reach":iv_saved.Market_value_difference.mean(),
                      "Starter completion":iv_saved.Starter_completion_difference.mean(),
                      "Roster balance":iv_saved.Roster_balance_difference.mean(),
                      "Availability":iv_saved.Availability_difference.mean()}
            worst=min(comp_map,key=comp_map.get)
            if comp_map[worst] < -.25:
                st.warning(f"Largest independent drag: {worst} ({comp_map[worst]:+.2f} grade points per draft vs consensus).")
            else:
                st.info("No single independent component explains the gap; inspect room and slot interactions.")

            iv_csv=iv_saved.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download V7.24 10/52 champion validation CSV",
                iv_csv,
                "fantasy_edge_v7_24_10_52_champion_validation.csv",
                "text/csv",
                key="v724_download"
            )
            st.caption("The download remains available through normal Streamlit reruns until you press Clear independent results.")



with tabs[3]:
    st.subheader("Yahoo waiver candidates")
    x=board[~board.player.isin(set(state["taken"]))].sort_values("waiver_score",ascending=False).copy()
    x["Breakout"]=x.breakout.map(lambda v:f"{v:.0%}")
    if len(x):
        x["Suggested FAAB"]=np.clip((x.waiver_score-x.waiver_score.quantile(.35))*.7,1,35)/100*faab
        x["Suggested FAAB"]=x["Suggested FAAB"].round().astype(int)
    st.dataframe(x[["player","position","team","projection","Breakout","injury","Suggested FAAB","waiver_score"]].head(100),
                 use_container_width=True,hide_index=True)

with tabs[4]:
    st.subheader("🛡️ Defensive Lineman & Defensive Back board")
    st.caption("DL emphasizes sacks/pressure plus tackle volume. DB emphasizes tackle floor plus interceptions/pass breakups, while discounting unsustainable big-play spikes.")
    x=board[board.position.isin(["DL","DB"]) & ~board.player.isin(set(state["taken"]))].copy()
    idppos=st.radio("IDP position",["Both","DL","DB"],horizontal=True)
    if idppos!="Both": x=x[x.position.eq(idppos)]
    x["Breakout"]=x.breakout.map(lambda v:f"{v:.0%}")
    x["Regression"]=x.decline.map(lambda v:f"{v:.0%}")
    st.dataframe(x[["player","position","raw_position","team","projection","vorp","Breakout","Regression","injury","draft_score"]].head(80),
                 use_container_width=True,hide_index=True)

with tabs[5]:
    a,b=st.columns(2)
    with a:
        st.subheader("🚀 Breakout")
        x=board.sort_values("breakout",ascending=False).head(35).copy(); x["Probability"]=x.breakout.map(lambda v:f"{v:.0%}")
        st.dataframe(x[["player","position","team","Probability","projection","progression"]],use_container_width=True,hide_index=True)
    with b:
        st.subheader("📉 Regression")
        x=board.sort_values("decline",ascending=False).head(35).copy(); x["Probability"]=x.decline.map(lambda v:f"{v:.0%}")
        st.dataframe(x[["player","position","team","Probability","projection","regression"]],use_container_width=True,hide_index=True)

with tabs[6]:
    x=board[board.player.isin(state["my_team"])].copy()
    if x.empty: st.info("Add your Yahoo roster under League Setup.")
    else:
        x["Breakout"]=x.breakout.map(lambda v:f"{v:.0%}"); x["Regression"]=x.decline.map(lambda v:f"{v:.0%}")
        st.dataframe(x[["player","position","team","projection","Breakout","Regression","injury"]],
                     use_container_width=True,hide_index=True)

with tabs[7]:
    name=st.selectbox("Player",all_names)
    p=board[board.player.eq(name)].iloc[0]
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

if market.empty and "market_error" in st.session_state:
    st.warning("Current consensus rankings did not load, so the app is temporarily using the statistical model without the consensus reality-check layer.")
