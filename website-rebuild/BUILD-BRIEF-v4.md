# Build brief: Reput8ion Dynamics website

**Version:** 4.0
**Date:** 17 July 2026
**Owner:** James Dunny
**Supersedes:** v1.0, v2.0, v3.0, v3.1. This document is complete and standalone. Ignore all earlier versions.
**Purpose:** a specification for building a full working site. Written as a single input for a build agent. Read all of it before writing any code or copy.

---

## 1. What this site is

A **confirmation asset**, not an acquisition asset.

Almost nobody lands here cold. Visitors arrive warm: referred by a board member, a communications director, a fellow chair, or a journalist. They already have the name and they already have a problem. They come to answer two questions:

1. Are they right for this specific problem?
2. Will I look sensible bringing this name to my chair?

Every element must serve one of those two. Anything that serves neither is cut.

**The visitor.** A chair, CEO, company secretary, corporate affairs lead or communications director at a mid-to-large organisation, usually Irish or UK. Often under time pressure. Reading on a phone. Pattern-matching, not browsing. Under three minutes on first visit.

**What this is not.** Not a lead-generation funnel. No SEO content programme, no gated downloads, no newsletter capture, no chatbot, no pricing page.

**Success test.** The referred conversation is warmer after the visit than before it. There is no analytics goal.

---

## 2. The positioning correction

**The most important section in this brief. Read it before writing a word of copy.**

The current site sells crisis. The actual work is issues management, narrative development, communications training, corporate strategy, reputation counsel and leadership positioning. Crisis matters but it is a small share of the revenue.

That mismatch costs twice. It advertises for work that does not come. And it makes the work that does come look like an afterthought.

**The correction: crisis is the credential, not the service line.**

Thirty years of it, including Head of Crisis Management EMEA at FleishmanHillard and External Communications Director at Kerry Group, is *why* a chair takes the call about a narrative problem or a training programme. It is not what they are buying. It is the evidence that the judgement has been tested.

Most consultancies do this the wrong way round: they sell the range and bury the pressure-tested judgement. This site sells the range and leads with the fact that it is delivered by people who have been in the room when it went wrong.

**Copy implication.** Crisis appears in the credential line and on the About page. It gets one problem entry, no more. The other four or five are the work that actually pays.

**The consequence to accept.** First person plural, client logos and a broad service range are each defensible, and together they describe the site that already exists. All three are confirmed. So the differentiation must be carried entirely by two things: **how the problems are framed, and the Notes.** There is nowhere else for it to live. Both must be excellent or the site is generic. This is not a design problem and no build agent can fix it.

---

## 3. Audit of the existing site

### 3.1 Carry over unaltered

| Asset | Value |
|---|---|
| Tagline | Senior counsel for leaders when reputation is on the line |
| Email | james@reput8ion.ie |
| Phone | +353 86 388 3903 |
| LinkedIn | linkedin.com/company/reput8iondynamics |
| Voice | First person plural. "We", "the practice" |

### 3.2 Carry over and sharpen

**Radical Clarity** is the strongest page on the current site and the only one already in the correct register. It opens with a problem, not a service:

> Most organisations don't have a communication problem. They have a clarity problem.

> The leadership team has a strategy. But ask them individually what the organisation stands for, why it makes the decisions it makes, or how they'd explain the business to a sceptical stakeholder, and you get five different answers.

That is the model for every problem entry on the new site. Radical Clarity keeps its name, its three-stage shape (workshop, focused refinement, narrative delivery) and its own page as one of the entries.

**Two lines worth keeping, cut of their em dashes:**

> Reputation is built over years and lost in moments. The difference is the quality of counsel you have in the room.

> Good communications counsel is not about managing messages. It is about managing reality, and helping leaders understand the difference.

**Two of the six principles survive.** Deployment-ready ("we do not produce reports that sit on shelves") and Senior access ("the level of counsel you need is the level you receive"). The other four are throat-clearing. Fold the surviving two into /about as prose. Do not carry the numbered grid.

**The AI use policy** carries over as a linked page. It is a discretion signal and it is unusual. It does not count against the page limit.

### 3.3 Fix

