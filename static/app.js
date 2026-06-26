/**
 * SmartExports Frontend
 * Handles fertilizer label upload, API calls, and results display
 */

// Get DOM elements
const uploadForm = document.getElementById('uploadForm');
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const previewImg = document.getElementById('previewImg');
const submitBtn = document.getElementById('submitBtn');
const submitText = document.getElementById('submitText');
const submitSpinner = document.getElementById('submitSpinner');

const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');

// File input change handler - show preview
imageInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    
    if (file) {
        // Check file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('File is too large. Maximum size is 10MB.');
            clearImage();
            return;
        }
        
        // Show preview
        const reader = new FileReader();
        reader.onload = function(event) {
            previewImg.src = event.target.result;
            imagePreview.style.display = 'flex';
        };
        reader.readAsDataURL(file);
    }
});

// Clear image preview
function clearImage() {
    imageInput.value = '';
    previewImg.src = '';
    imagePreview.style.display = 'none';
}

// Form submission - upload and analyze
uploadForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Validation
    if (!imageInput.files.length) {
        alert('Please select an image file');
        return;
    }
    
    // Hide previous results
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    // Show loading state
    submitBtn.disabled = true;
    submitText.textContent = 'Analyzing...';
    submitSpinner.style.display = 'inline-block';
    
    try {
        // Prepare form data
        const formData = new FormData();
        formData.append('image', imageInput.files[0]);
        
        // Send to backend
        console.log('Sending image to backend...');
        const response = await fetch('/api/analyze-label/', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Display results
            displayResults(data);
        } else {
            // Display error
            displayError(data.error || 'An error occurred');
        }
        
    } catch (error) {
        console.error('Error:', error);
        displayError('Failed to connect to the server. Please try again.');
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        submitText.textContent = 'Analyze Label';
        submitSpinner.style.display = 'none';
    }
});

/**
 * Display results from the API
 */
function displayResults(data) {
    console.log('Results:', data);
    
    // Hide upload, show results
    uploadForm.style.display = 'none';
    resultsSection.style.display = 'block';
    errorSection.style.display = 'none';
    
    // Set verdict
    const verdictBox = document.getElementById('verdictBox');
    const riskClass = `verdict-${data.risk_level}`;
    verdictBox.className = `verdict-box ${riskClass}`;
    document.getElementById('verdictContent').textContent = data.verdict;
    
    // Display chemicals if any were found
    if (data.chemicals_found && data.chemicals_found.length > 0) {
        document.getElementById('chemicalsSection').style.display = 'block';
        const chemicalsList = document.getElementById('chemicalsList');
        chemicalsList.innerHTML = '';
        
        data.chemicals_found.forEach(chemical => {
            const div = document.createElement('div');
            div.className = `chemical-item chemical-${chemical.risk_level}`;
            div.innerHTML = `
                <div class="chemical-name">${chemical.name}</div>
                <div class="chemical-reason">${chemical.reason}</div>
            `;
            chemicalsList.appendChild(div);
        });
    } else {
        document.getElementById('chemicalsSection').style.display = 'none';
    }
    
    // Display explanations
    if (data.explanations && data.explanations.length > 0) {
        document.getElementById('explanationsSection').style.display = 'block';
        const explanationsList = document.getElementById('explanationsList');
        explanationsList.innerHTML = '';
        
        data.explanations.forEach(explanation => {
            const div = document.createElement('div');
            div.className = 'explanation-item';
            div.textContent = explanation;
            explanationsList.appendChild(div);
        });
    } else {
        document.getElementById('explanationsSection').style.display = 'none';
    }
    
    // Display recommendations
    document.getElementById('recommendationsBox').textContent = data.recommendations;
    
    // Display extracted text (debug)
    document.getElementById('extractedText').textContent = data.extracted_text || 'No text extracted';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Display error message
 */
function displayError(errorMessage) {
    console.error('Error displayed:', errorMessage);
    
    uploadForm.style.display = 'block';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'block';
    
    document.getElementById('errorMessage').textContent = errorMessage;
    
    // Scroll to error
    errorSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Reset form to initial state
 */
function resetForm() {
    // Clear form
    uploadForm.reset();
    clearImage();
    
    // Show upload, hide results
    uploadForm.style.display = 'block';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    // Scroll to top
    document.querySelector('.upload-card').scrollIntoView({ behavior: 'smooth' });
}

// Drag and drop support
const fileLabel = document.querySelector('.file-label');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    fileLabel.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    fileLabel.addEventListener(eventName, () => {
        fileLabel.style.borderColor = '#764ba2';
        fileLabel.style.background = '#f0f2ff';
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    fileLabel.addEventListener(eventName, () => {
        fileLabel.style.borderColor = '#667eea';
        fileLabel.style.background = '#f8f9ff';
    }, false);
});

fileLabel.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    imageInput.files = files;
    
    // Trigger change event
    const event = new Event('change', { bubbles: true });
    imageInput.dispatchEvent(event);
}

console.log('SmartExports app loaded successfully');