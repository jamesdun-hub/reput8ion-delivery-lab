---
title: The Reput8ion Feed
subtitle: Product brief, lean build and content plan
date: 31 July 2026
---

# What prompted this

The Instagram ad James saw is for Deepstash, sold as "TikTok for high IQ people". The pitch: a feed that looks and swipes exactly like TikTok, but every card is one idea from a book, podcast or expert, condensed into 20 seconds. No outrage, no gossip, no noise.

Two things are worth knowing before we copy it. First, the ad itself is a comms confection. Deepstash was founded in Bucharest around 2019, not by Stanford and MIT engineers in 2020, and the "47 books in their first year" figure is unverifiable marketing. The origin-story-plus-secret-knowledge formula clearly works as an ad, which is itself a lesson worth stealing. Second, the product mechanic is real and it works. Deepstash has millions of downloads on the back of one insight: the swipe feed is the most habit-forming content container ever built, and nobody says the ideas inside it have to be junk.

# Could we build it

Yes. The honest version of the answer has two halves.

The mechanic is cheap. A vertical swipe feed of text cards is a solved front-end problem. A working version is days of build, not months, and this repo's delivery lab setup is exactly the environment to do it in.

The library is the real product. Deepstash's moat is not code, it is 200,000 curated idea cards built over six years. We cannot and should not compete with that. What we can do is own a narrow vertical they serve badly: reputation, crisis and leadership communications. Nobody has built the swipe feed for people who run reputations. That niche is ours to take, and 150 good cards is enough to open it.

So the recommendation is not "build a Deepstash competitor". It is "build the Reput8ion Feed: a free, swipeable library of reputation and crisis insight that markets the consultancy every time a card is shared".

# What it would be

**Working title:** The Reput8ion Feed.

**One line:** 20-second insights on reputation, crisis and leadership communications, drawn from real cases, real research and real rooms.

**Who it is for:** CEOs, comms directors, in-house teams, founders and board members. The same people the tagline addresses: senior counsel for leaders when reputation is on the line.

**What it is for us:** a marketing and business development asset, not a consumer app business. Every card carries the Reput8ion mark. Every share on LinkedIn is an ad we did not pay for. The feed demonstrates the thinking instead of asserting it, which is exactly how the brand guidelines say authority should be earned.

**What it is not:** an App Store play, a subscription product or a second job. If it ever earns a native app, traction will tell us. We do not start there.

# Product design

## The card

One idea per card, structured the same way every time:

- **Hook:** one line, ten words or fewer, that earns the next three seconds. "Your first statement is evidence, not PR."
- **The idea:** 40 to 60 words. One insight, argued, not described.
- **So what:** one sentence telling a leader what to do differently.
- **Source:** the case, study, book or "from the room at Reput8ion" attribution.

Readable in 20 seconds. No video needed at launch. Clean typography on brand colours does the job, and it is 50 times cheaper to produce.

## The feed

- Full-screen vertical cards, swipe or scroll-snap to advance, exactly the TikTok grammar.
- Opens instantly in a browser. No app download, no login, no cookie wall for v1.
- Save (stored on the device), share and "next" are the only buttons.
- Topic decks the user can filter to: Crisis, Media, Boardroom, Science, Case Files.

## The share loop

This is the growth engine and it gets designed first, not last. Every card has its own link and its own auto-generated image, so a shared card lands on LinkedIn as a clean branded tile, not a bare URL. One "share to LinkedIn" tap per card. The feed's job is to make our thinking easy to steal with our name attached.

# The lean build

Three phases. Phase 1 is the commitment; the rest is earned.

## Phase 1: the working feed (target: live by end of August 2026)

- **What:** a progressive web app at a Reput8ion subdomain, for example feed.reput8ion.ie. The main site stays on Wix untouched; the feed is a separate, faster thing linked from it.
- **Stack:** Next.js and Tailwind, cards stored as simple markdown or JSON files in this repo, auto-generated share images, deployed on Vercel or Cloudflare Pages. Publishing a card is a git commit; the lab's existing watcher pattern fits this well.
- **Build effort:** two to three days of build in this delivery lab, plus design polish.
- **Cash cost:** effectively nil. Hosting is free at this scale; the domain already exists.
- **Launch content:** 150 cards (see content plan).

Actions: James approves concept and name by 7 August. Delivery lab builds prototype with 20 seed cards by 14 August. James reviews on his phone, one revision round, live by 31 August.

