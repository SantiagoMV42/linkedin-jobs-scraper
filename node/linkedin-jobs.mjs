// LinkedIn jobs from the last 24 hours, new ones only.
// npm i apify-client   (or pnpm add / bun add)
// APIFY_TOKEN=... node linkedin-jobs.mjs
import { ApifyClient } from 'apify-client';

const client = new ApifyClient({ token: process.env.APIFY_TOKEN });

const run = await client.actor('santiagomv/linkedin-jobs').call({
    searchQueries: ['product designer'],
    location: 'London, England, United Kingdom',
    datePosted: 'day',
    maxJobsPerSearch: 100,
    onlyNewJobs: true,
});

const { items } = await client.dataset(run.defaultDatasetId).listItems();
for (const job of items) console.log(`${job.title} @ ${job.company} (${job.location}) ${job.url}`);
console.log(`${items.length} new jobs`);
