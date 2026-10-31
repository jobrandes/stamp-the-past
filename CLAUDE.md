# Stamp the Past: project brief for Claude

Read this first in every session. Keep it current: update it whenever scope, rules, status or the roadmap change.

## What this is
**Stamp the Past** is a phone-first history scavenger-hunt app about real landmarks. Tagline: "Go there. Prove it. Stamp the past."
Built by Jo-Anne (builder, on-site verifier) and her 14-year-old son (tester and idea source). Public credit: "made by a mom and her teenage son". Never name the son publicly.

- Repo: `jobrandes/missions-app` (private). Live site: `stampthepast.com` (Porkbun domain bought Oct 25, DNS A record to Netlify, www CNAME; Porkbun auto-renew is OFF, expires 2027-10-25, so set a reminder). Test site `stamp-the-past.netlify.app` still works. Auto-deploys on push to GitHub.
- Claude Artifact copy: https://claude.ai/artifact/4jha39rpChXp1cMVXRYkBs (republish after every build; the page must stay under 16 MB).
- The App Store is the eventual destination. Netlify is only for testing.

## Goals (apply to every decision)
1. Fun to build together. "We made this."
2. Unique, not a copy of an existing app. Not a Strava-style "Local Legend" feature (explicitly rejected).
3. Aim for a top App Store ranking. Eventually earns money.
4. Funny, confident tone. Sarcasm and humor welcome.
5. Go global months after the MVP (France, Mexico, Italy, etc.), so nothing may be tied to one town or an English idiom.

## Hard rules
- No weapons or tactical guidance. No surveillance. No precise location data from kids. No accounts or uploads in the MVP. GPS is allowed ONLY as the optional, on-device 'verified visit' check (never sent anywhere, never required).
- Caden does not manage payments or accounts, and does not publish personal info.
- Jo-Anne verifies on site. Content is "written from sources, not yet checked on site" until she walks it.
- Photos: real, freely licensed photos only (Wikimedia Commons, Library of Congress, public domain). Credit every photo in `CREDITS.md` and in the stop's `ph` block. If no free photo exists, show an honest "photo pending". **Do not go live with missing photos** (her requirement, Oct 19). Never email archives or ask permission-by-email.
- In-phone missions only, not printable.
- Naming: no teen slang, no mashed-up made-up words. Domain not purchased yet. No lawyer. Claude checks App Store, domains and trademarks itself.
- Protect her Claude usage. Connect to GitHub, Netlify and Google instead of doing things by hand. Check quality and mobile and desktop responsiveness every time. She is not a developer but knows quality engineering.
- Verify facts from fetched sources, never memory. When a source disagrees with a popular claim, use the source and mark the claim "disputed" or "not true".

## How the code works
- `build.py` builds `index.html` (the Artifact fragment) and `site/` (index, `_headers`, `sw.js`, manifest, icons, privacy, support, hidden Netlify form) from `src/`. `netlify.toml` publishes `site/`.
- Packs: `src/packs/<id>.json`. Order and "coming soon" list: `src/packs/index.json`. Boss questions: `src/boss.json` (4 per pack). Photos: `src/photos/<key>.jpg` (max 640 px, q60) plus `manifest.json`. Photos are NOT embedded: the page references `photos/<key>.jpg` and they load on demand (build copies them to `site/photos/`; the Artifact publish must pass every photo in `files`, max 255 per publish). Tests wrap the page in `src/_*.html` so relative photo paths work.
- Pack schema: id, name, explorer, initials, ranks, heroKey, heroAlt, heroLi, heroCredit, mission, afterDone, safetyNote, badgeMap {stopId:[photoKey,"x% y%"]}, level, region, stops. Exactly 4 stops per town. Each stop has id, name, short, badge, tag, teaser, map, clue, safety, field, q{prompt,options,answer,hint,verify}, then{yr,label,line,ph?,link{t,u}} (link is REQUIRED), now{...,ph?}, story[], fact, disputed, claims[] (2, a: 0 solid, 1 disputed, 2 not true), sources[] (2+ https), card.
- XP: 100 per stop, 25 per claim, 600 max per town. Save code is `TN3-` plus one 12-char group per town, so the dash count equals the town count. When adding towns, bump the counts in `tests/flows.py` (town count, `code.count('-')`, and the "too many towns" test with N+1 groups).
- Validator rules: 3+ distinct correct-answer positions per pack, hint must not give the answer, boss answers not all in one slot, 4 distinct boss options.
- Home: regions are collapsible groups and rails. The passport has its own page (rail button next to Home, `onPass` state, `viewPass()`), and Home shows a teaser row. The passport is grouped by region (folds, with per-region stamp counts). The hero circles and "How it works" badges follow the current mission. "Try it from home" demo mode earns no saved stamp.
- Tests: `sh tests/run_all.sh`. If only expected screens change, accept with `python3 tests/snapshot.py index.html tests/baseline.json`.
- Commit trailers: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and the session link.

## Photo pipeline (what works)
- LoC images: navigate the pane to the cdn.loc.gov URL (it redirects to tile.loc.gov; both need site access), then same-origin fetch of location.href and download via canvas. Commons categories can be listed cross-origin from en.wikipedia with origin=*.
- Wikimedia/LoC downloads run in the Claude app's built-in browser (Chrome JS from Apple Events is unreliable). Request site access for commons.wikimedia.org, upload.wikimedia.org, en.wikipedia.org, loc.gov.
- Search the Commons API; filter licenses to Public domain, CC0, CC BY, CC BY-SA; width at least 1000 for "now", at least 600 for old PD.
- For "then" photos the Commons keyword search is poor. Best method: on an en.wikipedia.org page, call /w/api.php with generator=images (article) or generator=categorymembers (Commons category, from a commons.wikimedia.org page) plus prop=imageinfo&iiurlwidth=960, filter license and date, fetch the thumbnail cross-origin (upload.wikimedia.org allows it), shrink on a canvas to 720 px and trigger an <a download>. Also try LoC HABS/HAER surveys and DPLA postcards.
- Download: navigate a tab to the upload.wikimedia.org 960px thumbnail, fetch same-origin, save via `<a download>`. Files land in `~/Downloads` as hidden temp files; rename by byte size, then `device_stage_files`, view a contact sheet to confirm each photo matches its stop, then resize and wire in.

