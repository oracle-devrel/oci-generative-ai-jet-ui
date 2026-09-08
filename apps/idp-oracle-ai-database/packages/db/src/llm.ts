import oracledb from "oracledb";
import { z } from "zod";
import { withConnection } from "./pool.js";
import {
  getFieldsSchema,
  getJsonSchemaForType,
  type ExtractableDocType,
  type FieldsByType,
} from "@idp/schemas";
import { logger } from "@idp/logger";

const CREDENTIAL_NAME = "OCI_CRED";
const EXTRACT_MAX_TOKENS = 4096;
const EXTRACT_RETRIES = 1;

function generationParams(maxTokens: number): string {
  const region = process.env.OCI_GENAI_REGION ?? "eu-frankfurt-1";
  const model = process.env.OCI_GENAI_MODEL ?? "meta.llama-3.3-70b-instruct";
  return JSON.stringify({
    provider: "ocigenai",
    credential_name: CREDENTIAL_NAME,
    url: `https://inference.generativeai.${region}.oci.oraclecloud.com/20231130/actions/chat`,
    model,
    chatRequest: { maxTokens, temperature: 0 },
  });
}

async function generate(prompt: string, maxTokens: number): Promise<string> {
  return withConnection(async (conn) => {
    conn.callTimeout = 60_000;
    const result = await conn.execute<{ OUT: string }>(
      `SELECT DBMS_VECTOR_CHAIN.UTL_TO_GENERATE_TEXT(:input, JSON(:params)) AS OUT FROM DUAL`,
      { input: prompt, params: generationParams(maxTokens) },
      {
        outFormat: oracledb.OUT_FORMAT_OBJECT,
        fetchInfo: { OUT: { type: oracledb.STRING } },
      }
    );
    return (result.rows?.[0]?.OUT ?? "").trim();
  });
}

function extractJsonObject(raw: string): unknown {
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidate = (fenced?.[1] ?? raw).trim();
  const firstBrace = candidate.indexOf("{");
  const lastBrace = candidate.lastIndexOf("}");
  if (firstBrace === -1 || lastBrace <= firstBrace) {
    throw new Error(`LLM response is not JSON: ${raw.slice(0, 200)}`);
  }
  return JSON.parse(candidate.slice(firstBrace, lastBrace + 1));
}

export async function extractFieldsInDb<T extends ExtractableDocType>(
  text: string,
  docType: T
): Promise<FieldsByType[T]> {
  const schema = getFieldsSchema(docType);
  const jsonSchema = getJsonSchemaForType(docType);
  const basePrompt = `You extract structured fields from a document. Respond with a single JSON object that matches the provided JSON Schema exactly. EVERY field that is not explicitly marked nullable in the schema MUST be filled with a real value extracted or inferred from the document — never return null for required fields. No prose, no markdown fences.

Document type: ${docType}
JSON Schema:
${JSON.stringify(jsonSchema)}

Document text:
${text}`;

  let lastError: unknown;
  for (let attempt = 0; attempt <= EXTRACT_RETRIES; attempt++) {
    const prompt =
      attempt === 0
        ? basePrompt
        : `${basePrompt}\n\nYour previous attempt failed validation with: ${
            (lastError as Error)?.message?.slice(0, 400) ?? "unknown error"
          }\nReturn a corrected JSON object now.`;
    const raw = await generate(prompt, EXTRACT_MAX_TOKENS);
    try {
      const obj = extractJsonObject(raw);
      return (schema as z.ZodTypeAny).parse(obj) as FieldsByType[T];
    } catch (err) {
      lastError = err;
      logger.warn("extractFieldsInDb attempt failed", {
        attempt: attempt + 1,
        error: (err as Error).message.slice(0, 200),
      });
    }
  }
  throw lastError;
}
