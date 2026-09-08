import { createFileRoute } from '@tanstack/react-router'
import { chat, maxIterations, toServerSentEventsResponse } from '@tanstack/ai'
import { anthropicText } from '@tanstack/ai-anthropic'
import { openaiText } from '@tanstack/ai-openai'
import { geminiText } from '@tanstack/ai-gemini'
import { ollamaText } from '@tanstack/ai-ollama'

import { executeQuery } from '#/lib/oracle-tools'

const SYSTEM_PROMPT = `You are a helpful assistant for a shoe store.

You have access to the store's shoe database through the execute_query tool.
Use it to answer questions about products, inventory, customers, sales, and orders.

IMPORTANT — HOW TO PHRASE QUESTIONS FOR execute_query:
The database AI translates your question directly to SQL. It works best with concrete,
column-oriented phrasing. ALWAYS rephrase the user's question before sending it:

- Use column names: "highest price" not "most expensive", "lowest stock_qty" not "running low"
- Prefer sorting: "show products ordered by price descending limit 1" instead of "what is the most expensive product"
- Avoid abstract adjectives: translate "cheapest" → "lowest price", "best-selling" → "highest total_amount", "popular" → "most transactions"
- Be specific about what to return: "show brand, model, and price" not just "show the shoe"

Examples of good rephrasing:
  User: "What's our most expensive shoe?" → "Show brand, model, and price from products ordered by price descending limit 1"
  User: "Which shoes are running low?" → "Show brand, model, and stock_qty from products where stock_qty is less than 15"
  User: "What's our best-selling category?" → "Show category and count of transactions grouped by product category ordered by count descending"
  User: "Who are our top customers?" → "Show customer first_name, last_name, and sum of total_amount from transactions joined with customers grouped by customer ordered by sum descending limit 5"

Present the results conversationally. If the data suggests follow-up insights, share them.
`

export const Route = createFileRoute('/api/ai/chat')({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const requestSignal = request.signal

        if (requestSignal.aborted) {
          return new Response(null, { status: 499 })
        }

        const abortController = new AbortController()

        try {
          const body = await request.json()
          const { messages } = body

          let provider: string = 'ollama'
          let model: string = 'mistral:7b'
          if (process.env.ANTHROPIC_API_KEY) {
            provider = 'anthropic'
            model = 'claude-haiku-4-5'
          } else if (process.env.OPENAI_API_KEY) {
            provider = 'openai'
            model = 'gpt-4o'
          } else if (process.env.GEMINI_API_KEY) {
            provider = 'gemini'
            model = 'gemini-2.0-flash-exp'
          }

          const adapterConfig = {
            anthropic: () =>
              anthropicText((model || 'claude-haiku-4-5') as any),
            openai: () => openaiText((model || 'gpt-4o') as any),
            gemini: () => geminiText((model || 'gemini-2.0-flash-exp') as any),
            ollama: () => ollamaText((model || 'mistral:7b') as any),
          }

          const adapter = adapterConfig[provider]()

          const stream = chat({
            adapter,
            tools: [executeQuery],
            systemPrompts: [SYSTEM_PROMPT],
            agentLoopStrategy: maxIterations(10),
            messages,
            abortController,
          })

          return toServerSentEventsResponse(stream, { abortController })
        } catch (error: any) {
          if (error.name === 'AbortError' || abortController.signal.aborted) {
            return new Response(null, { status: 499 })
          }
          return new Response(
            JSON.stringify({ error: 'Failed to process chat request' }),
            {
              status: 500,
              headers: { 'Content-Type': 'application/json' },
            },
          )
        }
      },
    },
  },
})
