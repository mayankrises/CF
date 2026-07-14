"""
Codeforces Common Solved Problems Finder — Streamlit app.

Enter 1-3 Codeforces handles. The app finds every problem solved by
ALL of the entered handles, groups them by rating, and shows each
problem's global accepted-solve count alongside when each handle
solved it.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from cf_api import CodeforcesAPIError, fetch_problem_statistics, get_solved_problems

st.set_page_config(
    page_title="CF Common Solved Problems",
    page_icon="🧩",
    layout="wide",
)

st.title("🧩 Codeforces — Common Solved Problems Finder")
st.caption(
    "Enter 1 to 3 Codeforces handles. Get the problems solved by **all** of them, "
    "grouped rating-wise, along with each problem's global accepted-solve count."
)

with st.form("handles_form"):
    col1, col2, col3 = st.columns(3)
    handle1 = col1.text_input("Handle 1 (required)", placeholder="tourist")
    handle2 = col2.text_input("Handle 2 (optional)", placeholder="Benq")
    handle3 = col3.text_input("Handle 3 (optional)", placeholder="Um_nik")
    exclude_handle = st.text_input(
        "Exclude handle (optional)",
        placeholder="e.g. jiangly",
        help="Any problem this handle has already solved will be removed from the results below.",
    ).strip()
    submitted = st.form_submit_button("Find common problems", use_container_width=True)

if not submitted:
    st.info("Enter at least one handle above and click **Find common problems** to begin.")
    st.stop()

handles = [h.strip() for h in (handle1, handle2, handle3) if h and h.strip()]
handles = list(dict.fromkeys(handles))  # de-dup, keep order

if not handles:
    st.error("Please enter at least one Codeforces handle.")
    st.stop()

solved_by_handle: dict[str, dict] = {}
errors: list[str] = []

progress = st.progress(0.0, text="Starting…")
for i, handle in enumerate(handles):
    progress.progress(i / (len(handles) + 1), text=f"Fetching submissions for {handle}…")
    try:
        solved_by_handle[handle] = get_solved_problems(handle)
    except CodeforcesAPIError as error:
        errors.append(f"**{handle}**: {error}")

excluded_solved: dict = {}
if exclude_handle and exclude_handle.lower() not in [h.lower() for h in handles]:
    progress.progress(
        len(handles) / (len(handles) + 2), text=f"Fetching submissions for {exclude_handle} (to exclude)…"
    )
    try:
        excluded_solved = get_solved_problems(exclude_handle)
    except CodeforcesAPIError as error:
        errors.append(f"**{exclude_handle}** (exclude): {error}")

progress.progress(
    (len(handles) + 1) / (len(handles) + 2) if exclude_handle else len(handles) / (len(handles) + 1),
    text="Fetching global problem statistics…",
)
try:
    solve_counts = fetch_problem_statistics()
except CodeforcesAPIError as error:
    solve_counts = {}
    errors.append(f"**Global stats**: {error}")

progress.progress(1.0, text="Done")
progress.empty()

for err in errors:
    st.error(err)

valid_handles = [h for h in handles if h in solved_by_handle]
if not valid_handles:
    st.stop()

# --- Summary metrics -------------------------------------------------
metric_cols = st.columns(len(valid_handles))
for col, h in zip(metric_cols, valid_handles):
    col.metric(h, f"{len(solved_by_handle[h])} solved")

# --- Intersection ------------------------------------------------------
key_sets = [set(solved_by_handle[h].keys()) for h in valid_handles]
common_keys = set.intersection(*key_sets)

if len(valid_handles) == 1:
    st.info("Only one valid handle entered — showing every problem they've solved.")
else:
    st.subheader(f"✅ {len(common_keys)} problem(s) solved by all {len(valid_handles)} handles")

# --- Declude: drop anything the exclude handle has already solved ----------
if excluded_solved:
    before_count = len(common_keys)
    common_keys = common_keys - set(excluded_solved.keys())
    removed_count = before_count - len(common_keys)
    st.caption(
        f"🚫 Removed {removed_count} problem(s) already solved by **{exclude_handle}** "
        f"— {len(common_keys)} remaining."
    )

if not common_keys:
    st.warning("No common problems found between the given handles.")
    st.stop()

# --- Build result table -------------------------------------------------
rows = []
for key in common_keys:
    base = solved_by_handle[valid_handles[0]][key]
    contest_id, index, name = key
    global_solves = solve_counts.get((contest_id, index))

    row = {
        "rating": base["rating"] if base["rating"] is not None else "Unrated",
        "problem": f"{contest_id}{index}" if contest_id is not None else (index or "?"),
        "name": name,
        "tags": ", ".join(base["tags"]),
        "global_solves": global_solves if global_solves is not None else -1,
        "url": base["url"] or None,
    }
    for h in valid_handles:
        row[f"{h} solved on"] = solved_by_handle[h][key]["solved_date"]

    rows.append(row)

df = pd.DataFrame(rows)


def _rating_sort_key(rating):
    return (rating == "Unrated", rating if rating != "Unrated" else float("inf"))


df["_rating_sort"] = df["rating"].apply(_rating_sort_key)
df = df.sort_values(
    by=["_rating_sort", "global_solves"],
    ascending=[True, False],
).drop(columns=["_rating_sort"])
df["global_solves"] = df["global_solves"].replace(-1, pd.NA)

# --- Download ------------------------------------------------------------
csv_df = df.drop(columns=["url"]).rename(columns={"global_solves": "global_solves_(accepted_count)"})
csv_bytes = csv_df.to_csv(index=False).encode("utf-8-sig")
csv_filename = "_".join(valid_handles) + "_common_solved"
if excluded_solved:
    csv_filename += f"_not_{exclude_handle}"
csv_filename += ".csv"

st.download_button(
    "⬇️ Download as CSV",
    data=csv_bytes,
    file_name=csv_filename,
    mime="text/csv",
    use_container_width=True,
)

# --- Display, rating-wise --------------------------------------------------
date_columns = [f"{h} solved on" for h in valid_handles]
column_order = ["problem", "name", "tags", "global_solves", "url"] + date_columns

for rating in df["rating"].unique():
    rating_df = df[df["rating"] == rating].drop(columns=["rating"])[column_order]
    with st.expander(f"Rating {rating} — {len(rating_df)} problem(s)", expanded=True):
        st.dataframe(
            rating_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "problem": st.column_config.TextColumn("Problem"),
                "name": st.column_config.TextColumn("Name", width="medium"),
                "tags": st.column_config.TextColumn("Tags", width="large"),
                "global_solves": st.column_config.NumberColumn(
                    "Global Solves", help="How many people have solved this, across all of Codeforces"
                ),
                "url": st.column_config.LinkColumn("Link", display_text="Open ↗"),
                **{
                    col: st.column_config.TextColumn(col.replace(" solved on", "'s solve date"))
                    for col in date_columns
                },
            },
        )