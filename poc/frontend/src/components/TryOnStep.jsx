import { useState, useRef, useCallback } from "react";

export default function TryOnStep({ outfitImageUrl, outfitDescription, onComplete, onSkip }) {
  const [outfitSource, setOutfitSource]       = useState(outfitImageUrl ? "generated" : "url");
  const [productUrl, setProductUrl]           = useState("");
  const [fetchedProduct, setFetchedProduct]   = useState(null);
  const [fetchingProduct, setFetchingProduct] = useState(false);
  const [fetchError, setFetchError]           = useState(null);
  const [categoryOverride, setCategoryOverride] = useState("auto");

  const [photo, setPhoto]               = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState(null);
  const [result, setResult]             = useState(null);

  // Camera state
  const [cameraOpen, setCameraOpen]       = useState(false);
  const [cameraError, setCameraError]     = useState(null);
  const [stream, setStream]               = useState(null);
  const [facingMode, setFacingMode]       = useState("user"); // "user"=front, "environment"=back

  const fileRef   = useRef();
  const videoRef  = useRef();
  const canvasRef = useRef();

  const activeOutfitUrl  = outfitSource === "url" ? fetchedProduct?.image_url : outfitImageUrl;
  const activeOutfitName = outfitSource === "url" ? fetchedProduct?.product_name : outfitDescription;

  // ── File upload ──
  function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  }

  // ── Camera: open ──
  async function openCamera() {
    setCameraError(null);
    setCameraOpen(true);
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      setStream(s);
      if (videoRef.current) videoRef.current.srcObject = s;
    } catch (e) {
      setCameraError("Camera access denied. Please allow camera permission.");
      setCameraOpen(false);
    }
  }

  // ── Camera: flip front/back ──
  async function flipCamera() {
    if (stream) stream.getTracks().forEach(t => t.stop());
    const newMode = facingMode === "user" ? "environment" : "user";
    setFacingMode(newMode);
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: newMode, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      setStream(s);
      if (videoRef.current) videoRef.current.srcObject = s;
    } catch (e) {
      setCameraError("Could not switch camera.");
    }
  }

  // ── Camera: capture ──
  function capturePhoto() {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      const file = new File([blob], "camera-photo.jpg", { type: "image/jpeg" });
      setPhoto(file);
      setPhotoPreview(URL.createObjectURL(blob));
      setResult(null);
      setError(null);
      closeCamera();
    }, "image/jpeg", 0.92);
  }

  // ── Camera: close ──
  const closeCamera = useCallback(() => {
    if (stream) stream.getTracks().forEach(t => t.stop());
    setStream(null);
    setCameraOpen(false);
  }, [stream]);

  // ── Fetch product URL ──
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
      if (!resp.ok) { const e = await resp.json(); throw new Error(e.detail || "Could not fetch product"); }
      setFetchedProduct(await resp.json());
    } catch (e) {
      setFetchError(e.message);
    } finally {
      setFetchingProduct(false);
    }
  }

  // ── Try-on ──
  async function handleTryOn() {
    if (!photo || !activeOutfitUrl) return;
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("person_photo", photo);
      const params = new URLSearchParams({
        outfit_url: activeOutfitUrl,
        outfit_description: activeOutfitName || "",
        category: categoryOverride,
      });
      const resp = await fetch(
        `${import.meta.env.VITE_API_URL}/api/tryon?${params}`,
        { method: "POST", body: formData }
      );
      if (!resp.ok) { const e = await resp.json(); throw new Error(e.detail || "Try-on failed"); }
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

      {/* ── TRY-ON MODE TOGGLE ── */}
      <div className="toggle-row" style={{ marginBottom: 20 }}>
        <label className="field-label">What to wear?</label>
        <div className="toggle-group">
          <button className={`toggle-btn ${categoryOverride === "auto" ? "active" : ""}`} onClick={() => setCategoryOverride("auto")}>🤖 Auto</button>
          <button className={`toggle-btn ${categoryOverride === "tops" ? "active" : ""}`} onClick={() => setCategoryOverride("tops")}>👕 Top</button>
          <button className={`toggle-btn ${categoryOverride === "bottoms" ? "active" : ""}`} onClick={() => setCategoryOverride("bottoms")}>👖 Bottom</button>
          <button className={`toggle-btn ${categoryOverride === "one-pieces" ? "active" : ""}`} onClick={() => setCategoryOverride("one-pieces")}>👗 Full Dress</button>
        </div>
      </div>

      {/* ── URL INPUT ── */}
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
            <button className="btn-primary" onClick={handleFetchProduct} disabled={fetchingProduct || !productUrl.trim()}>
              {fetchingProduct ? <span className="loading-text"><span className="spinner" /> Fetching...</span> : "Fetch →"}
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

        {/* Outfit column */}
        <div className="tryon-col">
          <p className="col-label">{outfitSource === "url" ? "Product" : "Generated Outfit"}</p>
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

        {/* Person photo column */}
        <div className="tryon-col">
          <p className="col-label">Your Photo</p>

          {photoPreview ? (
            <img src={photoPreview} alt="Your photo" className="tryon-image" />
          ) : (
            <div className="upload-placeholder" onClick={() => fileRef.current.click()}>
              <span>📷</span>
              <span>Upload or take photo</span>
            </div>
          )}

          {/* Photo source buttons */}
          <div className="photo-source-row">
            <button className="btn-secondary" onClick={() => fileRef.current.click()} title="Upload from gallery">
              📁 {photoPreview ? "Change" : "Upload"}
            </button>
            <button className="btn-secondary" onClick={openCamera} title="Take photo with camera">
              📷 Camera
            </button>
          </div>

          <input type="file" ref={fileRef} accept="image/*" style={{ display: "none" }} onChange={handleFileChange} />
          {cameraError && <p className="camera-error">{cameraError}</p>}
        </div>

        {/* Result column */}
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
            <button className="btn-primary" onClick={handleTryOn} disabled={!photo || !activeOutfitUrl || loading}>
              {loading
                ? <span className="loading-text"><span className="spinner" /> Processing... (~30s)</span>
                : "Try it on 👗"}
            </button>
            <button className="btn-ghost" onClick={onSkip}>Skip → Get styling tips</button>
          </>
        ) : (
          <button className="btn-primary" onClick={() => onComplete({ ...result, outfit_name: activeOutfitName })}>
            Get styling tips →
          </button>
        )}
      </div>

      {/* ── CAMERA MODAL ── */}
      {cameraOpen && (
        <div className="camera-overlay" onClick={(e) => e.target === e.currentTarget && closeCamera()}>
          <div className="camera-modal">
            <div className="camera-header">
              <span className="camera-title">Take your photo</span>
              <button className="camera-close" onClick={closeCamera}>✕</button>
            </div>

            <div className="camera-viewfinder">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="camera-video"
                onLoadedMetadata={() => videoRef.current?.play()}
              />
              {/* Pose guide overlay */}
              <div className="camera-guide">
                <div className="guide-silhouette" />
                <p className="guide-text">Stand full body in frame</p>
              </div>
            </div>

            <div className="camera-controls">
              <button className="camera-flip" onClick={flipCamera} title="Flip camera">
                🔄 Flip
              </button>
              <button className="camera-capture" onClick={capturePhoto}>
                <span className="capture-ring" />
              </button>
              <button className="camera-cancel" onClick={closeCamera}>
                Cancel
              </button>
            </div>

            <canvas ref={canvasRef} style={{ display: "none" }} />
          </div>
        </div>
      )}
    </div>
  );
}
