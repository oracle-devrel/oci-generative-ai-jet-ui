import { randomUUID } from 'node:crypto';
import { withConn, oracledb } from './db.ts';
import { chat, embed, parseJsonResponse } from './llm.ts';
import type { StyleProfile, ProfileDiff, SimilarPost } from '../../shared/types.ts';

// ─── Layer 1: Episodic memory ─────────────────────────────────────────────────

export async function savePost(args: {
  userId: string;
  platform: string;
  topic: string;
  content: string;
}): Promise<string> {
  const id = randomUUID();
  const [embedding] = await embed([args.content]);

  await withConn(async (conn) => {
    await conn.execute(
      `INSERT INTO posts (id, user_id, platform, topic, content, embedding)
       VALUES (:id, :userId, :platform, :topic, :content, :embedding)`,
      {
        id,
        userId: args.userId,
        platform: args.platform,
        topic: args.topic,
        content: args.content,
        // Float32Array binds as FLOAT32 to match the column's declared format.
        // Plain number[] binds as FLOAT64 and breaks VECTOR_DISTANCE comparisons.
        embedding: { type: oracledb.DB_TYPE_VECTOR, val: new Float32Array(embedding) },
      },
      { autoCommit: true },
    );
  });

  return id;
}

export async function retrieveSimilarPosts(args: {
  userId: string;
  platform: string;
  topic: string;
  k?: number;
}): Promise<SimilarPost[]> {
  const k = args.k ?? 5;
  const [queryEmbedding] = await embed([args.topic]);

  return withConn(async (conn) => {
    const result = await conn.execute<[string, string, string | null, number]>(
      `SELECT id, content, topic,
              VECTOR_DISTANCE(embedding, :q, COSINE) AS distance
       FROM posts
       WHERE user_id = :userId
         AND platform = :platform
         AND is_deleted = 0
       ORDER BY distance
       FETCH APPROX FIRST :k ROWS ONLY`,
      {
        q: { type: oracledb.DB_TYPE_VECTOR, val: new Float32Array(queryEmbedding) },
        userId: args.userId,
        platform: args.platform,
        k,
      },
    );

    return (result.rows ?? []).map(([id, content, topic, distance]) => ({
      id, content, topic, distance,
    }));
  });
}

export async function forgetPost(userId: string, postId: string): Promise<void> {
  await withConn(async (conn) => {
    await conn.execute(
      `UPDATE posts SET is_deleted = 1
       WHERE id = :postId AND user_id = :userId`,
      { postId, userId },
      { autoCommit: true },
    );
  });
}

// ─── Layer 2: Style profile (semantic memory) ─────────────────────────────────

const SEED_SYSTEM = `You are a voice analyst. You will read several social media posts
by one author and produce a JSON style profile describing how they write.

Be specific and concrete. "Tone is friendly" is useless. "Tone is direct,
occasionally self-deprecating, slightly skeptical of hype" is useful.

Output ONLY valid JSON matching this schema:
{
  "tone": [string],
  "sentenceLength": {"averageWords": int, "habit": string},
  "structuralHabits": [string],
  "signaturePhrases": [string],
  "thingsINeverDo": [string],
  "topicsICareAbout": [string],
  "platformQuirks": {string: string}
}`;

export async function seedStyleProfile(
  userId: string,
  sampleSize = 20,
): Promise<StyleProfile> {
  const rows = await withConn(async (conn) => {
    const r = await conn.execute<[string, string]>(
      `SELECT platform, content FROM posts
       WHERE user_id = :userId AND is_deleted = 0
       ORDER BY created_at DESC
       FETCH FIRST :n ROWS ONLY`,
      { userId, n: sampleSize },
    );
    return r.rows ?? [];
  });

  if (rows.length === 0) {
    throw new Error(`No posts found for user ${userId} — seed the corpus first.`);
  }

  const postsText = rows
    .map(([platform, content]) => `[${platform}] ${content}`)
    .join('\n\n---\n\n');

  const response = await chat({
    system: SEED_SYSTEM,
    user: `Posts:\n\n${postsText}`,
  });
  const profile = parseJsonResponse<StyleProfile>(response);

  await withConn(async (conn) => {
    await conn.execute(
      `MERGE INTO style_profile sp
       USING (SELECT :userId AS user_id FROM dual) src
       ON (sp.user_id = src.user_id)
       WHEN MATCHED THEN UPDATE SET
         profile = :profile, updated_at = CURRENT_TIMESTAMP, version = version + 1
       WHEN NOT MATCHED THEN INSERT (user_id, profile)
         VALUES (:userId, :profile)`,
      { userId, profile: JSON.stringify(profile) },
      { autoCommit: true },
    );
  });

  return profile;
}

