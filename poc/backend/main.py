import os
import re
import time
import base64
import asyncio
import tempfile
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from gradio_client import Client as GradioClient, handle_file

load_dotenv()

app = FastAPI(title="Sahion Fashion POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your Vercel domain in production if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
CLIPDROP_API_KEY = os.getenv("CLIPDROP_API_KEY")

REPLICATE_HEADERS = {
    "Authorization": f"Token {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}

NANOBANANA_API_KEY = os.getenv("NANOBANANA_API_KEY")
NANOBANANA_HEADERS = {
    "Authorization": f"Bearer {NANOBANANA_API_KEY}",
    "Content-Type": "application/json",
}

FAL_API_KEY = os.getenv("FAL_API_KEY")
FAL_HEADERS = {
    "Authorization": f"Key {FAL_API_KEY}",
    "Content-Type": "application/json",
}

SEGMIND_API_KEY = os.getenv("SEGMIND_API_KEY")
SEGMIND_HEADERS = {
    "x-api-key": SEGMIND_API_KEY or "",
    "Content-Type": "application/json",
}

# HuggingFace token — used to call fal.ai/Fashn via HF's inference router
HF_TOKEN = os.getenv("HF_TOKEN")
HF_FAL_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json",
}


# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    description: str           # e.g. "flowy sage green midi dress for beach"
    gender: str = "unisex"     # male / female / unisex
    person_type: str = "adult" # adult / kid
    age: int = None


class StyleRequest(BaseModel):
    outfit_description: str
    skin_tone: str = "not specified"
    body_type: str = "not specified"
    height_cm: float = None
    weight_kg: float = None
    bmi: float = None
    gender: str = "not specified"   # male / female / unisex
    age: int = None
    person_type: str = "adult"      # adult / kid


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def poll_replicate(prediction_id: str, timeout: int = 180) -> dict:
    """Poll Replicate until job completes or times out."""
    url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = httpx.get(url, headers=REPLICATE_HEADERS)
        data = resp.json()
        status = data.get("status")
        if status == "succeeded":
            return data
        if status == "failed":
            raise HTTPException(status_code=500, detail=f"Replicate job failed: {data.get('error')}")
        time.sleep(3)
    raise HTTPException(status_code=504, detail="Replicate job timed out")


# Keyword maps: what user types → exact SD tokens that SDXL understands well
SLEEVE_MAP = {
    # short sleeve variants — English
    "half sleeve":   "t-shirt with short sleeves above the elbow",
    "half sleeves":  "t-shirt with short sleeves above the elbow",
    "half hand":     "t-shirt with short sleeves above the elbow",
    "half hands":    "t-shirt with short sleeves above the elbow",
    "short sleeve":  "short sleeve shirt, sleeves ending above elbow",
    "short sleeves": "short sleeve shirt, sleeves ending above elbow",
    "cap sleeve":    "cap sleeve top, very short sleeves at shoulder",
    "elbow sleeve":  "elbow-length sleeves",
    "sleeveless":    "sleeveless top, no sleeves",
    "tank top":      "sleeveless tank top, no sleeves",
    # long sleeve variants — English
    "full sleeve":   "full sleeve shirt, long sleeves reaching wrists",
    "full sleeves":  "full sleeve shirt, long sleeves reaching wrists",
    "full hand":     "full sleeve shirt, long sleeves reaching wrists",
    "full hands":    "full sleeve shirt, long sleeves reaching wrists",
    "long sleeve":   "long sleeve shirt, sleeves reaching wrists",
    "long sleeves":  "long sleeve shirt, sleeves reaching wrists",
    # Hindi sleeve keywords
    "आधी बाँह":     "t-shirt with short sleeves above the elbow",
    "आधी बाह":      "t-shirt with short sleeves above the elbow",
    "छोटी बाँह":    "short sleeve shirt, sleeves ending above elbow",
    "पूरी बाँह":    "full sleeve shirt, long sleeves reaching wrists",
    "पूरी बाह":     "full sleeve shirt, long sleeves reaching wrists",
    "लंबी बाँह":    "full sleeve shirt, long sleeves reaching wrists",
    "बिना बाँह":    "sleeveless top, no sleeves",
    # Telugu sleeve keywords
    "సగం చేతి":     "t-shirt with short sleeves above the elbow",
    "పొట్టి చేతి":  "short sleeve shirt, sleeves ending above elbow",
    "పూర్తి చేతి":  "full sleeve shirt, long sleeves reaching wrists",
    "పొడవు చేతి":   "full sleeve shirt, long sleeves reaching wrists",
    # Malayalam sleeve keywords
    "പകുതി കൈ":    "t-shirt with short sleeves above the elbow",
    "ചെറിയ കൈ":    "short sleeve shirt, sleeves ending above elbow",
    "നീളൻ കൈ":     "full sleeve shirt, long sleeves reaching wrists",
    # Tamil sleeve keywords
    "அரை கை":      "t-shirt with short sleeves above the elbow",
    "முழு கை":      "full sleeve shirt, long sleeves reaching wrists",
    # Chinese sleeve keywords
    "短袖":          "short sleeve shirt, sleeves ending above elbow",
    "长袖":          "full sleeve shirt, long sleeves reaching wrists",
    "无袖":          "sleeveless top, no sleeves",
    # Russian sleeve keywords
    "короткий рукав": "short sleeve shirt, sleeves ending above elbow",
    "длинный рукав":  "full sleeve shirt, long sleeves reaching wrists",
    "без рукавов":    "sleeveless top, no sleeves",
}

def extract_sleeve_token(description: str) -> str | None:
    """Return the exact SD sleeve token if user specified one, else None.
    Checks both lowercased (for English/Russian/etc.) and original (for Telugu/Hindi/Chinese scripts).
    """
    desc_lower = description.lower()
    for keyword, token in SLEEVE_MAP.items():
        if keyword in desc_lower or keyword in description:
            return token
    return None


FASHION_VOCABULARY_GUIDE = """
You know ALL fashion garments worldwide, including:

INDIAN ETHNIC WEAR:
- Saree/Sari/చీర/साड़ी/ساڑی = 6-yard draped silk/cotton garment worn by women
- Lehenga/లేహంగా/लहंगा = flared skirt with choli blouse and dupatta
- Salwar Kameez/Churidar/Kurta Pajama = tunic with pants
- Anarkali = long flared kurta dress
- Kurti/కుర్తీ/कुर्ती = short tunic top
- Pattu/పట్టు = silk fabric (as in pattu saree = silk saree)
- Pavada/Langa = half-saree skirt for girls
- Dhoti/Panche/Veshti/పంచె/धोती = traditional men's lower garment, wrapped white cloth
- Sherwani/Achkan = men's long formal coat
- Bandhgala = mandarin collar formal jacket
- Nehru jacket = sleeveless/short-sleeved formal jacket
- Dupatta/Chunni/ఓఢని = long scarf/stole
- Ghagra = full flared skirt
- Banyan/Baniyan/బనియన్ = undershirt/vest (in South Asia)
- Lungi/లుంగీ/لنگی = casual men's wraparound cloth
- Mundu = white Kerala men's dhoti
- Angavastram = men's shoulder cloth
- Phulkari = Punjabi embroidered fabric
- Kanjivaram/Kanjeevaram = premium silk saree from Tamil Nadu
- Banarasi = silk brocade saree from Varanasi
- Chanderi = lightweight silk-cotton fabric
- Chikankari = Lucknow embroidery style

CASUAL / EVERYDAY WORDS:
- Frock/ఫ్రాక్/फ्रॉक = casual dress, often for kids or women
- Shirt/Tee/T-shirt = upper body garment
- Pant/Trouser = lower body garment
- Jeans/Denim = denim trousers
- Skirt = lower garment for women
- Jacket/Coat = outer layer
- Sweater/Pullover/Jumper = knit top
- Hoodie = sweatshirt with hood
- Blouse/చొక్కా = fitted top/shirt
- Maxi dress = full length dress
- Mini dress = short dress
- Midi dress = knee-length dress
- Jumpsuit/Romper = one-piece
- Dungarees/Overalls = bib overalls

COLORS (common words people actually say):
- Red/Lal/Erra/Sivappu/Adom/Красный/红色/Rouge = red
- Blue/Neela/Neel/Pacha(dark)/Nilam/Синий/蓝色 = blue
- Green/Hara/Pacha/Pacchai/Yeşil/Зелёный/绿色 = green
- Yellow/Peela/Puvvu/Manjal/Gelb/Жёлтый/黄色 = yellow
- Pink/Gulabi/Roja/Roosi/Rosa/Розовый/粉色 = pink
- White/Safed/Tella/Vellai/Weiß/Белый/白色 = white
- Black/Kala/Nalla/Karuppu/Schwarz/Чёрный/黑色 = black
- Orange/Naranja/Narancssárga/橙色 = orange
- Purple/Violet/Baigani/Jamuni/Violet/紫色 = purple
- Gold/Sona/Bangaru/Thanga/Золотой/金色 = gold
- Silver/Chandi/Veludi/Вересень/银色 = silver
- Maroon/Dark red/Koyu kırmızı = dark red
- Cream/Ivory/Off-white = light white-yellow

FABRICS:
- Silk/Reshmi/Pattu/Resham/Soie = silk
- Cotton/Sutar/Patti/Coton = cotton
- Linen = natural flax fabric
- Chiffon = sheer lightweight fabric
- Georgette = crinkled lightweight fabric
- Net/Mesh = see-through fabric
- Velvet = soft plush fabric
- Satin = smooth shiny fabric
- Denim = heavy cotton twill
- Khadi = handspun cotton

OCCASION WORDS:
- Wedding/Shadi/Kalyanam/Vivah/Byah = wedding outfit
- Party/Function/Celebration = party wear
- Office/Work/Formal = formal wear
- Casual/Daily/Everyday = casual wear
- Festival/Puja/Pooja/Eid/Diwali/Navratri = festive wear
- Beach/Summer/Holiday = casual summer
- College/School = student/casual

EMBELLISHMENTS:
- Embroidery/Kadhai/Kasu/Zari = decorative needlework
- Sequin/Sitara/Tikki = sparkly decorations
- Mirror work/Sheesha = mirror embellishments
- Lace = decorative trim
- Printed/Print/Floral/Geometric = print patterns
- Plain/Simple/Solid = no pattern
- Checks/Plaid/Stripes/Dots = geometric patterns

Always interpret the user's description using this knowledge, then generate a precise Stable Diffusion prompt.
"""


def enrich_prompt(user_description: str, sleeve_token: str | None,
                  gender: str = "unisex", person_type: str = "adult", age: int = None) -> str:
    """
    GPT enriches style/fabric/lighting details.
    Gender is enforced as a hard constraint — injected at the START of the SD prompt.
    Sleeve token is also injected at the START so SDXL cannot override either.
    """
    # Build a strict gender instruction so GPT never defaults to female fashion
    if gender == "male":
        gender_rule = (
            "CRITICAL: This outfit is for a MAN. Generate ONLY menswear. "
            "Use masculine clothing: shirts, trousers, kurtas, sherwanis, dhotis, suits, etc. "
            "NEVER generate dresses, sarees, lehengas, blouses, or any women's garments. "
            "The SD prompt must start with 'male model wearing' or 'man wearing'."
        )
        gender_prefix = "male model wearing"
    elif gender == "female":
        gender_rule = (
            "This outfit is for a WOMAN. Generate womenswear. "
            "The SD prompt must start with 'female model wearing' or 'woman wearing'."
        )
        gender_prefix = "female model wearing"
    else:
        gender_rule = "Generate gender-neutral / unisex clothing."
        gender_prefix = "model wearing"

    if person_type == "kid":
        age_str = f"{age}-year-old " if age else ""
        gender_rule += f" This is for a {age_str}child — keep it age-appropriate and playful."
        gender_prefix = f"{age_str}child wearing"

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Stable Diffusion fashion prompt engineer with deep knowledge of "
                    "global fashion, ethnic wear, and everyday clothing words across all cultures.\n\n"
                    + FASHION_VOCABULARY_GUIDE +
                    f"\n\nGENDER RULE (NON-NEGOTIABLE): {gender_rule}\n\n"
                    "The user may write in ANY language (Telugu, Hindi, Malayalam, Odia, Tamil, "
                    "Chinese, Russian, Arabic, Spanish, French, or any other). "
                    "Understand what outfit they want using the vocabulary above, then write a detailed "
                    "English Stable Diffusion prompt with: fabric texture, color details, fit, "
                    "ghost mannequin product photography, clothing only on invisible mannequin, "
                    "pure white background, studio lighting, sharp detail, 4k quality. "
                    "DO NOT mention sleeves or sleeve length — that will be added separately. "
                    f"The prompt MUST begin with '{gender_prefix}'. "
                    "Keep under 100 words. Return ONLY the English prompt text, no explanation."
                ),
            },
            {"role": "user", "content": user_description},
        ],
        max_tokens=180,
    )
    base = response.choices[0].message.content.strip()

    # Ensure gender prefix is at the very start (fallback if GPT forgot)
    base_lower = base.lower()
    if not any(base_lower.startswith(p) for p in ["male", "female", "man ", "woman ", "child", "boy", "girl"]):
        base = f"{gender_prefix}, {base}"

    # Inject sleeve token at the START so SDXL sees it with highest weight
    if sleeve_token:
        return f"{sleeve_token}, {base}"
    return base


