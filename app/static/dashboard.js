import {
  api,
  attachLocationPicker,
  buildLocationMapUrl,
  escapeHtml,
  formatCurrency,
  formatDateTime,
  fromDatetimeLocal,
  getCurrentUser,
  redirectTo,
  setupGlobalFooter,
  setupAccountMenu,
  showToast,
  toDatetimeLocal,
} from "/static/shared.js?v=20260328-location-coordinates";

const eventGrid = document.querySelector("[data-testid='event-grid']");
const refreshButton = document.querySelector("#refresh-events");
const eventSearchInput = document.querySelector("#event-search");
const eventSearchSubmitButton = document.querySelector("#event-search-submit");
const eventCategoryFilter = document.querySelector("#event-category-filter");
const eventLocationFilter = document.querySelector("#event-location-filter");
const eventPriceFilter = document.querySelector("#event-price-filter");
const eventSortFilter = document.querySelector("#event-sort");
const eventBoardState = document.querySelector("#event-board-state");
const eventMatchList = document.querySelector("#event-match-list");
const welcomeText = document.querySelector("#welcome-text");
const heroBanner = document.querySelector(".hero-banner.hero-banner-stage");
const eventCount = document.querySelector("[data-testid='event-count']");
const roleChip = document.querySelector("[data-testid='user-role-chip']");
const dashboardConsole = document.querySelector("#dashboard-console");
const adminBrandTrigger = document.querySelector("[data-admin-brand='true']");
const adminTopbarNav = document.querySelector("#admin-topbar-nav");
const adminViewPanels = Array.from(document.querySelectorAll("[data-admin-panel]"));
const adminSection = document.querySelector("[data-testid='admin-section']");
const adminManagerList = document.querySelector("#admin-manager-list");
const adminManagerCount = document.querySelector("#admin-manager-count");
const adminAnalysisSummary = document.querySelector("#admin-analysis-summary");
const adminAnalyticsEventCount = document.querySelector("#admin-analytics-event-count");
const adminAnalyticsMarketCount = document.querySelector("#admin-analytics-market-count");
const adminForm = document.querySelector("#admin-form");
const attendeeList = document.querySelector("[data-testid='attendee-list']");
const analyticsTotalRegistrations = document.querySelector("#analytics-total-registrations");
const analyticsTotalRevenue = document.querySelector("#analytics-total-revenue");
const analyticsOccupancyRate = document.querySelector("#analytics-occupancy-rate");
const analyticsAverageTicket = document.querySelector("#analytics-average-ticket");
const analyticsCustomerRatio = document.querySelector("#analytics-customer-ratio");
const analyticsCustomerMix = document.querySelector("#analytics-customer-mix");
const analyticsCountryDistribution = document.querySelector("#analytics-country-distribution");
const analyticsEventGrid = document.querySelector("#admin-event-analytics");
const adminOpenCreateButton = document.querySelector("#admin-open-create");
const adminEventModal = document.querySelector("#admin-event-modal");
const adminModalTitle = document.querySelector("#admin-modal-title");
const adminModalSubtitle = document.querySelector("#admin-modal-subtitle");
const adminModalCloseButton = document.querySelector("#admin-modal-close");
const adminCancelButton = document.querySelector("#admin-cancel");
const adminImageInput = document.querySelector("#admin-image-url");
const adminImageAdd = document.querySelector("#admin-image-add");
const adminImagePreview = document.querySelector("#admin-image-preview");
const adminImageStatus = document.querySelector("#admin-image-status");
const adminImageClear = document.querySelector("#admin-image-clear");
const adminImageGallery = document.querySelector("#admin-image-gallery");
const adminImageFilesInput = document.querySelector("#admin-image-files");
const adminImageDropzone = document.querySelector("#admin-image-dropzone");
const dashboardRegistrationModal = document.querySelector("#dashboard-registration-modal");
const dashboardRegistrationClose = document.querySelector("#dashboard-registration-close");
const dashboardRegistrationCancel = document.querySelector("#dashboard-registration-cancel");
const dashboardRegistrationForm = document.querySelector("#dashboard-registration-form");
const dashboardRegistrationQuantity = document.querySelector("#dashboard-registration-quantity");
const dashboardRegistrationName = document.querySelector("#dashboard-registration-name");
const dashboardRegistrationEmail = document.querySelector("#dashboard-registration-email");
const dashboardRegistrationPhone = document.querySelector("#dashboard-registration-phone");
const dashboardRegistrationSummary = document.querySelector("#dashboard-registration-summary");
const dashboardRegistrationQuantityFocus = document.querySelector("#dashboard-registration-quantity-focus");
const dashboardRegistrationPriceFocus = document.querySelector("#dashboard-registration-price-focus");

const DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg";
const currentPath = window.location.pathname;

const EVENT_SLIDE_INTERVAL_MS = 6000;

const state = {
  user: null,
  events: [],
  adminManagerEvents: [],
  attendees: [],
  analytics: null,
  adminDraftImages: [],
  eventSlideIndex: 0,
  eventSlideTimerId: null,
  analyticsSidebarOpen: false,
  selectedAnalyticsEventId: null,
  adminModalMode: "create",
  adminDraggedImageIndex: null,
  adminDropImageIndex: null,
  adminActiveView: "event-board",
  eventFilters: {
    search: "",
    category: "",
    location: "",
    pricing: "",
    sort: "soonest",
  },
  hasSubmittedSearch: false,
  dashboardRegistrationEventId: null,
};

