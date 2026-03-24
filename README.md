# Sahion - AI Fashion Stylist & Virtual Try-On

Sahion is an advanced AI-powered fashion styling and virtual try-on web application. It enables users to generate hyper-realistic clothing concepts based on simple text descriptions (in almost any language) and visualize those exact outfits directly on their own body.

## 🌟 Key Features

- **Multilingual Outfit Generation**: Describe what you want to wear in any language (English, Telugu, Hindi, Spanish, etc.). The AI translates and enriches your description into a hyper-detailed studio photography prompt, generating a photorealistic outfit using Google's newest **Gemini 3.1 Flash Image** models or fallback **SDXL** models.
- **Body & Style Profiling**: Enter your demographic, height, weight, skin tone, and body type to get personalized color and fit recommendations. The app dynamically renders a body silhouette based on your BMI.
- **Intelligent Virtual Try-On**: Upload a selfie or use your webcam to try on the generated outfits (or paste a product link from external sites).
- **Multi-Engine AI Routing**: The backend is designed with a highly robust fallback hierarchy that routes your try-on request to the highest quality model available. Supported engines include:
  - **Gemini 3.1 Flash** (Native Multi-Image Try-On)
  - **Fashn.ai** (Absolute highest quality try-on via Fal.ai or HuggingFace)
  - **IDM-VTON** (Free upper-body try-on via HuggingFace Spaces)
  - **Segmind / Nanobanana** (Text-to-Image masking fallbacks)
- **Granular Garment Control**: Explicitly control how the AI edits your photo. Override the automatic detection to specifically replace just your **Top**, your **Bottom**, or swap your entire look with a **Full Dress/Suit** mask. 
- **Mobile Wi-Fi Testing**: Includes a `start-mobile.bat` script that automatically detects your local IP and broadcasts the local frontend/backend servers across your home Wi-Fi network, allowing for seamless mobile testing.

## 🏗️ Architecture

- **Frontend**: Built with **React** and **Vite**. Features a heavily stylized, dark-mode CSS architecture with fully responsive multi-step wizards, interactive toggle buttons, and native device webcam API integration.
- **Backend**: Built with **Python** and **FastAPI**. Highly concurrent and asynchronous, utilizing `httpx` for fast third-party AI inference fetching. The backend mathematically preserves and dynamically scales final images to explicitly match the native resolution of your uploaded selfies.

## 🚀 How to Run Locally

1. Ensure you have **Python 3.9+** and **Node.js** installed on your system.
2. Provide your API environment variables in `poc/backend/.env`. 
   *(The system heavily supports modular keys, such as `GEMINI_API_KEY`, `OPENAI_API_KEY`, `REPLICATE_API_TOKEN`, `HF_TOKEN`, `FAL_API_KEY`, `SEGMIND_API_KEY`, and `NANOBANANA_API_KEY`. Add the ones you prefer to use!)*
3. Double-click **`start.bat`** on your PC. This script automatically terminates stale instances, spins up both the FastAPI server and Vite server, and directly opens your default web browser to the app.
4. **To test on a mobile device:** Make sure your phone is on the exact same Wi-Fi network and run **`start-mobile.bat`**. This dynamically configures your proxy bindings to allow traffic from your smartphone.
