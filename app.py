from __future__ import annotations

import base64
import binascii
import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Vercel executes this file from the repository root. Adding src explicitly
# keeps local `uvicorn app:app` and Vercel's Python runtime identical even when
# the project package itself has not been installed editable.
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cherry_memory_ledger.decision_engine import decide, default_treatment  # noqa: E402
from cherry_memory_ledger.memory_gateway import SibylMemoryGateway  # noqa: E402
from cherry_memory_ledger.models import (  # noqa: E402
    AccountingDecisionMemory,
    AccountingTreatment,
    Transaction,
)

app = FastAPI(
    title="Cherry Memory Ledger",
    description="Load-bearing accounting memory across genuinely fresh sessions.",
    version="0.2.1",
)

MAX_SNAPSHOT_BYTES = 3 * 1024 * 1024


class TransactionPayload(BaseModel):
    business_id: str = "demo-company"
    transaction_id: str
    description: str
    supplier: str | None = None
    amount: Decimal
    currency: str = "GBP"


class RememberPayload(BaseModel):
    memory_snapshot: str | None = None
    transaction: TransactionPayload
    original_category: str = "General Expenses"
    approved_category: str
    vat_treatment: str | None = None
    reconciliation_action: str | None = None
    rationale: str
    approved_by_role: str = "accountant"
    evidence_requirements: list[str] = Field(default_factory=list)
    scope_conditions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RecommendPayload(BaseModel):
    memory_snapshot: str | None = None
    transaction: TransactionPayload


def _to_transaction(payload: TransactionPayload) -> Transaction:
    return Transaction(
        business_id=payload.business_id,
        transaction_id=payload.transaction_id,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        supplier=payload.supplier,
        occurred_at=datetime.now(timezone.utc),
    )


def _restore_snapshot(snapshot: str | None, db_path: Path) -> None:
    if not snapshot:
        return
    try:
        raw = base64.b64decode(snapshot.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid Sibyl memory snapshot") from exc
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise HTTPException(status_code=413, detail="Sibyl memory snapshot is too large")
    db_path.write_bytes(raw)


def _encode_snapshot(db_path: Path) -> str:
    """Checkpoint Sibyl's WAL then encode the durable SQLite file.

    Vercel functions have an ephemeral filesystem. For this hackathon web demo
    the browser carries the official Sibyl SQLite file between requests in
    localStorage. Each API call therefore constructs a genuinely new
    MemoryClient from persisted bytes rather than relying on process memory.
    """
    if not db_path.exists():
        return ""

    # Sibyl enables WAL mode. Checkpointing is essential before we take the
    # portable snapshot or a just-written entity could still live in -wal.
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()

    raw = db_path.read_bytes()
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise HTTPException(status_code=507, detail="Sibyl memory snapshot exceeded demo limit")
    return base64.b64encode(raw).decode("ascii")


@contextmanager
def _memory_workspace(snapshot: str | None) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="cherry-sibyl-") as workdir:
        db_path = Path(workdir) / "memory.db"
        _restore_snapshot(snapshot, db_path)
        yield db_path


def _treatment_dict(treatment: AccountingTreatment) -> dict[str, object]:
    return {
        "category": treatment.category,
        "vat_treatment": treatment.vat_treatment,
        "reconciliation_action": treatment.reconciliation_action,
        "evidence_requirements": list(treatment.evidence_requirements),
    }


def _build_commit() -> str:
    """Expose the deployed commit for the hackathon's on-screen proof."""
    return os.getenv("VERCEL_GIT_COMMIT_SHA", "local")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "cherry-memory-ledger",
        "memory": "sibyl",
        "commit_sha": _build_commit(),
    }


