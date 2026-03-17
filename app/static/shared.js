function formatValidationDetail(detail) {
  if (!detail || typeof detail !== "object") {
    return "Unexpected request failure.";
  }

  const location = Array.isArray(detail.loc) ? detail.loc[detail.loc.length - 1] : "field";
  const fieldLabel = String(location || "field").replaceAll("_", " ");
  const titledField = fieldLabel.charAt(0).toUpperCase() + fieldLabel.slice(1);
  const context = detail.ctx || {};

  if (detail.type === "missing") {
    return `${titledField} is required.`;
  }
  if (detail.type === "string_too_short") {
    return `${titledField} must be at least ${context.min_length || 1} characters.`;
  }
  if (detail.type === "string_too_long") {
    return `${titledField} must be at most ${context.max_length || 1} characters.`;
  }
  if (typeof detail.msg === "string" && detail.msg.startsWith("Value error, ")) {
    return detail.msg.replace("Value error, ", "");
  }
  return detail.msg || "Unexpected request failure.";
}

function extractErrorMessage(payload) {
  if (payload?.error?.message) {
    return payload.error.message;
  }
  if (Array.isArray(payload?.error?.details) && payload.error.details.length) {
    return formatValidationDetail(payload.error.details[0]);
  }
  if (Array.isArray(payload?.detail) && payload.detail.length) {
    return formatValidationDetail(payload.detail[0]);
  }
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }
  return "Unexpected request failure.";
}

export async function api(url, options = {}) {
  const hasJsonBody = options.body && !(options.body instanceof FormData);
  const response = await fetch(url, {
    headers: {
      ...(hasJsonBody ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(extractErrorMessage(payload));
  }
  return payload;
}

export async function getCurrentUser() {
  try {
    return await api("/api/me");
  } catch {
    return null;
  }
}

export function redirectTo(path) {
  window.location.href = path;
}

export function showNotice(target, message, kind = "info") {
  target.textContent = message;
  target.className = `notice ${kind}`;
}

export function clearNotice(target) {
  target.textContent = "";
  target.className = "notice hidden";
}

let toastStack = null;

function ensureToastStack() {
  if (toastStack instanceof HTMLElement && document.body.contains(toastStack)) {
    return toastStack;
  }

  toastStack = document.createElement("div");
  toastStack.className = "toast-stack";
  toastStack.setAttribute("aria-live", "polite");
  toastStack.setAttribute("aria-atomic", "true");
  document.body.appendChild(toastStack);
  return toastStack;
}

export function showToast(message, kind = "info", durationMs = 2800) {
  const stack = ensureToastStack();
  const toast = document.createElement("div");
  toast.className = `toast ${kind}`;
  toast.textContent = message;
  stack.appendChild(toast);

  const dismiss = () => {
    toast.classList.add("is-leaving");
    window.setTimeout(() => {
      toast.remove();
      if (!stack.childElementCount) {
        stack.remove();
      }
    }, 220);
  };

  window.setTimeout(dismiss, durationMs);
  return toast;
}

export function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      });
}

export function toDatetimeLocal(value) {
  return value.slice(0, 16);
}

export function fromDatetimeLocal(value) {
  return `${value}:00`;
}

export function initials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

export async function logoutAndRedirect() {
  await api("/api/auth/logout", { method: "POST" });
  redirectTo("/");
}

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function extractEventIdFromPath() {
  const match = window.location.pathname.match(/\/events\/(\d+)\/view$/);
  return match ? Number(match[1]) : null;
}

export function renderUserAvatar(target, user, imageClass = "avatar-image-fill") {
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const name = String(user?.name || "User").trim() || "User";
  const avatarUrl = String(user?.avatar_url || "").trim();
  const fallbackText = initials(name) || "U";

  target.classList.toggle("has-image", Boolean(avatarUrl));
  target.textContent = "";

  if (!avatarUrl) {
    target.textContent = fallbackText;
    return;
  }

  const avatarImage = document.createElement("img");
  avatarImage.className = imageClass;
  avatarImage.src = avatarUrl;
  avatarImage.alt = `${name} avatar`;
  avatarImage.addEventListener(
    "error",
    () => {
      target.classList.remove("has-image");
      target.textContent = fallbackText;
    },
    { once: true }
  );
  target.appendChild(avatarImage);
}

