import { useEffect, useMemo, useState } from 'react'
import {
  FileSpreadsheet,
  History,
  LayoutDashboard,
  Loader2,
  LogOut,
  Receipt,
  Rocket,
  Upload,
} from 'lucide-react'
import { apiUrl } from './api'

const AUTH_KEY = 'invoiceiq_session'
const DEMO_EMAIL = 'demo@college.edu'
const DEMO_PASS = 'demo123'

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'extract', label: 'Extract Invoice', icon: Receipt },
  { id: 'history', label: 'History', icon: History },
  { id: 'upcoming', label: 'Upcoming', icon: Rocket },
]

const UPCOMING = [
  {
    title: 'Multi-page PDF extraction',
    detail: 'Process multi-page invoices and merge header fields with line items across pages.',
  },
  {
    title: 'Human correction & export',
    detail: 'Allow reviewers to edit extracted fields and export CSV/JSON for AP systems.',
  },
  {
    title: 'Line-item table parsing',
    detail: 'Improve detection of tabular rows (qty, unit price, amount) on scanned invoices.',
  },
  {
    title: 'Confidence calibration',
    detail: 'Surface low-confidence fields for review and reduce false totals on noisy OCR.',
  },
]

function loadSession() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY) || 'null')
  } catch {
    return null
  }
}

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState(DEMO_EMAIL)
  const [password, setPassword] = useState(DEMO_PASS)
  const [err, setErr] = useState('')

  function submit(e) {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      setErr('Enter email and password.')
      return
    }
    const session = { email: email.trim(), at: Date.now() }
    localStorage.setItem(AUTH_KEY, JSON.stringify(session))
    onLogin(session)
  }

  return (
    <div className="min-h-full flex items-center justify-center p-6">
      <form onSubmit={submit} className="ops-card w-full max-w-md p-8 pop">
        <p className="mono text-[10px] uppercase tracking-[0.25em] text-[var(--accent)]">Finance ops</p>
        <h1 className="display text-4xl mt-2">InvoiceIQ</h1>
        <p className="text-[var(--muted)] mt-3 text-sm">
          Sign in to extract vendor, totals, and line items from real invoices.
        </p>
        <label className="block text-xs text-[var(--muted)] mt-7">Work email</label>
        <input
          className="mt-1 w-full rounded-lg bg-black/30 border border-[var(--line)] px-3 py-2.5 text-sm"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          type="email"
        />
        <label className="block text-xs text-[var(--muted)] mt-4">Password</label>
        <input
          className="mt-1 w-full rounded-lg bg-black/30 border border-[var(--line)] px-3 py-2.5 text-sm"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
        />
        {err && <p className="mt-3 text-sm text-[var(--danger)]">{err}</p>}
        <button
          type="submit"
          className="mt-6 w-full rounded-full bg-[var(--accent)] text-[#062016] py-2.5 text-sm font-bold"
        >
          Continue to ops
        </button>
        <p className="mt-4 text-xs text-[var(--muted)] mono">
          {DEMO_EMAIL} / {DEMO_PASS}
        </p>
      </form>
    </div>
  )
}

function Shell({ page, setPage, children, badge, user, onLogout }) {
  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-[var(--line)] bg-[var(--charcoal)]/90 backdrop-blur sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[var(--accent)]/20 text-[var(--accent)] flex items-center justify-center">
              <Receipt size={18} />
            </div>
            <div>
              <h1 className="display text-lg leading-none">InvoiceIQ</h1>
              <p className="text-[10px] text-[var(--muted)] mono mt-0.5">AP extraction desk</p>
            </div>
          </div>
          <nav className="flex flex-wrap gap-1 p-1 rounded-full bg-black/30 border border-[var(--line)]">
            {NAV.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setPage(id)}
                className={`tab inline-flex items-center gap-1.5 px-3 py-1.5 text-xs ${
                  page === id ? 'active' : 'text-[var(--muted)]'
                }`}
              >
                <Icon size={13} />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
            <span className="mono text-[var(--accent)] hidden md:inline">{badge}</span>
            <span className="hidden lg:inline">{user?.email}</span>
            <button
              onClick={onLogout}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--line)] px-3 py-1.5 hover:border-[var(--accent)]"
            >
              <LogOut size={13} /> Logout
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-7">{children}</main>
    </div>
  )
}

function StatPill({ label, value }) {
  return (
    <div className="ops-card px-4 py-4">
      <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{label}</p>
      <p className="display text-3xl mt-1 mono tabular-nums text-[var(--accent)]">{value}</p>
    </div>
  )
}

