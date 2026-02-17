/**
 * auth.js
 * Handles JWT authentication, storage, and API communication.
 */

const API_BASE = '/api/v1/auth';

const auth = {
    // Check if user is logged in
    isAuthenticated: () => {
        const token = localStorage.getItem('optimus_token');
        return !!token;
    },

    // Get current user info from token (decode payload)
    getUser: () => {
        const token = localStorage.getItem('optimus_token');
        if (!token) return null;
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            console.error('Invalid token', e);
            return null;
        }
    },

    // Login function
    login: async (email, password) => {
        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ username: email, password: password })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }

            const data = await response.json();
            localStorage.setItem('optimus_token', data.access_token);
            return { success: true };
        } catch (error) {
            return { success: false, message: error.message };
        }
    },

    // Register function
    register: async (email, password, displayName) => {
        try {
            const response = await fetch(`${API_BASE}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, display_name: displayName })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Registration failed');
            }

            return { success: true };
        } catch (error) {
            return { success: false, message: error.message };
        }
    },

    // Logout function
    logout: () => {
        localStorage.removeItem('optimus_token');
        window.location.href = '/login.html';
    },

    // Attach token to headers
    authHeader: () => {
        const token = localStorage.getItem('optimus_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }
};

// Expose to window
window.auth = auth;
