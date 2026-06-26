"""
Risk Assessment Service

This service analyzes extracted fertilizer label text and matches it against
EU restricted substances. Returns a risk verdict and plain-language explanation.

Mock data is used here. Later, this will be replaced with Neo4j queries.
"""

class RiskAssessmentService:
    
    # Mock EU restricted substances database
    # In production, this comes from Neo4j
    RESTRICTED_SUBSTANCES = {
        'cadmium': {
            'risk_level': 'high',
            'reason': 'Cadmium is a heavy metal restricted in EU food safety standards',
            'action': 'DO NOT USE for EU export. This fertilizer will cause rejection at EU border.'
        },
        'lead': {
            'risk_level': 'high',
            'reason': 'Lead is a heavy metal banned in EU organic and conventional farming',
            'action': 'DO NOT USE for EU export. This fertilizer will cause rejection at EU border.'
        },
        'arsenic': {
            'risk_level': 'high',
            'reason': 'Arsenic is a heavy metal restricted in EU food regulations',
            'action': 'DO NOT USE for EU export. This fertilizer will cause rejection at EU border.'
        },
        'chromium': {
            'risk_level': 'high',
            'reason': 'Chromium (especially Cr(VI)) is restricted in EU regulations',
            'action': 'DO NOT USE for EU export.'
        },
        'mercury': {
            'risk_level': 'high',
            'reason': 'Mercury is banned in EU food production inputs',
            'action': 'DO NOT USE for EU export. Immediate rejection at border.'
        },
        'phosphonate': {
            'risk_level': 'high',
            'reason': 'Phosphonates (phosphonic acid derivatives) are restricted in EU organic production',
            'action': 'DO NOT USE if selling as organic. Will cause rejection.'
        },
        'glyphosate': {
            'risk_level': 'high',
            'reason': 'Glyphosate is restricted/banned in many EU countries for certain uses',
            'action': 'DO NOT USE for EU export. Check with buyer first.'
        },
        'neonicotinoid': {
            'risk_level': 'high',
            'reason': 'Neonicotinoids (imidacloprid, clothianidin, thiamethoxam) are restricted in EU',
            'action': 'DO NOT USE. These are banned for most uses in EU.'
        },
        'ddt': {
            'risk_level': 'high',
            'reason': 'DDT is banned in EU and internationally',
            'action': 'DO NOT USE. Immediate rejection at border.'
        },
        'endosulfan': {
            'risk_level': 'high',
            'reason': 'Endosulfan is banned in EU',
            'action': 'DO NOT USE. This will cause rejection.'
        },
        'synthetic': {
            'risk_level': 'medium',
            'reason': 'Synthetic chemicals may not be allowed in organic production',
            'action': 'Check if this is approved for organic farming. Get expert review.'
        },
        'mineral': {
            'risk_level': 'low',
            'reason': 'Mineral-based fertilizers are generally acceptable for EU',
            'action': 'Likely safe, but verify exact composition.'
        },
        'organic': {
            'risk_level': 'low',
            'reason': 'Organic fertilizers are generally EU-compliant',
            'action': 'Likely safe for EU export. Verify it\'s certified.'
        },
        'potassium': {
            'risk_level': 'low',
            'reason': 'Potassium (K) is essential and safe for EU',
            'action': 'Safe for EU export.'
        },
        'nitrogen': {
            'risk_level': 'low',
            'reason': 'Nitrogen (N) is essential and safe for EU',
            'action': 'Safe for EU export.'
        },
        'phosphorus': {
            'risk_level': 'low',
            'reason': 'Phosphorus (P) is essential and safe for EU',
            'action': 'Safe for EU export.'
        },
        'calcium': {
            'risk_level': 'low',
            'reason': 'Calcium is essential and safe for EU',
            'action': 'Safe for EU export.'
        },
        'magnesium': {
            'risk_level': 'low',
            'reason': 'Magnesium is essential and safe for EU',
            'action': 'Safe for EU export.'
        },
        'sulfur': {
            'risk_level': 'low',
            'reason': 'Sulfur is approved for organic and conventional farming in EU',
            'action': 'Safe for EU export.'
        },
        'boron': {
            'risk_level': 'low',
            'reason': 'Boron is a micronutrient approved for EU farming',
            'action': 'Safe for EU export.'
        },
        'zinc': {
            'risk_level': 'low',
            'reason': 'Zinc is a micronutrient approved for EU farming',
            'action': 'Safe for EU export.'
        },
        'copper': {
            'risk_level': 'low',
            'reason': 'Copper is approved for organic farming (Bordeaux mixture, copper sulfate)',
            'action': 'Safe for EU export if within limits.'
        },
        'iron': {
            'risk_level': 'low',
            'reason': 'Iron is a micronutrient approved for EU farming',
            'action': 'Safe for EU export.'
        },
        'manganese': {
            'risk_level': 'low',
            'reason': 'Manganese is a micronutrient approved for EU farming',
            'action': 'Safe for EU export.'
        },
    }
    
    def assess_risk(self, extracted_text):
        """
        Analyze extracted fertilizer label text and return risk assessment.
        
        Args:
            extracted_text: str - the text extracted from the fertilizer label
            
        Returns:
            dict with:
                - risk_level: 'high', 'medium', or 'low'
                - verdict: str - summary of the risk
                - chemicals_found: list of identified chemicals
                - explanations: list of detailed explanations
                - recommendations: str - what the farmer should do next
        """
        
        if not extracted_text or extracted_text.strip() == '':
            return {
                'risk_level': 'unknown',
                'verdict': 'Could not extract text from image. Please provide a clearer photo of the fertilizer label.',
                'chemicals_found': [],
                'explanations': [],
                'recommendations': 'Try uploading a clearer image of the label.'
            }
        
        # Convert text to lowercase for matching
        text_lower = extracted_text.lower()
        
        # Find which restricted substances are mentioned
        chemicals_found = []
        high_risk_found = False
        medium_risk_found = False
        explanations = []
        
        for substance, details in self.RESTRICTED_SUBSTANCES.items():
            if substance in text_lower:
                chemicals_found.append({
                    'name': substance,
                    'risk_level': details['risk_level'],
                    'reason': details['reason']
                })
                
                explanations.append(f"🚨 {substance.upper()}: {details['reason']}")
                
                if details['risk_level'] == 'high':
                    high_risk_found = True
                elif details['risk_level'] == 'medium':
                    medium_risk_found = True
        
        # Determine overall risk level
        if high_risk_found:
            overall_risk = 'high'
            verdict = '⚠️ HIGH RISK: This fertilizer contains substances restricted in EU market. DO NOT USE for EU export.'
        elif medium_risk_found:
            overall_risk = 'medium'
            verdict = '⚠️ MEDIUM RISK: This fertilizer may have EU compliance issues. Get expert review before use.'
        elif chemicals_found:
            overall_risk = 'low'
            verdict = '✅ LOW RISK: This fertilizer appears to be EU-compliant. Safe to use for EU export.'
        else:
            overall_risk = 'unclear'
            verdict = '❓ UNCLEAR: Could not identify the chemicals in this fertilizer. Please get expert review.'
        
        # Build recommendations
        if overall_risk == 'high':
            recommendations = (
                'STOP. Do not use this fertilizer. It contains substances that will cause EU border rejection. '
                'Switch to an alternative brand that is EU-certified. Ask your supplier for an EU-compliant fertilizer.'
            )
        elif overall_risk == 'medium':
            recommendations = (
                'CAUTION. This fertilizer may have EU compliance issues. '
                'Get a technical advisor or agronomist to review the label before use. '
                'Contact your buyer to confirm they will accept produce from this input.'
            )
        elif overall_risk == 'low':
            recommendations = (
                'This fertilizer is likely safe for EU export. However, keep the label for your records. '
                'Best practice: Ask your buyer to confirm they accept this input before application.'
            )
        else:
            recommendations = (
                'The label text was unclear. Please upload a clearer image or contact a technical advisor to review the label. '
                'Do not apply this fertilizer until you are certain it is EU-compliant.'
            )
        
        return {
            'risk_level': overall_risk,
            'verdict': verdict,
            'chemicals_found': chemicals_found,
            'explanations': explanations,
            'recommendations': recommendations,
            'raw_extracted_text': extracted_text
        }