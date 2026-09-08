import 'dotenv/config';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { initDb, withConn, closeDb } from '../src/server/db.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function main() {
  await initDb();
  const sql = await readFile(join(__dirname, '..', 'schema.sql'), 'utf-8');

  // Strip whole-line `--` comments first, then split on statement-terminating
  // semicolons. Doing it in this order is important: if you split first and
  // then filter, leading comments stay glued to the statement they precede.
  const stripped = sql
    .split('\n')
    .filter((line) => !line.trim().startsWith('--'))
    .join('\n');

  const statements = stripped
    .split(/;\s*\n/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  await withConn(async (conn) => {
    for (const stmt of statements) {
      try {
        await conn.execute(stmt);
        console.log('OK:', stmt.split('\n')[0]);
      } catch (e: any) {
        if (e.errorNum === 955) {
          console.log('SKIP (exists):', stmt.split('\n')[0]);
        } else {
          throw e;
        }
      }
    }
  });

  await closeDb();
  console.log('Schema applied.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
