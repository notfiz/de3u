import gradio as gr
import os
import matplotlib
import json
import threading
import webbrowser
import utils, oai

oai_sizes = ['1024x1024', '1024x1792', '1792x1024']
nai_sizes = ['832x1216', '1216x832', '1024x1024', '1536x1024', '1472x1472', '1088x1920', '1920x1088', '512x768', '768x512', '640x640']
nai_samplers = ['Euler', 'Euler Ancestral', 'DPM++ 2S Ancestral', 'DPM++ 2M', 'DDIM']
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


def oai_main(proxy_url, api_key, prompt, hd, jb, size, style, count):
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
    tab_oai = gr.TabItem("Dall-e Generator")
    tab_nai = gr.TabItem("Nai Generator")
    tab_metadata = gr.TabItem("Image Metadata")
    tab_history = gr.TabItem("Image History")
    with tab_oai:
        with gr.Row():
            with gr.Column():
                oai_proxy_url = gr.Textbox(label="Reverse proxy Link", placeholder="Enter reverse proxy link if needed", value=load_config()[2])
                oai_api_key = gr.Textbox(label="API Key", placeholder="Enter your API key", type="password", value=load_config()[0])
                oai_prompt = gr.Textbox(label="Prompt", placeholder="Enter your prompt", lines=3)
                oai_hd = gr.Checkbox(label="HD")
                oai_jb = gr.Checkbox(label="JB", info="makes the ai less likely to change your input. more likely to get filtered. useful if you are using an already revised prompt.")
                oai_size = gr.Dropdown(label="Size", choices=oai_sizes, value=oai_sizes[0], allow_custom_value=False)
                oai_style = gr.Radio(label="Style", choices=['vivid', 'natural'], value='vivid')
                with gr.Row():
                    oai_generate_button = gr.Button("Generate")
                    oai_cancel_button = gr.Button("Cancel")
                    oai_num_images_input = gr.Number(label="Number of Images", value=1, step=1, minimum=1, interactive=True)
            with gr.Column():
                oai_image_output = gr.Gallery(label="Generated Images")
                oai_revised_prompt_output = gr.Textbox(label="Revised Prompt", lines=10)
                oai_price_output = gr.Textbox(label="Price")
                oai_output_button = gr.Button("Show Output Folder")
    with tab_nai:
        with gr.Row():
            with gr.Column():
                nai_api_key = gr.Textbox(label="API Key", placeholder="Enter your API key", type="password")
                nai_prompt = gr.Textbox(label="Prompt", placeholder="Enter your prompt", lines=3)
                nai_neg_prompt = gr.Textbox(label="Undesired Content", placeholder="Enter your negative prompt", lines=3)
                nai_size = gr.Dropdown(label="Size", choices=nai_sizes, value=nai_sizes[0], allow_custom_value=False, interactive=True)
                with gr.Row():
                    nai_steps = gr.Slider(label="Steps", value=28, step=1, minimum=1, maximum=50, interactive=True)
                    nai_guide = gr.Slider(label="Prompt Guidance", value=5, step=0.1, minimum=0, maximum=10, interactive=True)
                    nai_sampler = gr.Dropdown(label="Sampler", choices=nai_samplers, value=nai_samplers[0], interactive=True)
                with gr.Row():
                    nai_generate = gr.Button()
            with gr.Row():
                nai_gallery = gr.Gallery()

    with tab_metadata:
        with gr.Row():
            metadata_image = gr.Image(type="pil", width=500, height=500, sources=["upload", "clipboard"])
            metadata_output = gr.Textbox(label="Metadata", interactive=False)
    with tab_history:
        with gr.Row():
            history_gallery = gr.Gallery(label="Image History")
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
    oai_generate_button.click(
        fn=oai_main,
        inputs=[oai_proxy_url, oai_api_key, oai_prompt, oai_hd, oai_jb, oai_size, oai_style, oai_num_images_input],
        outputs=[oai_image_output, oai_revised_prompt_output, oai_price_output]
    )
    oai_cancel_button.click(
        fn=cancel_toggle
    )
    oai_output_button.click(
        fn=show_output,
    )

instance.launch(inbrowser=False, show_api=False)
