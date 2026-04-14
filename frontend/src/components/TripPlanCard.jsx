import { useState } from "react";

function DayCard({ day }) {
  const [open, setOpen] = useState(true);

  const hasMeta = day.drive_miles > 0 || day.drive_hours > 0;

  return (
    <div className="day-card">
      {/* Clickable header */}
      <div className="day-header" onClick={() => setOpen(o => !o)}>
        <div className="day-number">{day.day}</div>
        <div className="day-title-group">
          <div className="day-city">{day.location || "Unknown stop"}</div>
          {hasMeta && (
            <div className="day-meta">
              {day.drive_miles > 0 && `${day.drive_miles} mi`}
              {day.drive_miles > 0 && day.drive_hours > 0 && " · "}
              {day.drive_hours > 0 && `${day.drive_hours}h drive`}
            </div>
          )}
        </div>
        <span className={`day-chevron ${open ? "open" : ""}`}>▾</span>
      </div>

      {/* Expandable body */}
      {open && (
        <div className="day-body">
          {day.gas_stop && (
            <>
              <div className="day-section-label">⛽ Gas Stop</div>
              <div className="tags">
                <span className="tag gas">⛽ {day.gas_stop}</span>
              </div>
            </>
          )}

          {day.lodging && (
            <>
              <div className="day-section-label">🏨 Where to Stay</div>
              <div className="tags">
                <span className="tag lodging">🏨 {day.lodging}</span>
              </div>
            </>
          )}

          {day.activities?.length > 0 && (
            <>
              <div className="day-section-label">📍 Activities</div>
              <div className="tags">
                {day.activities.map((a, i) => (
                  <span key={i} className="tag activity">📍 {a}</span>
                ))}
              </div>
            </>
          )}

          {day.restaurants?.length > 0 && (
            <>
              <div className="day-section-label">🍽️ Food</div>
              <div className="tags">
                {day.restaurants.map((r, i) => (
                  <span key={i} className="tag restaurant">🍽️ {r}</span>
                ))}
              </div>
            </>
          )}

          {day.weather_note && (
            <div className="weather-note">
              🌤️ <span>{day.weather_note}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TripPlanCard({ plan, onNewTrip }) {
  if (!plan) return null;

  const mapsUrl = `https://www.google.com/maps/dir/${encodeURIComponent(plan.origin)}/${encodeURIComponent(plan.destination)}`;

  return (
    <div className="plan-container">

      {/* ── Hero ── */}
      <div className="plan-hero">
        <div className="plan-route">
          <span className="route-city">{plan.origin}</span>
          <span className="route-arrow">→</span>
          <span className="route-city">{plan.destination}</span>
        </div>
        {plan.travel_dates && (
          <div className="plan-dates">📅 {plan.travel_dates}</div>
        )}
      </div>

      {/* ── Stats ── */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Distance</div>
          <div className="stat-value">{plan.total_miles?.toLocaleString() || 0} <span style={{fontSize:"0.7rem",fontWeight:400,color:"var(--text-muted)"}}>mi</span></div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Drive Time</div>
          <div className="stat-value">{plan.total_drive_hours || 0} <span style={{fontSize:"0.7rem",fontWeight:400,color:"var(--text-muted)"}}>hrs</span></div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Est. Fuel Cost</div>
          <div className="stat-value">${plan.gas_summary?.estimated_fuel_cost || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Gas Stops</div>
          <div className="stat-value">{plan.gas_summary?.num_stops ?? 0}</div>
        </div>
      </div>

      {/* ── Gas summary ── */}
      {plan.gas_summary?.stops_description && (
        <div className="gas-banner">
          <span className="gas-icon">⛽</span>
          <span>{plan.gas_summary.stops_description}</span>
        </div>
      )}

      {/* ── Day-by-day ── */}
      <div className="section-header">
        <span>📅</span> Day-by-Day Itinerary
      </div>
      <div className="day-cards">
        {plan.days?.map(day => <DayCard key={day.day} day={day} />)}
      </div>

      {/* ── Tips ── */}
      {plan.tips?.length > 0 && (
        <>
          <div className="section-header" style={{marginTop: 28}}>
            <span>💡</span> Road Trip Tips
          </div>
          <div className="tips-list">
            {plan.tips.map((tip, i) => (
              <div key={i} className="tip-item">
                <div className="tip-bullet" />
                <span>{tip}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ── Actions ── */}
      <div className="plan-actions">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="maps-btn"
        >
          🗺️ Open in Google Maps
        </a>
        <button className="btn-ghost" onClick={onNewTrip} style={{padding: "10px 18px"}}>
          + Plan Another Trip
        </button>
      </div>

    </div>
  );
}