export function setupAccountMenu(user) {
  const trigger = document.querySelector("[data-testid='account-trigger']");
  const menu = document.querySelector("[data-testid='account-menu']");
  const avatar = document.querySelector("[data-testid='account-avatar']");
  const name = document.querySelector("[data-testid='account-menu-name']");
  const email = document.querySelector("[data-testid='account-menu-email']");
  const accountLink = document.querySelector("[data-testid='account-profile-link']");
  const logout = document.querySelector("[data-testid='account-logout']");

  if (!trigger || !menu || !avatar || !name || !email || !accountLink || !logout) {
    return;
  }

  renderUserAvatar(avatar, user, "account-avatar-image");
  name.textContent = user.name;
  email.textContent = user.email;
  accountLink.href = "/account";

  if (trigger.dataset.accountMenuBound === "true") {
    return;
  }

  trigger.addEventListener("click", () => {
    menu.classList.toggle("hidden");
  });

  logout.addEventListener("click", async () => {
    await logoutAndRedirect();
  });

  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Node)) {
      return;
    }
    if (!menu.contains(event.target) && !trigger.contains(event.target)) {
      menu.classList.add("hidden");
    }
  });

  trigger.dataset.accountMenuBound = "true";
}

function buildGlobalFooterMarkup(user) {
  const normalizedUser = user || { name: "User", email: "email@example.com", role: "user" };
  const isAdmin = normalizedUser.role === "admin";
  const roleLabel = isAdmin ? "Admin" : "User";

  return `
    <footer class="dashboard-site-footer">
      <section class="dashboard-site-footer-panel">
        <div class="dashboard-site-footer-top">
          <a class="dashboard-support-link" href="mailto:thienphu210505@gmail.com?subject=EventHub%20Verify%20Support">
            <span aria-hidden="true">&#9993;</span>
            Contact site support
            <span aria-hidden="true">&#8599;</span>
          </a>
        </div>

        <div class="dashboard-site-footer-grid">
          <section class="dashboard-site-footer-column">
            <p class="dashboard-site-footer-label">Session</p>
            <p class="dashboard-site-footer-copy">
              You are signed in as <strong>${escapeHtml(normalizedUser.name)}</strong> (${escapeHtml(roleLabel)})
              <a class="dashboard-footer-inline-link" href="/account">Account details</a>
              <button class="dashboard-footer-inline-button" data-action="global-footer-logout" type="button">Sign out</button>
            </p>
            <a class="dashboard-footer-link" href="mailto:${escapeHtml(normalizedUser.email)}">Email: ${escapeHtml(normalizedUser.email)}</a>
          </section>

          <section class="dashboard-site-footer-column">
            <p class="dashboard-site-footer-label">About EventHub Verify</p>
            <a class="dashboard-footer-link" href="/aboutus">SE113.Q21 event board</a>
            <p class="dashboard-site-footer-copy">Reserve seats with clearer venue and timing context.</p>
            <p class="dashboard-site-footer-copy">Updates stay more reliable through MongoDB-backed event data.</p>
          </section>

          <section class="dashboard-site-footer-column">
            <p class="dashboard-site-footer-label">Website Information</p>
            <p class="dashboard-site-footer-copy"><strong>Admin: Truong Thien Phu</strong></p>
            <a class="dashboard-footer-link" href="mailto:thienphu210505@gmail.com">Email: thienphu210505@gmail.com</a>
            <a class="dashboard-footer-link" href="tel:0365349036">Contact: 0365349036</a>
            <p class="dashboard-site-footer-copy">Location: Thu Duc, Ho Chi Minh City.</p>
          </section>
        </div>
      </section>
    </footer>
  `;
}

export function setupGlobalFooter(user) {
  const appShell = document.querySelector('.app-shell');
  if (!(appShell instanceof HTMLElement) || !user) {
    return;
  }

  let host = appShell.querySelector('[data-global-footer-host]');
  if (!(host instanceof HTMLElement)) {
    host = document.createElement('div');
    host.setAttribute('data-global-footer-host', '');
    appShell.appendChild(host);
  }

  host.className = 'global-footer-host';
  host.innerHTML = buildGlobalFooterMarkup(user);

  const logoutButton = host.querySelector('[data-action="global-footer-logout"]');
  logoutButton?.addEventListener('click', async () => {
    try {
      await logoutAndRedirect();
    } catch (error) {
      showToast(error.message || 'Could not sign out.', 'error');
    }
  });
}
