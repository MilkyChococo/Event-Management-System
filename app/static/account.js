import {
  api,
  escapeHtml,
  formatCurrency,
  formatDateTime,
  fromDatetimeLocal,
  getCurrentUser,
  redirectTo,
  renderUserAvatar,
  setupGlobalFooter,
  setupAccountMenu,
  showToast,
} from "/static/shared.js?v=20260317-global-footer-routes";
import {
  DEFAULT_COUNTRY,
  DEFAULT_DISTRICT,
  DEFAULT_PHONE_DIAL_CODE,
  DEFAULT_PROVINCE,
  PHONE_COUNTRIES,
  getCountryNames,
  getDistricts,
  getPhoneCountryByCode,
  getProvinces,
  getWards,
} from "/static/location-data.js";

const profileName = document.querySelector("[data-testid='profile-name']");
const profileEmail = document.querySelector("#profile-email");
const profileRole = document.querySelector("#profile-role");
const profileAvatar = document.querySelector("[data-testid='profile-avatar']");
const profileNameField = document.querySelector("#profile-name-field");
const profileAge = document.querySelector("#profile-age");
const profileDateOfBirth = document.querySelector("#profile-date-of-birth");
const profilePhoneFlag = document.querySelector("#profile-phone-flag");
const profilePhoneRegion = document.querySelector("#profile-phone-region");
const profilePhone = document.querySelector("#profile-phone");
const profileCountry = document.querySelector("#profile-country");
const profileProvince = document.querySelector("#profile-province");
const profileDistrict = document.querySelector("#profile-district");
const profileWard = document.querySelector("#profile-ward");
const profileStreetAddress = document.querySelector("#profile-street-address");
const profileAddress = document.querySelector("#profile-address");
const ticketList = document.querySelector("[data-testid='account-ticket-list']");
const profileEditTrigger = document.querySelector("#profile-edit-trigger");
const profileModal = document.querySelector("#profile-modal");
const profileModalClose = document.querySelector("#profile-modal-close");
const profileCancelButton = document.querySelector("#profile-cancel");
const profileResetButton = document.querySelector("#profile-reset");
const profileForm = document.querySelector("#profile-form");
const profileAvatarPreview = document.querySelector("#profile-avatar-preview");
const profileAvatarStatus = document.querySelector("#profile-avatar-status");
const profileAvatarBrowse = document.querySelector("#profile-avatar-browse");
const profileAvatarClear = document.querySelector("#profile-avatar-clear");
const profileAvatarApply = document.querySelector("#profile-avatar-apply");
const profileAvatarFile = document.querySelector("#profile-avatar-file");
const profileAvatarUrl = document.querySelector("#profile-avatar-url");
const profileFormEmail = document.querySelector("#profile-form-email");
const profileFormName = document.querySelector("#profile-form-name");
const profileFormDateOfBirth = document.querySelector("#profile-form-date-of-birth");
const profileFormCountry = document.querySelector("#profile-form-country");
const profileFormProvince = document.querySelector("#profile-form-province");
const profileFormDistrict = document.querySelector("#profile-form-district");
const profileFormWard = document.querySelector("#profile-form-ward");
const profileFormStreetAddress = document.querySelector("#profile-form-street-address");
const profileFormPhoneFlag = document.querySelector("#profile-form-phone-flag");
const profileFormPhoneCountry = document.querySelector("#profile-form-phone-country");
const profileFormPhoneLocalNumber = document.querySelector("#profile-form-phone-local-number");
const walletBalance = document.querySelector("#wallet-balance");
const walletTopUpForm = document.querySelector("#wallet-topup-form");
const walletTopUpAmount = document.querySelector("#wallet-topup-amount");
const walletTopUpProvider = document.querySelector("#wallet-topup-provider");
const walletTopUpNote = document.querySelector("#wallet-topup-note");
const walletQrShell = document.querySelector("#wallet-qr-shell");
const walletQrImage = document.querySelector("#wallet-qr-image");
const walletQrPayload = document.querySelector("#wallet-qr-payload");
const walletTransactionList = document.querySelector("#wallet-transaction-list");
const walletExportButton = document.querySelector("#wallet-export-button");
const ownedEventForm = document.querySelector("#owned-event-form");
const ownedEventList = document.querySelector("#owned-event-list");
const securityForm = document.querySelector("#security-form");

const DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg";
const ACTIVE_TICKET_STATUSES = new Set(["confirmed", "checked_in"]);

const state = {
  user: null,
  draftAvatarUrl: "",
  tickets: [],
  walletTransactions: [],
  latestTopUp: null,
  ownedEvents: [],
};

function fillSelect(select, values, preferredValue = "", { allowBlank = false, blankLabel = "Not specified" } = {}) {
  if (!(select instanceof HTMLSelectElement)) {
    return;
  }

  const normalizedValues = Array.isArray(values) ? values.filter(Boolean) : [];
  const options = allowBlank ? ["", ...normalizedValues] : normalizedValues;
  select.innerHTML = options
    .map((value) => {
      const label = value || blankLabel;
      return `<option value="${value}">${label}</option>`;
    })
    .join("");

  if (!options.length) {
    return;
  }

  const nextValue = options.includes(preferredValue) ? preferredValue : options[0];
  select.value = nextValue;
}

function syncPhoneCountryPreview() {
  if (!(profileFormPhoneCountry instanceof HTMLSelectElement) || !profileFormPhoneFlag) {
    return;
  }

  const selectedPhoneCountry = getPhoneCountryByCode(profileFormPhoneCountry.value || DEFAULT_PHONE_DIAL_CODE);
  profileFormPhoneFlag.className = `flag-badge flag-${selectedPhoneCountry.flag}`;
  profileFormPhoneFlag.setAttribute("aria-label", selectedPhoneCountry.name);
}

function syncWardOptions(preferredValue = "") {
  if (!(profileFormCountry instanceof HTMLSelectElement) || !(profileFormProvince instanceof HTMLSelectElement) || !(profileFormDistrict instanceof HTMLSelectElement)) {
    return;
  }

  const wards = getWards(profileFormCountry.value, profileFormProvince.value, profileFormDistrict.value);
  fillSelect(profileFormWard, wards, preferredValue || "", { allowBlank: true });
}

function syncDistrictOptions(preferredValue = "", preferredWard = "") {
  if (!(profileFormCountry instanceof HTMLSelectElement) || !(profileFormProvince instanceof HTMLSelectElement)) {
    return;
  }

  const districts = getDistricts(profileFormCountry.value, profileFormProvince.value);
  fillSelect(profileFormDistrict, districts, preferredValue || DEFAULT_DISTRICT);
  syncWardOptions(preferredWard);
}

function syncProvinceOptions(preferredValue = "", preferredDistrict = "", preferredWard = "") {
  if (!(profileFormCountry instanceof HTMLSelectElement)) {
    return;
  }

  const provinces = getProvinces(profileFormCountry.value);
  fillSelect(profileFormProvince, provinces, preferredValue || DEFAULT_PROVINCE);
  syncDistrictOptions(preferredDistrict, preferredWard);
}

function initializeProfileLocationControls() {
  fillSelect(profileFormCountry, getCountryNames(), DEFAULT_COUNTRY);
  syncProvinceOptions();

  profileFormCountry?.addEventListener("change", () => syncProvinceOptions());
  profileFormProvince?.addEventListener("change", () => syncDistrictOptions());
  profileFormDistrict?.addEventListener("change", () => syncWardOptions());

  if (profileFormPhoneCountry instanceof HTMLSelectElement) {
    profileFormPhoneCountry.innerHTML = PHONE_COUNTRIES.map(
      (country) => `<option value="${country.dialCode}">${country.dialCode} ${country.name}</option>`
    ).join("");
    profileFormPhoneCountry.value = DEFAULT_PHONE_DIAL_CODE;
    profileFormPhoneCountry.addEventListener("change", syncPhoneCountryPreview);
    syncPhoneCountryPreview();
  }
}

function updateAvatarStatus(message) {
  if (profileAvatarStatus) {
    profileAvatarStatus.textContent = message;
  }
}

