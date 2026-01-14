// Estimation Bot Application
let API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const hourlyRateInput = document.getElementById('hourlyRate');
const apiUrlInput = document.getElementById('apiUrl');
const loadingIndicator = document.getElementById('loadingIndicator');

// Initialize
apiUrlInput.addEventListener('change', (e) => {
    API_BASE_URL = e.target.value || 'http://localhost:8000';
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        fileName.textContent = e.target.files[0].name;
        fileName.style.display = 'inline';
    } else {
        fileName.textContent = '';
        fileName.style.display = 'none';
    }
});

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendButton.addEventListener('click', sendMessage);

// Auto-scroll to bottom
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add message to chat
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = content;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    scrollToBottom();
}

// Format estimate response
function formatEstimateResponse(estimate) {
    const timeMin = Math.round(estimate.estimated_time_hours_min);
    const timeMax = Math.round(estimate.estimated_time_hours_max);
    const costMin = estimate.estimated_cost_min;
    const costMax = estimate.estimated_cost_max;
    
    return `
        <div class="estimate-result">
            <h3 style="margin-bottom: 20px; color: #667eea;">📊 Estimate Result</h3>
            <div class="estimate-summary">
                <div class="estimate-item large">
                    <span class="label">Estimated Time</span>
                    <span class="value time">${timeMin} - ${timeMax} hours</span>
                    <span class="range-note">Range estimate</span>
                </div>
                <div class="estimate-item large">
                    <span class="label">Estimated Cost</span>
                    <span class="value cost">$${costMin.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} - $${costMax.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                    <span class="range-note">Range estimate</span>
                </div>
            </div>
        </div>
    `;
}

// Show loading indicator
function showLoading() {
    loadingIndicator.classList.remove('hidden');
    scrollToBottom();
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

// Send message
async function sendMessage() {
    const requirements = chatInput.value.trim();
    const file = fileInput.files[0];
    const hourlyRate = hourlyRateInput.value ? parseFloat(hourlyRateInput.value) : null;
    
    if (!requirements && !file) {
        alert('Please provide requirements (text or file)');
        return;
    }
    
    // Add user message to chat
    let userMessage = '';
    if (requirements) {
        userMessage += requirements;
    }
    if (file) {
        userMessage += (requirements ? '\n\n' : '') + `[Uploaded: ${file.name}]`;
    }
    addMessage('user', userMessage.replace(/\n/g, '<br/>'));
    
    // Clear inputs
    chatInput.value = '';
    fileInput.value = '';
    fileName.textContent = '';
    fileName.style.display = 'none';
    
    // Show loading
    showLoading();
    
    try {
        // Prepare form data
        const formData = new FormData();
        if (requirements) {
            formData.append('requirements', requirements);
        }
        if (file) {
            formData.append('file', file);
        }
        if (hourlyRate) {
            formData.append('hourly_rate', hourlyRate.toString());
        }
        
        const response = await fetch(`${API_BASE_URL}/api/v1/estimate`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get estimate');
        }
        
        const data = await response.json();
        
        // Display estimate result
        addMessage('assistant', formatEstimateResponse(data));
        
    } catch (error) {
        console.error('Error:', error);
        addMessage('assistant', `<div class="error-message">Sorry, I encountered an error: ${error.message}. Please check your API URL and make sure the server is running.</div>`);
    } finally {
        hideLoading();
    }
}

// Health check on load
window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/health`);
        if (response.ok) {
            console.log('✅ API connected');
        }
    } catch (error) {
        console.warn('⚠️ API health check failed. Make sure the server is running.');
    }
    
    // Focus input
    chatInput.focus();
});
