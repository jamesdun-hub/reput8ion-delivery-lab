import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Schemas are fixed by the brief. If a field feels missing, that is the
// schema doing its job. Do not extend without a brief revision.

const notes = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/notes' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    standfirst: z.string(),
    draft: z.boolean(),
  }),
});

const problems = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/problems' }),
  schema: z.object({
    title: z.string(),
    order: z.number(),
    summary: z.string(),
  }),
});

const endorsements = defineCollection({
  loader: glob({ pattern: '**/*.json', base: './src/content/endorsements' }),
  schema: z.object({
    quote: z.string(),
    name: z.string(),
    title: z.string(),
    organisation: z.string(),
    placement: z.string(),
  }),
});

export const collections = { notes, problems, endorsements };
