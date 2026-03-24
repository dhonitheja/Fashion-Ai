import requests
from PIL import Image
import io

# Create a valid local image
img = Image.new('RGB', (200, 200), color = 'red')
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='JPEG')
img_bytes = img_byte_arr.getvalue()

url = 'http://localhost:8000/api/tryon?outfit_url=https://via.placeholder.com/200'
files = {'person_photo': ('photo.jpg', img_bytes, 'image/jpeg')}

try:
    resp = requests.post(url, files=files, timeout=60)
    with open('test_output2.txt', 'w') as f:
        f.write(resp.text)
except Exception as e:
    with open('test_output2.txt', 'w') as f:
        f.write(str(e))
