import gradio as gr
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import matplotlib

image_sizes = ['1024x1024', '1024x1792', '1792x1024']
api_url = 'https://api.openai.com/v1/images/generations'

matplotlib.use('Agg')


def generate_error_image(error_text):
    img_width = 400
    img_height = 100
    img = Image.new('RGB', (img_width, img_height), color='black')
    draw = ImageDraw.Draw(img)
    font_size = 20
    font_path = 'arial.ttf'

    try:
        font = ImageFont.truetype(font_path, size=font_size)
    except IOError:
        font = ImageFont.load_default()
    text_width, text_height = draw.textbbox((0, 0), error_text, font=font)[2:]

    while text_width > img_width:
        font_size -= 1
        if font_size <= 5:
            raise ValueError(f"Text({error_text}) cannot be accommodated, even with the smallest font size.")
        font = ImageFont.truetype(font_path, size=font_size)
        text_width, text_height = draw.textbbox((0, 0), error_text, font=font)[2:]

    text_x = (img_width - text_width) // 2
    text_y = (img_height - text_height) // 2

    draw.text((text_x, text_y), error_text, font=font, fill='white')
    return img


def generate_image(api_key, prompt, hd, size, style):
    print("generating...")
    try:

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
        response = requests.post(api_url, json=data, headers=headers)
        response_json = response.json()

        if response.status_code == 200:
            b64_content = response_json['data'][0]['b64_json']
            revised_prompt = response_json['data'][0].get('revised_prompt', 'No revised prompt provided.')

            # output is in base64 format we need to convert it
            image_bytes = base64.b64decode(b64_content)
            image = Image.open(io.BytesIO(image_bytes))
            return image, revised_prompt

        elif response.status_code == 401:
            return generate_error_image("Invalid API key."), "Invalid API key."

        elif response.status_code == 400 or response.status_code == 429:
            error_message = response_json['error']['message']
            if response_json['error']['code'] == "content_policy_violation":
                print(f"Filtered.")
                return generate_error_image("Filtered"), error_message
            else:
                print(f"Error: {error_message}")
                return generate_error_image(f"{error_message}"), f"{error_message}"

        else:
            print(f"Failed to generate image: {response.text}")
            return generate_error_image(f"Unknown Error"), f"{response.text}"

    # this should never get triggered but you never know
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(e)
        return generate_error_image("An unexpected error occurred")


iface = gr.Interface(
    fn=generate_image,
    inputs=[
        gr.Textbox(label="API Key", placeholder="Enter your API key here...", type="password"),
        gr.Textbox(label="Prompt", placeholder="Enter your prompt here..."),
        gr.Checkbox(label="HD mode"),
        gr.Dropdown(label="Size", choices=image_sizes, value=image_sizes[0]),
        gr.Radio(label="Style", choices=['vivid', 'natural'], value='vivid')
    ],
    outputs=[
        gr.Image(),
        gr.Textbox(label="Revised Prompt")],
    title="de3u",
)

# Run the Gradio app
iface.launch()
