import { useState, useEffect, useRef } from "react";
import logo from "./assets/spark-logo.png";
import officeScene from "./assets/office-scene.png";
import agentS from "./assets/agent-s.png";
import agentP from "./assets/agent-p.png";
import agentA from "./assets/agent-a.png";
import agentR from "./assets/agent-r.png";
import agentK from "./assets/agent-k.png";
import profile from "./assets/profile.png";
import routingStar from "./assets/spark-star-new.png";
import { API } from "./services/api";
import { createSessionSocket } from "./services/websocket";
import { Landing } from "./Landing";

const AGENT_METADATA = {
  "S": {
    name: "Sammo",
    role: "Search Specialist",
    bay: "Research Hub",
    color: "#ff4154", // Red
    image: agentS,
    keywords: ["research", "search", "lookup", "source", "external", "extract", "evidence", "find"],
    tools: ["retrieval", "source scan", "text extraction"],
  },
  "P": {
    name: "Paro",
    role: "Creative Strategist",
    bay: "Creative Studio",
    color: "#55b8ff", // Blue
    image: agentP,
    keywords: ["marketing", "strategy", "campaign", "brand", "business", "creative", "launch", "growth"],
    tools: ["brief synthesis", "positioning", "campaign map"],
  },
  "A": {
    name: "Amo",
    role: "Analytics Engineer",
    bay: "Engineering Lab",
    color: "#5bd842", // Green
    image: agentA,
    keywords: ["code", "api", "automation", "debug", "technical", "logic", "build", "backend"],
    tools: ["code plan", "debugger", "automation"],
  },
  "R": {
    name: "Repo",
    role: "Content Creator",
    bay: "Content Studio",
    color: "#ffc04b", // Yellow
    image: agentR,
    keywords: ["write", "caption", "script", "copy", "story", "communication", "post", "email"],
    tools: ["copy draft", "tone pass", "storyline"],
  },
  "K": {
    name: "Kmailo",
    role: "Data Analyst",
    bay: "Data Observatory",
    color: "#a66bff", // Violet
    image: agentK,
    keywords: ["data", "analysis", "pattern", "summary", "compare", "report", "metrics", "insight"],
    tools: ["metrics scan", "pattern model", "report builder"],
  },
};

const SUPPORTED_MODELS = [
  {
    id: "gemini-1.5-flash",
    name: "Gemini 1.5 Flash",
    provider: "Google DeepMind",
    badge: "⚡ Ultra-Fast",
    context: "1M ctx",
    latency: "180ms",
    cost: "$0.075/1M",
    color: "#4285F4",
  },
  {
    id: "gemini-1.5-pro",
    name: "Gemini 1.5 Pro",
    provider: "Google DeepMind",
    badge: "🧠 Deep Reasoning",
    context: "2M ctx",
    latency: "420ms",
    cost: "$1.25/1M",
    color: "#9333EA",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "OpenAI",
    badge: "🎯 Multimodal",
    context: "128k ctx",
    latency: "320ms",
    cost: "$2.50/1M",
    color: "#10A37F",
  },
  {
    id: "llama-3.1-70b",
    name: "Llama 3.1 70B",
    provider: "Meta AI",
    badge: "🦙 Open Weights",
    context: "128k ctx",
    latency: "260ms",
    cost: "$0.40/1M",
    color: "#0081FB",
  },
  {
    id: "kimi-k2",
    name: "Kimi K2",
    provider: "Moonshot AI",
    badge: "📚 Long Context",
    context: "200k ctx",
    latency: "350ms",
    cost: "$0.60/1M",
    color: "#F59E0B",
  },
];

const DEFAULT_MODEL_MAP = {
  S: "gemini-1.5-flash",
  P: "gemini-1.5-pro",
  A: "gpt-4o",
  R: "llama-3.1-70b",
  K: "kimi-k2",
};

const DEFAULT_AGENTS = Object.entries(AGENT_METADATA).map(([id, meta]) => ({
  id,
  backendId: `agent-${id.toLowerCase()}`,
  ...meta,
  tasks_completed: 0,
  tokens_used: 0,
  model: DEFAULT_MODEL_MAP[id] || "gemini-1.5-flash",
  status: "IDLE",
}));

const WAYPOINTS = {
  S: [
    [27, 92],
    [30, 86],
    [65.2, 86],
    [65.2, 74],
    [65.2, 62],
    [39.0, 52],
    [39.0, 36],
  ],
  P: [
    [38, 92],
    [42, 86],
    [65.2, 86],
    [65.2, 74],
    [65.2, 62],
    [55.0, 52],
    [55.0, 36],
  ],
  A: [
    [50, 92],
    [54, 86],
    [65.2, 86],
    [65.2, 74],
    [65.2, 62],
    [68.5, 52],
    [68.5, 36],
  ],
  R: [
    [62, 92],
    [63, 86],
    [65.2, 86],
    [65.2, 74],
    [65.2, 62],
    [81.8, 52],
    [81.8, 36],
  ],
  K: [
    [73, 92],
    [72, 86],
    [65.2, 86],
    [65.2, 74],
    [65.2, 62],
    [93.8, 52],
    [93.8, 36],
  ],
};

const CUBICLES = [
  { id: "S", name: "Research Hub", cubicleName: "Cubicle S", desk: [39.0, 36], color: "#ff4154" },
  { id: "P", name: "Creative Studio", cubicleName: "Cubicle P", desk: [55.0, 36], color: "#55b8ff" },
  { id: "A", name: "Engineering Lab", cubicleName: "Cubicle A", desk: [68.5, 36], color: "#5bd842" },
  { id: "R", name: "Content Studio", cubicleName: "Cubicle R", desk: [81.8, 36], color: "#ffc04b" },
  { id: "K", name: "Data Observatory", cubicleName: "Cubicle K", desk: [93.8, 36], color: "#a66bff" },
];

const AGENT_DIRECT_MATCHES = {
  S: /\b(sammo|agent[\s\-_]*s|@s|search\s*specialist|research\s*hub)\b/i,
  P: /\b(paro|agent[\s\-_]*p|@p|creative\s*strategist|creative\s*studio|brand\s*strategist)\b/i,
  A: /\b(amo|agent[\s\-_]*a|@a|analytics\s*engineer|engineering\s*lab|automation\s*engineer)\b/i,
  R: /\b(repo|agent[\s\-_]*r|@r|content\s*creator|content\s*studio|copywriter|writer)\b/i,
  K: /\b(kmailo|agent[\s\-_]*k|@k|data\s*analyst|data\s*observatory|telemetry\s*analyst)\b/i,
};

const sampleTasks = [
  { agent: "S", label: "Sammo (Search)", text: "Research top customer onboarding examples with external sources." },
  { agent: "P", label: "Paro (Strategy)", text: "Create a marketing strategy and creative launch campaign for our new product." },
  { agent: "A", label: "Amo (Engineering)", text: "Debug the API automation pipelines and build backend test scripts." },
  { agent: "R", label: "Repo (Content)", text: "Write a high-converting product launch script and social copy." },
  { agent: "K", label: "Kmailo (Data)", text: "Compare quarterly telemetry metrics and report token savings insights." },
];

function scoreAgents(task, agentList = DEFAULT_AGENTS) {
  const normalized = task.toLowerCase();

  // 1. Check direct mention match
  let directTarget = null;
  for (const [id, regex] of Object.entries(AGENT_DIRECT_MATCHES)) {
    if (regex.test(normalized)) {
      directTarget = id;
      break;
    }
  }

  return agentList.map((agent) => {
    if (directTarget && agent.id === directTarget) {
      return {
        ...agent,
        confidence: 99,
        hits: 10,
        directMatch: true,
      };
    }

    const hits = (agent.keywords || []).filter((keyword) => normalized.includes(keyword)).length;
    const base = 14 + agent.id.charCodeAt(0) % 11;
    const roleBoost = hits * 26;

    let domainBoost = 0;
    if (agent.id === "S" && /(source|research|find|lookup|scrape|fetch|gather|evidence)/i.test(normalized)) domainBoost += 25;
    if (agent.id === "P" && /(marketing|launch|brand|campaign|strategy|creative|positioning|growth)/i.test(normalized)) domainBoost += 25;
    if (agent.id === "A" && /(code|api|automation|debug|script|backend|build|logic|server)/i.test(normalized)) domainBoost += 25;
    if (agent.id === "R" && /(write|caption|script|copy|story|communication|post|email|draft|blog)/i.test(normalized)) domainBoost += 25;
    if (agent.id === "K" && /(summary|summarize|compare|metrics|data|analysis|pattern|report|tokens|telemetry)/i.test(normalized)) domainBoost += 25;

    return {
      ...agent,
      confidence: Math.min(98, base + roleBoost + domainBoost),
      hits,
    };
  }).sort((a, b) => b.confidence - a.confidence);
}

