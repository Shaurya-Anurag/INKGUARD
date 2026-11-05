import {
  Activity, ArrowDownRight, ArrowUpRight, Bell, BookOpenCheck, CheckCircle2,
  ChevronDown, CircleHelp, Clock3, FileCheck2, FilePlus2, FileText,
  LayoutDashboard, Search, Settings2, ShieldCheck, Sparkles, Users,
} from "lucide-react";

const navigation = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Brand intelligence", icon: BookOpenCheck },
  { label: "Content audits", icon: FileCheck2 },
  { label: "New submission", icon: FilePlus2 },
  { label: "Approval centre", icon: CheckCircle2 },
  { label: "Governance analytics", icon: Activity },
];

const stats = [
  { label: "CONTENT AUDITED", value: "128", note: "+12 this week", trend: "up" },
  { label: "NEEDS ATTENTION", value: "09", note: "Across 6 audits", trend: "down" },
  { label: "APPROVAL RATE", value: "94.2%", note: "+2.4% this month", trend: "up" },
  { label: "PENDING REVIEW", value: "04", note: "2 high priority", trend: "neutral" },
];

const audits = [
  { name: "Vitamin C serum — launch campaign", type: "Social campaign", date: "Today, 10:42 AM", findings: 3, status: "Needs review", tone: "rose" },
  { name: "HydraLock product landing page", type: "Website copy", date: "Today, 09:18 AM", findings: 1, status: "In review", tone: "amber" },
  { name: "September newsletter", type: "Email marketing", date: "Yesterday", findings: 0, status: "Approved", tone: "green" },
];

