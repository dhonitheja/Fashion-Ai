import { useState } from "react";
import BodyProfileStep from "./components/BodyProfileStep";
import GenerateStep from "./components/GenerateStep";
import TryOnStep from "./components/TryOnStep";
import StyleStep from "./components/StyleStep";
import "./App.css";

const STEPS = ["Body Profile", "Generate Outfit", "Virtual Try-On", "Styling Tips"];

export default function App() {
  const [step, setStep] = useState(0);
  const [bodyProfile, setBodyProfile] = useState(null);
  const [generatedOutfit, setGeneratedOutfit] = useState(null);
  const [tryOnResult, setTryOnResult] = useState(null);

  function restart() {
    setBodyProfile(null);
    setGeneratedOutfit(null);
    setTryOnResult(null);
    setStep(0);
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Sahion</h1>
        <p className="tagline">AI Fashion Stylist</p>
      </header>

      <nav className="stepper">
        {STEPS.map((label, i) => (
          <button
            key={i}
            className={`step-btn ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}
            onClick={() => i <= step && setStep(i)}
            disabled={i > step}
          >
            <span className="step-num">{i < step ? "✓" : i + 1}</span>
            {label}
          </button>
        ))}
      </nav>

      <main className="content">
        {step === 0 && (
          <BodyProfileStep
            onComplete={(profile) => {
              setBodyProfile(profile);
              setStep(1);
            }}
          />
        )}
        {step === 1 && (
          <GenerateStep
            bodyProfile={bodyProfile}
            onComplete={(outfit) => {
              setGeneratedOutfit(outfit);
              setStep(2);
            }}
            onSkip={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <TryOnStep
            outfitImageUrl={generatedOutfit?.image_url}
            outfitDescription={generatedOutfit?.original_description}
            bodyProfile={bodyProfile}
            onComplete={(result) => {
              setTryOnResult(result);
              setStep(3);
            }}
            onSkip={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <StyleStep
            outfitDescription={generatedOutfit?.original_description}
            outfitImageUrl={generatedOutfit?.image_url}
            tryOnImageUrl={tryOnResult?.result_url}
            bodyProfile={bodyProfile}
            onRestart={restart}
          />
        )}
      </main>
    </div>
  );
}
