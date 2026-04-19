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
const SUPPORT_CONTACT = {
  name: "Truong Thien Phu",
  email: "thienphu210505@gmail.com",
  phone: "0365349036",
  location: "Thu Duc, Ho Chi Minh City",
  note: "Primary admin contact for website information, event updates, and user support.",
};
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

export function buildLocationMapUrl(query, latitude = null, longitude = null) {
  const lat = Number(latitude);
  const lng = Number(longitude);
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  }
  const target = String(query || "").trim() || "Ho Chi Minh City";
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(target)}`;
}

const LOCATION_PICKER_DEFAULT_VIEW = { latitude: 10.8231, longitude: 106.6297, zoom: 13 };
const LEAFLET_CSS_ID = "leaflet-location-picker-css";
const LEAFLET_JS_ID = "leaflet-location-picker-js";
const LEAFLET_CSS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_JS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
let locationPickerAssetPromise = null;
let locationPickerState = null;

function parseCoordinateValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  return Math.round(numeric * 1_000_000) / 1_000_000;
}

function hasCoordinates(latitude, longitude) {
  return Number.isFinite(Number(latitude)) && Number.isFinite(Number(longitude));
}

function ensureExternalStylesheet(id, href) {
  const existing = document.getElementById(id);
  if (existing instanceof HTMLLinkElement) {
    return Promise.resolve(existing);
  }
  return new Promise((resolve, reject) => {
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = href;
    link.onload = () => resolve(link);
    link.onerror = () => reject(new Error("Could not load map styles."));
    document.head.appendChild(link);
  });
}

function ensureExternalScript(id, src) {
  const existing = document.getElementById(id);
  if (existing instanceof HTMLScriptElement) {
    if (window.L) {
      return Promise.resolve(existing);
    }
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", () => resolve(existing), { once: true });
      existing.addEventListener("error", () => reject(new Error("Could not load the map library.")), { once: true });
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = id;
    script.src = src;
    script.async = true;
    script.onload = () => resolve(script);
    script.onerror = () => reject(new Error("Could not load the map library."));
    document.head.appendChild(script);
  });
}

async function loadLocationPickerAssets() {
  if (window.L) {
    return window.L;
  }
  if (!locationPickerAssetPromise) {
    locationPickerAssetPromise = Promise.all([
      ensureExternalStylesheet(LEAFLET_CSS_ID, LEAFLET_CSS_URL),
      ensureExternalScript(LEAFLET_JS_ID, LEAFLET_JS_URL),
    ]).then(() => {
      if (!window.L) {
        throw new Error("Map library was loaded but Leaflet is unavailable.");
      }
      return window.L;
    });
  }
  return locationPickerAssetPromise;
}

async function geocodeLocationQuery(query) {
  const target = String(query || "").trim();
  if (!target) {
    return null;
  }
  const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${encodeURIComponent(target)}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error("Could not search this location right now.");
  }
  const payload = await response.json();
  if (!Array.isArray(payload) || !payload.length) {
    return null;
  }
  const first = payload[0];
  return {
    label: String(first.display_name || target).trim(),
    latitude: parseCoordinateValue(first.lat),
    longitude: parseCoordinateValue(first.lon),
  };
}

async function reverseGeocodeLocation(latitude, longitude) {
  const lat = parseCoordinateValue(latitude);
  const lng = parseCoordinateValue(longitude);
  if (lat === null || lng === null) {
    return null;
  }
  const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    return null;
  }
  const payload = await response.json();
  return String(payload?.display_name || "").trim() || null;
}

async function ensureLocationPickerModal() {
  if (locationPickerState?.modal instanceof HTMLElement && document.body.contains(locationPickerState.modal)) {
    await loadLocationPickerAssets();
    return locationPickerState;
  }

  const L = await loadLocationPickerAssets();
  const wrapper = document.createElement("div");
  wrapper.innerHTML = `
    <div id="location-picker-modal" class="admin-modal hidden" aria-hidden="true">
      <div class="admin-modal-backdrop" data-location-action="close"></div>
      <div class="admin-modal-dialog admin-card location-picker-dialog" role="dialog" aria-modal="true" aria-labelledby="location-picker-title">
        <div class="admin-modal-header">
          <div>
            <p class="eyebrow">Location picker</p>
            <h3 id="location-picker-title">Choose a signature location</h3>
            <p class="subtle">Search a venue, then drag the map until the fixed center marker sits on the exact point that should appear after approval.</p>
          </div>
          <button class="secondary-button" type="button" data-location-action="close">Close</button>
        </div>
        <div class="location-picker-stack">
          <label class="full-width">
            Search location
            <div class="location-search-row">
              <input id="location-picker-search" type="text" placeholder="Aster Hall, 14 Mercer Street, District 1" />
              <button class="secondary-button" id="location-picker-search-button" type="button">Search</button>
            </div>
          </label>
          <div class="detail-map-preview location-picker-preview">
            <div id="location-picker-map" class="location-picker-map" aria-label="Interactive map picker"></div>
            <div class="location-picker-center-marker" aria-hidden="true">
              <svg class="location-picker-center-icon" viewBox="0 0 24 24" focusable="false">
                <path d="M12 21s6-5.33 6-11a6 6 0 1 0-12 0c0 5.67 6 11 6 11Zm0-8.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z" fill="currentColor"/>
              </svg>
              <span class="location-picker-center-label">Center marker</span>
            </div>
            <p class="location-picker-helper">Keep the venue you want under the center marker, then confirm.</p>
          </div>
          <div class="location-picker-coordinates">
            <strong id="location-picker-coordinates">Lat --, Lng --</strong>
          </div>
          <p id="location-picker-status" class="subtle">Search a venue to jump there, or place the marker manually.</p>
        </div>
        <div class="button-row">
          <button class="primary-button" id="location-picker-confirm" type="button">Use this location</button>
          <button class="secondary-button danger-button" type="button" data-location-action="close">Cancel</button>
        </div>
      </div>
    </div>
  `;
  const modal = wrapper.firstElementChild;
  if (!(modal instanceof HTMLElement)) {
    throw new Error("Could not create location picker modal.");
  }
  document.body.appendChild(modal);

  const searchInput = modal.querySelector("#location-picker-search");
  const searchButton = modal.querySelector("#location-picker-search-button");
  const mapElement = modal.querySelector("#location-picker-map");
  const coordinates = modal.querySelector("#location-picker-coordinates");
  const status = modal.querySelector("#location-picker-status");
  const confirmButton = modal.querySelector("#location-picker-confirm");

  if (!(searchInput instanceof HTMLInputElement) || !(searchButton instanceof HTMLButtonElement) || !(mapElement instanceof HTMLElement) || !(coordinates instanceof HTMLElement) || !(status instanceof HTMLElement) || !(confirmButton instanceof HTMLButtonElement)) {
    throw new Error("Location picker controls are missing.");
  }

  const map = L.map(mapElement, { zoomControl: true, scrollWheelZoom: true }).setView(
    [LOCATION_PICKER_DEFAULT_VIEW.latitude, LOCATION_PICKER_DEFAULT_VIEW.longitude],
    LOCATION_PICKER_DEFAULT_VIEW.zoom
  );

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map);

  let suppressNextMoveSync = false;

  const close = () => {
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    locationPickerState.activeTarget = null;
  };

  const updateCoordinateText = (latitude, longitude) => {
    coordinates.textContent = `Lat ${latitude.toFixed(6)}, Lng ${longitude.toFixed(6)}`;
  };

  const setSelectedPoint = async (latitude, longitude, options = {}) => {
    const lat = parseCoordinateValue(latitude);
    const lng = parseCoordinateValue(longitude);
    if (lat === null || lng === null) {
      return;
    }
    const { recenter = true, resolvedLabel = "", lookupAddress = false } = options;
    if (recenter) {
      suppressNextMoveSync = true;
      const nextZoom = Math.max(map.getZoom() || LOCATION_PICKER_DEFAULT_VIEW.zoom, 15);
      map.setView([lat, lng], nextZoom);
    }
    updateCoordinateText(lat, lng);
    locationPickerState.selectedCoordinates = { latitude: lat, longitude: lng };

    let label = String(resolvedLabel || "").trim();
    if (!label && lookupAddress) {
      status.textContent = "Resolving the centered point...";
      try {
        label = (await reverseGeocodeLocation(lat, lng)) || "";
      } catch {
        label = "";
      }
    }
    if (label) {
      searchInput.value = label;
      locationPickerState.selectedLabel = label;
      status.textContent = `Centered on ${label}. This exact point will be used for the event.`;
    } else {
      locationPickerState.selectedLabel = searchInput.value.trim();
      status.textContent = "Map centered. Confirm to use this exact point for the event.";
    }
  };

  const syncSelectedPointFromCenter = async (options = {}) => {
    const center = map.getCenter();
    await setSelectedPoint(center.lat, center.lng, { recenter: false, ...options });
  };

  const searchLocation = async () => {
    const query = searchInput.value.trim();
    if (!query) {
      status.textContent = "Enter a venue or address before searching.";
      return;
    }
    status.textContent = `Searching for ${query}...`;
    try {
      const result = await geocodeLocationQuery(query);
      if (!result || result.latitude === null || result.longitude === null) {
        status.textContent = "No matching place was found. Try a more specific address.";
        return;
      }
      await setSelectedPoint(result.latitude, result.longitude, {
        recenter: true,
        resolvedLabel: result.label,
        lookupAddress: false,
      });
    } catch (error) {
      status.textContent = error.message || "Could not search this location.";
    }
  };

  const apply = () => {
    const selectedCoordinates = locationPickerState.selectedCoordinates;
    if (!selectedCoordinates || !locationPickerState.activeTarget?.input) {
      return;
    }
    const label = searchInput.value.trim() || locationPickerState.selectedLabel || `Pinned location (${selectedCoordinates.latitude}, ${selectedCoordinates.longitude})`;
    locationPickerState.activeTarget.input.value = label;
    locationPickerState.activeTarget.input.dispatchEvent(new Event("input", { bubbles: true }));

    const mapUrlInput = locationPickerState.activeTarget.mapUrlInput;
    if (mapUrlInput instanceof HTMLInputElement) {
      mapUrlInput.value = buildLocationMapUrl(label, selectedCoordinates.latitude, selectedCoordinates.longitude);
      mapUrlInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    const latitudeInput = locationPickerState.activeTarget.latitudeInput;
    if (latitudeInput instanceof HTMLInputElement) {
      latitudeInput.value = String(selectedCoordinates.latitude);
      latitudeInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    const longitudeInput = locationPickerState.activeTarget.longitudeInput;
    if (longitudeInput instanceof HTMLInputElement) {
      longitudeInput.value = String(selectedCoordinates.longitude);
      longitudeInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    locationPickerState.activeTarget.input.dataset.locationValidated = "true";
    close();
  };

  map.on("moveend", async () => {
    if (suppressNextMoveSync) {
      suppressNextMoveSync = false;
      return;
    }
    await syncSelectedPointFromCenter({ lookupAddress: true });
  });

  modal.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.dataset.locationAction === "close") {
      close();
    }
  });
  searchButton.addEventListener("click", searchLocation);
  searchInput.addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    await searchLocation();
  });
  confirmButton.addEventListener("click", apply);
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    if (!modal.classList.contains("hidden")) {
      close();
    }
  });

  locationPickerState = {
    modal,
    searchInput,
    searchButton,
    map,
    coordinates,
    status,
    confirmButton,
    selectedCoordinates: {
      latitude: LOCATION_PICKER_DEFAULT_VIEW.latitude,
      longitude: LOCATION_PICKER_DEFAULT_VIEW.longitude,
    },
    selectedLabel: "",
    setSelectedPoint,
    searchLocation,
    activeTarget: null,
  };
  updateCoordinateText(LOCATION_PICKER_DEFAULT_VIEW.latitude, LOCATION_PICKER_DEFAULT_VIEW.longitude);
  return locationPickerState;
}

export function attachLocationPicker({
  inputSelector,
  buttonSelector,
  mapUrlSelector = "",
  latitudeSelector = "",
  longitudeSelector = "",
}) {
  const input = document.querySelector(inputSelector);
  const button = document.querySelector(buttonSelector);
  const mapUrlInput = mapUrlSelector ? document.querySelector(mapUrlSelector) : null;
  const latitudeInput = latitudeSelector ? document.querySelector(latitudeSelector) : null;
  const longitudeInput = longitudeSelector ? document.querySelector(longitudeSelector) : null;
  if (!(input instanceof HTMLInputElement) || !(button instanceof HTMLButtonElement)) {
    return;
  }
  if (button.dataset.locationPickerBound === "true") {
    return;
  }

  const clearPickedCoordinates = () => {
    if (latitudeInput instanceof HTMLInputElement) {
      latitudeInput.value = "";
    }
    if (longitudeInput instanceof HTMLInputElement) {
      longitudeInput.value = "";
    }
    if (mapUrlInput instanceof HTMLInputElement) {
      mapUrlInput.value = "";
    }
    input.dataset.locationValidated = "false";
  };

  input.addEventListener("input", () => {
    input.dataset.locationValidated = "false";
    clearPickedCoordinates();
  });

  button.addEventListener("click", async () => {
    try {
      const state = await ensureLocationPickerModal();
      state.activeTarget = {
        input,
        mapUrlInput: mapUrlInput instanceof HTMLInputElement ? mapUrlInput : null,
        latitudeInput: latitudeInput instanceof HTMLInputElement ? latitudeInput : null,
        longitudeInput: longitudeInput instanceof HTMLInputElement ? longitudeInput : null,
      };
      state.modal.classList.remove("hidden");
      state.modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");
      state.searchInput.value = input.value.trim();
      const latitude = latitudeInput instanceof HTMLInputElement ? parseCoordinateValue(latitudeInput.value) : null;
      const longitude = longitudeInput instanceof HTMLInputElement ? parseCoordinateValue(longitudeInput.value) : null;
      if (latitude !== null && longitude !== null) {
        await state.setSelectedPoint(latitude, longitude, {
          recenter: true,
          resolvedLabel: input.value.trim(),
          lookupAddress: !input.value.trim(),
        });
      } else if (input.value.trim()) {
        await state.searchLocation();
      } else {
        await state.setSelectedPoint(LOCATION_PICKER_DEFAULT_VIEW.latitude, LOCATION_PICKER_DEFAULT_VIEW.longitude, {
          recenter: true,
          resolvedLabel: "",
          lookupAddress: false,
        });
        state.status.textContent = "Drag the map until the fixed center marker sits on the right venue point.";
      }
      window.setTimeout(() => {
        state.map.invalidateSize();
      }, 80);
      state.searchInput.focus();
      state.searchInput.select();
    } catch (error) {
      showToast(error.message || "Could not open the location picker.", "error");
    }
  });

  button.dataset.locationPickerBound = "true";
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

function ensureNotificationBell() {
  const topbarActions = document.querySelector(".topbar-actions");
  if (!(topbarActions instanceof HTMLElement)) {
    return null;
  }

  let anchor = topbarActions.querySelector(".notification-anchor");
  if (!(anchor instanceof HTMLElement)) {
    anchor = document.createElement("div");
    anchor.className = "notification-anchor";
    anchor.innerHTML = `
      <button class="notification-trigger" data-testid="notification-trigger" type="button" aria-label="Notifications">
        <svg class="notification-bell-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M12 3a4 4 0 0 0-4 4v1.06c0 .64-.2 1.27-.57 1.8L6 12.5V14h12v-1.5l-1.43-2.64a3.64 3.64 0 0 1-.57-1.8V7a4 4 0 0 0-4-4Zm0 18a2.77 2.77 0 0 0 2.45-1.5h-4.9A2.77 2.77 0 0 0 12 21Z" fill="currentColor" />
        </svg>
        <span class="notification-badge hidden" data-testid="notification-badge">0</span>
      </button>
      <div class="notification-menu hidden" data-testid="notification-menu">
        <div class="notification-menu-head">
          <strong>Notifications</strong>
          <span class="subtle">Latest updates</span>
        </div>
        <div class="notification-list" data-testid="notification-list">
          <p class="subtle notification-empty">No notifications yet.</p>
        </div>
      </div>
    `;
    const accountAnchor = topbarActions.querySelector(".account-anchor");
    topbarActions.insertBefore(anchor, accountAnchor || null);
  }

  const trigger = anchor.querySelector("[data-testid='notification-trigger']");
  const badge = anchor.querySelector("[data-testid='notification-badge']");
  const menu = anchor.querySelector("[data-testid='notification-menu']");
  const list = anchor.querySelector("[data-testid='notification-list']");
  if (!(trigger instanceof HTMLButtonElement) || !(badge instanceof HTMLElement) || !(menu instanceof HTMLElement) || !(list instanceof HTMLElement)) {
    return null;
  }

  return { anchor, trigger, badge, menu, list };
}

function renderNotificationItems(target, items) {
  if (!(target instanceof HTMLElement)) {
    return;
  }

  if (!Array.isArray(items) || !items.length) {
    target.innerHTML = '<p class="subtle notification-empty">No notifications yet.</p>';
    return;
  }

  target.innerHTML = items
    .map(
      (item) => `
        <a class="notification-item ${item.is_read ? "" : "is-unread"}" href="${escapeHtml(item.link || "/activity")}">
          <div class="notification-item-copy">
            <strong>${escapeHtml(item.title || "Notification")}</strong>
            <p>${escapeHtml(item.body || "")}</p>
          </div>
          <div class="notification-item-foot">
            <time class="notification-item-time">${escapeHtml(formatDateTime(item.created_at || ""))}</time>
            ${item.action_label ? `<span class="notification-item-action">${escapeHtml(item.action_label)}</span>` : ""}
          </div>
        </a>
      `
    )
    .join("");
}

function updateNotificationBadge(badge, unreadCount) {
  if (!(badge instanceof HTMLElement)) {
    return;
  }
  const count = Math.max(Number(unreadCount || 0), 0);
  badge.textContent = count > 99 ? "99+" : String(count);
  badge.classList.toggle("hidden", count === 0);
}

function markRenderedNotificationsRead(list) {
  if (!(list instanceof HTMLElement)) {
    return;
  }
  list.querySelectorAll(".notification-item.is-unread").forEach((item) => item.classList.remove("is-unread"));
}

async function refreshNotificationMenu(shell) {
  if (!shell) {
    return { unread_count: 0, items: [] };
  }
  const payload = await api("/api/me/notifications");
  renderNotificationItems(shell.list, payload.items || []);
  updateNotificationBadge(shell.badge, payload.unread_count || 0);
  shell.trigger.dataset.unreadCount = String(payload.unread_count || 0);
  return payload;
}

export function requestNotificationRefresh() {
  window.dispatchEvent(new CustomEvent("eventhub:notifications-refresh"));
}

function setupNotificationMenu() {
  const shell = ensureNotificationBell();
  if (!shell) {
    return null;
  }

  if (shell.trigger.dataset.notificationMenuBound !== "true") {
    shell.trigger.addEventListener("click", async () => {
      const accountMenu = document.querySelector("[data-testid='account-menu']");
      accountMenu?.classList.add("hidden");

      const willOpen = shell.menu.classList.contains("hidden");
      shell.menu.classList.toggle("hidden");
      if (!willOpen) {
        return;
      }

      try {
        const payload = await refreshNotificationMenu(shell);
        if (Number(payload.unread_count || 0) > 0) {
          await api("/api/me/notifications/read-all", { method: "POST" });
          updateNotificationBadge(shell.badge, 0);
          shell.trigger.dataset.unreadCount = "0";
          markRenderedNotificationsRead(shell.list);
        }
      } catch (error) {
        shell.list.innerHTML = `<p class="subtle notification-empty">${escapeHtml(error.message || "Could not load notifications right now.")}</p>`;
      }
    });

    document.addEventListener("click", (event) => {
      if (!(event.target instanceof Node)) {
        return;
      }
      if (!shell.menu.contains(event.target) && !shell.trigger.contains(event.target)) {
        shell.menu.classList.add("hidden");
      }
    });

    window.addEventListener("eventhub:notifications-refresh", () => {
      void refreshNotificationMenu(shell).catch(() => {
        updateNotificationBadge(shell.badge, 0);
      });
    });

    shell.trigger.dataset.notificationMenuBound = "true";
  }

  void refreshNotificationMenu(shell).catch(() => {
    updateNotificationBadge(shell.badge, 0);
  });
  return shell;
}

function syncSharedModalLock() {
  const hasOpenModal = Boolean(document.querySelector(".admin-modal:not(.hidden)"));
  document.body.classList.toggle("modal-open", hasOpenModal);
}

function ensureIssueReporterShell() {
  let root = document.querySelector("[data-issue-report-root]");
  if (!(root instanceof HTMLElement)) {
    root = document.createElement("div");
    root.setAttribute("data-issue-report-root", "");
    root.innerHTML = `
      <button class="issue-report-trigger" data-testid="issue-report-trigger" type="button" aria-label="Raise issue">
        <span class="issue-report-trigger-mark" aria-hidden="true">!</span>
      </button>
      <div id="issue-report-modal" class="admin-modal hidden" aria-hidden="true">
        <div class="admin-modal-backdrop" data-issue-report-action="close"></div>
        <div class="admin-modal-dialog admin-card issue-report-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="issue-report-title-heading">
          <div class="admin-modal-header">
            <div>
              <p class="eyebrow">Raise issue</p>
              <h3 id="issue-report-title-heading">Send an issue report to admin</h3>
              <p class="subtle issue-report-copy">Describe the problem clearly so the admin can review it from the right page context.</p>
            </div>
            <button class="secondary-button" id="issue-report-close" type="button" data-issue-report-action="close">Close</button>
          </div>
          <form id="issue-report-form" class="form-grid admin-modal-form">
            <label>
              Issue title
              <input id="issue-report-title" type="text" minlength="4" maxlength="120" placeholder="Ticket quantity did not update" required />
            </label>
            <label>
              Category
              <select id="issue-report-category">
                <option value="General">General</option>
                <option value="Reservation">Reservation</option>
                <option value="Billing">Billing</option>
                <option value="UI">UI</option>
                <option value="Notification">Notification</option>
              </select>
            </label>
            <label class="full-width">
              What happened?
              <textarea id="issue-report-description" rows="5" minlength="10" maxlength="1500" placeholder="Explain the issue, what you expected, and what actually happened." required></textarea>
            </label>
            <div class="button-row issue-report-actions full-width">
              <button class="secondary-button danger-button" id="issue-report-cancel" type="button" data-issue-report-action="close">Cancel</button>
              <button class="primary-button" id="issue-report-submit" type="submit">Send report</button>
            </div>
          </form>
        </div>
      </div>
    `;
    document.body.appendChild(root);
  }

  const trigger = root.querySelector("[data-testid='issue-report-trigger']");
  const modal = root.querySelector("#issue-report-modal");
  const form = root.querySelector("#issue-report-form");
  const closeButton = root.querySelector("#issue-report-close");
  const cancelButton = root.querySelector("#issue-report-cancel");
  const titleInput = root.querySelector("#issue-report-title");
  const categoryInput = root.querySelector("#issue-report-category");
  const descriptionInput = root.querySelector("#issue-report-description");

  if (
    !(trigger instanceof HTMLButtonElement) ||
    !(modal instanceof HTMLElement) ||
    !(form instanceof HTMLFormElement) ||
    !(closeButton instanceof HTMLButtonElement) ||
    !(cancelButton instanceof HTMLButtonElement) ||
    !(titleInput instanceof HTMLInputElement) ||
    !(categoryInput instanceof HTMLSelectElement) ||
    !(descriptionInput instanceof HTMLTextAreaElement)
  ) {
    return null;
  }

  return { root, trigger, modal, form, closeButton, cancelButton, titleInput, categoryInput, descriptionInput };
}

function ensureContactSupportShell(issueShell) {
  if (!issueShell?.root || !(issueShell.trigger instanceof HTMLButtonElement)) {
    return null;
  }

  let trigger = issueShell.root.querySelector("[data-testid='contact-admin-trigger']");
  if (!(trigger instanceof HTMLButtonElement)) {
    trigger = document.createElement("button");
    trigger.className = "contact-support-trigger";
    trigger.type = "button";
    trigger.setAttribute("data-testid", "contact-admin-trigger");
    trigger.setAttribute("aria-label", "Contact admin");
    trigger.innerHTML = `
      <span class="contact-support-trigger-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.9.33 1.78.63 2.62a2 2 0 0 1-.45 2.11L8 9.91a16 16 0 0 0 6.09 6.09l1.46-1.29a2 2 0 0 1 2.11-.45c.84.3 1.72.51 2.62.63A2 2 0 0 1 22 16.92Z" />
        </svg>
      </span>
    `;
    issueShell.root.insertBefore(trigger, issueShell.trigger);
  }

  let modal = issueShell.root.querySelector("#contact-admin-modal");
  if (!(modal instanceof HTMLElement)) {
    modal = document.createElement("div");
    modal.id = "contact-admin-modal";
    modal.className = "admin-modal hidden";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="admin-modal-backdrop" data-contact-admin-action="close"></div>
      <div class="admin-modal-dialog admin-card contact-admin-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="contact-admin-title-heading">
        <div class="admin-modal-header">
          <div>
            <p class="eyebrow">Contact</p>
            <h3 id="contact-admin-title-heading">Admin contact</h3>
            <p class="subtle issue-report-copy">Reach the admin directly if you need booking support, event information, or a quick follow-up.</p>
          </div>
          <button class="secondary-button" id="contact-admin-close" type="button" data-contact-admin-action="close">Close</button>
        </div>
        <section class="contact-admin-card">
          <p class="eyebrow">Primary admin</p>
          <h4 class="contact-admin-name">${SUPPORT_CONTACT.name}</h4>
          <p class="subtle contact-admin-copy">${SUPPORT_CONTACT.note}</p>
          <div class="contact-admin-list">
            <a class="contact-admin-link" href="tel:${SUPPORT_CONTACT.phone}">
              <span>Phone</span>
              <strong>${SUPPORT_CONTACT.phone}</strong>
            </a>
            <a class="contact-admin-link" href="mailto:${SUPPORT_CONTACT.email}">
              <span>Email</span>
              <strong>${SUPPORT_CONTACT.email}</strong>
            </a>
            <div class="contact-admin-meta">
              <span>Location</span>
              <strong>${SUPPORT_CONTACT.location}</strong>
            </div>
          </div>
        </section>
        <div class="button-row contact-admin-actions">
          <button class="secondary-button danger-button" id="contact-admin-cancel" type="button" data-contact-admin-action="close">Close</button>
          <a class="primary-button" href="tel:${SUPPORT_CONTACT.phone}">Call admin</a>
        </div>
      </div>
    `;
    issueShell.root.appendChild(modal);
  }

  const closeButton = modal.querySelector("#contact-admin-close");
  const cancelButton = modal.querySelector("#contact-admin-cancel");
  if (!(closeButton instanceof HTMLButtonElement) || !(cancelButton instanceof HTMLButtonElement)) {
    return null;
  }

  return { trigger, modal, closeButton, cancelButton };
}