# ─────────────────────────────────────────────
# ENDPOINT 1: TEXT → OUTFIT IMAGE
# ─────────────────────────────────────────────

@app.post("/api/generate")
async def generate_outfit(req: GenerateRequest):
    """
    Takes a text description, enriches it, generates outfit via SDXL.
    Returns the generated image URL.
    """
    # Step 1: Extract exact sleeve token from user description BEFORE enrichment
    sleeve_token = extract_sleeve_token(req.description)

    # Step 2: Enrich — gender + sleeve token injected at front of final prompt
    enriched = enrich_prompt(req.description, sleeve_token,
                             gender=req.gender, person_type=req.person_type, age=req.age)

    # Step 3: Build negative prompt
    short_sleeve_terms = ["half sleeve", "half hand", "short sleeve", "half-sleeve",
                          "half-hand", "elbow sleeve", "cap sleeve", "sleeveless", "tank top"]
    desc_lower = req.description.lower()
    is_short_sleeve = any(t in desc_lower for t in short_sleeve_terms)

    base_negative = "blurry, bad anatomy, distorted, ugly, low quality, watermark, text"

    # Add sleeve negation
    if is_short_sleeve:
        base_negative += ", long sleeves, full sleeves, full length sleeves, sleeves past elbow"

    # Add strong gender negation to prevent wrong gender output
    if req.gender == "male":
        base_negative += ", woman, girl, female, dress, saree, skirt, lehenga, bra, feminine"
    elif req.gender == "female":
        base_negative += ", man, boy, masculine, men's suit"

    negative_prompt = base_negative

    # Step 3: Submit to Replicate SDXL
    resp = httpx.post(
        "https://api.replicate.com/v1/predictions",
        headers=REPLICATE_HEADERS,
        json={
            "version": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            "input": {
                "prompt": enriched,
                "negative_prompt": negative_prompt,
                "width": 768,
                "height": 1024,
                "num_inference_steps": 35,
                "guidance_scale": 8.5,
                "scheduler": "DPMSolverMultistep",
            },
        },
    )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Replicate submit failed: {resp.text}")

    prediction_id = resp.json()["id"]

    # Step 4: Poll until done
    result = poll_replicate(prediction_id)
    image_url = result["output"][0] if isinstance(result["output"], list) else result["output"]

    # Step 5: Re-host on catbox so Nanobanana try-on can reliably fetch it later
    try:
        img_bytes = httpx.get(image_url, timeout=20).content
        catbox_url = httpx.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": ("outfit.jpg", img_bytes, "image/jpeg")},
            timeout=30,
        ).text.strip()
        if catbox_url.startswith("https://"):
            image_url = catbox_url
    except Exception:
        pass  # use original Replicate URL if catbox upload fails

    return {
        "image_url": image_url,
        "enriched_prompt": enriched,
        "negative_prompt": negative_prompt,
        "original_description": req.description,
        "prediction_id": prediction_id,
    }