@app.post("/api/memory/remember")
def remember(payload: RememberPayload) -> dict[str, object]:
    transaction = _to_transaction(payload.transaction)
    baseline = default_treatment(transaction)

    memory = AccountingDecisionMemory(
        memory_id=None,
        business_id=transaction.business_id,
        supplier=transaction.supplier,
        source_transaction_id=transaction.transaction_id,
        source_description=transaction.description,
        original_treatment=AccountingTreatment(
            category=payload.original_category,
            vat_treatment=baseline.vat_treatment,
            reconciliation_action=baseline.reconciliation_action,
            evidence_requirements=baseline.evidence_requirements,
        ),
        approved_treatment=AccountingTreatment(
            category=payload.approved_category,
            vat_treatment=payload.vat_treatment,
            reconciliation_action=payload.reconciliation_action,
            evidence_requirements=tuple(payload.evidence_requirements),
        ),
        rationale=payload.rationale,
        approved_by_role=payload.approved_by_role,
        approved_at=datetime.now(timezone.utc),
        scope_conditions=tuple(payload.scope_conditions),
        tags=tuple(payload.tags),
    )

    with _memory_workspace(payload.memory_snapshot) as db_path:
        gateway = SibylMemoryGateway(db_path)
        memory_id = gateway.persist_accounting_decision(memory)
        snapshot = _encode_snapshot(db_path)

    return {
        "ok": True,
        "memory_id": memory_id,
        "memory_snapshot": snapshot,
        "snapshot_bytes": len(base64.b64decode(snapshot)) if snapshot else 0,
        "sibyl_writes": ["set_entity", "write_event"],
        "message": "Accountant-approved decision persisted to Sibyl Memory.",
    }


