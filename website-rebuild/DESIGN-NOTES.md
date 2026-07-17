# Design revision v3, 17 July 2026: cinematic

James pushed further: "more dynamic - with strong visuals. Think a
production company." He approved, by direct choice, the full cinematic
hero with the headline set over the darkened portrait, breaking brief
section 13's text-over-photograph ban, and full CSS motion.

## v3 changes

- Full-viewport hero: the portrait fills the first screen under a dark
  scrim with the headline, tagline and credential line set over it
- Practice-area ticker strip under the hero, pure CSS marquee
- Scroll reveals on sections and rows via CSS scroll-driven animations,
  no JavaScript, off automatically for reduced-motion users
- Navigation fixed over the imagery, transparent at the top of the page
  and condensing to dark glass on scroll
- Problem entries as full-width rows that invert to dark on hover, with
  outlined numerals
- Giant ghosted numerals and letters behind section headings, and an
  outlined display wordmark across the footer
- The speaking frame runs full-bleed at up to 72vh on the training entry
- Both photographs carry a consistent cold teal cast applied in CSS

## Additional brief deviations in v3, all James-approved

| Brief rule | Status |
|---|---|
| Text never laid over a photograph (section 13) | Broken deliberately in the hero, at James's explicit choice |
| No scroll-triggered animation (section 9.3) | Scroll reveals and the ticker added. Reduced-motion users see a still page |
| Images uncropped, never as background (section 4.5) | The hero and the speaking band crop with object-fit cover |
| Black and white, one grade (section 4.5) | A uniform teal cast now sits over both frames |

Still honoured: exactly two photographs, no stock, no AI imagery, zero
client-side JavaScript, the copy register, placeholder gating and every
structural rule.

---

# Design revision v2, 17 July 2026

James reviewed the first build and rejected the minimal treatment as too
basic. This revision moves the site to a darker, more finished editorial
design: advance, sleek, slick and professional was the direction.

## What changed

- Dark bands: hero, page headers, the contact block and the footer sit on
  near-black with the photography and cyan accent doing the work
- Sticky navigation with a blurred dark bar and uppercase interface type
- Inter added as a second family for interface details only: nav, eyebrow
  labels, numbering, metadata, buttons. All reading text stays Source Serif 4
- Numbered sections and problem entries (01 to 06) with hover motion on
  arrows and rows
- The portrait sits beside the headline in the hero inside a hairline frame.
  The speaking frame sits sticky beside the training entry
- Larger type scale throughout, tighter leading on display sizes

## Deviations from brief v4, accepted by James's direction

The brief (sections 9 and 13) called for white pages, no dark panels, no
gradients, no animation and a single serif. This revision breaks those
rules deliberately:

| Brief rule | Status now |
|---|---|
| No coloured panels or tinted sections | Dark bands and one whisper-grey tint band |
| No gradients | One near-invisible dark-on-dark gradient in the hero band |
| No scroll or hover animation | Restrained hover transitions on links, rows and arrows. No scroll animation, and reduced-motion preferences disable all of it |
| Serif only | Inter carries interface details. Reading text unchanged |
| Text never over an image | Still honoured. Text sits beside images, never on them |
| Two photographs only | Still honoured |
| Colour as functional accent | Loosened. Cyan and teal now also carry numbering and eyebrow labels |

Everything else stands: the architecture, the schemas, the copy rules, the
placeholder gating, the cleared-logo filter, the redirects and the launch
gate are unchanged. If the brief is to remain the contract, section 9
should be revised to match this direction before launch sign-off.
