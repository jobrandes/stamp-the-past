# Community-city test (branch `community-test`)

Updated Nov 2 2026. Supersedes the "links only, no uploads, Reno pilot" version in the design doc for the TEST branch only; the doc's rules for the live app still stand.

## What Jo-Anne decided
- Her dad plays a stranger: he adds a city, four places, photos, with no help from her.
- It shows up instantly, but only in the test deploy. The live site and the App Store build never read it.
- Shape: a full four-stop mission, same format as every town.

## What the contributor writes
City, four places, a story per place (their own words from their sources), two https sources per place, a "then" and a "now" photo per place with credit, year, license and caption. Optional: address, lat/lon, and one quiz question per place.

## What Claude fills in
- Placeholder quiz when none is supplied: "Which of these is the name of the place you are standing at?" using the four place names. Labelled as a placeholder.
- GPS circle only when the contributor gives lat/lon (300 m). No lat/lon, no verified-visit button.
- Not possible without inventing facts: fact-check claims and the final challenge. Community cities have neither. A later step can have Claude draft claims from the contributor's sources, reviewed by Jo-Anne.

## Photo rules (unchanged in spirit)
"Then": must link a commons.wikimedia.org or loc.gov page, license Public domain / CC0 / CC BY / CC BY-SA. "Now": the contributor's own photo (ticks "I took this", picks CC0 / CC BY / CC BY-SA) or a linked free source. Rights are the contributor's word plus the link, so nothing leaves the test branch without Jo-Anne checking each photo.

## Privacy
No name, email or precise location collected. Photos are re-encoded in the browser (EXIF removed). Optional nickname. A reference id plus secret edit token lives only in the edit link. Stored in Netlify Blobs on the test deploy. Retention: nothing deletes automatically; Jo-Anne can delete the store in Netlify (Data & Storage > Blobs).

## Open before production
Review gate (flag `hidden` exists), Apple Guideline 1.2 (report, block, contact), privacy page text, support email, photo-rights review, claims and boss questions, cost check for function usage.
