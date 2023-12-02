import gradio as gr
import os
import matplotlib
import json
import threading
import webbrowser
import utils, oai

image_sizes = ['1024x1024', '1024x1792', '1792x1024']
config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
output = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')

matplotlib.use('Agg')
os.makedirs(output, exist_ok=True)

cancel = False
cancel_event = threading.Event()
image_history = []


def show_output():
    webbrowser.open(output)


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


def cancel_toggle():
    global cancel_event
    if not cancel_event.is_set():
        print("Canceling... please wait")
        cancel_event.set()


def main(proxy_url, api_key, prompt, hd, jb, size, style, count):
    global image_history
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

        img_final, revised_prompt, success = oai.generate_image(proxy_url, api_key, prompt, hd, jb, size, style, cancel_event)
        images.append(img_final)
        revised_prompts += f"{i + 1}- {revised_prompt}\n"
        if success:
            image_history.insert(0, (img_final, prompt))
            image_history = image_history[:10]
            price += utils.calculate_price(size, hd)
            utils.ding()

    _, total, _ = load_config()
    total += price
    save_config(api_key, total, proxy_url)
    print("done.")
    return images, revised_prompts, f"price for this batch:${price:.2f}, total generated:${total:.2f}"


def refresh_history():
    images, prompts = zip(*image_history) if image_history else ([], [])
    return images, "\n".join(prompts)


with gr.Blocks(title="de3u") as instance:
    gr.Markdown("# de3u")
    tab_main = gr.TabItem("Image Generator")
    tab_metadata = gr.TabItem("Image Metadata")
    tab_history = gr.TabItem("Image History")
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
    with tab_history:
        with gr.Row():
            history_gallery = gr.Gallery(label="Image History", )
            history_prompts = gr.Textbox(label="Prompts", lines=10, interactive=False)

    tab_history.select(
        fn=refresh_history,
        inputs=[],
        outputs=[history_gallery, history_prompts],
        show_progress="hidden"
    )
    metadata_image.change(
        fn=utils.get_metadata,
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
        fn=show_output,
    )

instance.launch(inbrowser=True, show_api=False)
