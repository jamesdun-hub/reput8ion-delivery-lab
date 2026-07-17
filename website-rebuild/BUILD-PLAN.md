# Build plan: Reput8ion Dynamics website

**Date:** 17 July 2026
**Source:** BUILD-BRIEF-v4.md (in this folder). The brief is the contract. Where this plan and the brief disagree, the brief wins.
**Status:** Planning complete. Build not started.

---

## 1. Reading of the brief

The brief has been read in full. The plan below accepts every constraint in it, in particular:

- The site is a confirmation asset for warm, referred visitors. Two questions to answer: are they right for this problem, and will I look sensible bringing this name to my chair.
- Crisis is the credential, not the service line. One crisis entry only. The range leads.
- The differentiation lives entirely in the problem framing and the Notes. Neither can be written by a build agent. **This plan does not schedule any model to draft the positioning statement, the problem titles or the "why it goes wrong" copy.** Those are James, unaided, per section 11.
- Two photographs on the whole site. Type carries everything else.
- Every non-negotiable in section 13 is treated as a build-time check, not a style preference.

### Verification done during planning

Both supplied frames were inspected:

| File | Measured | Matches brief | Note |
|---|---|---|---|
| `jd-portrait.jpg` | 2048x1365, 268KB | Yes, the WhatsApp export flagged in 4.2 | Editorial, off-camera, herringbone, natural falloff. Carries the home page. Original still needed |
| `jd-speaking.jpg` | 1262x1600, 308KB | Cropped and graded as described | Credible conference frame. The crop is 1262px wide, not a fresh cut from the 5400x3600 original. Fine at its intended column width. If it is ever wanted larger, re-crop from the original rather than upscale |

The delivered speaking crop retains a sliver of the adjacent panellist and the mic stand. The brief marks it ready, so it ships as supplied. No re-crop is scheduled.

### One inconsistency to note

This repo is the Delivery Lab, a separate product. The website is a fresh Astro project and should live in its own repository (working name `reput8ion-website`), wired to Netlify or Cloudflare Pages with deploy on push to main, per section 10. This folder holds the plan, the brief and the graded frames so any build session can start from one place.

---

## 2. Gates: what blocks what

The build splits cleanly into work that can start today and work that is gated on inputs only James can supply. The scaffold must never absorb invented copy to feel finished. Placeholders are marked, ugly and impossible to ship by accident.

### Gate A: blocks launch, does not block the scaffold

| Input | Owner | Brief ref |
|---|---|---|
| Positioning statement | James, unaided | 8.1, 11 |
| Five to six problem entries, full copy, real titles | James, unaided | 8.2, 11 |
| Two to three case notes, cleared or anonymised | James | 8.2 |
| About copy | James with Opus assist | 8.3, 11 |
| Three banked notes covering the range, not only crisis | James | 8.4, 12 |
| Discretion line | James with Opus assist | 5, 8.1 |
| Three endorsements, named, about judgement | James | 5 |
| Logo clearances, client by client | James | 5 |

### Gate B: blocks specific build steps

| Input | Blocks | Fallback if unavailable |
|---|---|---|
| Original uncompressed portrait | Full-bleed hero at retina sizes | Cap display width so the 2048px export never renders above its true resolution. Accept it. No upscaling, no AI enhancement |
| Kerry Group title confirmed (External Communications Director vs Head of Communications) | Credential line on home, About copy, meta descriptions | None. It appears on pages a chair will read. Must be confirmed before any page carrying it goes live |
| Switch-over date | Nothing technically, everything practically | Set before the first commit of the site repo, per section 12. A clean build with no deadline stalls at 90 per cent |

### Gate C: blocks nothing, decided in this plan

Typeface, component inventory, redirect map, build order. All below.

---

## 3. Build phases

### Phase 0: pre-build (James, this week)

1. Send the one message asking for the original portrait file. Highest-value action on the project.
2. Confirm the Kerry Group title.
3. Set the switch-over date and treat it as a client date.
4. Create the `reput8ion-website` repository and the Netlify or Cloudflare Pages project against it.
5. Begin logo clearance and the three endorsement asks in parallel. The ask, verbatim from the brief: "What was the call I made that you would not have made?"

