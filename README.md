
# Fantasy Edge

A Streamlit fantasy-football dashboard for:

- Draft rankings
- Breakout/progression candidates
- Regression/fade candidates
- Waiver-wire ranking and suggested FAAB
- Weekly start/sit rankings
- Player-level model explanations

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

The included data is synthetic demo data so the app works immediately.

## Real data architecture

Recommended:
- nflverse / nflreadpy for historical and weekly NFL data.
- Sleeper API for league settings, rosters and drafts.
- Optional injury/news and market inputs.

### Modeling roadmap

**Preseason / season-long**
Train rolling-season models with features such as:
age, experience, draft capital, prior-year touches/targets, route participation,
target share, rush share, red-zone share, yards per route run, explosive play rate,
team pass/rush tendencies, offensive line/team environment, and ADP.

**Weekly**
Use expanding-window training and features that were known before kickoff:
last 1/3/5 week usage, snap/route share, target/carry share, red-zone usage,
opponent defensive tendencies, game total/spread, injury/depth-chart changes.

Use walk-forward validation. Never train a week using information from that same
week's result.