function toTitleCase(value) {
  if (!value) {
    return "";
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatApprovalStatus(status) {
  if (status === "pending") {
    return "Pending review";
  }
  if (status === "rejected") {
    return "Needs revision";
  }
  return "Approved";
}

function excerpt(text, maxLength = 120) {
  if (!text) {
    return "";
  }
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

function parseLineList(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatLineList(values) {
  return Array.isArray(values) ? values.filter(Boolean).join("\n") : "";
}

function formatTicketTypes(ticketTypes) {
  if (!Array.isArray(ticketTypes) || !ticketTypes.length) {
    return "";
  }

  return ticketTypes
    .map((ticket) => {
      const numericPrice = Number(ticket.price || 0);
      const price = Number.isInteger(numericPrice) ? String(numericPrice) : numericPrice.toFixed(2);
      return [ticket.label, price, ticket.details || ""].join(" | ");
    })
    .join("\n");
}

function parseTicketTypes(value, fallbackPrice = 0) {
  const lines = parseLineList(value);
  if (!lines.length) {
    return [];
  }

  return lines
    .map((line) => {
      const [labelPart = "", pricePart = "", detailsPart = ""] = line.split("|").map((part) => part.trim());
      const numericPrice = Number(pricePart || fallbackPrice || 0);
      return {
        label: labelPart,
        price: Number.isFinite(numericPrice) ? numericPrice : Number(fallbackPrice || 0),
        details: detailsPart,
      };
    })
    .filter((ticket) => ticket.label);
}

function fromDatetimeLocalOptional(value) {
  return value ? fromDatetimeLocal(value) : "";
}

function formatPercent(value) {
  const numeric = Number(value || 0);
  const digits = Number.isInteger(numeric) ? 0 : 1;
  return `${numeric.toFixed(digits)}%`;
}

function getAnalyticsEventId(event) {
  return Number(event?.event_id ?? event?.id ?? 0);
}

function sortVisibleEvents(events, sortKey) {
  const nextEvents = [...events];
  if (sortKey === "latest") {
    return nextEvents.sort((first, second) => new Date(second.start_at).getTime() - new Date(first.start_at).getTime());
  }
  if (sortKey === "price-high") {
    return nextEvents.sort((first, second) => Number(second.price || 0) - Number(first.price || 0));
  }
  if (sortKey === "seats-low") {
    return nextEvents.sort((first, second) => Number(first.seats_left || 0) - Number(second.seats_left || 0));
  }
  return nextEvents.sort((first, second) => new Date(first.start_at).getTime() - new Date(second.start_at).getTime());
}

function getVisibleEvents() {
  return sortVisibleEvents(state.events, "soonest");
}

function getMatchedEvents() {
  const filters = state.eventFilters;
  const searchTerm = filters.search.trim().toLowerCase();
  if (!state.hasSubmittedSearch) {
    return sortVisibleEvents(state.events, filters.sort || "soonest");
  }

  const filteredEvents = state.events.filter((event) => {
    const matchesSearch =
      !searchTerm ||
      [event.title, event.description, event.location, event.category, event.organizer_name]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(searchTerm));
    const matchesCategory = !filters.category || event.category === filters.category;
    const matchesLocation = !filters.location || event.location === filters.location;
    const matchesPricing =
      !filters.pricing ||
      (filters.pricing === "free" ? Number(event.price || 0) <= 0 : Number(event.price || 0) > 0);
    return matchesSearch && matchesCategory && matchesLocation && matchesPricing;
  });

  return sortVisibleEvents(filteredEvents, filters.sort || "soonest");
}

function updateSelectOptions(select, values, preferredValue = "", allLabel = "All") {
  if (!(select instanceof HTMLSelectElement)) {
    return;
  }

  const options = ["", ...values];
  select.innerHTML = options
    .map((value, index) => `<option value="${escapeHtml(value)}">${escapeHtml(value || allLabel)}</option>`)
    .join("");
  select.value = options.includes(preferredValue) ? preferredValue : "";
}

function renderEventFilters() {
  const categories = [...new Set(state.events.map((event) => event.category).filter(Boolean))].sort();
  const locations = [...new Set(state.events.map((event) => event.location).filter(Boolean))].sort();
  updateSelectOptions(eventCategoryFilter, categories, state.eventFilters.category, "All categories");
  updateSelectOptions(eventLocationFilter, locations, state.eventFilters.location, "All locations");
  if (eventSearchInput) {
    eventSearchInput.value = state.eventFilters.search;
  }
  if (eventPriceFilter) {
    eventPriceFilter.value = state.eventFilters.pricing;
  }
  if (eventSortFilter) {
    eventSortFilter.value = state.eventFilters.sort;
  }
}

function renderEventBoardState() {
  if (!eventBoardState) {
    return;
  }

  if (!state.events.length) {
    eventBoardState.textContent = "No events are available yet.";
    return;
  }

  const matchedEvents = getMatchedEvents();
  if (!matchedEvents.length) {
    eventBoardState.textContent = "No events match the current search and filter settings.";
    return;
  }

  if (matchedEvents.length === state.events.length) {
    eventBoardState.textContent = `Showing all ${matchedEvents.length} events.`;
    return;
  }

  eventBoardState.textContent = `Showing ${matchedEvents.length} of ${state.events.length} events.`;
}

function buildEventMatchMarkup(event) {
  const registrationAction = event.is_registered
    ? `<button class="secondary-button" data-action="cancel" data-id="${event.id}" type="button">Cancel reservation</button>`
    : `<button class="primary-button" data-action="register" data-id="${event.id}" type="button" ${event.seats_left === 0 ? "disabled" : ""}>Reserve now</button>`;
  return `
    <article class="event-match-card" data-testid="event-match-${event.id}">
      <div class="event-match-copy">
        <div>
          <h3>${escapeHtml(event.title)}</h3>
          <p class="event-match-time">${escapeHtml(formatDateTime(event.start_at))}</p>
        </div>
        <dl class="event-match-meta">
          <div>
            <dt>Location</dt>
            <dd>${escapeHtml(event.location)}</dd>
          </div>
          <div>
            <dt>Price</dt>
            <dd>${escapeHtml(formatCurrency(event.price))} / ticket</dd>
          </div>
        </dl>
      </div>
      <div class="event-match-actions">
        <a class="detail-link" data-testid="event-match-detail-${event.id}" href="/events/${event.id}/view">View detail</a>
        ${registrationAction}
      </div>
    </article>
  `;
}

function renderEventMatchList() {
  if (!eventMatchList) {
    return;
  }

  eventMatchList.classList.remove("is-placeholder");

  if (!state.events.length) {
    eventMatchList.classList.add("is-placeholder");
    eventMatchList.innerHTML = '<article class="event-match-empty"><strong>No event available</strong><p>The explore panel will fill up once events are added to the board.</p></article>';
    return;
  }

  const matchedEvents = getMatchedEvents();
  if (!matchedEvents.length) {
    eventMatchList.classList.add("is-placeholder");
    eventMatchList.innerHTML = '<article class="event-match-empty"><strong>No event available</strong><p>Try a broader search term or clear one of the filters, then press Search again.</p></article>';
    return;
  }

  eventMatchList.innerHTML = matchedEvents.map((event) => buildEventMatchMarkup(event)).join("");
}

function getEventById(eventId) {
  return state.events.find((event) => Number(event.id) === Number(eventId)) || null;
}

function renderDashboardRegistrationSummary() {
  const selectedEvent = getEventById(state.dashboardRegistrationEventId);
  if (!dashboardRegistrationSummary || !selectedEvent) {
    return;
  }

  const maxQuantity = Math.max(1, Math.min(5, Number(selectedEvent.seats_left || 0) || 1));
  const requestedQuantity = Number(dashboardRegistrationQuantity?.value || 1);
  const quantity = Math.max(1, Math.min(maxQuantity, Number.isFinite(requestedQuantity) ? requestedQuantity : 1));
  if (dashboardRegistrationQuantity) {
    dashboardRegistrationQuantity.value = String(quantity);
    dashboardRegistrationQuantity.max = String(maxQuantity);
  }
  const pricePerTicket = Number(selectedEvent.price || selectedEvent.ticket_types?.[0]?.price || 0);
  const totalPrice = pricePerTicket * quantity;

  if (dashboardRegistrationQuantityFocus) {
    dashboardRegistrationQuantityFocus.innerHTML = `
      <span>Quantity</span>
      <strong>${escapeHtml(String(quantity))} ticket${quantity > 1 ? "s" : ""}</strong>
      <p class="subtle">Limit ${escapeHtml(String(maxQuantity))} for this event.</p>
    `;
  }

  if (dashboardRegistrationPriceFocus) {
    dashboardRegistrationPriceFocus.innerHTML = `
      <span>Price</span>
      <strong>${escapeHtml(formatCurrency(pricePerTicket))} per ticket</strong>
      <p class="subtle">Total ${escapeHtml(formatCurrency(totalPrice))}</p>
    `;
  }

  dashboardRegistrationSummary.innerHTML = `
    <article class="detail-registration-summary-item">
      <span>Event</span>
      <strong>${escapeHtml(selectedEvent.title)}</strong>
    </article>
    <article class="detail-registration-summary-item">
      <span>Attendee</span>
      <strong>${escapeHtml(dashboardRegistrationName?.value.trim() || state.user?.name || "")}</strong>
      <p class="subtle">${escapeHtml(dashboardRegistrationEmail?.value.trim() || state.user?.email || "")}</p>
    </article>
    <article class="detail-registration-summary-item">
      <span>Venue</span>
      <strong>${escapeHtml(selectedEvent.location)}</strong>
      <p class="subtle">${escapeHtml(formatDateTime(selectedEvent.start_at))}</p>
    </article>
  `;
}

function openDashboardRegistrationModal(eventId) {
  const selectedEvent = getEventById(eventId);
  if (!selectedEvent || !dashboardRegistrationModal) {
    return;
  }
  if (selectedEvent.is_registered) {
    showToast("You already have a reservation for this event.");
    return;
  }
  if (selectedEvent.seats_left <= 0) {
    showToast("No seats left for this event.", "error");
    return;
  }

  state.dashboardRegistrationEventId = selectedEvent.id;
  const maxQuantity = Math.max(1, Math.min(5, Number(selectedEvent.seats_left || 0) || 1));
  if (dashboardRegistrationQuantity) {
    dashboardRegistrationQuantity.min = "1";
    dashboardRegistrationQuantity.max = String(maxQuantity);
    dashboardRegistrationQuantity.value = "1";
  }
  dashboardRegistrationName.value = state.user?.name || "";
  dashboardRegistrationEmail.value = state.user?.email || "";
  dashboardRegistrationPhone.value = state.user?.phone_number || "";
  renderDashboardRegistrationSummary();
  dashboardRegistrationModal.classList.remove("hidden");
  dashboardRegistrationModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  dashboardRegistrationQuantity?.focus();
}

function closeDashboardRegistrationModal() {
  dashboardRegistrationModal?.classList.add("hidden");
  dashboardRegistrationModal?.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  dashboardRegistrationForm?.reset();
  if (dashboardRegistrationSummary) {
    dashboardRegistrationSummary.innerHTML = "";
  }
  if (dashboardRegistrationQuantityFocus) {
    dashboardRegistrationQuantityFocus.innerHTML = "";
  }
  if (dashboardRegistrationPriceFocus) {
    dashboardRegistrationPriceFocus.innerHTML = "";
  }
  state.dashboardRegistrationEventId = null;
}

async function handleDashboardRegistrationSubmit(event) {
  event.preventDefault();
  const selectedEvent = getEventById(state.dashboardRegistrationEventId);
  if (!selectedEvent) {
    return;
  }

  const maxQuantity = Math.max(1, Math.min(5, Number(selectedEvent.seats_left || 0) || 1));
  const requestedQuantity = Number(dashboardRegistrationQuantity?.value || 1);
  const quantity = Math.max(1, Math.min(maxQuantity, Number.isFinite(requestedQuantity) ? requestedQuantity : 1));

  const updatedEvent = await api(`/api/events/${selectedEvent.id}/register`, {
    method: "POST",
    body: JSON.stringify({
      quantity,
      attendee_name: dashboardRegistrationName.value.trim(),
      attendee_email: dashboardRegistrationEmail.value.trim(),
      attendee_phone: dashboardRegistrationPhone.value.trim(),
    }),
  });
  updateEventInState(updatedEvent);
  renderEventGrid({ restartTimer: false });
  renderEventSearchPanel();
  closeDashboardRegistrationModal();
  await syncAdminAnalyticsAfterReservation();
  showToast(quantity > 1 ? `${quantity} seats reserved successfully.` : "Seat reserved successfully.");
}
function renderEventSearchPanel() {
  renderEventBoardState();
  renderEventMatchList();
}

function setAdminView(view = "event-board") {
  const isAdmin = state.user?.role === "admin";
  const allowedViews = new Set(["event-board", "manager", "analysis"]);
  const nextView = allowedViews.has(view) ? view : "event-board";
  state.adminActiveView = nextView;

  dashboardConsole?.classList.toggle("is-admin", isAdmin);
  adminTopbarNav?.classList.toggle("hidden", !isAdmin);
  adminBrandTrigger?.classList.toggle("is-active", !isAdmin || nextView === "event-board");
  heroBanner?.classList.toggle("hidden", isAdmin && nextView !== "event-board");

  adminViewPanels.forEach((panel) => {
    const panelView = panel.dataset.adminPanel;
    const shouldShow = isAdmin ? panelView === nextView : panelView === "event-board";
    panel.classList.toggle("hidden", !shouldShow);
  });

  adminTopbarNav?.querySelectorAll("[data-admin-view]").forEach((button) => {
    if (!(button instanceof HTMLElement)) {
      return;
    }
    button.classList.toggle("is-active", button.dataset.adminView === nextView);
  });

  if (isAdmin && nextView === "manager") {
    loadEvents()
      .then(() => {
        renderAdminManagerList();
      })
      .catch((error) => {
        showToast(error.message || "Could not load the event inventory.", "error");
      });
    loadAdminManagerEvents().catch((error) => {
      showToast(error.message || "Could not load the moderation queue.", "error");
    });
  }

  if (isAdmin && nextView === "analysis") {
    loadAdminAnalytics().catch((error) => {
      showToast(error.message || "Could not load analytics.", "error");
    });
  }
}

function normalizeImageList(values) {
  const normalized = [];
  for (const value of values || []) {
    const cleaned = String(value || "").trim();
    if (cleaned && !normalized.includes(cleaned)) {
      normalized.push(cleaned);
    }
  }
  return normalized;
}

function getEventImages(event) {
  const gallery = normalizeImageList(Array.isArray(event?.image_urls) ? event.image_urls : []);
  if (gallery.length) {
    return gallery;
  }
  const primary = String(event?.image_url || "").trim();
  return primary ? [primary] : [DEFAULT_EVENT_IMAGE];
}

function getPrimaryEventImage(event) {
  return getEventImages(event)[0] || DEFAULT_EVENT_IMAGE;
}

function setHeroBannerBackground(event) {
  if (!heroBanner) {
    return;
  }

  const image = event ? getPrimaryEventImage(event) : "";
  heroBanner.style.setProperty("--hero-event-image", image ? `url("${image}")` : "none");
}

function setAdminDraftImages(images) {
  state.adminDraftImages = normalizeImageList(images);
}

function clearAdminImagePicker() {
  if (adminImageInput) {
    adminImageInput.value = "";
  }
  if (adminImageFilesInput) {
    adminImageFilesInput.value = "";
  }
}

function summarizeAdminImageSource(image) {
  if (image.startsWith("data:image/")) {
    const imageType = image.slice(11, image.indexOf(";")) || "upload";
    return `Embedded ${imageType.toUpperCase()} upload`;
  }
  return image.length > 82 ? `${image.slice(0, 79)}...` : image;
}

function setAdminImageDropTarget(index = null) {
  state.adminDropImageIndex = Number.isInteger(index) ? index : null;
  if (!adminImageGallery) {
    return;
  }

  adminImageGallery.querySelectorAll(".admin-image-card").forEach((card) => {
    const cardIndex = Number(card.dataset.index);
    card.classList.toggle(
      "is-drop-target",
      state.adminDropImageIndex !== null && !Number.isNaN(cardIndex) && cardIndex === state.adminDropImageIndex
    );
  });
}

function clearAdminImageDragState() {
  state.adminDraggedImageIndex = null;
  setAdminImageDropTarget(null);
  adminImageGallery?.classList.remove("is-sorting");
  adminImageGallery?.querySelectorAll(".admin-image-card").forEach((card) => {
    card.classList.remove("is-dragging");
  });
}

function renderAdminImageEditor(message = "") {
  if (!adminImagePreview || !adminImageStatus || !adminImageGallery) {
    return;
  }

  const images = state.adminDraftImages;
  const coverImage = images[0] || DEFAULT_EVENT_IMAGE;
  adminImagePreview.src = coverImage;
  adminImagePreview.alt = images.length ? "Cover image preview" : "Default event image preview";
  adminImagePreview.dataset.previewSource = coverImage;
  adminImageStatus.textContent =
    message ||
    (images.length
      ? `${images.length} gallery images ready. The first image is the cover shown on event cards. Drag the cards below to reorder them.`
      : "No custom images yet. Drop photos here, browse from your machine, or add a static path.");

  if (adminImageClear) {
    adminImageClear.disabled = images.length === 0;
  }

  clearAdminImageDragState();
  adminImageDropzone?.classList.remove("is-dragover");

  if (!images.length) {
    adminImageGallery.innerHTML =
      '<p class="subtle">No custom images added yet. Drop one or more images here so viewers can swipe through the event gallery.</p>';
    return;
  }

  adminImageGallery.innerHTML = images
    .map(
      (image, index) => `
        <article class="admin-image-card" data-index="${index}" draggable="true">
          <img class="admin-image-thumb" src="${escapeHtml(image)}" alt="Gallery image ${index + 1}" />
          <div class="admin-image-card-copy">
            <div class="admin-image-card-row">
              <strong>${index === 0 ? "Cover image" : `Gallery image ${index + 1}`}</strong>
              <span class="image-order-chip">Slide ${index + 1}</span>
            </div>
            <p class="subtle">${escapeHtml(summarizeAdminImageSource(image))}</p>
            <p class="admin-image-helper">Drag to reorder. The first image is used as the event cover.</p>
          </div>
          <div class="admin-image-card-actions">
            <button class="secondary-button image-card-button" data-action="cover-image" data-index="${index}" type="button" ${index === 0 ? "disabled" : ""}>${index === 0 ? "Cover" : "Move first"}</button>
            <button class="secondary-button danger-button image-card-button" data-action="remove-image" data-index="${index}" type="button">Delete</button>
          </div>
        </article>
      `
    )
    .join("");
}

function handleAdminImagePreviewError() {
  if (!adminImagePreview || !adminImageStatus) {
    return;
  }

  const attemptedSource = adminImagePreview.dataset.previewSource || DEFAULT_EVENT_IMAGE;
  adminImagePreview.dataset.previewSource = DEFAULT_EVENT_IMAGE;
  adminImagePreview.src = DEFAULT_EVENT_IMAGE;
  adminImagePreview.alt = "Default event image preview";
  adminImageStatus.textContent = `Could not load ${attemptedSource}. Default artwork shown instead.`;
}

function addAdminImageSources(images, successMessage, duplicateMessage) {
  const normalizedImages = normalizeImageList(images);
  if (!normalizedImages.length) {
    renderAdminImageEditor(duplicateMessage);
    return 0;
  }

  const nextImages = normalizeImageList([...state.adminDraftImages, ...normalizedImages]);
  const addedCount = nextImages.length - state.adminDraftImages.length;
  if (!addedCount) {
    renderAdminImageEditor(duplicateMessage);
    return 0;
  }

  setAdminDraftImages(nextImages);
  renderAdminImageEditor(successMessage(addedCount, nextImages.length));
  return addedCount;
}

function addAdminImage() {
  if (!adminImageInput) {
    return;
  }

  const image = adminImageInput.value.trim();
  if (!image) {
    renderAdminImageEditor("Enter an image URL or static path before adding it.");
    return;
  }

  addAdminImageSources(
    [image],
    (addedCount, totalCount) =>
      addedCount === 1
        ? `Added gallery image ${totalCount}. Drag the cards below to choose the cover order.`
        : `Added ${addedCount} gallery images.`,
    `This image is already in the gallery: ${image}`
  );
  clearAdminImagePicker();
}

function readAdminImageFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || "").trim());
    reader.onerror = () => reject(reader.error || new Error(`Could not read ${file.name}.`));
    reader.readAsDataURL(file);
  });
}

