"use client";

// Renderers for the structured blocks Aura Analyst emits inside its answer.
//
// The /chat stream returns each piece of the answer as its own `output_text`
// part. Some parts are prose; others are a single self-contained JSON blob:
//   {"type":"chart", chart_type, title, raw_data:{columns,rows}, chart_metadata}
//   {"type":"table", title, columns:[{name,type}], table_data:[[...]]}
// We parse those and render them as real charts/tables instead of dumping the
// JSON as text. Charts use recharts (already used across the demo) driven off
// the clean `raw_data` + `chart_metadata`, so we skip the heavy Plotly figure.

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ---------------------------------------------------------------------------
// Types + parsing
// ---------------------------------------------------------------------------

export interface ChartBlob {
  type: "chart";
  chart_type?: string;
  title?: string;
  raw_data?: { columns: string[]; rows: unknown[][] };
  chart_metadata?: Record<string, string | null>;
}

export interface TableBlob {
  type: "table";
  title?: string;
  columns?: { name: string; type: string }[];
  table_data?: unknown[][];
}

export type VizBlob = ChartBlob | TableBlob;

/** True once a streaming text buffer is unambiguously a chart/table blob. */
export function looksLikeViz(buffer: string): "chart" | "table" | null {
  const s = buffer.trimStart();
  if (!s.startsWith("{")) return null;
  if (/^\{\s*"type"\s*:\s*"chart"/.test(s)) return "chart";
  if (/^\{\s*"type"\s*:\s*"table"/.test(s)) return "table";
  return null;
}

/** Parse a completed text part into a viz blob, or null if it's just prose. */
export function parseViz(text: string): VizBlob | null {
  const s = text.trim();
  if (!s.startsWith("{")) return null;
  try {
    const j = JSON.parse(s);
    if (j && (j.type === "chart" || j.type === "table")) return j as VizBlob;
  } catch {
    // not JSON — prose
  }
  return null;
}

// SingleStore purple + a complementary palette for multi-series / pie slices.
const PALETTE = [
  "#553BCC",
  "#2CA01C",
  "#7C6BE0",
  "#0EA5E9",
  "#F59E0B",
  "#EC4899",
  "#14B8A6",
  "#8B5CF6",
  "#EF4444",
  "#10B981",
];

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function isNum(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function fmtNum(v: unknown): string {
  if (!isNum(v)) return v == null ? "" : String(v);
  const abs = Math.abs(v);
  if (abs >= 1000 || (abs > 0 && abs < 0.01)) {
    return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function fmtAxis(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return `${v}`;
}

function truncate(s: string, n = 22): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------

function rowsToObjects(blob: ChartBlob): Record<string, unknown>[] {
  const cols = blob.raw_data?.columns ?? [];
  const rows = blob.raw_data?.rows ?? [];
  return rows.map((r) =>
    Object.fromEntries(cols.map((c, i) => [c, (r as unknown[])[i]])),
  );
}

export function ChartView({ blob }: { blob: ChartBlob }) {
  const meta = blob.chart_metadata ?? {};
  const cols = blob.raw_data?.columns ?? [];
  const data = rowsToObjects(blob);

  if (data.length === 0) {
    return <RawFallback label="chart" title={blob.title} />;
  }

  const kind = (blob.chart_type || "bar").toLowerCase();
  // Prefer the un-truncated label column the Analyst ships alongside the x axis.
  const fullLabelCol = cols.find((c) => c === "_full_x_label");

  const xKey = meta.x || meta.names || cols[0] || "x";
  const yKey =
    meta.y ||
    meta.values ||
    cols.find((c) => c !== xKey && c !== fullLabelCol) ||
    cols[1] ||
    "y";

  const labelOf = (row: Record<string, unknown>): string => {
    const raw = (fullLabelCol ? row[fullLabelCol] : row[xKey]) ?? row[xKey];
    return raw == null ? "" : String(raw);
  };

  const tooltipProps = {
    formatter: (v: number) => [fmtNum(v), String(yKey)] as [string, string],
    labelStyle: { color: "#0f172a", fontWeight: 600 },
    contentStyle: {
      border: "1px solid #e5e7eb",
      borderRadius: 6,
      fontSize: 12,
    },
  };

  let chart: React.ReactNode;

  if (kind === "pie" || kind === "donut") {
    const pieData = data.map((row) => ({
      name: labelOf(row),
      value: Number(row[yKey]) || 0,
    }));
    chart = (
      <PieChart>
        <Pie
          data={pieData}
          dataKey="value"
          nameKey="name"
          innerRadius={kind === "donut" ? 60 : 0}
          outerRadius={100}
          paddingAngle={1}
        >
          {pieData.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => fmtNum(v)} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    );
  } else if (kind === "line" || kind === "area") {
    const Cmp = kind === "area" ? AreaChart : LineChart;
    chart = (
      <Cmp data={data} margin={{ top: 8, right: 16, left: 0, bottom: 36 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 11, fill: "#475569" }}
          tickFormatter={(v: unknown) => truncate(String(v))}
          interval="preserveStartEnd"
          angle={-20}
          textAnchor="end"
          height={56}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#475569" }}
          tickFormatter={fmtAxis}
          width={56}
        />
        <Tooltip {...tooltipProps} />
        {kind === "area" ? (
          <Area
            type="monotone"
            dataKey={yKey}
            stroke="#553BCC"
            fill="#553BCC"
            fillOpacity={0.15}
            strokeWidth={2}
          />
        ) : (
          <Line
            type="monotone"
            dataKey={yKey}
            stroke="#553BCC"
            strokeWidth={2}
            dot={false}
          />
        )}
      </Cmp>
    );
  } else {
    // Default: bar (the common Analyst case).
    chart = (
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 64 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 11, fill: "#475569" }}
          tickFormatter={(v: unknown) => truncate(String(v), 16)}
          interval={0}
          angle={-40}
          textAnchor="end"
          height={88}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#475569" }}
          tickFormatter={fmtAxis}
          width={56}
        />
        <Tooltip {...tooltipProps} />
        <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    );
  }

  return (
    <figure className="my-1 w-full rounded-lg border border-gray-200 bg-white p-3">
      {blob.title && (
        <figcaption className="mb-2 px-1 text-sm font-semibold text-gray-800">
          {blob.title}
        </figcaption>
      )}
      <ResponsiveContainer width="100%" height={300}>
        {chart as React.ReactElement}
      </ResponsiveContainer>
    </figure>
  );
}

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

export function TableView({ blob }: { blob: TableBlob }) {
  const cols = blob.columns ?? [];
  const rows = blob.table_data ?? [];
  if (cols.length === 0 || rows.length === 0) {
    return <RawFallback label="table" title={blob.title} />;
  }
  const numeric = cols.map(
    (c) => c.type === "int64" || c.type === "float64" || c.type === "int" || c.type === "float",
  );

  return (
    <div className="my-1 w-full">
      {blob.title && (
        <p className="mb-2 px-1 text-sm font-semibold text-gray-800">
          {blob.title}
        </p>
      )}
      <div className="max-h-[22rem] overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {cols.map((c, i) => (
                <TableHead
                  key={i}
                  className={numeric[i] ? "text-right" : undefined}
                >
                  {c.name}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {(rows as unknown[][]).map((row, ri) => (
              <TableRow key={ri}>
                {row.map((cell, ci) => (
                  <TableCell
                    key={ci}
                    className={numeric[ci] ? "text-right tabular-nums" : undefined}
                  >
                    {numeric[ci] ? fmtNum(cell) : String(cell ?? "")}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// Last-resort: a blob we couldn't make sense of. Better than raw JSON.
function RawFallback({ label, title }: { label: string; title?: string }) {
  return (
    <div className="my-1 rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-4 text-sm text-gray-500">
      {title || `Analyst returned a ${label} with no displayable data.`}
    </div>
  );
}

export function VizBlock({ blob }: { blob: VizBlob }) {
  return blob.type === "chart" ? (
    <ChartView blob={blob} />
  ) : (
    <TableView blob={blob} />
  );
}
