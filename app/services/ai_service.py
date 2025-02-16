import base64
import json
import os
from abc import ABC, abstractmethod
from io import BytesIO

import google.generativeai as genai
import openai
import requests
from dotenv import load_dotenv
from openai.types.chat import ChatCompletion
from together import Together
from together.types import ChatCompletionResponse
from typing_extensions import TypedDict

# Ensure environment variables are loaded at the very beginning
load_dotenv(override=True)


class DetectedObjectSchema(TypedDict):
    name: str
    bounding_boxes: list[int]


class DetectedObjectListSchema(TypedDict):
    objects: list[DetectedObjectSchema]


class AiService(ABC):
    @abstractmethod
    def extract_bounding_boxes(
        self,
        image_url: str,
        document_contents: dict[str, str],
        system_prompt: str,
        assistant_prompt: str,
    ) -> DetectedObjectListSchema:
        pass

    @staticmethod
    def resize_and_compress_image(
        image_path: str,
        max_width: int = 1000,
        quality: int = 95,
    ) -> BytesIO:
        from PIL import Image  # noqa: PLC0415

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


class TogetherAiService(AiService):
    def __init__(self) -> None:
        self.together_api_key = os.getenv('TOGETHER_API_KEY')
        self.model = 'Qwen/Qwen2-VL-72B-Instruct'
        self.client = Together(api_key=self.together_api_key)

        if not self.together_api_key:
            raise ValueError('Please set TOGETHER_API_KEY in the .env file')

    def extract_bounding_boxes(
        self,
        image_url: str,
        document_contents: dict[str, str],
        system_prompt: str,
        assistant_prompt: str,
    ) -> DetectedObjectListSchema:
        image_path = 'image.jpg'
        with open(image_path, 'wb') as f:
            response = requests.get(image_url)
            f.write(response.content)

        image_buffer = self.resize_and_compress_image(image_path)
        image_data = base64.b64encode(image_buffer.getvalue()).decode('utf-8')

        modified_system_prompt = (
            """You are a helpful assistant to detect objects in images. When
            asked to detect elements you return bounding boxes in the form of
            [xmin, ymin, xmax, ymax] with the values being scaled to match the
            1024x1024 size. """
            # + system_prompt
            + """Always respond in JSON format with an object with a key
            'objects' that contains a list of objects where each object has the
            following keys: 'bounding_boxes' and 'name'. Here's an example of
            what the object must look like:
            {
                "objects": [
                    {
                        "bounding_boxes": [435, 595, 704, 710],
                        "name": "electric car"
                    },
                    {
                        "bounding_boxes": [300, 450, 665, 610],
                        "name": "house"
                    }
                ]
            }
            """
        )

        prompt = assistant_prompt

        # Add the document contents to the prompt
        for key, value in document_contents.items():
            prompt += (
                '\n\n<document>'
                f'<name>{key}</name>'
                f'<content>{value}</content>'
                '</document>'
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    'role': 'system',
                    'content': modified_system_prompt,
                },
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{image_data}',
                            },
                        },
                    ],
                },
            ],
        )

        if (
            type(response) is not ChatCompletionResponse
            or response.choices is None
            or len(response.choices) <= 0
            or response.choices[0].message is None
            or type(response.choices[0].message.content) is not str
        ):
            raise ValueError('Invalid response from Together API')

        info = response.choices[0].message.content
        print(info)

        # Remove markdown code block delimiters if present
        info = info.replace('```json', '').replace('```', '').strip()
        return json.loads(info)


class HyperbolicAiService(AiService):
    def __init__(self) -> None:
        self.hyperbolic_api_key = os.getenv('HYPERBOLIC_API_KEY')
        self.model = 'Qwen/Qwen2-VL-72B-Instruct'
        self.client = openai.OpenAI(
            api_key=self.hyperbolic_api_key,
            base_url='https://api.hyperbolic.xyz/v1',
        )
        if not self.hyperbolic_api_key:
            raise ValueError('Please set HYPERBOLIC_API_KEY in the .env file')

    def extract_bounding_boxes(
        self,
        image_url: str,
        document_contents: dict[str, str],
        system_prompt: str,
        assistant_prompt: str,
    ) -> DetectedObjectListSchema:
        image_path = 'image.jpg'
        with open(image_path, 'wb') as f:
            img_response = requests.get(image_url)
            f.write(img_response.content)

        image_buffer = self.resize_and_compress_image(image_path)
        image_data = base64.b64encode(image_buffer.getvalue()).decode('utf-8')

        modified_system_prompt = """You are a helpful assistant that precisely
            detects objects in images. When asked to detect objects, you return
            bounding boxes in the form of [xmin, ymin, xmax, ymax] with the
            values being scaled to match the 1024x1024 size.
            Always respond in JSON format with an object with a key
            'objects' that contains a list of objects where each object has the
            following keys: 'bounding_boxes' and 'name'. Here's an example of
            what the object must look like:
            {
                "objects": [
                    {
                        "bounding_boxes": [xmin, ymin, xmax, ymax],
                        "name": "object1"
                    },
                    {
                        "bounding_boxes": [xmin, ymin, xmax, ymax],
                        "name": "object2"
                    }
                ]
            }
            """

        prompt = """Detect all objects in this image and provide
        bounding boxes for each of them.
        """

        # Add the document contents to the prompt
        # for key, value in document_contents.items():
        #     prompt += (
        #         '\n\n<document>'
        #         f'<name>{key}</name>'
        #         f'<content>{value}</content>'
        #         '</document>'
        #     )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    'role': 'system',
                    'content': modified_system_prompt,
                },
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{image_data}',
                            },
                        },
                    ],
                },
            ],
        )

        if (
            type(response) is not ChatCompletion
            or response.choices is None
            or len(response.choices) <= 0
            or response.choices[0].message is None
            or type(response.choices[0].message.content) is not str
        ):
            raise ValueError('Invalid response from Hyperbolic API')

        info = response.choices[0].message.content
        print(info)

        # Remove markdown code block delimiters if present
        info = info.replace('```json', '').replace('```', '').strip()
        return json.loads(info)


class GeminiAiService(AiService):
    def __init__(self) -> None:
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        self.model_name = 'gemini-1.5-pro-latest'

        if not self.gemini_api_key:
            raise ValueError('Please set GOOGLE_API_KEY in the .env file')

    def extract_bounding_boxes(
        self,
        image_url: str,
        document_contents: dict[str, str],
        system_prompt: str,
        assistant_prompt: str,
    ) -> DetectedObjectListSchema:
        image_path = 'image.jpg'
        with open(image_path, 'wb') as f:
            response = requests.get(image_url)
            f.write(response.content)

        image_buffer = self.resize_and_compress_image(image_path)
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
            model_name=self.model_name,
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
