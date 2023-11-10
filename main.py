import gradio as gr
import requests
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
import io
import base64
import matplotlib
import os
import json

image_sizes = ['1024x1024', '1024x1792', '1792x1024']
api_url = 'https://api.openai.com/v1/images/generations'
config = 'config.json'

matplotlib.use('Agg')


def load_config():
    if os.path.exists(config):
        with open(config, 'r') as file:
            data = json.load(file)
            return data.get('api_key', ''), data.get('total_spent', 0)
    return '', 0


def save_config(api, total):
    with open(config, 'w') as file:
        json.dump({'api_key': api, 'total_spent': f"{total:.2f}"}, file)
        file.flush()


def generate_text(text):
    width = 400
    height = 100
    img = Image.new('RGB', (width, height), color='black')
    draw = ImageDraw.Draw(img)
    font_size = 20
    font_path = 'arial.ttf'

    try:
        font = ImageFont.truetype(font_path, size=font_size)
    except IOError:
        font = ImageFont.load_default()
    width, height = draw.textbbox((0, 0), text, font=font)[2:]

    while width > width:
        font_size -= 1
        if font_size <= 5:
            generate_text("none")
        font = ImageFont.truetype(font_path, size=font_size)
        width, height = draw.textbbox((0, 0), text, font=font)[2:]

    x = (img.width - width) // 2
    y = (img.height - height) // 2

    draw.text((x, y), text, font=font, fill='white')
    return img


def calculate_price(size, hd):
    prices = {
        '1024x1024': 0.04,
        '1024x1792': 0.08,
        '1792x1024': 0.08
    }
    hd_prices = {
        '1024x1024': 0.08,
        '1024x1792': 0.12,
        '1792x1024': 0.12
    }
    price = hd_prices[size] if hd else prices[size]
    return price


def request_dalle(api_key, prompt, hd, size, style):
    data = {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": size,
        "quality": "hd" if hd else "standard",
        "style": style if style else "vivid",
        "response_format": "b64_json"
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    try:
        response = requests.post(api_url, json=data, headers=headers)
        return response.status_code, response.json()
    except Exception as e:
        print("error:", e)
        return None, e


def generate_image(api_key, prompt, hd, size, style):
    print("generating...")
    status, response = request_dalle(api_key, prompt, hd, size, style)

    if status is None:
        return generate_text("connection issue"), response, 0

    if status == 200:
        b64_content = response['data'][0]['b64_json']
        revised_prompt = response['data'][0].get('revised_prompt', 'No revised prompt provided.')
        image_bytes = base64.b64decode(b64_content)
        image = Image.open(io.BytesIO(image_bytes))
        # metadata stuff
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("generation_info", f"prompt:{prompt}, hd:{hd}, style:{style}")
        metadata.add_text("revised_prompt", revised_prompt)
        buffer = io.BytesIO()
        image.save(buffer, "PNG", pnginfo=metadata)
        buffer.seek(0)
        img_final = Image.open(buffer)
        # price calculations
        price = calculate_price(size, hd)
        _, total = load_config()
        total += price
        save_config(api_key, total)
        return img_final, revised_prompt, f"${price:.2f}, total:${total:.2f}"

    elif status == 401:
        return generate_text("Invalid API key"), "Invalid API key.", 0

    elif status == 400 or status == 429:
        error_message = response['error']['message']
        # filtered
        if response['error']['code'] == "content_policy_violation":
            print(f"Filtered.")
            return generate_text("Filtered"), error_message, 0
        # rate limited or quota issue
        print(f"Error: {error_message}")
        return generate_text(f"{error_message}"), f"{error_message}", 0

    else:
        print(f"Unknown error: {response}")
        return generate_text(f"Unknown Error"), f"{response}", 0


# this function is stupid for now but will be useful later
def main(api_key, prompt, hd, size, style):
    img_final, revised_prompt, price_info = generate_image(api_key, prompt, hd, size, style)
    return img_final, revised_prompt, price_info


with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            api_key_input = gr.Textbox(label="API Key", placeholder="Enter your API key here...", type="password",
                                       value=load_config()[0])
            prompt_input = gr.Textbox(label="Prompt", placeholder="Enter your prompt here...")
            hd_input = gr.Checkbox(label="HD mode")
            size_input = gr.Dropdown(label="Size", choices=image_sizes, value=image_sizes[0])
            style_input = gr.Radio(label="Style", choices=['vivid', 'natural'], value='vivid')
            generate_button = gr.Button("Generate")
        with gr.Column():
            image_output = gr.Image()
            revised_prompt_output = gr.Textbox(label="Revised Prompt")
            price_output = gr.Textbox(label="Price")

    generate_button.click(
        fn=main,
        inputs=[api_key_input, prompt_input, hd_input, size_input, style_input],
        outputs=[image_output, revised_prompt_output, price_output]
    )

demo.launch()
