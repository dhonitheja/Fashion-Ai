import sys
import io
import asyncio
from fastapi import UploadFile
from PIL import Image
from main import virtual_tryon

async def test():
    img = Image.new('RGB', (200, 200), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    upload_file = UploadFile(filename="photo.jpg", file=io.BytesIO(img_bytes), headers={"content-type": "image/jpeg"})
    
    outfit_url = "https://via.placeholder.com/200"
    try:
        res = await virtual_tryon(upload_file, outfit_url)
        print("SUCCESS:", res)
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == "__main__":
    asyncio.run(test())
