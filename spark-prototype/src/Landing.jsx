import { useState, useEffect } from "react";
import logo from "./assets/spark-logo.png";
import officeScene from "./assets/office-scene.png";
import routingStar from "./assets/spark-star-new.png";
import agentS from "./assets/agent-s.png";
import agentP from "./assets/agent-p.png";
import agentA from "./assets/agent-a.png";
import agentR from "./assets/agent-r.png";
import agentK from "./assets/agent-k.png";
import blueSpark from "../images/blue Spark.png";
import greenSpark from "../images/green Spark.png";
import purpleSpark from "../images/purple Spark.png";
import redSpark from "../images/red Spark.png";
import yellowSpark from "../images/yellow Spark.png";

const SPARK_STARS = [
  { id: "blue", image: blueSpark, alt: "Blue SPARK star" },
  { id: "green", image: greenSpark, alt: "Green SPARK star" },
  { id: "purple", image: purpleSpark, alt: "Purple SPARK star" },
  { id: "red", image: redSpark, alt: "Red SPARK star" },
  { id: "yellow", image: yellowSpark, alt: "Yellow SPARK star" },
];

const AGENTS_INFO = [
  {
    id: "S",
    name: "Sammo",
    role: "Search & Support Specialist",
    color: "#ff5f96",
    bgColor: "#fff0f5",
    image: agentS,
    type: "SEARCH",
    stats: { reach: 98, speed: 95, creativity: 88 },
    description: "Resolves customer inquiries, scans live documentation, queries knowledge bases, and performs fast web research with precision.",
  },
  {
    id: "P",
    name: "Paro",
    role: "Creative Strategist",
    color: "#55b8ff",
    bgColor: "#f0f7ff",
    image: agentP,
    type: "CREATIVE",
    stats: { reach: 88, speed: 86, creativity: 98 },
    description: "Brainstorms campaigns, scripts engaging social narratives, writes compelling ad copy, and crafts high-converting marketing strategies.",
  },
  {
    id: "A",
    name: "Amo",
    role: "Analytics & Automation Specialist",
    color: "#7ed957",
    bgColor: "#f2ffe6",
    image: agentA,
    type: "AUTOMATION",
    stats: { reach: 94, speed: 92, creativity: 82 },
    description: "Constructs automated execution DAGs, connects API pipelines, analyzes system logs, and streamlines multi-step organizational workflows.",
  },
  {
    id: "R",
    name: "Repo",
    role: "Content Creator",
    color: "#ffc04b",
    bgColor: "#fff9e6",
    image: agentR,
    type: "CONTENT",
    stats: { reach: 91, speed: 89, creativity: 94 },
    description: "Generates long-form technical briefs, executive summaries, marketing assets, blog articles, and production-ready multimedia copy.",
  },
  {
    id: "K",
    name: "Kmailo",
    role: "Data Analyst",
    color: "#a66bff",
    bgColor: "#f5f0ff",
    image: agentK,
    type: "DATA",
    stats: { reach: 96, speed: 91, creativity: 84 },
    description: "Processes structured telemetry, models business trends, predicts token consumption metrics, and builds real-time observatory dashboards.",
  },
];

const TESTIMONIALS = [
  {
    quote: "SPARK cut our operational overhead by 78%. The single-agent routing engine is pure magic — it knows exactly who to dispatch.",
    name: "Sarah Chen",
    title: "COO, TechNova Inc.",
    avatar: "SC",
    stars: 5,
  },
  {
    quote: "We replaced fragmented AI prompts with SPARK. The token savings alone paid for our annual subscription in 3 weeks.",
    name: "Marcus Rivera",
    title: "Head of AI Architecture, Bloom Digital",
    avatar: "MR",
    stars: 5,
  },
  {
    quote: "Watching agents walk to their cubicles in the isometric office map gives our team tangible visibility into autonomous operations.",
    name: "Priya Sharma",
    title: "Founder, ScaleUp Labs",
    avatar: "PS",
    stars: 5,
  },
];

