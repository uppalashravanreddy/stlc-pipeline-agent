"""
Token Analytics — reads all JSONL log files and generates a visual HTML report.

Usage:
  python scripts/token_analytics.py                  # all runs
  python scripts/token_analytics.py --ticket KAN-28  # single story

Output:
  output/token_report_<ts>.html  — open in browser
"""
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

LOGS_DIR   = Path(__file__).parent.parent / "logs"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Anthropic Sonnet pricing (per million tokens)
PRICE_INPUT       = 3.00   # $ per 1M input tokens
PRICE_OUTPUT      = 15.00  # $ per 1M output tokens
PRICE_INPUT_CACHE = 0.30   # $ per 1M cached input tokens (90% cheaper)

PHASE_LABELS = {
    "analysis":  "Phase 0+1 — Classify + Test Plan",
    "generation": "Phase 2+3 — Test Cases + Review",
    "automation": "Phase 4+5 — Automation + Review",
}


def load_runs(ticket_filter: str = None) -> list[dict]:
    runs = []
    for log_file in sorted(LOGS_DIR.glob("*.jsonl")):
        if ticket_filter and ticket_filter.upper() not in log_file.name.upper():
            continue
        try:
            events = [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]
            run = parse_run(events, log_file.name)
            if run:
                runs.append(run)
        except Exception:
            continue
    return runs


def parse_run(events: list[dict], filename: str) -> dict | None:
    start = next((e for e in events if e.get("event") == "pipeline_start"), None)
    end   = next((e for e in events if e.get("event") == "pipeline_complete"), None)
    if not start:
        return None

    feature = start.get("feature", filename)
    ts      = start.get("ts", "")[:19]

    # Collect per-agent token totals
    agents = defaultdict(lambda: {"iterations": 0, "in": 0, "out": 0, "calls": []})
    for e in events:
        agent = e.get("agent")
        if not agent:
            continue
        if e.get("event", "").startswith("iter"):
            agents[agent]["iterations"] += 1
            agents[agent]["in"]  += e.get("tokens_in", 0)
            agents[agent]["out"] += e.get("tokens_out", 0)
            agents[agent]["calls"].append({
                "iter":  e.get("iteration", 0),
                "in":    e.get("tokens_in", 0),
                "out":   e.get("tokens_out", 0),
                "stop":  e.get("stop_reason", ""),
            })

    total_in  = sum(a["in"]  for a in agents.values())
    total_out = sum(a["out"] for a in agents.values())
    cost      = (total_in * PRICE_INPUT + total_out * PRICE_OUTPUT) / 1_000_000

    # Estimate prompt caching savings
    # Assumption: system prompt ~600 tokens per agent, called ~iterations times
    total_iters = sum(a["iterations"] for a in agents.values())
    cacheable_per_call = 600  # system prompt tokens
    cache_saving_tokens = cacheable_per_call * max(0, total_iters - len(agents))
    cache_saving_cost   = cache_saving_tokens * (PRICE_INPUT - PRICE_INPUT_CACHE) / 1_000_000

    return {
        "feature":             feature,
        "ts":                  ts,
        "filename":            filename,
        "agents":              dict(agents),
        "total_in":            total_in,
        "total_out":           total_out,
        "cost":                cost,
        "cost_with_cache":     cost - cache_saving_cost,
        "cache_saving":        cache_saving_cost,
        "phases_done":         end.get("phases_done", "?") if end else "?",
        "test_cases":          end.get("test_cases", 0) if end else 0,
        "complete":            end is not None,
    }


def generate_html(runs: list[dict]) -> str:
    runs_json = json.dumps(runs, indent=2)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Token Analytics</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=swap">
<style>
:root{{
  --bg:#0d1117;--s1:#161b22;--s2:#1c2128;--border:#30363d;
  --blue:#58a6ff;--green:#3fb950;--amber:#e3b341;--purple:#bc8cff;--red:#f85149;
  --tp:#e6edf3;--ts:#8b949e;--tm:#484f58;
  color-scheme:dark;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--tp);font-family:'Inter',sans-serif;padding:24px 16px;}}
