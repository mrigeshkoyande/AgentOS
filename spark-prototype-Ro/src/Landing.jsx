import { useState, useEffect } from 'react';
import logo from "./assets/spark-logo.png";
import officeScene from "./assets/office-scene.png";
import routingStar from "./assets/spark-star-new.png";
import agentM from "./assets/agent-m.png";
import agentA from "./assets/agent-a.png";
import agentS from "./assets/agent-s.png";
import agentC from "./assets/agent-c.png";
import agentD from "./assets/agent-d.png";
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
    role: "Social Media",
    color: "#ff5f96",
    bgColor: "#fff0f5",
    image: agentM,
    type: "SOCIAL",
    stats: { reach: 92, speed: 85, creativity: 96 },
    description: "Manages your entire social media presence — scheduling posts, tracking engagement, and drafting content across Instagram, LinkedIn, and Twitter.",
  },
  {
    id: "P",
    name: "Paro",
    role: "Personnel & HR",
    color: "#55b8ff",
    bgColor: "#f0f7ff",
    image: agentA,
    type: "HR",
    stats: { reach: 78, speed: 88, creativity: 72 },
    description: "Handles recruitment workflows end-to-end — parsing resumes, scheduling interviews, and automating candidate screening pipelines.",
  },
  {
    id: "A",
    name: "Amo",
    role: "Advertising & Marketing",
    color: "#ffc04b",
    bgColor: "#fff9e6",
    image: agentC,
    type: "MARKETING",
    stats: { reach: 95, speed: 80, creativity: 90 },
    description: "Powers your marketing engine with competitor analysis, ad copy generation, campaign reporting, and brand strategy optimization.",
  },
  {
    id: "R",
    name: "Repo",
    role: "Reporting & Operations",
    color: "#94db52",
    bgColor: "#f2ffe6",
    image: agentS,
    type: "OPS",
    stats: { reach: 82, speed: 94, creativity: 68 },
    description: "Keeps your operations running smoothly with task management, data visualization, workflow building, and automated business reports.",
  },
  {
    id: "K",
    name: "Kmailo",
    role: "Key Communications",
    color: "#a66bff",
    bgColor: "#f5f0ff",
    image: agentD,
    type: "COMMS",
    stats: { reach: 88, speed: 91, creativity: 76 },
    description: "Masters your communication channels — drafting emails, scanning inboxes, managing follow-ups, and coordinating meetings.",
  },
];

const TESTIMONIALS = [
  {
    quote: "SPARK cut our operational overhead by 60%. The agent routing is incredibly intelligent — it just knows which agent to deploy.",
    name: "Sarah Chen",
    title: "COO, TechNova Inc.",
    avatar: "SC",
    stars: 5,
  },
  {
    quote: "We replaced 4 different SaaS tools with SPARK. The token savings alone paid for itself in the first month.",
    name: "Marcus Rivera",
    title: "Head of Marketing, Bloom Digital",
    avatar: "MR",
    stars: 5,
  },
  {
    quote: "The AI office concept is brilliant. Watching agents walk to their cubicles and execute tasks makes AI feel tangible and trustworthy.",
    name: "Priya Sharma",
    title: "Founder, ScaleUp Labs",
    avatar: "PS",
    stars: 5,
  },
];

const FAQS = [
  {
    q: "What is SPARK?",
    a: "SPARK is an AI-powered virtual office platform that uses specialized agents to handle different business functions — from social media and HR to marketing, operations, and communications. Each agent is purpose-built, meaning it only loads the context it needs, saving tokens and delivering faster, more accurate results.",
  },
  {
    q: "How does the intelligent routing work?",
    a: "When you submit a task, SPARK's routing engine analyzes your intent and scores each agent based on keyword relevance, capability matching, and context requirements. The best-fit agent is dispatched to its designated cubicle, loads only the relevant context, and streams back results — all while you watch in real time.",
  },
  {
    q: "What makes SPARK different from other AI tools?",
    a: "Unlike traditional multi-agent systems that load all agents with full context, SPARK dispatches a single specialized agent with minimal, targeted context. This results in 60-80% fewer tokens processed, faster response times, and more accurate outputs.",
  },
  {
    q: "Can I customize the agents for my business?",
    a: "Absolutely. Each agent's knowledge base, tools, and workflows can be tailored to your specific industry and processes. You can define custom keywords, upload proprietary data, and configure agent behaviors to match your team's exact needs.",
  },
  {
    q: "Is my data secure?",
    a: "Yes. SPARK employs end-to-end encryption, role-based access controls, and isolated agent environments. Your data never crosses between agents unless explicitly configured, and all interactions are logged for full auditability.",
  },
];

