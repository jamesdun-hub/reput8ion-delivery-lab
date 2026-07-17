# Reput8ion Dynamics website

Astro, TypeScript, static output, zero client-side JavaScript. Built to
BUILD-BRIEF-v4.md (one level up). The brief is the contract.

## Run it

```bash
npm install
npm run dev        # local preview at localhost:4321
npm run build      # regenerates image renditions, builds to dist/
npm run preview    # serves the built site
npm run check      # the launch gate. Must pass before DNS switches
```

## How content works

- **Notes**: add a markdown file to `src/content/notes/`. Frontmatter is
  title, date, standfirst, draft. Save, commit, push. That is the whole
  publishing workflow. RSS and the home page latest-note block update
  themselves.
- **Problems**: `src/content/problems/`, ordered by the `order` field.
- **Endorsements**: `src/content/endorsements/`, placed by the `placement`
  field.
- **Client logos**: `src/data/clients.json`. Nothing renders unless
  `cleared` is true for that client. Drop the logo file in
  `public/images/logos/`.

## Sample content

Copy that is not final carries a visible red tag on the page and a
`data-placeholder` attribute in the HTML. `src/data/samples.json` lists
every sample entry. `npm run check` fails while any of it remains, so the
site cannot launch with sample copy by accident. As James finalises each
piece, remove its id from samples.json.

## The two photographs

Source frames live in `../assets`. `npm run build` regenerates the webp
and jpg renditions. The portrait is capped at its true 2048px until the
original file is sourced. The pipeline refuses to upscale.
