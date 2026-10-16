
import { useMemo, useState } from "react";
import Plot from "react-plotly.js";
import "./App.css";
import Papa from "papaparse";
type Campaign = {
  campaign: string;
  impressions: number;
  visits: number;
  conversions: number;
  spend: number;
};

const demoCampaigns: Campaign[] = [
  { campaign: "Campaign A", impressions: 12000, visits: 720, conversions: 96, spend: 1800 },
  { campaign: "Campaign B", impressions: 15000, visits: 840, conversions: 105, spend: 2400 },
  { campaign: "Campaign C", impressions: 9800, visits: 510, conversions: 72, spend: 1500 },
  { campaign: "Campaign D", impressions: 17500, visits: 980, conversions: 142, spend: 3100 },
  { campaign: "Campaign E", impressions: 11000, visits: 660, conversions: 88, spend: 1950 },
];


function parseCSV(text: string): Campaign[] {
  const required = [
    "campaign",
    "impressions",
    "visits",
    "conversions",
    "spend",
  ];

  const result = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: "greedy",
    transformHeader: (header) => header.trim().toLowerCase(),
  });

  if (result.errors.length > 0) {
    throw new Error(
      `CSV parsing failed: ${result.errors[0].message}`,
    );
  }

  const headers = result.meta.fields ?? [];

  if (new Set(headers).size !== headers.length) {
    throw new Error("CSV contains duplicate column headers.");
  }

  const missing = required.filter((name) => !headers.includes(name));

  if (missing.length > 0) {
    throw new Error(`Missing required columns: ${missing.join(", ")}`);
  }

  if (result.data.length === 0) {
    throw new Error("CSV contains no campaign records.");
  }

  const seenCampaigns = new Set<string>();

  return result.data.map((row, index) => {
    const rowNumber = index + 2;
    const campaign = (row.campaign ?? "").trim();

    if (!campaign) {
      throw new Error(`Campaign name is missing on row ${rowNumber}.`);
    }

    const campaignKey = campaign.toLowerCase();

    if (seenCampaigns.has(campaignKey)) {
      throw new Error(`Duplicate campaign "${campaign}" found.`);
    }

    seenCampaigns.add(campaignKey);

    const parseCount = (column: string): number => {
      const raw = row[column]?.trim() ?? "";

      if (!/^\d+$/.test(raw)) {
        throw new Error(
          `${column} must be a non-negative integer on row ${rowNumber}.`,
        );
      }

      const value = Number(raw);

      if (!Number.isSafeInteger(value)) {
        throw new Error(`${column} is too large on row ${rowNumber}.`);
      }

      return value;
    };

    const impressions = parseCount("impressions");
    const visits = parseCount("visits");
    const conversions = parseCount("conversions");
    const spendText = row.spend?.trim() ?? "";

    if (!spendText || !Number.isFinite(Number(spendText))) {
      throw new Error(`Invalid spend on row ${rowNumber}.`);
    }

    const spend = Number(spendText);

    if (spend < 0) {
      throw new Error(`Spend cannot be negative on row ${rowNumber}.`);
    }

    if (visits > impressions) {
      throw new Error(`Visits exceed impressions on row ${rowNumber}.`);
    }

    if (conversions > visits) {
      throw new Error(`Conversions exceed visits on row ${rowNumber}.`);
    }

    return { campaign, impressions, visits, conversions, spend };
  });
}