**The Kerry Group title.** The site and the PRII bio say **External Communications Director, Kerry Group**. Other material says Head of Communications. One is wrong on a page a chair will read. **Open: James to confirm and use it consistently.**

**FleishmanHillard is missing from the site.** Head of Crisis Management, EMEA is the credential that underwrites everything else. It goes above the fold.

**The service grid is crisis-first and range-second.** Invert it. See section 2.

### 3.4 Leave behind

The six-service grid as currently written. "Reputation is your most valuable asset." The stat strip ("30+ YEARS OF EXPERIENCE", "CRISIS READY. ALWAYS"). The word "INSIGHTS". The Wix hero image. The logo carousel format. Every instance of stock imagery.

---

## 4. Image inventory: fixed and closed

**There is no photoshoot. There is no budget and no time for one, and the inventory does not need it.**

The site is **type-led with two photographs**, used large and used once each. One image used with conviction reads as confidence. Six reads as a gallery. This is the specification, not a compromise.

### 4.1 The two frames

Both are supplied, graded to black and white, and sitting in `/images`.

| File | Source | Use | Status |
|---|---|---|---|
| `jd-portrait.jpg` / `.webp` | `IMG-20250424-WA0023.jpg` | **Home, above the fold.** Full-bleed, once | Graded. **Resolution flagged, see 4.2** |
| `jd-speaking.jpg` / `.webp` | `3RII_Conf_JD_2.jpg`, cropped from a 5400x3600 original | **One problem entry** (training or narrative). Not the home page | Graded and cropped. Ready |

**Why the portrait works.** Available light. Herringbone jacket, dark shirt. Not smiling. Turned slightly off-camera. Real space in the frame and natural falloff on the wall behind. It is editorial, not corporate, and nobody would guess it was not commissioned. It carries the home page on its own.

**Why the speaking frame works cropped.** Full frame it is four people under blue stage gels with James as furniture on the right. Cropped tight and graded, the blue disappears and it reads as a credible conference frame. The original is 5400x3600 so the crop costs nothing.

### 4.2 The one blocking action

**`IMG-20250424-WA0023.jpg` is a WhatsApp export.** 2048x1365 at 229KB. It has been through platform compression. Run full-bleed on a retina screen it will show.

**Action: James to get the original file from whoever took it. One message. Highest-value action on this project.** If the original is unavailable, cap the portrait's display width so the compression does not show, and accept it. Do not upscale it and do not run it through an AI enhancer.

### 4.3 Rejected, with reasons

Do not use these. They are listed so nobody re-litigates them.

| File | Why not |
|---|---|
| `PRII_Conf_JD_2.jpg` | Same moment as the speaking frame, wider, with bottles and chair backs in the foreground. Redundant |
| `ConversationsFest24_1.jpeg` | 1280px phone shot. Good room, but polo shirt and trainers, looking at someone else. Wrong register |
| `IMG_9443_v2__2_.webp` | The current site portrait. Rotated, blown-out window, grey wall, smiling at camera. This is the corporate register the brief exists to avoid. **Retire it** |
| `JD_headshot_v2.png` | 249x249. Favicon derivation or nothing |

### 4.4 Absolute image rules

- **No stock. Ever.** No handshakes, glass towers, chess pieces, lighthouses, compasses, icebergs, aerial city shots, or a diverse team in a bright meeting room. One stock image undoes every other decision in this brief
- **No AI-generated imagery.** James argues publicly that judgement is the scarce resource and that AI exposes people who were bluffing. A synthetic photograph on this site is not a shortcut, it is a story
- **No abstract shapes, gradients, colour fields, illustration, icon sets or geometric decoration**
- Client logos are the only other images on the site. See section 5

### 4.5 Treatment and presentation

- **Black and white, one grade, both frames.** Applied. It removes a hundred small decisions, it reads as serious, and it stops the teal fighting the photography. Mixed treatment is the failure mode
- Large, generous, uncropped where possible
- Full-bleed on the home page only, and once
- **Never as a background with text laid over it.** Text sits beside or beneath an image, never on top
- No hover effects, no zoom, no reveal animation, no lightbox, no captions

---

