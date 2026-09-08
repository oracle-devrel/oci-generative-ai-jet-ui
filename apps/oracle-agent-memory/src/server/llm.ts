import * as common from 'oci-common';
import { GenerativeAiInferenceClient } from 'oci-generativeaiinference';

const provider = new common.ConfigFileAuthenticationDetailsProvider();
const client = new GenerativeAiInferenceClient({
  authenticationDetailsProvider: provider,
});

const compartmentId = process.env.OCI_COMPARTMENT_ID!;

// Model IDs rotate in OCI Generative AI — versioned (dated) IDs are required
// once the unversioned alias is deprecated. Override via env vars if these
// stop working; check the Console at Analytics & AI → Generative AI → Pretrained
// Foundational Models for what's currently available in your region.
const EMBED_MODEL = process.env.OCI_EMBED_MODEL_ID ?? 'cohere.embed-english-v3.0';
const CHAT_MODEL  = process.env.OCI_CHAT_MODEL_ID  ?? 'cohere.command-r-plus-08-2024';

/**
 * Embed one or more texts into 1024-dim vectors using OCI's hosted Cohere model.
 */
export async function embed(texts: string[]): Promise<number[][]> {
  const res = await client.embedText({
    embedTextDetails: {
      inputs: texts,
      servingMode: {
        servingType: 'ON_DEMAND',
        modelId: EMBED_MODEL,
      },
      compartmentId,
    },
  });
  return res.embedTextResult.embeddings;
}

/**
 * Chat with the model. `system` is the preamble (rules, persona, schema);
 * `user` is the turn-specific message. Returns the model's text reply.
 */
export async function chat(args: {
  system: string;
  user: string;
  temperature?: number;
  maxTokens?: number;
}): Promise<string> {
  const res = await client.chat({
    chatDetails: {
      servingMode: {
        servingType: 'ON_DEMAND',
        modelId: CHAT_MODEL,
      },
      compartmentId,
      chatRequest: {
        apiFormat: 'COHERE',
        preambleOverride: args.system,
        message: args.user,
        temperature: args.temperature ?? 0.2,
        maxTokens: args.maxTokens ?? 1500,
      },
    },
  });
  return res.chatResult.chatResponse.text;
}

/**
 * Parse a JSON response from the LLM, tolerating common formatting quirks
 * (markdown code fences, leading/trailing whitespace).
 */
export function parseJsonResponse<T>(raw: string): T {
  const cleaned = raw
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();
  return JSON.parse(cleaned) as T;
}