function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>(demoCampaigns);
  const [budget, setBudget] = useState("10000");
  const [dataSource, setDataSource] = useState("Illustrative demo data");
  const [error, setError] = useState("");

  const totals = useMemo(() => campaigns.reduce(
    (result, campaign) => ({
      impressions: result.impressions + campaign.impressions,
      visits: result.visits + campaign.visits,
      conversions: result.conversions + campaign.conversions,
      spend: result.spend + campaign.spend,
    }),
    { impressions: 0, visits: 0, conversions: 0, spend: 0 },
  ), [campaigns]);

  const budgetValue = Number(budget);
  const budgetValid = budget.trim() !== "" &&
    Number.isFinite(budgetValue) && budgetValue >= 0;

  async function handleUpload(file?: File) {
    if (!file) return;

    setError("");
    try {
      const parsed = parseCSV(await file.text());
      if (!parsed.length) throw new Error("The CSV contains no campaign rows.");
      setCampaigns(parsed);
      setDataSource(`Uploaded: ${file.name}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the CSV.");
    }
  }


function downloadCampaignReport() {
  const headers = [
    "campaign",
    "impressions",
    "visits",
    "conversions",
    "spend",
    "conversion_rate_pct",
    "cost_per_conversion",
  ];

  const rows = campaigns.map((c) => [
    c.campaign,
    c.impressions,
    c.visits,
    c.conversions,
    c.spend.toFixed(2),
    c.visits ? ((c.conversions / c.visits) * 100).toFixed(2) : "0.00",
    c.conversions ? (c.spend / c.conversions).toFixed(2) : "",
  ]);

  const escapeCell = (value: string | number) =>
    `"${String(value).replace(/"/g, '""')}"`;

  const csv = [headers, ...rows]
    .map((row) => row.map(escapeCell).join(","))
    .join("\n");

  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8;" }),
  );

  const link = document.createElement("a");
  link.href = url;
  link.download = "econocausal_campaign_report.csv";
  link.click();
  URL.revokeObjectURL(url);
}

  const money = (value: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">E</div>
          <div>
            <strong>EconoCausal</strong>
            <span>Decision intelligence</span>
          </div>
        </div>

        <p className="nav-heading">WORKSPACE</p>
        <a className="nav-link active" href="#overview">▦ <span>Overview</span></a>
        <a className="nav-link" href="#campaign-data">▤ <span>Campaign data</span></a>
        <a className="nav-link" href="#budget">◈ <span>Budget settings</span></a>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Week 1 · Foundation
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="eyebrow">PROJECT WORKSPACE / WEEK 1</span>
            <h1>Marketing overview</h1>
            <p>Explore campaign performance and configure your budget.</p>
          </div>
          <span className="status-badge">Foundation build</span>
        </header>

        <section className="notice">
          <span>ⓘ</span>
          <div>
            <strong>{dataSource}</strong>
            <p>
              {dataSource.startsWith("Uploaded")
                ? "Charts use the uploaded CSV. These are descriptive statistics, not causal estimates."
                : "Illustrative values only. They are not actual Criteo results or validated pricing recommendations."}
            </p>
          </div>
        </section>

        <section className="metrics-grid" id="overview">
          <article className="metric-card">
            <span>Total impressions</span>
            <strong>{totals.impressions.toLocaleString("en-IN")}</strong>
            <small>Campaign reach</small>
          </article>
          <article className="metric-card">
            <span>Total visits</span>
            <strong>{totals.visits.toLocaleString("en-IN")}</strong>
            <small>Recorded campaign visits</small>
          </article>
          <article className="metric-card">
            <span>Conversions</span>
            <strong>{totals.conversions.toLocaleString("en-IN")}</strong>
            <small>Recorded conversions</small>
          </article>
          <article className="metric-card">
            <span>Conversion rate</span>
            <strong>{totals.visits ? `${(totals.conversions / totals.visits * 100).toFixed(2)}%` : "—"}</strong>
            <small>Conversions ÷ visits</small>
          </article>

<article className="metric-card">
  <span>Total campaign spend</span>
  <strong>{money(totals.spend)}</strong>
  <small>Sum of reported campaign spend</small>
</article>

<article className="metric-card">
  <span>Cost per conversion</span>
  <strong>
    {totals.conversions > 0
      ? money(totals.spend / totals.conversions)
      : "—"}
  </strong>
  <small>
    {totals.conversions > 0
      ? "Spend ÷ conversions"
      : "No conversions recorded"}
  </small>
</article>

        </section>

        <section className="content-grid">
          <article className="panel chart-panel">
            <div className="panel-heading">
              <div>
                <h2>Campaign performance</h2>
                <p>Visits and conversions by campaign</p>
              </div>
              <span className="small-tag">Plotly</span>
            </div>

            <Plot
              data={[
                {
                  type: "bar",
                  name: "Visits",
                  x: campaigns.map((c) => c.campaign),
                  y: campaigns.map((c) => c.visits),
                  marker: { color: "#7b8df5" },
                },
                {
                  type: "bar",
                  name: "Conversions",
                  x: campaigns.map((c) => c.campaign),
                  y: campaigns.map((c) => c.conversions),
                  marker: { color: "#38b89a" },
                },
              ]}
              layout={{
                autosize: true,
                barmode: "group",
                margin: { l: 45, r: 15, t: 20, b: 55 },
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                font: { family: "Inter, sans-serif", color: "#68758b" },
                legend: { orientation: "h", y: 1.13 },
                xaxis: { fixedrange: true },
                yaxis: { gridcolor: "#edf0f5", fixedrange: true },
              }}
              config={{ responsive: true, displayModeBar: false }}
              useResizeHandler
              style={{ width: "100%", height: "320px" }}
            />
          </article>

          <article className="panel budget-panel" id="budget">
            <div className="panel-heading">
              <div>
                <h2>Budget settings</h2>
                <p>Configure a marketing budget</p>
              </div>
              <span className="budget-icon">₹</span>
            </div>

            <label htmlFor="budget">Total marketing budget (INR)</label>
            <input
              id="budget"
              type="number"
              min="0"
              step="100"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
            />

            <div className="budget-summary">
              <span>Configured budget</span>
              <strong>{budgetValid ? money(budgetValue) : "Enter a valid budget"}</strong>
            </div>

            <p className="helper-text">
              This is a configuration input only. Budget allocation will be
              implemented during the optimization phase.
            </p>
          </article>
        </section>

        <section className="panel upload-panel" id="campaign-data">
          <div className="panel-heading">
            <div>
              <h2>Historical campaign data</h2>
              <p>Upload a CSV to replace the illustrative data.</p>
            </div>
          </div>

          <div className="upload-box">
            <div className="upload-icon">↑</div>
            <div className="upload-copy">
              <strong>Select a campaign CSV</strong>
              <span>Required columns: campaign, impressions, visits, conversions, spend</span>
            </div>
            <label className="upload-button">
              Choose CSV
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => {
                  void handleUpload(e.target.files?.[0]);
                  e.currentTarget.value = "";
                }}
              />
            </label>
          </div>

          {error && <p className="error-message" role="alert">{error}</p>}

<button
  type="button"
  className="export-button"
  onClick={downloadCampaignReport}
>
  Download campaign report
</button>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Impressions</th>
                  <th>Visits</th>
                  <th>Conversions</th>
                  <th>Spend</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => (
                  <tr key={campaign.campaign}>
                    <td>{campaign.campaign}</td>
                    <td>{campaign.impressions.toLocaleString("en-IN")}</td>
                    <td>{campaign.visits.toLocaleString("en-IN")}</td>
                    <td>{campaign.conversions.toLocaleString("en-IN")}</td>
                    <td>{money(campaign.spend)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <footer className="page-footer">
          <span>EconoCausal · Causal marketing decision support</span>
          <span>Week 1 foundation · No causal estimates yet</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
