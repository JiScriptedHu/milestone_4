// ------------------------------------------
// Config
// ------------------------------------------
const API_URL = "http://127.0.0.1:8000/api/auth";

// ------------------------------------------
// View Toggle
// ------------------------------------------
function toggleView() {
    const login = document.getElementById("loginView");
    const signup = document.getElementById("signupView");

    const showLogin = login.style.display === "none";

    login.style.display = showLogin ? "block" : "none";
    signup.style.display = showLogin ? "none" : "block";

    document.querySelectorAll(".error-msg").forEach(el => (el.style.display = "none"));
    document.querySelectorAll("input").forEach(el => (el.value = ""));
}

// ------------------------------------------
// Auth Request
// ------------------------------------------
async function handleAuth(endpoint, username, password, errorId) {
    const errorEl = document.getElementById(errorId);
    errorEl.style.display = "none";

    try {
        const res = await fetch(`${API_URL}/${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || "Authentication failed");

        return data;

    } catch (err) {
        errorEl.innerText = err.message;
        errorEl.style.display = "block";
        throw err;
    }
}

// ------------------------------------------
// Login
// ------------------------------------------
async function handleLogin() {
    const username = document.getElementById("loginUser").value;
    const password = document.getElementById("loginPass").value;

    try {
        const data = await handleAuth("login", username, password, "loginError");
        localStorage.setItem("stockUser", data.username);
        window.location.href = "index.html";
    } catch (_) {}
}

// ------------------------------------------
// Signup
// ------------------------------------------
async function handleSignup() {
    const username = document.getElementById("signupUser").value;
    const password = document.getElementById("signupPass").value;

    try {
        await handleAuth("signup", username, password, "signupError");
        alert("Account created successfully! Please sign in.");
        toggleView();
    } catch (_) {}
}