async function addAdminImageFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) {
    return;
  }

  const imageFiles = files.filter((file) => file.type.startsWith("image/"));
  const skippedCount = files.length - imageFiles.length;
  if (!imageFiles.length) {
    clearAdminImagePicker();
    renderAdminImageEditor("Only image files can be added to the gallery.");
    return;
  }

  const uploadedImages = [];
  let failedCount = 0;
  for (const file of imageFiles) {
    try {
      const encoded = await readAdminImageFile(file);
      if (encoded) {
        uploadedImages.push(encoded);
      } else {
        failedCount += 1;
      }
    } catch {
      failedCount += 1;
    }
  }

  const nextImages = normalizeImageList([...state.adminDraftImages, ...uploadedImages]);
  const addedCount = nextImages.length - state.adminDraftImages.length;
  if (addedCount) {
    setAdminDraftImages(nextImages);
  }

  const messages = [];
  if (addedCount) {
    messages.push(`Added ${addedCount} uploaded ${addedCount === 1 ? "image" : "images"}.`);
  } else {
    messages.push("All selected images are already in the gallery.");
  }
  if (skippedCount) {
    messages.push(`${skippedCount} non-image ${skippedCount === 1 ? "file was" : "files were"} skipped.`);
  }
  if (failedCount) {
    messages.push(`${failedCount} ${failedCount === 1 ? "image failed" : "images failed"} to load.`);
  }
  messages.push("Drag the cards below to reorder the cover and slide order.");
  clearAdminImagePicker();
  renderAdminImageEditor(messages.join(" "));
}

