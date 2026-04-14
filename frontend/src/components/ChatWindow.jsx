import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import { sendMessage, clearSession } from "../api/chat";

const WELCOME = "👋 Hey there! I'm RoadWise, your AI road trip planner.\n\nLet's plan your perfect road trip! I'll ask you a few quick questions to build your personalized itinerary.\n\nFirst — where are you starting your trip from?";

const PLANNING_STEPS = [
  { id: "route",      label: "Calculating your route",        icon: "🗺️"  },
  { id: "gas",        label: "Computing gas stop schedule",    icon: "⛽"  },
  { id: "lodging",    label: "Finding places to stay",         icon: "🏨"  },
  { id: "food",       label: "Discovering restaurants",        icon: "🍽️" },
  { id: "activities", label: "Sourcing activities & sights",   icon: "📍"  },
  { id: "finalizing", label: "Assembling your trip plan",      icon: "✨"  },
];

function PlanningOverlay() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep(prev => (prev < PLANNING_STEPS.length - 1 ? prev + 1 : prev));
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="planning-overlay">
      <div className="planning-spinner" />
      <div>
        <div className="planning-title">Building your road trip...</div>
        <div className="planning-step" key={activeStep}>
          {PLANNING_STEPS[activeStep].icon} {PLANNING_STEPS[activeStep].label}
        </div>
      </div>
      <div className="planning-steps-list">
        {PLANNING_STEPS.map((step, i) => (
          <div
            key={step.id}
            className={`step-item ${i < activeStep ? "done" : i === activeStep ? "active" : ""}`}
          >
            <div className="step-dot" />
            <span>{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ChatWindow({ sessionId, phase, onNewTrip, onPlanReady, onPhaseChange }) {
  const [messages, setMessages]   = useState([{ role: "assistant", content: WELCOME }]);
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [planning, setPlanning]   = useState(false);
  const bottomRef                 = useRef(null);
  const textareaRef               = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, planning]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading || planning) return;

    setMessages(prev => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendMessage(sessionId, text);

      // If planning has started (phase transitions to "done"), show the overlay
      if (data.phase === "done" || data.trip_plan) {
        setLoading(false);
        setPlanning(true);

        // Show planning overlay for at least 2s so the animation is meaningful
        await new Promise(r => setTimeout(r, 2000));
        setPlanning(false);

        setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
        onPlanReady?.(data.trip_plan, data.phase);
        onPhaseChange?.(data.phase);
      } else {
        setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
        onPhaseChange?.(data.phase);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: `⚠️ Something went wrong: ${err.message}. Please try again.` },
      ]);
    } finally {
      setLoading(false);
      setPlanning(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleNewTrip() {
    clearSession(sessionId);
    setMessages([{ role: "assistant", content: WELCOME }]);
    setInput("");
    setLoading(false);
    setPlanning(false);
    onNewTrip?.();
  }

  const isDone   = phase === "done";
  const isActive = !loading && !planning && !isDone;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>

      {/* ── Header ── */}
      <div className="header">
        <div className="logo">
          <div className="logo-icon">🛣️</div>
          RoadWise
        </div>
        <div className="header-actions">
          {isDone && <span className="phase-badge">✓ Plan ready</span>}
          <button className="btn-ghost" onClick={handleNewTrip}>+ New Trip</button>
        </div>
      </div>

      {/* ── Messages / Planning overlay ── */}
      <div className="messages">
        {planning ? (
          <PlanningOverlay />
        ) : (
          <div className="messages-inner">
            {messages.map((msg, i) => (
              <MessageBubble key={i} role={msg.role} content={msg.content} />
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="typing-row">
                <div className="avatar">🛣️</div>
                <div className="typing-bubble">
                  <div className="dot" style={{ animationDelay: "0s" }} />
                  <div className="dot" style={{ animationDelay: "0.2s" }} />
                  <div className="dot" style={{ animationDelay: "0.4s" }} />
                </div>
              </div>
            )}

            {/* Done state */}
            {isDone && (
              <div className="done-banner">
                🎉 Your trip plan is ready! View it on the right →
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}

        {planning && <div ref={bottomRef} />}
      </div>

      {/* ── Input area ── */}
      {!isDone && !planning && (
        <div className="input-area">
          <div className="input-row">
            <textarea
              ref={textareaRef}
              className="input-box"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your answer…"
              rows={1}
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={loading || !input.trim()}
              title="Send (Enter)"
            >
              ➤
            </button>
          </div>
          <div className="input-hint">Enter to send · Shift+Enter for new line</div>
        </div>
      )}
    </div>
  );
}
