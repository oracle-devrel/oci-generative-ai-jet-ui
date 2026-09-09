import { chat } from './llm.ts';
import { loadStyleProfile, retrieveSimilarPosts } from './memory.ts';
import type { DraftResponse } from '../../shared/types.ts';

const GENERATE_SYSTEM = (profile: object, examples: string) => `You are drafting a social media post in the user's voice.

STYLE PROFILE (how this user writes):
${JSON.stringify(profile, null, 2)}

EXAMPLES (recent posts by this user on similar topics):
${examples}

Write ONE draft post. Match the style profile and the cadence of the
examples. Do not copy phrases from the examples. Do not mention that
you are an AI or that you are following a profile.`;

export async function generatePost(args: {
  userId: string;
  platform: string;
  topic: string;
}): Promise<DraftResponse> {
  const profile = (await loadStyleProfile(args.userId)) ?? {};
  const examples = await retrieveSimilarPosts({ ...args, k: 5 });
  const examplesText = examples.map((e) => e.content).join('\n\n---\n\n');

  const draft = await chat({
    system: GENERATE_SYSTEM(profile, examplesText),
    user: `Platform: ${args.platform}\nTopic: ${args.topic}\n\nDraft:`,
    temperature: 0.6,
    maxTokens: 1000,
  });

  return {
    draft,
    basedOn: examples.map((e) => ({
      postId: e.id,
      topic: e.topic,
      distance: e.distance,
    })),
  };
}