function removeAdminImage(index) {
  const nextImages = state.adminDraftImages.filter((_, imageIndex) => imageIndex !== index);
  setAdminDraftImages(nextImages);
  renderAdminImageEditor(
    nextImages.length
      ? `Removed image ${index + 1}. The gallery now has ${nextImages.length} images.`
      : "Gallery cleared. The event will fall back to the default artwork when you save."
  );
}

function setAdminCoverImage(index) {
  if (index <= 0 || index >= state.adminDraftImages.length) {
    return;
  }

  const nextImages = [...state.adminDraftImages];
  const [coverImage] = nextImages.splice(index, 1);
  nextImages.unshift(coverImage);
  setAdminDraftImages(nextImages);
  renderAdminImageEditor("Updated cover image. Viewers will see this image first.");
}

function moveAdminImage(fromIndex, toIndex) {
  if (fromIndex < 0 || fromIndex >= state.adminDraftImages.length) {
    clearAdminImageDragState();
    return;
  }

  const insertionIndex = Math.max(0, Math.min(toIndex, state.adminDraftImages.length));
  const normalizedInsertionIndex = insertionIndex > fromIndex ? insertionIndex - 1 : insertionIndex;
  if (normalizedInsertionIndex === fromIndex) {
    clearAdminImageDragState();
    return;
  }

  const nextImages = [...state.adminDraftImages];
  const [movedImage] = nextImages.splice(fromIndex, 1);
  nextImages.splice(normalizedInsertionIndex, 0, movedImage);
  state.adminDraggedImageIndex = null;
  state.adminDropImageIndex = null;
  setAdminDraftImages(nextImages);
  renderAdminImageEditor(
    normalizedInsertionIndex === 0
      ? "Reordered gallery. The dropped image is now the cover."
      : `Reordered gallery. The dropped image is now slide ${normalizedInsertionIndex + 1}.`
  );
}

function getAdminImageDropContext(event) {
  if (!adminImageGallery) {
    return { insertIndex: state.adminDraftImages.length, highlightIndex: null };
  }

  const card = event.target instanceof HTMLElement ? event.target.closest(".admin-image-card") : null;
  if (!(card instanceof HTMLElement)) {
    return { insertIndex: state.adminDraftImages.length, highlightIndex: state.adminDraftImages.length - 1 };
  }

  const index = Number(card.dataset.index);
  if (Number.isNaN(index)) {
    return { insertIndex: state.adminDraftImages.length, highlightIndex: null };
  }

  const cardBounds = card.getBoundingClientRect();
  const insertAfter = event.clientY > cardBounds.top + cardBounds.height / 2;
  return {
    insertIndex: insertAfter ? index + 1 : index,
    highlightIndex: index,
  };
}

