"""
AI Configuration Page for Signal Bot Web Interface

PURPOSE:
    Dedicated interface for configuring and managing AI providers (Ollama and Gemini)
    that power the bot's intelligent analysis and response capabilities.

FUNCTIONALITY:
    1. Ollama Configuration (Local AI):
       - Configure local Ollama server URL
       - Test server connectivity
       - Select and manage AI models
       - View model details (size, context window, quantization)
       - Preload models into memory
       - Monitor VRAM usage and model status

    2. Gemini Configuration (External AI):
       - Configure Gemini CLI command path
       - Enable/disable Gemini provider
       - Fallback option when Ollama unavailable

    3. Provider Management:
       - Switch between AI providers
       - View active provider status
       - Monitor response times and availability
       - Display loaded models and memory usage

    4. Model Operations:
       - List available models from Ollama server
       - Preload selected models for faster response
       - View detailed model specifications
       - Automatic model selection based on availability

PAGE STRUCTURE:
    - Provider configuration sections (Ollama/Gemini)
    - Real-time connection testing interface
    - Model selection dropdown with details
    - Status dashboard showing provider health
    - Action buttons for save/preload/refresh

TESTING:
    1. Navigate to /ai-config or access via Settings > AI Configuration tab
    2. Test Ollama server connection with various URLs
    3. Verify model list population from Ollama server
    4. Test model preloading functionality
    5. Verify provider switching between Ollama and Gemini
    6. Check status updates reflect actual provider state
    7. Test error handling for invalid server URLs
    8. Verify configuration persistence after save

API ENDPOINTS USED:
    - GET /api/ai-status - Get current AI provider status
    - GET /api/ai-config - Load saved AI configuration
    - POST /api/ai-config - Save AI configuration
    - GET /api/ollama-models?host={url} - List available Ollama models
    - POST /api/ollama-preload - Preload selected model

DATABASE INTERACTIONS:
    - Reads/writes ai_config table for provider settings
    - Stores selected model preferences
    - Caches provider status for performance
"""

from typing import Dict, Any
from ..shared.base_page import BasePage


