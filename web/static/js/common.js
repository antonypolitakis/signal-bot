/**
 * Common JavaScript functionality shared across all pages
 * This file contains utility functions and common behaviors used throughout the Signal Bot web interface
 */

// ============================================================================
// DEBUG LOGGING SYSTEM
// ============================================================================

// Check if DEBUG mode is enabled
const DEBUG_MODE = window.location.search.includes('debug=1') ||
                   window.localStorage.getItem('signal_bot_debug') === '1';

// Global DebugLogger for client-side debugging (only active in DEBUG mode)
const DebugLogger = {
    logs: [],
    maxLogs: 100,
    enabled: DEBUG_MODE,

    log: function(message, data = {}) {
        if (!this.enabled) return;

        const entry = {
            timestamp: new Date().toISOString(),
            message: message,
            data: data,
            url: window.location.href,
            userAgent: navigator.userAgent,
            page: window.location.pathname
        };

        this.logs.push(entry);
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        console.log(`[DEBUG] ${message}`, data);
    },

    sendToServer: function(entry) {
        if (!this.enabled) return;

        try {
            fetch('/debug_log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(entry)
            }).catch(err => {
                console.error('Failed to send debug log:', err);
            });
        } catch (error) {
            console.error('Error sending debug log:', error);
        }
    },

    getNavigationTiming: function() {
        const timing = performance.getEntriesByType('navigation')[0];
        if (!timing) return null;

        return {
            domContentLoaded: timing.domContentLoadedEventEnd - timing.domContentLoadedEventStart,
            loadComplete: timing.loadEventEnd - timing.loadEventStart,
            domInteractive: timing.domInteractive - timing.fetchStart,
            pageLoadTime: timing.loadEventEnd - timing.fetchStart
        };
    },

    sendDebugReport: function() {
        if (!this.enabled || this.logs.length === 0) return;

        const report = {
            timestamp: new Date().toISOString(),
            message: 'Debug Report',
            data: {
                logs: this.logs,
                timing: this.getNavigationTiming(),
                memory: performance.memory ? {
                    used: Math.round(performance.memory.usedJSHeapSize / 1048576) + 'MB',
                    total: Math.round(performance.memory.totalJSHeapSize / 1048576) + 'MB',
                    limit: Math.round(performance.memory.jsHeapSizeLimit / 1048576) + 'MB'
                } : null
            }
        };

        this.sendToServer(report);
    },

    logError: function(error) {
        if (!this.enabled) {
            // Still throw error even if not logging
            throw error;
        }

        const errorInfo = {
            message: error.message || error.toString(),
            stack: error.stack,
            url: window.location.href,
            timestamp: new Date().toISOString()
        };

        this.log('ERROR', errorInfo);
        this.sendToServer({
            timestamp: new Date().toISOString(),
            message: 'Client Error',
            data: errorInfo
        });

        // Re-throw to maintain normal error flow
        throw error;
    },

    // Enable/disable debug mode
    setEnabled: function(enabled) {
        this.enabled = enabled;
        if (enabled) {
            window.localStorage.setItem('signal_bot_debug', '1');
            console.log('[DEBUG] Debug mode enabled');
        } else {
            window.localStorage.removeItem('signal_bot_debug');
            console.log('[DEBUG] Debug mode disabled');
        }
    }
};

// Setup debug mode monitoring (only when enabled)
if (DEBUG_MODE) {
    // Page lifecycle monitoring
    window.addEventListener('DOMContentLoaded', function() {
        DebugLogger.log('DOM CONTENT LOADED', {
            timing: DebugLogger.getNavigationTiming()
        });
    });

    window.addEventListener('load', function() {
        DebugLogger.log('PAGE LOAD COMPLETE', {
            timing: DebugLogger.getNavigationTiming()
        });
    });

    // Monitor visibility changes
    document.addEventListener('visibilitychange', function() {
        DebugLogger.log('VISIBILITY CHANGE', {
            state: document.visibilityState,
            hidden: document.hidden
        });
    });

    // Monitor errors
    window.addEventListener('error', function(e) {
        DebugLogger.log('GLOBAL ERROR', {
            message: e.message,
            filename: e.filename,
            line: e.lineno,
            col: e.colno
        });
    });

    // Monitor unhandled promise rejections
    window.addEventListener('unhandledrejection', function(e) {
        DebugLogger.log('UNHANDLED REJECTION', {
            reason: e.reason ? e.reason.toString() : 'unknown'
        });
    });

    // Send debug info on page unload if there were issues
    window.addEventListener('beforeunload', function() {
        // Log page unload for debugging
        DebugLogger.log('PAGE UNLOAD', {
            url: window.location.href,
            logs_count: DebugLogger.logs.length
        });
    });
}

// ============================================================================
// STANDARD NOTIFICATION SYSTEM
// ============================================================================

/**
 * Show a notification message to the user
 * @param {string} message - The message to display
 * @param {string} type - Type of notification (success, error, warning, info)
 * @param {number} duration - How long to show the notification (ms)
 */
