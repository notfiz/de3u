import gradio as gr
import requests
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
import io
import os
import matplotlib
import json
import datetime
import threading
import webbrowser

image_sizes = ['1024x1024', '1024x1792', '1792x1024']
openai_url = 'https://api.openai.com/v1/images/generations'
config = 'config.json'
output = 'output'

matplotlib.use('Agg')
os.makedirs(output, exist_ok=True)

cancel = False
cancel_event = threading.Event()


def load_config():
    if os.path.exists(config):
        with open(config, 'r') as file:
            data = json.load(file)
            api_key = data.get('api_key', '')
            total_spent = float(data.get('total_spent', 0))
            proxy_url = data.get('proxy_url', '')
            return api_key, total_spent, proxy_url
    return '', 0, ''


def save_config(api, total, proxy_url):
    with open(config, 'w') as file:
        json.dump({'api_key': api, 'total_spent': f"{total:.2f}", 'proxy_url': proxy_url}, file)
        file.flush()


def generate_text(text, width=1000, height=250, color='black', font_color='white'):
    img = Image.new('RGB', (width, height), color=color)
    draw = ImageDraw.Draw(img)
    font_size = 50
    font_path = 'arial.ttf'

    try:
        font = ImageFont.truetype(font_path, size=font_size)
    except IOError:
        font = ImageFont.load_default()

    text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
    while text_width > img.width - 20:
        font_size -= 1
        if font_size <= 5:
            return generate_text("none")
        font = ImageFont.truetype(font_path, size=font_size)
        text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]

    x = (img.width - text_width) / 2
    y = (img.height - text_height) / 2
    draw.text((x, y), text, font=font, fill=font_color)
    return img


def calculate_price(size, hd, count=1):
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
    return price * count


def get_metadata(img):
    metadata_str = ""
    if img is None:
        return "No image provided."
    generation_info_raw = img.info.get("generation_info", "")
    revised_prompt = img.info.get("revised_prompt", "")
    try:
        if generation_info_raw:
            generation_info = json.loads(generation_info_raw)
            metadata_str += "Generation Info:\n"
            for key, value in generation_info.items():
                metadata_str += f"{key}: {value}\n"
        else:
            metadata_str += "No generation info found.\n"
    except json.JSONDecodeError:
        # older/unsupported generation info
        metadata_str += generation_info_raw + "\n"

    if revised_prompt:
        metadata_str += "\n\nRevised Prompt:\n" + revised_prompt
    else:
        metadata_str += "\n\nNo revised prompt found."

    return metadata_str


def cancel_toggle():
    global cancel_event
    if not cancel_event.is_set():
        print("Canceling... please wait")
        cancel_event.set()


def show_output():
    webbrowser.open(output)


def request_dalle(url, api_key, prompt, hd, size, style):
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


