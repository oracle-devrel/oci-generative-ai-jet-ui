import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GenerativeRenderer } from "@/components/GenerativeRenderer";

describe("GenerativeRenderer", () => {
  it("renders a typed KPI component", () => {
    render(
      <GenerativeRenderer
        response={{
          title: "Active users this month",
          summary: "Usage increased from the previous month.",
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
        }}
      />
    );

    expect(screen.getByText("Active users this month")).toBeInTheDocument();
    expect(screen.getByText("49,110")).toBeInTheDocument();
    expect(screen.getByText("+8.6%")).toBeInTheDocument();
  });
});
