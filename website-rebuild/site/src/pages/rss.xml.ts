import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const notes = (await getCollection('notes'))
    .filter((n) => !n.data.draft)
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

  return rss({
    title: 'Reput8ion Dynamics. Notes',
    description:
      'Published thinking on reputation, narrative, issues management and counsel under pressure.',
    site: context.site!,
    items: notes.map((n) => ({
      title: n.data.title,
      pubDate: n.data.date,
      description: n.data.standfirst,
      link: `/notes/${n.id}`,
    })),
  });
}