.page{{max-width:1000px;margin:0 auto}}
h1{{font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700;letter-spacing:-.02em}}
.sub{{font-size:12px;color:var(--ts);margin-top:4px}}
.section-title{{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:var(--tm);margin:28px 0 12px}}

/* stat tiles */
.tiles{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin-top:20px}}
.tile{{background:var(--s1);border:1px solid var(--border);border-radius:10px;padding:16px}}
.tile-label{{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--ts);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}}
.tile-value{{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}}
.tile-sub{{font-size:11px;color:var(--ts);margin-top:6px}}
.blue{{color:var(--blue)}} .green{{color:var(--green)}} .amber{{color:var(--amber)}} .purple{{color:var(--purple)}}

/* chart card */
.card{{background:var(--s1);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:16px}}
.card-title{{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;color:var(--ts);margin-bottom:16px;text-transform:uppercase;letter-spacing:.06em}}

/* bar chart */
.chart-wrap{{overflow-x:auto}}
svg text{{font-family:'JetBrains Mono',monospace;fill:var(--ts)}}
.bar-in{{fill:var(--blue);opacity:.85}}
.bar-out{{fill:var(--green);opacity:.85}}
.bar-cached{{fill:var(--purple);opacity:.85}}

/* legend */
.legend{{display:flex;gap:16px;margin-top:12px;flex-wrap:wrap}}
.legend-item{{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ts)}}
.legend-dot{{width:10px;height:10px;border-radius:2px;flex-shrink:0}}

/* runs table */
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--tm);text-align:left;padding:8px 12px;border-bottom:1px solid var(--border)}}
td{{padding:8px 12px;border-bottom:1px solid rgba(48,54,61,.5);font-variant-numeric:tabular-nums}}
tr:hover td{{background:var(--s2)}}
.ok{{color:var(--green)}} .warn{{color:var(--amber)}}

/* optimisation tips */
.tip{{background:var(--s2);border-left:3px solid var(--blue);border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:8px;font-size:12px;line-height:1.5}}
.tip b{{color:var(--tp)}}
.saving{{color:var(--green);font-family:'JetBrains Mono',monospace}}
</style>
</head>
<body>
<div class="page">
  <div style="margin-bottom:28px">
    <h1>Token Analytics</h1>
    <div class="sub">STLC Pipeline · {ts} · {len(runs)} run{"s" if len(runs)!=1 else ""} analysed</div>
  </div>
  <div id="root"></div>
</div>

<script>
const RUNS = {runs_json};
const PRICE_IN = 3.00, PRICE_OUT = 15.00, PRICE_CACHE = 0.30;

function fmt(n){{ return n.toLocaleString(); }}
function fmtCost(c){{ return '$' + c.toFixed(4); }}
function fmtPct(a,b){{ return b>0?(a/b*100).toFixed(1)+'%':'—'; }}

const totIn  = RUNS.reduce((s,r)=>s+r.total_in,0);
const totOut = RUNS.reduce((s,r)=>s+r.total_out,0);
const totCost= RUNS.reduce((s,r)=>s+r.cost,0);
const totSave= RUNS.reduce((s,r)=>s+r.cache_saving,0);

const root = document.getElementById('root');

// ── Stat tiles ──────────────────────────────────────────────────────────────
root.innerHTML += `
<div class="section-title">Pipeline Totals (all runs)</div>
<div class="tiles">
  <div class="tile"><div class="tile-label">Total Input Tokens</div>
    <div class="tile-value blue">${{fmt(totIn)}}</div>
    <div class="tile-sub">Context sent to Claude</div></div>
  <div class="tile"><div class="tile-label">Total Output Tokens</div>
    <div class="tile-value green">${{fmt(totOut)}}</div>
    <div class="tile-sub">Claude's generated text</div></div>
  <div class="tile"><div class="tile-label">Total Cost</div>
    <div class="tile-value amber">${{fmtCost(totCost)}}</div>
    <div class="tile-sub">$3/M in · $15/M out</div></div>
  <div class="tile"><div class="tile-label">With Prompt Caching</div>
    <div class="tile-value purple">${{fmtCost(totCost-totSave)}}</div>
    <div class="tile-sub">Save ~${{fmtCost(totSave)}} per run</div></div>
</div>`;