function transferIncludesFiles(event) {
  return Array.from(event.dataTransfer?.types || []).includes("Files");
}
function toDistributionMarkup(items, emptyMessage) {
  if (!Array.isArray(items) || !items.length) {
    return `<p class="subtle">${escapeHtml(emptyMessage)}</p>`;
  }

  return items
    .map((item) => {
      const share = Number(item.share || 0);
      const width = share > 0 ? Math.max(share, 6) : 0;
      return `
        <article class="distribution-item">
          <div class="distribution-label-row">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(String(item.count))} - ${escapeHtml(formatPercent(share))}</span>
          </div>
          <div class="distribution-track">
            <span class="distribution-fill" style="width: ${width}%;"></span>
          </div>
        </article>
      `;
    })
    .join("");
}

function clearEventSlideTimer() {
  if (state.eventSlideTimerId === null) {
    return;
  }
  window.clearTimeout(state.eventSlideTimerId);
  state.eventSlideTimerId = null;
}

function buildEventSlideMarkup(event) {
  const registrationAction = event.is_registered
    ? `<button class="secondary-button" data-action="cancel" data-id="${event.id}" type="button">Cancel reservation</button>`
    : `<button class="primary-button" data-action="register" data-id="${event.id}" type="button" ${event.seats_left === 0 ? "disabled" : ""}>Reserve now</button>`;
  const deadlineLabel = event.registration_deadline ? `Register by ${formatDateTime(event.registration_deadline)}` : "Open registration";
  const seatWarning = event.seats_left > 0 && event.seats_left <= 3 ? `<span class="pill pill-warning">Only ${escapeHtml(String(event.seats_left))} seats left</span>` : "";
  return `
    <section class="event-slide is-active" data-slide-id="${event.id}" data-testid="event-slide-${event.id}">
      <article class="event-card event-card-editorial event-card-editorial-compact" data-testid="event-card-${event.id}">
        <img src="${escapeHtml(getPrimaryEventImage(event))}" alt="${escapeHtml(event.title)}" />
        <div class="event-card-body event-slide-body">
          <div class="event-card-header-row">
            <div>
              <p class="eyebrow">Featured Event</p>
              <h3>${escapeHtml(event.title)}</h3>
            </div>
            <span class="event-price-badge">${escapeHtml(formatCurrency(event.price))} / ticket</span>
          </div>
          <div class="card-pills">
            <span class="pill">${escapeHtml(event.category || "Event")}</span>
            <span class="pill">${escapeHtml(event.event_format || "Offline")}</span>
            <span class="pill">${escapeHtml(deadlineLabel)}</span>
            ${seatWarning}
          </div>
          <p class="hero-copy event-summary">${escapeHtml(excerpt(event.description, 140))}</p>
          <div class="event-slide-facts">
            <article>
              <span>Date & Time</span>
              <strong>${escapeHtml(formatDateTime(event.start_at))}</strong>
            </article>
            <article>
              <span>Location</span>
              <strong>${escapeHtml(event.location)}</strong>
            </article>
            <article>
              <span>Organizer</span>
              <strong>${escapeHtml(event.organizer_name || "EventHub Verify Studio")}</strong>
            </article>
          </div>
          <div class="button-row">
            <a class="detail-link" data-testid="detail-link-${event.id}" href="/events/${event.id}/view">View detail</a>
            ${registrationAction}
          </div>
        </div>
      </article>
    </section>
  `;
}

function updateEventSlidePosition(restartTimer = false) {
  renderEventGrid({ restartTimer });
}

function startEventSlideTimer() {
  clearEventSlideTimer();
  const visibleEvents = getVisibleEvents();
  if (visibleEvents.length <= 1) {
    return;
  }
  if (state.user?.role === "admin" && state.adminActiveView !== "event-board") {
    return;
  }

  state.eventSlideTimerId = window.setTimeout(() => {
    state.eventSlideIndex = (state.eventSlideIndex + 1) % visibleEvents.length;
    updateEventSlidePosition(false);
    startEventSlideTimer();
  }, EVENT_SLIDE_INTERVAL_MS);
}

function goToEventSlide(index, restartTimer = true) {
  const visibleEvents = getVisibleEvents();
  if (!visibleEvents.length) {
    return;
  }

  const total = visibleEvents.length;
  state.eventSlideIndex = ((index % total) + total) % total;
  updateEventSlidePosition(false);
  if (restartTimer) {
    startEventSlideTimer();
  }
}

function renderEventGrid(options = {}) {
  if (!eventGrid || !eventCount) {
    return;
  }

  const visibleEvents = getVisibleEvents();
  const { restartTimer = true } = options;
  if (restartTimer) {
    clearEventSlideTimer();
  }

  if (!state.events.length) {
    setHeroBannerBackground(null);
    eventGrid.innerHTML = '<section class="admin-card ticket-empty-state"><p class="eyebrow">Empty board</p><h3>No events available yet</h3><p class="subtle">The board will fill up as soon as an admin adds events to MongoDB.</p></section>';
    eventCount.textContent = "0";
    state.eventSlideIndex = 0;
    return;
  }

  if (!visibleEvents.length) {
    setHeroBannerBackground(null);
    eventGrid.innerHTML = '<section class="admin-card ticket-empty-state"><p class="eyebrow">No match</p><h3>No events fit this search</h3><p class="subtle">Try clearing one filter, changing the sort, or using a broader search term.</p></section>';
    eventCount.textContent = "0";
    state.eventSlideIndex = 0;
    return;
  }

  state.eventSlideIndex = Math.min(state.eventSlideIndex, visibleEvents.length - 1);
  eventCount.textContent = String(visibleEvents.length);
  const activeEvent = visibleEvents[state.eventSlideIndex];
  setHeroBannerBackground(activeEvent);
  eventGrid.innerHTML = `
    <div class="event-slider-shell" data-testid="event-slider-shell">
      <div class="event-slider-stage" aria-live="polite">
        ${visibleEvents.length > 1 ? `
          <button class="event-slide-nav is-prev" data-slide-nav="prev" type="button" aria-label="Previous event">
            <span aria-hidden="true">&#8592;</span>
          </button>
          <button class="event-slide-nav is-next" data-slide-nav="next" type="button" aria-label="Next event">
            <span aria-hidden="true">&#8594;</span>
          </button>
        ` : ""}
        ${buildEventSlideMarkup(activeEvent)}
      </div>
      <div class="event-slide-dots" data-role="event-slide-dots">
        ${visibleEvents
          .map(
            (event, index) => `
              <button
                class="event-slide-dot ${index === state.eventSlideIndex ? "is-active" : ""}"
                data-slider-index="${index}"
                data-testid="event-slide-dot-${event.id}"
                type="button"
                aria-label="Show ${escapeHtml(event.title)}"
                aria-pressed="${index === state.eventSlideIndex ? "true" : "false"}"
              ></button>
            `
          )
          .join("")}
      </div>
    </div>
  `;

  if (restartTimer) {
    startEventSlideTimer();
  }
}

function setAdminModalCopy(mode, eventTitle = "") {
  if (!adminModalTitle || !adminModalSubtitle) {
    return;
  }

  if (mode === "edit") {
    adminModalTitle.textContent = "Edit event";
    adminModalSubtitle.textContent = eventTitle
      ? `Update ${eventTitle} and save the changes back to MongoDB.`
      : "Update the selected event and save the changes back to MongoDB.";
    return;
  }

  adminModalTitle.textContent = "Create event";
  adminModalSubtitle.textContent = "Add a new event and save it straight to MongoDB.";
}

