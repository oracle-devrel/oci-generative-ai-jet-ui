import 'dotenv/config';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { initDb, closeDb, withConn } from '../src/server/db.ts';
import { savePost, seedStyleProfile } from '../src/server/memory.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Idempotently rebuild the demo corpus.
 *
 * 1. Wipes any existing posts, reflections, and style profile for the demo user.
 * 2. Loads the LinkedIn-export JSON into the posts table.
 * 3. Generates the initial style profile from the loaded posts.
 *
 * Each post in the input file is a plain string. We attach the demo user and
 * platform=linkedin to all of them and let the LLM infer the topic from the
 * content during the seed pass.
 */
async function main() {
  const userId = process.env.DEMO_USER_ID || 'allen';
  const file = join(__dirname, '..', 'data', 'linkedin-posts.json');
  const raw = await readFile(file, 'utf-8');
  const posts = JSON.parse(raw) as string[];

  await initDb();

  console.log(`Clearing existing data for user "${userId}"...`);
  await withConn(async (conn) => {
    await conn.execute(
      `DELETE FROM reflections WHERE user_id = :userId`,
      { userId }, { autoCommit: true },
    );
    await conn.execute(
      `DELETE FROM style_profile WHERE user_id = :userId`,
      { userId }, { autoCommit: true },
    );
    await conn.execute(
      `DELETE FROM posts WHERE user_id = :userId`,
      { userId }, { autoCommit: true },
    );
  });

  console.log(`Seeding ${posts.length} posts for user "${userId}"...`);
  let saved = 0;
  for (const content of posts) {
    if (!content.trim()) continue;
    const topic = content.split('\n')[0].slice(0, 100); // first line as topic stub
    await savePost({ userId, platform: 'linkedin', topic, content });
    saved++;
    if (saved % 5 === 0) console.log(`  ${saved}/${posts.length}`);
  }
  console.log(`Saved ${saved} posts.`);

  console.log('Generating initial style profile...');
  const profile = await seedStyleProfile(userId, Math.min(20, saved));
  console.log('Profile:');
  console.log(JSON.stringify(profile, null, 2));

  await closeDb();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
