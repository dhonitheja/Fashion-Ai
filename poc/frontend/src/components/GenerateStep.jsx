import { useState } from "react";

const EXAMPLE_PROMPTS = [
  "Flowy sage green midi dress for a beach vacation",
  "Sleek black power suit for a job interview",
  "Cozy oversized camel coat for autumn in the city",
  "Vibrant floral sundress for a garden wedding",
];

export default function GenerateStep({ onComplete, onSkip, bodyProfile }) {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleGenerate() {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    // Build description with body context (but gender/person_type sent separately as hard constraints)
    let enrichedDescription = description;
    if (bodyProfile) {
      enrichedDescription += `. ${bodyProfile.bmi_label} build, ${bodyProfile.skin_tone.label} skin tone`;
      if (bodyProfile.height_cm) enrichedDescription += `, ${bodyProfile.height_cm}cm`;
    }

    try {
      const resp = await fetch(`${import.meta.env.VITE_API_URL}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: enrichedDescription,
          gender: bodyProfile?.gender || "unisex",
          person_type: bodyProfile?.person_type || "adult",
          age: bodyProfile?.age || null,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Generation failed");
      }
      const data = await resp.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="step-container">
      <h2>Describe your outfit</h2>
      <p className="step-desc">
        Tell us what you want to wear — in any language (English, తెలుగు, हिन्दी, മലയാളം, ଓଡ଼ିଆ, 中文, Русский &amp; more).
      </p>

      {bodyProfile && (
        <div className="profile-summary-banner">
          <div className="profile-summary-swatch" style={{ background: bodyProfile.skin_tone.hex }} />
          <span>
            <strong>{bodyProfile.skin_tone.label}</strong> skin ·{" "}
            <strong>{bodyProfile.bmi_label}</strong> ·{" "}
            {bodyProfile.height_cm} cm / {bodyProfile.weight_kg} kg · BMI {bodyProfile.bmi}
          </span>
        </div>
      )}

      <div className="examples">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            className="example-chip"
            onClick={() => setDescription(p)}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="input-group">
        <textarea
          className="prompt-input"
          rows={3}
          placeholder="e.g. A flowy white linen dress... or నీలి రంగు చీర... or नीली साड़ी... or 蓝色连衣裙..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={loading}
        />
        <button
          className="btn-primary"
          onClick={handleGenerate}
          disabled={loading || !description.trim()}
        >
          {loading ? (
            <span className="loading-text">
              <span className="spinner" /> Generating... (~25s)
            </span>
          ) : (
            "Generate Outfit ✨"
          )}
        </button>
      </div>

      {error && <div className="error-box">⚠️ {error}</div>}

      {!result && (
        <button className="btn-ghost" onClick={onSkip} style={{ marginTop: 12 }}>
          Skip → Try a product link instead
        </button>
      )}

      {result && (
        <div className="result-card">
          <img
            src={result.image_url}
            alt="Generated outfit"
            className="outfit-image"
          />
          <div className="result-meta">
            <p className="prompt-badge">
              <strong>SD prompt:</strong> {result.enriched_prompt}
            </p>
            <p className="prompt-badge" style={{ marginTop: 6 }}>
              <strong>Negative:</strong> {result.negative_prompt}
            </p>
            <button
              className="btn-primary"
              onClick={() => onComplete(result)}
            >
              Try this on →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