@app.post("/api/memory/recommend")
def recommend(payload: RecommendPayload) -> dict[str, object]:
    transaction = _to_transaction(payload.transaction)

    with _memory_workspace(payload.memory_snapshot) as db_path:
        gateway = SibylMemoryGateway(db_path)
        outcome = decide(transaction, gateway)

    response: dict[str, object] = {
        "ok": True,
        "source": outcome.source,
        "used_memory": outcome.used_memory,
        "treatment": _treatment_dict(outcome.treatment),
        "rationale": outcome.rationale,
        "sibyl_reads": ["get_entity", "search_entities"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "commit_sha": _build_commit(),
    }
    if outcome.memory:
        response["memory"] = {
            "memory_id": outcome.memory.memory_id,
            "supplier": outcome.memory.supplier,
            "approved_at": outcome.memory.approved_at.isoformat(),
            "approved_by_role": outcome.memory.approved_by_role,
            "scope_conditions": list(outcome.memory.scope_conditions),
            "original_category": outcome.memory.original_treatment.category,
            "approved_category": outcome.memory.approved_treatment.category,
        }
    return response


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cherry Memory Ledger · Sibyl Hackathon</title>
  <style>
    :root {
      --ink: #191919; --muted: #6b6b67; --line: #e7e5df; --paper: #fbfaf7;
      --card: #ffffff; --accent: #b51f35; --accent2: #7e1325; --good: #176b4d;
      --good-bg: #edf8f3; --warm: #fff6df; --shadow: 0 18px 55px rgba(39,32,22,.08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--paper); color: var(--ink); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    button, input, textarea { font: inherit; }
    .shell { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
    header { padding: 28px 0 20px; border-bottom: 1px solid var(--line); background: rgba(251,250,247,.92); position: sticky; top: 0; backdrop-filter: blur(14px); z-index: 20; }
    .nav { display:flex; align-items:center; justify-content:space-between; gap:18px; }
    .brand { display:flex; align-items:center; gap:12px; min-width:0; }
    .cherry { width:36px; height:36px; border-radius:50%; background:var(--accent); box-shadow: 18px 4px 0 -9px #d44b60; position:relative; flex:0 0 auto; }
    .cherry:before { content:""; position:absolute; width:22px; height:12px; border-top:3px solid #365640; border-radius:50%; transform:rotate(-38deg); left:16px; top:-4px; }
    .brand strong { display:block; font-size:16px; }
    .brand span { color:var(--muted); font-size:12px; }
    .nav-actions { display:flex; gap:10px; align-items:center; }
    .pill { border:1px solid var(--line); background:white; border-radius:999px; padding:8px 12px; font-size:12px; color:var(--muted); white-space:nowrap; }
    .pill.good { background:var(--good-bg); color:var(--good); border-color:#cbe9dc; }
    .ghost { border:1px solid var(--line); background:white; color:var(--ink); border-radius:10px; padding:9px 12px; cursor:pointer; }
    main { padding: 58px 0 90px; }
    .hero { display:grid; grid-template-columns: 1.25fr .75fr; gap:28px; align-items:end; margin-bottom:38px; }
    .eyebrow { text-transform:uppercase; letter-spacing:.16em; font-size:12px; color:var(--accent); font-weight:700; }
    h1 { font-size:clamp(42px,7vw,82px); line-height:.94; letter-spacing:-.055em; margin:14px 0 18px; max-width:900px; }
    .lead { color:var(--muted); font-size:clamp(17px,2vw,21px); line-height:1.55; max-width:760px; margin:0; }
    .hero-note { border-left:3px solid var(--accent); padding:4px 0 4px 18px; color:var(--muted); line-height:1.5; }
    .flow { display:grid; gap:18px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:22px; box-shadow:var(--shadow); overflow:hidden; }
    .card-head { padding:22px 24px 18px; display:flex; justify-content:space-between; gap:18px; align-items:flex-start; border-bottom:1px solid var(--line); }
    .step { width:34px; height:34px; border-radius:50%; display:grid; place-items:center; color:white; background:var(--ink); font-weight:700; flex:0 0 auto; }
    .title-row { display:flex; gap:14px; align-items:flex-start; }
    h2 { margin:0 0 5px; font-size:22px; letter-spacing:-.025em; }
    .sub { margin:0; color:var(--muted); line-height:1.45; font-size:14px; }
    .session-tag { padding:7px 10px; border-radius:999px; background:#f1f0ec; color:#575752; font-size:12px; white-space:nowrap; }
    .card-body { padding:24px; }
    .grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }
    .grid.three { grid-template-columns: 1.2fr .8fr .6fr; }
    label { display:block; font-size:12px; font-weight:700; color:#55554f; margin:0 0 7px; }
    input, textarea { width:100%; border:1px solid #dedcd5; border-radius:11px; background:#fff; padding:12px 13px; color:var(--ink); outline:none; transition:.15s; }
    input:focus, textarea:focus { border-color:#bba9a4; box-shadow:0 0 0 3px rgba(181,31,53,.08); }
    textarea { min-height:86px; resize:vertical; }
    .suggestion { margin-top:18px; border:1px dashed #d6d2c8; background:#faf9f6; border-radius:14px; padding:15px 16px; display:flex; gap:14px; align-items:flex-start; }
    .suggestion b { display:block; margin-bottom:3px; }
    .muted { color:var(--muted); }
    .correction { margin-top:18px; padding-top:18px; border-top:1px solid var(--line); }
    .actions { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-top:18px; }
    .primary { border:0; background:var(--accent); color:white; border-radius:11px; padding:12px 17px; font-weight:700; cursor:pointer; box-shadow:0 8px 24px rgba(181,31,53,.18); }
    .primary:hover { background:var(--accent2); }
    .primary:disabled, .ghost:disabled { opacity:.55; cursor:not-allowed; }
    .status { font-size:13px; color:var(--muted); }
    .boundary { background:#171717; color:white; border-radius:22px; padding:26px; display:grid; grid-template-columns:1fr auto; gap:24px; align-items:center; }
    .boundary h2 { font-size:24px; }
    .boundary p { margin:8px 0 0; color:#bdbdb7; line-height:1.5; max-width:760px; }
    .boundary button { background:white; color:#171717; border:0; border-radius:11px; padding:12px 17px; font-weight:750; cursor:pointer; }
    .result { margin-top:18px; border-radius:16px; padding:18px; border:1px solid var(--line); background:#faf9f6; display:none; }
    .result.visible { display:block; }
    .result.memory { border-color:#bfe3d3; background:var(--good-bg); }
    .result.default { border-color:#ecdba9; background:var(--warm); }
    .result-top { display:flex; justify-content:space-between; gap:14px; align-items:flex-start; margin-bottom:14px; }
    .signal { font-size:11px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    .memory .signal { color:var(--good); }
    .default .signal { color:#8a6815; }
    .big-category { font-size:28px; letter-spacing:-.03em; font-weight:800; margin:3px 0; }
    .result-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .fact { background:rgba(255,255,255,.7); border-radius:11px; padding:12px; }
    .fact small { display:block; color:var(--muted); margin-bottom:4px; }
    .proof-fact { border:1px solid rgba(23,107,77,.2); }
    .debug { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:18px; }
    .debug-card { border:1px solid var(--line); border-radius:17px; padding:18px; background:#fff; }
    .debug-card h3 { margin:0 0 10px; font-size:15px; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; background:#f1f0ec; padding:2px 5px; border-radius:5px; font-size:.9em; }
    .primitive { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:6px 9px; margin:3px 4px 3px 0; color:#55554f; font-size:12px; }
    .toast { position:fixed; right:22px; bottom:22px; width:min(390px,calc(100% - 44px)); padding:15px 17px; border-radius:14px; background:#171717; color:white; box-shadow:0 20px 50px rgba(0,0,0,.25); opacity:0; transform:translateY(10px); pointer-events:none; transition:.2s; z-index:50; }
    .toast.show { opacity:1; transform:none; }
    .fineprint { color:var(--muted); font-size:12px; line-height:1.5; margin-top:28px; }
    @media (max-width: 820px) {
      .hero, .grid, .grid.three, .result-grid, .debug { grid-template-columns:1fr; }
      .boundary { grid-template-columns:1fr; }
      .nav-actions .pill { display:none; }
      main { padding-top:38px; }
      h1 { font-size:48px; }
    }
  </style>
</head>
<body>
<header>
  <div class="shell nav">
    <div class="brand">
      <div class="cherry" aria-hidden="true"></div>
      <div><strong>Cherry Memory Ledger</strong><span>Sibyl Labs hackathon build</span></div>
    </div>
    <div class="nav-actions">
      <span id="memoryBadge" class="pill">Sibyl memory: empty</span>
      <span id="sessionBadge" class="pill">Session A</span>
      <button class="ghost" onclick="resetDemo()">Reset demo</button>
    </div>
  </div>
</header>

<main class="shell">
  <section class="hero">
    <div>
      <div class="eyebrow">Load-bearing memory for accounting</div>
      <h1>Correct it once.<br>Remember it next time.</h1>
      <p class="lead">An accountant's correction becomes a durable Sibyl Memory rule. A genuinely fresh session recalls it and changes the next bookkeeping decision.</p>
    </div>
    <div class="hero-note"><strong>Judge-visible counterfactual:</strong><br>delete the memory and the same transaction falls back to General Expenses.</div>
  </section>

  <section class="flow">
    <article class="card" id="sessionA">
      <div class="card-head">
        <div class="title-row"><div class="step">1</div><div><h2>Session A · Accountant teaches Cherry</h2><p class="sub">Cherry makes a generic first-pass suggestion. The accountant corrects it and approves the rule.</p></div></div>
        <span class="session-tag">WRITE</span>
      </div>
      <div class="card-body">
        <div class="grid three">
          <div><label for="aDescription">Bank description</label><input id="aDescription" value="AMZN AWS EMEA 120.00 GBP" /></div>
          <div><label for="aSupplier">Supplier</label><input id="aSupplier" value="AWS" /></div>
          <div><label for="aAmount">Amount</label><input id="aAmount" type="number" step="0.01" value="120.00" /></div>
        </div>
        <div class="suggestion"><div>🤖</div><div><b>Cherry's no-memory suggestion</b><span class="muted">General Expenses · review VAT evidence · leave unmatched for routine review</span></div></div>
        <div class="correction">
          <div class="grid">
            <div><label for="approvedCategory">Accountant-approved category</label><input id="approvedCategory" value="Software & Cloud Services" /></div>
            <div><label for="vatTreatment">VAT treatment</label><input id="vatTreatment" value="Reclaim input VAT only when a valid VAT invoice is held" /></div>
            <div><label for="reconciliationAction">Reconciliation action</label><input id="reconciliationAction" value="Match to monthly cloud-services invoice" /></div>
            <div><label for="evidence">Evidence requirement</label><input id="evidence" value="Valid VAT invoice" /></div>
          </div>
          <div style="margin-top:16px"><label for="rationale">Why this is the right treatment</label><textarea id="rationale">AWS is an approved recurring cloud-software supplier. Use Software & Cloud Services, and reclaim VAT only when the required VAT invoice is held.</textarea></div>
          <div class="actions">
            <button id="rememberBtn" class="primary" onclick="rememberDecision()">Approve & save to Sibyl Memory</button>
            <span id="rememberStatus" class="status">Uses <code>set_entity</code> + <code>write_event</code></span>
          </div>
        </div>
      </div>
    </article>

    <section class="boundary">
      <div><h2>Fresh-session boundary</h2><p>This reload destroys this page's JavaScript state. Only the persisted Sibyl SQLite memory snapshot survives in browser storage. Session B creates a brand-new server-side <code>MemoryClient</code>.</p></div>
      <button onclick="startFreshSession()">End Session A → Start Session B</button>
    </section>

    <article class="card" id="sessionB">
      <div class="card-head">
        <div class="title-row"><div class="step">2</div><div><h2>Session B · New transaction, no re-explaining</h2><p class="sub">A related but non-identical bank transaction arrives. Cherry has to decide using whatever Sibyl remembers.</p></div></div>
        <span class="session-tag">READ</span>
      </div>
      <div class="card-body">
        <div class="grid three">
          <div><label for="bDescription">Bank description</label><input id="bDescription" value="AWS EMEA SARL 240.00 GBP" /></div>
          <div><label for="bSupplier">Supplier</label><input id="bSupplier" value="AWS" /></div>
          <div><label for="bAmount">Amount</label><input id="bAmount" type="number" step="0.01" value="240.00" /></div>
        </div>
        <div class="actions">
          <button id="recommendBtn" class="primary" onclick="runRecommendation()">Ask Cherry in this fresh session</button>
          <button class="ghost" onclick="deleteMemoryAndRetry()">Delete memory & run counterfactual</button>
          <span class="status">Uses <code>get_entity</code> + <code>search_entities</code></span>
        </div>
        <div id="result" class="result"></div>
      </div>
    </article>
  </section>

  <section class="debug">
    <div class="debug-card">
      <h3>Memory proof</h3>
      <div id="memoryMeta" class="muted">No Sibyl snapshot stored yet.</div>
    </div>
    <div class="debug-card">
      <h3>Primitives exercised by this build</h3>
      <span class="primitive">WARM entity · set_entity</span>
      <span class="primitive">exact recall · get_entity</span>
      <span class="primitive">FTS5 recall · search_entities</span>
      <span class="primitive">COLD audit · write_event</span>
    </div>
  </section>

  <p class="fineprint">Demo-safe synthetic transactions only. This prototype demonstrates memory behaviour, not tax or accounting advice. The Vercel demo carries Sibyl's checkpointed SQLite file in browser localStorage because serverless filesystems are ephemeral; all accounting memory reads/writes themselves use the official <code>sibyl-memory-client</code>.</p>
</main>
<div id="toast" class="toast"></div>

<script>
const SNAPSHOT_KEY = 'cherry-sibyl-memory-snapshot-v1';
const MEMORY_ID_KEY = 'cherry-sibyl-last-memory-id';
const PHASE_KEY = 'cherry-sibyl-demo-phase';

function snapshot() { return localStorage.getItem(SNAPSHOT_KEY) || null; }
function bytesFromBase64(value) { return value ? Math.floor(value.length * 3 / 4) : 0; }
function formatBytes(n) { return n < 1024 ? `${n} B` : `${(n/1024).toFixed(1)} KB`; }
function transaction(prefix, id) {
  return {
    business_id: 'demo-company', transaction_id: id,
    description: document.getElementById(prefix+'Description').value.trim(),
    supplier: document.getElementById(prefix+'Supplier').value.trim() || null,
    amount: document.getElementById(prefix+'Amount').value,
    currency: 'GBP'
  };
}
function toast(message) {
  const el = document.getElementById('toast'); el.textContent = message; el.classList.add('show');
  clearTimeout(window.__toastTimer); window.__toastTimer = setTimeout(()=>el.classList.remove('show'), 3200);
}
function setBusy(id, busy) { document.getElementById(id).disabled = busy; }
function refreshMemoryUI() {
  const s = snapshot(); const bytes = bytesFromBase64(s); const id = localStorage.getItem(MEMORY_ID_KEY);
  const badge = document.getElementById('memoryBadge');
  if (s) { badge.className='pill good'; badge.textContent=`Sibyl memory: ${formatBytes(bytes)}`; }
  else { badge.className='pill'; badge.textContent='Sibyl memory: empty'; }
  document.getElementById('memoryMeta').innerHTML = s
    ? `<strong>Persisted SQLite snapshot:</strong> ${formatBytes(bytes)}<br><strong>Latest rule:</strong> <code>${escapeHtml(id || 'unknown')}</code><br><span class="muted">Survives page reload; a new API request reopens it with a new Sibyl MemoryClient.</span>`
    : 'No Sibyl snapshot stored yet.';
}
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

async function api(path, payload) {
  const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

async function rememberDecision() {
  setBusy('rememberBtn', true); document.getElementById('rememberStatus').textContent='Writing to Sibyl…';
  try {
    const data = await api('/api/memory/remember', {
      memory_snapshot: snapshot(), transaction: transaction('a', 'session-a-'+Date.now()),
      original_category: 'General Expenses', approved_category: document.getElementById('approvedCategory').value.trim(),
      vat_treatment: document.getElementById('vatTreatment').value.trim(),
      reconciliation_action: document.getElementById('reconciliationAction').value.trim(),
      rationale: document.getElementById('rationale').value.trim(), approved_by_role: 'accountant',
      evidence_requirements: [document.getElementById('evidence').value.trim()].filter(Boolean),
      scope_conditions: ['Supplier is AWS', 'Valid VAT invoice required for VAT reclaim'],
      tags: ['aws','cloud','software','vat']
    });
    localStorage.setItem(SNAPSHOT_KEY, data.memory_snapshot); localStorage.setItem(MEMORY_ID_KEY, data.memory_id);
    document.getElementById('rememberStatus').innerHTML=`Saved <code>${escapeHtml(data.memory_id)}</code> using Sibyl`;
    refreshMemoryUI(); toast('Accountant correction persisted to Sibyl Memory.');
  } catch (error) { document.getElementById('rememberStatus').textContent=error.message; toast(error.message); }
  finally { setBusy('rememberBtn', false); }
}

function startFreshSession() {
  if (!snapshot()) { toast('Save the accountant correction first.'); return; }
  localStorage.setItem(PHASE_KEY, 'B');
  window.location.reload();
}

async function runRecommendation() {
  setBusy('recommendBtn', true); const result=document.getElementById('result');
  result.className='result visible'; result.innerHTML='Recalling from Sibyl Memory…';
  try {
    const data = await api('/api/memory/recommend', {memory_snapshot:snapshot(), transaction:transaction('b','session-b-'+Date.now())});
    const t=data.treatment; const m=data.memory;
    const commit=(data.commit_sha || 'local').slice(0,7);
    result.className=`result visible ${data.used_memory ? 'memory' : 'default'}`;
    result.innerHTML = `
      <div class="result-top"><div><div class="signal">${data.used_memory ? 'Recalled from Sibyl Memory' : 'No memory · default path'}</div><div class="big-category">${escapeHtml(t.category)}</div></div><div>${data.used_memory ? '🧠 ✓' : '⚠️'}</div></div>
      <div class="result-grid">
        <div class="fact"><small>VAT treatment</small>${escapeHtml(t.vat_treatment || 'Not specified')}</div>
        <div class="fact"><small>Reconciliation</small>${escapeHtml(t.reconciliation_action || 'Not specified')}</div>
        <div class="fact"><small>Why Cherry chose this</small>${escapeHtml(data.rationale)}</div>
        <div class="fact"><small>Memory trace</small>${m ? `<code>${escapeHtml(m.memory_id)}</code><br>${escapeHtml(m.approved_by_role)} · ${escapeHtml(m.approved_at)}` : 'No prior decision available'}</div>
        <div class="fact proof-fact"><small>Fresh-session proof · required for judging</small>Observed <strong>${escapeHtml(data.observed_at)}</strong><br>Deployed commit <code>${escapeHtml(commit)}</code></div>
      </div>`;
    toast(data.used_memory ? 'Fresh session changed by recalled Sibyl memory.' : 'No memory found: generic baseline used.');
  } catch (error) { result.className='result visible default'; result.textContent=error.message; toast(error.message); }
  finally { setBusy('recommendBtn', false); }
}

async function deleteMemoryAndRetry() {
  localStorage.removeItem(SNAPSHOT_KEY); localStorage.removeItem(MEMORY_ID_KEY); refreshMemoryUI();
  toast('Sibyl memory deleted. Running the counterfactual…');
  await runRecommendation();
}

function resetDemo() {
  localStorage.removeItem(SNAPSHOT_KEY); localStorage.removeItem(MEMORY_ID_KEY); localStorage.removeItem(PHASE_KEY); window.location.reload();
}

(function init(){
  refreshMemoryUI();
  const phase=localStorage.getItem(PHASE_KEY) || 'A'; document.getElementById('sessionBadge').textContent=`Session ${phase}`;
  if (phase==='B') { setTimeout(()=>document.getElementById('sessionB').scrollIntoView({behavior:'smooth', block:'center'}), 250); }
})();
</script>
</body>
</html>
"""