import {
  api,
  attachLocationPicker,
  escapeHtml,
  formatCurrency,
  formatDateTime,
  fromDatetimeLocal,
  getCurrentUser,
  redirectTo,
  renderUserAvatar,
  setupAccountMenu,
  setupGlobalFooter,
  showToast,
  toDatetimeLocal,
} from "/static/shared.js?v=20260328-location-coordinates";

const DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg";

const activityAvatar = document.querySelector("[data-testid='activity-avatar']");
const activityTitle = document.querySelector("#activity-title");
const activityHeroCopy = document.querySelector("#activity-hero-copy");
const activityWelcomeText = document.querySelector("#activity-welcome-text");
const activityRoleChip = document.querySelector("#activity-role-chip");
const activityAdminTopbarNav = document.querySelector("#activity-admin-topbar-nav");
const joinedCount = document.querySelector("#activity-joined-count");
const activeCount = document.querySelector("#activity-active-count");
const ownedCount = document.querySelector("#activity-owned-count");
const joinedList = document.querySelector("#activity-joined-list");
const ownedEventForm = document.querySelector("#activity-owned-event-form");
const ownedEventId = document.querySelector("#activity-owned-event-id");
const ownedEventTitle = document.querySelector("#activity-owned-event-title");
const ownedEventCategory = document.querySelector("#activity-owned-event-category");
const ownedEventDescription = document.querySelector("#activity-owned-event-description");
const ownedEventVenueDetails = document.querySelector("#activity-owned-event-venue-details");
const ownedEventLocation = document.querySelector("#activity-owned-event-location");
const ownedEventLatitude = document.querySelector("#activity-owned-event-latitude");
const ownedEventLongitude = document.querySelector("#activity-owned-event-longitude");
const ownedEventStartAt = document.querySelector("#activity-owned-event-start-at");
const ownedEventCapacity = document.querySelector("#activity-owned-event-capacity");
const ownedEventPrice = document.querySelector("#activity-owned-event-price");
const ownedEventSubmit = document.querySelector("#activity-owned-event-submit");
const ownedEventCancel = document.querySelector("#activity-owned-event-cancel");
const ownedEventList = document.querySelector("#activity-owned-event-list");
const formKicker = document.querySelector("#activity-form-kicker");
const formTitle = document.querySelector("#activity-form-title");
const activityToggles = Array.from(document.querySelectorAll("[data-activity-toggle]"));
const activityImageUrl = document.querySelector("#activity-image-url");
const activityImageAdd = document.querySelector("#activity-image-add");
const activityImageFiles = document.querySelector("#activity-image-files");
const activityImageDropzone = document.querySelector("#activity-image-dropzone");
const activityImageBrowse = document.querySelector("#activity-image-browse");
const activityImagePreview = document.querySelector("#activity-image-preview");
const activityImageStatus = document.querySelector("#activity-image-status");
const activityImageClear = document.querySelector("#activity-image-clear");
const activityImageGallery = document.querySelector("#activity-image-gallery");

