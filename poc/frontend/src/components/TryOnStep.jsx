import { useState, useRef } from "react";

export default function TryOnStep({ outfitImageUrl, outfitDescription, bodyProfile, onComplete, onSkip }) {
  // Outfit source: "generated" (from step 1) or "url" (pasted link)
  const [outfitSource, setOutfitSource]       = useState(outfitImageUrl ? "generated" : "url");
  const [productUrl, setProductUrl]           = useState("");
  const [fetchedProduct, setFetchedProduct]   = useState(null); // { image_url, product_name }
  const [fetchingProduct, setFetchingProduct] = useState(false);
  const [fetchError, setFetchError]           = useState(null);

  const [photo, setPhoto]           = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [result, setResult]         = useState(null);
  const fileRef = useRef();

  // Which outfit image to actually use for try-on
  const activeOutfitUrl = outfitSource === "url"
    ? fetchedProduct?.image_url
    : outfitImageUrl;

  const activeOutfitName = outfitSource === "url"
    ? fetchedProduct?.product_name
    : outfitDescription;

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  }

  async function handleFetchProduct() {
    if (!productUrl.trim()) return;
    setFetchingProduct(true);
    setFetchError(null);
    setFetchedProduct(null);

    try {
      const resp = await fetch(`${import.meta.env.VITE_API_URL}/api/fetch-product`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: productUrl.trim() }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Could not fetch product");
      }
      const data = await resp.json();
      setFetchedProduct(data);
    } catch (e) {
      setFetchError(e.message);
    } finally {
      setFetchingProduct(false);
    }
  }

  async function handleTryOn() {
    if (!photo || !activeOutfitUrl) return;
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("person_photo", photo);

      const resp = await fetch(
        `${import.meta.env.VITE_API_URL}/api/tryon?outfit_url=${encodeURIComponent(activeOutfitUrl)}`,
        { method: "POST", body: formData }
      );

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Try-on failed");
      }
      const data = await resp.json();
      setResult({ ...data, outfit_name: activeOutfitName });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="step-container">
      <h2>Try it on yourself</h2>
      <p className="step-desc">
        Use the AI-generated outfit or paste a link from Amazon, Temu, Shein, Myntra, Flipkart, etc.
      </p>

      {/* ── OUTFIT SOURCE TOGGLE ── */}
      <div className="toggle-row" style={{ marginBottom: 20 }}>
        <label className="field-label">Outfit source</label>
        <div className="toggle-group">
          <button
            className={`toggle-btn ${outfitSource === "generated" ? "active" : ""}`}
            onClick={() => { setOutfitSource("generated"); setFetchedProduct(null); setFetchError(null); }}
          >
            AI Generated
          </button>
          <button
            className={`toggle-btn ${outfitSource === "url" ? "active" : ""}`}
            onClick={() => setOutfitSource("url")}
          >
            Paste Product Link
          </button>
        </div>
      </div>

      {/* ── URL INPUT (only when "url" selected) ── */}
      {outfitSource === "url" && (
        <div className="url-input-section">
          <div className="url-input-row">
            <input
              type="url"
              className="url-input"
              placeholder="https://www.amazon.com/dp/... or temu.com/... or shein.com/..."
              value={productUrl}
              onChange={(e) => { setProductUrl(e.target.value); setFetchedProduct(null); setFetchError(null); }}
              onKeyDown={(e) => e.key === "Enter" && handleFetchProduct()}
            />
            <button
              className="btn-primary"
              onClick={handleFetchProduct}
              disabled={fetchingProduct || !productUrl.trim()}
            >
              {fetchingProduct ? (
                <span className="loading-text"><span className="spinner" /> Fetching...</span>
              ) : "Fetch →"}
            </button>
          </div>

          <div className="site-chips">
            {["Amazon", "Temu", "Shein", "Myntra", "Flipkart", "H&M", "Zara"].map(s => (
              <span key={s} className="site-chip">{s}</span>
            ))}
          </div>

          {fetchError && <div className="error-box" style={{ marginTop: 10 }}>⚠️ {fetchError}</div>}

          {fetchedProduct && (
            <div className="fetched-product-card">
              <img src={fetchedProduct.image_url} alt="Product" className="fetched-product-img" />
              <div className="fetched-product-info">
                <p className="fetched-product-name">{fetchedProduct.product_name || "Product"}</p>
                <p className="fetched-product-domain">from {fetchedProduct.source_domain}</p>
                <span className="fetched-ok-badge">✓ Ready for try-on</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── MAIN TRY-ON LAYOUT ── */}
      <div className="tryon-layout">
        {/* Outfit image */}
        <div className="tryon-col">
          <p className="col-label">
            {outfitSource === "url" ? "Product" : "Generated Outfit"}
          </p>
          {activeOutfitUrl ? (
            <>
              <img src={activeOutfitUrl} alt="Outfit" className="tryon-image" />
              <p className="outfit-name">{activeOutfitName}</p>
            </>
          ) : (
            <div className="upload-placeholder" style={{ cursor: "default" }}>
              <span>🛍️</span>
              <span>Paste a link above</span>
            </div>
          )}
        </div>

        <div className="tryon-arrow">+</div>

        {/* Person photo */}
        <div className="tryon-col">
          <p className="col-label">Your Photo</p>
          {photoPreview ? (
            <img src={photoPreview} alt="Your photo" className="tryon-image" />
          ) : (
            <div className="upload-placeholder" onClick={() => fileRef.current.click()}>
              <span>📷</span>
              <span>Upload photo</span>
            </div>
          )}
          <input
            type="file"
            ref={fileRef}
            accept="image/*"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          {photoPreview && (
            <button className="btn-secondary" onClick={() => fileRef.current.click()}>
              Change photo
            </button>
          )}
        </div>

        {/* Result */}
        {result && (
          <>
            <div className="tryon-arrow">→</div>
            <div className="tryon-col">
              <p className="col-label">Result ✨</p>
              <img src={result.result_url} alt="Try-on result" className="tryon-image" />
            </div>
          </>
        )}
      </div>

      {error && <div className="error-box">⚠️ {error}</div>}

      <div className="action-row">
        {!result ? (
          <>
            <button
              className="btn-primary"
              onClick={handleTryOn}
              disabled={!photo || !activeOutfitUrl || loading}
            >
              {loading ? (
                <span className="loading-text">
                  <span className="spinner" /> Processing... (~60s)
                </span>
              ) : (
                "Try it on 👗"
              )}
            </button>
            <button className="btn-ghost" onClick={onSkip}>
              Skip → Get styling tips
            </button>
          </>
        ) : (
          <button
            className="btn-primary"
            onClick={() => onComplete({ ...result, outfit_name: activeOutfitName })}
          >
            Get styling tips →
          </button>
        )}
      </div>
    </div>
  );
}