# ─────────────────────────────────────────────
# ENDPOINT 2: PHOTO + OUTFIT → VIRTUAL TRY-ON
# Priority 1: Segmind Try-On Diffusion (free credits, Hugging Face)
# Priority 2: Fashn.ai (fal.ai) — purpose-built, high quality
# Priority 3: Nanobanana (fallback)
# ─────────────────────────────────────────────

def image_url_to_base64(url: str) -> str:
    """Download an image from a URL and return base64-encoded string."""
    resp = httpx.get(url, timeout=20, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return base64.b64encode(resp.content).decode("utf-8")


def image_bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


async def tryon_idmvton(person_bytes: bytes, outfit_bytes: bytes, garment_desc: str = "") -> str:
    """
    Virtual try-on via IDM-VTON HuggingFace Space (yisol/IDM-VTON).
    Uses gradio_client + HF_TOKEN — completely FREE with any HF account.
    Returns base64 data URI of the result image.
    """
    # Write bytes to temp files (gradio_client needs file paths)
    pf = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    pf.write(person_bytes); pf.close()
    gf = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    gf.write(outfit_bytes); gf.close()

    try:
        # Run blocking gradio call in thread pool so we don't block FastAPI
        def _run():
            client = GradioClient("yisol/IDM-VTON", token=HF_TOKEN)
            return client.predict(
                dict={"background": handle_file(pf.name), "layers": [], "composite": None},
                garm_img=handle_file(gf.name),
                garment_des=garment_desc or "garment",
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon",
            )

        result = await asyncio.get_event_loop().run_in_executor(None, _run)
        result_path = result[0]  # first return value is the result image path

        with open(result_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{img_b64}"
    finally:
        os.unlink(pf.name)
        os.unlink(gf.name)


async def tryon_segmind(person_bytes: bytes, outfit_url: str, category: str = "tops") -> str:
    """
    Segmind Try-On Diffusion via https://api.segmind.com/v1/try-on-diffusion
    Uses base64-encoded images — no need for public URLs.
    category: 'Upper body' | 'Lower body' | 'Dress'
    Returns base64-encoded result image (data URI).
    """
    # Map our category names to Segmind's
    cat_map = {
        "tops": "Upper body",
        "bottoms": "Lower body",
        "one-pieces": "Dress",
        "auto": "Upper body",  # sensible default
    }
    segmind_category = cat_map.get(category, "Upper body")

    # Encode person photo
    person_b64 = image_bytes_to_base64(person_bytes)

    # Download + encode outfit image
    async with httpx.AsyncClient(timeout=20) as client:
        outfit_resp = await client.get(outfit_url, follow_redirects=True,
                                       headers={"User-Agent": "Mozilla/5.0"})
    outfit_b64 = image_bytes_to_base64(outfit_resp.content)

    payload = {
        "model_image": person_b64,
        "cloth_image": outfit_b64,
        "category": segmind_category,
        "num_inference_steps": 35,
        "guidance_scale": 7.5,
        "seed": -1,
        "base64": True,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.segmind.com/v1/try-on-diffusion",
            headers=SEGMIND_HEADERS,
            json=payload,
        )

    if resp.status_code == 401:
        raise Exception("Segmind: invalid API key")
    if resp.status_code == 429:
        raise Exception("Segmind: rate limit exceeded")
    if resp.status_code != 200:
        raise Exception(f"Segmind failed ({resp.status_code}): {resp.text[:200]}")

    # Response is base64 image — could be JSON or plain text
    try:
        data = resp.json()
        img_b64 = data.get("image") or data.get("data") or data.get("result") or data.get("output")
    except Exception:
        img_b64 = resp.text.strip()

    if not img_b64:
        raise Exception(f"Segmind: empty response: {resp.text[:200]}")

    # Return as data URI
    return f"data:image/png;base64,{img_b64}"


async def tryon_hf_fashn(person_url: str, outfit_url: str, category: str = "auto") -> str:
    """
    Virtual try-on using Fashn via HuggingFace's fal-ai inference provider.
    Uses HF_TOKEN — works with free HuggingFace account.
    Same Fashn model, billed through HuggingFace credits.
    """
    cat_map = {
        "tops": "tops",
        "bottoms": "bottoms",
        "one-pieces": "one-pieces",
        "auto": "auto",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://router.huggingface.co/fal-ai/fashn/tryon/v1.5",
            headers=HF_FAL_HEADERS,
            json={
                "model_image": person_url,
                "garment_image": outfit_url,
                "category": cat_map.get(category, "auto"),
                "mode": "quality",
                "garment_photo_type": "auto",
                "moderation_level": "permissive",
                "num_samples": 1,
                "output_format": "jpeg",
            },
        )

        if resp.status_code == 401:
            raise Exception("HF token invalid or missing inference permissions")
        if resp.status_code != 200:
            raise Exception(f"HF Fashn failed ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()

        # Synchronous response with images array
        if data.get("images"):
            return data["images"][0]["url"]

        # Async polling via request_id
        request_id = data.get("request_id")
        if not request_id:
            raise Exception(f"No request_id from HF Fashn: {data}")

        deadline = time.time() + 120
        while time.time() < deadline:
            status_resp = await client.get(
                f"https://router.huggingface.co/fal-ai/fashn/tryon/v1.5/requests/{request_id}/status",
                headers=HF_FAL_HEADERS,
            )
            status = status_resp.json()
            if status.get("status") == "COMPLETED":
                result_resp = await client.get(
                    f"https://router.huggingface.co/fal-ai/fashn/tryon/v1.5/requests/{request_id}",
                    headers=HF_FAL_HEADERS,
                )
                return result_resp.json()["images"][0]["url"]
            if status.get("status") in ("FAILED", "CANCELLED"):
                raise Exception(f"HF Fashn job failed: {status}")
            await asyncio.sleep(3)

    raise Exception("HF Fashn try-on timed out")


async def tryon_fashn(person_url: str, outfit_url: str, category: str = "auto") -> str:
    """
    Use Fashn.ai via fal.ai for high-quality virtual try-on.
    category: 'tops' | 'bottoms' | 'one-pieces' | 'auto'
    Returns result image URL.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        # Submit job
        resp = await client.post(
            "https://fal.run/fal-ai/fashn/tryon/v1.5",
            headers=FAL_HEADERS,
            json={
                "model_image": person_url,
                "garment_image": outfit_url,
                "category": category,
                "mode": "quality",
                "garment_photo_type": "auto",
                "moderation_level": "permissive",
                "num_samples": 1,
                "output_format": "jpeg",
            },
        )

        if resp.status_code != 200:
            raise Exception(f"Fashn submit failed: {resp.text[:200]}")

        data = resp.json()

        # Synchronous response — output is returned directly
        if data.get("images"):
            return data["images"][0]["url"]

        # Async response — poll via request_id
        request_id = data.get("request_id")
        if not request_id:
            raise Exception(f"No request_id from Fashn: {data}")

        deadline = time.time() + 120
        while time.time() < deadline:
            status_resp = await client.get(
                f"https://fal.run/fal-ai/fashn/tryon/v1.5/requests/{request_id}/status",
                headers=FAL_HEADERS,
            )
            status = status_resp.json()
            if status.get("status") == "COMPLETED":
                result_resp = await client.get(
                    f"https://fal.run/fal-ai/fashn/tryon/v1.5/requests/{request_id}",
                    headers=FAL_HEADERS,
                )
                return result_resp.json()["images"][0]["url"]
            if status.get("status") in ("FAILED", "CANCELLED"):
                raise Exception(f"Fashn job failed: {status}")
            await asyncio.sleep(3)

        raise Exception("Fashn try-on timed out")


def poll_nanobanana(task_id: str, timeout: int = 180) -> str:
    """Poll Nanobanana until job completes, return result image URL."""
    url = "https://api.nanobananaapi.ai/api/v1/nanobanana/record-info"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = httpx.get(url, headers=NANOBANANA_HEADERS, params={"taskId": task_id})
        outer = resp.json()
        # All result fields are nested under "data"
        data = outer.get("data") or {}
        flag = data.get("successFlag")
        if flag == 1:
            response = data.get("response") or {}
            return response.get("resultImageUrl") or response.get("originImageUrl")
        if flag in (2, 3):
            raise HTTPException(status_code=500, detail=f"Nanobanana job failed: {data}")
        time.sleep(3)
    raise HTTPException(status_code=504, detail="Nanobanana job timed out")


async def remove_background(image_bytes: bytes) -> bytes:
    """Remove background using Clipdrop so only the garment remains (no model confusion)."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                "https://clipdrop-api.co/remove-background/v1",
                headers={"x-api-key": CLIPDROP_API_KEY},
                files={"image_file": ("outfit.jpg", image_bytes, "image/jpeg")},
            )
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
    return image_bytes  # fallback: return original


async def upload_to_public_host(image_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload image bytes to catbox.moe and return the public URL."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (filename, image_bytes, content_type)},
            )
            if r.status_code == 200 and r.text.strip().startswith("https://"):
                return r.text.strip()
        except Exception:
            pass
    raise HTTPException(status_code=500, detail="Could not upload image to a public host. Please try again.")


@app.post("/api/tryon")
async def virtual_tryon(
    person_photo: UploadFile = File(...),
    outfit_url: str = Query(...),
    outfit_description: str = Query(default=""),
):
    person_bytes = await person_photo.read()

    # Detect garment category from description
    desc_lower = outfit_description.lower()
    is_top    = any(w in desc_lower for w in ["shirt","tshirt","t-shirt","top","blouse","kurta","kurti","sherwani","jacket","coat","sweater","hoodie","polo","tank","vest","tunic","kameez"])
    is_bottom = any(w in desc_lower for w in ["pant","trouser","jeans","skirt","shorts","dhoti","lungi","legging","churidar","pajama","salwar"])
    is_dress  = any(w in desc_lower for w in ["dress","saree","sari","lehenga","gown","frock","jumpsuit","romper"])

    if is_dress:
        fashn_category = "one-pieces"
    elif is_bottom and not is_top:
        fashn_category = "bottoms"
    elif is_top and not is_bottom:
        fashn_category = "tops"
    else:
        fashn_category = "auto"

    # Download outfit image bytes once (needed by IDM-VTON and Segmind)
    outfit_bytes = None
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            dl = await client.get(outfit_url, follow_redirects=True,
                                  headers={"User-Agent": "Mozilla/5.0"})
            if dl.status_code == 200 and len(dl.content) > 1000:
                outfit_bytes = dl.content
        except Exception:
            pass

    # ── Priority 1: IDM-VTON via HuggingFace Space (FREE with HF token) ──
    if HF_TOKEN and HF_TOKEN != "your_hf_token_here" and outfit_bytes:
        try:
            result_url = await tryon_idmvton(person_bytes, outfit_bytes, garment_desc=outfit_description)
            return {"result_url": result_url, "engine": "idm-vton"}
        except Exception:
            pass  # fall through

    # ── Priority 2: Segmind (no public URL needed) ──
    if SEGMIND_API_KEY and SEGMIND_API_KEY != "your_segmind_key_here":
        try:
            result_url = await tryon_segmind(person_bytes, outfit_url, category=fashn_category)
            return {"result_url": result_url, "engine": "segmind"}
        except Exception:
            pass  # fall through

    # For HF-Fashn/Nanobanana we need public URLs — upload to catbox
    person_image_url = await upload_to_public_host(
        person_bytes,
        person_photo.filename or "photo.jpg",
        person_photo.content_type or "image/jpeg"
    )
    if outfit_bytes:
        try:
            outfit_url = await upload_to_public_host(outfit_bytes, "outfit.jpg", "image/jpeg")
        except Exception:
            pass

    # ── Priority 3: HuggingFace → Fashn (paid HF credits) ──
    if HF_TOKEN and HF_TOKEN != "your_hf_token_here":
        try:
            result_url = await tryon_hf_fashn(person_image_url, outfit_url, category=fashn_category)
            return {"result_url": result_url, "engine": "hf-fashn"}
        except Exception:
            pass  # fall through

    # ── Priority 4: Direct Fashn.ai key ──
    if FAL_API_KEY and FAL_API_KEY != "your_fal_key_here":
        try:
            result_url = await tryon_fashn(person_image_url, outfit_url, category=fashn_category)
            return {"result_url": result_url, "engine": "fashn"}
        except Exception:
            pass  # fall through to Nanobanana

    # ── Priority 5: Nanobanana ──
    async with httpx.AsyncClient(timeout=30) as client:
        nb_resp = await client.post(
            "https://api.nanobananaapi.ai/api/v1/nanobanana/generate",
            headers=NANOBANANA_HEADERS,
            json={
                "prompt": (
                    f"Virtual try-on. IMAGE 1 is the TARGET PERSON — keep their exact face, skin, hair, body, pose. "
                    f"IMAGE 2 is the GARMENT — apply it onto the person from Image 1. "
                    f"{'Garment: ' + outfit_description + '.' if outfit_description else ''} "
                    f"Realistic fit, natural drape, correct lighting."
                ),
                "type": "IMAGETOIAMGE",
                "numImages": 1,
                "imageUrls": [person_image_url, outfit_url],
                "callBackUrl": "https://webhook.site/noop",
                "watermark": False,
            },
        )

    if nb_resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Try-on failed: {nb_resp.text}")

    resp_data = nb_resp.json()
    if resp_data.get("code") == 402:
        raise HTTPException(status_code=402, detail="Try-on credits exhausted. Please top up Nanobanana or add a FAL_API_KEY.")

    task_id = (resp_data.get("data") or {}).get("taskId") or resp_data.get("taskId")
    if not task_id:
        raise HTTPException(status_code=500, detail=f"No taskId in response: {nb_resp.text}")

    result_url = poll_nanobanana(task_id, timeout=180)
    return {"result_url": result_url, "engine": "nanobanana", "task_id": task_id}


# ─────────────────────────────────────────────
# ENDPOINT 3: STYLING SUGGESTIONS
# ─────────────────────────────────────────────

@app.post("/api/style")
async def get_styling_suggestions(req: StyleRequest):
    """
    Returns accessories, occasions, how-to-wear tips, and color palettes
    personalized to skin tone and body type.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional fashion stylist with deep knowledge of global and ethnic fashion.\n\n"
                    + FASHION_VOCABULARY_GUIDE +
                    "\n\nThe outfit description may be in any language — understand it using the vocabulary "
                    "above and respond in English JSON. "
                    "Always respond with valid JSON matching the exact schema provided. "
                    "Give specific, actionable advice tailored to the garment type (ethnic, western, casual, etc.). "
                    "Be concise but useful."
                ),
            },
            {
                "role": "user",
                "content": f"""
Provide styling advice for this outfit:
- Outfit: {req.outfit_description}
- Person type: {req.person_type} {'(child/teen — keep all suggestions age-appropriate and playful)' if req.person_type == 'kid' else ''}
- Gender: {req.gender}
{f'- Age: {req.age} years old' if req.age else ''}
- Skin tone: {req.skin_tone}
- Body build: {req.body_type}
{f'- Height: {req.height_cm} cm' if req.height_cm else ''}
{f'- Weight: {req.weight_kg} kg' if req.weight_kg else ''}
{f'- BMI: {req.bmi}' if req.bmi else ''}

IMPORTANT RULES:
- If person_type is "kid": all suggestions must be age-appropriate, fun, and safe for children. No adult styles.
- If gender is "male": suggest masculine styles, menswear accessories, no female-specific items unless unisex.
- If gender is "female": suggest feminine or unisex styles.
- If gender is "unisex": suggest gender-neutral styles.
- Use age to calibrate: teens (13-17) → trendy/streetwear; young adults (18-30) → fashion-forward; adults (30+) → classic/smart.
- Use BMI to tailor fit advice:
  * BMI < 18.5 → structured, layered looks to add visual fullness
  * BMI 18.5-24.9 → most silhouettes work, suggest trendy cuts
  * BMI 25-29.9 → A-line, empire waist, vertical patterns
  * BMI 30+ → flowy fabrics, monochrome, wrap styles
- Use skin tone to recommend the most flattering colors.

Respond with this exact JSON schema:
{{
  "accessories": [
    {{
      "item": "item name",
      "color": "recommended color",
      "why": "one sentence reason"
    }}
  ],
  "occasions": ["occasion 1", "occasion 2", "occasion 3", "occasion 4"],
  "how_to_wear": ["tip 1", "tip 2", "tip 3"],
  "color_palettes": [
    {{
      "name": "palette name",
      "colors": ["#hexcode1", "#hexcode2", "#hexcode3"],
      "mood": "casual / elegant / bold"
    }}
  ],
  "style_verdict": "one sentence overall styling verdict personalized to their body and skin tone"
}}

Provide 3-5 accessories, 4-5 occasions, 3 how-to-wear tips, 2 color palettes. Use hex color codes in palettes.
""",
            },
        ],
        max_tokens=800,
    )

    import json
    suggestions = json.loads(response.choices[0].message.content)

    return {
        "outfit_description": req.outfit_description,
        "suggestions": suggestions,
    }


# ─────────────────────────────────────────────
# ENDPOINT 4: FETCH PRODUCT IMAGE FROM URL
# ─────────────────────────────────────────────

class FetchProductRequest(BaseModel):
    url: str

# Browser-like headers to avoid 403s from retail sites
SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def is_clothing_image(url: str) -> bool:
    """Filter out icons, logos, tiny images by URL pattern."""
    url_lower = url.lower()
    skip = ["logo", "icon", "sprite", "banner", "badge", "avatar", "star", "rating",
            ".svg", "1x1", "pixel", "track", "spacer", "loading", "placeholder"]
    return not any(s in url_lower for s in skip)

def score_image(url: str, alt: str, width: int, height: int) -> int:
    """Score candidate images — higher = more likely to be the main product image."""
    score = 0
    url_lower = url.lower()
    alt_lower = (alt or "").lower()

    # Size score — larger images are better
    if width >= 400 and height >= 400: score += 30
    elif width >= 200 and height >= 200: score += 15

    # URL signals
    good_url = ["product", "item", "main", "large", "zoom", "detail", "full", "original",
                "dress", "shirt", "cloth", "fashion", "wear", "outfit"]
    score += sum(10 for k in good_url if k in url_lower)

    # Alt text signals
    good_alt = ["dress", "shirt", "pant", "trouser", "jacket", "coat", "top", "skirt",
                "outfit", "wear", "fashion", "cloth", "product"]
    score += sum(8 for k in good_alt if k in alt_lower)

    return score


@app.post("/api/fetch-product")
async def fetch_product(req: FetchProductRequest):
    """
    Scrape a product page (Amazon, Temu, Shein, Myntra, Flipkart, etc.)
    and return the best product image URL + product name.
    """
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")

    # Detect site for site-specific extraction
    domain = url.split("/")[2].lower().replace("www.", "")

    try:
        resp = httpx.get(url, headers=SCRAPE_HEADERS, follow_redirects=True, timeout=15)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch URL: {str(e)}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Site returned {resp.status_code}. Try copying the direct image URL instead."
        )

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── 1. Try Open Graph image (most reliable across all sites) ──
    og_image = soup.find("meta", property="og:image")
    og_title = soup.find("meta", property="og:title")
    product_name = og_title["content"].strip() if og_title and og_title.get("content") else ""

    # ── 2. Try Twitter card image ──
    tw_image = soup.find("meta", attrs={"name": "twitter:image"})

    # ── 3. Site-specific selectors ──
    site_image_url = None

    if "amazon" in domain:
        # Amazon: main product image in #landingImage or #imgBlkFront
        tag = soup.find("img", {"id": ["landingImage", "imgBlkFront", "main-image"]})
        if tag:
            site_image_url = tag.get("data-old-hires") or tag.get("data-src") or tag.get("src")
        if not product_name:
            title_tag = soup.find("span", {"id": "productTitle"})
            if title_tag:
                product_name = title_tag.get_text(strip=True)

    elif "temu" in domain:
        tag = soup.find("img", {"class": re.compile(r"(main|product|hero)", re.I)})
        if tag:
            site_image_url = tag.get("src")

    elif "shein" in domain or "she.in" in domain:
        tag = soup.find("img", {"class": re.compile(r"(main|product|gallery)", re.I)})
        if tag:
            site_image_url = tag.get("src")

    elif "myntra" in domain:
        tag = soup.find("img", {"class": re.compile(r"(main|product|hero|pdp)", re.I)})
        if tag:
            site_image_url = tag.get("src")

    elif "flipkart" in domain:
        tag = soup.find("img", {"class": re.compile(r"(main|product|_396cs4|DByuf4)", re.I)})
        if tag:
            site_image_url = tag.get("src")

    # ── 4. Fallback: score all img tags ──
    best_url = site_image_url
    if not best_url and og_image and og_image.get("content"):
        best_url = og_image["content"]
    if not best_url and tw_image and tw_image.get("content"):
        best_url = tw_image["content"]

    if not best_url:
        # Score all images and pick best
        candidates = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
            if not src or not src.startswith("http"):
                src = img.get("data-original") or ""
            if not src or len(src) < 10:
                continue
            if not is_clothing_image(src):
                continue
            try:
                w = int(img.get("width", 0))
                h = int(img.get("height", 0))
            except (ValueError, TypeError):
                w, h = 0, 0
            alt = img.get("alt", "")
            score = score_image(src, alt, w, h)
            candidates.append((score, src))

        if candidates:
            candidates.sort(reverse=True)
            best_url = candidates[0][1]

    if not best_url:
        raise HTTPException(
            status_code=404,
            detail="Could not find a product image on this page. Try pasting the image URL directly."
        )

    # Ensure URL is absolute
    if best_url.startswith("//"):
        best_url = "https:" + best_url

    # Auto-detect product name from page title if still missing
    if not product_name:
        title_tag = soup.find("title")
        if title_tag:
            product_name = title_tag.get_text(strip=True).split("|")[0].split("-")[0].strip()

    return {
        "image_url": best_url,
        "product_name": product_name,
        "source_domain": domain,
    }


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "services": ["generate", "tryon", "style"]}


@app.get("/debug/replicate")
def debug_replicate():
    """Check if Replicate token is valid and account has billing set up."""
    resp = httpx.get(
        "https://api.replicate.com/v1/account",
        headers=REPLICATE_HEADERS,
    )
    if resp.status_code == 200:
        data = resp.json()
        return {"status": "ok", "username": data.get("username"), "type": data.get("type")}
    return {"status": "error", "code": resp.status_code, "detail": resp.text}