function showNotification(message, type = 'info', duration = 3000) {
    // Check if notification container exists, create if not
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(container);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        margin-bottom: 10px;
        padding: 12px 20px;
        border-radius: 4px;
        animation: slideIn 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    `;

    // Add to container
    container.appendChild(notification);

    // Debug log if enabled
    if (typeof DebugLogger !== 'undefined' && DebugLogger.enabled) {
        DebugLogger.log('Notification shown', {message, type});
    }

    // Auto-remove after duration
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

// Shorthand functions for common notification types
function showSuccess(message) { showNotification(message, 'success'); }
function showError(message) { showNotification(message, 'error'); }
function showWarning(message) { showNotification(message, 'warning'); }
function showInfo(message) { showNotification(message, 'info'); }

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Debounce function to limit how often a function can be called
 * @param {Function} func - Function to debounce
 * @param {number} wait - Milliseconds to wait
 * @returns {Function} Debounced function
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Set button loading state
 * @param {HTMLElement} btn - Button element
 * @param {boolean} loading - Loading state
 * @param {string} loadingText - Text to show when loading
 */
function setButtonLoading(btn, loading, loadingText = 'Loading...') {
    if (loading) {
        btn.disabled = true;
        btn.dataset.originalText = btn.textContent;
        btn.textContent = loadingText;
    } else {
        btn.disabled = false;
        if (btn.dataset.originalText) {
            btn.textContent = btn.dataset.originalText;
            delete btn.dataset.originalText;
        }
    }
}

// ============================================================================
// TAB NAVIGATION
// ============================================================================

/**
 * Switch to a different tab by updating the URL
 * @param {string} tab - Tab identifier
 */
function switchTab(tab) {
    // Get current path
    const currentPath = window.location.pathname;
    // Navigate to the tab URL
    window.location.href = `${currentPath}?tab=${tab}`;
}

/**
 * Initialize tab navigation for the current page
 */
function initializeTabs() {
    // Handle browser back/forward buttons
    window.addEventListener('popstate', function(event) {
        const params = new URLSearchParams(window.location.search);
        const tab = params.get('tab');
        if (tab) {
            activateTab(tab);
        }
    });

    // Activate current tab on page load
    document.addEventListener('DOMContentLoaded', function() {
        const params = new URLSearchParams(window.location.search);
        const currentTab = params.get('tab');
        if (currentTab) {
            activateTab(currentTab);
        }
    });
}

/**
 * Activate a specific tab (update UI without navigation)
 * @param {string} tabId - Tab identifier
 */
function activateTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Activate selected tab button
    const activeBtn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }

    // Activate selected tab content
    const activeContent = document.getElementById(`${tabId}-tab`);
    if (activeContent) {
        activeContent.classList.add('active');
    }
}

// ============================================================================
// NOTIFICATION FUNCTIONS
// ============================================================================

/**
 * Show a notification message
 * @param {string} message - Message to display
 * @param {string} type - Type of notification (success, error, info, warning)
 * @param {number} duration - How long to show the notification (ms)
 */
function showNotification(message, type = 'info', duration = 3000) {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.notification-toast');
    existingNotifications.forEach(n => n.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-toast alert alert-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 250px;
        padding: 12px 20px;
        animation: slideIn 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    `;

    document.body.appendChild(notification);

    // Auto-remove after duration
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

/**
 * Show success notification
 * @param {string} message - Success message
 */
function showSuccess(message) {
    showNotification(message, 'success');
}

/**
 * Show error notification
 * @param {string} message - Error message
 */
function showError(message) {
    showNotification(message, 'error');
}

/**
 * Show info notification
 * @param {string} message - Info message
 */
function showInfo(message) {
    showNotification(message, 'info');
}

/**
 * Show warning notification
 * @param {string} message - Warning message
 */
function showWarning(message) {
    showNotification(message, 'warning');
}

// ============================================================================
// FORM UTILITIES
// ============================================================================

/**
 * Serialize form data to JSON
 * @param {HTMLFormElement} form - Form element
 * @returns {Object} Form data as object
 */
function serializeForm(form) {
    const formData = new FormData(form);
    const data = {};

    for (const [key, value] of formData.entries()) {
        // Handle multiple values for the same key (like checkboxes)
        if (data[key]) {
            if (!Array.isArray(data[key])) {
                data[key] = [data[key]];
            }
            data[key].push(value);
        } else {
            data[key] = value;
        }
    }

    return data;
}

/**
 * Reset form to default values
 * @param {HTMLFormElement} form - Form element
 */
function resetForm(form) {
    form.reset();
    // Clear any custom error messages
    form.querySelectorAll('.error-message').forEach(el => el.remove());
}

// ============================================================================
// API UTILITIES
// ============================================================================

/**
 * Make an API request with error handling
 * @param {string} url - API endpoint URL
 * @param {Object} options - Fetch options
 * @returns {Promise} Response data
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

/**
 * POST request helper
 * @param {string} url - API endpoint URL
 * @param {Object} data - Data to send
 * @returns {Promise} Response data
 */
async function postRequest(url, data) {
    return apiRequest(url, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

/**
 * GET request helper
 * @param {string} url - API endpoint URL
 * @returns {Promise} Response data
 */
async function getRequest(url) {
    return apiRequest(url, { method: 'GET' });
}

// ============================================================================
// DATE/TIME UTILITIES
// ============================================================================

/**
 * Format timestamp to local time
 * @param {number} timestamp - Unix timestamp (milliseconds)
 * @returns {string} Formatted date/time string
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

/**
 * Get relative time string (e.g., "2 hours ago")
 * @param {number} timestamp - Unix timestamp (milliseconds)
 * @returns {string} Relative time string
 */
function getRelativeTime(timestamp) {
    const now = Date.now();
    const diff = now - timestamp;

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return `${seconds} second${seconds > 1 ? 's' : ''} ago`;
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Add notification animation styles if not already present
document.addEventListener('DOMContentLoaded', function() {
    if (!document.getElementById('common-styles')) {
        const style = document.createElement('style');
        style.id = 'common-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            .tab-content {
                display: none;
            }

            .tab-content.active {
                display: block;
            }

            .tab-btn {
                cursor: pointer;
            }

            .tab-btn.active {
                font-weight: bold;
            }
        `;
        document.head.appendChild(style);
    }
});