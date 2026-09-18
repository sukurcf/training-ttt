---
name: Training status board
about: Create the issue that receives daily learner status updates
title: "[Training] Status board"
labels: training
assignees: ""
---

Use this issue as the shared training status board. Comment with an exact topic
or `Day N`, followed by one or more learner updates:

```text
Day 1, Vasudha-inprogress, Lakshmi-done
```

Accepted statuses:

- `not-started`
- `in-progress`
- `done`
- `blocked`

The automation accepts `person1` / `p1`, positional aliases for each learner,
and the display names in `data/training.csv`. It updates the CSV and GitHub
Pages dashboard after a valid comment.
