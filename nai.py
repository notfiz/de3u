import requests

api_key = ''


def generate_image(input_text, width, height, steps, guidance_scale, negative_prompt):
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    payload_data = {
        "input": input_text,
        "model": "nai-diffusion-3",
        "action": "generate",
        "parameters": {
            "width": width,
            "height": height,
            "steps": steps,
            "sampler": "k_euler",
            "guidance": guidance_scale,
            "negative_prompt": negative_prompt if negative_prompt else "",
        },
    }
