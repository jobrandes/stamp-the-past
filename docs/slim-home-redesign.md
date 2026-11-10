# Slim Home redesign (design from the Nov 9 2026 session; NOT built)

Mockups: `docs/design/slim-home-first-time.png` and `docs/design/slim-home-returning.png` (each shows today's first screens, today's whole page and the slim whole page). The slim version was only built temporarily to take screenshots; the live site is unchanged.

## Size
First-time visitor: about 7.8 screens today, about 1.1 slim. Returning player: about 6 screens, under 1.

## Keeps
- First-time: one "Try one from your couch" start card (town photo, "Play the <stop>", "Or find real stops near me"). Reno Arch in the mockup was only a placeholder.
- Returning: existing progress card with Next stop.
- Both: "Today" row (Daily Fact or Fiction), "Your places" row if they contributed, links "Browse all 62 towns" and "Add your town".

## Moves off Home
Town list, search and state chips go to the Towns tab (its own page; about a day plus test updates, since many tests assume the list is on Home). Backup nudge (to Passport plus a one-time toast after the first stamp), Story of the day, town rings, Trail of the week, From the community card, town-request box, and the How it works / Then and now / Is that actually true / parents sections (landing page covers them).

## Decision (Jo-Anne): not Reno as the default
Start-card town, in order: (1) location already allowed -> nearest stop with distance; (2) else the phone's time zone (reuse `startTownHtml`, nothing sent); (3) "Not near <town>? Pick your state" link, remembered on the phone. Pacific zone (CA, WA, OR, NV): no guess, show a state picker up front. State with no town: say so, offer nearest town plus "Add your town". Never ask for location on first load.

## Open
Jo-Anne's yes to build; keep the four-stamp photo cluster as the start card image? (she earlier said not to hide hero content). Mockup flaws to ignore: wordmark twice on returning, sample streak and like numbers, bottom bar and badge popup drawn mid-page.
