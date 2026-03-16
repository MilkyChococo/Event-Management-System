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

  avatar.textContent = initials(user.name);
  name.textContent = user.name;
  email.textContent = user.email;
  accountLink.href = "/account";

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
}