function openContactSupport(contactShell) {
  if (!contactShell) {
    return;
  }
  contactShell.modal.classList.remove("hidden");
  contactShell.modal.setAttribute("aria-hidden", "false");
  syncSharedModalLock();
}

function closeContactSupport(contactShell) {
  if (!contactShell) {
    return;
  }
  contactShell.modal.classList.add("hidden");
  contactShell.modal.setAttribute("aria-hidden", "true");
  syncSharedModalLock();
}

function openIssueReporter(shell) {
  if (!shell) {
    return;
  }
  shell.modal.classList.remove("hidden");
  shell.modal.setAttribute("aria-hidden", "false");
  syncSharedModalLock();
  window.setTimeout(() => {
    shell.titleInput.focus();
  }, 50);
}

function closeIssueReporter(shell, reset = false) {
  if (!shell) {
    return;
  }
  shell.modal.classList.add("hidden");
  shell.modal.setAttribute("aria-hidden", "true");
  if (reset) {
    shell.form.reset();
    }
  syncSharedModalLock();
}

function setupIssueReporter(user) {
  const existingRoot = document.querySelector("[data-issue-report-root]");
  if (user?.role === "admin") {
    existingRoot?.remove();
    return null;
  }

  const shell = ensureIssueReporterShell();
  if (!shell) {
    return null;
  }

  const contactShell = ensureContactSupportShell(shell);
  if (contactShell && contactShell.trigger.dataset.contactSupportBound !== "true") {
    contactShell.trigger.addEventListener("click", () => {
      closeIssueReporter(shell, false);
      openContactSupport(contactShell);
    });

    contactShell.closeButton.addEventListener("click", () => {
      closeContactSupport(contactShell);
    });

    contactShell.cancelButton.addEventListener("click", () => {
      closeContactSupport(contactShell);
    });

    contactShell.modal.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      if (target.dataset.contactAdminAction === "close") {
        closeContactSupport(contactShell);
      }
    });

    contactShell.trigger.dataset.contactSupportBound = "true";
  }

  if (shell.trigger.dataset.issueReporterBound === "true") {
    return shell;
  }

  shell.trigger.addEventListener("click", () => {
    closeContactSupport(contactShell);
    openIssueReporter(shell);
  });

  shell.closeButton.addEventListener("click", () => {
    closeIssueReporter(shell, true);
  });
  shell.cancelButton.addEventListener("click", () => {
    closeIssueReporter(shell, true);
  });

  shell.modal.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.dataset.issueReportAction === "close") {
      closeIssueReporter(shell, true);
    }
  });

  shell.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!shell.form.reportValidity()) {
      return;
    }

    try {
      await api("/api/me/issues", {
        method: "POST",
        body: JSON.stringify({
          title: shell.titleInput.value.trim(),
          category: shell.categoryInput.value,
          description: shell.descriptionInput.value.trim(),
          page_path: `${window.location.pathname}${window.location.search}`.trim(),
        }),
      });
      closeIssueReporter(shell, true);
      showToast("Issue report sent to admin.");
      requestNotificationRefresh();
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    if (contactShell && !contactShell.modal.classList.contains("hidden")) {
      closeContactSupport(contactShell);
    }
    if (!shell.modal.classList.contains("hidden")) {
      closeIssueReporter(shell, true);
    }
  });

  shell.trigger.dataset.issueReporterBound = "true";
  return shell;
}

