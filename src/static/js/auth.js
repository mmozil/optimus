/**
 * auth.js
 * Handles JWT authentication, storage, and API communication.
 */

const API_BASE = '/api/v1/auth';

const auth = {
    // Check if user is logged in AND token is not expired
    isAuthenticated: () => {
        const token = localStorage.getItem('optimus_token');
        if (!token) return false;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            // exp is in seconds; give 60s buffer to avoid edge cases
            return payload.exp && (payload.exp - 60) > (Date.now() / 1000);
        } catch (e) {
            return false;
        }
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

    // Refresh the access token using the stored refresh token
    refreshToken: async () => {
        const refreshToken = localStorage.getItem('optimus_refresh_token');
        if (!refreshToken) return false;
        try {
            const response = await fetch(`${API_BASE}/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            if (!response.ok) return false;
            const data = await response.json();
            localStorage.setItem('optimus_token', data.data.access_token);
            return true;
        } catch (e) {
            return false;
        }
    },

    // Get a valid token — auto-refreshes if expired
    getValidToken: async () => {
        if (auth.isAuthenticated()) {
            return localStorage.getItem('optimus_token');
        }
        // Try to refresh
        const refreshed = await auth.refreshToken();
        if (refreshed) {
            return localStorage.getItem('optimus_token');
        }
        // Token invalid and refresh failed — redirect to login
        auth.logout();
        return null;
    },

    // Login function
    login: async (email, password) => {
        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Credenciais inválidas.');
            }

            const data = await response.json();
            // API returns { status, data: { access_token, refresh_token, user } }
            localStorage.setItem('optimus_token', data.data.access_token);
            // Save refresh token for auto-renewal
            if (data.data.refresh_token) {
                localStorage.setItem('optimus_refresh_token', data.data.refresh_token);
            }
            localStorage.setItem('optimus_user', JSON.stringify(data.data.user));
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
        localStorage.removeItem('optimus_refresh_token');
        localStorage.removeItem('optimus_user');
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