### Phase 1: scaffold (Sonnet tier, one session)

Astro, TypeScript, content collections, static output, zero client-side JavaScript. Repo structure exactly as section 10 specifies. Deliverables:

- Project init with `astro.config.mjs`, strict TypeScript, no UI framework integrations.
- Content collections and schemas, verbatim from the brief:
  - Notes: `{ title: string, date: Date, standfirst: string, draft: boolean }`
  - Problems: `{ title: string, order: number, summary: string }`
  - Endorsements: `{ quote: string, name: string, title: string, organisation: string, placement: 'home' | 'about' | string }`
- `src/data/clients.json` with `cleared: boolean` per entry. The logo grid component filters on `cleared === true` as a hard filter in the build. Additionally a build-time assertion fails the deploy if any rendered logo lacks `cleared: true`, so the filter cannot be refactored away silently.
- Routes: `/`, `/problems`, `/problems/[slug]`, `/about`, `/notes`, `/notes/[slug]`, `/contact`, `/ai-use`, `rss.xml`. No others. No 404 content beyond a one-line page pointing home.
- RSS via `@astrojs/rss`, full standfirst in the description, absolute URLs.
- Redirects (host-level config, plus `<meta http-equiv>` fallback pages only if the host config cannot express them):
  - `/services` → `/problems`
  - `/radical-clarity` → `/problems`
  - `/blog` → `/notes`
  - `/blog/{slug}` → `/notes/{slug}` for carried-over pieces, mapped individually once the carry-over list exists
- Sitemap and robots.txt. Meta descriptions left as marked placeholders for the copy phase.

### Phase 2: design system (Sonnet tier, one session)

**Typography.** The type is the design, so this is the one aesthetic decision that matters. Recommendation: **Source Serif 4** self-hosted, woff2, subset to Latin, two weights (regular for body, semibold or bold for headings), with its optical-size axis used to get a display cut for headings from the same family. It is high quality, free to self-host and has genuine display presence at large sizes. Alternatives if James dislikes it on sight: Newsreader or Spectral. One family, two files, no system fallback doing the real work.

- Body 18px minimum, larger on desktop. Measure 60 to 75 characters everywhere prose runs.
- Headings set large. Real size contrast between levels. No timidity.

**Colour.** Tokens for `#0CC0DF`, `#098DA3`, `#359781`, `#1B4C41`. Used for links, hairline rules and the wordmark only. Body text near-black on white. Contrast checked against WCAG AA at the actual sizes used, noting `#0CC0DF` on white fails AA for text and is therefore reserved for the wordmark and non-text accents, with the deeper teals carrying links.

**Layout.** Single column for all prose, generous white space, images break the column. One hairline rule style. Nothing else: no cards, shadows, rounded panels, parallax or scroll animation.

**Components** (deliberately few):

| Component | Notes |
|---|---|
| `BaseLayout` | Head, fonts, nav, footer, skip link |
| `Nav` | Four text items: Problems, About, Notes, Contact. Wordmark returns home. No dropdowns |
| `Footer` | Contact line, LinkedIn, AI use policy link. No logos, no social icons |
| `Hero` | Portrait full-bleed with text beside or beneath, never on top. Width-capped until the original arrives |
| `ProblemsList` | The primary navigation of the site |
| `LogoGrid` | Static, greyscale, uniform optical weight, cleared-only |
| `Endorsement` | Single quote, name, title, organisation. Never a carousel |
| `LatestNote` | Title, date, one line, link |
| `NoteList` / `NoteEntry` | Date, title, standfirst. Nothing else |
| `Prose` | Measure, line height, note typography |

**Wordmark.** Carry the existing wordmark over as SVG. Favicon derived from `JD_headshot_v2.png` (249px) or a type-based mark, whichever reads at 16px.

### Phase 3: images (script, same session as Phase 2)

- Generate webp with jpg fallback for both frames at the exact display widths the layout needs, `srcset` capped at 2048 for the portrait until the original arrives. No upscaling.
- Logo pipeline: normalise to greyscale, trim, equalise optical weight, output as SVG where sources allow or high-density PNG where not.
- Alt text written in the copy phase, held to the same voice rules.