export default function App() {
  const [session, setSession] = useState(() => loadSession())
  const [page, setPage] = useState('dashboard')
  const [stats, setStats] = useState(null)
  const [history, setHistory] = useState([])
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState('')
  const [step, setStep] = useState(1)

  const badge = useMemo(() => {
    if (!stats) return 'CONNECTING'
    return stats.demo_mode ? 'OCR PIPELINE' : 'LIVE VLM'
  }, [stats])

  async function refresh() {
    try {
      const [s, h] = await Promise.all([
        fetch(apiUrl('/api/stats')).then((r) => r.json()),
        fetch(apiUrl('/api/extractions')).then((r) => r.json()),
      ])
      setStats(s)
      setHistory(h)
      setError('')
    } catch {
      setError('Backend unreachable. Start API on port 8003 with DEMO_MODE=1.')
    }
  }

  useEffect(() => {
    if (session) refresh()
  }, [session])

  function logout() {
    localStorage.removeItem(AUTH_KEY)
    setSession(null)
    setPage('dashboard')
  }

  async function onUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setError('')
    setStep(2)
    if (file.type.startsWith('image/')) {
      setPreview(URL.createObjectURL(file))
    } else {
      setPreview('')
    }
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(apiUrl('/api/extract'), { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Extraction failed')
      setResult(data)
      setStep(3)
      setPage('extract')
      await refresh()
    } catch (err) {
      setError(err.message)
      setStep(1)
    } finally {
      setBusy(false)
      e.target.value = ''
    }
  }

  if (!session) return <LoginPage onLogin={setSession} />

  return (
    <Shell page={page} setPage={setPage} badge={badge} user={session} onLogout={logout}>
      {error && (
        <div className="mb-4 rounded-xl border border-[var(--danger)]/40 bg-[var(--danger)]/10 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {page === 'dashboard' && (
        <div className="space-y-6 pop">
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="mono text-[10px] uppercase tracking-[0.2em] text-[var(--accent)]">AP overview</p>
              <h2 className="display text-4xl mt-1">Extraction ops</h2>
              <p className="text-[var(--muted)] mt-2 text-sm max-w-xl">
                KPIs and recent runs only. Upload invoices on the Extract workspace.
              </p>
            </div>
            <button
              onClick={() => setPage('extract')}
              className="rounded-full bg-[var(--accent)] text-[#062016] px-5 py-2.5 text-sm font-bold"
            >
              Extract Invoice →
            </button>
          </header>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <StatPill label="Extractions" value={stats?.extractions ?? '—'} />
            <StatPill label="Avg fields" value={stats?.avg_fields ?? '—'} />
            <StatPill
              label="Amount sum"
              value={stats ? Number(stats.total_amount_sum || 0).toLocaleString() : '—'}
            />
            <StatPill
              label="Doc types"
              value={stats ? Object.keys(stats.by_type || {}).length : '—'}
            />
          </div>
          <section className="ops-card p-5">
            <div className="flex items-center gap-2 text-[var(--accent)]">
              <FileSpreadsheet size={16} />
              <h3 className="font-bold">Recent extractions</h3>
            </div>
            <ul className="mt-4 space-y-3">
              {(stats?.recent || []).length === 0 && (
                <li className="text-sm text-[var(--muted)]">No invoices yet.</li>
              )}
              {(stats?.recent || []).map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between text-sm border-b border-[var(--line)] pb-3"
                >
                  <span>{r.filename}</span>
                  <span className="text-[var(--muted)] mono text-xs">
                    {r.doc_type} · {r.total_amount ?? '—'}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}

      {page === 'extract' && (
        <div className="space-y-6 pop">
          <header>
            <p className="mono text-[10px] uppercase tracking-[0.2em] text-[var(--accent)]">Workspace</p>
            <h2 className="display text-4xl mt-1">Extract invoice</h2>
          </header>

          <div className="ops-card px-5 py-4 flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className={`step-dot ${step >= 1 ? (step > 1 ? 'done' : 'on') : ''}`}>1</span>
              <span className={step === 1 ? 'text-[var(--accent)] font-semibold' : 'text-[var(--muted)]'}>
                Upload
              </span>
            </div>
            <div className="h-px w-8 bg-[var(--line)]" />
            <div className="flex items-center gap-2">
              <span className={`step-dot ${step >= 2 ? (step > 2 ? 'done' : 'on') : ''}`}>2</span>
              <span className={step === 2 ? 'text-[var(--accent)] font-semibold' : 'text-[var(--muted)]'}>
                Process
              </span>
            </div>
            <div className="h-px w-8 bg-[var(--line)]" />
            <div className="flex items-center gap-2">
              <span className={`step-dot ${step >= 3 ? 'on' : ''}`}>3</span>
              <span className={step === 3 ? 'text-[var(--accent)] font-semibold' : 'text-[var(--muted)]'}>
                Review fields
              </span>
            </div>
            <label className="ml-auto inline-flex items-center gap-2 rounded-full bg-[var(--accent)] text-[#062016] px-4 py-2 text-sm font-bold cursor-pointer">
              {busy ? <Loader2 className="animate-spin" size={16} /> : <Upload size={16} />}
              Upload invoice
              <input type="file" accept=".png,.jpg,.jpeg,.pdf,.tiff" className="hidden" onChange={onUpload} />
            </label>
          </div>

          <div className="grid lg:grid-cols-2 gap-4 min-h-[420px]">
            <section className="ops-card p-5 flex flex-col">
              <p className="text-xs uppercase tracking-wider text-[var(--muted)] mb-3">Document preview</p>
              <div className="flex-1 flex items-center justify-center rounded-xl bg-black/25 border border-dashed border-[var(--line)] min-h-72">
                {preview ? (
                  <img src={preview} alt="Invoice preview" className="max-h-[400px] rounded-lg object-contain" />
                ) : (
                  <p className="text-sm text-[var(--muted)] text-center px-6">
                    Upload a PNG/JPG/PDF. Text PDFs use native extract; images use Tesseract OCR.
                  </p>
                )}
              </div>
            </section>

            <section className="ops-card p-5 space-y-4 overflow-auto">
              <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Extracted fields</p>
              {!result && (
                <p className="text-sm text-[var(--muted)]">Fields from your file appear here after upload.</p>
              )}
              {result && (
                <>
                  <div className="flex flex-wrap gap-2 text-[10px] mono">
                    <span className="rounded-full border border-[var(--line)] px-3 py-1">{result.filename}</span>
                    <span className="rounded-full border border-[var(--line)] px-3 py-1">{result.document_type}</span>
                    <span className="rounded-full border border-[var(--accent)]/40 text-[var(--accent)] px-3 py-1">
                      Total: {result.total_amount ?? '—'}
                    </span>
                    <span className="rounded-full border border-[var(--line)] px-3 py-1">Mode: {result.mode}</span>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {(result.fields || []).map((f) => (
                      <div key={f.field_name} className="rounded-xl border border-[var(--line)] bg-black/20 p-3">
                        <p className="text-[10px] text-[var(--muted)] uppercase tracking-wide">{f.field_name}</p>
                        <p className="mt-1 font-semibold text-sm">{f.value}</p>
                        <p className="text-[10px] text-[var(--muted)] mt-1 mono">
                          {f.category} · {Math.round(f.confidence * 100)}%
                        </p>
                      </div>
                    ))}
                  </div>
                  {(result.line_items || []).length > 0 && (
                    <div>
                      <p className="text-xs uppercase tracking-wider text-[var(--muted)] mb-2">Line items</p>
                      <div className="overflow-hidden rounded-xl border border-[var(--line)]">
                        <table className="w-full text-sm">
                          <thead className="text-left text-[var(--muted)] bg-black/25 text-xs">
                            <tr>
                              <th className="p-3">Description</th>
                              <th className="p-3">Qty</th>
                              <th className="p-3">Amount</th>
                            </tr>
                          </thead>
                          <tbody>
                            {result.line_items.map((li, i) => (
                              <tr key={i} className="border-t border-[var(--line)]">
                                <td className="p-3">{li.description}</td>
                                <td className="p-3 mono">{li.quantity}</td>
                                <td className="p-3 mono">{li.amount}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}
            </section>
          </div>
        </div>
      )}

      {page === 'history' && (
        <div className="space-y-6 pop">
          <h2 className="display text-4xl">Extraction history</h2>
          <div className="ops-card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="text-left text-[var(--muted)] border-b border-[var(--line)] bg-black/20">
                <tr>
                  <th className="p-4">File</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Fields</th>
                  <th className="p-4">Total</th>
                  <th className="p-4">When</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-b border-[var(--line)]/60">
                    <td className="p-4">{h.filename}</td>
                    <td className="p-4">{h.doc_type}</td>
                    <td className="p-4 mono">{h.field_count}</td>
                    <td className="p-4 mono">{h.total_amount ?? '—'}</td>
                    <td className="p-4 text-[var(--muted)]">
                      {h.created_at ? new Date(h.created_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
                {history.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-6 text-[var(--muted)]">
                      No history yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {page === 'upcoming' && (
        <div className="space-y-6 pop">
          <header>
            <h2 className="display text-4xl">Upcoming features</h2>
            <p className="text-[var(--muted)] mt-2 text-sm max-w-2xl">
              Planned enhancements — not available in the current release.
            </p>
          </header>
          <div className="grid md:grid-cols-2 gap-4">
            {UPCOMING.map((item) => (
              <article key={item.title} className="ops-card p-5">
                <p className="mono text-[10px] uppercase tracking-wider text-[var(--warn)]">Not implemented</p>
                <h3 className="display text-xl mt-2">{item.title}</h3>
                <p className="text-sm text-[var(--muted)] mt-3 leading-relaxed">{item.detail}</p>
              </article>
            ))}
          </div>
        </div>
      )}
    </Shell>
  )
}