const state = {
  user: null,
  tickets: [],
  ownedEvents: [],
  editingEventId: null,
  draftImages: [],
  openPanels: new Set(["registrations"]),
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

function renderActivityAccordion() {
  activityToggles.forEach((toggle) => {
    const target = toggle.dataset.activityToggle;
    if (!target) {
      return;
    }
    const isOpen = state.openPanels.has(target);
    toggle.classList.toggle("is-open", isOpen);
    toggle.classList.toggle("is-active", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));

    const icon = toggle.querySelector("[data-activity-icon]");
    if (icon) {
      icon.textContent = isOpen ? "^" : "v";
    }

    const panel = document.querySelector(`[data-activity-panel='${target}']`);
    if (panel instanceof HTMLElement) {
      panel.classList.toggle("hidden", !isOpen);
      panel.classList.toggle("is-active", isOpen);
    }
  });
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

function setDraftImages(images) {
  state.draftImages = normalizeImageList(images);
}

function clearImagePicker() {
  if (activityImageUrl) {
    activityImageUrl.value = "";
  }
  if (activityImageFiles) {
    activityImageFiles.value = "";
  }
}

function renderImageEditor(message = "") {
  if (!activityImagePreview || !activityImageStatus || !activityImageGallery) {
    return;
  }

  const images = state.draftImages;
  const coverImage = images[0] || DEFAULT_EVENT_IMAGE;
  activityImagePreview.src = coverImage;
  activityImagePreview.alt = images.length ? "Owned event cover preview" : "Default event cover preview";
  activityImageStatus.textContent =
    message ||
    (images.length
      ? `${images.length} gallery images ready. The first image is the cover shown on cards and detail pages.`
      : "No custom images yet. The event will use the default artwork until you add photos.");

  if (activityImageClear) {
    activityImageClear.disabled = images.length === 0;
  }

  if (!images.length) {
    activityImageGallery.innerHTML = '<p class="subtle">No custom images added yet. Add one or more photos for a richer event card and detail page.</p>';
    return;
  }

  activityImageGallery.innerHTML = images
    .map(
      (image, index) => `
        <article class="admin-image-card">
          <img class="admin-image-thumb" src="${escapeHtml(image)}" alt="Gallery image ${index + 1}" />
          <div class="admin-image-card-copy">
            <div class="admin-image-card-row">
              <strong>${index === 0 ? "Cover image" : `Gallery image ${index + 1}`}</strong>
              <span class="image-order-chip">Slide ${index + 1}</span>
            </div>
            <p class="subtle">${escapeHtml(image.length > 84 ? `${image.slice(0, 81)}...` : image)}</p>
            <p class="admin-image-helper">Use Move first to choose the cover shown on event cards.</p>
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

function addImageSources(images, successMessage, duplicateMessage) {
  const normalizedImages = normalizeImageList(images);
  if (!normalizedImages.length) {
    renderImageEditor(duplicateMessage);
    return 0;
  }

  const nextImages = normalizeImageList([...state.draftImages, ...normalizedImages]);
  const addedCount = nextImages.length - state.draftImages.length;
  if (!addedCount) {
    renderImageEditor(duplicateMessage);
    return 0;
  }

  setDraftImages(nextImages);
  renderImageEditor(successMessage(addedCount, nextImages.length));
  return addedCount;
}

function addImageFromInput() {
  if (!activityImageUrl) {
    return;
  }

  const image = activityImageUrl.value.trim();
  if (!image) {
    renderImageEditor("Enter an image URL or static path before adding it.");
    return;
  }

  addImageSources(
    [image],
    (addedCount, totalCount) =>
      addedCount === 1
        ? `Added gallery image ${totalCount}. The first image becomes the event cover.`
        : `Added ${addedCount} gallery images.`,
    `This image is already in the gallery: ${image}`
  );
  clearImagePicker();
}

function readImageFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || "").trim());
    reader.onerror = () => reject(reader.error || new Error(`Could not read ${file.name}.`));
    reader.readAsDataURL(file);
  });
}

async function addImageFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) {
    return;
  }

  const imageFiles = files.filter((file) => file.type.startsWith("image/"));
  const skippedCount = files.length - imageFiles.length;
  if (!imageFiles.length) {
    clearImagePicker();
    renderImageEditor("Only image files can be added to the gallery.");
    return;
  }

  const uploadedImages = [];
  let failedCount = 0;
  for (const file of imageFiles) {
    try {
      const encoded = await readImageFile(file);
      if (encoded) {
        uploadedImages.push(encoded);
      }
    } catch {
      failedCount += 1;
    }
  }

  const nextImages = normalizeImageList([...state.draftImages, ...uploadedImages]);
  const addedCount = nextImages.length - state.draftImages.length;
  if (addedCount) {
    setDraftImages(nextImages);
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
  clearImagePicker();
  renderImageEditor(messages.join(" "));
}

function removeImage(index) {
  const nextImages = state.draftImages.filter((_, imageIndex) => imageIndex !== index);
  setDraftImages(nextImages);
  renderImageEditor(
    nextImages.length
      ? `Removed image ${index + 1}. The gallery now has ${nextImages.length} images.`
      : "Gallery cleared. The event will fall back to the default artwork when you save."
  );
}

function setCoverImage(index) {
  if (index <= 0 || index >= state.draftImages.length) {
    return;
  }

  const nextImages = [...state.draftImages];
  const [coverImage] = nextImages.splice(index, 1);
  nextImages.unshift(coverImage);
  setDraftImages(nextImages);
  renderImageEditor("Updated cover image. Viewers will see this image first.");
}

function resetOwnedEventForm() {
  state.editingEventId = null;
  if (ownedEventForm instanceof HTMLFormElement) {
    ownedEventForm.reset();
  }
  if (ownedEventId) ownedEventId.value = "";
  if (ownedEventCategory) ownedEventCategory.value = "Community";
  if (ownedEventLatitude) ownedEventLatitude.value = "";
  if (ownedEventLongitude) ownedEventLongitude.value = "";
  if (ownedEventSubmit) ownedEventSubmit.textContent = "Send request";
  if (ownedEventCancel) ownedEventCancel.classList.add("hidden");
  if (formKicker) formKicker.textContent = "Request";
  if (formTitle) formTitle.textContent = "Send a new event request";
  setDraftImages([]);
  clearImagePicker();
  renderImageEditor();
}

function fillOwnedEventForm(event) {
  state.editingEventId = Number(event.id);
  if (ownedEventId) ownedEventId.value = String(event.id);
  if (ownedEventTitle) ownedEventTitle.value = event.title || "";
  if (ownedEventCategory) ownedEventCategory.value = event.category || "Community";
  if (ownedEventDescription) ownedEventDescription.value = event.description || "";
  if (ownedEventVenueDetails) ownedEventVenueDetails.value = event.venue_details || "";
  if (ownedEventLocation) ownedEventLocation.value = event.location || "";
  if (ownedEventLatitude) ownedEventLatitude.value = event.latitude ?? "";
  if (ownedEventLongitude) ownedEventLongitude.value = event.longitude ?? "";
  if (ownedEventStartAt) ownedEventStartAt.value = toDatetimeLocal(event.start_at || "");
  if (ownedEventCapacity) ownedEventCapacity.value = String(event.capacity || 1);
  if (ownedEventPrice) ownedEventPrice.value = String(event.price || 0);
  if (ownedEventSubmit) ownedEventSubmit.textContent = "Resubmit request";
  if (ownedEventCancel) ownedEventCancel.classList.remove("hidden");
  if (formKicker) formKicker.textContent = "Update request";
  if (formTitle) formTitle.textContent = `Update request: ${event.title}`;
  setDraftImages((Array.isArray(event.image_urls) ? event.image_urls : []).filter((image) => image !== DEFAULT_EVENT_IMAGE));
  renderImageEditor(
    state.draftImages.length
      ? `Editing ${state.draftImages.length} gallery images for ${event.title}.`
      : "This event currently uses the default artwork. Add one or more images for the viewer gallery."
  );
  state.openPanels.add("studio");
  renderActivityAccordion();
  ownedEventForm?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderMetrics() {
  const activeReservations = state.tickets.filter((ticket) => ticket.status === "confirmed" || ticket.status === "checked_in");
  if (joinedCount) {
    joinedCount.textContent = String(state.tickets.length);
  }
  if (activeCount) {
    activeCount.textContent = String(activeReservations.length);
  }
  if (ownedCount) {
    ownedCount.textContent = String(state.ownedEvents.length);
  }
}

function renderJoinedEvents() {
  if (!joinedList) {
    return;
  }

  joinedList.classList.remove("is-placeholder");

  if (!state.tickets.length) {
    joinedList.classList.add("is-placeholder");
    joinedList.innerHTML = `
      <article class="event-match-empty activity-empty-card">
        <strong>No event registration yet</strong>
        <p>Reserve an event from the dashboard and it will appear here with quantity, total spend, and status.</p>
      </article>
    `;
    return;
  }

  joinedList.innerHTML = state.tickets
    .map(
      (ticket) => `
        <article class="event-match-card activity-registration-card">
          <div class="event-match-copy activity-registration-copy">
            <div>
              <h3>${escapeHtml(ticket.title)}</h3>
              <p class="event-match-time">${escapeHtml(formatDateTime(ticket.start_at))}</p>
            </div>
            <dl class="event-match-meta activity-registration-meta">
              <div>
                <dt>Location</dt>
                <dd>${escapeHtml(ticket.location)}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>${escapeHtml(ticketStatusLabel(ticket.status))}</dd>
              </div>
              <div>
                <dt>Quantity</dt>
                <dd>${escapeHtml(String(ticket.quantity || 1))} ticket${Number(ticket.quantity || 1) > 1 ? "s" : ""}</dd>
              </div>
              <div>
                <dt>Total</dt>
                <dd>${escapeHtml(formatCurrency(ticket.total_price || ticket.ticket_price || 0))}</dd>
              </div>
            </dl>
          </div>
          <div class="event-match-actions activity-registration-actions">
            <a class="detail-link" href="/events/${ticket.event_id}/view">View detail</a>
          </div>
        </article>
      `
    )
    .join("");
}

function renderOwnedEvents() {
  if (!ownedEventList) {
    return;
  }

  if (!state.ownedEvents.length) {
    ownedEventList.innerHTML = '<p class="subtle">You have not sent any event request yet.</p>';
    return;
  }

  ownedEventList.innerHTML = state.ownedEvents
    .map((event) => {
      const status = String(event.approval_status || "approved").toLowerCase();
      const reviewNote = event.review_note ? `<p class="subtle activity-request-note">${escapeHtml(event.review_note)}</p>` : "";
      return `
        <article class="owned-event-item activity-request-item" data-event-id="${event.id}">
          <div>
            <div class="activity-request-head">
              <strong>${escapeHtml(event.title)}</strong>
              <span class="image-order-chip manager-status-badge is-${status}">${escapeHtml(formatApprovalStatus(status))}</span>
            </div>
            <p class="subtle">${escapeHtml(formatDateTime(event.start_at))} - ${escapeHtml(event.location)}</p>
            <p class="subtle">${escapeHtml(formatCurrency(event.price))} / ticket - ${escapeHtml(String(event.capacity))} capacity - ${escapeHtml(String(event.registered_count))} reserved</p>
            ${reviewNote}
          </div>
          <div class="owned-event-actions">
            <a class="secondary-button" href="/events/${event.id}/view">View detail</a>
            <button class="secondary-button" data-action="edit-owned-event" data-id="${event.id}" type="button">Edit request</button>
            <button class="secondary-button danger-button" data-action="delete-owned-event" data-id="${event.id}" type="button">Delete request</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function populateHeader(user) {
  renderUserAvatar(activityAvatar, user, "profile-avatar-image");
  if (activityTitle) {
    activityTitle.textContent = `${user.name}'s activity`;
  }
  if (activityHeroCopy) {
    activityHeroCopy.textContent = `${user.email} - track joined events and monitor your event requests in one place.`;
  }
  if (activityWelcomeText) {
    activityWelcomeText.textContent = `Welcome, ${user.name}`;
  }
  if (activityRoleChip) {
    activityRoleChip.textContent = toTitleCase(user.role);
  }
  activityAdminTopbarNav?.classList.toggle("hidden", user.role !== "admin");
  setupAccountMenu(user);
  setupGlobalFooter(user);
}

async function loadActivityData() {
  const [tickets, ownedEvents] = await Promise.all([api("/api/me/registrations"), api("/api/me/owned-events")]);
  state.tickets = Array.isArray(tickets) ? tickets : [];
  state.ownedEvents = Array.isArray(ownedEvents) ? ownedEvents : [];
  renderMetrics();
  renderJoinedEvents();
  renderOwnedEvents();
}

function buildOwnedEventPayload() {
  const latitudeValue = ownedEventLatitude?.value.trim() || "";
  const longitudeValue = ownedEventLongitude?.value.trim() || "";
  return {
    title: ownedEventTitle?.value.trim() || "",
    category: ownedEventCategory?.value.trim() || "Community",
    description: ownedEventDescription?.value.trim() || "",
    venue_details: ownedEventVenueDetails?.value.trim() || "",
    location: ownedEventLocation?.value.trim() || "",
    start_at: fromDatetimeLocal(ownedEventStartAt?.value || ""),
    capacity: Number(ownedEventCapacity?.value || 0),
    price: Number(ownedEventPrice?.value || 0),
    latitude: latitudeValue ? Number(latitudeValue) : null,
    longitude: longitudeValue ? Number(longitudeValue) : null,
    image_url: state.draftImages[0] || "",
    image_urls: state.draftImages,
  };
}

async function handleOwnedEventSubmit(event) {
  event.preventDefault();
  const payload = buildOwnedEventPayload();
  if (state.editingEventId) {
    await api(`/api/me/owned-events/${state.editingEventId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    showToast("Request updated and sent for review.");
  } else {
    await api("/api/me/owned-events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast("Request sent for admin review.");
  }
  resetOwnedEventForm();
  await loadActivityData();
}

async function handleOwnedEventAction(target) {
  const eventId = Number(target.dataset.id);
  if (!eventId) {
    return;
  }

  if (target.dataset.action === "edit-owned-event") {
    const event = state.ownedEvents.find((item) => item.id === eventId);
    if (event) {
      fillOwnedEventForm(event);
    }
    return;
  }

  if (target.dataset.action === "delete-owned-event") {
    await api(`/api/me/owned-events/${eventId}`, { method: "DELETE" });
    if (state.editingEventId === eventId) {
      resetOwnedEventForm();
    }
    showToast("Event request deleted.");
    await loadActivityData();
  }
}

async function boot() {
  const user = await getCurrentUser();
  if (!user) {
    redirectTo("/");
    return;
  }

  state.user = user;
  populateHeader(user);
  attachLocationPicker({
    inputSelector: "#activity-owned-event-location",
    buttonSelector: "#activity-location-picker",
    latitudeSelector: "#activity-owned-event-latitude",
    longitudeSelector: "#activity-owned-event-longitude",
  });
  resetOwnedEventForm();
  renderActivityAccordion();
  await loadActivityData();

  activityToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const target = toggle.dataset.activityToggle;
      if (!target) {
        return;
      }
      if (state.openPanels.has(target)) {
        state.openPanels.delete(target);
      } else {
        state.openPanels.add(target);
      }
      renderActivityAccordion();
    });
  });

  ownedEventForm?.addEventListener("submit", async (event) => {
    try {
      await handleOwnedEventSubmit(event);
    } catch (error) {
      showToast(error.message || "Could not send your event request.", "error");
    }
  });

  ownedEventCancel?.addEventListener("click", () => {
    resetOwnedEventForm();
  });

  activityImageAdd?.addEventListener("click", addImageFromInput);
  activityImageUrl?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    addImageFromInput();
  });
  activityImageBrowse?.addEventListener("click", () => {
    activityImageFiles?.click();
  });
  activityImageDropzone?.addEventListener("click", () => {
    activityImageFiles?.click();
  });
  activityImageDropzone?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    activityImageFiles?.click();
  });
  activityImageFiles?.addEventListener("change", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }
    await addImageFiles(target.files);
  });
  ["dragenter", "dragover"].forEach((eventName) => {
    activityImageDropzone?.addEventListener(eventName, (event) => {
      const transferTypes = Array.from(event.dataTransfer?.types || []);
      if (!transferTypes.includes("Files")) {
        return;
      }
      event.preventDefault();
      activityImageDropzone.classList.add("is-dragover");
    });
  });
  activityImageDropzone?.addEventListener("dragleave", (event) => {
    const relatedTarget = event.relatedTarget;
    if (relatedTarget instanceof Node && activityImageDropzone.contains(relatedTarget)) {
      return;
    }
    activityImageDropzone.classList.remove("is-dragover");
  });
  activityImageDropzone?.addEventListener("drop", async (event) => {
    const transferTypes = Array.from(event.dataTransfer?.types || []);
    if (!transferTypes.includes("Files")) {
      return;
    }
    event.preventDefault();
    activityImageDropzone.classList.remove("is-dragover");
    await addImageFiles(event.dataTransfer?.files);
  });
  activityImageClear?.addEventListener("click", () => {
    setDraftImages([]);
    clearImagePicker();
    renderImageEditor("Gallery cleared. Save the event to fall back to the default artwork.");
  });
  activityImageGallery?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const actionTarget = target.closest("[data-action]");
    if (!(actionTarget instanceof HTMLElement)) {
      return;
    }
    const index = Number(actionTarget.dataset.index);
    if (Number.isNaN(index)) {
      return;
    }
    if (actionTarget.dataset.action === "remove-image") {
      removeImage(index);
    }
    if (actionTarget.dataset.action === "cover-image") {
      setCoverImage(index);
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
      showToast(error.message || "Could not update your event.", "error");
    }
  });
}

boot();
