import { toolDefinition } from '@tanstack/ai'
import { z } from 'zod'

import { executeSelectAI } from '#/lib/oracle'

export const executeQueryToolDef = toolDefinition({
  name: 'execute_query',
  description:
    'Query the shoe store database using natural language. The database AI translates your question to SQL, so use concrete column-oriented phrasing for reliable results. Tables: products (brand, model, category, price, stock_qty, color, size_range, released, description), customers (first_name, last_name, email, city, state, joined_date), transactions (customer_id, product_id, quantity, total_amount, txn_date, status). Prefer "ordered by price descending limit 1" over "most expensive". Avoid abstract adjectives — use column names instead.',
  inputSchema: z.object({
    question: z
      .string()
      .describe(
        'A concrete, column-oriented question for the database AI. Use actual column names and sorting/limit phrasing. Good: "show brand, model, price from products ordered by price descending limit 1". Bad: "what is the most expensive shoe".',
      ),
  }),
  outputSchema: z.object({
    result: z.string(),
  }),
})

export const executeQuery = executeQueryToolDef.server(async ({ question }) => {
  try {
    const answer = await executeSelectAI(question, 'narrate')
    return { result: answer }
  } catch (error) {
    console.error('Select AI error:', error)
    return {
      result: `Unable to query the database right now. Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    }
  }
})