function fillAdminForm(event) {
  document.querySelector("#admin-event-id").value = event.id;
  document.querySelector("#admin-title").value = event.title;
  document.querySelector("#admin-location").value = event.location;
  document.querySelector("#admin-latitude").value = event.latitude ?? "";
  document.querySelector("#admin-longitude").value = event.longitude ?? "";
  document.querySelector("#admin-description").value = event.description;
  document.querySelector("#admin-category").value = event.category || "";
  document.querySelector("#admin-event-format").value = event.event_format || "Offline";
  document.querySelector("#admin-venue-details").value = event.venue_details || "";
  document.querySelector("#admin-start-at").value = toDatetimeLocal(event.start_at);
  document.querySelector("#admin-registration-deadline").value = event.registration_deadline ? toDatetimeLocal(event.registration_deadline) : "";
  document.querySelector("#admin-capacity").value = event.capacity;
  document.querySelector("#admin-price").value = event.price;
  document.querySelector("#admin-organizer-name").value = event.organizer_name || "";
  document.querySelector("#admin-speaker-lineup").value = formatLineList(event.speaker_lineup || []);
  document.querySelector("#admin-ticket-types").value = formatTicketTypes(event.ticket_types || []);
  document.querySelector("#admin-map-url").value = event.map_url || "";
  document.querySelector("#admin-contact-email").value = event.contact_email || "";
  document.querySelector("#admin-contact-phone").value = event.contact_phone || "";
  document.querySelector("#admin-refund-policy").value = event.refund_policy || "";
  document.querySelector("#admin-check-in-policy").value = event.check_in_policy || "";
  setAdminDraftImages(getEventImages(event).filter((image) => image !== DEFAULT_EVENT_IMAGE));
  clearAdminImagePicker();
  renderAdminImageEditor(
    state.adminDraftImages.length
      ? `Editing ${state.adminDraftImages.length} gallery images for ${event.title}.`
      : "This event currently uses the default artwork. Add one or more images for the viewer carousel."
  );
}

function resetAdminForm() {
  adminForm.reset();
  document.querySelector("#admin-event-id").value = "";
  document.querySelector("#admin-price").value = 0;
  document.querySelector("#admin-event-format").value = "Offline";
  document.querySelector("#admin-registration-deadline").value = "";
  document.querySelector("#admin-category").value = "";
  document.querySelector("#admin-organizer-name").value = "";
  document.querySelector("#admin-speaker-lineup").value = "";
  document.querySelector("#admin-ticket-types").value = "";
  document.querySelector("#admin-map-url").value = "";
  document.querySelector("#admin-latitude").value = "";
  document.querySelector("#admin-longitude").value = "";
  document.querySelector("#admin-contact-email").value = "";
  document.querySelector("#admin-contact-phone").value = "";
  document.querySelector("#admin-refund-policy").value = "";
  document.querySelector("#admin-check-in-policy").value = "";
  setAdminDraftImages([]);
  clearAdminImagePicker();
  renderAdminImageEditor();
}