function StatBar({ label, value, color }) {
  return (
    <div className="poke-stat">
      <span className="poke-stat-label">{label}</span>
      <div className="poke-stat-bar-bg">
        <div className="poke-stat-bar-fill" style={{ width: `${value}%`, background: color }}></div>
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
        <span className="poke-faq-num">#{String(index + 1).padStart(2, '0')}</span>
        <span className="poke-faq-text">{faq.q}</span>
        <span className={`poke-faq-arrow ${open ? "rotated" : ""}`}>▼</span>
      </button>
      <div className="poke-faq-answer">
        <p>{faq.a}</p>
      </div>
    </div>
  );
}

export function Landing({ onGetStarted }) {
  const [stars, setStars] = useState([]);

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
      <div className="poke-orb poke-orb-1"></div>
      <div className="poke-orb poke-orb-2"></div>
      <div className="poke-orb poke-orb-3"></div>

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
          <button className="poke-nav-cta" onClick={onGetStarted}>
            <span>⚡</span> Launch Dashboard
          </button>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="poke-hero">
        <div className="poke-hero-content">
          <div className="poke-badge-row">
            <span className="poke-badge poke-badge-fire">🔥 AI POWERED</span>
            <span className="poke-badge poke-badge-electric">⚡ 5 AGENTS</span>
          </div>
          <h1 className="poke-hero-title">
            Choose Your<br />
            <span className="poke-hero-gradient">AI Agent.</span>
          </h1>
          <p className="poke-hero-sub">
            Deploy specialized AI agents to handle your business tasks.
            Each agent has unique abilities — pick the right one and watch them work!
          </p>
          <div className="poke-hero-actions">
            <button className="poke-btn-primary" onClick={onGetStarted}>
              <span>Start Your Journey</span>
              <span className="poke-btn-arrow">→</span>
            </button>
            <a href="#agents" className="poke-btn-secondary">Meet the Agents</a>
          </div>
          <div className="poke-hero-mini-agents">
            {AGENTS_INFO.map(a => (
              <div key={a.id} className="poke-mini-agent" style={{"--c": a.color}}>
                <img src={a.image} alt={a.name} />
              </div>
            ))}
          </div>
        </div>
        <div className="poke-hero-visual">
          <div className="poke-hero-frame">
            <div className="poke-hero-frame-shine"></div>
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
              SPARK reimagines how AI agents work together. Instead of flooding every agent with your entire context,
              our intelligent routing engine dispatches a single, purpose-built specialist who loads only what's needed.
            </p>
            <div className="poke-stats-row">
              <div className="poke-stat-card" style={{"--accent": "#ff5f96"}}>
                <div className="poke-stat-card-value">5</div>
                <div className="poke-stat-card-label">Agents</div>
              </div>
              <div className="poke-stat-card" style={{"--accent": "#55b8ff"}}>
                <div className="poke-stat-card-value">78%</div>
                <div className="poke-stat-card-label">Token Savings</div>
              </div>
              <div className="poke-stat-card" style={{"--accent": "#94db52"}}>
                <div className="poke-stat-card-value">3×</div>
                <div className="poke-stat-card-label">Faster</div>
              </div>
            </div>
          </div>
          <div className="poke-about-visual">
            <div className="poke-star-container">
              <div className="poke-star-glow"></div>
              <img src={routingStar} alt="SPARK routing star" className="poke-star-img" />
            </div>
          </div>
        </div>
      </section>

      {/* ─── Agents ─── */}
      <section className="poke-agents" id="agents">
        <span className="poke-section-badge">🎮 AGENT ROSTER</span>
        <h2 className="poke-section-title poke-center">Choose Your <span>Agent</span></h2>
        <p className="poke-section-sub">Each agent is a domain expert with unique stats and abilities.</p>
        <div className="poke-agents-grid">
          {AGENTS_INFO.map((agent) => (
            <div className="poke-card" key={agent.id} style={{ "--accent": agent.color, "--bg-accent": agent.bgColor }}>
              <div className="poke-card-top">
                <span className="poke-card-name">{agent.name}</span>
                <span className="poke-card-type" style={{ background: agent.color }}>{agent.type}</span>
              </div>
              <div className="poke-card-img-area">
                <div className="poke-card-img-circle"></div>
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
        <h2 className="poke-section-title poke-center">Loved by <span>Teams</span></h2>
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
        <h2 className="poke-section-title poke-center">Frequently <span>Asked</span></h2>
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
              {AGENTS_INFO.map(a => (
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
              <h4>Company</h4>
              <a href="#">Blog</a>
              <a href="#">Careers</a>
              <a href="#">Contact</a>
            </div>
            <div className="poke-footer-col">
              <h4>Legal</h4>
              <a href="#">Privacy</a>
              <a href="#">Terms</a>
              <a href="#">Security</a>
            </div>
          </div>
        </div>
        <div className="poke-footer-bottom">
          <span>© {new Date().getFullYear()} SPARK AI — Gotta automate 'em all! ⚡</span>
        </div>
      </footer>
    </div>
  );
}
