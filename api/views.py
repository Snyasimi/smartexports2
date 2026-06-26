from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .services.featherless_service import FeatherlessService
from .services.risk_assessment import RiskAssessmentService


@csrf_exempt  # For hackathon. In production, use proper CSRF protection
@require_http_methods(["POST"])
def analyze_fertilizer_label(request):
    """
    Main API endpoint to analyze a fertilizer label image.
    
    Expected request:
    - POST with multipart/form-data
    - 'image' file field containing the fertilizer label photo
    
    Returns JSON with:
    - risk_level: 'high', 'medium', 'low', 'unclear'
    - verdict: plain language summary
    - chemicals_found: list of identified chemicals
    - explanations: detailed explanations for each chemical
    - recommendations: what the farmer should do
    """
    
    try:
        # Check if image was uploaded
        if 'image' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No image file provided. Please upload a photo of the fertilizer label.'
            }, status=400)
        
        image_file = request.FILES['image']
        
        # Step 1: Extract text from image using Featherless AI
        print("[1/3] Extracting text from fertilizer label image...")
        featherless_service = FeatherlessService()
        extraction_result = featherless_service.extract_text_from_image(image_file)
        
        if not extraction_result['success']:
            return JsonResponse({
                'success': False,
                'error': extraction_result['error']
            }, status=500)
        
        extracted_text = extraction_result['text']
        print(f"[1/3] ✓ Text extracted successfully")
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
            'extracted_text': extracted_text  # For debugging
        }
        print("[3/3] ✓ Response ready")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


def index(request):
    """
    Render the main page with the upload form.
    """
    return render(request, 'index.html')