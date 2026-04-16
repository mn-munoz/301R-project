import { useState } from "react";

// ── Star rating renderer ─────────────────────────────────────────────────────
function Stars({ rating }) {
  if (!rating) return null;
  const full  = Math.floor(rating);
  const half  = rating % 1 >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <span style={{ color: "#f59e0b", fontSize: "0.75rem", letterSpacing: "0.5px" }}>
      {"★".repeat(full)}
      {half ? "½" : ""}
      {"☆".repeat(empty)}
      <span style={{ color: "var(--text-muted)", marginLeft: 4, fontSize: "0.72rem" }}>
        {rating.toFixed(1)}
      </span>
    </span>
  );
}

// ── Single place card ────────────────────────────────────────────────────────
function PlaceCard({ place, accent = "var(--accent)" }) {
  if (!place || !place.name) return null;

  const isFallback = place.name.toLowerCase().includes("search locally");

  return (
    <div className="place-card" style={{ borderLeftColor: accent }}>
      <div className="place-card-top">
        <span className="place-name">{place.name}</span>
        {place.price_level && (
          <span className="place-price" style={{ color: accent }}>{place.price_level}</span>
        )}
      </div>

      {!isFallback && (
        <>
          {place.rating && <Stars rating={place.rating} />}
          {place.address && (
            <div className="place-address">📍 {place.address}</div>
          )}
          {place.maps_url && (
            <a
              href={place.maps_url}
              target="_blank"
              rel="noopener noreferrer"
              className="place-link"
            >
              View on Google Maps →
            </a>
          )}
        </>
      )}
    </div>
  );
}

// ── Collapsible day card ─────────────────────────────────────────────────────
function DayCard({ day }) {
  const [open, setOpen] = useState(true);
  const hasDrive = day.drive_miles > 0 || day.drive_hours > 0;

  return (
    <div className="day-card">
      <div className="day-header" onClick={() => setOpen(o => !o)}>
        <div className="day-number">{day.day}</div>
        <div className="day-title-group">
          <div className="day-city">{day.location || "Unknown stop"}</div>
          {hasDrive && (
            <div className="day-meta">
              {day.drive_miles > 0 && `${day.drive_miles} mi`}
              {day.drive_miles > 0 && day.drive_hours > 0 && " · "}
              {day.drive_hours > 0 && `${day.drive_hours}h drive`}
            </div>
          )}
        </div>
        <span className={`day-chevron ${open ? "open" : ""}`}>▾</span>
      </div>

      {open && (
        <div className="day-body">

          {/* Gas stop */}
          {day.gas_stop && (
            <div className="day-section">
              <div className="day-section-label">⛽ Gas Stop</div>
              <div className="tags">
                <span className="tag gas">⛽ {day.gas_stop}</span>
              </div>
            </div>
          )}

          {/* Lodging */}
          {day.lodging && (
            <div className="day-section">
              <div className="day-section-label">🏨 Where to Stay</div>
              <PlaceCard place={day.lodging} accent="var(--accent)" />
            </div>
          )}

          {/* Activities */}
          {day.activities?.length > 0 && (
            <div className="day-section">
              <div className="day-section-label">📍 Things to Do</div>
              <div className="place-list">
                {day.activities.map((a, i) => (
                  <PlaceCard key={i} place={a} accent="var(--green)" />
                ))}
              </div>
            </div>
          )}

          {/* Restaurants */}
          {day.restaurants?.length > 0 && (
            <div className="day-section">
              <div className="day-section-label">🍽️ Where to Eat</div>
              <div className="place-list">
                {day.restaurants.map((r, i) => (
                  <PlaceCard key={i} place={r} accent="var(--pink)" />
                ))}
              </div>
            </div>
          )}

          {/* Weather */}
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

// ── Main plan card ───────────────────────────────────────────────────────────
export default function TripPlanCard({ plan, onNewTrip }) {
  if (!plan) return null;

  const mapsUrl = `https://www.google.com/maps/dir/${encodeURIComponent(plan.origin)}/${encodeURIComponent(plan.destination)}`;

  return (
    <div className="plan-container">

      {/* Hero */}
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

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Distance</div>
          <div className="stat-value">
            {plan.total_miles?.toLocaleString() || 0}
            <span style={{ fontSize: "0.7rem", fontWeight: 400, color: "var(--text-muted)" }}> mi</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Drive Time</div>
          <div className="stat-value">
            {plan.total_drive_hours || 0}
            <span style={{ fontSize: "0.7rem", fontWeight: 400, color: "var(--text-muted)" }}> hrs</span>
          </div>
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

      {/* Gas banner */}
      {plan.gas_summary?.stops_description && (
        <div className="gas-banner">
          <span className="gas-icon">⛽</span>
          <span>{plan.gas_summary.stops_description}</span>
        </div>
      )}

      {/* Itinerary */}
      <div className="section-header"><span>📅</span> Day-by-Day Itinerary</div>
      <div className="day-cards">
        {plan.days?.map(day => <DayCard key={day.day} day={day} />)}
      </div>

      {/* Tips */}
      {plan.tips?.length > 0 && (
        <>
          <div className="section-header" style={{ marginTop: 28 }}>
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

      {/* Actions */}
      <div className="plan-actions">
        <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className="maps-btn">
          🗺️ Open Route in Google Maps
        </a>
        <button className="btn-ghost" onClick={onNewTrip} style={{ padding: "10px 18px" }}>
          + Plan Another Trip
        </button>
      </div>

    </div>
  );
}