## 5. Client logos and endorsements

Confirmed in. They carry credibility and the client base earns it. Two rules make them work rather than decorate.

**Logos.**

- A static grid, not a carousel. Carousels signal that the list is too short to stand still
- Greyscale, uniform optical weight, generous spacing. Consistent with the photography treatment. They are evidence, not a sponsor wall
- Home page and nowhere else. Do not repeat them in the footer
- **Permission clearance required, client by client, before any logo goes live.** This is a professional exposure, not a design decision. Any client where the engagement was sensitive, or where the contract is silent on publicity, comes off the grid regardless of how good it looks
- Where a name cannot be used, it is not replaced with "a leading Irish plc". Silent omission only
- Enterprise Ireland is on the current site and is available: `static.wixstatic.com/media/38a989_3f9a2b3778b04cf284552dd2bceddcce~mv2.png`

**Endorsements.**

- Three maximum. Ten is a wall of noise and reads as insecurity
- Named, titled, attributed. An anonymous endorsement is worth less than none
- They must praise **judgement under pressure or a specific outcome**, not niceness, responsiveness or being a pleasure to work with. An endorsement that could describe any supplier actively lowers the register
- **Action: James to source three. The ask is: "What was the call I made that you would not have made?"** Do not accept the generic answer
- Placement: one on home, the others on /about or against the relevant problem entry. Never a carousel

**The discretion line still applies.** Some work is not published and the site says so in one sentence. Visible logos and stated discretion coexist if the sentence is honest: named clients where permitted, silence where not.

---

## 6. Voice

**Tagline, exact:** Senior counsel for leaders when reputation is on the line

**Person.** First person plural. "We", "the practice". Consistent throughout.

**Register.** Calm, unimpressed, specific. Someone who has been in the room and is not selling. Authority is demonstrated through how a problem is framed, never asserted. Humble but confident: confidence comes from scale and restraint, not volume.

**Copy rules, everywhere including microcopy, buttons, meta descriptions and alt text:**

- UK spelling
- No Oxford comma
- No em dashes. The current site is full of them. Strip every one
- Active voice. Short sentences by default, longer only on purpose
- Dates UK style: 17 July 2026
- Hyphenate compound modifiers

**Banned on sight.** "Comprehensive communications support", "tailored solutions", "we partner with organisations to", "leveraging our experience", "best-in-class", "world-class", "sector-leading", "our team of experts", "we are passionate about", "proactive strategic communications", "in today's competitive landscape", "unlock", "reach out", "bespoke to the situation", "trusted adviser".

**Test for every sentence.** Could a competitor put their name on this? If yes, cut it. With "we", logos and a broad range on the page, this test is the entire defence against genericism. Apply it ruthlessly.

---

## 7. Site architecture

```
/                    Home
/problems            Five to six problem-shaped entry points
/problems/{slug}     Individual entry (Radical Clarity is one)
/about               The practice and James
/notes               Published thinking (index)
/notes/{slug}        Individual pieces
/contact             Contact
/ai-use              AI use policy (footer link only)
```

No services page. No case studies page. No team page.

**Navigation.** Four items, text only, no dropdowns. Order: Problems, About, Notes, Contact. Wordmark returns home.

---

## 8. Page specifications

### 8.1 Home

**Above the fold:**

- `jd-portrait`, full-bleed, black and white. The only full-bleed image on the site
- Positioning statement, set beside or beneath the image, never on it. Names what the practice fixes, for whom, when it matters. It must cover the actual range, not just crisis. Specific enough that the wrong buyer self-selects out. **Written by James, not the build agent**
- The tagline
- One line of hard credential, no adjectives: 30 years. External Communications Director, Kerry Group. Head of Crisis Management EMEA, FleishmanHillard. Fellow of the PRII

**Below the fold, in order:**

1. **The problems block.** Five to six problem statements in the visitor's own language, linking through. The primary navigation of the site. Weighted to the actual work
2. **Client logos.** Static grid, greyscale, permission-cleared
3. **One endorsement.** Named, titled, about judgement
4. **Latest note.** Title, date, one line, link. The currency signal. Over eight weeks old and it is doing damage
5. **Discretion line.** One sentence
6. **Contact.** Direct, above the footer

