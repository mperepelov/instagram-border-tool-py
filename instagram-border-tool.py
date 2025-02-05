import gradio as gr
from PIL import Image
import io
import re
import tempfile
import os
import numpy as np
import time
from functools import partial

def parse_color(color_str):
    """Parse various color formats to RGB tuple"""
    try:
        # Handle rgba format
        rgba_match = re.match(r'rgba?\((\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)', color_str)
        if rgba_match:
            return tuple(int(float(x)) for x in rgba_match.groups())
        # Handle hex format
        elif color_str.startswith('#'):
            return tuple(int(color_str[i:i+2], 16) for i in (1, 3, 5))
        return (255, 255, 255)  # Default to white
    except Exception:
        return (255, 255, 255)  # Return white if parsing fails

def resize_for_preview(image, max_size=800):
    """Resize image for preview while maintaining aspect ratio"""
    try:
        width, height = image.size
        if width > max_size or height > max_size:
            ratio = min(max_size/width, max_size/height)
            new_size = (int(width * ratio), int(height * ratio))
            return image.resize(new_size, Image.Resampling.LANCZOS)
        return image
    except Exception as e:
        print(f"Error in resize_for_preview: {e}")
        return image

def add_borders(image, border_color, aspect_ratio, is_preview=False):
    try:
        if image is None:
            return None, None
            
        # Convert numpy array to PIL Image if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image.astype('uint8'))
        
        # Parse the color
        border_color = parse_color(border_color)
        
        # Instagram aspect ratios
        INSTAGRAM_RATIOS = {
            "1:1 (Square)": (1, 1),
            "4:5 (Portrait)": (4, 5),
            "16:9 (Landscape)": (16, 9)
        }
        
        # Get target ratio
        target_ratio = INSTAGRAM_RATIOS[aspect_ratio]
        target_ratio_value = target_ratio[0] / target_ratio[1]
        
        # Get original dimensions
        orig_width, orig_height = image.size
        orig_ratio = orig_width / orig_height
        
        # Calculate new dimensions
        if orig_ratio > target_ratio_value:
            new_width = orig_width
            new_height = int(orig_width / target_ratio_value)
        else:
            new_height = orig_height
            new_width = int(orig_height * target_ratio_value)
        
        # Create new image with border color
        new_image = Image.new('RGB', (new_width, new_height), border_color)
        
        # Calculate position to paste original image
        paste_x = (new_width - orig_width) // 2
        paste_y = (new_height - orig_height) // 2
        
        # Paste original image
        new_image.paste(image, (paste_x, paste_y))
        
        if is_preview:
            # For preview, resize to smaller size and use lower quality
            new_image = resize_for_preview(new_image)
            return new_image, None
        else:
            # For download, save at full quality
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "processed_image.jpg")
            new_image.save(temp_path, format='JPEG', quality=100)
            return new_image, temp_path
    except Exception as e:
        print(f"Error in add_borders: {e}")
        return None, None

last_update_time = 0
update_interval = 0.1  # 100ms debounce

def process_preview(input_image, border_color, aspect_ratio):
    """Handle preview updates with debouncing"""
    global last_update_time
    
    try:
        current_time = time.time()
        if current_time - last_update_time < update_interval:
            return None
        
        last_update_time = current_time
        
        if input_image is None:
            return None
            
        preview_image, _ = add_borders(input_image, border_color, aspect_ratio, is_preview=True)
        return preview_image
    except Exception as e:
        print(f"Error in process_preview: {e}")
        return None

def process_download(input_image, border_color, aspect_ratio):
    """Handle final image download"""
    try:
        if input_image is None:
            return None
            
        _, download_path = add_borders(input_image, border_color, aspect_ratio, is_preview=False)
        return download_path
    except Exception as e:
        print(f"Error in process_download: {e}")
        return None

with gr.Blocks() as iface:
    gr.Markdown("# Instagram Border Generator")
    gr.Markdown("Upload an image and add borders to match Instagram aspect ratios. Preview updates automatically as you adjust settings.")
    
    with gr.Row():
        # Left column for inputs
        with gr.Column(scale=1):
            input_image = gr.Image(
                type="numpy",
                label="Upload Image",
                show_label=True
            )
            color_picker = gr.ColorPicker(
                label="Choose Border Color",
                value="#FFFFFF"
            )
            aspect_ratio = gr.Radio(
                choices=["1:1 (Square)", "4:5 (Portrait)", "16:9 (Landscape)"],
                value="1:1 (Square)",
                label="Choose Aspect Ratio"
            )
            gr.Markdown("*Preview updates automatically. Click Generate Download for full quality.*")
        
        # Right column for outputs
        with gr.Column(scale=1):
            preview = gr.Image(label="Preview")
            with gr.Row():
                download_btn = gr.Button("Generate Download", variant="primary")
                clear_btn = gr.Button("Clear")
            download = gr.File(label="Download Processed Image")
    
    # Update preview on any input change with debouncing
    input_components = [input_image, color_picker, aspect_ratio]
    
    for component in input_components:
        component.change(
            fn=process_preview,
            inputs=input_components,
            outputs=preview,
            show_progress=False
        )
    
    # Generate download file when button is clicked
    download_btn.click(
        fn=process_download,
        inputs=input_components,
        outputs=download,
        show_progress=True
    )
    
    # Clear button functionality
    def clear():
        return None, None, None, None
    
    clear_btn.click(
        fn=clear,
        outputs=[input_image, preview, download, color_picker]
    )

if __name__ == "__main__":
    iface.launch()