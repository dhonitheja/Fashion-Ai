import { useState, useEffect } from "react";

const SKIN_TONES = [
  { id: "I",   label: "Very Light",  hex: "#FDDBB4", fitzpatrick: "Type I"   },
  { id: "II",  label: "Light",       hex: "#F5C89A", fitzpatrick: "Type II"  },
  { id: "III", label: "Medium",      hex: "#D4956A", fitzpatrick: "Type III" },
  { id: "IV",  label: "Olive",       hex: "#B87040", fitzpatrick: "Type IV"  },
  { id: "V",   label: "Brown",       hex: "#8B4513", fitzpatrick: "Type V"   },
  { id: "VI",  label: "Deep",        hex: "#4A2508", fitzpatrick: "Type VI"  },
];

// BMI categories differ for kids vs adults
function getBMICategory(bmi, isKid, age) {
  if (isKid) {
    // Simplified pediatric ranges (age-adjusted in real apps, this is approximate)
    if (age <= 5)  return bmi < 14 ? slim() : bmi < 18 ? fit() : bmi < 20 ? average() : heavy();
    if (age <= 10) return bmi < 15 ? slim() : bmi < 20 ? fit() : bmi < 23 ? average() : heavy();
    return           bmi < 16 ? slim() : bmi < 22 ? fit() : bmi < 26 ? average() : heavy();
  }
  if (bmi < 18.5) return slim();
  if (bmi < 25)   return fit();
  if (bmi < 30)   return average();
  return heavy();
}

const slim    = () => ({ label: "Slim",      key: "slim",    color: "#5b9bd5" });
const fit     = () => ({ label: "Fit",        key: "fit",     color: "#5ca87a" });
const average = () => ({ label: "Chubby",     key: "average", color: "#c9a84c" });
const heavy   = () => ({ label: "Heavy",      key: "heavy",   color: "#e05c5c" });

// SVG silhouette — adapts to gender + body category
function BodySilhouette({ category, skinHex, gender, isKid }) {
  const tone = skinHex || "#D4956A";
  const scale = isKid ? 0.72 : 1;

  // Body path variants
  const bodies = {
    slim: {
      male:   "M 50 32 C 40 32,33 40,33 52 L 31 97 L 36 97 L 38 72 L 44 72 L 44 122 L 41 142 L 46 142 L 50 127 L 54 142 L 59 142 L 56 122 L 56 72 L 62 72 L 64 97 L 69 97 L 67 52 C 67 40,60 32,50 32Z",
      female: "M 50 32 C 40 32,33 40,33 52 L 30 97 L 35 97 L 37 72 L 41 72 L 39 122 L 36 142 L 42 142 L 50 127 L 58 142 L 64 142 L 61 122 L 59 72 L 63 72 L 65 97 L 70 97 L 67 52 C 67 40,60 32,50 32Z",
    },
    fit: {
      male:   "M 50 32 C 37 32,27 40,27 54 L 25 97 L 32 97 L 34 72 L 40 72 L 40 122 L 37 142 L 43 142 L 50 128 L 57 142 L 63 142 L 60 122 L 60 72 L 66 72 L 68 97 L 75 97 L 73 54 C 73 40,63 32,50 32Z",
      female: "M 50 32 C 38 32,28 40,28 54 L 26 97 L 32 97 L 34 72 L 39 72 L 37 122 L 33 142 L 41 142 L 50 128 L 59 142 L 67 142 L 63 122 L 61 72 L 66 72 L 68 97 L 74 97 L 72 54 C 72 40,62 32,50 32Z",
    },
    average: {
      male:   "M 50 32 C 34 32,22 42,21 57 L 19 97 L 28 99 L 31 74 L 37 74 L 37 122 L 33 144 L 41 144 L 50 130 L 59 144 L 67 144 L 63 122 L 63 74 L 69 74 L 72 99 L 81 97 L 79 57 C 78 42,66 32,50 32Z",
      female: "M 50 32 C 35 32,22 42,21 57 L 18 97 L 27 99 L 30 74 L 36 74 L 33 122 L 28 144 L 38 144 L 50 130 L 62 144 L 72 144 L 67 122 L 64 74 L 70 74 L 73 99 L 82 97 L 79 57 C 78 42,65 32,50 32Z",
    },
    heavy: {
      male:   "M 50 32 C 30 32,16 44,15 60 L 13 97 L 24 100 L 28 75 L 35 77 L 33 122 L 27 146 L 39 146 L 50 132 L 61 146 L 73 146 L 67 122 L 65 77 L 72 75 L 76 100 L 87 97 L 85 60 C 84 44,70 32,50 32Z",
      female: "M 50 32 C 31 32,16 44,15 60 L 12 97 L 23 100 L 27 75 L 34 77 L 30 122 L 24 146 L 38 146 L 50 132 L 62 146 L 76 146 L 70 122 L 66 77 L 73 75 L 77 100 L 88 97 L 85 60 C 84 44,69 32,50 32Z",
    },
  };

  const gKey = gender === "female" ? "female" : "male";
  const bodyPath = bodies[category]?.[gKey] || bodies.fit.male;

  // Female: longer hair; Male: short hair; Kid: round big head
  const headR = isKid ? 15 : 13;
  const headY = isKid ? 16 : 18;

  return (
    <svg
      viewBox="0 0 100 160"
      width={120 * scale}
      height={180 * scale}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Hair */}
      {gender === "female" ? (
        <>
          <ellipse cx="50" cy={headY - 4} rx={headR + 1} ry={headR * 0.55} fill="#3a2a1a" />
          <ellipse cx="35" cy={headY + 8} rx="5" ry="14" fill="#3a2a1a" />
          <ellipse cx="65" cy={headY + 8} rx="5" ry="14" fill="#3a2a1a" />
        </>
      ) : (
        <ellipse cx="50" cy={headY - 6} rx={headR} ry={headR * 0.45} fill="#2a1a0a" />
      )}
      {/* Head */}
      <circle cx="50" cy={headY} r={headR} fill={tone} stroke="rgba(0,0,0,0.12)" strokeWidth="0.5" />
      {/* Neck */}
      <rect x="46" y={headY + headR - 1} width="8" height="6" fill={tone} />
      {/* Body */}
      <path d={bodyPath} fill={tone} stroke="rgba(0,0,0,0.12)" strokeWidth="0.5" />
      {/* Female: skirt hint at hips */}
      {gender === "female" && category !== "slim" && (
        <ellipse cx="50" cy="128" rx="18" ry="5" fill={tone} opacity="0.4" />
      )}
    </svg>
  );
}

