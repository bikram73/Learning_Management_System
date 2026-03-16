const API_BASE = window.location.origin + "/api";
const FLASH_TOAST_KEY = "lms_flash_toast";

function getToken() {
  return localStorage.getItem("lms_token");
}

function getUser() {
  const raw = localStorage.getItem("lms_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setSession(token, user) {
  localStorage.setItem("lms_token", token);
  localStorage.setItem("lms_user", JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem("lms_token");
  localStorage.removeItem("lms_user");
}

function isLoggedIn() {
  return Boolean(getToken() && getUser());
}

function requireAuth(roles = []) {
  const user = getUser();
  if (!user) {
    window.location.href = "/login.html";
    return false;
  }
  if (roles.length && !roles.includes(user.role)) {
    window.location.href = "/dashboard.html";
    return false;
  }
  return true;
}

async function apiFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || "Request failed");
  }

  return payload;
}

function showNotice(element, message, type = "success") {
  showToast(message, type);
  // Keep legacy function calls across pages, but render as toast-only.
}

function showToast(message, type = "success", duration = 2800) {
  let root = document.getElementById("toast-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "toast-root";
    root.className = "toast-root";
    document.body.appendChild(root);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  root.appendChild(toast);

  const removeToast = () => {
    if (toast.parentElement) {
      toast.classList.add("out");
      setTimeout(() => toast.remove(), 220);
    }
  };

  setTimeout(removeToast, duration);
}

function setFlashToast(message, type = "success") {
  const payload = JSON.stringify({ message, type });
  sessionStorage.setItem(FLASH_TOAST_KEY, payload);
}

function consumeFlashToast() {
  const raw = sessionStorage.getItem(FLASH_TOAST_KEY);
  if (!raw) return;

  sessionStorage.removeItem(FLASH_TOAST_KEY);
  try {
    const payload = JSON.parse(raw);
    if (payload?.message) {
      showToast(payload.message, payload.type || "success");
    }
  } catch {
    // Ignore invalid payload and continue without blocking UI.
  }
}

function mountNav() {
  const navLinks = document.getElementById("nav-links");
  if (!navLinks) return;

  const user = getUser();
  if (!user) {
    navLinks.innerHTML = `
      <a class="nav-link" href="/index.html">Home</a>
      <a class="nav-link" href="/login.html">Login</a>
      <a class="btn" href="/signup.html">Get Started</a>
    `;
    return;
  }

  navLinks.innerHTML = `
    <a class="nav-link" href="/dashboard.html">Dashboard</a>
    <a class="nav-link" href="/index.html">Courses</a>
    <button class="btn secondary" id="logout-btn" type="button">Logout</button>
  `;

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await apiFetch("/logout", { method: "POST" });
      } catch {
        // Ignore network/auth errors for logout because token is removed anyway.
      }
      clearSession();
      window.location.href = "/login.html";
    });
  }
}

function fmtCourseCard(course, includeOpenButton = true) {
  const thumb = course.thumbnail || "https://images.unsplash.com/photo-1513258496099-48168024aec0?auto=format&fit=crop&w=900&q=70";
  return `
    <article class="card stagger">
      <img src="${thumb}" alt="${course.title}" style="width:100%;height:170px;object-fit:cover;border-radius:12px;" />
      <h3>${course.title}</h3>
      <p>${course.description}</p>
      <div class="meta">
        <span class="tag">Instructor: ${course.instructor}</span>
        <span class="tag">${course.lessons_count} lessons</span>
      </div>
      ${includeOpenButton ? `<div style="margin-top:12px;"><a class="btn" href="/course.html?id=${course.id}">Open Course</a></div>` : ""}
    </article>
  `;
}

consumeFlashToast();