**Do not include:** carousels, animated counters, stat strips, icon grids, mission statement, video.

### 8.2 Problems

Five to six entries, identically structured. Each gets its own page.

- **The problem, in their words.** One sentence, the language a chair or corporate affairs director would actually use
- **Why it goes wrong.** Two or three sentences naming the default move and why the default move is wrong. This is where judgement is demonstrated. **The most important copy on the site**
- **What the engagement looks like.** Shape, not a menu. What happens, over what period, what the client is left holding
- **Optional:** one endorsement or one anonymised case note

**Coverage required, weighted to real revenue:**

| Entry | Underlying work |
|---|---|
| Radical Clarity | Narrative development, leadership alignment |
| A live issue with a long fuse | Issues management |
| Senior people who cannot land the message | Communications training, leadership positioning. `jd-speaking` sits here |
| The story has not kept pace with the strategy | Corporate strategy, narrative |
| The board and the executive are not saying the same thing | Reputation counsel, governance |
| A journalist has the story and we have four hours | Crisis. One entry only |

Titles above are placeholders showing register. **James writes the real ones.**

No prices, no fixed durations, no deliverable bullet lists that read as a proposal.

Case notes are framed as a **decision under pressure**: situation, choice, reasoning, consequence. Two hundred words maximum. Permission or anonymisation required.

### 8.3 About

Purpose: the boardroom test.

- Opens with the strongest fact, not a story
- Career as evidence, not chronology. Kerry Group and the post-divestment repositioning. FleishmanHillard EMEA. Nearly 30 years at senior practitioner level. Fellow of the PRII, elected February 2026
- States the range plainly and states that crisis experience is what underwrites the rest
- Every engagement is led directly by James, with specialist associates where the situation requires. Say it once, plainly
- Absorbs the two surviving principles as prose: deployment-ready output, senior access
- **No photograph.** The portrait is spent on the home page. Repeating it here halves its effect and there is no second portrait worth using
- No values section, no principles grid, no origin story

Length: 500 to 700 words.

### 8.4 Notes (index)

**Naming.** The section is called **Notes**. Never "Blog", never "Insights".

- Reverse chronological, single stream, no pagination for the first fifty pieces
- Each entry: date, title, one line of standfirst. Nothing else
- No cards, no thumbnails, no read-time, no tags, no byline, no share counts, no featured slot
- Text-dense reads senior. Visual reads agency
- No images in this section at all. The type carries it

**Two tiers, one stream.** Long pieces of 800 to 1,200 words carry authority. Short notes of around 300 words carry currency cheaply. Distinguished by length alone. No separate section, no labels, no filters.

**Dates visible and prominent.** Owning the date is the only reason the section works.

**Range.** The Notes must cover the actual practice, not just crisis. If every piece is about a crisis, the site has re-committed the error section 2 exists to fix.

### 8.5 Notes (individual)

- Full piece, one page. No pagination, no gating, no truncation
- Measure 60 to 75 characters. Generous line height. Readable on a phone at 22:00 by someone over fifty
- Date under the title
- Foot: one line pointing to contact. Not a signup box, not related posts, not a share bar
- **No comments.** An unanswered comment on a reputation piece is a surface with no upside
- RSS feed. Journalists still use it

### 8.6 Contact

- Direct email as visible text: james@reput8ion.ie
- Phone as visible text, `tel:` link on mobile: +353 86 388 3903
- A form may exist as a secondary option. Never the only option, never above the direct routes, three fields maximum
- One line setting response expectation, and stick to it
- Dublin and Kildare base. No office photograph, no map embed

---

## 9. Design direction

**The rule:** the site is carried by typography and two photographs. Nothing else.

### 9.1 Typography

With two images across seven pages, the type is the design. It has to hold.

- Serif for body. High-quality, not a system fallback. Self-hosted, two weights, subset
- A distinct display face or a heavier cut of the body serif for headings. Real hierarchy, real size contrast
- Body no smaller than 18px. Measure 60 to 75 characters
- Set large and confident. Timid type on a site with almost no imagery reads as apology

