from PIL import Image, ImageDraw, ImageFont
import json
import webbrowser


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


def show_output(output):
    webbrowser.open(output)