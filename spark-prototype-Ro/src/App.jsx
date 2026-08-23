import { useState } from "react";
import logo from "./assets/spark-logo.png";
import officeScene from "./assets/office-scene.png";
import agentM from "./assets/agent-m.png";
import agentA from "./assets/agent-a.png";
import agentS from "./assets/agent-s.png";
import agentC from "./assets/agent-c.png";
import agentD from "./assets/agent-d.png";
import profile from "./assets/profile.png";
import routingStar from "./assets/spark-star-new.png";
import { Landing } from "./Landing";

const AGENTS = [
  {
    id: "S",
    name: "Sammo",
    role: "Social Media",
    bay: "Social Hub",
    color: "#ff5f96",
    image: agentM,
    keywords: ["instagram", "linkedin", "twitter", "post", "caption", "content", "schedule", "community"],
    tools: ["scheduler", "engagement tracker", "content drafter"],
  },
  {
    id: "P",
    name: "Paro",
    role: "Personnel & HR",
    bay: "HR Department",
    color: "#55b8ff",
    image: agentA,
    keywords: ["recruit", "hire", "candidate", "resume", "interview", "job", "screening"],
    tools: ["resume parser", "interview calendar", "workflow automation"],
  },
  {
    id: "A",
    name: "Amo",
    role: "Advertising & Mktg",
    bay: "Marketing Studio",
    color: "#ffc04b",
    image: agentC,
    keywords: ["marketing", "campaign", "ad", "brand", "lead", "competitor", "strategy", "launch"],
    tools: ["market analysis", "ad copy gen", "campaign reporting"],
  },
  {
    id: "R",
    name: "Repo",
    role: "Reporting & Ops",
    bay: "Operations Center",
    color: "#94db52",
    image: agentS,
    keywords: ["task", "report", "data", "workflow", "automation", "calendar", "operations", "business"],
    tools: ["task manager", "data visualizer", "workflow builder"],
  },
  {
    id: "K",
    name: "Kmailo",
    role: "Key Comms & Email",
    bay: "Communications Hub",
    color: "#a66bff",
    image: agentD,
    keywords: ["email", "inbox", "reply", "follow-up", "meeting", "message", "communication"],
    tools: ["email drafter", "inbox scanner", "follow-up manager"],
  },
];

const WAYPOINTS = {
  S: [
    [16, 96],
    [46, 96],
    [65, 79],
    [65, 68],
    [47, 53],
  ],
  P: [
    [16, 96],
    [46, 96],
    [65, 79],
    [65, 68],
    [66, 55],
  ],
  A: [
    [16, 96],
    [46, 96],
    [65, 79],
    [65, 68],
    [28, 43],
  ],
  R: [
    [16, 96],
    [46, 96],
    [65, 79],
    [65, 68],
    [88, 55],
  ],
  K: [
    [16, 96],
    [46, 96],
    [65, 79],
    [65, 68],
    [55, 55],
  ],
};

const STAGES = [
  "READY",
  "SELECTED",
  "DISPATCHED",
  "ENTERING",
  "WALKING",
  "ARRIVING",
  "WORKING",
  "STREAMING",
  "COMPLETED",
  "RETURNING",
  "READY",
];

const sampleTasks = [
  "Send a follow-up email to shortlisted candidates and announce our new product on LinkedIn.",
  "Draft an email to 5 people and analyze competitor market strategy.",
  "Create an Instagram post for our new hiring workflow.",
  "Coordinate calendar for operations and launch an ad campaign.",
  "Screen recent resumes and generate a weekly business report.",
];

function scoreAgents(task) {
  const normalized = task.toLowerCase();
  return AGENTS.map((agent) => {
    const hits = agent.keywords.filter((keyword) => normalized.includes(keyword)).length;
    const base = 14 + agent.id.charCodeAt(0) % 11;
    const roleBoost = hits * 26;
    const adjacentBoost =
      agent.id === "A" && /(campaign|ad|brand)/.test(normalized)
        ? 18
        : agent.id === "R" && /(report|data|business)/.test(normalized)
          ? 20
          : agent.id === "P" && /(hire|recruit|interview)/.test(normalized)
            ? 18
            : agent.id === "K" && /(email|mail)/.test(normalized)
              ? 22
              : 0;
    return {
      ...agent,
      confidence: Math.min(98, base + roleBoost + adjacentBoost),
      hits,
    };
  }).sort((a, b) => b.confidence - a.confidence);
}

