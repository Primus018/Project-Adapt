import { useEffect, useMemo, useState } from 'react'
import {
  FileText,
  History,
  LayoutDashboard,
  Loader2,
  LogOut,
  MessageSquareQuote,
  Rocket,
  Scale,
  Upload,
} from 'lucide-react'
import { apiUrl } from './api'

const AUTH_KEY = 'contractiq_session'
const DEMO_EMAIL = 'demo@college.edu'
const DEMO_PASS = 'demo123'

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'workspace', label: 'Corrective QA', icon: MessageSquareQuote },
  { id: 'history', label: 'History', icon: History },
  { id: 'upcoming', label: 'Upcoming', icon: Rocket },
]

const UPCOMING = [
  {
    title: 'RAG efficiency upgrades',
    detail: 'Cache embeddings, use ANN retrieval, and cut repeated NLI calls — pipeline works but is not efficient yet.',
  },
  {
    title: 'Live web-search recovery',
    detail: 'When grader returns WEB_SEARCH, query an external index and re-ground the answer.',
  },
  {
    title: 'Adaptive-RAG complexity routing',
    detail: 'Route simple vs multi-hop questions to different retrieval depths before generation.',
  },
  {
    title: 'Latency & cost study',
    detail: 'Quantify overhead of the corrective loop vs vanilla RAG at equal answer quality.',
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
      <form onSubmit={submit} className="doc-sheet w-full max-w-md p-8 fade-in">
        <div className="flex items-center gap-3 text-[var(--accent)]">
          <Scale size={22} />
          <span className="text-xs uppercase tracking-[0.28em]">Legal research desk</span>
        </div>
        <h1 className="display text-5xl mt-3 text-[var(--accent)]">ContractIQ</h1>
        <p className="text-[var(--muted)] mt-3 text-sm leading-relaxed">
          Sign in to review contracts with confidence-gated corrective RAG.
        </p>
        <label className="block text-xs uppercase tracking-wider text-[var(--muted)] mt-8">Email</label>
        <input
          className="mt-1 w-full border border-[var(--line)] bg-white px-3 py-2.5 text-sm"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          type="email"
          autoComplete="username"
        />
        <label className="block text-xs uppercase tracking-wider text-[var(--muted)] mt-4">Password</label>
        <input
          className="mt-1 w-full border border-[var(--line)] bg-white px-3 py-2.5 text-sm"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          autoComplete="current-password"
        />
        {err && <p className="mt-3 text-sm text-[var(--danger)]">{err}</p>}
        <button
          type="submit"
          className="mt-6 w-full bg-[var(--accent)] text-[var(--panel)] py-2.5 text-sm font-semibold tracking-wide"
        >
          Enter workspace
        </button>
        <p className="mt-4 text-xs text-[var(--muted)]">
          Demo: {DEMO_EMAIL} / {DEMO_PASS} (any non-empty credentials also work)
        </p>
      </form>
    </div>
  )
}

function Shell({ page, setPage, children, badge, user, onLogout }) {
  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-[var(--line)] bg-[var(--panel)]/90 backdrop-blur sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-5 py-3 flex flex-wrap items-center gap-4 justify-between">
          <div className="flex items-center gap-3">
            <Scale size={20} className="text-[var(--accent-2)]" />
            <div>
              <h1 className="display text-2xl leading-none text-[var(--accent)]">ContractIQ</h1>
              <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)] mt-0.5">
                Clause QA · Corrective RAG
              </p>
            </div>
          </div>
          <nav className="flex flex-wrap items-center gap-5 text-sm">
            {NAV.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setPage(id)}
                className={`top-link inline-flex items-center gap-1.5 pb-1 ${page === id ? 'active font-semibold' : 'text-[var(--muted)]'}`}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
            <span className="hidden sm:inline">{badge}</span>
            <span className="hidden md:inline border-l border-[var(--line)] pl-3">{user?.email}</span>
            <button
              onClick={onLogout}
              className="inline-flex items-center gap-1 text-[var(--accent)] hover:text-[var(--accent-2)]"
              title="Log out"
            >
              <LogOut size={14} /> Logout
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-5 py-8">{children}</main>
    </div>
  )
}

function Metric({ label, value, hint }) {
  return (
    <div className="doc-sheet p-5 border-l-4 border-l-[var(--accent)]">
      <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">{label}</p>
      <p className="display text-4xl mt-1 text-[var(--accent)]">{value}</p>
      {hint && <p className="text-xs text-[var(--muted)] mt-2">{hint}</p>}
    </div>
  )
}

