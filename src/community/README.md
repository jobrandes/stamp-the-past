# Community places (test branch)

Current model (Jo-Anne, Nov 5 2026): every community place is an **Explore History Story stop**. Missions are promoted only by Jo-Anne.

- `stories/<submission id>.json` is the published place: `{"sub","town","state","added","by"?,"stop":{...Story-stop schema...}}`. Photo keys `cm_<sub>_<n|t|x1..x5>`; bytes live in the test deploy's storage. Rules for writing one: `docs/community-agent.md`.
- `rules.json` are the approval rules (shown on /contribute/admin/). `approvals.json` is the decision log, one record per submission (added, declined, needs-owner, waiting, removed). `tools/community.py check` enforces both.
- `held/<id>.json`: a place taken out of the app that waits for Jo-Anne's decision. Never built, never published.
- `declined.json` `{id: reason}`, `declined-photos.json` (photo suffixes held back), `waiting.json` (needs a photo), `merged.json` (add-photo and correction submissions already handled).
- `places/<id>.json` is the OLD mission-pack path. It is not used for new places. A file there is refused by `check` unless it carries `"promoted_by": "Jo-Anne"` and `"promoted_on"`.
- Photos are public only when the built `status.json` lists them in `photos` (every photo that is part of a published place) and their place is in `added`.
- `tools/community.py build` writes `site/community/places.json`, `status.json` and `report.json`.
- Optional `by`: the contributor's nickname (1-30 plain characters). Never an email or name.