### 9.2 Colour

- Primary accent: `#0CC0DF`
- Deep teal: `#098DA3`
- Teal green: `#359781`
- Dark forest teal: `#1B4C41`

Colour is a functional accent, not a design element. Links, rules, the wordmark. Nothing else. No coloured panels, no tinted sections, no gradients. With black and white photography, the accent is the only colour on the page and it appears rarely. Ignore any additional ramps in the Wix theme.

### 9.3 Layout

Generous white space. Single column for all prose. Images break the column, text does not.

No parallax, no scroll-triggered animation, no cards, no shadowed containers, no rounded-corner panels, no dividers beyond a single hairline rule.

### 9.4 The trade-off to accept

A type-led site with one strong photograph puts every sentence on display. There is nothing for weak copy to hide behind. If the copy in section 8 is not finished to standard, the site will look empty rather than confident. The writing is load-bearing.

---

## 10. Technical specification

**Stack.** Astro, TypeScript, content collections. Static output, no client-side framework, no runtime JavaScript except where genuinely required. This is a text site and it ships as HTML.

**Rationale:** markdown-backed content collections, zero-JS by default, native RSS, trivial to host. The Notes workflow becomes writing a file, which is the only workflow that will be sustained.

**Repo structure:**

```
/
├── src/
│   ├── pages/
│   │   ├── index.astro
│   │   ├── about.astro
│   │   ├── contact.astro
│   │   ├── ai-use.astro
│   │   ├── rss.xml.ts
│   │   ├── problems/
│   │   │   ├── index.astro
│   │   │   └── [slug].astro
│   │   └── notes/
│   │       ├── index.astro
│   │       └── [slug].astro
│   ├── content/
│   │   ├── config.ts
│   │   ├── notes/
│   │   ├── problems/
│   │   └── endorsements/
│   ├── data/
│   │   └── clients.json      # logo grid, `cleared` boolean per entry
│   ├── components/
│   ├── layouts/
│   └── styles/
├── public/images/
│   ├── jd-portrait.jpg / .webp
│   ├── jd-speaking.jpg / .webp
│   ├── wordmark.svg
│   └── logos/
└── astro.config.mjs
```

**Notes schema:**

```ts
{ title: string, date: Date, standfirst: string, draft: boolean }
```

No tags, no category, no author, no image, no featured flag. If the schema tempts expansion later, that is the schema doing its job.

**Problems schema:**

```ts
{ title: string, order: number, summary: string }
```

**Endorsements schema:**

```ts
{ quote: string, name: string, title: string, organisation: string, placement: 'home' | 'about' | string }
```

**Clients data.** Each entry carries `cleared: boolean`. **The build must exclude any logo where `cleared` is false.** A hard filter, not a warning. This prevents an uncleared logo shipping because nobody re-read the file.

**Images.** Serve webp with jpg fallback. Do not upscale `jd-portrait`. Set a max display width that respects its true resolution until the original is sourced.

**Hosting.** Netlify or Cloudflare Pages, GitHub repo, deploy on push to main. Keep Wix live until sign-off, then switch DNS on reput8ion.ie.

**Analytics.** Plausible or nothing. No Google Analytics, no pixels, no session recording. The traffic is a handful of qualified people and there is nothing to optimise.

**Performance.** Lighthouse 100 across the board. First contentful paint under one second on 4G.

**Accessibility.** WCAG AA minimum on contrast. The buyer is over fifty and reading on a phone.

**Redirects.** `/services` and `/radical-clarity` to `/problems`. `/blog` to `/notes`. `/blog/{slug}` to `/notes/{slug}` where a piece is carried over.

---

## 11. Model routing

**The rule: judgement work goes to the top tier, production work does not.** The copy is the product.

