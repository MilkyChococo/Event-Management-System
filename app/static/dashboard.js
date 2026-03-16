import {
  api,
  clearNotice,
  escapeHtml,
  formatCurrency,
  formatDateTime,
  fromDatetimeLocal,
  getCurrentUser,
  redirectTo,
  setupAccountMenu,
  showNotice,
  showToast,
  toDatetimeLocal,
} from "/static/shared.js?v=20260316-toast-actions";

const messageBox = document.querySelector("[data-testid='dashboard-message']");
const eventGrid = document.querySelector("[data-testid='event-grid']");
const refreshButton = document.querySelector("#refresh-events");
const welcomeText = document.querySelector("#welcome-text");
const heroBanner = document.querySelector(".hero-banner.hero-banner-editorial");
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

const DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg";

const EVENT_SLIDE_INTERVAL_MS = 6000;

const state = {
  user: null,
  events: [],
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
};

function toTitleCase(value) {
  if (!value) {
    return "";
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function excerpt(text, maxLength = 120) {
  if (!text) {
    return "";
  }
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

function formatPercent(value) {
  const numeric = Number(value || 0);
  const digits = Number.isInteger(numeric) ? 0 : 1;
  return `${numeric.toFixed(digits)}%`;
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
  window.clearInterval(state.eventSlideTimerId);
  state.eventSlideTimerId = null;
}

function buildEventSlideMarkup(event) {
  const registrationAction = event.is_registered
    ? `<button class="secondary-button" data-action="cancel" data-id="${event.id}" type="button">Cancel reservation</button>`
    : `<button class="primary-button" data-action="register" data-id="${event.id}" type="button" ${event.seats_left === 0 ? "disabled" : ""}>Reserve now</button>`;
  const adminActions =
    state.user?.role === "admin"
      ? `
          <button class="secondary-button" data-action="edit" data-id="${event.id}" type="button">Edit</button>
          <button class="secondary-button danger-button" data-action="delete" data-id="${event.id}" type="button">Delete</button>
          <button class="secondary-button" data-action="attendees" data-id="${event.id}" type="button">Attendees</button>
        `
      : "";

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
              <span>Seats left</span>
              <strong data-testid="event-seats-${event.id}">${event.seats_left}/${event.capacity}</strong>
            </article>
          </div>
          <div class="button-row">
            <a class="detail-link" data-testid="detail-link-${event.id}" href="/events/${event.id}/view">View detail</a>
            ${registrationAction}
            ${adminActions}
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
  if (state.events.length <= 1) {
    return;
  }

  state.eventSlideTimerId = window.setInterval(() => {
    state.eventSlideIndex = (state.eventSlideIndex + 1) % state.events.length;
    updateEventSlidePosition(false);
  }, EVENT_SLIDE_INTERVAL_MS);
}

function goToEventSlide(index, restartTimer = true) {
  if (!state.events.length) {
    return;
  }

  const total = state.events.length;
  state.eventSlideIndex = ((index % total) + total) % total;
  updateEventSlidePosition(false);
  if (restartTimer) {
    startEventSlideTimer();
  }
}

function renderEventGrid(options = {}) {
  const { restartTimer = true } = options;
  if (restartTimer) {
    clearEventSlideTimer();
  }

  if (!state.events.length) {
    eventGrid.innerHTML = "<p>No events available yet.</p>";
    eventCount.textContent = "0";
    state.eventSlideIndex = 0;
    return;
  }

  state.eventSlideIndex = Math.min(state.eventSlideIndex, state.events.length - 1);
  eventCount.textContent = String(state.events.length);
  const activeEvent = state.events[state.eventSlideIndex];
  eventGrid.innerHTML = `
    <div class="event-slider-shell" data-testid="event-slider-shell">
      <div class="event-slider-stage" aria-live="polite">
        ${buildEventSlideMarkup(activeEvent)}
      </div>
      <div class="event-slide-dots" data-role="event-slide-dots">
        ${state.events
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
  document.querySelector("#admin-description").value = event.description;
  document.querySelector("#admin-venue-details").value = event.venue_details || "";
  document.querySelector("#admin-start-at").value = toDatetimeLocal(event.start_at);
  document.querySelector("#admin-capacity").value = event.capacity;
  document.querySelector("#admin-price").value = event.price;
  setAdminDraftImages(getEventImages(event).filter((image) => image !== DEFAULT_EVENT_IMAGE));
  clearAdminImagePicker();
  renderAdminImageEditor(
    state.adminDraftImages.length
      ? `Editing ${state.adminDraftImages.length} gallery images for ${event.title}.`
      : "This event currently uses the default artwork. Add one or more images for the viewer carousel."
  );
  document.querySelector("#admin-opening-highlights").value = event.opening_highlights || "";
  document.querySelector("#admin-mid-event-highlights").value = event.mid_event_highlights || "";
  document.querySelector("#admin-closing-highlights").value = event.closing_highlights || "";
}

function resetAdminForm() {
  adminForm.reset();
  document.querySelector("#admin-event-id").value = "";
  document.querySelector("#admin-price").value = 0;
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

  const events = Array.isArray(state.events) ? state.events : [];
  if (adminManagerCount) {
    adminManagerCount.textContent = `${events.length} ${events.length === 1 ? "event" : "events"}`;
  }

  if (!events.length) {
    adminManagerList.innerHTML = `
      <section class="admin-manager-empty">
        <p class="eyebrow">Empty board</p>
        <p class="subtle">There are no events yet. Use <strong>+ Add event</strong> to create the first one.</p>
      </section>
    `;
    return;
  }

  adminManagerList.innerHTML = events
    .map(
      (event) => `
        <article class="admin-manager-item" data-testid="admin-manager-item-${event.id}">
          <img class="admin-manager-thumb" src="${escapeHtml(getPrimaryEventImage(event))}" alt="${escapeHtml(event.title)}" />
          <div class="admin-manager-body">
            <div class="admin-manager-row">
              <div>
                <strong>${escapeHtml(event.title)}</strong>
                <p class="admin-manager-kicker">${escapeHtml(formatDateTime(event.start_at))}</p>
              </div>
              <span class="image-order-chip">${escapeHtml(String(event.seats_left))} seats left</span>
            </div>
            <p class="subtle admin-manager-location">${escapeHtml(event.location)}</p>
            <div class="admin-manager-metrics">
              <span>${escapeHtml(formatCurrency(event.price))} / ticket</span>
              <span>${escapeHtml(String(event.registered_count))} registered</span>
              <span>${escapeHtml(String(event.capacity))} capacity</span>
            </div>
          </div>
          <div class="admin-manager-actions">
            <button class="secondary-button image-card-button" data-action="edit" data-id="${event.id}" type="button">Edit</button>
            <button class="secondary-button image-card-button" data-action="attendees" data-id="${event.id}" type="button">Attendees</button>
            <button class="secondary-button danger-button image-card-button" data-action="delete" data-id="${event.id}" type="button">Delete</button>
          </div>
        </article>
      `
    )
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
  renderEventGrid();
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
    tasks.push(loadAdminAnalytics());
  }
  await Promise.all(tasks);
}

function updateEventInState(updatedEvent) {
  state.events = state.events.map((event) => (event.id === updatedEvent.id ? { ...event, ...updatedEvent } : event));
  renderAdminManagerList();
}

async function syncAdminAnalyticsAfterReservation() {
  if (state.user?.role !== "admin") {
    return;
  }
  await loadAdminAnalytics();
}

async function handleGridAction(target) {
  const eventId = Number(target.dataset.id);
  if (!eventId) {
    return;
  }

  if (target.dataset.action === "register") {
    const updatedEvent = await api(`/api/events/${eventId}/register`, { method: "POST" });
    updateEventInState(updatedEvent);
    renderEventGrid({ restartTimer: false });
    await syncAdminAnalyticsAfterReservation();
    showToast("Seat reserved successfully.");
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

  if (target.dataset.action === "edit") {
    openAdminModal("edit", await api(`/api/events/${eventId}`));
    return;
  }

  if (target.dataset.action === "delete") {
    await api(`/api/admin/events/${eventId}`, { method: "DELETE" });
    state.attendees = [];
    renderAttendees("Select an event and click \"Attendees\".");
    showNotice(messageBox, "Event deleted.");
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
  clearNotice(messageBox);
  const eventId = document.querySelector("#admin-event-id").value;
  const payload = {
    title: document.querySelector("#admin-title").value,
    location: document.querySelector("#admin-location").value,
    description: document.querySelector("#admin-description").value,
    venue_details: document.querySelector("#admin-venue-details").value,
    start_at: fromDatetimeLocal(document.querySelector("#admin-start-at").value),
    capacity: Number(document.querySelector("#admin-capacity").value),
    price: Number(document.querySelector("#admin-price").value),
    image_url: state.adminDraftImages[0] || "",
    image_urls: state.adminDraftImages,
    opening_highlights: document.querySelector("#admin-opening-highlights").value,
    mid_event_highlights: document.querySelector("#admin-mid-event-highlights").value,
    closing_highlights: document.querySelector("#admin-closing-highlights").value,
  };
  const method = eventId ? "PUT" : "POST";
  const url = eventId ? `/api/admin/events/${eventId}` : "/api/admin/events";

  try {
    await api(url, { method, body: JSON.stringify(payload) });
    closeAdminModal();
    showNotice(messageBox, eventId ? "Event updated successfully." : "Event created successfully.");
    await refreshDashboardData();
  } catch (error) {
    showNotice(messageBox, error.message, "error");
  }
}

async function boot() {
  state.user = await getCurrentUser();
  if (!state.user) {
    redirectTo("/");
    return;
  }

  setupAccountMenu(state.user);
  welcomeText.textContent = `Welcome, ${state.user.name}`;
  roleChip.textContent = toTitleCase(state.user.role);
  document.querySelector("#admin-price").value = 0;
  renderAdminImageEditor();
  renderAttendees("Select an event and click \"Attendees\".");
  setAdminView("event-board");

  refreshButton.addEventListener("click", async () => {
    clearNotice(messageBox);
    await refreshDashboardData();
    showNotice(messageBox, "Event board refreshed.");
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

    const actionTarget = target.closest("[data-action]");
    if (!(actionTarget instanceof HTMLElement)) {
      return;
    }

    try {
      clearNotice(messageBox);
      await handleGridAction(actionTarget);
    } catch (error) {
      showNotice(messageBox, error.message, "error");
    }
  });

  eventGrid.addEventListener("mouseenter", () => {
    clearEventSlideTimer();
  });

  eventGrid.addEventListener("mouseleave", () => {
    startEventSlideTimer();
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
      clearNotice(messageBox);
      await handleGridAction(actionTarget);
    } catch (error) {
      showNotice(messageBox, error.message, "error");
    }
  });

  adminBrandTrigger?.addEventListener("click", (event) => {
    if (state.user?.role !== "admin") {
      return;
    }
    event.preventDefault();
    setAdminView("event-board");
  });

  adminTopbarNav?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const viewButton = target.closest("[data-admin-view]");
    if (!(viewButton instanceof HTMLElement)) {
      return;
    }

    setAdminView(viewButton.dataset.adminView || "event-board");
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
      if (!state.analyticsSidebarOpen) {
        state.selectedAnalyticsEventId = null;
      } else if (
        state.selectedAnalyticsEventId === null ||
        !analyticsEvents.some((analyticsEvent) => analyticsEvent.id === state.selectedAnalyticsEventId)
      ) {
        state.selectedAnalyticsEventId = analyticsEvents[0]?.id ?? null;
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

    state.selectedAnalyticsEventId = state.selectedAnalyticsEventId === eventId ? null : eventId;
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
    if (event.key === "Escape" && adminEventModal && !adminEventModal.classList.contains("hidden")) {
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
      showNotice(messageBox, "Admin form reset.");
    });
  }

  await refreshDashboardData();
}

boot();