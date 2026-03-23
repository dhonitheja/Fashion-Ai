import os
import re
import time
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup

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
                    "studio lighting, fashion editorial photography style, 4k quality. "
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

    # Step 3: Poll until done
    result = poll_replicate(prediction_id)
    image_url = result["output"][0] if isinstance(result["output"], list) else result["output"]

    return {
        "image_url": image_url,
        "enriched_prompt": enriched,
        "negative_prompt": negative_prompt,
        "original_description": req.description,
        "prediction_id": prediction_id,
    }


# ─────────────────────────────────────────────
# ENDPOINT 2: PHOTO + OUTFIT → VIRTUAL TRY-ON (Nanobanana)
# ─────────────────────────────────────────────

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


@app.post("/api/tryon")
async def virtual_tryon(
    person_photo: UploadFile = File(..., description="Full body photo of the person"),
    outfit_url: str = Query(..., description="Public URL of the outfit image"),
):
    """
    Takes a person photo + outfit image URL.
    Uploads person photo to a temp host, then sends both URLs to Nanobanana for try-on.
    """
    person_bytes = await person_photo.read()

    # Step 1: Upload person photo to catbox.moe (free anonymous hosting) to get a public URL.
    # Nanobanana requires real public URLs — it cannot accept base64 data URIs.
    upload_resp = httpx.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": (person_photo.filename or "photo.jpg", person_bytes, person_photo.content_type or "image/jpeg")},
        timeout=30,
    )

    if upload_resp.status_code != 200 or not upload_resp.text.startswith("https://"):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload person photo for try-on: {upload_resp.text[:200]}"
        )

    person_image_url = upload_resp.text.strip()

    # Step 2: Submit try-on to Nanobanana
    resp = httpx.post(
        "https://api.nanobananaapi.ai/api/v1/nanobanana/generate",
        headers=NANOBANANA_HEADERS,
        json={
            "prompt": (
                "Virtual fashion try-on: place the garment from Reference Image 2 onto the person "
                "in Reference Image 1. Preserve the person's face, body, and pose exactly. "
                "Make the clothing fit realistically with natural fabric drape and lighting."
            ),
            "type": "IMAGETOIAMGE",  # Nanobanana API typo — this is their actual enum value
            "numImages": 1,
            "imageUrls": [person_image_url, outfit_url],
            "callBackUrl": "https://webhook.site/noop",  # required field; we poll instead
            "watermark": False,
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Nanobanana submit failed: {resp.text}")

    resp_data = resp.json()
    # taskId may be at top level or nested under "data"
    task_id = (
        resp_data.get("taskId")
        or (resp_data.get("data") or {}).get("taskId")
    )
    if not task_id:
        raise HTTPException(status_code=500, detail=f"No taskId in response: {resp.text}")

    # Step 3: Poll until done
    result_url = poll_nanobanana(task_id, timeout=180)

    return {
        "result_url": result_url,
        "task_id": task_id,
    }


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