const FAQS = [
  {
    q: "What is SPARK?",
    a: "SPARK is an AI Organization Operating System. Instead of a monolithic bot, SPARK deploys specialized AI agents (Agent S, P, A, R, K) across custom cubicle bays, reducing token overhead by up to 80% while maximizing output precision.",
  },
  {
    q: "How does the SPARK routing engine work?",
    a: "When you submit an admin task, the Star Routing Engine analyzes intent, score matches across agents, and dispatches the optimal agent to its cubicle. The agent loads only relevant context and streams execution results back via WebSockets.",
  },
  {
    q: "Which LLM models are supported?",
    a: "SPARK natively supports Gemini 1.5 Flash, Gemini 1.5 Pro, GPT-4o, Llama 3.1 70B, and Kimi K2. You can switch models on the fly for any agent in the Agent Registry.",
  },
  {
    q: "Can I customize the agent tools and instructions?",
    a: "Yes! Each agent has its own dedicated tools, system instructions, and execution bays. You can inspect telemetry, re-assign bays, and audit decision matrices from the Dashboard.",
  },
  {
    q: "Is data synchronized with the backend?",
    a: "All agent states, tasks, token savings metrics, and execution logs persist in SQLite and stream live to your browser over a real-time FastAPI WebSocket channel.",
  },
];

function StatBar({ label, value, color }) {
  return (
    <div className="poke-stat">
      <span className="poke-stat-label">{label}</span>
      <div className="poke-stat-bar-bg">
        <div className="poke-stat-bar-fill" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="poke-stat-value">{value}</span>
    </div>
  );
}

function FaqItem({ faq, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`poke-faq-item ${open ? "open" : ""}`}>
      <button className="poke-faq-question" onClick={() => setOpen(!open)} type="button">
        <span className="poke-faq-num">#{String(index + 1).padStart(2, "0")}</span>
        <span className="poke-faq-text">{faq.q}</span>
        <span className={`poke-faq-arrow ${open ? "rotated" : ""}`}>▼</span>
      </button>
      <div className="poke-faq-answer">
        <p>{faq.a}</p>
      </div>
    </div>
  );
}

