# Community places (test branch)

One file per researched place: `places/<submission id>.json`.

```json
{"sub":"ab12cd34","town":"Mill Valley","state":"CA","added":"2026-11-03","stop":{ ...a normal pack stop... }}
```

`stop` uses the same schema as `src/packs/*.json` stops (id, name, short, badge, teaser, map, geo, clue, safety, field, q, then, now, story, fact, disputed, claims[2], sources[2+], card), plus the rules in `docs/community-agent.md`. Photo keys are `cm_<sub>_t` and `cm_<sub>_n`; the bytes live in the test deploy's storage and are served from `/api/community/photo/<sub>_t|n`.

`declined.json`: `{"<sub id>": "plain-language reason"}` for submissions that cannot be added.

`tools/community.py` groups places by town into packs at build time (`site/community/places.json`) and writes `site/community/status.json`.

`seq`: 1, 2, 3 ... per town (town + state), never reused and never changed. New places in a town get the next number, so a player's saved stamps never shift to another place.
