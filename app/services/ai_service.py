import base64
import json
import os
from io import BytesIO

import google.generativeai as genai
import requests
from dotenv import load_dotenv
from PIL import Image
from typing_extensions import TypedDict

load_dotenv()


class DetectedObjectSchema(TypedDict):
    name: str
    bounding_boxes: list[int]


class DetectedObjectListSchema(TypedDict):
    objects: list[DetectedObjectSchema]


def resize_and_compress_image(image_path, max_width=1000, quality=95):
    """Resize and compress the input image."""
    with Image.open(image_path) as img:
        image = img

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Calculate new dimensions
        width, height = image.size
        if width > max_width:
            height = int((height * max_width) / width)
            width = max_width

        # Resize image
        image = image.resize((width, height), Image.Resampling.LANCZOS)

        # Save compressed image to BytesIO
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)

        return buffer


def extract_bounding_boxes(
    image_url: str,
    document_contents: dict[str, str],
    system_prompt: str,
    assistant_prompt: str,
) -> DetectedObjectListSchema:
    gemini_api_key = os.getenv('GOOGLE_API_KEY')
    model_name = 'gemini-1.5-pro-latest'

    if not gemini_api_key:
        raise ValueError('Please set GOOGLE_API_KEY in the .env file')

    image_path = 'image.jpg'
    with open(image_path, 'wb') as f:
        response = requests.get(image_url)
        f.write(response.content)

    image_buffer = resize_and_compress_image(image_path)
    image_data = base64.b64encode(image_buffer.getvalue()).decode('utf-8')

    # Create the image part for gemini request
    image_part = {'mime_type': 'image/jpeg', 'data': image_data}

    prompt = assistant_prompt

    # Add the document contents to the prompt
    for key, value in document_contents.items():
        prompt += (
            '\n\n<document>'
            f'<name>{key}</name>'
            f'<content>{value}</content>'
            '</document>'
        )

    contents = [
        {'inline_data': image_part},
        {'text': prompt},
    ]

    # Initialize the model
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )

    # Generate response
    response = model.generate_content(
        contents,
        generation_config=genai.GenerationConfig(
            response_mime_type='application/json',
            response_schema=DetectedObjectListSchema,
            temperature=0.05,
        ),
    )

    # Return decoded json
    return json.loads(response.text)