function renderDraftAvatar() {
  if (!profileAvatarPreview || !state.user) {
    return;
  }

  renderUserAvatar(
    profileAvatarPreview,
    { name: state.user.name, avatar_url: state.draftAvatarUrl },
    "profile-avatar-preview-image"
  );
  if (profileAvatarClear) {
    profileAvatarClear.disabled = !state.draftAvatarUrl;
  }
}

function setDraftAvatar(avatarUrl, message) {
  state.draftAvatarUrl = String(avatarUrl || "").trim();
  renderDraftAvatar();
  updateAvatarStatus(message);
}

function populateProfile(user) {
  profileName.textContent = user.name;
  profileEmail.textContent = user.email;
  profileRole.textContent = user.role;
  renderUserAvatar(profileAvatar, user, "profile-avatar-image");
  profileNameField.textContent = user.name;
  profileAge.textContent = String(user.age);
  profileDateOfBirth.textContent = user.date_of_birth;
  profilePhoneFlag.className = `flag-badge flag-${user.phone_country_flag || "vn"}`;
  profilePhoneRegion.textContent = `${user.phone_country_code} ${user.phone_country_label}`;
  profilePhone.textContent = user.phone_number;
  profileCountry.textContent = user.country;
  profileProvince.textContent = user.province;
  profileDistrict.textContent = user.district;
  profileWard.textContent = user.ward || "Not specified";
  profileStreetAddress.textContent = user.street_address;
  profileAddress.textContent = user.permanent_address;
  setupAccountMenu(user);
}

function fillProfileForm(user) {
  profileFormEmail.value = user.email;
  profileFormName.value = user.name;
  profileFormDateOfBirth.value = user.date_of_birth;
  fillSelect(profileFormCountry, getCountryNames(), user.country || DEFAULT_COUNTRY);
  syncProvinceOptions(user.province, user.district, user.ward || "");
  profileFormStreetAddress.value = user.street_address;
  if (profileFormPhoneCountry instanceof HTMLSelectElement) {
    profileFormPhoneCountry.value = user.phone_country_code || DEFAULT_PHONE_DIAL_CODE;
  }
  syncPhoneCountryPreview();
  profileFormPhoneLocalNumber.value = user.phone_local_number;
  if (profileAvatarUrl) {
    profileAvatarUrl.value = "";
  }
  setDraftAvatar(
    user.avatar_url || "",
    user.avatar_url
      ? "Current avatar ready. Upload a new image or paste a URL to replace it."
      : "Add a profile photo to personalize your account card and menu avatar."
  );
  if (profileAvatarFile) {
    profileAvatarFile.value = "";
  }
}

function openProfileModal() {
  if (!state.user) {
    return;
  }

  fillProfileForm(state.user);
  profileModal?.classList.remove("hidden");
  profileModal?.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  window.setTimeout(() => {
    profileFormName?.focus();
  }, 0);
}

function closeProfileModal() {
  profileModal?.classList.add("hidden");
  profileModal?.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function buildPayload() {
  const selectedPhoneCountry = getPhoneCountryByCode(profileFormPhoneCountry?.value || DEFAULT_PHONE_DIAL_CODE);
  return {
    name: profileFormName.value.trim(),
    date_of_birth: profileFormDateOfBirth.value,
    country: profileFormCountry.value,
    province: profileFormProvince.value,
    district: profileFormDistrict.value,
    ward: profileFormWard.value,
    street_address: profileFormStreetAddress.value.trim(),
    phone_country_code: selectedPhoneCountry.dialCode,
    phone_country_label: selectedPhoneCountry.name,
    phone_country_flag: selectedPhoneCountry.flag,
    phone_local_number: profileFormPhoneLocalNumber.value.trim(),
    avatar_url: state.draftAvatarUrl,
  };
}

function readAvatarFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || "").trim());
    reader.onerror = () => reject(reader.error || new Error(`Could not read ${file.name}.`));
    reader.readAsDataURL(file);
  });
}

