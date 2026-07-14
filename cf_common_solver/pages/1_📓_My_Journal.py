"""
My Journal — a personal revision log of solved Codeforces problems.

Shows every problem solved by a fixed handle (ramortizedsoul), with a
link to the problem and a link to the actual accepted solution, plus
an editable star rating (difficulty, out of 5) and a free-text review
so you can revise your own solved problems later.

No login needed — this is a single-user page. Ratings/reviews are
saved locally to journal_data.json via journal_store.py.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from cf_api import CodeforcesAPIError, get_solved_problems, problem_key_to_str
from journal_store import get_entry, load_journal, save_journal

HANDLE = "ramortizedsoul"

st.set_page_config(page_title="My Journal", page_icon="📓", layout="wide")

st.title(f"📓 {HANDLE}'s Problem Journal")
st.caption(
    "Every problem you've solved, with a link to your accepted solution. "
    "Rate the difficulty and jot a review so you can come back and revise later."
)

# --- Fetch solved problems -------------------------------------------------
with st.spinner(f"Fetching solved problems for {HANDLE}…"):
    try:
        solved = get_solved_problems(HANDLE)
    except CodeforcesAPIError as error:
        st.error(f"Couldn't fetch problems for **{HANDLE}**: {error}")
        st.stop()

if not solved:
    st.info("No solved problems found yet.")
    st.stop()

journal = load_journal()

# --- Build the working dataframe -------------------------------------------
rows = []
for key, info in solved.items():
    key_str = problem_key_to_str(key)
    entry = get_entry(journal, key_str)
    contest_id, index, name = key
    rows.append(
        {
            "_key": key_str,
            "problem": f"{contest_id}{index}" if contest_id is not None else (index or "?"),
            "name": name,
            "rating": info["rating"] if info["rating"] is not None else 0,
            "tags": ", ".join(info["tags"]),
            "problem_link": info["url"] or None,
            "solution_link": info["solution_url"] or None,
            "solved_on": info["solved_date"],
            "stars": entry["stars"],
            "review": entry["review"],
        }
    )

full_df = pd.DataFrame(rows)

# --- Filters -----------------------------------------------------------
with st.sidebar:
    st.header("Filters")

    search = st.text_input("Search by name or problem id", "")

    rated_df = full_df[full_df["rating"] > 0]
    if not rated_df.empty:
        min_r, max_r = int(rated_df["rating"].min()), int(rated_df["rating"].max())
        rating_range = st.slider("Rating range", min_r, max_r, (min_r, max_r), step=100)
    else:
        rating_range = None

    all_tags = sorted({t.strip() for tags in full_df["tags"] for t in tags.split(",") if t.strip()})
    tag_filter = st.multiselect("Tags", all_tags)

    only_unreviewed = st.checkbox("Only unreviewed (no stars, no review)", value=False)

    sort_by = st.selectbox(
        "Sort by",
        ["Solved date (newest first)", "Solved date (oldest first)", "Rating (low to high)", "Rating (high to low)", "Stars (low to high)", "Stars (high to low)"],
    )

df = full_df.copy()

if search:
    mask = df["name"].str.contains(search, case=False, na=False) | df["problem"].str.contains(search, case=False, na=False)
    df = df[mask]

if rating_range is not None:
    df = df[(df["rating"] == 0) | ((df["rating"] >= rating_range[0]) & (df["rating"] <= rating_range[1]))]

if tag_filter:
    df = df[df["tags"].apply(lambda t: any(tag in [x.strip() for x in t.split(",")] for tag in tag_filter))]

if only_unreviewed:
    df = df[(df["stars"] == 0) & (df["review"].str.strip() == "")]

sort_map = {
    "Solved date (newest first)": ("solved_on", False),
    "Solved date (oldest first)": ("solved_on", True),
    "Rating (low to high)": ("rating", True),
    "Rating (high to low)": ("rating", False),
    "Stars (low to high)": ("stars", True),
    "Stars (high to low)": ("stars", False),
}
sort_col, sort_asc = sort_map[sort_by]
df = df.sort_values(by=sort_col, ascending=sort_asc)

# --- Summary metrics ---------------------------------------------------
total = len(full_df)
reviewed = len(full_df[(full_df["stars"] > 0) | (full_df["review"].str.strip() != "")])
avg_stars = full_df.loc[full_df["stars"] > 0, "stars"].mean()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total solved", total)
m2.metric("Reviewed", reviewed)
m3.metric("Avg. difficulty (rated)", f"{avg_stars:.1f} ★" if pd.notna(avg_stars) else "—")
m4.metric("Showing", len(df))

st.divider()

if df.empty:
    st.warning("No problems match the current filters.")
    st.stop()

# --- Editable journal table --------------------------------------------
st.caption("Edit **Stars** and **Review** directly in the table below, then click **Save changes**.")

edited_df = st.data_editor(
    df,
    key="journal_editor",
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_order=[
        "problem",
        "name",
        "rating",
        "tags",
        "problem_link",
        "solution_link",
        "solved_on",
        "stars",
        "review",
    ],
    column_config={
        "problem": st.column_config.TextColumn("Problem", disabled=True),
        "name": st.column_config.TextColumn("Name", width="medium", disabled=True),
        "rating": st.column_config.NumberColumn("Rating", disabled=True, help="0 = unrated problem"),
        "tags": st.column_config.TextColumn("Tags", width="large", disabled=True),
        "problem_link": st.column_config.LinkColumn("Problem", display_text="Open ↗", disabled=True),
        "solution_link": st.column_config.LinkColumn("My Solution", display_text="View ↗", disabled=True),
        "solved_on": st.column_config.TextColumn("Solved on", disabled=True),
        "stars": st.column_config.SelectboxColumn(
            "Difficulty ★", options=[0, 1, 2, 3, 4, 5], help="Your own difficulty rating, 0 = not rated yet"
        ),
        "review": st.column_config.TextColumn("Review / notes", width="large"),
    },
)

if st.button("💾 Save changes", use_container_width=True, type="primary"):
    for _, row in edited_df.iterrows():
        journal[row["_key"]] = {"stars": int(row["stars"]), "review": row["review"] or ""}
    save_journal(journal)
    st.success(f"Saved {len(edited_df)} entries.")
    st.rerun()
