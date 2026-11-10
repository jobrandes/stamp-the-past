# Community live (Nov 10 2026)

Jo-Anne's decision, Nov 10 2026: merge the community project into `main` and switch it on for stampthepast.com (website only). Own-photo uploads allowed. Likes on community photos only.

## What is live
- `/contribute/`, community places in Explore History, likes and contributor kudos work on stampthepast.com. The native app has none of it (`COMON` is false inside Capacitor).
- Older notes that say "test branch only", "never merge" or "404 on production" are history.
- Every place and photo is still held until approved (rules in `src/community/rules.json`, daily run in `docs/community-agent.md`).

## Backend
- `netlify/functions/community.mjs` answers on production. Production uses the SAME blob store the test used (`community-branch-deploy`), so the published places, their photos and old status links carried over. Deploy previews and local dev keep their own stores.
- Netlify env vars `COMMUNITY_ADMIN_KEY` and `COMMUNITY_UPLOADS=1` must exist for the production context.
- The daily run reads `https://stampthepast.com/api/community/...` and pushes to `main`, touching only `src/community/` and the rebuilt site files.

## Likes (community photos only)
- `POST /api/community/like/<id>_<t|n|x1..x5>` with body `{on:true|false}`; `GET /api/community/likes` returns every count.
- Only a count per photo is stored (blob `like/<id>`). No liker id. One like per photo per device (localStorage `stp-liked`). Published photos only.
- No accounts, so a determined person can inflate a count; the function rate limit (60 a minute per IP) is the only brake.
- App: heart button under the gallery on a community Story card (`likeBtn`, `likeTap`, `likesLoad`, `likePaint` in `src/app.js`). Anonymous event `photo-like`.

## Contributor kudos
- Per device, from the private status links in `stp-sugg`. `ctSync()` asks `/api/community/mine/<token>` for each and stores totals in `stp-contrib` {a places added, p own photos published, l likes, f towns founded, w in review, nw new likes since last visit}.
- Home "Your contributions" card (`contribCardHtml`): places in the app, own photos published, likes, "+N new likes since your last visit", in review, with "See your place" and "Add another place".
- A toast when a suggested place is newly added. 100 XP per added place.
- Six contributor badges, website only (46 badges on the website, 40 in the native app): Local Historian (1 place added), Town Crier (5), Town Founder (first place in a town), Photo Credit (own photo published), Crowd Favorite (10 likes), Hall of Frame (50 likes).
- `tools/community.py` marks the first place added in each community town `founder`; its card says "First community place in <town>" and names the contributor's nickname if there is one.
- Home "From the community" card (`comCardHtml`): newest community place, who added it, its likes, and "Add a place".

## Other changes
- The reported-and-hidden list no longer blocks page load: the app reads `stp-hid`, and `hidSync()` refreshes it after load (one reload if a place on screen was just hidden).
- `tests/community.py`: admin tests use a fixture that puts Liberty Island back to needs-owner in the TEMP copy only (the real record is `added`). Production-context tests now expect the backend to work.
- `tests/flows.py` expects 46 badges.

## Still open
- DMCA designated agent (Jo-Anne). No automatic image scanning.
- Nicknames are not verified, so there is no public leaderboard by nickname.
- `/contribute/` is still noindex.
- Likes and kudos are not in the native app.
- CLAUDE.md has not been updated with this section (Claude was not allowed to edit it in the Nov 10 session); this file is the record until it is.