export function Landing({ onCreateOrganization, onGetStarted }) {
  const [stars, setStars] = useState([]);
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const starList = SPARK_STARS.map((spark) => ({
      ...spark,
      left: `${Math.random() * 88 + 4}%`,
      top: `${Math.random() * 72 + 14}%`,
      size: `${Math.random() * 58 + 52}px`,
      delay: `${Math.random() * -18}s`,
      duration: `${Math.random() * 14 + 16}s`,
      driftX: `${Math.random() * 160 - 80}px`,
      driftY: `${Math.random() * 140 - 70}px`,
      rotation: `${Math.random() * 360}deg`,
      spin: `${Math.random() > 0.5 ? 1 : -1}`,
    }));
    setStars(starList);
  }, []);

  return (
    <div className="poke-landing">
      {/* Randomly floating background stars */}
      <div className="poke-stars-container">
        {stars.map((star) => (
          <img
            key={star.id}
            className="poke-star-particle"
            src={star.image}
            alt={star.alt}
            aria-hidden="true"
            style={{
              left: star.left,
              top: star.top,
              width: star.size,
              height: star.size,
              animationDelay: star.delay,
              animationDuration: star.duration,
              "--start-rotation": star.rotation,
              "--drift-x": star.driftX,
              "--drift-y": star.driftY,
              "--spin": star.spin,
            }}
          />
        ))}
      </div>

      {/* Floating decorative orbs */}
      <div className="poke-orb poke-orb-1" />
      <div className="poke-orb poke-orb-2" />
      <div className="poke-orb poke-orb-3" />

      {/* ─── Navbar ─── */}
      <nav className="poke-nav">
        <div className="poke-nav-brand">
          <img src={logo} alt="SPARK logo" />
          <h1>SPARK</h1>
        </div>
        <div className="poke-nav-links">
          <a href="#about">About</a>
          <a href="#agents">Agents</a>
          <a href="#testimonials">Reviews</a>
          <a href="#faq">FAQ</a>
          <button className="poke-nav-cta" onClick={onGetStarted} type="button">
            <span>⚡</span> Launch SPARK
          </button>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="poke-hero">
        <div className="poke-hero-content">
          <div className="poke-badge-row">
            <span className="poke-badge poke-badge-fire">🔥 AI WORKFORCE</span>
            <span className="poke-badge poke-badge-electric">⚡ 5 SPECIALIZED AGENTS</span>
          </div>
          <h1 className="poke-hero-title">
            Choose Your<br />
            <span className="poke-hero-gradient">AI Agent.</span>
          </h1>
          <p className="poke-hero-sub">
            Deploy specialized AI agents to execute your business workflows.
            Watch them walk to their cubicles in real time and deliver high-precision blueprints.
          </p>
          
          <form
            className="poke-hero-form"
            onSubmit={async (e) => {
              e.preventDefault();
              if (!description.trim() || loading) return;
              setLoading(true);
              setError("");
              try {
                await onCreateOrganization(description);
              } catch (err) {
                setError(err.message || "Failed to create organization");
                setLoading(false);
              }
            }}
            style={{ width: "100%", maxWidth: "520px", display: "flex", flexDirection: "column", gap: "12px", margin: "20px 0" }}
          >
            <textarea
              className="poke-hero-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter your project description (e.g. Build an AI-powered platform that helps small businesses automate customer support, analytics, marketing, and internal operations.)"
              required
              rows={3}
              disabled={loading}
              style={{
                width: "100%",
                padding: "14px 18px",
                borderRadius: "var(--nb-radius)",
                border: "var(--nb-border)",
                background: "#fff",
                color: "var(--nb-dark)",
                fontSize: "14px",
                fontWeight: "600",
                boxShadow: "var(--nb-shadow-sm)",
                resize: "none",
                outline: "none"
              }}
            />
            {error && (
              <p style={{ color: "#e11d48", fontWeight: "800", fontSize: "13px", margin: "0", textAlign: "left" }}>
                ⚠️ {error}
              </p>
            )}
            <div className="poke-hero-actions" style={{ marginTop: "4px" }}>
              <button
                className="poke-btn-primary"
                type="submit"
                disabled={loading}
                style={{ width: "100%", opacity: loading ? 0.75 : 1 }}
              >
                <span>{loading ? "Generating Organization..." : "⚡ Create Organization"}</span>
                <span className="poke-btn-arrow">→</span>
              </button>
            </div>
          </form>
          <div className="poke-hero-mini-agents">
            {AGENTS_INFO.map((a) => (
              <div key={a.id} className="poke-mini-agent" style={{ "--c": a.color }}>
                <img src={a.image} alt={a.name} />
              </div>
            ))}
          </div>
        </div>
        <div className="poke-hero-visual">
          <div className="poke-hero-frame" onClick={onGetStarted} style={{ cursor: "pointer" }} title="Click to Enter Workspace">
            <div className="poke-hero-frame-shine" />
            <img src={officeScene} alt="AI Office" />
          </div>
        </div>
      </section>

      {/* ─── About ─── */}
      <section className="poke-about" id="about">
        <div className="poke-about-inner">
          <div className="poke-about-text">
            <span className="poke-section-badge">📖 ABOUT SPARK</span>
            <h2 className="poke-section-title">One Office.<br /><span>Five Specialists.</span></h2>
            <p className="poke-about-desc">
              SPARK reimagines how autonomous AI agents collaborate. Instead of flooding every model with massive global context,
              our Star Routing Engine dispatches a single, purpose-built specialist who loads only what is required.
            </p>
            <div className="poke-stats-row">
              <div className="poke-stat-card" style={{ "--accent": "#ff5f96" }}>
                <div className="poke-stat-card-value">5</div>
                <div className="poke-stat-card-label">Agents</div>
              </div>
              <div className="poke-stat-card" style={{ "--accent": "#55b8ff" }}>
                <div className="poke-stat-card-value">78%</div>
                <div className="poke-stat-card-label">Token Savings</div>
              </div>
              <div className="poke-stat-card" style={{ "--accent": "#7ed957" }}>
                <div className="poke-stat-card-value">3×</div>
                <div className="poke-stat-card-label">Faster</div>
              </div>
            </div>
          </div>
          <div className="poke-about-visual">
            <div className="poke-star-container">
              <div className="poke-star-glow" />
              <img src={routingStar} alt="SPARK routing star" className="poke-star-img" />
            </div>
          </div>
        </div>
      </section>

      {/* ─── Agents ─── */}
      <section className="poke-agents" id="agents">
        <span className="poke-section-badge">🎮 AGENT ROSTER</span>
        <h2 className="poke-section-title poke-center">Choose Your <span>Agent</span></h2>
        <p className="poke-section-sub">Each agent is a domain expert with unique abilities, tools, and multi-model support.</p>
        <div className="poke-agents-grid">
          {AGENTS_INFO.map((agent) => (
            <div className="poke-card" key={agent.id} style={{ "--accent": agent.color, "--bg-accent": agent.bgColor }}>
              <div className="poke-card-top">
                <span className="poke-card-name">{agent.name}</span>
                <span className="poke-card-type" style={{ background: agent.color }}>{agent.type}</span>
              </div>
              <div className="poke-card-img-area">
                <div className="poke-card-img-circle" />
                <img src={agent.image} alt={agent.name} className="poke-card-img" />
              </div>
              <div className="poke-card-body">
                <p className="poke-card-role">{agent.role}</p>
                <p className="poke-card-desc">{agent.description}</p>
                <div className="poke-card-stats">
                  <StatBar label="RCH" value={agent.stats.reach} color={agent.color} />
                  <StatBar label="SPD" value={agent.stats.speed} color={agent.color} />
                  <StatBar label="CRE" value={agent.stats.creativity} color={agent.color} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Testimonials ─── */}
      <section className="poke-testimonials" id="testimonials">
        <span className="poke-section-badge">⭐ TRAINER REVIEWS</span>
        <h2 className="poke-section-title poke-center">Loved by <span>Engineering Teams</span></h2>
        <div className="poke-reviews-grid">
          {TESTIMONIALS.map((t, i) => (
            <div className="poke-review-card" key={i}>
              <div className="poke-review-stars">
                {"★".repeat(t.stars)}
              </div>
              <p className="poke-review-quote">"{t.quote}"</p>
              <div className="poke-review-author">
                <div className="poke-review-avatar">{t.avatar}</div>
                <div>
                  <strong>{t.name}</strong>
                  <span>{t.title}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section className="poke-faq" id="faq">
        <span className="poke-section-badge">❓ HELP CENTER</span>
        <h2 className="poke-section-title poke-center">Frequently <span>Asked Questions</span></h2>
        <div className="poke-faq-list">
          {FAQS.map((faq, i) => (
            <FaqItem key={i} faq={faq} index={i} />
          ))}
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="poke-footer">
        <div className="poke-footer-inner">
          <div className="poke-footer-brand">
            <img src={logo} alt="SPARK" />
            <h2>SPARK</h2>
            <p>Your AI office, in motion.</p>
            <div className="poke-footer-agents">
              {AGENTS_INFO.map((a) => (
                <img key={a.id} src={a.image} alt={a.name} />
              ))}
            </div>
          </div>
          <div className="poke-footer-links">
            <div className="poke-footer-col">
              <h4>Product</h4>
              <a href="#about">About</a>
              <a href="#agents">Agents</a>
              <a href="#faq">FAQ</a>
            </div>
            <div className="poke-footer-col">
              <h4>Console</h4>
              <button type="button" onClick={onGetStarted} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.7)", cursor: "pointer", padding: 0, textAlign: "left", fontSize: "14px", fontWeight: "500" }}>
                SPARK Workspace
              </button>
              <a href="#agents">Models</a>
              <a href="#about">Token Analytics</a>
            </div>
            <div className="poke-footer-col">
              <h4>Organization</h4>
              <a href="#">Documentation</a>
              <a href="#">Security</a>
              <a href="#">API Keys</a>
            </div>
          </div>
        </div>
        <div className="poke-footer-bottom">
          <span>© {new Date().getFullYear()} SPARK — AI Organization Operating System ⚡</span>
        </div>
      </footer>
    </div>
  );
}