function openAdminModal(mode = "create", event = null) {
  state.adminModalMode = mode;
  if (mode === "edit" && event) {
    fillAdminForm(event);
    setAdminModalCopy("edit", event.title);
  } else {
    resetAdminForm();
    setAdminModalCopy("create");
  }
  adminEventModal?.classList.remove("hidden");
  adminEventModal?.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeAdminModal(reset = true) {
  if (reset) {
    resetAdminForm();
    setAdminModalCopy("create");
  }
  adminEventModal?.classList.add("hidden");
  adminEventModal?.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function renderAttendees(emptyMessage = "No attendees available for the selected event.") {
  if (!attendeeList) {
    return;
  }

  if (!state.attendees.length) {
    attendeeList.innerHTML = `<p>${escapeHtml(emptyMessage)}</p>`;
    return;
  }

  attendeeList.innerHTML = `<ul>${state.attendees
    .map(
      (attendee) =>
        `<li>${escapeHtml(attendee.name)} - ${escapeHtml(attendee.email)} - ${escapeHtml(attendee.registered_at)}</li>`
    )
    .join("")}</ul>`;
}

function renderAdminManagerList() {
  if (!adminManagerList) {
    return;
  }

  const events = state.user?.role === "admin" ? (state.adminManagerEvents.length ? state.adminManagerEvents : state.events) : [];
  if (adminManagerCount) {
    adminManagerCount.textContent = `${events.length} ${events.length === 1 ? "event" : "events"}`;
  }

  if (!events.length) {
    adminManagerList.innerHTML = `
      <section class="admin-manager-empty">
        <p class="eyebrow">Moderation queue</p>
        <p class="subtle">There are no event requests waiting for review right now.</p>
      </section>
    `;
    return;
  }

  adminManagerList.innerHTML = events
    .map((event) => {
      const status = String(event.approval_status || "approved").toLowerCase();
      const statusLabel = formatApprovalStatus(status);
      const statusClass = `is-${status}`;
      const moderationActions = [];
      if (status === "pending" || status === "rejected") {
        moderationActions.push(
          `<button class="secondary-button image-card-button" data-action="approve-request" data-id="${event.id}" type="button">Approve</button>`
        );
      }
      if (status === "pending" || status === "approved") {
        moderationActions.push(
          `<button class="secondary-button danger-button image-card-button" data-action="reject-request" data-id="${event.id}" type="button">${status === "approved" ? "Unpublish" : "Reject"}</button>`
        );
      }
      const attendeeAction =
        status === "approved"
          ? `<button class="secondary-button image-card-button" data-action="attendees" data-id="${event.id}" type="button">Attendees</button>`
          : "";
      const reviewNote = event.review_note
        ? `<p class="subtle admin-manager-review">${escapeHtml(event.review_note)}</p>`
        : "";
      return `
        <article class="admin-manager-item" data-testid="admin-manager-item-${event.id}">
          <img class="admin-manager-thumb" src="${escapeHtml(getPrimaryEventImage(event))}" alt="${escapeHtml(event.title)}" />
          <div class="admin-manager-body">
            <div class="admin-manager-row">
              <div>
                <strong>${escapeHtml(event.title)}</strong>
                <p class="admin-manager-kicker">${escapeHtml(formatDateTime(event.start_at))}</p>
              </div>
              <span class="image-order-chip manager-status-badge ${statusClass}">${escapeHtml(statusLabel)}</span>
            </div>
            <p class="subtle admin-manager-location">${escapeHtml(event.location)}</p>
            <div class="admin-manager-metrics">
              <span>${escapeHtml(formatCurrency(event.price))} / ticket</span>
              <span>${escapeHtml(String(event.registered_count))} registered</span>
              <span>${escapeHtml(String(event.capacity))} capacity</span>
            </div>
            ${reviewNote}
          </div>
          <div class="admin-manager-actions">
            ${moderationActions.join("")}
            <button class="secondary-button image-card-button" data-action="edit" data-id="${event.id}" type="button">Edit</button>
            ${attendeeAction}
            <button class="secondary-button danger-button image-card-button" data-action="delete" data-id="${event.id}" type="button">Delete</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderAnalytics() {
  if (!state.analytics) {
    return;
  }

  const { summary, country_distribution: countryDistribution, events } = state.analytics;
  const analyticsEvents = Array.isArray(events) ? events : [];
  if (analyticsTotalRegistrations) {
    analyticsTotalRegistrations.textContent = String(summary.total_registrations);
  }
  if (analyticsTotalRevenue) {
    analyticsTotalRevenue.textContent = formatCurrency(summary.total_revenue);
  }
  if (analyticsOccupancyRate) {
    analyticsOccupancyRate.textContent = formatPercent(summary.occupancy_rate);
  }
  if (analyticsAverageTicket) {
    analyticsAverageTicket.textContent = formatCurrency(summary.average_ticket_price);
  }
  if (analyticsCustomerRatio) {
    analyticsCustomerRatio.textContent = `${formatPercent(summary.domestic_customer_ratio)} / ${formatPercent(summary.international_customer_ratio)}`;
  }
  if (adminAnalyticsEventCount) {
    adminAnalyticsEventCount.textContent = String(analyticsEvents.length);
  }
  if (adminAnalyticsMarketCount) {
    adminAnalyticsMarketCount.textContent = String(Array.isArray(countryDistribution) ? countryDistribution.length : 0);
  }
  if (adminAnalysisSummary) {
    adminAnalysisSummary.textContent = analyticsEvents.length
      ? `Track ${analyticsEvents.length} live events with ${summary.total_registrations} registrations and projected revenue of ${formatCurrency(summary.total_revenue)}.`
      : "Open the dedicated analytics page to inspect profit, customer mix, and per-event distribution in a cleaner management view.";
  }
}

async function loadEvents() {
  state.events = await api("/api/events");
  renderEventFilters();
  renderEventGrid();
  renderEventSearchPanel();
}

async function loadAdminManagerEvents() {
  if (state.user?.role !== "admin") {
    state.adminManagerEvents = [];
    renderAdminManagerList();
    return;
  }
  state.adminManagerEvents = await api("/api/admin/events");
  renderAdminManagerList();
}

async function loadAdminAnalytics() {
  if (state.user?.role !== "admin") {
    return;
  }
  state.analytics = await api("/api/admin/analytics");
  renderAnalytics();
}

async function refreshDashboardData() {
  const tasks = [loadEvents()];
  if (state.user?.role === "admin") {
    tasks.push(loadAdminManagerEvents(), loadAdminAnalytics());
  }
  const results = await Promise.allSettled(tasks);
  const firstFailure = results.find((result) => result.status === "rejected");
  if (firstFailure && firstFailure.status === "rejected") {
    throw firstFailure.reason;
  }
}

function updateEventInState(updatedEvent) {
  state.events = state.events.map((event) => (event.id === updatedEvent.id ? { ...event, ...updatedEvent } : event));
  state.adminManagerEvents = state.adminManagerEvents.map((event) =>
    event.id === updatedEvent.id ? { ...event, ...updatedEvent } : event
  );
  renderEventSearchPanel();
  renderAdminManagerList();
}

async function syncAdminAnalyticsAfterReservation() {
  if (state.user?.role !== "admin") {
    return;
  }
  await Promise.all([loadAdminAnalytics(), loadAdminManagerEvents()]);
}

async function handleGridAction(target) {
  const eventId = Number(target.dataset.id);
  if (!eventId) {
    return;
  }

  if (target.dataset.action === "register") {
    openDashboardRegistrationModal(eventId);
    return;
  }

  if (target.dataset.action === "cancel") {
    const updatedEvent = await api(`/api/events/${eventId}/register`, { method: "DELETE" });
    updateEventInState(updatedEvent);
    renderEventGrid({ restartTimer: false });
    await syncAdminAnalyticsAfterReservation();
    showToast("Reservation cancelled.");
    return;
  }

  if (target.dataset.action === "approve-request") {
    await api(`/api/admin/events/${eventId}/approve`, { method: "POST" });
    showToast("Event request approved.");
    await refreshDashboardData();
    return;
  }

  if (target.dataset.action === "reject-request") {
    await api(`/api/admin/events/${eventId}/reject`, { method: "POST" });
    state.attendees = [];
    renderAttendees('Select an event and click "Attendees".');
    showToast("Event request sent back for revision.");
    await refreshDashboardData();
    return;
  }

  if (target.dataset.action === "edit") {
    openAdminModal("edit", await api(`/api/events/${eventId}`));
    return;
  }

  if (target.dataset.action === "delete") {
    await api(`/api/admin/events/${eventId}`, { method: "DELETE" });
    state.attendees = [];
    renderAttendees('Select an event and click "Attendees".');
    showToast("Event deleted.");
    await refreshDashboardData();
    return;
  }

  if (target.dataset.action === "attendees") {
    state.attendees = await api(`/api/events/${eventId}/registrations`);
    renderAttendees();
  }
}

async function handleAdminSubmit(event) {
  event.preventDefault();
  const eventId = document.querySelector("#admin-event-id").value;
  const price = Number(document.querySelector("#admin-price").value);
  const locationValue = document.querySelector("#admin-location").value.trim();
  const latitudeValue = document.querySelector("#admin-latitude").value.trim();
  const longitudeValue = document.querySelector("#admin-longitude").value.trim();
  const latitude = latitudeValue ? Number(latitudeValue) : null;
  const longitude = longitudeValue ? Number(longitudeValue) : null;
  const payload = {
    title: document.querySelector("#admin-title").value,
    location: locationValue,
    description: document.querySelector("#admin-description").value,
    category: document.querySelector("#admin-category").value,
    event_format: document.querySelector("#admin-event-format").value,
    venue_details: document.querySelector("#admin-venue-details").value,
    start_at: fromDatetimeLocal(document.querySelector("#admin-start-at").value),
    registration_deadline: fromDatetimeLocalOptional(document.querySelector("#admin-registration-deadline").value),
    capacity: Number(document.querySelector("#admin-capacity").value),
    price,
    organizer_name: document.querySelector("#admin-organizer-name").value,
    organizer_details: "",
    speaker_lineup: parseLineList(document.querySelector("#admin-speaker-lineup").value),
    ticket_types: parseTicketTypes(document.querySelector("#admin-ticket-types").value, price),
    latitude,
    longitude,
    map_url: document.querySelector("#admin-map-url").value.trim() || buildLocationMapUrl(locationValue, latitude, longitude),
    contact_email: document.querySelector("#admin-contact-email").value,
    contact_phone: document.querySelector("#admin-contact-phone").value,
    refund_policy: document.querySelector("#admin-refund-policy").value,
    check_in_policy: document.querySelector("#admin-check-in-policy").value,
    image_url: state.adminDraftImages[0] || "",
    image_urls: state.adminDraftImages,
    opening_highlights: "",
    mid_event_highlights: "",
    closing_highlights: "",
  };
  const method = eventId ? "PUT" : "POST";
  const url = eventId ? `/api/admin/events/${eventId}` : "/api/admin/events";

  try {
    await api(url, { method, body: JSON.stringify(payload) });
    closeAdminModal();
    showToast(eventId ? "Event updated successfully." : "Event created successfully.");
    await refreshDashboardData();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function boot() {
  state.user = await getCurrentUser();
  if (!state.user) {
    redirectTo("/");
    return;
  }

  setupAccountMenu(state.user);
  setupGlobalFooter(state.user);
  attachLocationPicker({
    inputSelector: "#admin-location",
    buttonSelector: "#admin-location-picker",
    mapUrlSelector: "#admin-map-url",
    latitudeSelector: "#admin-latitude",
    longitudeSelector: "#admin-longitude",
  });
  welcomeText.textContent = `Welcome, ${state.user.name}`;
  roleChip.textContent = toTitleCase(state.user.role);
  document.querySelector("#admin-price").value = 0;
  renderAdminImageEditor();
  renderAttendees("Select an event and click \"Attendees\".");
  const initialAdminView = state.user.role === "admin" && currentPath === "/admin/manager" ? "manager" : "event-board";
  document.title = initialAdminView === "manager" ? "Admin Manager | EventHub Verify" : "Dashboard | EventHub Verify";
  setAdminView(initialAdminView);

  refreshButton.addEventListener("click", async () => {
    try {
      await refreshDashboardData();
      showToast("Event board refreshed.");
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  const applyBoardFilters = () => {
    state.eventFilters.search = eventSearchInput?.value.trim() || "";
    state.eventFilters.category = eventCategoryFilter?.value || "";
    state.eventFilters.location = eventLocationFilter?.value || "";
    state.eventFilters.pricing = eventPriceFilter?.value || "";
    state.eventFilters.sort = eventSortFilter?.value || "soonest";
    state.hasSubmittedSearch = true;
    renderEventSearchPanel();
  };

  eventSearchInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    applyBoardFilters();
  });
  eventSearchSubmitButton?.addEventListener("click", applyBoardFilters);

  dashboardRegistrationClose?.addEventListener("click", closeDashboardRegistrationModal);
  dashboardRegistrationCancel?.addEventListener("click", closeDashboardRegistrationModal);
  dashboardRegistrationForm?.addEventListener("submit", async (event) => {
    try {
      await handleDashboardRegistrationSubmit(event);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  dashboardRegistrationModal?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.closest('[data-action="close-dashboard-registration"]')) {
      closeDashboardRegistrationModal();
    }
  });
  [dashboardRegistrationQuantity, dashboardRegistrationName, dashboardRegistrationEmail, dashboardRegistrationPhone].forEach((element) => {
    element?.addEventListener("input", renderDashboardRegistrationSummary);
    element?.addEventListener("change", renderDashboardRegistrationSummary);
  });

  eventGrid.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const slideDot = target.closest("[data-slider-index]");
    if (slideDot instanceof HTMLElement) {
      goToEventSlide(Number(slideDot.dataset.sliderIndex));
      return;
    }

    const slideNav = target.closest("[data-slide-nav]");
    if (slideNav instanceof HTMLElement) {
      const direction = slideNav.dataset.slideNav === "prev" ? -1 : 1;
      goToEventSlide(state.eventSlideIndex + direction);
      return;
    }

    const actionTarget = target.closest("[data-action]");
    if (!(actionTarget instanceof HTMLElement)) {
      return;
    }

    try {
          await handleGridAction(actionTarget);
    } catch (error) {
      showToast(error.message, "error");
    }
  });


  eventMatchList?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const actionButton = target.closest("[data-action]");
    if (!(actionButton instanceof HTMLElement)) {
      return;
    }

    try {
      await handleGridAction(actionButton);
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  adminManagerList?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const actionTarget = target.closest("[data-action]");
    if (!(actionTarget instanceof HTMLElement)) {
      return;
    }

    try {
          await handleGridAction(actionTarget);
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  analyticsEventGrid?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !state.analytics) {
      return;
    }

    const analyticsEvents = Array.isArray(state.analytics.events) ? state.analytics.events : [];
    const toggleTarget = target.closest('[data-action="toggle-event-analytics"]');
    if (toggleTarget instanceof HTMLElement) {
      state.analyticsSidebarOpen = !state.analyticsSidebarOpen;
      if (
        state.analyticsSidebarOpen &&
        (
          state.selectedAnalyticsEventId === null ||
          !analyticsEvents.some((analyticsEvent) => getAnalyticsEventId(analyticsEvent) === state.selectedAnalyticsEventId)
        )
      ) {
        state.selectedAnalyticsEventId = analyticsEvents.length ? getAnalyticsEventId(analyticsEvents[0]) : null;
      }
      renderAnalytics();
      return;
    }

    const eventTarget = target.closest('[data-action="select-analytics-event"]');
    if (!(eventTarget instanceof HTMLElement)) {
      return;
    }

    const eventId = Number(eventTarget.dataset.id);
    if (!eventId) {
      return;
    }

    state.selectedAnalyticsEventId = eventId;
    renderAnalytics();
  });

  adminOpenCreateButton?.addEventListener("click", () => {
    openAdminModal("create");
  });
  adminModalCloseButton?.addEventListener("click", () => {
    closeAdminModal();
  });
  adminCancelButton?.addEventListener("click", () => {
    closeAdminModal();
  });
  adminEventModal?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.closest('[data-action="close-admin-modal"]')) {
      closeAdminModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    if (dashboardRegistrationModal && !dashboardRegistrationModal.classList.contains("hidden")) {
      closeDashboardRegistrationModal();
      return;
    }
    if (adminEventModal && !adminEventModal.classList.contains("hidden")) {
      closeAdminModal();
    }
  });

  if (adminForm) {
    adminForm.addEventListener("submit", handleAdminSubmit);
    adminImageAdd?.addEventListener("click", addAdminImage);
    adminImageInput?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      addAdminImage();
    });
    adminImageFilesInput?.addEventListener("change", async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) {
        return;
      }
      await addAdminImageFiles(target.files);
    });
    adminImageDropzone?.addEventListener("click", () => {
      adminImageFilesInput?.click();
    });
    adminImageDropzone?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      event.preventDefault();
      adminImageFilesInput?.click();
    });
    ["dragenter", "dragover"].forEach((eventName) => {
      adminImageDropzone?.addEventListener(eventName, (event) => {
        if (!transferIncludesFiles(event)) {
          return;
        }
        event.preventDefault();
        adminImageDropzone.classList.add("is-dragover");
      });
    });
    adminImageDropzone?.addEventListener("dragleave", (event) => {
      const relatedTarget = event.relatedTarget;
      if (relatedTarget instanceof Node && adminImageDropzone.contains(relatedTarget)) {
        return;
      }
      adminImageDropzone.classList.remove("is-dragover");
    });
    adminImageDropzone?.addEventListener("drop", async (event) => {
      if (!transferIncludesFiles(event)) {
        return;
      }
      event.preventDefault();
      adminImageDropzone.classList.remove("is-dragover");
      await addAdminImageFiles(event.dataTransfer?.files);
    });
    adminImagePreview?.addEventListener("error", handleAdminImagePreviewError);
    adminImageClear?.addEventListener("click", () => {
      setAdminDraftImages([]);
      clearAdminImagePicker();
      renderAdminImageEditor("Gallery cleared. Save the event to fall back to the default artwork.");
    });
    adminImageGallery?.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const action = target.dataset.action;
      const index = Number(target.dataset.index);
      if (!action || Number.isNaN(index)) {
        return;
      }
      if (action === "remove-image") {
        removeAdminImage(index);
      }
      if (action === "cover-image") {
        setAdminCoverImage(index);
      }
    });
    adminImageGallery?.addEventListener("dragstart", (event) => {
      const card = event.target instanceof HTMLElement ? event.target.closest(".admin-image-card") : null;
      if (!(card instanceof HTMLElement)) {
        return;
      }
      const index = Number(card.dataset.index);
      if (Number.isNaN(index)) {
        return;
      }
      state.adminDraggedImageIndex = index;
      adminImageGallery.classList.add("is-sorting");
      card.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(index));
      }
    });
    adminImageGallery?.addEventListener("dragover", (event) => {
      if (state.adminDraggedImageIndex === null) {
        return;
      }
      event.preventDefault();
      const dropContext = getAdminImageDropContext(event);
      setAdminImageDropTarget(dropContext.highlightIndex);
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "move";
      }
    });
    adminImageGallery?.addEventListener("dragleave", (event) => {
      const relatedTarget = event.relatedTarget;
      if (relatedTarget instanceof Node && adminImageGallery.contains(relatedTarget)) {
        return;
      }
      setAdminImageDropTarget(null);
    });
    adminImageGallery?.addEventListener("drop", (event) => {
      if (state.adminDraggedImageIndex === null) {
        return;
      }
      event.preventDefault();
      const dropContext = getAdminImageDropContext(event);
      moveAdminImage(state.adminDraggedImageIndex, dropContext.insertIndex);
    });
    adminImageGallery?.addEventListener("dragend", () => {
      clearAdminImageDragState();
    });
    document.querySelector("#admin-reset").addEventListener("click", () => {
      resetAdminForm();
      setAdminModalCopy("create");
      showToast("Admin form reset.");
    });
  }

  try {
    await refreshDashboardData();
  } catch (error) {
    showToast(error.message || "Could not load dashboard data.", "error");
  }
}

boot();