### Phase 4: content drop-in (James plus Opus for About and microcopy)

- James's copy lands in the content collections as markdown files. No model touches the positioning statement, problem titles or "why it goes wrong" sections beyond adversarial critique.
- Radical Clarity carries over with its name, its three-stage shape and its existing opening, em dashes stripped.
- The two surviving principles (deployment-ready, senior access) folded into About as prose.
- The two kept lines placed, cut of their em dashes.
- The AI use policy carried over to `/ai-use`, linked from the footer only.
- Meta descriptions and alt text written last, same register, same bans.

### Phase 5: adversarial pass (Fable/Mythos tier, one pass, whole site)

Run once, after all strings exist, against every string in the build output including meta tags and alt text:

- Zero em dashes, zero Oxford commas, zero US spellings.
- Every phrase on the banned list absent.
- The competitor test on every sentence: if another consultancy could sign it, it goes back to James flagged, not rewritten silently.
- Confirm the Notes range covers the practice, not only crisis.

A small script greps the built HTML for em dashes, the banned phrases, "Insights" and known US spellings as a deploy-blocking check, so regressions cannot ship after launch either.

### Phase 6: QA against the definition of done

- Lighthouse 100 across performance, accessibility, best practices and SEO. FCP under one second on throttled 4G.
- WCAG AA contrast minimum, verified with tooling and by eye.
- Exactly two photographs in the shipped output, counted mechanically.
- Old URLs redirect, tested against the live Wix URL list.
- The phone number reachable in under ten seconds from landing, `tel:` link on mobile.
- Home page answers "are they right for my problem" within two screens on a phone.
- The stranger test: the whole site read once on a phone at night. Any sentence that could belong to another consultancy gets rewritten before switch-over.

### Phase 7: launch

1. Deploy to production URL on the host, Wix untouched.
2. James signs off against the section 15 checklist, item by item.
3. DNS switches on reput8ion.ie. Wix retained dark for a fortnight, then closed.
4. Plausible added, or nothing. No Google Analytics, no pixels.
5. RSS URL checked from a feed reader.

---

## 4. Estimated effort

| Phase | Sessions | Tier |
|---|---|---|
| 1 Scaffold | 1 | Sonnet |
| 2 Design system | 1 | Sonnet |
| 3 Images | with Phase 2 | Script |
| 4 Content drop-in | 1, after Gate A | Opus assist |
| 5 Adversarial pass | 1 | Fable/Mythos |
| 6 QA | 1 | Sonnet |

The build itself is roughly four to five working sessions. The schedule is set by Gate A, the writing, not by the build. That matches the brief's own risk assessment: this is a writing risk, not a build risk.

---

## 5. Risks carried into the build, with build-side mitigations

| Risk (brief section 14) | Build-side mitigation |
|---|---|
| Genericism | The build never drafts gated copy. Placeholders are visibly unfinished. The adversarial pass flags rather than rewrites |
| Notes fail visibly | Latest-note block shows the date prominently, so staleness is visible to James before it is visible to a chair. Three banked before launch is a launch gate, not advice |
| Uncleared logo ships | Hard `cleared` filter plus a deploy-blocking assertion |
| Generic endorsements | If three specific ones do not exist at launch, the endorsement slots render nothing. Shipping none is the designed fallback |
| Compressed portrait | Width cap in the image pipeline until the original lands, then one config change |
| Migration stalls at 90 per cent | Switch-over date set in Phase 0, before the first commit |

---

## 6. Open items for James

1. The one message: source the original portrait file.
2. Kerry Group title, confirmed once, used everywhere.
3. Switch-over date.
4. Positioning statement and problem entries drafted before Phase 4 is scheduled.
5. Three endorsements sourced with the specific ask.
6. Logo clearances, client by client, honestly flagged in `clients.json`.
7. Three notes banked.
8. Confirm the typeface recommendation, or pick from the two alternatives, on sight of a one-page type specimen the scaffold session will produce.
