// Remote engineering jobs from company career sites (Greenhouse, Lever, Ashby, Workable...).
// npm i apify-client   (or pnpm add / bun add)
// APIFY_TOKEN=... node career-site-jobs.mjs
import { ApifyClient } from 'apify-client';

const client = new ApifyClient({ token: process.env.APIFY_TOKEN });

const run = await client.actor('santiagomv/ats-jobs').call({
    companies: ['https://boards.greenhouse.io/stripe', 'https://jobs.ashbyhq.com/openai', 'lever:palantir'],
    titleKeywords: ['engineer'],
    remoteOnly: true,
});

const { items } = await client.dataset(run.defaultDatasetId).listItems();
console.table(items.map(({ company, title, location, ats, url }) => ({ company, title, location, ats, url })));