| Element | Model | Why |
|---|---|---|
| Positioning statement, problem titles, "why it goes wrong" copy | **James, unaided** | This is the site. A model produces competent generic and you will not notice until a chair reads it |
| Adversarial critique of James's drafts | **Fable / Mythos tier** | Ask it to break the copy against the register rules, not to praise it |
| About page, discretion line, microcopy | **Opus** | Voice matching, James editing |
| Architecture, schemas, redirect mapping | **Opus** | Structural judgement, once |
| Astro scaffolding, components, layouts, build config, RSS, deploy | **Sonnet** | Production. Do not spend top tier here |
| Image pipeline, subsetting, logo processing | **Sonnet or a script** | Mechanical |
| Final anti-AI-pattern pass across every string on the site | **Fable / Mythos tier** | Highest sensitivity to register failure. Run last, whole site, one pass |

**Do not let any model translate the existing service grid into problem entries.** That is exactly the task a model does plausibly and wrongly.

---

## 12. Content inventory required at launch

| Item | Quantity | Owner | Status |
|---|---|---|---|
| Positioning statement | 1 | James | To write |
| Problem entries, full copy | 5 to 6 | James | To write. Radical Clarity is one |
| Case notes | 2 to 3 | James | To write |
| About copy | 1 | James, Opus assist | To write |
| Notes, publication-ready | 3 | James | To write and bank |
| Discretion statement | 1 | James | To write |
| Client logos, permission-cleared | TBC | James | To clear, client by client |
| Endorsements, named and specific | 3 | James | To source |
| `jd-portrait` original, uncompressed | 1 | James | **One message. Do it first** |
| Photography | 2 frames | Closed | Done. Graded and supplied |
| Kerry Group title confirmed | 1 | James | Open |

**Actions:**

- James to source the original portrait file. One message, highest value, do it today
- James to draft the positioning statement and problem entries before build starts. The build agent must not invent them
- James to clear every logo individually before any goes into `clients.json` as `cleared: true`
- James to bank three notes before launch. Never publish from zero inventory
- Cut every piece by twenty per cent before it goes live
- Set the switch-over date before the first commit

---

## 13. Non-negotiables

The build agent may not add any of the following, regardless of convention or best practice:

Comments. Newsletter signup. Testimonial carousel. Logo carousel. Uncleared client logos. Anonymous endorsements. Stock photography. AI-generated imagery. A third photograph. Abstract shapes, gradients or colour fields. Icon sets. Chatbot. Social share buttons. Read-time estimates. Category taxonomy on Notes. A services page. Pricing. Any page beyond those specified. The word "Insights". Text laid over a photograph.

---

## 14. Known risks

**Genericism.** First person plural, logos and a broad service range describe the site that already exists. The only remaining differentiators are the problem framing and the Notes. If either is average, the rebuild has bought nothing but a faster page load. This is the primary risk and it is a writing risk, not a build risk.

**The Notes fail silently and visibly.** A live section converts the strongest asset, currency, into the biggest liability, visible neglect. A three-month gap reads as "he got busy or he got quiet". Both are bad. Mitigation: two-tier structure, three banked before launch, and harvest rather than invent. Every client engagement and board session is a piece with the specifics stripped out. This is declassification, not content generation.

**An uncleared logo ships.** Reputational exposure on a reputation practice's own site. Mitigated by the hard `cleared` filter, but the filter only works if the flag is honest.

**Generic endorsements.** Three quotes about being a pleasure to work with will do more damage than no endorsements at all. If the specific ones cannot be sourced, ship none.

**The portrait is compressed.** It is the single image carrying the home page and it came through WhatsApp. If the original cannot be found, the site is capped at a display size that hides it. Acceptable but not ideal.

**The migration stalls at 90 per cent.** A clean build has no client waiting and no deadline. Set a switch-over date before the first commit and treat it as a client date.

---

## 15. Definition of done

- The specified pages and no others
- Every non-negotiable in section 13 absent
- Exactly two photographs on the whole site
- Three notes live, dated within the last six weeks, covering the range and not only crisis
- Zero em dashes, zero Oxford commas, zero US spellings, zero voice-killer phrases across every string including meta tags and alt text
- Every logo in the grid individually cleared
- Every endorsement named and about judgement
- Lighthouse 100 across the board
- Old URLs redirect
- The home page answers "are they right for my problem" without scrolling twice
- A chair finds the phone number in under ten seconds
- Read the whole site once on a phone, at night, as a stranger. If any sentence could belong to another consultancy, rewrite it
