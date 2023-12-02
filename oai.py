import requests
import threading
from PIL import Image
import io
import os
import datetime
import error_handler, utils

openai_url = 'https://api.openai.com/v1/images/generations'
output = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')


def request_dalle(url, api_key, prompt, hd, size, style, cancel_event):
    cancel_event.clear()
    response_container = {'status': None, 'response': None}

    def request_thread(u, d, h, r):
        try:
            response = requests.post(u, json=d, headers=h)
            r['status'] = response.status_code
            r['response'] = response.json()
        except Exception as e:
            r['status'] = None
            r['response'] = e

    data = {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": size,
        "quality": "hd" if hd else "standard",
        "style": style if style else "vivid",
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    thread = threading.Thread(target=request_thread, args=(url, data, headers, response_container))
    thread.start()
    while thread.is_alive():
        if cancel_event.is_set():
            print("Cancellation requested.")
            break
        thread.join(timeout=0.1)

    if cancel_event.is_set():
        return None, "Operation was cancelled by the user."
    else:
        return response_container['status'], response_container['response']


def generate_image(proxy_url, api_key, prompt, hd, jb, size, style, cancel_event):
    proxy = False
    print("generating...")
    if jb:
        # openai docs
        prompt = "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS: " + prompt

    if proxy_url == '':
        status, response = request_dalle(openai_url, api_key, prompt, hd, size, style, cancel_event)
    else:
        proxy = True
        proxy_url = proxy_url.rstrip("/")
        proxy_url += '/v1/images/generations'
        status, response = request_dalle(proxy_url, api_key, prompt, hd, size, style, cancel_event)

    if status is None:
        error_message, success = error_handler.handle_connection(response)
        return utils.generate_text(error_message), error_message, success

    if status == 200:
        revised_prompt = response['data'][0].get('revised_prompt', 'No revised prompt provided.')
        image_url = response['data'][0]['url']
        try:
            print(f"generated:{image_url} downloading...")
            image_response = requests.get(image_url, timeout=200)
            image_response.raise_for_status()
            image_bytes = image_response.content
            image = Image.open(io.BytesIO(image_bytes))
        except requests.RequestException as e:
            print(f"Error fetching image from URL: {e}\n URL:{image_url}\n the image might still be retrievable manually by pasting the URL in a browser. the metadata will NOT be saved.")
            return utils.generate_text("error fetching image"), str(e), False
        # metadata stuff
        generation_info_data = {
            "prompt": prompt,
            "size": size,
            "hd": hd,
            "style": style,
        }
        img_final, metadata = utils.add_metadata(image, generation_info_data, revised_prompt)

        # saving stuff
        folder_path = os.path.join(output, datetime.datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(folder_path, exist_ok=True)
        file_number = 0
        file_path = os.path.join(folder_path, f"img_{file_number}.png")
        while os.path.exists(file_path):
            file_number += 1
            file_path = os.path.join(folder_path, f"img_{file_number}.png")
        img_final.save(file_path, "PNG", pnginfo=metadata)

        print("Success.")
        return img_final, revised_prompt, True

    else:
        error_message, success = error_handler.handle_openai(status, response, proxy, cancel_event)
        return utils.generate_text(error_message), error_message, success