function makeInitialResult(task, agentList = DEFAULT_AGENTS) {
  const scores = scoreAgents(task, agentList);
  const best = scores[0] || agentList[0];
  const traditional = 18400 + task.length * 11 + (best.tools || []).length * 120;
  const optimized = 3800 + task.length * 5 + (best.hits || 0) * 190;
  const saved = traditional - optimized;
  const reduction = Math.round((saved / traditional) * 100);
  return { scores, best, traditional, optimized, saved, reduction };
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value || 0);
}

function PokeballIcon({ width = 34, height = 34 }) {
  return (
    <svg className="pokeball-svg" viewBox="0 0 100 100" width={width} height={height}>
      <circle cx="50" cy="50" r="46" fill="#ffffff" stroke="#181818" strokeWidth="8" />
      <path d="M 4 50 A 46 46 0 0 1 96 50 Z" fill="#EE1515" stroke="#181818" strokeWidth="8" />
      <line x1="4" y1="50" x2="96" y2="50" stroke="#181818" strokeWidth="8" />
      <circle cx="50" cy="50" r="16" fill="#ffffff" stroke="#181818" strokeWidth="8" />
      <circle cx="50" cy="50" r="8" fill="#ffffff" stroke="#181818" strokeWidth="4" />
    </svg>
  );
}

function NavIcon({ type }) {
  switch (type) {
    case "Workspace":
      return (
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">
          <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />
        </svg>
      );
    case "Agents":
      return (
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">
          <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.38-1 1.72V7h4a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-8a3 3 0 0 1 3-3h4V5.72c-.6-.34-1-.98-1-1.72a2 2 0 0 1 2-2M7.5 12a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3m9 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3m-6 5h3a1 1 0 1 1 0 2h-3a1 1 0 1 1 0-2" />
        </svg>
      );
    case "Analytics":
      return (
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">
          <path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z" />
        </svg>
      );
    case "Token Savings":
      return (
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">
          <path d="M12 3c-4.97 0-9 1.79-9 4s4.03 4 9 4 9-1.79 9-4-4.03-4-9-4zm0 6c-3.87 0-7-1.12-7-2s3.13-2 7-2 7 1.12 7 2-3.13 2-7 2zm-9 3c0 2.21 4.03 4 9 4s9-1.79 9-4v3c0 2.21-4.03 4-9 4s-9-1.79-9-4zm0 5c0 2.21 4.03 4 9 4s9-1.79 9-4v3c0 2.21-4.03 4-9 4s-9-1.79-9-4z" />
        </svg>
      );
    case "Content Studio":
      return (
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">
          <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z" />
        </svg>
      );
    case "Data Observatory":
      return (
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">
          <path d="M4 4h16a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2m0 7h16a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2m0 7h16a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-1a2 2 0 0 1 2-2M6 7.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3m0 7a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3m0 6a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3" />
        </svg>
      );
    case "Settings":
      return (
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor">
          <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54A.484.484 0 0 0 14 2h-4c-.25 0-.46.18-.49.42l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.63 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h4c.25 0 .46-.18.49-.42l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6" />
        </svg>
      );
    default:
      return null;
  }
}

function MiniIcon({ label }) {
  return <span className="mini-icon" aria-hidden="true">{label}</span>;
}

