from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import InMemoryUploadedFile
import json
import sys
import io
from PIL import Image

from .services.featherless_service import FeatherlessService
from .services.risk_assessment import RiskAssessmentService


@csrf_exempt  
@require_http_methods(["POST"])
def analyze_fertilizer_label(request):
    try:
        # Check if image was uploaded
        if 'image' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No image file provided. Please upload a photo of the fertilizer label.'
            }, status=400)
        
        raw_image_file = request.FILES['image']
        
        # ---------------------------------------------------------------
        # IN-MEMORY IMAGE COMPRESSION LAYER
        # ---------------------------------------------------------------
        print(f"[PRE-PROCESS] Original file size: {raw_image_file.size / 1024:.2f} KB")
        try:
            # Load the uploaded image using Pillow
            img = Image.open(raw_image_file)
            
            # 1. Downscale dimensions if they exceed standard 1024px width/height
            max_dimension = 1024
            if img.width > max_dimension or img.height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # 2. Convert to RGB mode if it's PNG or RGBA (JPEG requires RGB)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # 3. Compress into memory as a JPEG
            output_io = io.BytesIO()
            img.save(output_io, format='JPEG', optimize=True, quality=75)
            output_io.seek(0)
            
            # 4. Wrap it back into a Django-compatible upload file object
            compressed_image_file = InMemoryUploadedFile(
                output_io,
                'ImageField',
                f"{raw_image_file.name.split('.')[0]}.jpg",
                'image/jpeg',
                sys.getsizeof(output_io),
                None
            )
            print(f"[PRE-PROCESS] ✓ Compressed file size: {compressed_image_file.size / 1024:.2f} KB")
        except Exception as img_err:
            # Safe fallback if image reading fails: use the raw file and let the pipeline proceed
            print(f"[WARNING] Image compression failed, using original file: {str(img_err)}")
            compressed_image_file = raw_image_file
        # ---------------------------------------------------------------
        
        # Step 1: Extract text from compressed image using Featherless AI
        print("[1/3] Extracting text from fertilizer label image...")
        featherless_service = FeatherlessService()
        
        # Pass the newly compressed file here
        extraction_result = featherless_service.extract_text_from_image(compressed_image_file)
        
        if not extraction_result['success']:
            print(f"[ERROR] Extraction failed: {extraction_result['error']}")
            return JsonResponse({
                'success': False,
                'error': extraction_result['error']
            }, status=500)
        
        extracted_text = extraction_result['text']
        is_demo = extraction_result.get('is_demo', False)
        demo_notice = extraction_result.get('error', '')
        print(f"[1/3] ✓ Text extracted successfully (demo={is_demo})")
        print(f"Extracted text: {extracted_text[:200]}...")  # First 200 chars
        
        # Step 2: Analyze the text for EU compliance risks
        print("[2/3] Analyzing for EU compliance risks...")
        risk_service = RiskAssessmentService()
        assessment = risk_service.assess_risk(extracted_text)
        print(f"[2/3] ✓ Risk assessment complete: {assessment['risk_level'].upper()}")
        
        # Step 3: Return results to user
        print("[3/3] Formatting response for farmer...")
        response_data = {
            'success': True,
            'risk_level': assessment['risk_level'],
            'verdict': assessment['verdict'],
            'chemicals_found': assessment['chemicals_found'],
            'explanations': assessment['explanations'],
            'recommendations': assessment['recommendations'],
            'extracted_text': extracted_text,  # For debugging
            'is_demo': is_demo,
            'demo_notice': demo_notice
        }
        print("[3/3] ✓ Response ready")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Full traceback:")
        print(error_trace)
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


def index(request):
    """
    Render the main page with the chat interface.
    """
    return render(request, 'index.html')