// ── Per-phase bar chart (latest run) ────────────────────────────────────────
if (RUNS.length > 0) {{
  const run = RUNS[RUNS.length-1];
  const agents = Object.entries(run.agents);
  const W=700, H=220, PL=160, PR=20, PT=20, PB=40;
  const chartW=W-PL-PR, chartH=H-PT-PB;
  const maxVal = Math.max(...agents.flatMap(([,a])=>[a.in,a.out]));
  const barW = Math.floor(chartW/agents.length);
  const pad = 8;

  let bars='', labels='', yAxis='';
  const ticks = 5;
  for(let i=0;i<=ticks;i++){{
    const v = Math.round(maxVal*i/ticks);
    const y = PT + chartH - chartH*i/ticks;
    yAxis += `<line x1="${{PL}}" x2="${{W-PR}}" y1="${{y}}" y2="${{y}}" stroke="var(--border)" stroke-width="1" stroke-dasharray="4,4"/>`;
    yAxis += `<text x="${{PL-8}}" y="${{y+4}}" text-anchor="end" font-size="10">${{fmt(v)}}</text>`;
  }}

  agents.forEach(([name, data], i) => {{
    const x = PL + i*barW + pad;
    const bw = (barW - pad*3) / 2;
    const hIn  = data.in  > 0 ? chartH * data.in  / maxVal : 0;
    const hOut = data.out > 0 ? chartH * data.out / maxVal : 0;
    const inCost  = (data.in  * PRICE_IN  / 1e6).toFixed(4);
    const outCost = (data.out * PRICE_OUT / 1e6).toFixed(4);

    bars += `<rect class="bar-in"  x="${{x}}"       y="${{PT+chartH-hIn}}"  width="${{bw}}" height="${{hIn}}"
      title="In: ${{fmt(data.in)}} tokens · $${{inCost}}"/>`;
    bars += `<rect class="bar-out" x="${{x+bw+2}}"  y="${{PT+chartH-hOut}}" width="${{bw}}" height="${{hOut}}"
      title="Out: ${{fmt(data.out)}} tokens · $${{outCost}}"/>`;

    const shortName = name==='analysis'?'Phase 0+1':name==='generation'?'Phase 2+3':'Phase 4+5';
    labels += `<text x="${{x+bw}}" y="${{H-10}}" text-anchor="middle" font-size="10">${{shortName}}</text>`;
    labels += `<text x="${{x+bw}}" y="${{PT+chartH-Math.max(hIn,hOut)-6}}" text-anchor="middle" font-size="10" fill="var(--ts)">
      ${{fmtCost((data.in*PRICE_IN+data.out*PRICE_OUT)/1e6)}}</text>`;
  }});

  root.innerHTML += `
  <div class="section-title">Token Consumption by Phase — ${{run.feature.split(':')[0]}}</div>
  <div class="card">
    <div class="card-title">Input vs Output tokens per agent (latest run)</div>
    <div class="chart-wrap">
      <svg width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}" style="max-width:100%;overflow:visible">
        ${{yAxis}}${{bars}}${{labels}}
        <line x1="${{PL}}" x2="${{PL}}" y1="${{PT}}" y2="${{PT+chartH}}" stroke="var(--border)" stroke-width="1"/>
        <line x1="${{PL}}" x2="${{W-PR}}" y1="${{PT+chartH}}" y2="${{PT+chartH}}" stroke="var(--border)" stroke-width="1"/>
      </svg>
    </div>
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:var(--blue)"></div>Input tokens (context sent)</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Output tokens (generated)</div>
    </div>
  </div>`;
}}

