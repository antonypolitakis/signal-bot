// Messages page JavaScript - handles tab navigation and AI analysis functions
// Note: DebugLogger is now available globally from common.js
// Note: GlobalFilters object is defined inline by filters.py render_filters()

// Global function for compatibility with AI analysis functions
function getGlobalFilters() {
    if (typeof GlobalFilters !== 'undefined' && GlobalFilters.getValues) {
        return GlobalFilters.getValues();
    }
    // Fallback if GlobalFilters not yet initialized
    return {
        groupId: '',
        senderId: '',
        date: '',
        hours: null,
        attachmentsOnly: false,
        dateMode: 'all'
    };
}

// AI Analysis functions for the AI Analysis tab
function showMessageAnalysisPreview() {
    const analysisType = document.getElementById('analysis-type-selector').value;
    const previewDiv = document.getElementById('message-analysis-preview');

    if (!analysisType) {
        showError('Please select an analysis type');
        return;
    }

    previewDiv.innerHTML = '<div class="loading">Loading preview...</div>';

    // Get current filters
    const filters = getGlobalFilters();
    const params = new URLSearchParams();

    params.append('analysis_type', analysisType);
    if (filters.groupId) params.append('group_id', filters.groupId);
    if (filters.senderId) params.append('sender_id', filters.senderId);
    if (filters.date) params.append('date', filters.date);
    if (filters.hours) params.append('hours', filters.hours);

    fetch('/api/ai-analysis/preview?' + params)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                previewDiv.innerHTML = `
                    <div class="card preview-card">
                        <h4>Preview</h4>
                        <p><strong>Messages found:</strong> ${data.message_count}</p>
                        <p><strong>Analysis type:</strong> ${data.analysis_type}</p>
                        ${data.preview ? `<div class="preview-content">${data.preview}</div>` : ''}
                    </div>
                `;
            } else {
                previewDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Failed to load preview'}</div>`;
            }
        })
        .catch(error => {
            previewDiv.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
        });
}

function runMessageAnalysis() {
    const analysisType = document.getElementById('analysis-type-selector').value;
    const resultsDiv = document.getElementById('message-analysis-results');

    if (!analysisType) {
        showError('Please select an analysis type');
        return;
    }

    resultsDiv.innerHTML = '<div class="loading">Running analysis...</div>';

    // Get current filters
    const filters = getGlobalFilters();
    const params = new URLSearchParams();

    params.append('analysis_type', analysisType);
    if (filters.groupId) params.append('group_id', filters.groupId);
    if (filters.senderId) params.append('sender_id', filters.senderId);
    if (filters.date) params.append('date', filters.date);
    if (filters.hours) params.append('hours', filters.hours);

    fetch('/api/ai-analysis/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(params))
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultsDiv.innerHTML = `
                    <div class="card results-card">
                        <h3>${data.title || 'Analysis Results'}</h3>
                        <div class="analysis-content">${data.content || data.result}</div>
                        <p class="text-muted" style="margin-top: 15px;">
                            <small>Analysis completed at ${new Date().toLocaleString()}</small>
                        </p>
                    </div>
                `;
            } else {
                resultsDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Analysis failed'}</div>`;
            }
        })
        .catch(error => {
            resultsDiv.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
        });
}

// Sentiment Analysis functions
function showSentimentPreview() {
    const previewDiv = document.getElementById('sentiment-preview');
    previewDiv.innerHTML = '<div class="loading">Loading preview...</div>';

    const filters = getGlobalFilters();
    const params = new URLSearchParams();

    if (filters.groupId) params.append('group_id', filters.groupId);
    if (filters.date) params.append('date', filters.date);

    fetch('/api/sentiment/preview?' + params)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                previewDiv.innerHTML = `
                    <div class="card preview-card">
                        <h4>Preview</h4>
                        <p>Found ${data.message_count} messages to analyze</p>
                    </div>
                `;
            } else {
                previewDiv.innerHTML = `<div class="alert alert-error">${data.error}</div>`;
            }
        })
        .catch(error => {
            previewDiv.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
        });
}

function analyzeSentiment(forceRefresh) {
    const resultsDiv = document.getElementById('sentiment-results');
    resultsDiv.innerHTML = '<div class="loading">Analyzing sentiment...</div>';

    const filters = getGlobalFilters();
    const params = new URLSearchParams();

    if (filters.groupId) params.append('group_id', filters.groupId);
    if (filters.date) params.append('date', filters.date);
    if (forceRefresh) params.append('force_refresh', 'true');

    fetch('/api/sentiment/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(params))
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload(); // Reload to show results
            } else {
                resultsDiv.innerHTML = `<div class="alert alert-error">${data.error}</div>`;
            }
        })
        .catch(error => {
            resultsDiv.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
        });
}

// Summary functions
function showSummaryPreview() {
    const previewDiv = document.getElementById('summary-preview');
    previewDiv.innerHTML = '<div class="loading">Loading preview...</div>';

    const filters = getGlobalFilters();
    const params = new URLSearchParams();

    if (filters.groupId) params.append('group_id', filters.groupId);
    if (filters.date) params.append('date', filters.date);

    fetch('/api/summary/preview?' + params)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                previewDiv.innerHTML = `
                    <div class="card preview-card">
                        <h4>Preview</h4>
                        <p>Found ${data.message_count} messages to summarize</p>
                    </div>
                `;
            } else {
                previewDiv.innerHTML = `<div class="alert alert-error">${data.error}</div>`;
            }
        })
        .catch(error => {
            previewDiv.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
        });
}

function generateSummary(forceRefresh) {
    const resultsDiv = document.getElementById('summary-results');
    resultsDiv.innerHTML = '<div class="loading">Generating summary...</div>';

    const filters = getGlobalFilters();
    const params = new URLSearchParams();

    if (filters.groupId) params.append('group_id', filters.groupId);
    if (filters.date) params.append('date', filters.date);
    if (forceRefresh) params.append('force_refresh', 'true');

    fetch('/api/summary/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(params))
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload(); // Reload to show results
            } else {
                resultsDiv.innerHTML = `<div class="alert alert-error">${data.error}</div>`;
            }
        })
        .catch(error => {
            resultsDiv.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
        });
}

// Initialize default tab
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab') || 'groups';

    // Show the correct tab content
    const tabContent = document.getElementById(tab + '-tab');
    const tabButton = document.querySelector(`[data-tab='${tab}']`);

    if (tabContent) {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
        // Show selected tab
        tabContent.style.display = 'block';
    }

    if (tabButton) {
        // Update active state
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        tabButton.classList.add('active');
    }

    // Note: GlobalFilters initialization is handled by filters.py inline JavaScript
});