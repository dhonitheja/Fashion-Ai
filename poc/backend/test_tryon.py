import requests

url = 'http://localhost:8000/api/tryon?outfit_url=https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png'

# Send a valid image (e.g. from the web)
image_resp = requests.get('https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png')
files = {'person_photo': ('photo.png', image_resp.content, 'image/png')}

try:
    resp = requests.post(url, files=files, timeout=60)
    with open('test_output.txt', 'w') as f:
        f.write(resp.text)
except Exception as e:
    with open('test_output.txt', 'w') as f:
        f.write(str(e))
