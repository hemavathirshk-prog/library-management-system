/**
 * Library Management System - Shared API and UI Helpers
 * Plain JavaScript (No frameworks, no CDN libraries)
 */

function formatCurrency(amount) {
    const val = Number(amount) || 0;
    return `₹${val.toFixed(2)}`;
}

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();
        return {
            ok: response.ok,
            status: response.status,
            data: result
        };
    } catch (err) {
        console.error('API Call Failed:', err);
        return {
            ok: false,
            status: 0,
            data: { error: 'Network or server connection error. Please try again.' }
        };
    }
}

function showAlert(elementId, message, type = 'danger') {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.className = `alert alert-${type}`;
    el.innerText = message;
    el.style.display = 'block';

    // Auto hide success alerts after 4 seconds
    if (type === 'success') {
        setTimeout(() => {
            el.style.display = 'none';
        }, 4000);
    }
}

function hideAlert(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.style.display = 'none';
    }
}

async function checkAuth(requiredRole = null) {
    const res = await apiCall('/api/auth/me');
    if (!res.ok || !res.data.logged_in) {
        window.location.href = '/login?msg=Please login to continue.';
        return null;
    }

    const user = res.data.user;
    if (requiredRole && user.role !== requiredRole) {
        window.location.href = '/login?msg=Access denied for your account role.';
        return null;
    }

    // Update user info elements in the DOM if they exist
    const userNameEl = document.getElementById('nav-user-name');
    if (userNameEl) {
        userNameEl.innerText = `${user.name} (${user.role})`;
    }

    return user;
}

async function handleLogout() {
    await apiCall('/api/auth/logout', 'POST');
    window.location.href = '/login?msg=Logged out successfully.';
}