export default function BodyProfileStep({ onComplete }) {
  const [personType, setPersonType] = useState("adult"); // "adult" | "kid"
  const [gender, setGender]         = useState("male");  // "male" | "female"
  const [age, setAge]               = useState("");
  const [height, setHeight]         = useState("");
  const [weight, setWeight]         = useState("");
  const [skinTone, setSkinTone]     = useState(SKIN_TONES[2]);
  const [bmi, setBmi]               = useState(null);
  const [bmiCategory, setBmiCategory] = useState(null);

  const [heightUnit, setHeightUnit] = useState("cm");
  const [weightUnit, setWeightUnit] = useState("kg");
  const [heightFt, setHeightFt]     = useState("");
  const [heightIn, setHeightIn]     = useState("");

  const isKid = personType === "kid";

  // Height/weight placeholder hints change by type
  const heightHint = isKid ? "110" : "170";
  const weightHint = isKid ? "20"  : "65";
  const heightMin  = isKid ? 60    : 100;
  const heightMax  = isKid ? 160   : 250;
  const weightMin  = isKid ? 10    : 30;
  const weightMax  = isKid ? 80    : 300;
  const ageMin     = isKid ? 2     : 18;
  const ageMax     = isKid ? 17    : 100;

  // Reset height/weight when switching type so stale values don't produce wrong BMI
  useEffect(() => {
    setHeight("");
    setWeight("");
    setHeightFt("");
    setHeightIn("");
    setAge("");
    setBmi(null);
    setBmiCategory(null);
  }, [personType]);

  useEffect(() => {
    let h_cm = heightUnit === "cm" ? parseFloat(height) : ((parseFloat(heightFt) || 0) * 12 + (parseFloat(heightIn) || 0)) * 2.54;
    let w_kg = weightUnit === "kg" ? parseFloat(weight) : (parseFloat(weight) || 0) * 0.453592;
    
    const h = h_cm / 100;
    const w = w_kg;
    const a = parseFloat(age) || (isKid ? 10 : 30);
    if (h > 0 && w > 0) {
      const calc = w / (h * h);
      setBmi(calc.toFixed(1));
      setBmiCategory(getBMICategory(calc, isKid, a));
    } else {
      setBmi(null);
      setBmiCategory(null);
    }
  }, [height, heightFt, heightIn, weight, age, isKid, heightUnit, weightUnit]);

  const canContinue = (heightUnit === "cm" ? parseFloat(height) > 0 : parseFloat(heightFt) > 0) && parseFloat(weight) > 0;

  function handleContinue() {
    let h_cm = heightUnit === "cm" ? parseFloat(height) : ((parseFloat(heightFt) || 0) * 12 + (parseFloat(heightIn) || 0)) * 2.54;
    let w_kg = weightUnit === "kg" ? parseFloat(weight) : (parseFloat(weight) || 0) * 0.453592;
    
    onComplete({
      person_type:  personType,
      gender,
      age:          age ? parseInt(age) : null,
      height_cm:    Math.round(h_cm),
      weight_kg:    Math.round(w_kg),
      bmi:          bmi ? parseFloat(bmi) : null,
      bmi_category: bmiCategory?.key,
      bmi_label:    bmiCategory?.label,
      skin_tone:    skinTone,
    });
  }

  const fitTip = {
    slim:    isKid ? "Light, layered clothing works well." : "Structured, layered looks add visual fullness.",
    fit:     isKid ? "Most kids styles will look great!"   : "Most silhouettes work beautifully.",
    average: isKid ? "Relaxed cuts are comfortable."       : "A-line and flowy styles are very flattering.",
    heavy:   isKid ? "Comfortable, relaxed fits."           : "Empire waists and vertical patterns slim the look.",
  };

  return (
    <div className="step-container">
      <h2>Your Profile</h2>
      <p className="step-desc">
        Helps us generate outfits and suggestions tailored to you.
      </p>

      {/* ── ADULT / KID TOGGLE ── */}
      <div className="toggle-row">
        <label className="field-label">Who is this for?</label>
        <div className="toggle-group">
          {["adult", "kid"].map((t) => (
            <button
              key={t}
              className={`toggle-btn ${personType === t ? "active" : ""}`}
              onClick={() => setPersonType(t)}
            >
              {t === "adult" ? "👤 Adult" : "🧒 Kid / Teen"}
            </button>
          ))}
        </div>
      </div>

      {/* ── GENDER ── */}
      <div className="toggle-row">
        <label className="field-label">Gender</label>
        <div className="toggle-group">
          {[
            { key: "male",   label: "♂ Male"   },
            { key: "female", label: "♀ Female" },
            { key: "unisex", label: "⊕ Unisex" },
          ].map((g) => (
            <button
              key={g.key}
              className={`toggle-btn ${gender === g.key ? "active" : ""}`}
              onClick={() => setGender(g.key)}
            >
              {g.label}
            </button>
          ))}
        </div>
      </div>

      <div className="profile-layout">
        {/* ── LEFT: inputs ── */}
        <div className="profile-form">

          {/* Age */}
          <div className="field-group">
            <label className="field-label">Age</label>
            <div className="input-with-unit">
              <input
                type="number"
                className="number-input"
                placeholder={isKid ? "8" : "25"}
                min={ageMin}
                max={ageMax}
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
              <span className="unit">yrs</span>
            </div>
            {isKid && <p className="field-hint">Age 2–17</p>}
          </div>

          {/* Height */}
          <div className="field-group">
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
              <label className="field-label">Height</label>
              <div className="toggle-group" style={{gap: '4px'}}>
                <button className={`toggle-btn ${heightUnit === "cm" ? "active" : ""}`} style={{padding:'2px 8px', fontSize:'0.7rem'}} onClick={() => {setHeightUnit("cm"); setHeight("");}}>cm</button>
                <button className={`toggle-btn ${heightUnit === "ft" ? "active" : ""}`} style={{padding:'2px 8px', fontSize:'0.7rem'}} onClick={() => {setHeightUnit("ft"); setHeightFt(""); setHeightIn("");}}>ft/in</button>
              </div>
            </div>
            {heightUnit === "cm" ? (
              <div className="input-with-unit">
                <input type="number" className="number-input" placeholder={heightHint} min={heightMin} max={heightMax} value={height} onChange={(e) => setHeight(e.target.value)} />
                <span className="unit">cm</span>
              </div>
            ) : (
             <div className="input-with-unit">
                <input type="number" className="number-input" style={{width:'70px'}} placeholder={isKid ? "3" : "5"} min="1" max="8" value={heightFt} onChange={(e) => setHeightFt(e.target.value)} />
                <span className="unit" style={{marginRight:'8px'}}>ft</span>
                <input type="number" className="number-input" style={{width:'70px'}} placeholder="8" min="0" max="11" value={heightIn} onChange={(e) => setHeightIn(e.target.value)} />
                <span className="unit">in</span>
              </div>
            )}
          </div>

          {/* Weight */}
          <div className="field-group">
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
              <label className="field-label">Weight</label>
              <div className="toggle-group" style={{gap: '4px'}}>
                <button className={`toggle-btn ${weightUnit === "kg" ? "active" : ""}`} style={{padding:'2px 8px', fontSize:'0.7rem'}} onClick={() => {setWeightUnit("kg"); setWeight("");}}>kg</button>
                <button className={`toggle-btn ${weightUnit === "lbs" ? "active" : ""}`} style={{padding:'2px 8px', fontSize:'0.7rem'}} onClick={() => {setWeightUnit("lbs"); setWeight("");}}>lbs</button>
              </div>
            </div>
            <div className="input-with-unit">
              <input
                type="number"
                className="number-input"
                placeholder={weightUnit === "kg" ? weightHint : (isKid ? "45" : "145")}
                min={weightUnit === "kg" ? weightMin : Math.round(weightMin * 2.2)}
                max={weightUnit === "kg" ? weightMax : Math.round(weightMax * 2.2)}
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
              />
              <span className="unit">{weightUnit}</span>
            </div>
          </div>

          {/* Skin tone */}
          <div className="field-group">
            <label className="field-label">Skin Tone</label>
            <div className="skin-tone-picker">
              {SKIN_TONES.map((tone) => (
                <button
                  key={tone.id}
                  className={`skin-swatch ${skinTone.id === tone.id ? "selected" : ""}`}
                  style={{ background: tone.hex }}
                  onClick={() => setSkinTone(tone)}
                  title={tone.label}
                />
              ))}
            </div>
            <p className="selected-tone-label">
              {skinTone.label} <span className="tone-type">({skinTone.fitzpatrick})</span>
            </p>
          </div>
        </div>

        {/* ── RIGHT: live visualization ── */}
        <div className="profile-preview">
          <div className="silhouette-card">
            <BodySilhouette
              category={bmiCategory?.key || "fit"}
              skinHex={skinTone.hex}
              gender={gender}
              isKid={isKid}
            />
            {bmiCategory ? (
              <>
                <div className="bmi-badge" style={{ borderColor: bmiCategory.color, color: bmiCategory.color }}>
                  {bmiCategory.label}
                </div>
                <div className="bmi-number">BMI {bmi}</div>
                <div className="bmi-detail">{fitTip[bmiCategory.key]}</div>
              </>
            ) : (
              <div className="bmi-placeholder">Enter height & weight</div>
            )}

            {/* Profile summary chips */}
            <div className="silhouette-tags">
              <span className="sil-tag">{gender}</span>
              <span className="sil-tag">{isKid ? "kid" : "adult"}</span>
              {age && <span className="sil-tag">{age} yrs</span>}
            </div>
          </div>

          {/* Color suggestions */}
          <div className="color-hint-card">
            <p className="color-hint-title">Best colors for {skinTone.label} skin</p>
            <div className="color-hint-swatches">
              {getColorSuggestions(skinTone.id).map((c) => (
                <div key={c.hex} className="hint-swatch" style={{ background: c.hex }} title={c.name}>
                  <span>{c.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <button
        className="btn-primary"
        onClick={handleContinue}
        disabled={!canContinue}
        style={{ marginTop: 28 }}
      >
        Continue with this profile →
      </button>
    </div>
  );
}

function getColorSuggestions(toneId) {
  const map = {
    I:   [
      { hex: "#8B1A1A", name: "Deep Red"     },
      { hex: "#1A3A5C", name: "Navy"         },
      { hex: "#2D6A4F", name: "Forest Green" },
      { hex: "#4A235A", name: "Plum"         },
      { hex: "#8B6914", name: "Warm Gold"    },
    ],
    II:  [
      { hex: "#C0392B", name: "Red"          },
      { hex: "#2E86AB", name: "Sky Blue"     },
      { hex: "#1D6A40", name: "Emerald"      },
      { hex: "#8E44AD", name: "Purple"       },
      { hex: "#D4AC0D", name: "Yellow"       },
    ],
    III: [
      { hex: "#E74C3C", name: "Coral Red"    },
      { hex: "#2980B9", name: "Ocean Blue"   },
      { hex: "#27AE60", name: "Sage Green"   },
      { hex: "#D35400", name: "Burnt Orange" },
      { hex: "#F0E68C", name: "Ivory"        },
    ],
    IV:  [
      { hex: "#FF6B35", name: "Orange"       },
      { hex: "#F7DC6F", name: "Golden"       },
      { hex: "#1ABC9C", name: "Teal"         },
      { hex: "#E91E63", name: "Hot Pink"     },
      { hex: "#FFFFFF", name: "White"        },
    ],
    V:   [
      { hex: "#FF8C00", name: "Deep Orange"  },
      { hex: "#FFD700", name: "Gold"         },
      { hex: "#00CED1", name: "Turquoise"    },
      { hex: "#FF1493", name: "Magenta"      },
      { hex: "#F5F5DC", name: "Cream"        },
    ],
    VI:  [
      { hex: "#FF4500", name: "Red-Orange"   },
      { hex: "#FFD700", name: "Bright Gold"  },
      { hex: "#00FF7F", name: "Lime Green"   },
      { hex: "#FF69B4", name: "Pink"         },
      { hex: "#FFFFFF", name: "White"        },
    ],
  };
  return map[toneId] || map["III"];
}