async function applyAvatarFiles(fileList) {
  const file = Array.from(fileList || []).find((item) => item.type.startsWith("image/"));
  if (!file) {
    showToast("Please choose an image file.", "error");
    return;
  }

  try {
    const encoded = await readAvatarFile(file);
    setDraftAvatar(encoded, "Avatar upload ready. Save changes to apply it to your profile.");
  } catch (error) {
    showToast(error.message || "Could not load the selected avatar.", "error");
  }
}

function applyAvatarUrl() {
  const avatarValue = profileAvatarUrl?.value.trim() || "";
  if (!avatarValue) {
    showToast("Enter an avatar URL or static path first.", "error");
    return;
  }

  setDraftAvatar(avatarValue, "Avatar URL ready. Save changes to apply it to your profile.");
  profileAvatarUrl.value = "";
}

function renderWallet() {
  if (!state.user) {
    return;
  }

  if (walletBalance) {
    walletBalance.textContent = formatCurrency(state.user.balance || 0);
  }

  if (!walletTransactionList) {
    return;
  }

  if (!state.walletTransactions.length) {
    walletTransactionList.innerHTML = '<p class="subtle">No wallet activity yet. Top up or reserve an event to see movement here.</p>';
  } else {
    walletTransactionList.innerHTML = state.walletTransactions
      .map(
        (transaction) => `
          <article class="wallet-transaction-item">
            <div>
              <strong>${escapeHtml(transaction.kind.replace(/_/g, " "))}</strong>
              <p class="subtle">${escapeHtml(transaction.note || "Wallet activity")}</p>
            </div>
            <div class="wallet-transaction-meta">
              <span>${escapeHtml(formatDateTime(transaction.created_at))}</span>
              <strong>${escapeHtml(formatCurrency(transaction.amount || 0))}</strong>
            </div>
          </article>
        `
      )
      .join("");
  }

  if (state.latestTopUp && walletQrShell && walletQrImage && walletQrPayload) {
    walletQrShell.classList.remove("hidden");
    walletQrImage.src = state.latestTopUp.qr_image_url;
    walletQrPayload.textContent = state.latestTopUp.qr_payload;
  }
}

function renderOwnedEvents() {
  if (!ownedEventList) {
    return;
  }

  if (!state.ownedEvents.length) {
    ownedEventList.innerHTML = '<p class="subtle">You have not created any personal events yet.</p>';
    return;
  }

  ownedEventList.innerHTML = state.ownedEvents
    .map(
      (event) => `
        <article class="owned-event-item" data-event-id="${event.id}">
          <div>
            <strong>${escapeHtml(event.title)}</strong>
            <p class="subtle">${escapeHtml(formatDateTime(event.start_at))} - ${escapeHtml(event.location)}</p>
            <p class="subtle">${escapeHtml(formatCurrency(event.price))} / ticket - ${escapeHtml(String(event.capacity))} capacity - ${escapeHtml(String(event.registered_count))} reserved</p>
          </div>
          <div class="owned-event-actions">
            <a class="secondary-button" href="/events/${event.id}/view">View detail</a>
            <button class="secondary-button danger-button" data-action="delete-owned-event" data-id="${event.id}" type="button">Delete</button>
          </div>
        </article>
      `
    )
    .join("");
}

async function loadWallet() {
  const wallet = await api("/api/me/wallet");
  state.user = wallet.user;
  state.walletTransactions = wallet.transactions || [];
  populateProfile(state.user);
  renderWallet();
}

async function loadOwnedEvents() {
  state.ownedEvents = await api("/api/me/owned-events");
  renderOwnedEvents();
}

async function handleWalletTopUpSubmit(event) {
  event.preventDefault();
  const response = await api("/api/me/wallet/top-up", {
    method: "POST",
    body: JSON.stringify({
      amount: Number(walletTopUpAmount.value),
      provider: walletTopUpProvider.value.trim(),
      note: walletTopUpNote.value.trim(),
    }),
  });
  state.user = response.user;
  state.latestTopUp = response;
  state.walletTransactions = [response.transaction, ...state.walletTransactions].slice(0, 20);
  populateProfile(state.user);
  renderWallet();
  walletTopUpForm?.reset();
  if (walletTopUpProvider) {
    walletTopUpProvider.value = "QR transfer";
  }
  showToast(response.message || "Wallet topped up successfully.");
}