class AIConfigPage(BasePage):
    @property
    def title(self) -> str:
        return "🤖 AI Configuration"

    @property
    def nav_key(self) -> str:
        return "ai-config"

    @property
    def subtitle(self) -> str:
        return "Manage local and external AI providers"

    def get_custom_js(self) -> str:
        return """
                function loadConfig() {
                    fetchWithTimeout('/api/ai-config', {}, 10000)
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('provider').value = data.provider || '';
                            document.getElementById('model').value = data.model || '';
                            document.getElementById('api-key').value = data.api_key || '';
                            document.getElementById('temperature').value = data.temperature || '0.7';
                            document.getElementById('max-tokens').value = data.max_tokens || '150';
                            document.getElementById('system-prompt').value = data.system_prompt || '';

                            document.getElementById('sentiment-enabled').checked = data.sentiment_enabled || false;
                            document.getElementById('summary-enabled').checked = data.summary_enabled || false;
                            document.getElementById('auto-reactions').checked = data.auto_reactions_enabled || false;
                        })
                        .catch(error => {
                            console.error('Error loading AI config:', error);
                            showMessage('Error loading configuration', 'error');
                        });
                }

                const saveConfig = debounce(function() {
                    const btn = document.getElementById('save-btn');
                    setButtonLoading(btn, true, '⏳ Saving...');

                    const config = {
                        provider: document.getElementById('provider').value,
                        model: document.getElementById('model').value,
                        api_key: document.getElementById('api-key').value,
                        temperature: parseFloat(document.getElementById('temperature').value),
                        max_tokens: parseInt(document.getElementById('max-tokens').value),
                        system_prompt: document.getElementById('system-prompt').value,
                        sentiment_enabled: document.getElementById('sentiment-enabled').checked,
                        summary_enabled: document.getElementById('summary-enabled').checked,
                        auto_reactions_enabled: document.getElementById('auto-reactions').checked
                    };

                    fetchWithTimeout('/api/ai-config', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(config)
                    }, 15000)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showMessage('Configuration saved successfully!', 'success');
                        } else {
                            showMessage('Error saving configuration: ' + data.message, 'error');
                        }
                    })
                    .catch(error => {
                        showMessage('Error saving configuration: ' + error.message, 'error');
                    })
                    .finally(() => {
                        setButtonLoading(btn, false);
                    });
                }, 300);
                }

                const testConnection = debounce(function() {
                    const btn = document.getElementById('test-btn');
                    setButtonLoading(btn, true, '⏳ Testing...');

                    fetchWithTimeout('/api/ai-config/test', {method: 'POST'}, 20000)
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                showMessage('AI connection test successful!', 'success');
                            } else {
                                showMessage('Connection test failed: ' + data.message, 'error');
                            }
                        })
                        .catch(error => {
                            showMessage('Connection test failed: ' + error.message, 'error');
                        })
                        .finally(() => {
                            setButtonLoading(btn, false);
                        });
                }, 300);
                }

                function showMessage(message, type) {
                    const messageDiv = document.getElementById('message-area');
                    messageDiv.innerHTML = `<div class="message ${type}">${message}</div>`;
                    setTimeout(() => {
                        messageDiv.innerHTML = '';
                    }, 5000);
                }

                function updateModelOptions() {
                    const provider = document.getElementById('provider').value;
                    const modelSelect = document.getElementById('model');

                    modelSelect.innerHTML = '<option value="">Select model...</option>';

                    if (provider === 'openai') {
                        const models = ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'];
                        models.forEach(model => {
                            modelSelect.innerHTML += `<option value="${model}">${model}</option>`;
                        });
                    } else if (provider === 'anthropic') {
                        const models = ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'];
                        models.forEach(model => {
                            modelSelect.innerHTML += `<option value="${model}">${model}</option>`;
                        });
                    } else if (provider === 'ollama') {
                        const models = ['llama2', 'mixtral', 'codellama', 'mistral'];
                        models.forEach(model => {
                            modelSelect.innerHTML += `<option value="${model}">${model}</option>`;
                        });
                    }
                }

                // Load config when page loads
                document.addEventListener('DOMContentLoaded', loadConfig);
        """

    def get_custom_css(self) -> str:
        """No custom CSS - using shared styling."""
        return ""

    def render_content(self, query: Dict[str, Any]) -> str:
        return """
            <h1>AI Configuration</h1>
            <p>Configure AI providers and settings for sentiment analysis, summaries, and automatic reactions.</p>

            <div id="message-area"></div>

            <div class="config-form">
                <div class="form-section">
                    <h3>Provider Settings</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="provider">AI Provider</label>
                            <select id="provider" onchange="updateModelOptions()">
                                <option value="">Select provider...</option>
                                <option value="openai">OpenAI</option>
                                <option value="anthropic">Anthropic</option>
                                <option value="ollama">Ollama (Local)</option>
                            </select>
                            <small>Choose your preferred AI service provider</small>
                        </div>
                        <div class="form-group">
                            <label for="model">Model</label>
                            <select id="model">
                                <option value="">Select model...</option>
                            </select>
                            <small>Specific AI model to use for generation</small>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="api-key">API Key</label>
                        <input type="password" id="api-key" placeholder="Enter API key (not needed for Ollama)">
                        <small>Your API key for the selected provider (leave blank for Ollama)</small>
                    </div>
                </div>

                <div class="form-section">
                    <h3>Generation Parameters</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="temperature">Temperature</label>
                            <input type="number" id="temperature" min="0" max="2" step="0.1" value="0.7">
                            <small>Controls randomness: 0 = deterministic, 2 = very random</small>
                        </div>
                        <div class="form-group">
                            <label for="max-tokens">Max Tokens</label>
                            <input type="number" id="max-tokens" min="1" max="4000" value="150">
                            <small>Maximum length of generated responses</small>
                        </div>
                    </div>
                </div>

                <div class="form-section">
                    <h3>System Prompt</h3>
                    <div class="form-group">
                        <label for="system-prompt">System Prompt</label>
                        <textarea id="system-prompt" placeholder="Enter system instructions for the AI..."></textarea>
                        <small>Instructions that define the AI's behavior and personality</small>
                    </div>
                </div>

                <div class="form-section">
                    <h3>Feature Toggles</h3>
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" id="sentiment-enabled">
                            <label for="sentiment-enabled">Enable Sentiment Analysis</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="summary-enabled">
                            <label for="summary-enabled">Enable Message Summaries</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="auto-reactions">
                            <label for="auto-reactions">Enable Auto Reactions</label>
                        </div>
                    </div>
                </div>

                <div class="form-actions">
                    <button id="test-btn" class="btn btn-secondary" onclick="testConnection()">Test Connection</button>
                    <button id="save-btn" class="btn btn-primary" onclick="saveConfig()">Save Configuration</button>
                </div>
            </div>
        """