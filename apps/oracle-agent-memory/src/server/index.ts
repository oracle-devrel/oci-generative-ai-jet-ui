import 'dotenv/config';
import express from 'express';
import { initDb, closeDb } from './db.ts';
import { router } from './routes.ts';

const app = express();
app.use(express.json({ limit: '1mb' }));
app.use('/api', router);

// Centralized error handler
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error(err);
  res.status(500).json({ error: err.message });
});

const port = Number(process.env.PORT ?? 3001);

async function start() {
  await initDb();
  app.listen(port, () => {
    console.log(`oracle-agent-memory server listening on http://localhost:${port}`);
  });
}

start().catch((err) => {
  console.error('Failed to start:', err);
  process.exit(1);
});

process.on('SIGINT', async () => {
  console.log('\nShutting down...');
  await closeDb();
  process.exit(0);
});