// ── Iteration growth chart (shows why in grows) ─────────────────────────────
if (RUNS.length > 0) {{
  const run = RUNS[RUNS.length-1];
  const allCalls = Object.entries(run.agents).flatMap(([agent, data]) =>
    data.calls.map(c => ({{ ...c, agent }}))
  );
  if (allCalls.length > 0) {{
    const W=700,H=180,PL=100,PR=20,PT=20,PB=30;
    const chartW=W-PL-PR, chartH=H-PT-PB;
    const maxIn = Math.max(...allCalls.map(c=>c.in));
    const pointW = chartW / (allCalls.length - 1 || 1);

    const colors = {{analysis:'var(--blue)',generation:'var(--green)',automation:'var(--amber)'}};
    let paths = {{}}, dots = '';
    allCalls.forEach((c,i) => {{
      const x = PL + i*pointW;
      const y = PT + chartH - chartH*c.in/maxIn;
      if (!paths[c.agent]) paths[c.agent] = `M${{x}},${{y}}`;
      else paths[c.agent] += ` L${{x}},${{y}}`;
      dots += `<circle cx="${{x}}" cy="${{y}}" r="4" fill="${{colors[c.agent]||'var(--ts)'}}"
        title="${{c.agent}} iter${{c.iter}}: in=${{fmt(c.in)}} out=${{fmt(c.out)}} (${{c.stop}})"/>`;
    }});

    let lines = '';
    Object.entries(paths).forEach(([agent, path]) => {{
      lines += `<path d="${{path}}" fill="none" stroke="${{colors[agent]||'var(--ts)'}}" stroke-width="2"/>`;
    }});

    let yTicks = '';
    for(let i=0;i<=4;i++) {{
      const v = Math.round(maxIn*i/4);
      const y = PT + chartH - chartH*i/4;
      yTicks += `<line x1="${{PL}}" x2="${{W-PR}}" y1="${{y}}" y2="${{y}}" stroke="var(--border)" stroke-width="1" stroke-dasharray="4,4"/>`;
      yTicks += `<text x="${{PL-6}}" y="${{y+4}}" text-anchor="end" font-size="10">${{fmt(v)}}</text>`;
    }}

    root.innerHTML += `
    <div class="card">
      <div class="card-title">Input token growth per iteration — why context accumulates</div>
      <div class="chart-wrap">
        <svg width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}" style="max-width:100%;overflow:visible">
          ${{yTicks}}${{lines}}${{dots}}
          <line x1="${{PL}}" x2="${{PL}}" y1="${{PT}}" y2="${{PT+chartH}}" stroke="var(--border)" stroke-width="1"/>
          <line x1="${{PL}}" x2="${{W-PR}}" y1="${{PT+chartH}}" y2="${{PT+chartH}}" stroke="var(--border)" stroke-width="1"/>
        </svg>
      </div>
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:var(--blue)"></div>Analysis</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Generation</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--amber)"></div>Automation</div>
      </div>
      <div style="font-size:11px;color:var(--ts);margin-top:10px">
        Each step appends the previous response to messages[] — input grows because the agent needs its own history.
        Between agents, summary_for_next_agent() compresses this to prevent O(n) growth across phases.
      </div>
    </div>`;
  }}
}}

// ── Optimisation tips ───────────────────────────────────────────────────────
root.innerHTML += `<div class="section-title">Token Optimisation — Current vs Opportunities</div>`;

const latestRun = RUNS[RUNS.length-1];
if (latestRun) {{
  const totalIn  = latestRun.total_in;
  const totalOut = latestRun.total_out;
  const totalCost= latestRun.cost;
  const iters    = Object.values(latestRun.agents).reduce((s,a)=>s+a.iterations,0);
  const cacheSave= latestRun.cache_saving;

  root.innerHTML += `
  <div class="card">
    <div class="tip">
      <b>✅ Already applied — Summary compression (summary_for_next_agent)</b><br>
      Instead of passing full conversation history between agents, only structured phase outputs are sent.
      Estimated saving: <span class="saving">~30,000 input tokens per run</span> vs passing raw history.
    </div>
    <div class="tip">
      <b>✅ Already applied — Hard stop (max_iterations=8)</b><br>
      Prevents runaway loops. Without it, a confused agent could accumulate
      unbounded input tokens across infinite iterations.
    </div>
    <div class="tip">
      <b>🔧 Next — Prompt Caching</b><br>
      System prompt (~600 tokens) is re-sent on every API call.
      With cache_control: ephemeral, it's stored after the first call and costs $0.30/M instead of $3/M.<br>
      This run: ${{iters}} API calls × 600 tokens = ${{fmt(iters*600)}} cacheable tokens.
      <span class="saving">Projected saving: ${{fmtCost(cacheSave)}} this run / ~${{(cacheSave*100).toFixed(2)}} per 100 runs.</span>
    </div>
    <div class="tip">
      <b>🔧 Next — Reduce tool schema size</b><br>
      Tool JSON schemas are included in every API call (~800 tokens for complex schemas).
      Shorter descriptions = lower input tokens on every iteration.
    </div>
    <div class="tip">
      <b>🔧 Next — Agent model mapping</b><br>
      Phase 3 (review) and Phase 5 (automation review) don't need Sonnet — they receive
      fully-structured input and score against a rubric. Switching to Haiku saves
      <span class="saving">~$0.08 per run</span> on review phases alone.
    </div>
  </div>`;
}}