async function handleOwnedEventSubmit(event) {
  event.preventDefault();
  await api("/api/me/owned-events", {
    method: "POST",
    body: JSON.stringify({
      title: document.querySelector("#owned-event-title").value.trim(),
      description: document.querySelector("#owned-event-description").value.trim(),
      category: document.querySelector("#owned-event-category").value.trim(),
      location: document.querySelector("#owned-event-location").value.trim(),
      start_at: fromDatetimeLocal(document.querySelector("#owned-event-start-at").value),
      capacity: Number(document.querySelector("#owned-event-capacity").value),
      price: Number(document.querySelector("#owned-event-price").value),
    }),
  });
  ownedEventForm?.reset();
  document.querySelector("#owned-event-category").value = "Community";
  await loadOwnedEvents();
  showToast("Your event was created successfully.");
}

async function handleOwnedEventAction(target) {
  if (target.dataset.action !== "delete-owned-event") {
    return;
  }
  const eventId = Number(target.dataset.id);
  if (!eventId) {
    return;
  }
  await api(`/api/me/owned-events/${eventId}`, { method: "DELETE" });
  state.ownedEvents = state.ownedEvents.filter((event) => event.id !== eventId);
  renderOwnedEvents();
  showToast("Owned event deleted.");
}

async function handleSecuritySubmit(event) {
  event.preventDefault();
  const currentPasswordField = document.querySelector("#security-current-password");
  const newPasswordField = document.querySelector("#security-new-password");
  const updatedUser = await api("/api/me/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPasswordField.value,
      new_password: newPasswordField.value,
    }),
  });
  state.user = updatedUser;
  populateProfile(updatedUser);
  securityForm?.reset();
  showToast("Password updated successfully.");
}