## Phase 2: capture and measure (September to October 2026)

Only after launch, and only what the numbers justify:

- Plausible analytics: swipe depth, saves, shares, top cards.
- Email capture: "get the ten best cards of the month" as a monthly digest, feeding the newsletter and the pipeline.
- Optional accounts via Supabase so saves follow the user across devices.

Actions: review launch numbers w/c 28 September. Add email capture only if weekly users exceed 200.

## Phase 3: native wrapper (2027, if earned)

If the web feed shows real retention, wrap it with Capacitor and ship to the App Store. This is a decision for January 2027 at the earliest, made on data.

> Build estimates assume Claude-assisted development in the delivery lab. A conventional agency quote for the same product would run €15,000 to €30,000.

# Content plan

## Five pillars

1. **Case Files.** What actually happened in named public crises and what the file teaches. The receipts do the arguing.
2. **Crisis craft.** Holding statements, the first hour, apologies, leaks, litigation pressure. The practical mechanics.
3. **Media handling.** How journalists actually work, interview technique, what "off the record" really buys you.
4. **The science.** Findings from published research on trust, apology and reputation recovery, always with the source named. No "studies have shown".
5. **Boardroom.** Governance, leadership visibility, internal comms as the first external audience.

Roughly 30 cards per pillar at launch. Case Files and Crisis craft will earn the most shares; the science pillar earns the authority.

## Production pipeline

- **Source list first.** James nominates the raw material: the case notes, books, reports and hard-won lines from real rooms that deserve cards. Anonymise client material to holding-statement standard.
- **Draft in batches.** Claude drafts cards in batches of 20 against the card template and house style. This is the same pattern as the rest of the lab: machine drafts, James edits.
- **James is the filter.** Nothing publishes without his pass. The bar: would a comms director screenshot this? If not, cut it.
- **Publish through the repo.** Approved cards merge to main and deploy automatically. The content plan lives in git alongside the product.

## Cadence

- **Launch library:** 150 cards. At 20 machine-drafted cards per batch and one editing hour per batch, that is roughly eight hours of James's time spread over three weeks.
- **Steady state:** ten new cards a week, batched into one drafting session. News-reactive cards, a fresh take within 48 hours of a major public crisis, will be the highest-value additions and should jump the queue.
- **Pruning:** kill the bottom 10% of cards by engagement each quarter. A small sharp library beats a big stale one.

## Rights and attribution

We publish ideas in our own words, never extracts. Short quotes only within fair-dealing norms, always attributed. Research cards name the study and authors. Nothing is lifted from Deepstash. Client-derived insights are anonymised past the point of recognition, the same discipline as the exemplar library.

# Distribution

The feed does not market itself. The plan:

- Every Reput8ion LinkedIn post that lands gets a companion card, and every strong card gets posted by James with a one-line setup.
- The monthly digest email doubles as a soft pitch surface.
- Cards go into proposals and training decks as proof of thinking.
- Ask five friendly clients and journalists to road-test the first 150 and say so publicly if they like it.

# Measurement

Judge it on four numbers, reviewed monthly: weekly users, average swipe depth, shares per hundred sessions and inbound enquiries that mention the feed. The last one is the only one that pays invoices. Vanity metrics, downloads and follower counts, do not appear in the review.

# Risks

- **The library goes stale.** The single most likely failure. Every content product dies of neglect, not launch. Mitigation: the ten-a-week cadence is one diarised session, and the pipeline makes drafting nearly free. If James cannot hold one hour a week, do not start.
- **Scope creep.** The temptation to build accounts, video, comments and an app before the content proves itself. Mitigation: the phase gates above are the decision, made once, now.
- **Distinctiveness.** Generic business-wisdom cards would sink it. Mitigation: the "from the room" standard. If a card could appear on Deepstash, it is not specific enough for us.
- **Client confidentiality.** A recognisable anonymised case is a fired client. Mitigation: James signs off every Case File card personally.

# Recommendation

Build it. The mechanic is proven, the niche is empty, the cost is a few days of lab time and eight hours of editing, and the worst case is a branded library of 150 sharp insights we reuse in proposals and posts forever. The upside is an owned channel that demonstrates the firm's thinking daily. That asymmetry is the whole decision.

Actions: James to confirm go, the name and the first source list by 7 August 2026. Prototype with 20 seed cards in this repo by 14 August. Live at the subdomain by 31 August with 150 cards.