## Status (Oct 20, 2026)
52 towns, 208 stops, 419 photos. **Every stop now has a free-licensed "then" and "now" photo.** Stops were swapped for landmarks that have free "then" photos: Fisher Building, Campus Martius, Saint Anthony Falls, Basilica of Saint Mary, Georgia Capitol, Atlanta Flatiron, Piedmont Park, Memphis Cotton Exchange, Fort Pulaski, Rookery, Lincoln Park Conservatory, Bradbury Building, Angels Flight, Olvera Street, Pioneer Square, Carpenters' Hall (Oct 19), then Reno Train Depot (replaced Original Arch), Cave Rock (replaced Sand Harbor) and Commons Beach (replaced Fanny Bridge) (Oct 20).
- West: Reno, Virginia City, Lake Tahoe (two packs), San Francisco, Los Angeles, Seattle, Portland, Salt Lake City, San Diego
- East: Boston, Washington DC, New York, Philadelphia, Pittsburgh, Baltimore, Providence, Gettysburg, Newport, Portland (Maine), New Haven, Burlington (VT)
- Midwest: Chicago, Detroit, Minneapolis, Cleveland, St. Louis, Milwaukee, Columbus
- South: New Orleans, Atlanta, Memphis, Savannah, Richmond, Charleston, Houston, Nashville, Louisville, Knoxville
- Southwest (new, Oct 20): Denver, Santa Fe, Phoenix, Albuquerque, Tucson, Colorado Springs, Las Vegas, Flagstaff, El Paso, San Antonio
- "Coming soon": Paris.
Some "then" photos are looser matches (labelled honestly): Providence Arcade (1958 survey photo, exterior vs interior now), Milwaukee Soldiers Home (1885 engraving), Carpenters' Hall (old plans), Pioneer Square (the street), Olvera Street (the old Plaza), Camp Richardson (survey photo), Tahoe stereoviews (Tahoe City, c. 1870s).
Also done: 4-step first-run guide (illustrated modal, Next/Back/Skip, ends by scrolling to the mission list; 'Replay the guide' link in the Home footer; seen flag `then-now-tour`), demo mode, dynamic Home hero, region-grouped passport, offline support, privacy and support pages, feedback form.


## Still to do
1. ~~Page size~~ done Oct 20: photos load as files on demand and the data is embedded once (index.html 0.4 MB, was 13.9 MB). Artifact publish needs `files` (limit 255 per publish, 511 per version, so about 500 photos total; then split or move to a CDN).
2. **Southwest** (Las Vegas done Oct 20: Fremont Street 1952, El Cortez 1940s postcard, Fifth Street School 1936, Hoover Dam 1935; photo keys use prefix lw_) (Denver, Santa Fe, Phoenix, Albuquerque, Tucson; written from sources, not yet checked on site).  Pittsburgh, Baltimore, Cleveland, St. Louis, Cincinnati, Indianapolis, Buffalo, Richmond, Charleston, Houston, Nashville, Providence, Salt Lake City, San Diego, Portland and Milwaukee done Oct 20. Hartford, Albany and Omaha scouted: too few free old photos (Hartford and Albany mostly drawings or modern photos mislabelled). Columbus and Gettysburg done Oct 20 (Gettysburg 'now' for the Wills House is an interior bedroom; Soldiers' Monument 'then' is a 1905 Detroit Photographic postcard). Scouted and too thin so far: Rochester (nothing old), Salem (Capitol 1909/1939 only), Next: Salem has only 3 good stops (Capitol 1909/1927 old capitol vs today's, Waller Hall 1868, Oregon Supreme Court Building c.1922; Kay Woolen Mill HABS are drawings only, so a 4th is needed). Louisville done Oct 20 (Galt House had only an 1891 print, so Louisville Water Tower replaced it Oct 21: 1890 tornado-ruins LoC photo vs 2024; Cave Hill had only certificates, so Union Station replaced it). Knoxville, Newport and Portland ME done Oct 20 (Newport/Portland 'then' are NYPL Detroit Publishing postcards, cropped; Portland City Hall 'then' is the 1867 hall that burned in 1908). New Haven and Burlington done Oct 20 (New Haven Green 'then' is a c.1910 postcard photo; Burlington 'then' photos are c.1930-45 Tichnor linen postcards). Jacksonville (only Hemming Park has a matching now/then) and Mobile (Spring Hill, Dauphin St, Government St need matching 'now' photos) are on hold. **Jo-Anne's note (Oct 20): the Southwest is the thinnest region, so keep scouting it.** Colorado Springs done Oct 20 (Pikes Peak 'then' is a c.1953 Tichnor postcard of the avenue; 'now' is the mountain from the highway). El Paso done Oct 21 (Union Depot 1972 white-stucco photo vs 2014 red brick, San Jacinto Plaza 1902 postcard, Hotel Paso del Norte 1913 postcard, Ysleta Mission 1936 HABS; prefix ep_). Flagstaff done Oct 21 (Lowell 1905, depot 1926, Weatherford Hotel, Walnut Canyon c.1900; photo keys prefix fg_; Monte Vista had no exterior 'then'; extra downloaded files unused). San Antonio done Oct 21 (Alamo 1922 LoC photo, San Fernando c.1910 postcard, Mission San Jose 1936 HABS, Sunset Depot postcard c.1903-24; prefix sa_; Nic Tengg c.1900 cards for Mission San Jose and Sunset Depot looked drawn, so rejected). Tulsa and Oklahoma City are too thin. Also: Little Rock and Lexington too thin; Kansas City and Dallas stay on hold (short of free old photos). Later South America (Buenos Aires or Lima) and Paris.
3. ~~App icon~~ done Oct 20 (rubber-stamp postmark with a columned landmark). Desktop layout for town and stop screens done Oct 20 (2-col stop list, 2-col story pane from 900px; phone unchanged).
4. Jo-Anne-owned: Reno on-site walk (`docs/verification-checklist.md`), run the USPTO search (domain done), support email, Apple Developer account, posting for testers.
5. Later: wrap for the App Store (decided Oct 20: no login. In the native wrapper, save progress in the app's own storage (Capacitor Preferences or similar), not browser localStorage, so iOS inactivity cleanup can't wipe it; it rides along with the normal iCloud device backup. Keep the TN3 save code as a manual backup. Sign in with Apple only if cross-device sync or leaderboards are ever needed), pricing/monetization decision, more towns each month.

