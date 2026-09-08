import { Router } from 'express';
import {
  countPosts,
  forgetPost,
  loadStyleProfile,
  reflect,
  savePost,
  seedStyleProfile,
} from './memory.ts';
import { generatePost } from './agent.ts';

export const router = Router();

// Single source of truth for "who is the demo user." The client fetches this
// on startup instead of hardcoding a userId.
router.get('/me', (_req, res) => {
  res.json({ userId: process.env.DEMO_USER_ID ?? 'allen' });
});

router.post('/draft', async (req, res, next) => {
  try {
    const { userId, platform, topic } = req.body;
    if (!userId || !platform || !topic) {
      return res.status(400).json({ error: 'userId, platform, topic required' });
    }
    const result = await generatePost({ userId, platform, topic });
    res.json(result);
  } catch (err) { next(err); }
});

router.post('/posts', async (req, res, next) => {
  try {
    const { userId, platform, topic, content } = req.body;
    if (!userId || !platform || !content) {
      return res.status(400).json({ error: 'userId, platform, content required' });
    }
    const id = await savePost({ userId, platform, topic, content });

    // Trigger reflection every 5 saved posts
    const total = await countPosts(userId);
    if (total > 0 && total % 5 === 0) {
      reflect(userId).catch((e) => console.error('Reflection failed:', e));
    }
    res.json({ id });
  } catch (err) { next(err); }
});

router.delete('/posts/:id', async (req, res, next) => {
  try {
    const { userId } = req.body;
    if (!userId) return res.status(400).json({ error: 'userId required' });
    await forgetPost(userId, req.params.id);
    res.json({ ok: true });
  } catch (err) { next(err); }
});

router.get('/profile/:userId', async (req, res, next) => {
  try {
    const profile = await loadStyleProfile(req.params.userId);
    res.json({ profile });
  } catch (err) { next(err); }
});

router.post('/profile/:userId/seed', async (req, res, next) => {
  try {
    const profile = await seedStyleProfile(req.params.userId);
    res.json({ profile });
  } catch (err) { next(err); }
});

router.post('/profile/:userId/reflect', async (req, res, next) => {
  try {
    const profile = await reflect(req.params.userId);
    res.json({ profile });
  } catch (err) { next(err); }
});
