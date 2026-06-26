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
        Aggressively compresses to reduce token size.
        """
        try:
            image_file.seek(0)
            img = Image.open(image_file)
            
            # Much smaller dimensions to reduce token count
            max_width = 640   # Reduced from 1280
            max_height = 640  # Reduced from 1280
            
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            compressed = BytesIO()
            img.save(compressed, format='JPEG', quality=60, optimize=True)  # Reduced from 80
            compressed.seek(0)
            
            image_data = compressed.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            print(f"[Featherless] Compressed image size: {len(image_data)} bytes, base64: {len(base64_image)} chars")
            return base64_image
            
        except Exception as e:
            raise Exception(f"Failed to compress image: {str(e)}")
    
    def extract_text_from_image(self, image_file):
        """
        Send image to Featherless AI and extract text from it.
        Uses structured content arrays to parse image inputs natively.
        """
        try:
            print("[Featherless] Compressing image...")
            base64_image = self.encode_image_to_base64(image_file)
            print(f"[Featherless] Compressed image size: {len(base64_image)} chars")
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # FIXED: Multimodal payload structure
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': 'Extract all text from this fertilizer label. List ingredients, chemicals, percentages, and warnings clearly.'
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
                'max_tokens': 1024
            }
            
            print(f"[Featherless] Sending request to {self.api_url}")
            print(f"[Featherless] Using model: {self.model}")
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            extracted_text = result['choices'][0]['message']['content']
            
            print("[Featherless] ✓ Text extraction successful")
            return {
                'success': True,
                'text': extracted_text,
                'error': None,
                'is_demo': False
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'text': None,
                'error': 'Request timed out. Please try again.',
                'is_demo': False
            }
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            print(f"[Featherless] HTTP Error: {error_msg}")
            
            try:
                response_text = e.response.text
                print(f"[Featherless] Full response: {response_text}")
            except:
                pass
            
            if '413' in error_msg:
                return {
                    'success': False,
                    'text': None,
                    'error': 'Image is too large. Use a smaller image.',
                    'is_demo': False
                }
            elif '503' in error_msg or '502' in error_msg or '400' in error_msg:
                print("[Featherless] Server issue or bad request syntax. Using demo mode fallback.")
                # If your class contains get_demo_extraction, trigger fallback
                if hasattr(self, 'get_demo_extraction'):
                    demo_result = self.get_demo_extraction()
                    demo_result['error'] = f'⚠️ Demo Mode Fallback: {error_msg}'
                    return demo_result
                return {
                    'success': False,
                    'text': None,
                    'error': f'Featherless API error: {error_msg}',
                    'is_demo': False
                }
            else:
                return {
                    'success': False,
                    'text': None,
                    'error': f'Featherless API error: {error_msg}',
                    'is_demo': False
                }
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            return {
                'success': False,
                'text': None,
                'error': f'Error: {str(e)}',
                'is_demo': False
            }