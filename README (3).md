# CF Common Solved Problems Finder

A Streamlit app that finds every Codeforces problem solved by **1 to 3**
handles, groups the results by problem rating, and shows each problem's
global accepted-solve count (how many people worldwide have solved it),
alongside when each handle solved it themselves.

This is a rebuild of the original CLI script (`compare_handles`), turned
into a proper two-person→N-person web app with:

- Support for 1, 2, or 3 handles (intersection of solved sets)
- Global solve-count per problem, pulled from `problemset.problems`
- Rating-wise grouping with sortable, filterable tables (via `st.dataframe`)
- Per-handle "solved on" dates shown side by side
- CSV export
- Response caching (30 min) so re-running or comparing overlapping
  handles doesn't hammer the Codeforces API

## Project layout

```
cf_common_solver/
├── app.py          # Streamlit UI + result assembly
├── cf_api.py        # Codeforces API client (fetch submissions, problem stats)
├── requirements.txt
└── README.md
```

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Notes

- If a handle doesn't exist or has submissions disabled/hidden, the app
  shows an error for that handle but still proceeds with the others.
- "Unrated" problems (no rating set by Codeforces) are grouped last.
- Global solve counts come from Codeforces' own `problemStatistics`
  endpoint, refreshed at most once every 30 minutes per session.
