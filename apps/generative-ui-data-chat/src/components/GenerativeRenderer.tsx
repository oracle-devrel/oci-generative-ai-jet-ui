"use client";

import React from "react";
import {
  AreaChart as OpenUIAreaChart,
  BarChart as OpenUIBarChart,
  Card,
  CardHeader,
  HorizontalBarChart as OpenUIHorizontalBarChart,
  LineChart as OpenUILineChart,
  PieChart as OpenUIPieChart,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
  TextCallout
} from "@openuidev/react-ui";
import { ArrowDownRight, ArrowRight, ArrowUpRight, ExternalLink } from "lucide-react";

import type { DataChatResponse, UiComponent } from "@/lib/schemas";

function TrendIcon({ trend }: { trend: "up" | "down" | "flat" }) {
  if (trend === "up") {
    return <ArrowUpRight className="h-5 w-5 text-ocean" aria-hidden />;
  }
  if (trend === "down") {
    return <ArrowDownRight className="h-5 w-5 text-signal" aria-hidden />;
  }
  return <ArrowRight className="h-5 w-5 text-cobalt" aria-hidden />;
}

function Panel({
  children,
  title,
  subtitle
}: {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}) {
  return (
    <Card variant="card" width="full" className="border border-ink/10 bg-white p-6 shadow-sm">
      <CardHeader title={title} subtitle={subtitle} className="px-0 pt-0" />
      <div className="mt-5">{children}</div>
    </Card>
  );
}

function ChartComponent({ component }: { component: Extract<UiComponent, { type: "lineChart" }> }) {
  const chartData = component.data.map((row) => ({
    [component.xKey]: row[component.xKey],
    [component.yKey]: row[component.yKey]
  })) as Array<Record<string, string | number>>;

  return (
    <Panel title={component.title} subtitle={component.description}>
      <div className="min-h-[440px] w-full">
        <OpenUILineChart
          data={chartData}
          categoryKey={component.xKey}
          theme="sunset"
          grid
          legend={false}
          showYAxis
          height={420}
          strokeWidth={3}
        />
      </div>
    </Panel>
  );
}

function AreaChartComponent({ component }: { component: Extract<UiComponent, { type: "areaChart" }> }) {
  return (
    <Panel title={component.title} subtitle={component.description}>
      <div className="min-h-[380px] w-full">
        <OpenUIAreaChart
          data={component.data as Array<Record<string, string | number>>}
          categoryKey={component.categoryKey}
          theme="sunset"
          grid
          legend={false}
          showYAxis
          height={360}
        />
      </div>
    </Panel>
  );
}

function BarChartComponent({ component }: { component: Extract<UiComponent, { type: "barChart" }> }) {
  return (
    <Panel title={component.title} subtitle={component.description}>
      <div className="min-h-[380px] w-full">
        <OpenUIBarChart
          data={component.data as Array<Record<string, string | number>>}
          categoryKey={component.categoryKey}
          theme="sunset"
          variant={component.variant}
          grid
          legend
          showYAxis
          height={360}
        />
      </div>
    </Panel>
  );
}

function HorizontalBarChartComponent({ component }: { component: Extract<UiComponent, { type: "horizontalBarChart" }> }) {
  return (
    <Panel title={component.title} subtitle={component.description}>
      <div className="min-h-[380px] w-full">
        <OpenUIHorizontalBarChart
          data={component.data as Array<Record<string, string | number>>}
          categoryKey={component.categoryKey}
          theme="sunset"
          variant={component.variant}
          grid
          legend={false}
          showXAxis
          height={360}
        />
      </div>
    </Panel>
  );
}

function PieChartComponent({ component }: { component: Extract<UiComponent, { type: "pieChart" }> }) {
  return (
    <Panel title={component.title} subtitle={component.description}>
      <div className="min-h-[360px] w-full">
        <OpenUIPieChart
          data={component.data as Array<Record<string, string | number>>}
          categoryKey={component.categoryKey}
          dataKey={component.dataKey}
          theme="sunset"
          variant={component.variant}
          format="number"
          legend
          legendVariant="stacked"
          height={340}
        />
      </div>
    </Panel>
  );
}

