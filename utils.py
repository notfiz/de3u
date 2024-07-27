from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
import json
import io
import os
import argparse
import platform


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


def add_metadata(img, generation_info, revised_prompt):
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("generation_info", json.dumps(generation_info))
    metadata.add_text("revised_prompt", revised_prompt)
    buffer = io.BytesIO()
    img.save(buffer, "PNG", pnginfo=metadata)
    buffer.seek(0)
    img_final = Image.open(buffer)
    return img_final, metadata


def get_path(path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


def parse_arguments():
    parser = argparse.ArgumentParser(description="DALL-E 3 Image Generator")
    parser.add_argument('--no-browser', '-nb', action='store_true',
                        help="Don't open the browser automatically", default=False)
    parser.add_argument('--port', '-p', type=int, default=7860,
                        help="Port to run the Gradio app on")
    parser.add_argument('--debug', '-d', action='store_true',
                        help="Run in debug mode")
    parser.add_argument('--no-sound', '-ns', action='store_true',
                        help="Disable sound effects")
    return parser.parse_args()


def play_sound(sound_path, no_sound):
    if no_sound:
        return
    if platform.system() == 'Windows':
        import winsound
        winsound.PlaySound(sound_path, winsound.SND_FILENAME)
    elif os.name == 'posix':
        import sys
        sys.stdout.write('\a\n')
    else:
        print("Sound playback is not supported on this platform. consider using the --no-sound flag")