export default function Home() {
  return (
    <div className="min-h-screen" style={{ display: "flex", background: "var(--background)" }}>
      <aside className="app-sidebar" style={{ width: 252, minHeight: "100vh", flexShrink: 0, padding: "27px 17px", background: "var(--surface)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "0 10px 30px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 30, height: 30, display: "grid", placeItems: "center", background: "var(--crimson)", color: "white", borderRadius: 4 }}><ShieldCheck size={18} /></div>
            <span style={{ fontSize: 19, fontWeight: 750, letterSpacing: ".12em" }}>INKGUARD</span>
          </div>
          <div className="eyebrow" style={{ margin: "9px 0 0 40px", fontSize: 9 }}>BRAND GOVERNANCE</div>
        </div>

        <button className="panel" style={{ padding: 11, display: "flex", alignItems: "center", gap: 10, textAlign: "left", cursor: "pointer", marginBottom: 27 }}>
          <div style={{ width: 31, height: 31, display: "grid", placeItems: "center", background: "var(--rose)", color: "var(--crimson-dark)", fontFamily: "var(--font-editorial)", fontSize: 18 }}>V</div>
          <div style={{ flex: 1 }}><div style={{ fontSize: 12, fontWeight: 650 }}>VELORA</div><div className="muted" style={{ fontSize: 10, marginTop: 3 }}>Workspace</div></div>
          <ChevronDown size={15} color="var(--muted)" />
        </button>

        <div className="eyebrow" style={{ padding: "0 10px", marginBottom: 10 }}>WORKSPACE</div>
        <nav style={{ display: "grid", gap: 4 }}>
          {navigation.map(({ label, icon: Icon, active }) => (
            <a key={label} href="#" aria-current={active ? "page" : undefined} style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 11px", borderRadius: 4, fontSize: 12, fontWeight: active ? 650 : 500, color: active ? "var(--crimson-dark)" : "var(--muted)", background: active ? "var(--rose)" : "transparent" }}>
              <Icon size={16} strokeWidth={1.8} />{label}
              {label === "Approval centre" && <span style={{ marginLeft: "auto", fontSize: 10, background: "var(--crimson)", color: "white", borderRadius: 10, padding: "2px 6px" }}>4</span>}
            </a>
          ))}
        </nav>

        <div className="eyebrow" style={{ padding: "25px 10px 10px" }}>PREFERENCES</div>
        <nav style={{ display: "grid", gap: 4 }}>
          <a href="#" style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 11px", color: "var(--muted)", fontSize: 12 }}><Users size={16} />Team</a>
          <a href="#" style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 11px", color: "var(--muted)", fontSize: 12 }}><Settings2 size={16} />Settings</a>
        </nav>

        <div style={{ marginTop: "auto", borderTop: "1px solid var(--border)", padding: "17px 8px 0" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <div style={{ width: 30, height: 30, borderRadius: "50%", background: "var(--surface-muted)", display: "grid", placeItems: "center", fontSize: 11, fontWeight: 700 }}>SA</div>
            <div><div style={{ fontSize: 11, fontWeight: 650 }}>Workspace admin</div><div className="muted" style={{ fontSize: 10, marginTop: 3 }}>VELORA team</div></div>
          </div>
        </div>
      </aside>

      <main style={{ minWidth: 0, flex: 1 }}>
        <header style={{ height: 66, padding: "0 4.2%", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border)", background: "rgba(255,253,249,.72)" }}>
          <div className="muted" style={{ fontSize: 11 }}>Workspace <span style={{ padding: "0 7px", color: "var(--border)" }}>/</span><span style={{ color: "var(--ink)", fontWeight: 600 }}>Overview</span></div>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <button aria-label="Search" style={{ color: "var(--muted)" }}><Search size={17} /></button>
            <button aria-label="Notifications" style={{ color: "var(--muted)" }}><Bell size={17} /></button>
            <div style={{ width: 1, height: 23, background: "var(--border)" }} />
            <div className="eyebrow">DEMO ENVIRONMENT</div>
          </div>
        </header>

        <div style={{ maxWidth: 1450, margin: "0 auto", padding: "42px 4.2% 60px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 20, flexWrap: "wrap", marginBottom: 31 }}>
            <div><div className="eyebrow" style={{ marginBottom: 10 }}>WEDNESDAY, NOVEMBER 05, 2026 · VELORA</div><h1 className="editorial" style={{ fontSize: "clamp(34px, 4vw, 47px)", lineHeight: 1.08, margin: 0 }}>Good morning.</h1><p className="muted" style={{ fontSize: 13, marginTop: 10 }}>Here&apos;s the current state of your brand governance.</p></div>
            <button style={{ display: "flex", alignItems: "center", gap: 9, background: "var(--crimson)", color: "white", padding: "12px 16px", borderRadius: 4, fontSize: 12, fontWeight: 650, boxShadow: "0 3px 8px #A8172520" }}><FilePlus2 size={15} />New content audit</button>
          </div>

          <section className="stat-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4,minmax(0,1fr))", gap: 13, marginBottom: 25 }}>
            {stats.map((stat) => <div key={stat.label} className="panel" style={{ padding: "19px 20px" }}><div className="eyebrow">{stat.label}</div><div style={{ display: "flex", alignItems: "baseline", gap: 9, marginTop: 14 }}><span className="editorial" style={{ fontSize: 34 }}>{stat.value}</span>{stat.trend === "up" ? <ArrowUpRight size={14} color="#47845B" /> : stat.trend === "down" ? <ArrowDownRight size={14} color="var(--crimson)" /> : null}</div><div className="muted" style={{ fontSize: 10, marginTop: 5 }}>{stat.note}</div></div>)}
          </section>

          <div className="dashboard-grid" style={{ display: "grid", gridTemplateColumns: "minmax(0,1.7fr) minmax(260px,.85fr)", gap: 16, alignItems: "start" }}>
            <section className="panel" style={{ overflow: "hidden" }}>
              <div style={{ padding: "20px 22px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)" }}><div><div className="editorial" style={{ fontSize: 21 }}>Recent content audits</div><div className="muted" style={{ fontSize: 11, marginTop: 5 }}>Latest submissions across your workspace</div></div><a href="#" style={{ color: "var(--crimson-dark)", fontSize: 11, fontWeight: 650 }}>View all →</a></div>
              <div>{audits.map((audit, index) => <div key={audit.name} style={{ padding: "17px 22px", display: "flex", alignItems: "center", gap: 13, borderBottom: index === audits.length - 1 ? 0 : "1px solid var(--border)" }}><div style={{ width: 35, height: 35, flexShrink: 0, display: "grid", placeItems: "center", background: "var(--surface-muted)", color: "var(--muted)", borderRadius: 4 }}><FileText size={17} /></div><div style={{ minWidth: 0, flex: 1 }}><div style={{ fontSize: 12, fontWeight: 650 }}>{audit.name}</div><div className="muted" style={{ fontSize: 10, marginTop: 5 }}>{audit.type} · {audit.date}</div></div><div style={{ textAlign: "right", flexShrink: 0 }}><div style={{ fontSize: 10, fontWeight: 650, color: audit.tone === "green" ? "#477553" : audit.tone === "rose" ? "var(--crimson-dark)" : "#98712B", background: audit.tone === "green" ? "var(--green)" : audit.tone === "rose" ? "var(--rose)" : "#F6EFDF", padding: "5px 8px", borderRadius: 3 }}>{audit.status}</div><div className="muted" style={{ fontSize: 10, marginTop: 6 }}>{audit.findings} findings</div></div></div>)}</div>
            </section>

            <div style={{ display: "grid", gap: 15 }}>
              <section className="panel" style={{ padding: 21 }}><div style={{ display: "flex", alignItems: "center", gap: 8 }}><Sparkles size={15} color="var(--crimson)" /><div className="eyebrow">GOVERNANCE PULSE</div></div><div className="editorial" style={{ fontSize: 23, lineHeight: 1.2, marginTop: 17 }}>Your brand is in good shape.</div><p className="muted" style={{ fontSize: 11, lineHeight: 1.7, marginTop: 9 }}>A few submissions need human review before they&apos;re ready to publish.</p><div style={{ marginTop: 18, height: 5, background: "var(--surface-muted)", borderRadius: 8, overflow: "hidden" }}><div style={{ width: "94.2%", height: "100%", background: "var(--crimson)" }} /></div><div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 10 }}><span className="muted">Governance score</span><strong>94.2%</strong></div></section>
              <section className="panel" style={{ padding: 21 }}><div className="eyebrow">NEEDS YOUR ATTENTION</div><div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 17 }}><div style={{ width: 37, height: 37, display: "grid", placeItems: "center", background: "var(--rose)", color: "var(--crimson-dark)", borderRadius: 4 }}><Clock3 size={17} /></div><div><div className="editorial" style={{ fontSize: 27 }}>04</div><div className="muted" style={{ fontSize: 10 }}>Items awaiting approval</div></div></div><div style={{ borderTop: "1px solid var(--border)", marginTop: 17, paddingTop: 14, display: "flex", alignItems: "center", justifyContent: "space-between" }}><span className="muted" style={{ fontSize: 10 }}>2 high-priority reviews</span><a href="#" style={{ color: "var(--crimson-dark)", fontSize: 10, fontWeight: 650 }}>Review queue →</a></div></section>
              <div className="muted" style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 10, padding: "2px 3px" }}><CircleHelp size={13} /> Findings require human review before approval.</div>
            </div>
          </div>
          <div className="muted" style={{ fontSize: 10, marginTop: 25 }}>INKGUARD · Brand governance workspace <span style={{ margin: "0 6px" }}>·</span> Demo data — not connected to live API yet</div>
        </div>
      </main>
    </div>
  );
}