function makeResult(task) {
  const scores = scoreAgents(task);
  const best = scores[0];
  const traditional = 18400 + task.length * 11 + best.tools.length * 120;
  const optimized = 3800 + task.length * 5 + best.hits * 190;
  const saved = traditional - optimized;
  const reduction = Math.round((saved / traditional) * 100);
  return { scores, best, traditional, optimized, saved, reduction };
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function MiniIcon({ label }) {
  return <span className="mini-icon" aria-hidden="true">{label}</span>;
}

export function App() {
  const [view, setView] = useState("landing");
  const [task, setTask] = useState(sampleTasks[0]);
  const [result, setResult] = useState(() => makeResult(sampleTasks[0]));
  const [stageIndex, setStageIndex] = useState(0);
  const [logs, setLogs] = useState([]);
  const [position, setPosition] = useState({ x: 16, y: 96 });
  const [isRunning, setIsRunning] = useState(false);
  const [activeNav, setActiveNav] = useState("Workspace");
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const stage = STAGES[stageIndex];

  function pushLog(source, text, tone = "system") {
    setLogs((items) => [
      ...items.slice(-8),
      {
        source,
        text,
        tone,
        time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      },
    ]);
  }

  function runTask(nextTask = task) {
    if (!nextTask.trim() || isRunning) return;
    const nextResult = makeResult(nextTask);
    const nextPath = WAYPOINTS[nextResult.best.id];
    setTask(nextTask);
    setResult(nextResult);
    setLogs([]);
    setIsRunning(true);
    setStageIndex(1);
    setPosition({ x: nextPath[0][0], y: nextPath[0][1] });

    // Fire off the task to our new local backend!
    fetch('http://localhost:3001/api/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: nextTask })
    }).catch(err => console.error("Backend connection error:", err));

    const timed = [
      [0, 1, nextPath[0], "System", "Analyzing your request...", "core"],
      [650, 2, nextPath[0], "System", "Intent and capability map created.", "core"],
      [1200, 3, nextPath[1], "System", `${nextResult.best.name} leaving deployment bay.`, "system"],
      [2250, 4, nextPath[2], "System", `${nextResult.best.name} entering through the front door.`, "system"],
      [3300, 5, nextPath[3], nextResult.best.name, "Inside the lobby. Walking to assigned cubicle.", nextResult.best.id],
      [4450, 6, nextPath[4], nextResult.best.name, `Arrived at ${nextResult.best.bay}.`, nextResult.best.id],
      [5350, 7, nextPath[4], nextResult.best.name, "Monitor online. Loading only relevant context.", nextResult.best.id],
      [6250, 8, nextPath[4], nextResult.best.name, `Streaming ${nextResult.best.role.toLowerCase()} response.`, nextResult.best.id],
      [7550, 9, nextPath[4], "Token Engine", `${formatNumber(nextResult.saved)} tokens saved with ${nextResult.reduction}% less context.`, "savings"],
      [8750, 10, nextPath[2], nextResult.best.name, "Task complete. Returning through the office door.", nextResult.best.id],
      [10000, 10, nextPath[0], "System", `${nextResult.best.name} returned to READY.`, "system"],
    ];

    timed.forEach(([delay, idx, point, source, text, tone]) => {
      window.setTimeout(() => {
        setStageIndex(idx);
        setPosition({ x: point[0], y: point[1] });
        pushLog(source, text, tone);
        if (idx === 9) setIsRunning(false);
      }, delay);
    });
  }

  const nav = ["Workspace", "Agents", "Analytics", "Token Savings", "Settings"];

  if (view === "landing") {
    return <Landing onGetStarted={() => setView("dashboard")} />;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand" onClick={() => setView("landing")} style={{ cursor: "pointer" }}>
          <img src={logo} alt="SPARK logo" />
          <div>
            <h1>SPARK</h1>
            <p>Your AI office, in motion.</p>
          </div>
        </div>

        <nav className="nav-list" aria-label="Primary">
          {nav.map((item) => (
            <button
              key={item}
              className={activeNav === item ? "active" : ""}
              type="button"
              onClick={() => setActiveNav(item)}
            >
              <MiniIcon label={item === "Workspace" ? "H" : item === "Agents" ? "A" : item === "Analytics" ? "B" : item === "Token Savings" ? "T" : "S"} />
              {item}
            </button>
          ))}
        </nav>

        <div className="status-card">
          <p className="eyebrow">System Status</p>
          <strong><span className="dot good" /> All systems ready</strong>
          <hr />
          <span>Active Task</span>
          <b>{isRunning ? result.best.name : "None"}</b>
        </div>

        <div className="user-card">
          <img src={profile} alt="Rohit profile" />
          <div>
            <strong>Rohit</strong>
            <span>Administrator</span>
          </div>
          <MiniIcon label="v" />
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="welcome" onClick={() => setView("landing")} style={{ cursor: "pointer" }}>
            <img src={logo} alt="" />
            <div>
              <h2>Welcome back, Rohit!</h2>
              <p>Your AI company is ready to work wonders.</p>
            </div>
          </div>
          <div className="metrics">
            <div className="profile-container" style={{ position: 'relative' }}>
              <button 
                className="profile-button" 
                onClick={() => setIsProfileOpen(!isProfileOpen)} 
                type="button" 
                aria-label="Profile Menu"
                style={{ background: 'none', border: 'none', padding: 0 }}
              >
                <img className="avatar" src={profile} alt="Profile" style={{ cursor: 'pointer' }} />
              </button>
              {isProfileOpen && (
                <div className="profile-dropdown">
                  <button type="button">Login</button>
                  <button type="button">Logout</button>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="content-grid">
          <section className="main-stage">
            <div className="office-card">
              <img className="office-map" src={officeScene} alt="Isometric SPARK AI office" />
              <div className={`core-pulse ${isRunning ? "active" : ""}`} />
              <div className={`office-door ${isRunning ? "open" : ""}`}>Door</div>
              <div className={`route-line ${isRunning ? "active" : ""}`} />
              <div
                className="runner-shadow"
                style={{ "--x": `${position.x}%`, "--y": `${position.y}%`, "--agent": result.best.color }}
              />
              <img
                className={`runner stage-${stage.toLowerCase()}`}
                src={result.best.image}
                alt={`${result.best.name} moving through office`}
                style={{ "--x": `${position.x}%`, "--y": `${position.y}%`, "--agent": result.best.color }}
              />
              <div className="state-chip" style={{ "--agent": result.best.color }}>
                {result.best.name} - {stage}
              </div>
            </div>



            <div className="console-row">
              <form className="talk-panel" onSubmit={(event) => { event.preventDefault(); runTask(); }}>
                <div className="input-row">
                  <textarea
                    id="task-input"
                    value={task}
                    onChange={(event) => setTask(event.target.value)}
                    placeholder="Tell your AI office what to work on..."
                  />
                  <button className="send-button" type="submit" disabled={isRunning} aria-label="Run route">
                    <MiniIcon label="→" />
                  </button>
                </div>
                <div className="sample-row">
                  {sampleTasks.slice(0, 4).map((item) => (
                    <button key={item} type="button" onClick={() => runTask(item)}>{item.split(" ").slice(0, 3).join(" ")}</button>
                  ))}
                </div>
              </form>
            </div>
          </section>

          <aside className="right-rail">
            <section className="rail-card routing">
              <h3>Routing Overview</h3>
              <img src={routingStar} alt="Five-agent routing star" />
              <div className="score-list">
                {result.scores.map((agent) => (
                  <div key={agent.id} className={agent.id === result.best.id ? "winner" : ""}>
                    <img className="score-agent-img" src={agent.image} alt={agent.id} style={{ "--agent": agent.color }} />
                    <b>{agent.name} ({agent.role})</b>
                  </div>
                ))}
              </div>
            </section>

            <section className="rail-card savings">
              <h3>Token Savings Comparison</h3>
              <div className="bar-row"><span>Traditional Multi-Agent</span><b>{formatNumber(result.traditional)}</b></div>
              <div className="bar hot"><i style={{ width: "92%" }} /></div>
              <div className="bar-row"><span>SPARK Optimized</span><b>{formatNumber(result.optimized)}</b></div>
              <div className="bar cool"><i style={{ width: `${Math.max(24, 100 - result.reduction)}%` }} /></div>
              <div className="saved-box">
                <strong>{formatNumber(result.saved)} Tokens Saved</strong>
                <span>{result.reduction}% less context processed</span>
              </div>
            </section>
          </aside>
        </div>
      </section>
    </main>
  );
}
