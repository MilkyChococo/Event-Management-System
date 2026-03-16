import {
  api,
  clearNotice,
  escapeHtml,
  extractEventIdFromPath,
  formatCurrency,
  formatDateTime,
  getCurrentUser,
  redirectTo,
  setupAccountMenu,
  showNotice,
  showToast,
} from "/static/shared.js?v=20260316-toast-actions";

const messageBox = document.querySelector("[data-testid='detail-message']");
const detailTitle = document.querySelector("[data-testid='detail-title']");
const detailDescription = document.querySelector("#detail-description");
const detailGalleryTrack = document.querySelector("#detail-gallery-track");
const detailGalleryDots = document.querySelector("#detail-gallery-dots");
const detailGalleryPrev = document.querySelector("#detail-gallery-prev");
const detailGalleryNext = document.querySelector("#detail-gallery-next");
const detailPrice = document.querySelector("[data-testid='event-price']");
const detailPriceChip = document.querySelector("#detail-price-chip");
const detailLocationChip = document.querySelector("#detail-location-chip");
const detailAttendees = document.querySelector("[data-testid='event-attendees']");
const detailSeats = document.querySelector("[data-testid='event-seats']");
const detailLocation = document.querySelector("#detail-location");
const detailVenueDetails = document.querySelector("#detail-venue-details");
const detailStartAt = document.querySelector("#detail-start-at");
const detailOpening = document.querySelector("#detail-opening");
const detailMiddle = document.querySelector("#detail-middle");
const detailClosing = document.querySelector("#detail-closing");
const detailStatus = document.querySelector("[data-testid='detail-status']");
const registerButton = document.querySelector("[data-testid='detail-register']");
const cancelButton = document.querySelector("[data-testid='detail-cancel']");
const attendeeSection = document.querySelector("[data-testid='detail-attendee-section']");
const attendeeList = document.querySelector("#detail-attendee-list");
const loadAttendeesButton = document.querySelector("#detail-load-attendees");
const detailPosterRail = document.querySelector(".detail-poster-rail");
const detailPoster = document.querySelector(".detail-poster");
const desktopPosterMedia = window.matchMedia("(min-width: 880px)");

const DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg";

const state = {
  user: null,
  event: null,
  eventId: extractEventIdFromPath(),
  galleryIndex: 0,
};

function getEventImages(event) {
  const images = Array.isArray(event?.image_urls) ? event.image_urls.filter(Boolean) : [];
  if (images.length) {
    return images;
  }
  return event?.image_url ? [event.image_url] : [DEFAULT_EVENT_IMAGE];
}

function updateGalleryControls(images) {
  const hasMultiple = images.length > 1;
  detailGalleryPrev.classList.toggle("hidden", !hasMultiple);
  detailGalleryNext.classList.toggle("hidden", !hasMultiple);
  detailGalleryPrev.disabled = state.galleryIndex === 0;
  detailGalleryNext.disabled = state.galleryIndex >= images.length - 1;

  detailGalleryDots.querySelectorAll("button").forEach((button, index) => {
    button.classList.toggle("is-active", index === state.galleryIndex);
    button.setAttribute("aria-pressed", index === state.galleryIndex ? "true" : "false");
  });
}

function scrollGalleryTo(index, smooth = true) {
  const images = getEventImages(state.event);
  const boundedIndex = Math.max(0, Math.min(index, images.length - 1));
  state.galleryIndex = boundedIndex;
  const left = detailGalleryTrack.clientWidth * boundedIndex;

  if (smooth) {
    detailGalleryTrack.scrollTo({ left, behavior: "smooth" });
  } else {
    detailGalleryTrack.scrollLeft = left;
  }
  updateGalleryControls(images);
}

function syncGalleryIndexFromScroll() {
  const images = getEventImages(state.event);
  if (!images.length) {
    return;
  }

  const width = Math.max(detailGalleryTrack.clientWidth, 1);
  const index = Math.max(0, Math.min(Math.round(detailGalleryTrack.scrollLeft / width), images.length - 1));
  if (index !== state.galleryIndex) {
    state.galleryIndex = index;
    updateGalleryControls(images);
  }
}

function renderGallery() {
  const images = getEventImages(state.event);
  state.galleryIndex = 0;
  detailGalleryTrack.innerHTML = images
    .map(
      (image, index) => `
        <div class="detail-gallery-slide">
          <img
            class="detail-gallery-image"
            ${index === 0 ? 'data-testid="event-image"' : ""}
            src="${escapeHtml(image)}"
            alt="${escapeHtml(state.event.title)} image ${index + 1}"
          />
        </div>
      `
    )
    .join("");

  detailGalleryDots.innerHTML =
    images.length > 1
      ? images
          .map(
            (_, index) => `
              <button class="detail-gallery-dot ${index === 0 ? "is-active" : ""}" data-index="${index}" type="button" aria-label="View image ${index + 1}" aria-pressed="${index === 0 ? "true" : "false"}"></button>
            `
          )
          .join("")
      : "";

  updateGalleryControls(images);
  requestAnimationFrame(() => {
    scrollGalleryTo(0, false);
  });
}

