# Python training tracker

This repository is a 30-day Python learning board for six people. The agenda,
status database, issue automation, and GitHub Pages dashboard are intentionally
small and dependency-free so the team can maintain them directly in GitHub.

## How it works

1. The 30-day plan and every learner's status live in
   [`data/training.csv`](data/training.csv).
2. A comment on the shared training issue is parsed by
   [`scripts/update_status.py`](scripts/update_status.py).
3. A valid comment updates the matching CSV row, commits the change, and pushes
   it to `main`.
4. The Pages workflow rebuilds the static dashboard from that commit. The
   browser loads the CSV and renders the agenda and progress cards.

The six learner columns are `Vasudha`, `Lakhsmi`, `Pragna`, `Navya`, `Sreenu`,
and `Uday`. The parser and dashboard discover learner columns automatically as
every column after the six agenda columns.

## Issue comment syntax

Use an exact topic name from the CSV or a day number, then one or more
`person-status` updates separated by commas:

```text
Day 1, Vasudha-inprogress, Lakhsmi-done
JSON and CSV data, Pragna-blocked
```

Learner names are case-insensitive. The display names above are recommended;
positional aliases such as `person1` and `p1` remain supported, so `p1` still
resolves to `Vasudha`. The supported statuses and common aliases are:

| Canonical status | Accepted examples |
| --- | --- |
| `not-started` | `notstarted`, `todo`, `pending` |
| `in-progress` | `inprogress`, `doing`, `active` |
| `done` | `complete`, `completed`, `finished` |
| `blocked` | `blocked` |

Comments that do not contain a status assignment are ignored. A malformed
status command fails the workflow instead of silently changing the wrong row.
The latest valid comment wins for each learner and topic.

## GitHub setup

1. Push this repository to GitHub with the default branch named `main`.
2. In **Settings → Pages**, choose **GitHub Actions** as the source.
3. Create an issue using the **Training status board** template.
4. Comment on that issue using the syntax above.

The two workflows are:

- [`update-training-status.yml`](.github/workflows/update-training-status.yml)
  listens for created and edited issue comments, ignores pull-request
  comments, commits only `data/training.csv`, and explicitly dispatches the
  Pages deployment after a status change. The explicit dispatch is required
  because GitHub does not start a second `push` workflow for commits made with
  `GITHUB_TOKEN`.
- [`pages.yml`](.github/workflows/pages.yml) deploys the root static site to
  GitHub Pages whenever `main` changes.

The workflow's `GITHUB_TOKEN` needs the repository's default Actions setting to
allow write access so it can push the CSV commit. If the repository belongs to
an organization with restricted Actions permissions, enable
**Read and write permissions** for Actions in **Settings → Actions →
General**.

## Local development

The dashboard is plain HTML, CSS, and JavaScript. Serve the repository root
over HTTP so the browser can fetch the CSV:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000>.

Run the status parser locally with:

```bash
python scripts/update_status.py \
  --comment "Day 1, Vasudha-inprogress, Lakhsmi-done"
```

The test suite uses only Python's standard library:

```bash
python -m unittest discover -s tests
```

## Changing the agenda

Keep the six agenda columns in this order:

`day`, `topic`, `focus`, `how_to_cover`, `practice`, `resource`

Add or edit learner columns after them. Topic comments match exact normalized
topic text or `Day N`, so changing a topic name also changes the text that
should be used in future comments.
