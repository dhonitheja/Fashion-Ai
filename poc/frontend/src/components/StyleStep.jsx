import { useState } from "react";

export default function StyleStep({ outfitDescription, outfitImageUrl, tryOnImageUrl, bodyProfile, onRestart }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggestions, setSuggestions] = useState(null);
  const [fetched, setFetched] = useState(false);

  // Derive skin tone and body type labels from bodyProfile
  const skinToneLabel = bodyProfile?.skin_tone?.label || "not specified";
  const bodyTypeLabel = bodyProfile?.bmi_label || "not specified";
  const heightCm      = bodyProfile?.height_cm;
  const weightKg      = bodyProfile?.weight_kg;
  const bmi           = bodyProfile?.bmi;

  async function fetchSuggestions() {
    setLoading(true);
    setError(null);

    try {
      const resp = await fetch(`${import.meta.env.VITE_API_URL}/api/style`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          outfit_description: outfitDescription,
          skin_tone: skinToneLabel,
          body_type: bodyTypeLabel,
          height_cm: heightCm,
          weight_kg: weightKg,
          bmi: bmi,
          gender: bodyProfile?.gender || "not specified",
          age: bodyProfile?.age || null,
          person_type: bodyProfile?.person_type || "adult",
        }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Style suggestions failed");
      }
      const data = await resp.json();
      setSuggestions(data.suggestions);
      setFetched(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="step-container">
      <h2>Styling Tips</h2>

      {/* Image + profile summary */}
      <div className="style-header">
        <img src={tryOnImageUrl || outfitImageUrl} alt="Outfit" className="style-thumb" />
        <div className="style-header-info">
          <strong>{outfitDescription}</strong>
          {bodyProfile && (
            <div className="style-profile-summary">
              <span className="profile-dot" style={{ background: bodyProfile.skin_tone.hex }} />
              {skinToneLabel} skin · {bodyTypeLabel}
              {heightCm && weightKg && (
                <span className="profile-measurements"> · {heightCm}cm / {weightKg}kg · BMI {bmi}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {!fetched && (
        <div className="personalize-section">
          <p className="step-desc">
            Your profile is ready. Get personalized styling tips based on your body type and skin tone.
          </p>
          <button
            className="btn-primary"
            onClick={fetchSuggestions}
            disabled={loading}
          >
            {loading ? (
              <span className="loading-text">
                <span className="spinner" /> Getting suggestions...
              </span>
            ) : (
              "Get Styling Tips ✨"
            )}
          </button>
        </div>
      )}

      {error && <div className="error-box">⚠️ {error}</div>}

      {suggestions && (
        <div className="suggestions">
          {/* Verdict */}
          <div className="verdict-card">
            <span className="verdict-icon">💬</span>
            <p>{suggestions.style_verdict}</p>
          </div>

          {/* Occasions */}
          <section className="suggestion-section">
            <h3>📅 Occasions</h3>
            <div className="tag-list">
              {suggestions.occasions?.map((o) => (
                <span key={o} className="tag">{o}</span>
              ))}
            </div>
          </section>

          {/* Accessories */}
          <section className="suggestion-section">
            <h3>👜 Accessories</h3>
            <div className="accessory-list">
              {suggestions.accessories?.map((a, i) => (
                <div key={i} className="accessory-card">
                  <div className="accessory-name">{a.item}</div>
                  <div className="accessory-color">Color: {a.color}</div>
                  <div className="accessory-why">{a.why}</div>
                </div>
              ))}
            </div>
          </section>

          {/* How to wear */}
          <section className="suggestion-section">
            <h3>💡 How to Wear It</h3>
            <ul className="tip-list">
              {suggestions.how_to_wear?.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </section>

          {/* Color palettes */}
          <section className="suggestion-section">
            <h3>🎨 Color Palettes</h3>
            <div className="palette-list">
              {suggestions.color_palettes?.map((p, i) => (
                <div key={i} className="palette-card">
                  <div className="palette-name">{p.name}</div>
                  <div className="palette-colors">
                    {p.colors?.map((c) => (
                      <span key={c} className="color-swatch" title={c}
                        style={{ background: c.startsWith("#") ? c : "var(--accent)" }}>
                        {c}
                      </span>
                    ))}
                  </div>
                  <div className="palette-mood">{p.mood}</div>
                </div>
              ))}
            </div>
          </section>

          <button className="btn-secondary" onClick={onRestart}>
            ← Start over with a new outfit
          </button>
        </div>
      )}
    </div>
  );
}