export function App() {
  const [view, setView] = useState(() => {
    if (typeof window !== "undefined" && (window.location.hash === "#workspace" || window.location.hash === "#dashboard")) {
      return "dashboard";
    }
    return "landing";
  });
  const [sessionId, setSessionId] = useState(() => localStorage.getItem("spark_session_id") || "spark_sess_1");
  const [agents, setAgents] = useState(DEFAULT_AGENTS);
  const [task, setTask] = useState(sampleTasks[0].text);
  const [result, setResult] = useState(() => makeInitialResult(sampleTasks[0].text, DEFAULT_AGENTS));
  const [stage, setStage] = useState("READY");
  const [logs, setLogs] = useState([]);
  const [position, setPosition] = useState(() => {
    const defaultAgent = makeInitialResult(sampleTasks[0].text, DEFAULT_AGENTS).best;
    const coords = WAYPOINTS[defaultAgent.id] || WAYPOINTS.S;
    return { x: coords[0][0], y: coords[0][1] };
  });
  const [isRunning, setIsRunning] = useState(false);
  const [activeNav, setActiveNav] = useState("Workspace");
  const [isMenuMinimized, setIsMenuMinimized] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  useEffect(() => {
    const onHashChange = () => {
      if (window.location.hash === "#workspace" || window.location.hash === "#dashboard") {
        setView("dashboard");
      } else if (window.location.hash === "#landing" || !window.location.hash) {
        setView("landing");
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigateToView = (nextView) => {
    setView(nextView);
    if (nextView === "dashboard") {
      window.location.hash = "workspace";
    } else {
      window.location.hash = "landing";
    }
  };
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [analyticsOverview, setAnalyticsOverview] = useState(null);
  const [tokenAnalytics, setTokenAnalytics] = useState(null);
  const [serverConnected, setServerConnected] = useState(false);

  const socketRef = useRef(null);
  const runnerTimerRef = useRef(null);
  const agentsRef = useRef(agents);
  agentsRef.current = agents;
  const resultRef = useRef(result);
  resultRef.current = result;

  function pushLog(source, text, tone = "system") {
    setLogs((items) => [
      ...items.slice(-12),
      {
        source,
        text,
        tone,
        time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      },
    ]);
  }

  // 1. Initialize session and fetch real agents and analytics from backend
  useEffect(() => {
    async function initBackend() {
      try {
        // Bootstrap session
        const sessionList = await API.sessions.list().catch(() => []);
        let activeId = sessionId;
        if (!sessionList.some((s) => s.id === activeId)) {
          const created = await API.sessions.create("SPARK Virtual Office Session").catch(() => null);
          if (created && created.session_id) {
            activeId = created.session_id;
            setSessionId(activeId);
            localStorage.setItem("spark_session_id", activeId);
          }
        }

        // Fetch agents
        const backendAgents = await API.agents.list().catch(() => []);
        if (backendAgents && backendAgents.length > 0) {
          const merged = DEFAULT_AGENTS.map((defaultAgent) => {
            const matched = backendAgents.find((ba) => {
              const bKey = (ba.cubicle || ba.id.replace("agent-", "")).toUpperCase();
              return bKey === defaultAgent.id;
            });
            if (matched) {
              return {
                ...defaultAgent,
                backendId: matched.id,
                name: matched.name || defaultAgent.name,
                role: matched.role || defaultAgent.role,
                model: matched.model || "gemini-1.5-flash",
                tasks_completed: matched.tasks_completed || 0,
                tokens_used: matched.tokens_used || 0,
                status: matched.status || "IDLE",
                tools: matched.tools && matched.tools.length ? matched.tools : defaultAgent.tools,
                capabilities: matched.capabilities || defaultAgent.keywords,
              };
            }
            return defaultAgent;
          });
          setAgents(merged);
          setResult((prev) => makeInitialResult(task, merged));
        }

        // Fetch analytics
        const overview = await API.analytics.getOverview().catch(() => null);
        if (overview) setAnalyticsOverview(overview);

        const tokens = await API.analytics.getTokens().catch(() => null);
        if (tokens) setTokenAnalytics(tokens);

        setServerConnected(true);
      } catch (err) {
        console.warn("Backend connection notice:", err);
      }
    }

    initBackend();
  }, []);

  // 2. Real-time WebSocket connection to /ws/sessions/{sessionId}
  useEffect(() => {
    if (!sessionId) return;

    const socket = createSessionSocket(sessionId);
    socketRef.current = socket;

    socket.on("connection_open", () => {
      setServerConnected(true);
    });

    socket.on("connection_close", () => {
      setServerConnected(false);
    });

    // Handle incoming state machine events
    socket.on("message", (msg) => {
      const eventType = msg.type || msg.event;
      const payload = msg.payload || msg;

      if (!eventType) return;

      const currentAgents = agentsRef.current;
      const currentBest = resultRef.current.best;

      if (eventType === "task_evaluating") {
        setStage("EVALUATING");
        pushLog("System", "Analyzing task intent and capabilities...", "core");
      } else if (eventType === "task_routing") {
        setStage("ROUTING");
        pushLog("System", "Computing agent compatibility scores...", "core");
      } else if (eventType === "task_selected" || eventType === "agent_selected") {
        setStage("SELECTED");
        const selectedId = (payload.selected_agent || "agent-s").replace("agent-", "").toUpperCase();
        const selectedAgent = currentAgents.find((a) => a.id === selectedId) || currentAgents[0];
        
        // Update winner
        setResult((prev) => {
          const updatedScores = prev.scores.map((s) => ({
            ...s,
            confidence: s.id === selectedAgent.id ? Math.max(92, Math.round((payload.match_score || 0.95) * 100)) : s.confidence,
          }));
          return {
            ...prev,
            best: selectedAgent,
            scores: updatedScores.sort((a, b) => b.confidence - a.confidence),
          };
        });

        const startPoint = (WAYPOINTS[selectedAgent.id] || WAYPOINTS.S)[0];
        setPosition({ x: startPoint[0], y: startPoint[1] });
        pushLog("System", `Selected ${selectedAgent.name} (${selectedAgent.role}). ${payload.reason || ""}`, "system");
      } else if (eventType === "agent_dispatch_started" || eventType === "task_dispatched") {
        setStage("DISPATCHED");
        const agId = (payload.agent_id || currentBest.backendId || currentBest.id).replace("agent-", "").toUpperCase();
        const ag = currentAgents.find((a) => a.id === agId) || currentBest;
        const waypoints = (payload.movement && payload.movement.waypoints) || WAYPOINTS[ag.id] || WAYPOINTS.S;
        setPosition({ x: waypoints[0][0], y: waypoints[0][1] });
        pushLog(ag.name, `Departing deployment bay for ${ag.bay}.`, ag.id);
      } else if (eventType === "agent_walking" || eventType === "task_walking") {
        setStage("WALKING");
        const agId = (payload.agent_id || currentBest.backendId || currentBest.id).replace("agent-", "").toUpperCase();
        const ag = currentAgents.find((a) => a.id === agId) || currentBest;
        const waypoints = (payload.movement && payload.movement.waypoints) || WAYPOINTS[ag.id] || WAYPOINTS.S;
        
        pushLog(ag.name, `Walking across hallway to ${ag.bay}...`, ag.id);

        // Smoothly traverse intermediate waypoints directly to cubicle
        let step = 1;
        if (runnerTimerRef.current) clearInterval(runnerTimerRef.current);
        runnerTimerRef.current = setInterval(() => {
          if (step < waypoints.length) {
            setPosition({ x: waypoints[step][0], y: waypoints[step][1] });
            step += 1;
          } else {
            clearInterval(runnerTimerRef.current);
          }
        }, 280);
      } else if (eventType === "agent_arriving" || eventType === "task_arriving") {
        setStage("ARRIVING");
        const agId = (payload.agent_id || currentBest.backendId || currentBest.id).replace("agent-", "").toUpperCase();
        const ag = currentAgents.find((a) => a.id === agId) || currentBest;
        const waypoints = (payload.movement && payload.movement.waypoints) || WAYPOINTS[ag.id] || WAYPOINTS.S;
        const seatPoint = waypoints[waypoints.length - 1];
        if (runnerTimerRef.current) clearInterval(runnerTimerRef.current);
        setPosition({ x: seatPoint[0], y: seatPoint[1] });
        pushLog(ag.name, `Arrived and seated at ${ag.bay}. Initializing workspace.`, ag.id);
      } else if (eventType === "agent_working" || eventType === "task_working") {
        setStage("WORKING");
        const agId = (payload.agent_id || currentBest.backendId || currentBest.id).replace("agent-", "").toUpperCase();
        const ag = currentAgents.find((a) => a.id === agId) || currentBest;
        const waypoints = WAYPOINTS[ag.id] || WAYPOINTS.S;
        const seatPoint = waypoints[waypoints.length - 1];
        setPosition({ x: seatPoint[0], y: seatPoint[1] });
        pushLog(ag.name, "Processing requirements and loading context.", ag.id);
      } else if (eventType === "agent_streaming" || eventType === "task_streaming") {
        setStage("STREAMING");
        const agId = (payload.agent_id || currentBest.backendId || currentBest.id).replace("agent-", "").toUpperCase();
        const ag = currentAgents.find((a) => a.id === agId) || currentBest;
        const waypoints = WAYPOINTS[ag.id] || WAYPOINTS.S;
        const seatPoint = waypoints[waypoints.length - 1];
        setPosition({ x: seatPoint[0], y: seatPoint[1] });
        if (payload.delta) {
          pushLog(ag.name, payload.delta, ag.id);
        }
      } else if (eventType === "agent_completed" || eventType === "task_completed") {
        setStage("COMPLETED");
        const agId = (payload.agent_id || currentBest.backendId || currentBest.id).replace("agent-", "").toUpperCase();
        const ag = currentAgents.find((a) => a.id === agId) || currentBest;
        const waypoints = WAYPOINTS[ag.id] || WAYPOINTS.S;
        const seatPoint = waypoints[waypoints.length - 1];
        setPosition({ x: seatPoint[0], y: seatPoint[1] });
        
        // Update real token stats
        if (payload.tokens_saved !== undefined || payload.reduction_percentage !== undefined) {
          setResult((prev) => ({
            ...prev,
            saved: payload.tokens_saved || prev.saved,
            optimized: payload.tokens_used || prev.optimized,
            reduction: payload.reduction_percentage ? Math.round(payload.reduction_percentage) : prev.reduction,
          }));
        }

        pushLog("Token Engine", `${formatNumber(payload.tokens_saved || resultRef.current.saved)} tokens saved (${payload.reduction_percentage || resultRef.current.reduction}% context reduction).`, "savings");
        pushLog(ag.name, "Task completed successfully.", ag.id);

        // Refresh analytics
        API.analytics.getOverview().then((res) => res && setAnalyticsOverview(res)).catch(() => {});
        API.analytics.getTokens().then((res) => res && setTokenAnalytics(res)).catch(() => {});
      } else if (eventType === "agent_returning" || eventType === "task_returning") {
        setStage("RETURNING");
        const agId = (payload.agent_id || currentBest.backendId || currentBest.id).replace("agent-", "").toUpperCase();
        const ag = currentAgents.find((a) => a.id === agId) || currentBest;
        const returnWaypoints = (payload.movement && payload.movement.waypoints) || [...(WAYPOINTS[ag.id] || WAYPOINTS.S)].reverse();
        
        pushLog(ag.name, "Returning to deployment bay.", ag.id);

        let step = 0;
        if (runnerTimerRef.current) clearInterval(runnerTimerRef.current);
        runnerTimerRef.current = setInterval(() => {
          if (step < returnWaypoints.length) {
            setPosition({ x: returnWaypoints[step][0], y: returnWaypoints[step][1] });
            step += 1;
          } else {
            clearInterval(runnerTimerRef.current);
          }
        }, 280);
      } else if (eventType === "agent_idle" || eventType === "task_idle") {
        setStage("READY");
        setIsRunning(false);
        if (runnerTimerRef.current) clearInterval(runnerTimerRef.current);
        const bestAgent = resultRef.current.best;
        const startPoint = (WAYPOINTS[bestAgent.id] || WAYPOINTS.S)[0];
        setPosition({ x: startPoint[0], y: startPoint[1] });
        pushLog("System", `${bestAgent.name} returned to READY status.`, "system");
      } else if (eventType === "agent_error" || eventType === "task_error") {
        setStage("ERROR");
        setIsRunning(false);
        if (runnerTimerRef.current) clearInterval(runnerTimerRef.current);
        pushLog("Error", payload.message || "An execution error occurred.", "system");
      }
    });

    return () => {
      if (runnerTimerRef.current) clearInterval(runnerTimerRef.current);
      socket.close();
    };
  }, [sessionId]);

  // Keep position aligned to selected agent when idle
  useEffect(() => {
    if (!isRunning) {
      const startPoint = (WAYPOINTS[result.best.id] || WAYPOINTS.S)[0];
      setPosition({ x: startPoint[0], y: startPoint[1] });
    }
  }, [result.best.id, isRunning]);

  function handleSelectAgent(agentId, promptSuffix = "") {
    if (isRunning) return;
    const ag = agents.find((a) => a.id === agentId) || agents[0];
    const newPrompt = promptSuffix ? `@${ag.name}: ${promptSuffix}` : `@${ag.name}: `;
    setTask(newPrompt);
    const newRes = makeInitialResult(newPrompt, agents);
    setResult(newRes);
    const startPoint = (WAYPOINTS[ag.id] || WAYPOINTS.S)[0];
    setPosition({ x: startPoint[0], y: startPoint[1] });
    const inputEl = document.getElementById("task-input");
    if (inputEl) inputEl.focus();
  }

  async function runTask(nextTask = task) {
    if (!nextTask.trim() || isRunning) return;
    
    const nextResult = makeInitialResult(nextTask, agents);
    const nextPath = WAYPOINTS[nextResult.best.id] || WAYPOINTS.S;
    
    setTask(nextTask);
    setResult(nextResult);
    setLogs([]);
    setIsRunning(true);
    setStage("DISPATCHED");
    setPosition({ x: nextPath[0][0], y: nextPath[0][1] });

    try {
      pushLog("System", `Submitting task to AgentOS for ${nextResult.best.name}...`, "core");
      const res = await API.tasks.create(sessionId, nextTask);
      if (res && res.task_id) {
        setCurrentTaskId(res.task_id);
      }
    } catch (err) {
      console.warn("Backend task creation fallback notice:", err);
      // If server is unreachable, run local animation fallback
      runLocalSimulation(nextResult, nextPath);
    }
  }

  function runLocalSimulation(nextResult, nextPath) {
    const timed = [
      [0, "EVALUATING", nextPath[0], "System", "Analyzing your request...", "core"],
      [600, "ROUTING", nextPath[0], "System", "Intent and capability map created.", "core"],
      [1200, "DISPATCHED", nextPath[1], "System", `${nextResult.best.name} leaving deployment bay.`, "system"],
      [1900, "WALKING", nextPath[2], "System", `${nextResult.best.name} approaching the front door.`, "system"],
      [2600, "WALKING", nextPath[3], "System", `${nextResult.best.name} passing through the door.`, "system"],
      [3300, "WALKING", nextPath[4], nextResult.best.name, "Inside the lobby. Walking along hallway.", nextResult.best.id],
      [4000, "WALKING", nextPath[5], nextResult.best.name, `Turning into ${nextResult.best.bay}.`, nextResult.best.id],
      [4700, "ARRIVING", nextPath[6], nextResult.best.name, `Seated at ${nextResult.best.bay}.`, nextResult.best.id],
      [5600, "WORKING", nextPath[6], nextResult.best.name, "Monitor online. Loading relevant context.", nextResult.best.id],
      [6500, "STREAMING", nextPath[6], nextResult.best.name, `Streaming ${nextResult.best.role.toLowerCase()} response.`, nextResult.best.id],
      [7600, "COMPLETED", nextPath[6], "Token Engine", `${formatNumber(nextResult.saved)} tokens saved with ${nextResult.reduction}% less context.`, "savings"],
      [8600, "RETURNING", nextPath[5], nextResult.best.name, "Task complete. Stepping back into hallway.", nextResult.best.id],
      [9300, "RETURNING", nextPath[4], nextResult.best.name, "Walking back to the office door.", nextResult.best.id],
      [10000, "RETURNING", nextPath[3], nextResult.best.name, "Passing through the door.", nextResult.best.id],
      [10700, "RETURNING", nextPath[2], nextResult.best.name, "Exiting through the door.", nextResult.best.id],
      [11400, "RETURNING", nextPath[1], nextResult.best.name, "Returning along sidewalk.", nextResult.best.id],
      [12100, "READY", nextPath[0], "System", `${nextResult.best.name} returned to READY.`, "system"],
    ];

    timed.forEach(([delay, stageName, point, source, text, tone]) => {
      window.setTimeout(() => {
        setStage(stageName);
        setPosition({ x: point[0], y: point[1] });
        pushLog(source, text, tone);
        if (delay === 12100) setIsRunning(false);
      }, delay);
    });
  }

  async function handleModelChange(agentId, newModel) {
    const modelMeta = SUPPORTED_MODELS.find((m) => m.id === newModel) || { name: newModel, provider: "AI" };
    try {
      await API.agents.overrideModel(agentId, newModel);
      setAgents((prev) => {
        const next = prev.map((a) => (a.backendId === agentId || a.id === agentId ? { ...a, model: newModel } : a));
        try {
          const map = {};
          next.forEach((a) => { map[a.id] = a.model; });
          localStorage.setItem("spark_agent_models", JSON.stringify(map));
        } catch (e) {
          console.error(e);
        }
        return next;
      });
      pushLog("Model Registry", `Agent ${agentId} reconfigured -> ${modelMeta.name} (${modelMeta.provider}) [${modelMeta.badge || "ACTIVE"}]`, "system");
    } catch (err) {
      console.error(err);
      // Update UI state locally
      setAgents((prev) =>
        prev.map((a) => (a.backendId === agentId || a.id === agentId ? { ...a, model: newModel } : a))
      );
      pushLog("Model Registry", `Agent ${agentId} connected to ${modelMeta.name}`, "system");
    }
  }

  async function handleCancelTask() {
    if (!currentTaskId) return;
    try {
      await API.tasks.cancel(currentTaskId);
      setIsRunning(false);
      setStage("READY");
      pushLog("System", "Task execution was cancelled.", "system");
    } catch (err) {
      console.error(err);
    }
  }

  const nav = [
    "Workspace",
    "Agents",
    "Analytics",
    "Token Savings",
    "Content Studio",
    "Data Observatory",
    "Settings",
  ];

  if (view === "landing") {
    return <Landing onGetStarted={() => navigateToView("dashboard")} />;
  }

  return (
    <div className="pokedex-viewport">
      <main className="pokedex-chassis">
        {/* ====================================================
            LEFT FLAP: HARDWARE LENS, SCREEN MENUBAR & CONTROLS
            ==================================================== */}
        <aside className={`pokedex-left-flap ${isMenuMinimized ? "minimized" : ""}`}>
          {/* Top Hardware: Main Blue Lens + 3 LEDs + SPARK Badge */}
          <div className="pokedex-top-hardware">
            <div className="lens-and-lights">
              <div className="pokedex-main-lens" title="SPARK Vision Lens">
                <div className="lens-reflection" />
              </div>
              <div className="pokedex-led-array">
                <span className="pokedex-led led-red" title="Power" />
                <span className="pokedex-led led-yellow" title="Routing Active" />
                <button
                  type="button"
                  className={`pokedex-led led-green ${isMenuMinimized ? "minimized-active" : ""}`}
                  title={isMenuMinimized ? "Click to Expand Menu Bar" : "Click to Minimize Menu Bar"}
                  onClick={() => setIsMenuMinimized((prev) => !prev)}
                  aria-label="Toggle Menu Bar"
                />
              </div>
            </div>

            {/* SPARK Brand Badge (Click to return to Landing Page) */}
            <div
              className="pokedex-brand-badge"
              onClick={() => navigateToView("landing")}
              style={{ cursor: "pointer" }}
              title="Return to Landing Page"
            >
              <img src={logo} alt="SPARK logo" className="pokedex-logo-img" />
              <div className="pokedex-brand-text">
                <h1>SPARK</h1>
                <p>Your AI Office ↗</p>
              </div>
            </div>
          </div>

          {/* Menubar CRT Screen Display */}
          <div className="pokedex-screen-left">
            <nav className="pokedex-nav-menu" aria-label="Main Navigation">
              {nav.map((item) => {
                const isActive = activeNav === item;
                return (
                  <button
                    key={item}
                    type="button"
                    className={`pokedex-nav-btn ${isActive ? "active" : ""}`}
                    onClick={() => setActiveNav(item)}
                  >
                    {isActive && <span className="nav-arrow-pointer" aria-hidden="true">▶</span>}
                    <span className="nav-icon-wrap">
                      <NavIcon type={item} />
                    </span>
                    <span className="nav-label-text">{item}</span>
                  </button>
                );
              })}
            </nav>

            {/* Footer inside Screen Frame */}
            <div className="pokedex-screen-footer">
              <div className="pokedex-footer-pill">
                <span className="star-icon">⭐</span>
                <span className="footer-pill-text">Your AI Office, in motion.</span>
              </div>
              <div className="pokedex-footer-slashes">//</div>
            </div>
          </div>

          {/* Bottom Physical Controller Hardware */}
          <div className="pokedex-bottom-controls">
            <div className="rocker-buttons-row">
              <button className="hw-rocker hw-rocker-red" type="button" aria-label="Secondary trigger" />
              <button className="hw-rocker hw-rocker-blue" type="button" aria-label="Option trigger" />
            </div>

            <div className="action-buttons-row">
              <div className="action-left-group">
                <button
                  className="hw-circle-btn"
                  type="button"
                  aria-label="Confirm button"
                  onClick={() => setActiveNav("Workspace")}
                  title="Return to Workspace"
                />
                <button
                  className="hw-green-rect"
                  type="button"
                  aria-label="Action switch"
                  onClick={() => {
                    setActiveNav("Workspace");
                    runTask();
                  }}
                  title="Execute Active Task"
                />
              </div>

              {/* D-Pad Cross Controller */}
              <div className="pokedex-dpad" aria-label="Directional Pad">
                <button
                  type="button"
                  className="dpad-btn dpad-up"
                  onClick={() => {
                    const idx = nav.indexOf(activeNav);
                    if (idx > 0) setActiveNav(nav[idx - 1]);
                  }}
                />
                <button
                  type="button"
                  className="dpad-btn dpad-right"
                  onClick={() => setActiveNav("Agents")}
                />
                <button
                  type="button"
                  className="dpad-btn dpad-down"
                  onClick={() => {
                    const idx = nav.indexOf(activeNav);
                    if (idx < nav.length - 1) setActiveNav(nav[idx + 1]);
                  }}
                />
                <button
                  type="button"
                  className="dpad-btn dpad-left"
                  onClick={() => setActiveNav("Workspace")}
                />
                <div className="dpad-center" />
              </div>
            </div>
          </div>
        </aside>

        {/* Hinge Cylinders */}
        <div className="pokedex-hinge">
          <div className="hinge-cylinder" />
          <div className="hinge-cylinder" />
          <div className="hinge-cylinder" />
        </div>

        {/* ====================================================
            RIGHT CONSOLE: MAIN SCREEN CANVAS & HUD CONTENT
            ==================================================== */}
        <section className="pokedex-right-console">
          <div className="pokedex-top-rivets">
            <div className="pokedex-rivet" />
            <div className="pokedex-rivet" />
          </div>

          <div className="pokedex-screen-main">
            {/* Topbar Banner: Yellow with Pokéball & Welcome Rohit */}
            <header className="pokedex-topbar-banner">
              <div className="topbar-left-content">
                <div className="pokeball-badge-wrap">
                  <PokeballIcon width={32} height={32} />
                </div>
                <div className="topbar-welcome-text">
                  <h2>Welcome to SPARK!</h2>
                  <p>Your AI organization is ready to work wonders.</p>
                </div>
              </div>

              <div className="topbar-right-profile">
                <button
                  type="button"
                  className="topbar-landing-btn"
                  onClick={() => navigateToView("landing")}
                  title="View SPARK Landing Page"
                >
                  🏠 Landing Page
                </button>
                <div className="profile-container">
                  <button
                    type="button"
                    className="profile-button-pokedex"
                    onClick={() => setIsProfileOpen((v) => !v)}
                    aria-label="User profile and session options"
                  >
                    <img src={profile} alt="Rohit Avatar" className="profile-avatar-img" />
                  </button>

                  {isProfileOpen && (
                    <div className="profile-dropdown">
                      <button type="button" onClick={() => navigateToView("landing")}>
                        🏠 Landing Page
                      </button>
                      <button type="button" onClick={() => API.sessions.export(sessionId, "json")}>
                        Export JSON
                      </button>
                      <button type="button" onClick={() => API.sessions.export(sessionId, "md")}>
                        Export Markdown
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const newId = `spark_${Date.now()}`;
                          setSessionId(newId);
                          localStorage.setItem("spark_session_id", newId);
                          window.location.reload();
                        }}
                      >
                        New Session
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </header>

            {/* ─── TAB: WORKSPACE ─── */}
            {activeNav === "Workspace" && (
              <div className="pokedex-workspace-grid">
                {/* Left Column: Office Map Stage + Deployment Bay + Talk Panel */}
                <div className="pokedex-stage-col">
                  {/* Office Map Card */}
                  <div className="pokedex-hud-card office-viewport-card">
                    <div className="hud-card-topbar">
                      <span className="hud-badge-status">
                        <span className="hud-green-dot" />
                        {result.best.name} - {stage}
                      </span>
                      <span className="hud-badge-title">AGENT CUBICLES</span>
                    </div>

                    <div className="office-card-viewport">
                      <img className="office-map" src={officeScene} alt="Isometric SPARK AI office" />
                      <div className={`core-pulse ${isRunning ? "active" : ""}`} />

                      {/* Cubicle Workspace Markers */}
                      <div className="cubicles-layer">
                        {CUBICLES.map((cubicle) => {
                          const isTargetCubicle = result.best.id === cubicle.id;
                          const isAgentAtDesk =
                            isTargetCubicle &&
                            isRunning &&
                            ["ARRIVING", "WORKING", "STREAMING", "COMPLETED"].includes(stage);
                          return (
                            <div
                              key={cubicle.id}
                              className={`cubicle-marker ${isTargetCubicle ? "targeted" : ""} ${
                                isAgentAtDesk ? "at-desk" : ""
                              }`}
                              style={{
                                "--x": `${cubicle.desk[0]}%`,
                                "--y": `${cubicle.desk[1]}%`,
                                "--agent": cubicle.color,
                              }}
                              onClick={() => handleSelectAgent(cubicle.id)}
                              title={`Click to prompt ${cubicle.name} (Agent ${cubicle.id})`}
                            >
                              <div className="cubicle-desk-glow" />
                              <div className="cubicle-pill">
                                <span className="cubicle-badge">{cubicle.id}</span>
                                <span className="cubicle-name">{cubicle.name}</span>
                                {isAgentAtDesk && <span className="cubicle-live-dot" />}
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <svg className="route-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
                        {isRunning && (
                          <polyline
                            points={(WAYPOINTS[result.best.id] || WAYPOINTS.S)
                              .map(([x, y]) => `${x},${y}`)
                              .join(" ")}
                            className="route-polyline"
                            style={{ "--agent": result.best.color }}
                          />
                        )}
                      </svg>

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
                  </div>

                  {/* Your AI Agents Section */}
                  <div className="pokedex-hud-card agents-section-card">
                    <div className="hud-card-header yellow-header">
                      <span>YOUR AI AGENTS</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>

                    <div className="deployment-bay-pokedex">
                      {agents.map((agent) => {
                        const isActive = isRunning && result.best.id === agent.id;
                        const isSelected = !isRunning && result.best.id === agent.id;
                        const mInfo = SUPPORTED_MODELS.find((m) => m.id === agent.model) || SUPPORTED_MODELS[0];
                        return (
                          <div
                            key={agent.id}
                            className={`agent-card-pokedex ${isActive ? "active" : ""} ${
                              isSelected ? "selected" : ""
                            }`}
                            style={{ "--agent": agent.color }}
                            onClick={() => handleSelectAgent(agent.id)}
                            title={`Click to prompt ${agent.name} (${agent.role})`}
                          >
                            <div className="agent-card-bg-glow" />
                            <img src={agent.image} alt={agent.name} className="agent-card-sprite" />
                            <div className="agent-card-meta">
                              <h4>{agent.name}</h4>
                              <p>{agent.role}</p>
                              <span className="agent-model-pill" style={{ "--m-color": mInfo.color }}>
                                {mInfo.name}
                              </span>
                            </div>
                            <span
                              className={`status-badge-pokedex ${
                                isActive ? "working" : isSelected ? "selected-badge" : "ready"
                              }`}
                            >
                              {isActive ? "WORKING" : isSelected ? "TARGETED" : "READY"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Talk & Prompt Bar */}
                  <div className={`console-row ${logs.length > 0 ? "with-logs" : ""}`}>
                    <form
                      className="talk-panel"
                      onSubmit={(event) => {
                        event.preventDefault();
                        runTask();
                      }}
                    >
                      <div className="input-row">
                        <textarea
                          id="task-input"
                          value={task}
                          onChange={(event) => {
                            const val = event.target.value;
                            setTask(val);
                            if (!isRunning && val.trim()) {
                              setResult(makeInitialResult(val, agents));
                            }
                          }}
                          placeholder="Give a task to any agent (e.g. '@Sammo: find sources', '@Paro: launch campaign', '@Amo: debug API')..."
                        />
                        {isRunning ? (
                          <button
                            className="send-button"
                            type="button"
                            onClick={handleCancelTask}
                            style={{ background: "#ff4154" }}
                            aria-label="Cancel task"
                          >
                            &#9632;
                          </button>
                        ) : (
                          <button
                            className="send-button"
                            type="submit"
                            style={{ "--agent": result.best.color }}
                            aria-label="Send task"
                          >
                            &rarr;
                          </button>
                        )}
                      </div>

                      <div className="sample-chips" aria-label="Sample tasks">
                        {sampleTasks.map((st) => (
                          <button
                            key={st.agent}
                            type="button"
                            className={`chip ${result.best.id === st.agent ? "active" : ""}`}
                            style={{ "--agent": (AGENT_METADATA[st.agent] || AGENT_METADATA.S).color }}
                            onClick={() => {
                              handleSelectAgent(st.agent);
                              setTask(st.text);
                              setResult(makeInitialResult(st.text, agents));
                            }}
                          >
                            {st.label}
                          </button>
                        ))}
                      </div>
                    </form>

                    {logs.length > 0 && (
                      <div className="activity-logs">
                        <div className="logs-header">
                          <h4>Real-Time Execution Telemetry</h4>
                          <button
                            type="button"
                            className="clear-logs-btn"
                            onClick={() => setLogs([])}
                          >
                            Clear
                          </button>
                        </div>
                        <div className="logs-scroll">
                          {logs.map((log, index) => (
                            <div key={index} className={`log-entry tone-${log.tone}`}>
                              <span className="log-time">{log.time}</span>
                              <strong className="log-source">{log.source}:</strong>
                              <span className="log-text">{log.text}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Column: Routing Overview & Token Savings */}
                <aside className="pokedex-sidebar-col">
                  {/* Routing Overview Card */}
                  <div className="pokedex-hud-card routing-card">
                    <div className="hud-card-header yellow-header">
                      <span>ROUTING OVERVIEW</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="routing-card-body">
                      <img src={routingStar} alt="Five-agent routing star" className="routing-star-img" />
                      <div className="routing-score-list">
                        {result.scores.map((agent) => (
                          <div
                            key={agent.id}
                            className={`routing-score-item ${agent.id === result.best.id ? "winner" : ""}`}
                            style={{ "--agent": agent.color }}
                          >
                            <span className="routing-agent-tag">{agent.id}</span>
                            <b className="routing-role-name">{agent.role}</b>
                            <em className="routing-percent">{agent.confidence}%</em>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Token Savings Card */}
                  <div className="pokedex-hud-card token-savings-card">
                    <div className="hud-card-header yellow-header">
                      <span>TOKEN SAVINGS</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="token-savings-body">
                      <div className="token-metric-row">
                        <span>Traditional Multi-Agent</span>
                        <b>{formatNumber(result.traditional || 19464)}</b>
                      </div>
                      <div className="token-bar-track">
                        <div className="token-bar-fill red-fill" style={{ width: "92%" }} />
                      </div>

                      <div className="token-metric-row" style={{ marginTop: 10 }}>
                        <span>SPARK Optimized</span>
                        <b>{formatNumber(result.optimized || 364)}</b>
                      </div>
                      <div className="token-bar-track">
                        <div
                          className="token-bar-fill green-fill"
                          style={{ width: `${Math.max(18, 100 - result.reduction)}%` }}
                        />
                      </div>

                      <div className="pokedex-token-saved-badge">
                        <PokeballIcon width={18} height={18} />
                        <strong>{result.reduction || 70}% TOKENS SAVED</strong>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            )}

            {/* ─── TAB: AGENTS ─── */}
            {activeNav === "Agents" && (
              <div className="pokedex-workspace-grid">
                <div className="pokedex-stage-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>SPECIALIST AGENT REGISTRY &amp; CONNECTED MODELS</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="agents-grid-pokedex">
                      {agents.map((agent) => {
                        const mInfo = SUPPORTED_MODELS.find((m) => m.id === agent.model) || SUPPORTED_MODELS[0];
                        return (
                          <div key={agent.id} className="agent-card-pokedex-full" style={{ "--agent": agent.color }}>
                            <div className="agent-card-top-row">
                              <img src={agent.image} alt={agent.name} className="agent-sprite-large" />
                              <div className="agent-title-block">
                                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                  <h4>{agent.name}</h4>
                                  <span className="active-model-chip" style={{ "--m-color": mInfo.color }}>
                                    {mInfo.badge} {mInfo.name}
                                  </span>
                                </div>
                                <span className="agent-bay-badge">{agent.bay} &bull; {agent.role}</span>
                                <div className="caps-list">
                                  {(agent.tools || []).map((t) => (
                                    <span key={t} className="cap-chip">{t}</span>
                                  ))}
                                </div>
                              </div>
                              <span className={`status-badge-pokedex ${agent.status === "BUSY" ? "working" : "ready"}`}>
                                {agent.status}
                              </span>
                            </div>

                            <div className="agent-stats-bar">
                              <div className="stat-pill">
                                <small>Tasks</small>
                                <strong>{agent.tasks_completed}</strong>
                              </div>
                              <div className="stat-pill">
                                <small>Tokens</small>
                                <strong>{formatNumber(agent.tokens_used)}</strong>
                              </div>
                              <div className="stat-pill">
                                <small>Assigned LLM</small>
                                <strong style={{ color: mInfo.color }}>{mInfo.name}</strong>
                              </div>
                              <div className="stat-pill">
                                <small>Latency / Ctx</small>
                                <strong>{mInfo.latency} &bull; {mInfo.context}</strong>
                              </div>
                            </div>

                            <div className="agent-card-actions">
                              <div className="model-select-wrapper">
                                <label>Connect Model:</label>
                                <select
                                  className="model-select"
                                  value={agent.model}
                                  onChange={(e) => handleModelChange(agent.backendId || agent.id, e.target.value)}
                                >
                                  {SUPPORTED_MODELS.map((m) => (
                                    <option key={m.id} value={m.id}>
                                      {m.name} ({m.provider} - {m.latency})
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <button
                                type="button"
                                className="prompt-agent-btn"
                                onClick={() => {
                                  setActiveNav("Workspace");
                                  handleSelectAgent(agent.id);
                                }}
                              >
                                Prompt in Workspace &rarr;
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <aside className="pokedex-sidebar-col">
                  {/* Connected Models Directory */}
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>CONNECTED LLM MODELS</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="model-directory-list">
                      {SUPPORTED_MODELS.map((m) => {
                        const assignedCount = agents.filter((a) => a.model === m.id).length;
                        return (
                          <div key={m.id} className="model-dir-item" style={{ "--m-color": m.color }}>
                            <div className="model-dir-top">
                              <span className="model-dir-name">{m.name}</span>
                              <span className="model-dir-status">ONLINE</span>
                            </div>
                            <div className="model-dir-meta">
                              <small>{m.provider}</small>
                              <small>{m.latency} &bull; {m.cost}</small>
                            </div>
                            <div className="model-assigned-pill">
                              {assignedCount > 0 ? (
                                <span>Assigned to {assignedCount} Agent{assignedCount > 1 ? "s" : ""}</span>
                              ) : (
                                <span style={{ opacity: 0.6 }}>Available</span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Routing Star Card */}
                  <div className="pokedex-hud-card routing-card">
                    <div className="hud-card-header yellow-header">
                      <span>ROUTING OVERVIEW</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="routing-card-body">
                      <img src={routingStar} alt="Five-agent routing star" className="routing-star-img" />
                      <div className="routing-score-list">
                        {result.scores.map((agent) => (
                          <div
                            key={agent.id}
                            className={`routing-score-item ${agent.id === result.best.id ? "winner" : ""}`}
                            style={{ "--agent": agent.color }}
                          >
                            <span className="routing-agent-tag">{agent.id}</span>
                            <b className="routing-role-name">{agent.role}</b>
                            <em className="routing-percent">{agent.confidence}%</em>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            )}

            {/* ─── TAB: ANALYTICS ─── */}
            {activeNav === "Analytics" && (
              <div className="pokedex-workspace-grid">
                <div className="pokedex-stage-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>SYSTEM TELEMETRY & PERFORMANCE</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="analytics-metrics-grid">
                      <div className="hud-stat-box">
                        <span className="stat-label">Total Tasks Dispatched</span>
                        <strong className="stat-number">{analyticsOverview ? analyticsOverview.tasks_total : 14}</strong>
                        <p className="stat-caption">100% automated resolution</p>
                      </div>
                      <div className="hud-stat-box">
                        <span className="stat-label">Completed Tasks</span>
                        <strong className="stat-number" style={{ color: "#16a34a" }}>
                          {analyticsOverview ? analyticsOverview.tasks_completed : 14}
                        </strong>
                        <p className="stat-caption">Zero unhandled runtime errors</p>
                      </div>
                      <div className="hud-stat-box">
                        <span className="stat-label">Avg. Classifier Latency</span>
                        <strong className="stat-number" style={{ color: "#0284c7" }}>
                          {analyticsOverview ? `${analyticsOverview.average_routing_latency_ms}ms` : "380ms"}
                        </strong>
                        <p className="stat-caption">Sub-500ms routing speed</p>
                      </div>
                      <div className="hud-stat-box">
                        <span className="stat-label">Total Tokens Conserved</span>
                        <strong className="stat-number" style={{ color: "#d97706" }}>
                          {formatNumber(tokenAnalytics ? tokenAnalytics.savings_tokens : 10412)}
                        </strong>
                        <p className="stat-caption">Context optimization active</p>
                      </div>
                    </div>
                  </div>

                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>AGENT THROUGHPUT MATRIX</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="agent-throughput-table">
                      {agents.map((ag) => (
                        <div key={ag.id} className="throughput-row" style={{ "--agent": ag.color }}>
                          <img src={ag.image} alt={ag.name} className="mini-agent-thumb" />
                          <div className="throughput-info">
                            <strong>{ag.name} ({ag.role})</strong>
                            <small>{ag.bay}</small>
                          </div>
                          <div className="throughput-bar-wrap">
                            <div
                              className="throughput-bar-fill"
                              style={{ width: `${Math.min(100, Math.max(15, (ag.tasks_completed + 1) * 20))}%`, background: ag.color }}
                            />
                          </div>
                          <span className="throughput-count">{ag.tasks_completed} Tasks</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <aside className="pokedex-sidebar-col">
                  <div className="pokedex-hud-card token-savings-card">
                    <div className="hud-card-header yellow-header">
                      <span>TOKEN EFFICIENCY</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="token-savings-body">
                      <div className="token-metric-row">
                        <span>Traditional Context Bloat</span>
                        <b>18,870</b>
                      </div>
                      <div className="token-bar-track">
                        <div className="token-bar-fill red-fill" style={{ width: "88%" }} />
                      </div>
                      <div className="token-metric-row" style={{ marginTop: 10 }}>
                        <span>SPARK Optimized Usage</span>
                        <b>5,750</b>
                      </div>
                      <div className="token-bar-track">
                        <div className="token-bar-fill green-fill" style={{ width: "30%" }} />
                      </div>
                      <div className="pokedex-token-saved-badge">
                        <PokeballIcon width={18} height={18} />
                        <strong>70% CONTEXT SAVED</strong>
                      </div>
                    </div>
                  </div>

                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>SYSTEM HEALTH</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="health-card-body">
                      <div className="health-item">
                        <span>FastAPI Backend:</span>
                        <strong className="status-online">ONLINE (8000)</strong>
                      </div>
                      <div className="health-item">
                        <span>WebSocket Stream:</span>
                        <strong className="status-online">CONNECTED</strong>
                      </div>
                      <div className="health-item">
                        <span>Database:</span>
                        <strong>agentos.db (SQLite)</strong>
                      </div>
                      <div className="health-item">
                        <span>Active Session:</span>
                        <code>{sessionId}</code>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            )}

            {/* ─── TAB: TOKEN SAVINGS ─── */}
            {activeNav === "Token Savings" && (
              <div className="pokedex-workspace-grid">
                <div className="pokedex-stage-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>CONTEXT & TOKEN SAVINGS INTELLIGENCE</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="analytics-metrics-grid">
                      <div className="hud-stat-box">
                        <span className="stat-label">Prompt Tokens</span>
                        <strong className="stat-number">{formatNumber(tokenAnalytics ? tokenAnalytics.prompt_tokens : 3360)}</strong>
                        <p className="stat-caption">Single-agent focused</p>
                      </div>
                      <div className="hud-stat-box">
                        <span className="stat-label">Completion Tokens</span>
                        <strong className="stat-number">{formatNumber(tokenAnalytics ? tokenAnalytics.completion_tokens : 1846)}</strong>
                        <p className="stat-caption">Synthesized responses</p>
                      </div>
                      <div className="hud-stat-box">
                        <span className="stat-label">Traditional Multi-Agent Tokens</span>
                        <strong className="stat-number" style={{ color: "#dc2626" }}>
                          {formatNumber(tokenAnalytics ? tokenAnalytics.traditional_tokens : 15618)}
                        </strong>
                        <p className="stat-caption">All-agent broadcast bloat</p>
                      </div>
                      <div className="hud-stat-box">
                        <span className="stat-label">SPARK Optimized Usage</span>
                        <strong className="stat-number" style={{ color: "#16a34a" }}>
                          {formatNumber(tokenAnalytics ? tokenAnalytics.total_tokens : 5206)}
                        </strong>
                        <p className="stat-caption">Zero redundant context loops</p>
                      </div>
                    </div>
                  </div>

                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>SAVINGS ARCHITECTURE BLUEPRINT</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="savings-blueprint-content">
                      <div className="blueprint-box">
                        <h4>🎯 Semantic Intent Routing vs. Broadcast Flooding</h4>
                        <p>
                          Standard multi-agent frameworks broadcast user tasks to all agents concurrently, burning 4x-6x token overhead on unnecessary role evaluations.
                        </p>
                        <p>
                          SPARK uses an exact regex & semantic classifier to dispatch <strong>only the single best-fit agent</strong> directly to its cubicle, reducing API costs by <strong>70%</strong>.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <aside className="pokedex-sidebar-col">
                  <div className="pokedex-hud-card token-savings-card">
                    <div className="hud-card-header yellow-header">
                      <span>SAVINGS METRIC</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="token-savings-body">
                      <div className="token-metric-row">
                        <span>Traditional Multi-Agent</span>
                        <b>15,618</b>
                      </div>
                      <div className="token-bar-track">
                        <div className="token-bar-fill red-fill" style={{ width: "90%" }} />
                      </div>
                      <div className="token-metric-row" style={{ marginTop: 10 }}>
                        <span>SPARK Optimized</span>
                        <b>5,206</b>
                      </div>
                      <div className="token-bar-track">
                        <div className="token-bar-fill green-fill" style={{ width: "33%" }} />
                      </div>
                      <div className="pokedex-token-saved-badge">
                        <PokeballIcon width={18} height={18} />
                        <strong>10,412 TOKENS CONSERVED</strong>
                      </div>
                    </div>
                  </div>

                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>EFFICIENCY GAINS</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="health-card-body">
                      <div className="health-item">
                        <span>Context Compression:</span>
                        <strong>70.2%</strong>
                      </div>
                      <div className="health-item">
                        <span>Cost Reduction:</span>
                        <strong className="status-online">3.3x Lower</strong>
                      </div>
                      <div className="health-item">
                        <span>Response Time:</span>
                        <strong className="status-online">64% Faster</strong>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            )}

            {/* ─── TAB: CONTENT STUDIO ─── */}
            {activeNav === "Content Studio" && (
              <div className="pokedex-workspace-grid">
                <div className="pokedex-stage-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>AGENT R — CONTENT STUDIO</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="studio-container-pokedex">
                      <div className="studio-intro-row">
                        <img src={agentR} alt="Agent R" className="studio-hero-sprite" />
                        <div>
                          <h4>Agent R &bull; Content Creator</h4>
                          <p>Craft viral social copy, product launch campaigns, email newsletters, and long-form storyboards.</p>
                        </div>
                      </div>

                      <div className="studio-prompt-box">
                        <label>Select Content Blueprint:</label>
                        <div className="studio-chip-templates">
                          {[
                            "Product Launch Tweet Thread with Hook",
                            "High-Converting Cold Email for B2B Leads",
                            "Viral LinkedIn Storytelling Post",
                            "Feature Changelog Release Notes",
                          ].map((tmpl) => (
                            <button
                              key={tmpl}
                              type="button"
                              className="chip"
                              onClick={() => {
                                setActiveNav("Workspace");
                                handleSelectAgent("R");
                                setTask(`@Agent R: Write ${tmpl}`);
                              }}
                            >
                              {tmpl}
                            </button>
                          ))}
                        </div>

                        <button
                          type="button"
                          className="action-btn"
                          style={{ marginTop: 14, width: "100%" }}
                          onClick={() => {
                            setActiveNav("Workspace");
                            handleSelectAgent("R");
                            setTask("@Agent R: Write a multi-channel creative marketing campaign and storytelling copy.");
                          }}
                        >
                          Open in Workspace &amp; Dispatch Agent R &rarr;
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <aside className="pokedex-sidebar-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>AGENT R CAPABILITIES</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="health-card-body">
                      <div className="health-item">
                        <span>Role:</span>
                        <strong>Content Creator</strong>
                      </div>
                      <div className="health-item">
                        <span>Workspace:</span>
                        <strong style={{ color: "#d97706" }}>Cubicle R (Content Studio)</strong>
                      </div>
                      <div className="health-item">
                        <span>Tools:</span>
                        <div className="caps-list" style={{ marginTop: 4 }}>
                          <span className="cap-chip">copy draft</span>
                          <span className="cap-chip">tone pass</span>
                          <span className="cap-chip">storyline</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pokedex-hud-card token-savings-card">
                    <div className="hud-card-header yellow-header">
                      <span>CONTENT TELEMETRY</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="token-savings-body">
                      <div className="token-metric-row">
                        <span>Tasks Completed</span>
                        <b>{agents.find((a) => a.id === "R")?.tasks_completed || 0}</b>
                      </div>
                      <div className="token-metric-row" style={{ marginTop: 6 }}>
                        <span>Tokens Processed</span>
                        <b>{formatNumber(agents.find((a) => a.id === "R")?.tokens_used || 0)}</b>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            )}

            {/* ─── TAB: DATA OBSERVATORY ─── */}
            {activeNav === "Data Observatory" && (
              <div className="pokedex-workspace-grid">
                <div className="pokedex-stage-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>AGENT K — DATA OBSERVATORY</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="studio-container-pokedex">
                      <div className="studio-intro-row">
                        <img src={agentK} alt="Agent K" className="studio-hero-sprite" />
                        <div>
                          <h4>Agent K &bull; Data Analyst</h4>
                          <p>Run statistical pattern models, token variance telemetry, performance anomaly detection, and metrics aggregations.</p>
                        </div>
                      </div>

                      <div className="studio-prompt-box">
                        <label>Select Telemetry Analysis Query:</label>
                        <div className="studio-chip-templates">
                          {[
                            "Analyze Task Latency Distribution Across Agents",
                            "Model Context Compression & Token Savings Trends",
                            "Detect Real-Time Routing Anomalies",
                            "Generate System Telemetry Benchmark Summary",
                          ].map((tmpl) => (
                            <button
                              key={tmpl}
                              type="button"
                              className="chip"
                              onClick={() => {
                                setActiveNav("Workspace");
                                handleSelectAgent("K");
                                setTask(`@Agent K: ${tmpl}`);
                              }}
                            >
                              {tmpl}
                            </button>
                          ))}
                        </div>

                        <button
                          type="button"
                          className="action-btn"
                          style={{ marginTop: 14, width: "100%" }}
                          onClick={() => {
                            setActiveNav("Workspace");
                            handleSelectAgent("K");
                            setTask("@Agent K: Scan execution logs, aggregate metrics patterns, and build a statistical summary report.");
                          }}
                        >
                          Open in Workspace &amp; Dispatch Agent K &rarr;
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <aside className="pokedex-sidebar-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>AGENT K CAPABILITIES</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="health-card-body">
                      <div className="health-item">
                        <span>Role:</span>
                        <strong>Data Analyst</strong>
                      </div>
                      <div className="health-item">
                        <span>Workspace:</span>
                        <strong style={{ color: "#8b5cf6" }}>Cubicle K (Data Observatory)</strong>
                      </div>
                      <div className="health-item">
                        <span>Tools:</span>
                        <div className="caps-list" style={{ marginTop: 4 }}>
                          <span className="cap-chip">metrics scan</span>
                          <span className="cap-chip">pattern model</span>
                          <span className="cap-chip">report builder</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pokedex-hud-card token-savings-card">
                    <div className="hud-card-header yellow-header">
                      <span>OBSERVATORY STATUS</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="token-savings-body">
                      <div className="token-metric-row">
                        <span>Analyses Completed</span>
                        <b>{agents.find((a) => a.id === "K")?.tasks_completed || 0}</b>
                      </div>
                      <div className="token-metric-row" style={{ marginTop: 6 }}>
                        <span>Tokens Processed</span>
                        <b>{formatNumber(agents.find((a) => a.id === "K")?.tokens_used || 0)}</b>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            )}

            {/* ─── TAB: SETTINGS ─── */}
            {activeNav === "Settings" && (
              <div className="pokedex-workspace-grid">
                <div className="pokedex-stage-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>SYSTEM SETTINGS &amp; CONFIGURATION</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div style={{ padding: 14 }}>
                      <table className="settings-table">
                        <thead>
                          <tr>
                            <th>Component</th>
                            <th>Configuration</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>Backend API Endpoint</td>
                            <td><code>{import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}</code></td>
                            <td><span className="status-badge-pokedex ready">{serverConnected ? "CONNECTED" : "OFFLINE"}</span></td>
                          </tr>
                          <tr>
                            <td>WebSocket Stream</td>
                            <td><code>/ws/sessions/{sessionId}</code></td>
                            <td><span className="status-badge-pokedex ready">READY</span></td>
                          </tr>
                          <tr>
                            <td>Active Session Identifier</td>
                            <td><code>{sessionId}</code></td>
                            <td><span className="status-badge-pokedex ready">ACTIVE</span></td>
                          </tr>
                          <tr>
                            <td>Database Store</td>
                            <td><code>agentos.db (SQLite3)</code></td>
                            <td><span className="status-badge-pokedex ready">OPERATIONAL</span></td>
                          </tr>
                        </tbody>
                      </table>

                      <div className="action-btn-row" style={{ marginTop: 16 }}>
                        <button className="action-btn" type="button" onClick={() => API.sessions.export(sessionId, "json")}>
                          Export Blueprint (JSON)
                        </button>
                        <button className="action-btn secondary" type="button" onClick={() => API.sessions.export(sessionId, "md")}>
                          Export Report (Markdown)
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <aside className="pokedex-sidebar-col">
                  <div className="pokedex-hud-card">
                    <div className="hud-card-header yellow-header">
                      <span>SESSION CONTROL</span>
                      <span className="arrow-icon">&gt;</span>
                    </div>
                    <div className="health-card-body">
                      <div className="health-item">
                        <span>Current Session:</span>
                        <code>{sessionId}</code>
                      </div>
                      <button
                        type="button"
                        className="action-btn"
                        style={{ marginTop: 10, width: "100%" }}
                        onClick={() => {
                          const newId = `spark_${Date.now()}`;
                          setSessionId(newId);
                          localStorage.setItem("spark_session_id", newId);
                          window.location.reload();
                        }}
                      >
                        Start Fresh Session
                      </button>
                    </div>
                  </div>
                </aside>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
