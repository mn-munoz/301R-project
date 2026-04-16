import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatWindow from "./components/ChatWindow";
import TripPlanCard from "./components/TripPlanCard";

export default function App() {
  const [sessionId, setSessionId]       = useState(() => uuidv4());
  const [tripPlan, setTripPlan]         = useState(null);
  const [phase, setPhase]               = useState("intake");
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const [planCollapsed, setPlanCollapsed] = useState(false);

  function handleNewTrip() {
    setSessionId(uuidv4());
    setTripPlan(null);
    setPhase("intake");
    setChatCollapsed(false);
    setPlanCollapsed(false);
  }

  function toggleChat() {
    setChatCollapsed(c => {
      const next = !c;
      // If expanding chat and plan was also collapsed, un-collapse plan too
      if (!next) setPlanCollapsed(false);
      return next;
    });
  }

  function togglePlan() {
    setPlanCollapsed(p => {
      const next = !p;
      if (!next) setChatCollapsed(false);
      return next;
    });
  }

  const hasPlan = !!tripPlan;

  // CSS class helpers — "collapsed" and "expanded" only matter in the
  // stacked (≤768px) media query; desktop ignores them.
  const chatClass = [
    "chat-panel",
    hasPlan ? "split" : "full",
    chatCollapsed ? "collapsed" : "",
    planCollapsed ? "expanded" : "",
  ].filter(Boolean).join(" ");

  const planClass = [
    "plan-panel",
    planCollapsed ? "collapsed" : "",
    chatCollapsed ? "expanded" : "",
  ].filter(Boolean).join(" ");

  return (
    <div className="app">
      {/* ── Chat panel ───────────────────────────────────────────────── */}
      <div className={chatClass}>
        {/* Collapse toggle — only rendered/visible in stacked layout */}
        {hasPlan && (
          <button className="panel-toggle" onClick={toggleChat} aria-label="Toggle chat">
            <span className="panel-toggle-label">💬 Chat</span>
            <span className={`panel-toggle-chevron ${chatCollapsed ? "closed" : "open"}`}>▾</span>
          </button>
        )}
        <div className="panel-content">
          <ChatWindow
            sessionId={sessionId}
            phase={phase}
            onNewTrip={handleNewTrip}
            onPlanReady={(plan, newPhase) => {
              setTripPlan(plan);
              setPhase(newPhase);
            }}
            onPhaseChange={setPhase}
          />
        </div>
      </div>

      {/* ── Plan panel ───────────────────────────────────────────────── */}
      {hasPlan && (
        <div className={planClass}>
          <button className="panel-toggle" onClick={togglePlan} aria-label="Toggle trip plan">
            <span className="panel-toggle-label">🗺️ Trip Plan</span>
            <span className={`panel-toggle-chevron ${planCollapsed ? "closed" : "open"}`}>▾</span>
          </button>
          <div className="panel-content">
            <TripPlanCard plan={tripPlan} onNewTrip={handleNewTrip} />
          </div>
        </div>
      )}
    </div>
  );
}