// ── Runs table ───────────────────────────────────────────────────────────────
root.innerHTML += `<div class="section-title">All Runs</div>
<div class="card">
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Story</th><th>Date</th><th>Phases</th>
      <th>Input tokens</th><th>Output tokens</th>
      <th>Cost</th><th>With Cache</th><th>Status</th>
    </tr></thead>
    <tbody id="runs-body"></tbody>
  </table></div>
</div>`;

const tbody = document.getElementById('runs-body');
RUNS.slice().reverse().forEach(run => {{
  const tr = document.createElement('tr');
  const story = run.feature.split(':')[0] || run.filename.split('_')[0];
  tr.innerHTML = `
    <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${{story}}</td>
    <td style="color:var(--ts)">${{run.ts}}</td>
    <td style="color:var(--ts)">${{run.phases_done}}/5</td>
    <td class="blue">${{fmt(run.total_in)}}</td>
    <td class="green">${{fmt(run.total_out)}}</td>
    <td class="amber">${{fmtCost(run.cost)}}</td>
    <td class="purple">${{fmtCost(run.cost_with_cache)}}</td>
    <td class="${{run.complete?'ok':'warn'}}">${{run.complete?'✅ Complete':'⚠️ Partial'}}</td>`;
  tbody.appendChild(tr);
}});
</script>
</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="STLC Token Analytics")
    parser.add_argument("--ticket", default=None, help="Filter by ticket ID e.g. KAN-28")
    args = parser.parse_args()

    print(f"\nReading logs from {LOGS_DIR}...")
    runs = load_runs(args.ticket)

    if not runs:
        print("No log files found. Run the pipeline first: python main.py --ticket KAN-28")
        return

    # Print console summary
    print(f"\n{'='*60}")
    print(f"  TOKEN ANALYTICS — {len(runs)} run(s)")
    print(f"{'='*60}")
    for run in runs:
        cost_save = run['cache_saving']
        print(f"\n  {run['feature'][:50]}")
        print(f"  Date    : {run['ts']}")
        print(f"  Phases  : {run['phases_done']}/5  |  Test cases: {run['test_cases']}")
        print(f"  Input   : {run['total_in']:>8,} tokens  (${run['total_in']*PRICE_INPUT/1e6:.4f})")
        print(f"  Output  : {run['total_out']:>8,} tokens  (${run['total_out']*PRICE_OUTPUT/1e6:.4f})")
        print(f"  Cost    : ${run['cost']:.4f}  →  with caching: ${run['cost_with_cache']:.4f}  (save ${cost_save:.4f})")

        for agent, data in run['agents'].items():
            label = {"analysis": "Phase 0+1", "generation": "Phase 2+3", "automation": "Phase 4+5"}.get(agent, agent)
            print(f"    {label:<20} in={data['in']:>7,}  out={data['out']:>6,}  iters={data['iterations']}")

    # Write HTML report
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = OUTPUT_DIR / f"token_report_{ts}.html"
    html_path.write_text(generate_html(runs), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"  Report → {html_path}")
    print(f"  Open in browser: code {html_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
