"""
Codeforces API client utilities.

This module talks to the public Codeforces API and exposes a small,
well-typed surface for the Streamlit frontend (app.py) to build on:

    - get_solved_problems(handle)   -> all problems a handle has solved
    - fetch_problem_statistics()    -> global accepted-solve count per problem

Both are wrapped with st.cache_data so repeated lookups (e.g. re-running
the comparison, or two handles sharing a session) don't re-hit the API
more than necessary.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests
import streamlit as st

USER_STATUS_URL = "https://codeforces.com/api/user.status"
PROBLEMSET_URL = "https://codeforces.com/api/problemset.problems"
PAGE_SIZE = 10_000

ProblemKey = tuple[Any, Any, str]  # (contestId, index, name)


class CodeforcesAPIError(Exception):
    """Raised when the Codeforces API returns an error or a bad response."""


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise CodeforcesAPIError(f"Network error while calling Codeforces: {error}") from error
    except ValueError as error:
        raise CodeforcesAPIError("Codeforces returned an invalid JSON response.") from error

    if data.get("status") != "OK":
        message = data.get("comment", "Unknown Codeforces API error")
        # Codeforces uses this phrase for handles that don't exist.
        if "not found" in message.lower():
            raise CodeforcesAPIError(f"Handle not found on Codeforces: {message}")
        raise CodeforcesAPIError(message)

    return data


def _fetch_all_submissions(handle: str) -> list[dict[str, Any]]:
    """Fetch every submission ever made by a Codeforces user (paginated)."""

    submissions: list[dict[str, Any]] = []
    start = 1

    while True:
        data = _get_json(
            USER_STATUS_URL,
            {"handle": handle, "from": start, "count": PAGE_SIZE},
        )

        current_page = data["result"]
        submissions.extend(current_page)

        if len(current_page) < PAGE_SIZE:
            break

        start += PAGE_SIZE
        time.sleep(0.5)  # be polite to the CF API between pages

    return submissions


def get_problem_key(problem: dict[str, Any]) -> ProblemKey:
    """
    Identify a problem. contestId + index is the real identity;
    name is kept as a tie-breaking fallback for the rare problem
    that lacks a contestId (e.g. some gym/April Fools problems).
    """
    return (
        problem.get("contestId"),
        problem.get("index"),
        problem.get("name", "Unknown problem"),
    )


def format_solved_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%d-%m-%Y %I:%M %p")


def problem_key_to_str(key: ProblemKey) -> str:
    """
    Turn a (contestId, index, name) ProblemKey into a stable string,
    safe to use as a JSON object key (e.g. for the journal store).
    """
    contest_id, index, name = key
    return f"{contest_id}|{index}|{name}"


@st.cache_data(ttl=300, show_spinner=False)
def get_solved_problems(handle: str) -> dict[ProblemKey, dict[str, Any]]:
    """
    Return every problem a handle has solved (verdict == OK), deduplicated,
    keyed by (contestId, index, name). The earliest accepted submission is
    kept as that problem's solve date/time.
    """

    submissions = _fetch_all_submissions(handle)

    solved: dict[ProblemKey, dict[str, Any]] = {}

    for submission in submissions:
        if submission.get("verdict") != "OK":
            continue

        problem = submission.get("problem", {})
        problem_key = get_problem_key(problem)
        solved_timestamp = submission.get("creationTimeSeconds")

        if solved_timestamp is None:
            continue

        contest_id = problem.get("contestId")
        index = problem.get("index")
        name = problem.get("name", "Unknown problem")
        submission_id = submission.get("id")

        if contest_id is not None and index is not None:
            url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
        else:
            url = ""

        if contest_id is not None and submission_id is not None:
            solution_url = f"https://codeforces.com/contest/{contest_id}/submission/{submission_id}"
        else:
            solution_url = ""

        info = {
            "rating": problem.get("rating"),
            "contest_id": contest_id,
            "index": index,
            "name": name,
            "tags": problem.get("tags", []),
            "solved_timestamp": solved_timestamp,
            "solved_date": format_solved_date(solved_timestamp),
            "url": url,
            "submission_id": submission_id,
            "solution_url": solution_url,
        }

        if problem_key not in solved or solved_timestamp < solved[problem_key]["solved_timestamp"]:
            solved[problem_key] = info

    return solved


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_problem_statistics() -> dict[tuple[Any, str], int]:
    """
    Fetch how many people have solved each problem on Codeforces
    (globally, across every user). Returns {(contestId, index): solvedCount}.
    """

    data = _get_json(PROBLEMSET_URL, {})
    stats = data["result"]["problemStatistics"]

    solve_counts: dict[tuple[Any, str], int] = {}
    for entry in stats:
        key = (entry.get("contestId"), entry.get("index"))
        solve_counts[key] = entry.get("solvedCount", 0)

    return solve_counts