Other docs: `docs/roadmap.md`, `docs/name-and-launch.md`, `docs/verification-checklist.md`, `docs/tester-post.md`, `CREDITS.md`.


**Photo audit Oct 21 (Jo-Anne: photos are number one, no paintings or drawings):** all 205 then-photos reviewed. Swapped to real photos: Chicago Buckingham 1933, Gettysburg monument 1905, Philly Carpenters' Hall, New Orleans Jackson Square 1900, New Haven Green c.1910. Nashville Fort Nashborough replaced by Public Square (1892 LoC photo vs courthouse; ids square/na_ps_), Louisville Galt House replaced by Water Tower (lv_wt_). Still non-photo "then" (need real photos or a stop swap): Atlanta Capitol (HABS is drawings only; Schaub stereoviews show the Kimball Opera House; linen postcard is painted), Milwaukee Soldiers Home, Milwaukee Auditorium (only an architect rendering). Savannah River Street fixed Oct 21 with a 1934 HABS photo. Painted-looking linen postcards to revisit: cs_pk, cl_tt, in_wm, bv_bp/cs/bl, lw_ec, tu_cc, tu_dp, sa_lf, sa_pg, de_cm, sd_mi, de_di, at_pk.

**UX batch 1 (Oct 21):** compact slim header inside a stop (no tabs/city rail), one back control (top '‹ Trail'; bottom bar only appears after step 1 as '‹ Previous step'; #barExit hidden), 'Sources' step label, 12px labels, fade on scrolling rails, no duplicate badge toast. Tests now exit stops via `.stophead [data-a=exit]`. Next: UX batch 2 (one photo block on story screen, rename Cards/Rewards/Passport, collapse empty passport towns, single locked tile) and batch 3 (home search + region cards, hero contrast, per-town mission text, tour length, slider nudge).

**UX batch 2 (Oct 21):** story screen shows one slider plus caption blocks (no repeated photos; old paired photos only when a photo is missing), tabs renamed Trail / Time Cards / Stamps, rail button 'My Passport', one combined 'N locked' tile in Time Cards, passport lists only started towns per region with a '"N not started"' line.

**UX batch 3 (Oct 21):** home town search (#townSearch filters towns, opens regions), progress ring per region, stronger hero scrim, mission card lists the town's four stops (full boilerplate only before the first stamp), unverified note shortens to one line, tour cut from 7 to 4 steps, slider nudges once per session. UX review done; remaining ideas: move hero photo credit out of the hero, tablet layout pass.

**UX batch 4 (Oct 21):** tablet pass (768px home headline/wordmark no longer wrap to 6 lines, app width 720px), fixed town rail scrolling off the active town at tablet widths, 'Today' caption no longer doubled. Hero photo credit stays in the hero (license wants it beside the photo).

**Beta prep (Oct 21):** 'Back up your passport' card (id #backup), link under the home passport row (data-a=backup), one-time nudge on the Trail after the first stamp (again after 8 more; localStorage `stp-bk-seen`). Netlify 'Powered by Netlify' badge (free plan, projects from Aug 19 2026) must be switched off in Project configuration > General by Jo-Anne. See `docs/beta-checklist.md`. Midwest is now the smallest region (9 towns); scouting Springfield IL and St. Paul next (Lincoln Home 1865 parlor photo and Minnesota Capitol construction photos exist on Commons).

## Dayton (Oct 22)
- Town 53, Midwest. Springfield IL and St. Paul were skipped: too few free "then" photos. Madison and Mackinac are also thin on Commons.
- Stop 1 then-photo (Orville in the shop, 1897) is from the West Third St shop, not the Williams St building. The captions say so.
- Stop 4 "then" is a 1906 portrait of Dunbar, not the house. Huffman Prairie is on Wright-Patterson AFB: safety text says to check NPS access rules. Jo-Anne should verify access on the day.
- Fact-check rounds 1-3 (46 stops) found 4 small fixes, all applied.

## Come-back batch (Oct 22)
- Home: progress card (weekly streak + stamps this month + next goal), My trip (star on town tiles), state chips, Trails across towns (regex on stop names: stations, capitols/courthouses, churches/missions, bridges/towers).
- Share card: canvas PNG (no location data), Web Share if available, else a save modal. Falls back to a no-photo card if the canvas is tainted (file://).
- localStorage keys: stp-log (stamp dates), stp-trip (starred towns). TSTATE/TFULL map towns to states: update when adding a town.

## Browse tabs (Oct 23)
- Home browse area is tabs: Towns (photo tiles) | Trails (colored collection cards + checklist) | My trip (checklist). State: btab/btrail vars, setBtab(). Next: hamburger Menu for secondary items (backup, guide, feedback, parents info, credits, settings; accounts later for the App Store).

## Menu (Oct 23)
- Right-side drawer from the top-bar Menu button (openMenu/closeMenu): backup, share passport, replay guide, how it works, feedback, parents info, photo credits, appearance (stp-theme: system/light/dark), Account placeholder ("No account needed"). Home footer now just links to the Menu. Hidden inside a stop. If real accounts are added, Apple requires in-app account deletion.

## Tab bar and Home redesign (Oct 24)
- Floating pill bottom nav `#bnav` (Home / Towns / Trails / Passport), hidden inside a stop; the top-rail Home and My Passport buttons are gone. Tests use `#bnav [data-t=home]`.
- Safety tips are removed from the UI (user feedback). `safety` and `safetyNote` stay in the packs only because the validator requires them. The Huffman base-access note lives in its clue.
- Home order: hero (on phones the photo cluster comes first), slim progress card (stamps, rank via GRANKS, small "Next stop" button), "Jump back in" town photo rings, then goal card and browse tabs. The big blue button and the dark passport card were rejected by Jo-Anne as ugly: keep things slim.
- Rule from Jo-Anne: copying ideas from other apps is fine, but check screenshots and make it look good. Do not hide hero content.
- Home hero photos auto-rotate every 5 s through towns (round-robin across regions: Reno, Boston, Chicago, New Orleans, Denver...). Paused 12 s after any manual focus (hover, region fold), when the tab is hidden, off Home, or with reduced motion.

## Native wrapper (Oct 24)
- Capacitor 8 project added: `ios/`, `android/`, `capacitor.config.json`, `package.json`, `assets/`. See `docs/native-app.md`. App id `com.stampthepast.app` (permanent after first upload). Plan: iPhone first (Jo-Anne has an iPhone and a Mac; Xcode not yet installed as of Oct 24, Mac screen was locked so it could not be installed remotely), Android later (Play needs 12 testers for 14 days on new personal accounts).
- Done Oct 24: progress is mirrored into native UserDefaults by a local Swift plugin `StampStore` (in AppDelegate.swift, registered by StampViewController in the storyboard; JS shim at top of app.js; restores into localStorage and reloads once if the web view was wiped). Untested on a device until Jo-Anne reruns from Xcode. TODO before store release: store listing text; privacy answers; real domain.

## Launch checklist (Oct 24)
- Live checklist artifact: https://claude.ai/artifact/Rqby3GwGuEoNVNfgqGL3bf (tick boxes, add items; data in the `tasks` collection, add rows with ArtifactData: title, note, group "N Name", kind store|want, owner Jo-Anne|Claude|Both, done, order). Source page: `docs/checklist.html`. Add new to-dos there as they come up and tick off what we finish.
- Oct 24: removed the per-stop Safety box from the Find it screen (user asked earlier for safety tips gone). iOS target is iPhone only now. Store text, privacy/age answers in `store/app-store-listing.md`; screenshots in `store/screenshots-iphone/` (regenerate with the script in that doc's notes: Playwright 440x956 @3x on `site/index.html`).

## Photo hunt notes (Oct 24, later)
- d04 progress: Santa Fe Palace of the Governors now a real 1934 HABS photo. 14 painted/odd "then" images left: cs_pk, cl_tt, in_wm, bv_bp, bv_cs, bv_bl, lw_ec, tu_cc, tu_dp, sa_lf, de_cm, sd_mi, de_di (a Rivera mural, not the building), at_pk (newspaper halftone). Commons keyword search is noisy; HABS/LoC photos from the 1930s are the best source.
- Tooling this session: the built-in browser pane's javascript_tool returned nothing, but Control_Chrome (her Chrome, tab on commons.wikimedia.org) worked: fetch the API with a same-origin path, take `iiurlwidth=720` `thumburl` (do NOT use Special:FilePath on .tif, it saves an HTML error page), save with `<a download>` to a normal-named file in ~/Downloads, then device_stage_files. Async results cannot be returned directly: put them in `document.title` (single line, truncated at about 1 KB) and read with get_current_tab after a few seconds. WebFetch of Wikipedia pages works for fact checks. Never list the whole ~/Downloads folder (huge).

## Review follow-up (Oct 24, evening)
- Full UI/UX review done on the live site (see repo history). Already fixed before: 44px state chips, lazy images, trail categories, Paris dead end hidden. Fixed now: 44px star buttons on town tiles, trail location labels (no more 'Portland, Maine, ME' or 'Washington DC, DC'), banner reworded to 'Written from sources, not walked yet'. The 'menu overlap' in the review was really the scrolling town rail with a fade, not a bug. Focus rings exist (`:focus-visible`). Still open: real-device test of progress backup in the native app, airplane-mode test, App Store native-value list, continue-first home screen idea.

## GPS verified visits (Oct 24)
- Audience is now anyone, not teen-only. Each stop has `"geo": [lat, lon, radius_m]` (211 of 212; Pikes Peak excluded). Validator checks it. Coordinates came from Wikipedia and Nominatim with outlier checks; a few were set by hand.
- Find it screen has an optional gold 'Check my location' button (geoCheck in app.js: accuracy <=150 m and inside radius). Normal 'I am here' always works. Verified flags live in localStorage `stp-geo` (mirrored natively, not in the TN3 save code). Location is never sent anywhere. iOS NSLocationWhenInUseUsageDescription and Android location permissions added; privacy page and store docs updated.
- Oct 25: live location while the app is open (Pokemon Go style, NOT background). Once location was allowed (`stp-geo-ok`), `watchPosition` runs while the page is visible (stops when hidden; Menu toggle `stp-geo-live`). Home shows a `#nearBox` card ('You are here' / 'Near you, X away'); standing at the open stop auto-jumps to the question; a stamped stop auto-verifies when you pass it. Auto-detect after allowing, plus a 'Verify this visit' card on stamped stops. Background geofencing (20-region cap, Always permission, Swift plugin, Android declaration) is parked as v1.2 opt-in. Tests wrap pages via `src/_flow.html`, regenerated only by `tests/run_all.sh`.

## Sparks (Oct 25)
- Town 54 (West, level Hidden Gems), photo keys prefix `sp_`. Stops: Victorian Square, Railroad Shops, Truckee River, Sparks Marina (Jo-Anne lives in Sparks; Marina verified on her phone Oct 25). GPS circles for Shops and Marina are estimates; Marina circle 900 m at the RV park (39.5378,-119.7236).
- Marina "then" is a USGS public-domain photo of the Jan 3, 1997 flood over Sparks (Patrick Glancy), labeled as NOT the pit. Still wanted: a free photo of the Helms Pit itself. Not usable (rights reserved or unknown): Peter Goin (LoC and wnhpc), NDOT 1997 photos on wnhpc, Sparks Museum 1970s/1997 photos.
- Sparks engine "then" is SP No. 8 in Carson City (1975), a looser match. Roundhouse stop was dropped (it shared a marker with Railroad Shops); roundhouse postcard is the Sparks hero.
- Proactive 'You are at X' banner (hereShow in app.js) when the app is open. Background alerts (iOS only, off by default, Menu toggle `stp-bg`): Swift `StampGeoPlugin` in AppDelegate.swift monitors the 20 nearest unstamped stops, local notification on entry, tap opens the stop. NOT yet compiled or tested on a device.
- Lesson: view every downloaded photo before wiring it in (the Commons "Sparks Marina.jpg" was a car show).

## Landing page (Oct 25)
- `src/landing.html` is built by build.py into `site/index.html` (stampthepast.com root). The game itself is `site/play.html` (served at /play). Manifest start_url and sw.js use play.html; sw ignores other navigations. robots.txt and sitemap.xml are generated; /play is noindex, the landing is indexable.
- Landing says location is optional and stays on the phone (not "no location tracking"); app Menu matches.

## Carson City (Oct 25)
- 4 stops: Capitol, Old Mint (Nevada State Museum), Stewart Indian School, Railroad Museum. Second town after Reno/Sparks (index order: reno, sparks, carson, vc...).
- GPS circles are estimates from Wikipedia coordinates (Stewart and Railroad Museum are rough). Jo-Anne to walk them.
- Capitol "Now" is a drone view (CC0); Stewart "Now" is a different building than 1905 Then; both labeled honestly. Stewart text is deliberately careful about boarding school history.
- Source for photos: Commons via browser pane; shell cannot reach Wikimedia.

## Oct 26 additions
- Trail of the week card on Home (rotates weekly through trails with 3+ stops; opens the Trails tab). Passport tab dot for unseen stamps (`stp-pass-seen`).
- Haptic on stamp: native `StampStore.haptic` (Swift in AppDelegate.swift, UINotificationFeedbackGenerator). Compile and feel NOT yet tested on a device. JS ignores it on web or old builds.
- Open in Maps button already existed on Find it (text search); do not add another.
- Passport share card already existed (Passport + each town); share text now carries the web address.

- Native app: Capacitor webDir is site/, whose index.html is the landing page. The landing head script redirects to play.html when running inside the app (capacitor: protocol). Do not remove it or the App Store build shows the website instead of the game.

## Level, badges and Trophy Case (Oct 26)
- Explorer level is global and derived from saved progress (`gStats()`, `lvOf()` in app.js): level L needs 25*(L-1)*(L+2) XP; titles Newcomer, Wanderer, Trailblazer, Pathfinder, Explorer, Historian, Archivist, Time Traveler, Grand Chronicler. XP = town XP (100/stamp, 25/claim) + 100 per finished town + 50 per verified visit + 50 per new state + challenge points. Town ranks and inks are unchanged.
- 40 badges in `BADGES` (common/rare/legendary), all derived; only the earned list is stored (`stp-badges`, id to date; `stp-bseen` for the Passport dot). Trophy Case and level card sit on the Passport page; Home status card shows level. A non-blocking snackbar (`#bpop`) announces new badges about 2 s after a stamp, claim check, challenge or verified visit. Existing players get their badges filed quietly with one toast.
- Next phases: quests/collections and the Now-photo camera (Phase 2), friends and leaderboards (Phase 3, needs accounts and moderation).

## Share this fade (Oct 29)
- Story screen has a "Share this fade" button (`.sharefade`, `fadeShare`/`fadeMake` in app.js): 720x960 canvas + MediaRecorder clip (mp4/webm) of the Now-to-Then fade, Web Share with file, `#sharem` modal fallback, PNG fallback. Needs http (canvas is tainted on file://). Native iOS web view behavior untested.
- Visitor counter live (Oct 29): GoatCounter site `stampthepast`, loader in src/landing.html and src/head.html, runs only on stampthepast.com and *.netlify.app (never native or tests); privacy page updated.
- Growth learnings: Reddit tester subs and the Historic Reno Preservation Society FB group (no promo/links) gave zero replies. Plan: GoatCounter visitor counter (cookie-free; then reword "no tracking" copy on landing, Menu, parents, privacy, store listing), short fade videos, DM local contacts, set a success bar before paying the $99 Apple fee.

## Crawlable pages (Oct 29)
- `seo.py` (called from build.py) writes 291 static pages into site/: `/<town>/` (58), `/<town>/<stop>/` (232), `/places/`; each has a unique title/description, OG image, JSON-LD, then/now fade slider with credits, story, fact check, sources, CTA to /play. Sitemap lists them all; landing footer links /places/. `/play` stays noindex. `tests/seo_check.py` checks titles, links, photos, overflow (it is part of run_all). Next: Jo-Anne verifies stampthepast.com in Google Search Console and we submit the sitemap; check GoatCounter in ~2 weeks.
- Event counters (Oct 29): `ping()`/`pingOnce()` in app.js send anonymous GoatCounter events `event/stamp`, `event/first-stamp`, `event/town-finished`, `event/active-day` (web only; no-op in native/offline; tested in flows.py). Read them in the GoatCounter dashboard. Privacy page updated.
- Test card (Oct 29): `/test` (noindex, built by `seo.test_pages`) is a written 10-minute test with 4 tasks and a neutral feedback form (Netlify form `testcard`, posts to /test-thanks.html). Jo-Anne will not pay testers, do video calls, or approach strangers or friends/family, so this one link is the recruiting asset. Netlify form notification email must be set by Jo-Anne in Netlify > Forms.
- Decision rule agreed Oct 29: wait ~3 weeks; if 100+ strangers visit and 5+ finish a town (town-finished events), the $99 is justified; if few reach a first stamp, fix onboarding first.
- Explore from home (Oct 30): the Find-it demo button now reads 'Not there? Explore from home' and the banner says stamps are for real visits. A real 'virtual stamp' that counts toward progress is NOT built; it needs a design decision (save code, XP, badges) and more than one person asking (first request came from a Facebook commenter).
- Daily Fact or Fiction (Oct 30): `/daily/` (built by `seo.daily_page`, indexable, in sitemap). One claim per day from the ~460 stop claims, same for everyone (seeded shuffle, day count since 2026-11-01, no server). Locks after answering (`stp-daily`), streak in `stp-daily-streak`, share text via Web Share or clipboard, anonymous `event/daily-played`. Linked from landing and page footers. Tested by tests/daily_check.py. Not yet linked inside the game (Menu item would need a link handler).
- Menu (web only): 'Play anywhere > Daily Fact or Fiction' item opens /daily/ (hidden in the native app because /daily and /play paths do not exist there).

- First-run home (no stamps yet) shows a "How it works" block (go there / prove it / stamp it, what XP is, explore-from-home hint). Added after test card #1: the tester did not realize you must travel, and did not know what XP is for. A first-run quick-tour modal already existed; people may skip it.

- Google Search Console: property https://stampthepast.com/ verified by HTML file `google7a48ffa7f434a573.html`, written by build.py into site/. Do not remove (verification lapses if it is gone).

- Share this fade: iOS Safari rejects navigator.share if it is not called from a tap, and the clip takes ~5s to record, so the clip now always opens a preview with a real "Share it" button (data-a=sharefile) plus Save. fadeMake has a 9s watchdog that falls back to the still picture. Closed `<details>` with a `display:flex` child (`.srcs`) rendered as a big blank box in iOS Safari; `details:not([open])>.srcs{display:none}` fixes it. Details cards now show a +/- marker.

- Two stamp tiers v1 (Oct 30): "Explore from home" now earns a VIRTUAL stamp when the question is answered right. Stored in localStorage `stp-virt` {"town:stop":1}; the TN3 save code and real stamps are untouched. Worth 25 XP in global level (gStats.virt) only, once per stop, ignored once the real stamp exists. Never counts toward town completion, town XP bar, badges or streaks. Stop list shows a dashed "Virtual stamp" chip. Event `virtual-stamp` is counted anonymously. Not built yet: Armchair Explorer badge, an outline stamp image, passport view of virtual stamps. See docs/two-tier-stamps.md.

- Virtual stamps look different: faded greyscale badge photo, dashed ring and a "Virtual" tag (`.bbox.virt`, `.vtag`). Real stamps keep full colour. In the native app `<a download>` does nothing in the WKWebView, so the share preview shows one "Share or save it" button (iOS share sheet has Save Video / Save Image); the plain Save link only appears where the share sheet is unavailable.

- Passport shows an "Explored from home" card (#vpass) listing virtual stamps. New badge `arm` Armchair Explorer (10 virtual stops, common), so 40 badges now. endDemo() calls awardSoon() so the badge is awarded after leaving the preview.

- "Spot the change" puzzle: optional `spot` {q,options,answer,why} on a stop, shown under the Then/Now slider (`spotHtml`, handler `spotpick`). No XP, nothing saved. Pilot is the 4 Reno stops, the 4 Phoenix stops and the 4 Sacramento stops, the 4 Sparks stops the 4 Carson City stops, the 4 Virginia City stops and the 4 Lake Tahoe stops (Andrea played Phoenix); every question and answer is taken only from text already in the pack's story/then/now lines. Add more only from sourced pack text, never invent a change.

- Spot the change is made prominent on purpose (Jo-Anne: "it is a fun feature, why hide it"): bordered "Puzzle: spot the change" card under the slider, a pointer in the slider hint, and a "Puzzle" chip on stops in the stop list.

- Report-driven batch 1 (Oct 30): removed "DRAFT" from privacy/support (now "Last updated October 30, 2026. A plain-language summary, not legal advice."), fixed wording to match the app (button is "Verify with my location (optional)"; save code is under "Back up your passport" on the Passport screen and the town Stamps tab; virtual stamps are not in the code). `now.yr` is the label for the TODAY photo, so it must be the photo's year, not an event year: fixed 7 stops (Reno arch, Faneuil Hall, Tahoe dam/gate/watson, VC C Street/Piper's). Find-it screen now says "I am here" is on your honor and location verification is optional.

- Story screen shows the first ~3 sentences (about 190 characters) and puts the rest under a "Read more" details (`storyHtml`, abbreviation-aware sentence split; the crawlable pages keep the full text). Town "Your mission" card shows `tourInfo`: about N miles in the shortest order and a rough walking time (3 mph x 1.3 detour), or "Spread out ... plan to drive" above 2.5 miles. Straight-line from the stops' map points, always worded "about".

## Oct 30 audit fixes (batch)
- SceneDelegate now creates `StampViewController` (it was a plain CAPBridgeViewController, so StampStore/StampGeo were probably never registered). Needs a device check: `Capacitor.Plugins.StampGeo` and `StampStore` should exist.
- Info.plist `UIRequiredDeviceCapabilities`: armv7 -> arm64.
- Fonts are bundled in `src/fonts/` (woff2 + fonts.css from @fontsource, latin subset) and copied to `site/fonts/`; `head.html` links `fonts/fonts.css`. The app makes no Google requests. Landing page and the 292 SEO pages still use Google Fonts (web only).
- `tourInfo` now starts with the stop count ("4 stops. About 1.2 miles...").
- q03: AppDelegate.didFinishLaunching creates `StampGeoRelaunch` (own CLLocationManager + delegate) when iOS relaunches the app for a location event, so region alerts fire without the web view. Alert code shared via `StampGeoNotify.entered`. Written without a compiler: the next Xcode build is the check, then a simulated-location test with the app killed.

## Home that feels like home (r12, Oct 30)
- Tappable `button.topmark` ("Stamp the Past", data-a="home") in the top bar; shown when the player has stamps (`body:not(.homefirst)`), hidden on first-time Home where the big stamp wordmark is already on screen.
- Returning Home order: progress + Next stop, Near you, Jump back in, hero. First-time: Near you, hero, How it works, rings. `viewHome` toggles `body.homefirst`.
- Returning Home's top bar is static (logo left, menu right) instead of the floating menu button.
- Inside a stop, the head has a "Home" link next to the stop tag.
- Menu has "About Stamp the Past (our website)" on stampthepast.com only (hidden in the native app).

- Find-it screen: "Get directions in Maps" opens Google Maps directions to the stop coordinates (falls back to a name search when a stop has no geo). Accessibility notes per stop are still open (checklist r02).

## Closest-stops list (r03, Oct 30)
- Home shows "Closest to you": the 5 nearest unstamped stops within 150 km, with distance, tap to open (`nearListHtml`, handler `nearme`). Before location is allowed it shows an optional "Show the closest stops" button; denied or no geolocation shows nothing. The old single "Near you" card is gone; "You are here" (inside the circle) stays.

## Accessibility pass 1 (r10, Oct 30)
- axe-core (wcag2a/aa/21aa + best-practice) on Home, Towns, Passport, Stop, Question in light and dark at 390px: 0 violations after fixes. Fixes: real `<main>` landmark wrapping the tabpanel `#main`, stop title is now an h1, photo-credit and Home caption contrast. Not covered: screen reader walkthrough on a device, Dynamic Type (q07), landing and SEO pages.

## Daily card on Home (audit #4, Oct 30)
- `dailyCardHtml()` shows a "Daily Fact or Fiction" card on Home on stampthepast.com only (hidden on localhost, the native app and test hosts). It reads `stp-daily` and `stp-daily-streak`, which the /daily/ page writes on the same origin; button uses the existing `daily` action. Not covered by the flow tests (they run on localhost); checked once with a simulated stampthepast.com origin.

- Find-it screen now says "Go there for the real stamp. About N minutes once you arrive. Or explore from home." (`stopMins`: story + question words at 200 wpm, plus 1 minute, clamped 2-6). Hidden once the stop is done and in demo mode. (audit #5)

- "Protect your stamps" backup nudge (`bkNudgeHtml`) now also shows on returning Home, under the progress card; same rule as the trail (after the first stamp, then every 8). (audit #8)

## Town finish payoff (audit #6, Oct 30)
- Before a town is finished the "Your mission" card says: "Finish all four to unlock the final challenge..." (only for towns with boss questions).
- The celebration modal leads with "Play the final challenge" (action `celebboss`) when the town has one; Share my stamps / passport / keep exploring follow. New flow tests cover both.

## Sacramento (town 59, added Oct 30 2026, a friend's request)
- Pack `src/packs/sacramento.json`, 4 stops: State Capitol, Sutter's Fort, Tower Bridge, Crocker Art Museum. Photo keys use the `sc_` prefix (`sa_` is San Antonio). Final challenge added in `src/boss.json`; `TSTATE` in app.js has `sacramento:CA`.
- Photos: all from Commons (PD or CC BY-SA/PD), credited in CREDITS.md and each stop's `ph`. Then photos: c.1900 Capitol (C. C. Pierce, CHS), 1925 fort bastion (HABS), July 1935 Tower Bridge construction (HAER), 1886 Crocker house (HABS/Society of California Pioneers). The Tower Bridge "now" photo is a 2006 public-domain edit.
- GPS circles are estimates from Wikipedia coordinates (Tower Bridge center moved east to the Sacramento approach). Nobody has walked these yet, so check circles on site.
- Photo route lesson: in this session the built-in browser could read Commons pages but not run downloads. Chrome via Control_Chrome worked after a full Chrome restart (frozen tab made every execute_javascript time out). Sync XHR in execute_javascript returns the result string directly.

## Stamp buzz test (Oct 31 2026)
- Jo-Anne felt no haptic on the iPhone build (she may not have earned a stamp). `haptic()` now finds the StampStore plugin via `Capacitor.Plugins` or `registerPlugin`, and reports ok/missing/error.
- New native-only menu item "Test the stamp buzz" (`hapticTest`) fires the buzz and toasts the result. Use it to tell a plugin failure from the iPhone's System Haptics setting.

## Anonymous error counter (Oct 31 2026)
- `window` error and unhandledrejection listeners call `errPing(line)`: GoatCounter event `error` with title `error L<line>`, max 3 per visit, website only (same gate as the visit counter). No message text, no player data. Read it in GoatCounter under events.

## Starting-town suggestion (Oct 31 2026)
- First-time Home (zero stamps) shows a "New here? Start in <town>" card (`startTownHtml`, class `starttown`) picked from the phone's time zone via `Intl`; nothing is sent anywhere. Map: New York->ny, Toronto->buffalo, Detroit, Chicago, Indianapolis, Louisville, Denver, Boise->saltlake, Phoenix, Anchorage->sitka, Honolulu; any non-American zone -> ny. Los Angeles zone shows nothing (Reno stays the default). Checked with Playwright timezone_id for 4 zones; no flows test yet.

- Town share card (r06): finished towns show a "Did you know?" line, one stop fact (<=150 chars, same one every time per town) via townDiscovery(k) in src/app.js.

- Landing + ~297 town pages now use bundled /fonts/fonts.css instead of Google Fonts (n02). Plex Mono 600 is not bundled; browsers synthesize it from 500.

- Larger text (q07): every font-size in src/styles.css is now rem (px/16), and `@supports (font:-apple-system-body){html{font:-apple-system-body}}` makes iOS Safari and the app follow the Dynamic Type setting (default Large = 17px, so about 6% bigger than before on iPhone). Checked in Playwright with html font-size 16/24/32px at 390 wide: no sideways scroll on Home/Towns. Landing page and SEO pages still use px. Not yet checked on a real phone with the setting turned up.

- Phone UX audit (Oct 31), tasks u01-u05 done: stop title #stopTitle clamp(2rem,9.5vw,3rem); Home .nearbox gap 56px -> 6px; town .hero min-height 240px on phones (content-limited, about 312px); edge fade + end spacer on .tcards/.schips/.rrow; Passport shows a .pnote and a next-step button while challenge seals is 0. Still to look at on a real phone.
- Home 'Story of the day' card (u08): featuredHtml() in src/app.js picks one not-yet-stamped stop of the current town per local day, shows its now-photo with credit, a sourced fact (or teaser) and a Read this stop button. Returning players only, placed below Closest to you so Next stop stays first.
- Trails stop rows (u10) show a 44px lazy-loaded thumbnail of the stop's now-photo (.tthumb), decorative alt.
- Badge snackbar (u06): a single new badge earned inside a stop also says 'Earned at <stop>, <town>.' plus the first sentence of that stop's fact (.bsn-p); stays 13 s. No share button on the snackbar (too tight on small phones).
- Menu (u09): Settings moved up under Play anywhere; Report stays visible under Help; Replay guide, buzz test, How it works and the website link now sit in a 'Guide and about' details (.mhelp). Privacy and backup wording unchanged.
- Landing photos near you (n03): build.py bakes four now-photos (with credits) for each time-zone town into src/landing.html ({{NEAR}}); an inline script swaps the four hero stamps, a small caption and the credits line from Intl time zone, on the device only. Pacific zones keep Nevada; zones outside the Americas get New York. Static HTML (what crawlers see) stays Reno.
- Home coherence (v01): nextRef() in src/app.js is the single source for Next stop; Closest to you skips it and Story of the day uses the Next-stop town and a different stop.
- Final challenge (v02): body.inboss (set in render) shrinks the hero to a slim town name and hides tabs, chips and the bottom nav so the question and answers are visible without scrolling.
- Bottom bar (v04): goHome() sets bnavSel='home' so any Home link highlights Home.
- Bottom bar room (v03): page bottom padding 96px (+safe area) so the last card scrolls fully clear of the floating bar on Home, Towns, Trails, Passport; test added.
- Check-in reach (v05): the 'I am here. Show me the question' button is sticky to the bottom of the screen on a stop's first step (.stickgo), so it never needs scrolling to find; test added.
- XP labels (v06): town header reads 'N town XP · next rank at M' (per-town rank); Home and Passport say 'Explorer level' for the global track.
- Verified-visit card (v07): on an already-stamped stop it now says you already have the stamp and that verifying upgrades it to a gold stamp for +50 XP.
- Nearby list (v08): Home shows 3 closest stops, then a 'See more nearby stops' button reveals up to 8.
- Badge popup (test fix): .bsnack lets taps pass through (only its See and close buttons catch taps) so it never blocks Next buttons beneath it for its 13 s.
- Home badge goal + Passport current town (v09, v10): Home progress card shows 'Next badge: <name> · n of goal' (closest unearned badge); Passport head shows 'Right now: <town> · d of t stamps, n to go' for the in-progress town. Tests added.
- Toast (w01): .toast uses width:max-content and a 18px radius; before, a fixed left:50% box shrank to half the screen and long messages became a tall blob at 360px.
- Keyboard (w02): Tab trap in menu/report/tour/celebration now covers links, inputs and summaries and ignores hidden ones (checkVisibility); closing Report with Escape returns focus to the Menu button. Tests added.
- Slider hint (w04): a 'Drag to travel back' tag sits on the Then/Now photo until the slider is used once (localStorage stp-dragged); test added.
- Spot the change (p15): added to Boston, New York and Chicago (12 more stops, 40 total), from sourced pack text only.
- Spot the change (p15): added to San Francisco, Washington DC and Honolulu (12 more stops, 52 total), from sourced pack text only.
- Save a stop (r05): stop screen has Save/Saved (aria-pressed) for unstamped stops; saved stops (localStorage stp-saved, 'k:stopid') list under Towns > My trip with Open and unstar. Not on Home yet.

## Phone review #3 fixes (x01-x04)
- x01: the "I am here" button now sits right after the clue and only pins (`.stickgo.pin`, toggled by `pinGo()` on scroll/resize/render) once the clue is above the pin line, so it never covers unread clue text. Test checks 390x844, 375x667, 360x740.
- x02: Story of the day skips stops shown in "Closest to you" (shared `nearArr()`).
- x03: Towns card now reads "Quickest town to finish: X" so it does not clash with Home's Next stop.
- x04: Passport badge progress labels (`.bt-s`) bumped to 13px.

## Phone review #4 (x05-x07)
- x05: Verified with a mocked location that Story of the day no longer repeats a stop in "Closest to you" (the reviewer likely saw the build before x02).
- x06: Saved stops: Home shows "Your saved stops: N" card (`savedCardHtml`, action `gotrip` opens Towns > My trip); My trip tab count includes saved stops; saved list shows minutes per stop, total time on site and is sorted closest-first when location is on; toast points to Home > My trip.
- x07: Finished-stop "What next" panel (`nextPanel`) now shows "N of M stamps in TOWN", a progress bar and the next badge goal above the Next stop button.
- Spot the change (p15): added to Philadelphia (`philly`), Seattle, Portland (OR) and Denver (16 more stops, 68 total), from sourced pack text only.
- Spot the change (p15): added to Atlanta, Nashville, New Orleans (`nola`) and Baltimore (16 more stops, 84 total), from sourced pack text only.
- Stop-list chips (x08): status and chips now sit in one `.srow` flex row (nowrap pills, 6px gap); "Tap to verify when you visit" became a quieter "Verify on a visit" (`.vchip.soft`) so Puzzle stands out. Test text updated.
- Spot the change (p15): added to Pittsburgh, Cleveland, St. Louis and Detroit (16 more stops, 100 total), from sourced pack text only.