export function setupAccountMenu(user) {
  const notificationShell = setupNotificationMenu();
  setupIssueReporter(user);
  const trigger = document.querySelector("[data-testid='account-trigger']");
  const menu = document.querySelector("[data-testid='account-menu']");
  const avatar = document.querySelector("[data-testid='account-avatar']");
  const name = document.querySelector("[data-testid='account-menu-name']");
  const email = document.querySelector("[data-testid='account-menu-email']");
  const accountDetailLink = document.querySelector("[data-testid='account-detail-link']");
  const accountBillingLink = document.querySelector("[data-testid='account-billing-link']");
  const accountSecurityLink = document.querySelector("[data-testid='account-security-link']");
  const logout = document.querySelector("[data-testid='account-logout']");

  if (!trigger || !menu || !avatar || !name || !email || !accountDetailLink || !logout) {
    return;
  }

  renderUserAvatar(avatar, user, "account-avatar-image");
  name.textContent = user.name;
  email.textContent = user.email;
  accountDetailLink.href = "/account";
  if (accountBillingLink instanceof HTMLAnchorElement) {
    accountBillingLink.href = "/account/billing";
  }
  if (accountSecurityLink instanceof HTMLAnchorElement) {
    accountSecurityLink.href = "/account/security";
  }

  if (trigger.dataset.accountMenuBound === "true") {
    return;
  }

  trigger.addEventListener("click", () => {
    notificationShell?.menu.classList.add("hidden");
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