function exportBillingHistory() {
  const rows = [
    ["kind", "amount", "balance_delta", "balance_after", "note", "created_at"],
    ...state.walletTransactions.map((transaction) => [
      transaction.kind,
      transaction.amount,
      transaction.balance_delta,
      transaction.balance_after,
      transaction.note,
      transaction.created_at,
    ]),
  ];
  const csv = rows.map((row) => row.map((value) => `"${String(value ?? "").replace(/"/g, '""')}"`).join(",")).join("
");
  createDownload("billing-history.csv", csv, "text/csv;charset=utf-8");
  showToast("Billing export downloaded.");
}

function scrollToSectionHash() {
  if (!window.location.hash) {
    return;
  }
  const target = document.querySelector(window.location.hash);
  if (!(target instanceof HTMLElement)) {
    return;
  }
  window.setTimeout(() => {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 120);
}

function createDownload(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const link = document.createElement("a");
  const objectUrl = URL.createObjectURL(blob);
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}

function toCalendarTimestamp(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return parsed.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function ticketStatusLabel(status) {
  if (status === "checked_in") {
    return "Checked in";
  }
  if (status === "cancelled") {
    return "Cancelled";
  }
  return "Confirmed";
}

function buildTicketQrUrl(payload) {
  return `https://api.qrserver.com/v1/create-qr-code/?size=176x176&data=${encodeURIComponent(payload)}`;
}

function downloadTicketPass(ticket) {
  const lines = [
    `Event: ${ticket.title}`,
    `Status: ${ticketStatusLabel(ticket.status)}`,
    `Ticket: ${ticket.ticket_label}`,
    `Ticket code: ${ticket.ticket_code}`,
    `Quantity: ${ticket.quantity || 1}`,
    `Price: ${formatCurrency(ticket.ticket_price)}`,
    `Total: ${formatCurrency(ticket.total_price || ticket.ticket_price)}`,
    `Attendee: ${ticket.attendee_name}`,
    `Email: ${ticket.attendee_email}`,
    `Phone: ${ticket.attendee_phone}`,
    `Location: ${ticket.location}`,
    `Start time: ${formatDateTime(ticket.start_at)}`,
    `QR payload: ${ticket.qr_payload}`,
  ];
  createDownload(`${ticket.ticket_code}.txt`, lines.join("
"), "text/plain;charset=utf-8");
}

function downloadCalendarInvite(ticket) {
  const startStamp = toCalendarTimestamp(ticket.start_at);
  const startDate = new Date(ticket.start_at);
  const endDate = Number.isNaN(startDate.getTime()) ? new Date() : new Date(startDate.getTime() + 2 * 60 * 60 * 1000);
  const endStamp = toCalendarTimestamp(endDate.toISOString());
  const dtStamp = toCalendarTimestamp(new Date().toISOString());
  const content = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//EventHub Verify//Ticket Calendar//EN",
    "BEGIN:VEVENT",
    `UID:${ticket.ticket_code}@eventhub-verify.local`,
    `DTSTAMP:${dtStamp}`,
    `DTSTART:${startStamp}`,
    `DTEND:${endStamp}`,
    `SUMMARY:${ticket.title}`,
    `LOCATION:${ticket.location}`,
    `DESCRIPTION:Ticket ${ticket.ticket_code} for ${ticket.ticket_label}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("

");
  createDownload(`${ticket.ticket_code}.ics`, content, "text/calendar;charset=utf-8");
}

function renderTickets() {
  if (!ticketList) {
    return;
  }

  if (!state.tickets.length) {
    ticketList.innerHTML = `
      <article class="admin-card ticket-empty-state">
        <p class="eyebrow">No registrations yet</p>
        <h3>No tickets in your account</h3>
        <p class="subtle">Reserve an event from the dashboard to keep the ticket code, QR access, and calendar download in one place.</p>
        <a class="primary-button" href="/dashboard">Explore events</a>
      </article>
    `;
    return;
  }

  ticketList.innerHTML = state.tickets
    .map((ticket) => {
      const statusClass = `is-${ticket.status || "confirmed"}`;
      const isActive = ACTIVE_TICKET_STATUSES.has(ticket.status || "confirmed");
      const qrMarkup = ticket.qr_payload
        ? `<img class="ticket-qr-image" src="${escapeHtml(buildTicketQrUrl(ticket.qr_payload))}" alt="QR code for ${escapeHtml(ticket.ticket_code)}" />`
        : `<div class="ticket-qr-fallback">QR unavailable</div>`;
      return `
        <article class="admin-card ticket-card ${statusClass}" data-ticket-id="${ticket.event_id}">
          <img class="ticket-card-image" src="${escapeHtml(ticket.image_url || DEFAULT_EVENT_IMAGE)}" alt="${escapeHtml(ticket.title)}" />
          <div class="ticket-card-body">
            <div class="ticket-card-header">
              <div>
                <p class="eyebrow">${escapeHtml(ticket.category || "Event")}</p>
                <h3>${escapeHtml(ticket.title)}</h3>
                <p class="subtle">${escapeHtml(formatDateTime(ticket.start_at))} - ${escapeHtml(ticket.location)}</p>
              </div>
              <span class="ticket-status-chip ${statusClass}">${escapeHtml(ticketStatusLabel(ticket.status))}</span>
            </div>
            <div class="ticket-meta-grid">
              <article>
                <span>Ticket</span>
                <strong>${escapeHtml(ticket.ticket_label)}</strong>
              </article>
              <article>
                <span>Ticket code</span>
                <strong>${escapeHtml(ticket.ticket_code)}</strong>
              </article>
              <article>
                <span>Attendee</span>
                <strong>${escapeHtml(ticket.attendee_name || ticket.attendee_email)}</strong>
              </article>
              <article>
                <span>Price</span>
                <strong>${escapeHtml(formatCurrency(ticket.ticket_price))} x ${escapeHtml(String(ticket.quantity || 1))}</strong>
              </article>
              <article>
                <span>Total</span>
                <strong>${escapeHtml(formatCurrency(ticket.total_price || ticket.ticket_price))}</strong>
              </article>
            </div>
            <div class="ticket-qr-row">
              ${qrMarkup}
              <div class="ticket-qr-copy">
                <span>QR payload</span>
                <code>${escapeHtml(ticket.qr_payload || ticket.ticket_code)}</code>
              </div>
            </div>
          </div>
          <div class="ticket-card-actions">
            <a class="secondary-button" href="/events/${ticket.event_id}/view">View event</a>
            <button class="secondary-button" data-action="download-pass" data-id="${ticket.event_id}" type="button">Download pass</button>
            <button class="secondary-button" data-action="add-calendar" data-id="${ticket.event_id}" type="button">Add to calendar</button>
            ${isActive ? `<button class="secondary-button danger-button" data-action="cancel-ticket" data-id="${ticket.event_id}" type="button">Cancel reservation</button>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadTickets() {
  if (!ticketList) {
    return;
  }

  ticketList.innerHTML = '<p class="subtle">Loading ticket access and registration history...</p>';
  state.tickets = await api("/api/me/registrations");
  renderTickets();
}

async function handleTicketAction(target) {
  const eventId = Number(target.dataset.id);
  if (!eventId) {
    return;
  }

  const ticket = state.tickets.find((item) => item.event_id === eventId);
  if (!ticket) {
    return;
  }

  if (target.dataset.action === "download-pass") {
    downloadTicketPass(ticket);
    showToast("Ticket download started.");
    return;
  }

  if (target.dataset.action === "add-calendar") {
    downloadCalendarInvite(ticket);
    showToast("Calendar file downloaded.");
    return;
  }

  if (target.dataset.action === "cancel-ticket") {
    await api(`/api/events/${eventId}/register`, { method: "DELETE" });
    showToast("Reservation cancelled.");
    await loadTickets();
  }
}

async function handleProfileSubmit(event) {
  event.preventDefault();
  try {
    const updatedUser = await api("/api/me", {
      method: "PUT",
      body: JSON.stringify(buildPayload()),
    });
    state.user = updatedUser;
    populateProfile(updatedUser);
    setupGlobalFooter(updatedUser);
    closeProfileModal();
    showToast("Profile updated successfully.");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function boot() {
  const user = await getCurrentUser();
  if (!user) {
    redirectTo("/");
    return;
  }

  initializeProfileLocationControls();
  state.user = user;
  populateProfile(user);
  setupGlobalFooter(user);
  await Promise.all([loadTickets(), loadOwnedEvents()]);

  profileEditTrigger?.addEventListener("click", openProfileModal);
  profileModalClose?.addEventListener("click", closeProfileModal);
  profileCancelButton?.addEventListener("click", closeProfileModal);
  profileResetButton?.addEventListener("click", () => {
    if (!state.user) {
      return;
    }
    fillProfileForm(state.user);
    showToast("Profile form reset.");
  });
  profileAvatarBrowse?.addEventListener("click", () => {
    profileAvatarFile?.click();
  });
  profileAvatarFile?.addEventListener("change", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }
    await applyAvatarFiles(target.files);
  });
  profileAvatarApply?.addEventListener("click", applyAvatarUrl);
  profileAvatarUrl?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    applyAvatarUrl();
  });
  profileAvatarClear?.addEventListener("click", () => {
    setDraftAvatar("", "Avatar removed. Save changes to use initials again.");
    if (profileAvatarUrl) {
      profileAvatarUrl.value = "";
    }
    if (profileAvatarFile) {
      profileAvatarFile.value = "";
    }
  });
  profileModal?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.closest('[data-action="close-profile-modal"]')) {
      closeProfileModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && profileModal && !profileModal.classList.contains("hidden")) {
      closeProfileModal();
    }
  });
  profileForm?.addEventListener("submit", handleProfileSubmit);
  ownedEventForm?.addEventListener("submit", async (event) => {
    try {
      await handleOwnedEventSubmit(event);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  ownedEventList?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const actionTarget = target.closest("[data-action]");
    if (!(actionTarget instanceof HTMLElement)) {
      return;
    }
    try {
      await handleOwnedEventAction(actionTarget);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  ticketList?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const actionTarget = target.closest("[data-action]");
    if (!(actionTarget instanceof HTMLElement)) {
      return;
    }
    try {
      await handleTicketAction(actionTarget);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
}

boot();