function gradeColor(grade) {
  if (grade === 'CORRECT') return 'border-[var(--ok)] bg-green-50 text-[var(--ok)]'
  if (grade === 'AMBIGUOUS') return 'border-[var(--warn)] bg-amber-50 text-[var(--warn)]'
  return 'border-[var(--danger)] bg-rose-50 text-[var(--danger)]'
}

export default function App() {
  const [session, setSession] = useState(() => loadSession())
  const [page, setPage] = useState('dashboard')
  const [stats, setStats] = useState(null)
  const [docs, setDocs] = useState([])
  const [history, setHistory] = useState([])
  const [docId, setDocId] = useState('')
  const [question, setQuestion] = useState('What is the termination notice period?')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [uploadName, setUploadName] = useState('')

  const badge = useMemo(() => {
    if (!stats) return 'Connecting…'
    return stats.demo_mode ? 'Lexical demo grader' : 'Live models'
  }, [stats])

  async function refresh() {
    try {
      const [s, d, h] = await Promise.all([
        fetch(apiUrl('/api/stats')).then((r) => r.json()),
        fetch(apiUrl('/api/documents')).then((r) => r.json()),
        fetch(apiUrl('/api/history')).then((r) => r.json()),
      ])
      setStats(s)
      setDocs(d)
      setHistory(h)
      if (!docId && d[0]) setDocId(d[0].id)
      setError('')
    } catch {
      setError('Backend unreachable. Start API on port 8001 with DEMO_MODE=1.')
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
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(apiUrl('/api/upload'), { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setDocId(data.doc_id)
      setUploadName(data.filename)
      setPage('workspace')
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      e.target.value = ''
    }
  }

  async function onQuery(e) {
    e.preventDefault()
    if (!docId) {
      setError('Upload a document first.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const res = await fetch(apiUrl('/api/query'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId, question }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Query failed')
      setResult(data)
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (!session) return <LoginPage onLogin={setSession} />

  return (
    <Shell page={page} setPage={setPage} badge={badge} user={session} onLogout={logout}>
      {error && (
        <div className="mb-4 border border-[var(--danger)]/40 bg-rose-50 px-4 py-3 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}

      {page === 'dashboard' && (
        <div className="space-y-8 fade-in">
          <header>
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--accent-2)]">Chambers overview</p>
            <h2 className="display text-5xl mt-1 text-[var(--accent)]">Retrieval quality</h2>
            <p className="text-[var(--muted)] mt-2 max-w-2xl text-sm leading-relaxed">
              KPIs and recent clause queries. Upload and ask questions only on the Corrective QA desk.
            </p>
          </header>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric label="Documents" value={stats?.documents ?? '—'} />
            <Metric label="Queries" value={stats?.queries ?? '—'} />
            <Metric
              label="Correction rate"
              value={stats ? `${Math.round((stats.correction_rate || 0) * 100)}%` : '—'}
              hint="Queries that triggered a corrective action"
            />
            <Metric label="Corrected" value={stats?.corrected_queries ?? '—'} />
          </div>
          <div className="grid lg:grid-cols-[1.4fr_1fr] gap-5">
            <section className="doc-sheet p-6">
              <h3 className="display text-2xl text-[var(--accent)]">Recent activity</h3>
              <ul className="mt-4 divide-y divide-[var(--line)]">
                {(stats?.recent || []).length === 0 && (
                  <li className="py-3 text-sm text-[var(--muted)]">No queries yet.</li>
                )}
                {(stats?.recent || []).map((r, i) => (
                  <li key={i} className="py-3 text-sm">
                    <div className="font-medium">{r.question}</div>
                    <div className="text-[var(--muted)] mt-1 text-xs">
                      {r.doc_name || 'Document'} · {r.action}
                      {r.was_corrected ? ' · corrected' : ''}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
            <section className="doc-sheet p-6 flex flex-col">
              <div className="flex items-center gap-2 text-[var(--accent)]">
                <FileText size={16} />
                <h3 className="display text-2xl">Library</h3>
              </div>
              <ul className="mt-4 space-y-2 flex-1">
                {docs.length === 0 && (
                  <li className="text-sm text-[var(--muted)]">No contracts ingested yet.</li>
                )}
                {docs.map((d) => (
                  <li key={d.id} className="flex justify-between text-sm border-b border-[var(--line)] pb-2">
                    <span>{d.name}</span>
                    <span className="text-[var(--muted)]">{d.chunks} chunks</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => setPage('workspace')}
                className="mt-5 w-full bg-[var(--accent)] text-[var(--panel)] py-2.5 text-sm font-semibold"
              >
                Go to Corrective QA →
              </button>
            </section>
          </div>
        </div>
      )}

      {page === 'workspace' && (
        <div className="space-y-6 fade-in">
          <header>
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--accent-2)]">Working papers</p>
            <h2 className="display text-5xl mt-1 text-[var(--accent)]">Corrective QA</h2>
            <p className="text-[var(--muted)] mt-2 text-sm">
              Active: {uploadName || docs.find((d) => d.id === docId)?.name || 'none selected'}
            </p>
          </header>
          <div className="grid lg:grid-cols-2 gap-5">
            <form onSubmit={onQuery} className="doc-sheet p-6 space-y-4">
              <label className="block text-xs uppercase tracking-wider text-[var(--muted)]">Document</label>
              <select
                className="w-full border border-[var(--line)] bg-white px-3 py-2.5 text-sm"
                value={docId}
                onChange={(e) => setDocId(e.target.value)}
              >
                <option value="">Select…</option>
                {docs.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <label className="inline-flex items-center gap-2 border border-[var(--line)] px-3 py-2 text-sm cursor-pointer hover:border-[var(--accent)]">
                <Upload size={14} /> Upload contract
                <input type="file" accept=".pdf,.txt" className="hidden" onChange={onUpload} />
              </label>
              <label className="block text-xs uppercase tracking-wider text-[var(--muted)]">Question</label>
              <textarea
                className="w-full min-h-28 border border-[var(--line)] bg-white px-3 py-2.5 text-sm"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
              <button
                disabled={busy}
                className="inline-flex items-center gap-2 bg-[var(--accent-2)] text-white px-4 py-2.5 text-sm font-semibold disabled:opacity-60"
              >
                {busy ? <Loader2 className="animate-spin" size={16} /> : null}
                Run corrective RAG
              </button>
            </form>

            <section className="doc-sheet p-6">
              {!result && (
                <p className="text-[var(--muted)] text-sm leading-relaxed">
                  Passage grades, corrective action, and the grounded answer appear here after you query the uploaded contract text.
                </p>
              )}
              {result && (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="border border-[var(--line)] px-3 py-1">Action: {result.action}</span>
                    <span className="border border-[var(--line)] px-3 py-1">
                      {result.was_corrected ? 'Corrected' : 'Accepted'}
                    </span>
                    <span className="border border-[var(--line)] px-3 py-1">Mode: {result.mode}</span>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Answer</p>
                    <p className="mt-2 leading-relaxed display text-xl">{result.answer}</p>
                  </div>
                  <div className="space-y-3">
                    <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Passage grades</p>
                    {(result.grades || []).map((g, i) => (
                      <div key={i} className={`border px-3 py-3 text-sm ${gradeColor(g.grade)}`}>
                        <div className="font-semibold">
                          {g.grade} · {Math.round(g.confidence * 100)}%
                        </div>
                        <p className="mt-1 opacity-90">{g.reasoning}</p>
                        <p className="mt-2 opacity-70 text-xs">{g.passage}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {page === 'history' && (
        <div className="space-y-6 fade-in">
          <h2 className="display text-5xl text-[var(--accent)]">Query history</h2>
          <div className="doc-sheet overflow-hidden">
            <table className="w-full text-sm">
              <thead className="text-left text-[var(--muted)] border-b border-[var(--line)] bg-[var(--bg-2)]/50">
                <tr>
                  <th className="p-4 font-medium">Document</th>
                  <th className="p-4 font-medium">Question</th>
                  <th className="p-4 font-medium">Action</th>
                  <th className="p-4 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-b border-[var(--line)]">
                    <td className="p-4">{h.doc_name || h.doc_id}</td>
                    <td className="p-4 max-w-md">{h.question}</td>
                    <td className="p-4">
                      {h.action}
                      {h.was_corrected ? ' ✦' : ''}
                    </td>
                    <td className="p-4 text-[var(--muted)]">
                      {h.created_at ? new Date(h.created_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
                {history.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-6 text-[var(--muted)]">
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
        <div className="space-y-6 fade-in">
          <header>
            <h2 className="display text-5xl text-[var(--accent)]">Upcoming features</h2>
            <p className="text-[var(--muted)] mt-2 max-w-2xl text-sm">
              Planned enhancements — not available in the current release.
            </p>
          </header>
          <div className="grid md:grid-cols-2 gap-4">
            {UPCOMING.map((item) => (
              <article key={item.title} className="doc-sheet p-5 border-t-4 border-t-[var(--accent-2)]">
                <p className="text-[10px] uppercase tracking-wider text-[var(--warn)]">Not implemented</p>
                <h3 className="display text-2xl mt-2">{item.title}</h3>
                <p className="text-sm text-[var(--muted)] mt-3 leading-relaxed">{item.detail}</p>
              </article>
            ))}
          </div>
        </div>
      )}
    </Shell>
  )
}