function syncDetailPosterRail() {
  if (!detailPosterRail || !detailPoster) {
    return;
  }

  if (!desktopPosterMedia.matches) {
    detailPosterRail.classList.remove("is-fixed");
    detailPosterRail.style.removeProperty("--detail-poster-left");
    detailPosterRail.style.removeProperty("--detail-poster-width");
    detailPosterRail.style.removeProperty("--detail-poster-height");
    return;
  }

  const railRect = detailPosterRail.getBoundingClientRect();
  const posterHeight = Math.max(380, Math.min(window.innerHeight - 160, 620));
  detailPosterRail.style.setProperty("--detail-poster-left", `${Math.round(railRect.left)}px`);
  detailPosterRail.style.setProperty("--detail-poster-width", `${Math.round(railRect.width)}px`);
  detailPosterRail.style.setProperty("--detail-poster-height", `${Math.round(posterHeight)}px`);
  detailPosterRail.classList.add("is-fixed");
}

function renderEvent() {
  if (!state.event) {
    return;
  }

  renderGallery();
  requestAnimationFrame(syncDetailPosterRail);
  detailTitle.textContent = state.event.title;
  detailDescription.textContent = state.event.description;
  detailPrice.textContent = `${formatCurrency(state.event.price)} per ticket`;
  detailPriceChip.textContent = `${formatCurrency(state.event.price)} / ticket`;
  detailLocationChip.textContent = state.event.location;
  detailAttendees.textContent = `${state.event.registered_count} people`;
  detailSeats.textContent = `${state.event.seats_left}/${state.event.capacity}`;
  detailLocation.textContent = state.event.location;
  detailVenueDetails.textContent = state.event.venue_details || state.event.location;
  detailStartAt.textContent = formatDateTime(state.event.start_at);
  detailOpening.textContent = state.event.opening_highlights || "Opening details will be announced soon.";
  detailMiddle.textContent = state.event.mid_event_highlights || "Main-program details will be announced soon.";
  detailClosing.textContent = state.event.closing_highlights || "Closing details will be announced soon.";
  detailStatus.textContent = state.event.is_registered ? "Reserved" : "Not reserved yet";
  registerButton.classList.toggle("hidden", state.event.is_registered);
  cancelButton.classList.toggle("hidden", !state.event.is_registered);
  registerButton.disabled = state.event.seats_left === 0;
}

async function loadEvent() {
  state.event = await api(`/api/events/${state.eventId}`);
  renderEvent();
}

async function loadAttendees() {
  const attendees = await api(`/api/events/${state.eventId}/registrations`);
  attendeeList.innerHTML = attendees.length
    ? `<ul>${attendees
        .map((attendee) => `<li>${escapeHtml(attendee.name)} - ${escapeHtml(attendee.email)} - ${escapeHtml(attendee.registered_at)}</li>`)
        .join("")}</ul>`
    : "<p>No attendees registered yet.</p>";
}

async function handleRegister() {
  clearNotice(messageBox);
  try {
    state.event = await api(`/api/events/${state.eventId}/register`, { method: "POST" });
    renderEvent();
    showToast("Seat reserved successfully.");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function handleCancel() {
  clearNotice(messageBox);
  try {
    state.event = await api(`/api/events/${state.eventId}/register`, { method: "DELETE" });
    renderEvent();
    showToast("Reservation cancelled.");
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
  if (!state.eventId) {
    redirectTo("/dashboard");
    return;
  }

  setupAccountMenu(state.user);
  attendeeSection.classList.toggle("hidden", state.user.role !== "admin");
  registerButton.addEventListener("click", handleRegister);
  cancelButton.addEventListener("click", handleCancel);
  detailGalleryPrev.addEventListener("click", () => {
    scrollGalleryTo(state.galleryIndex - 1);
  });
  detailGalleryNext.addEventListener("click", () => {
    scrollGalleryTo(state.galleryIndex + 1);
  });
  detailGalleryTrack.addEventListener("scroll", syncGalleryIndexFromScroll);
  detailGalleryDots.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || target.dataset.index === undefined) {
      return;
    }
    scrollGalleryTo(Number(target.dataset.index));
  });
  window.addEventListener("resize", () => {
    syncDetailPosterRail();
    if (state.event) {
      requestAnimationFrame(() => {
        scrollGalleryTo(state.galleryIndex, false);
      });
    }
  });
  loadAttendeesButton.addEventListener("click", async () => {
    try {
      await loadAttendees();
    } catch (error) {
      showNotice(messageBox, error.message, "error");
    }
  });

  syncDetailPosterRail();

  await loadEvent();
}

boot();