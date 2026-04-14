import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatWindow from "./components/ChatWindow";
import TripPlanCard from "./components/TripPlanCard";

export default function App() {
  const [sessionId, setSessionId] = useState(() => uuidv4());
  const [tripPlan, setTripPlan]   = useState(null);
  const [phase, setPhase]         = useState("intake");

  function handleNewTrip() {
    setSessionId(uuidv4());
    setTripPlan(null);
    setPhase("intake");
  }

  const hasPlan = !!tripPlan;

  return (
    <div className="app">
      {/* Left — chat panel (full width until plan appears, then narrows) */}
      <div className={`chat-panel ${hasPlan ? "split" : "full"}`}>
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

      {/* Right — trip plan panel (slides in when plan is ready) */}
      {hasPlan && (
        <div className="plan-panel">
          <TripPlanCard plan={tripPlan} onNewTrip={handleNewTrip} />
        </div>
      )}
    </div>
  );
}
