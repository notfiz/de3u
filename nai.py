import requests

api_key = ''

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
    },
}