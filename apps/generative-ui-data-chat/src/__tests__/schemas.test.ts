import { describe, expect, it } from "vitest";

import { DataChatApiResponseSchema, DataChatPlanSchema } from "@/lib/schemas";

describe("data chat schemas", () => {
  it("accepts a valid LLM plan", () => {
    const plan = DataChatPlanSchema.parse({
      intent: "revenueTrend",
      strategy: "sql",
      title: "Revenue trend",
      componentTypes: ["lineChart", "areaChart", "barChart", "horizontalBarChart", "pieChart"]
    });

    expect(plan.intent).toBe("revenueTrend");
  });

  it("rejects unsupported component types", () => {
    expect(() =>
      DataChatPlanSchema.parse({
        intent: "revenueTrend",
        strategy: "sql",
        title: "Revenue trend",
        componentTypes: ["markdown"]
      })
    ).toThrow();
  });

  it("accepts the public API response envelope", () => {
    const response = DataChatApiResponseSchema.parse({
      answer: {
        title: "Active users",
        summary: "Usage increased.",
        components: [
          {
            type: "kpiCard",
            title: "Active users",
            value: "49,110",
            delta: "+8.6%",
            trend: "up",
            caption: "Previous month: 45,220"
          }
        ]
      },
      queryTrace: [
        {
          strategy: "sql",
          label: "Active users month-over-month",
          statement: "SELECT 1 FROM DUAL",
          elapsedMs: 12,
          rowCount: 1
        }
      ]
    });

    expect(response.answer.components[0].type).toBe("kpiCard");
  });
});