export async function loadStyleProfile(
  userId: string,
): Promise<StyleProfile | null> {
  return withConn(async (conn) => {
    const r = await conn.execute<[unknown]>(
      `SELECT profile FROM style_profile WHERE user_id = :userId`,
      { userId },
    );
    if (!r.rows?.length) return null;
    // oracledb auto-parses JSON columns to JS objects on Oracle 23ai+, so we
    // only need to JSON.parse if the driver returns a string (older driver
    // versions or some connection modes).
    const raw = r.rows[0][0];
    return (typeof raw === 'string' ? JSON.parse(raw) : raw) as StyleProfile;
  });
}

// ─── Layer 3: Reflection loop ─────────────────────────────────────────────────

const REFLECT_SYSTEM = `You are reviewing how an author's voice may have evolved.

You have:
1. Their CURRENT style profile (built from their older posts)
2. Their MOST RECENT posts (not yet incorporated)

Read the recent posts. Compare to the profile. Decide whether the profile
needs updating. Be conservative: most of the time, voice is stable and you
should change little or nothing. Only emit updates that you can point to
specific evidence for in the recent posts.

Output ONLY valid JSON:
{
  "additions": [{"field": string, "value": any, "evidence": string}],
  "removals":  [{"field": string, "value": any, "reason": string}],
  "rationale": string
}

If nothing should change, return empty arrays for additions and removals.`;

/**
 * Apply a structured diff to a style profile.
 * Arrays get new values appended (dedup). Scalar fields are replaced.
 */
function applyDiff(profile: StyleProfile, diff: ProfileDiff): StyleProfile {
  const next: StyleProfile = JSON.parse(JSON.stringify(profile));

  const apply = (field: string, value: unknown, isAdd: boolean) => {
    const parts = field.split('.');
    let cursor: any = next;
    for (let i = 0; i < parts.length - 1; i++) {
      cursor = cursor[parts[i]] ?? (cursor[parts[i]] = {});
    }
    const leaf = parts[parts.length - 1];
    const current = cursor[leaf];

    if (Array.isArray(current)) {
      if (isAdd) {
        if (Array.isArray(value)) {
          cursor[leaf] = Array.from(new Set([...current, ...value]));
        } else if (!current.includes(value)) {
          cursor[leaf] = [...current, value];
        }
      } else {
        cursor[leaf] = current.filter((v) => v !== value);
      }
    } else if (typeof current === 'object' && current !== null) {
      if (isAdd && typeof value === 'object' && value !== null) {
        cursor[leaf] = { ...current, ...(value as object) };
      }
    } else {
      if (isAdd) cursor[leaf] = value;
    }
  };

  for (const a of diff.additions ?? []) apply(a.field, a.value, true);
  for (const r of diff.removals ?? []) apply(r.field, r.value, false);

  return next;
}

export async function reflect(
  userId: string,
  windowSize = 5,
): Promise<StyleProfile> {
  const profile = await loadStyleProfile(userId);
  if (!profile) return seedStyleProfile(userId);

  const rows = await withConn(async (conn) => {
    const r = await conn.execute<[string, string]>(
      `SELECT id, content FROM posts
       WHERE user_id = :userId AND is_deleted = 0
       ORDER BY created_at DESC
       FETCH FIRST :n ROWS ONLY`,
      { userId, n: windowSize },
    );
    return r.rows ?? [];
  });

  const postIds = rows.map(([id]) => id);
  const postsText = rows.map(([, content]) => content).join('\n\n---\n\n');

  const response = await chat({
    system: REFLECT_SYSTEM,
    user: `CURRENT PROFILE:\n${JSON.stringify(profile, null, 2)}\n\nRECENT POSTS:\n${postsText}`,
  });
  const diff = parseJsonResponse<ProfileDiff>(response);

  const updated = applyDiff(profile, diff);

  await withConn(async (conn) => {
    await conn.execute(
      `UPDATE style_profile
         SET profile = :profile, updated_at = CURRENT_TIMESTAMP, version = version + 1
       WHERE user_id = :userId`,
      { profile: JSON.stringify(updated), userId },
    );
    await conn.execute(
      `INSERT INTO reflections (id, user_id, posts_window, diff, profile_after)
       VALUES (:id, :userId, :window, :diff, :after)`,
      {
        id: randomUUID(),
        userId,
        window: JSON.stringify(postIds),
        diff: JSON.stringify(diff),
        after: JSON.stringify(updated),
      },
      { autoCommit: true },
    );
  });

  return updated;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

export async function countPosts(userId: string): Promise<number> {
  return withConn(async (conn) => {
    const r = await conn.execute<[number]>(
      `SELECT COUNT(*) FROM posts WHERE user_id = :userId AND is_deleted = 0`,
      { userId },
    );
    return r.rows?.[0]?.[0] ?? 0;
  });
}