def generate_image(proxy_url, api_key, prompt, hd, jb, size, style):
    proxy = False
    print("generating...")
    if jb:
        # openai docs
        prompt = "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS: " + prompt

    if proxy_url == '':
        status, response = request_dalle(openai_url, api_key, prompt, hd, size, style)
    else:
        proxy = True
        proxy_url = proxy_url.rstrip("/")
        proxy_url += '/v1/images/generations'
        status, response = request_dalle(proxy_url, api_key, prompt, hd, size, style)

    if status is None:
        print(f"Error: {response}")
        return generate_text("connection issue"), response, False

    if status == 200:
        revised_prompt = response['data'][0].get('revised_prompt', 'No revised prompt provided.')
        image_url = response['data'][0]['url']
        try:
            print("generated. downloading...")
            image_response = requests.get(image_url, timeout=180)
            image_response.raise_for_status()
            image_bytes = image_response.content
            image = Image.open(io.BytesIO(image_bytes))
        except requests.RequestException as e:
            print(f"Error fetching image from URL: {e}\n URL:{image_url}\n the image might still be retrievable manually by pasting the URL in a browser. the metadata will NOT be saved.")
            return generate_text("Error fetching image"), str(e), False
        # metadata stuff
        metadata = PngImagePlugin.PngInfo()
        generation_info_data = {
            "prompt": prompt,
            "size": size,
            "hd": hd,
            "style": style,
        }
        metadata.add_text("generation_info", json.dumps(generation_info_data))
        metadata.add_text("revised_prompt", revised_prompt)
        buffer = io.BytesIO()
        image.save(buffer, "PNG", pnginfo=metadata)
        buffer.seek(0)
        img_final = Image.open(buffer)
        # saving stuff
        folder_path = os.path.join(output, datetime.datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(folder_path, exist_ok=True)

        file_number = 0
        file_path = os.path.join(folder_path, f"img_{file_number}.png")
        while os.path.exists(file_path):
            file_number += 1
            file_path = os.path.join(folder_path, f"img_{file_number}.png")
        img_final.save(file_path, "PNG", pnginfo=metadata)

        print("success.")
        return img_final, revised_prompt, True

    # this is just hell. all of these needs to be refactored
    elif status == 401:
        print("Invalid API key.")
        return generate_text("Invalid API key"), "Invalid API key.", False

    # text: Your request was rejected as a result of our safety system. Your prompt may contain text that is not allowed by our safety system.
    # image: This request has been blocked by our content filters.
    elif status == 400 or status == 429:
        if 'error' not in response:
            return generate_text("error"), response, False
        error_message = response['error']['message']
        # filtered
        if response['error']['code'] == "content_policy_violation":
            if "Your prompt may contain text" in error_message and not proxy:
                print("Filtered by text moderation. You need to modify your prompt.")
            elif "Image descriptions generated" in error_message and not proxy:
                print("Filtered by image moderation. Your request may succeed if retried.")
            else:
                print(f"Filtered. {error_message}")
            return generate_text("Filtered"), error_message, False

        # rate limited or quota issue
        print(f"{error_message}")
        return generate_text(f"{error_message}"), f"{error_message}", False

    elif response['error'] == 'Not found':
        return generate_text("Reverse proxy not found"), f"Reverse proxy not found {response}", False

    else:
        print(f"Unknown error: {response}")
        return generate_text("Unknown Error"), f"{response}", False


def main(proxy_url, api_key, prompt, hd, jb, size, style, count):
    images = []
    revised_prompts = ""
    count = int(count)
    price = 0
    if cancel:
        cancel_toggle()

    for i in range(count):
        if cancel:
            print("Operation cancelled.")
            cancel_toggle()
            break

        img_final, revised_prompt, success = generate_image(proxy_url, api_key, prompt, hd, jb, size, style)
        images.append(img_final)
        revised_prompts += f"{i + 1}- {revised_prompt}\n"
        if success:
            price += calculate_price(size, hd)

    _, total, _ = load_config()
    total += price
    save_config(api_key, total, proxy_url)
    print("Done.")
    return images, revised_prompts, f"price for this batch:${price:.2f}, total generated:${total:.2f}"


with gr.Blocks(title="de3u") as instance:
    gr.Markdown("# de3u")
    tab_main = gr.TabItem("Image generator")
    tab_metadata = gr.TabItem("Image Metadata")
    with tab_main:
        with gr.Row():
            with gr.Column():
                proxy_url_input = gr.Textbox(label="Reverse proxy Link", placeholder="Enter reverse proxy link if needed", value=load_config()[2])
                api_key_input = gr.Textbox(label="API Key", placeholder="Enter your API key", type="password", value=load_config()[0])
                prompt_input = gr.Textbox(label="Prompt", placeholder="Enter your prompt")
                hd_input = gr.Checkbox(label="HD")
                jb_input = gr.Checkbox(label="JB", info="makes the ai less likely to change your input. more likely to get filtered. useful if you are using an already revised prompt.")
                size_input = gr.Dropdown(label="Size", choices=image_sizes, value=image_sizes[0], allow_custom_value=False)
                style_input = gr.Radio(label="Style", choices=['vivid', 'natural'], value='vivid')
                with gr.Row():
                    generate_button = gr.Button("Generate")
                    cancel_button = gr.Button("Cancel")
                    num_images_input = gr.Number(label="Number of Images", value=1, step=1, minimum=1, interactive=True)
            with gr.Column():
                image_output = gr.Gallery()
                revised_prompt_output = gr.Textbox(label="Revised Prompt", lines=10)
                price_output = gr.Textbox(label="Price")
                output_button = gr.Button("Show Output Folder")
    with tab_metadata:
        with gr.Row():
            metadata_image = gr.Image(type="pil", width=500, height=500, sources=["upload", "clipboard"])
            metadata_output = gr.Textbox(label="Metadata", interactive=False)

    metadata_image.change(
        fn=get_metadata,
        inputs=[metadata_image],
        outputs=[metadata_output],
        show_progress="hidden"
    )
    generate_button.click(
        fn=main,
        inputs=[proxy_url_input, api_key_input, prompt_input, hd_input, jb_input, size_input, style_input, num_images_input],
        outputs=[image_output, revised_prompt_output, price_output]
    )
    cancel_button.click(
        fn=cancel_toggle
    )
    output_button.click(
        fn=show_output
    )

instance.launch(inbrowser=True)