function TableComponent({ component }: { component: Extract<UiComponent, { type: "comparisonTable" }> }) {
  return (
    <Panel title={component.title}>
      <Table containerClassName="max-h-[560px] min-w-full overflow-auto rounded-md border border-ink/10">
        <TableHeader>
          <TableRow>
            {component.columns.map((column) => (
              <TableHead key={column.key} align={column.align === "right" ? "right" : "left"}>
                {column.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {component.rows.map((row, index) => (
            <TableRow key={index}>
              {component.columns.map((column) => (
                <TableCell key={column.key} align={column.align === "right" ? "right" : "left"}>
                  {row[column.key] ?? "-"}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Panel>
  );
}

function KpiComponent({ component }: { component: Extract<UiComponent, { type: "kpiCard" }> }) {
  return (
    <Panel title={component.title}>
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-7xl font-semibold leading-none text-ink">{component.value}</div>
          <p className="mt-4 text-base text-ink/65">{component.caption}</p>
        </div>
        <Tag
          variant={component.trend === "down" ? "warning" : component.trend === "up" ? "success" : "neutral"}
          size="lg"
          text={
            <span className="inline-flex items-center gap-2">
              <TrendIcon trend={component.trend} />
              {component.delta}
            </span>
          }
        />
      </div>
    </Panel>
  );
}

function SourcesComponent({ component }: { component: Extract<UiComponent, { type: "sourceCards" }> }) {
  return (
    <Panel title={component.title}>
      <div className="grid gap-4 lg:grid-cols-2">
        {component.sources.map((source) => (
          <article key={source.id} className="min-w-0 rounded-md border border-ink/10 bg-paper p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h4 className="text-lg font-semibold text-ink">{source.title}</h4>
                <p className="mt-1 text-sm font-medium text-ocean">{source.account}</p>
              </div>
              {typeof source.score === "number" ? (
                <Tag text={`${Math.round(source.score * 100)}%`} variant="info" size="sm" />
              ) : null}
            </div>
            <p className="mt-4 text-base leading-7 text-ink/75">{source.snippet}</p>
            <div className="mt-5 flex min-w-0 items-center gap-2 text-sm font-medium text-cobalt">
              <ExternalLink className="h-4 w-4" aria-hidden />
              <span className="min-w-0 break-words">{source.citation}</span>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}

function MixedComponent({ component }: { component: Extract<UiComponent, { type: "mixedInsight" }> }) {
  return (
    <section className="rounded-md border border-ink/10 bg-white p-6 shadow-sm">
      <CardHeader title={component.title} className="px-0 pt-0" />
      <TextCallout variant="warning" title={component.callout} className="mt-4" />
      <div className="mt-5 space-y-5">
        <ChartComponent component={component.chart} />
        <SourcesComponent component={component.sources} />
      </div>
      <ul className="mt-5 grid gap-3 lg:grid-cols-3">
        {component.bullets.map((bullet) => (
          <li key={bullet} className="flex gap-3 rounded-md border border-ink/10 bg-paper px-4 py-4 text-base leading-7 text-ink/75">
            <ArrowRight className="mt-1 h-5 w-5 flex-none text-cobalt" aria-hidden />
            <span>{bullet}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function renderComponent(component: UiComponent) {
  switch (component.type) {
    case "lineChart":
      return <ChartComponent component={component} />;
    case "areaChart":
      return <AreaChartComponent component={component} />;
    case "barChart":
      return <BarChartComponent component={component} />;
    case "horizontalBarChart":
      return <HorizontalBarChartComponent component={component} />;
    case "pieChart":
      return <PieChartComponent component={component} />;
    case "comparisonTable":
      return <TableComponent component={component} />;
    case "kpiCard":
      return <KpiComponent component={component} />;
    case "sourceCards":
      return <SourcesComponent component={component} />;
    case "mixedInsight":
      return <MixedComponent component={component} />;
  }
}

export function GenerativeRenderer({ response }: { response: DataChatResponse }) {
  return (
    <div>
      <div className="mb-7 max-w-5xl">
        <span className="generated-label">Generated interface</span>
        <h2 className="mt-4 text-4xl font-semibold leading-tight text-ink lg:text-5xl">{response.title}</h2>
        <p className="mt-3 text-xl leading-8 text-ink/70">{response.summary}</p>
      </div>
      <div className="space-y-5">{response.components.map((component, index) => <div key={`${component.type}-${index}`}>{renderComponent(component)}</div>)}</div>
    </div>
  );
}
