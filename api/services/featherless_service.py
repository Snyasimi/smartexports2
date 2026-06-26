import requests
import base64
import os
from django.conf import settings
from PIL import Image
from io import BytesIO

class FeatherlessService:
    """
    Service to interact with Featherless AI vision model.
    Sends images to the model and gets extracted text back.
    """
    
    def __init__(self):
        self.api_key = settings.FEATHERLESS_API_KEY
        self.api_url = settings.FEATHERLESS_API_URL
        self.model = settings.FEATHERLESS_MODEL
    
    def encode_image_to_base64(self, image_file):
        """
        Convert uploaded image file to base64 encoding.
        Compresses the image to reduce file size for API limits.
        
        Args:
            image_file: Django UploadedFile object
            
        Returns:
            base64 encoded string of the compressed image
        """
        try:
            # Open image
            image_file.seek(0)
            img = Image.open(image_file)
            
            # Compress: resize if too large, reduce quality
            max_width = 1280
            max_height = 1280
            
            # Resize if larger than max
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed (for JPEG quality)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Save compressed to bytes
            compressed = BytesIO()
            img.save(compressed, format='JPEG', quality=80, optimize=True)
            compressed.seek(0)
            
            # Encode to base64
            image_data = compressed.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            return base64_image
            
        except Exception as e:
            raise Exception(f"Failed to compress image: {str(e)}")
    
    def extract_text_from_image(self, image_file):
        """
        Send image to Featherless AI and extract text from it.
        
        This calls the vision model which reads the fertilizer label
        and returns all text it can see.
        
        Args:
            image_file: Django UploadedFile object
            
        Returns:
            dict with:
                - success: bool (True if extraction worked)
                - text: str (extracted text from image)
                - error: str (error message if it failed)
        """
        try:
            print("[Featherless] Compressing image...")
            # Convert image to base64
            base64_image = self.encode_image_to_base64(image_file)
            print(f"[Featherless] Image compressed. Base64 size: {len(base64_image)} chars")
            
            # Prepare the request to Featherless AI
            # We're asking the vision model to read the image and extract all text
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a fertilizer label analyzer. Extract ALL text from the fertilizer label image. List every ingredient, chemical name, and specification you can see. Be thorough and accurate.'
                    },
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': 'Please read this fertilizer label image carefully and extract all text. Include all ingredients, chemical names, percentages, warnings, and any other information visible on the label.'
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{base64_image}'
                                }
                            }
                        ]
                    }
                ],
                'max_tokens': 2048
            }
            
            print(f"[Featherless] Sending request to {self.api_url}")
            # Send request to Featherless AI
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Extract the text from the response
            result = response.json()
            extracted_text = result['choices'][0]['message']['content']
            
            print("[Featherless] ✓ Text extraction successful")
            return {
                'success': True,
                'text': extracted_text,
                'error': None
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'text': None,
                'error': 'Request to Featherless AI timed out. Please try again.'
            }
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if '413' in error_msg:
                error_msg = 'Image is still too large. Please use a smaller or lower-quality photo.'
            return {
                'success': False,
                'text': None,
                'error': f'Featherless API error: {error_msg}'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'text': None,
                'error': f'Failed to connect to Featherless AI: {str(e)}'
            }
        except KeyError:
            return {
                'success': False,
                'text': None,
                'error': 'Unexpected response format from Featherless AI.'
            }
        except Exception as e:
            return {
                'success': False,
                'text': None,
                'error': f'Error extracting text: {str(e)}'
            }