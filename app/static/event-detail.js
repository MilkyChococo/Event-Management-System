import {
  api,
  clearNotice,
  escapeHtml,
  extractEventIdFromPath,
  formatCurrency,
  formatDateTime,
  getCurrentUser,
  redirectTo,
  setupGlobalFooter,
  setupAccountMenu,
  showNotice,
  showToast,
} from "/static/shared.js?v=20260328-notification-reminder-cta";

const messageBox = document.querySelector("[data-testid='detail-message']");
const detailTitle = document.querySelector("[data-testid='detail-title']");
const detailDescription = document.querySelector("#detail-description");
const detailDescriptionBlock = document.querySelector("#detail-description-block");
const detailGalleryTrack = document.querySelector("#detail-gallery-track");
const detailGalleryDots = document.querySelector("#detail-gallery-dots");
const detailGalleryPrev = document.querySelector("#detail-gallery-prev");
const detailGalleryNext = document.querySelector("#detail-gallery-next");
const detailPrice = document.querySelector("[data-testid='event-price']");
const detailPriceChip = document.querySelector("#detail-price-chip");
const detailLocationChip = document.querySelector("#detail-location-chip");
const detailAttendees = document.querySelector("[data-testid='event-attendees']");
const detailSeats = document.querySelector("[data-testid='event-seats']");
const detailMapPreview = document.querySelector("#detail-map-preview");
const detailMapFrame = document.querySelector("#detail-map-frame");
const detailMapFallback = document.querySelector("#detail-map-fallback");
const detailStartAt = document.querySelector("#detail-start-at");
const detailCategoryBadge = document.querySelector("#detail-category-badge");
const detailFormatBadge = document.querySelector("#detail-format-badge");
const detailDeadlineBadge = document.querySelector("#detail-deadline-badge");
const detailMapLink = document.querySelector("#detail-map-link");
const detailOrganizerName = document.querySelector("#detail-organizer-name");
const detailOrganizerDetails = document.querySelector("#detail-organizer-details");
const detailSpeakers = document.querySelector("#detail-speakers");
const detailTicketTiers = document.querySelector("#detail-ticket-tiers");
const detailRefundPolicy = document.querySelector("#detail-refund-policy");
const detailCheckInPolicy = document.querySelector("#detail-check-in-policy");
const detailContact = document.querySelector("#detail-contact");
const detailOpening = document.querySelector("#detail-opening");
const detailMiddle = document.querySelector("#detail-middle");
const detailClosing = document.querySelector("#detail-closing");
const detailStatus = document.querySelector("[data-testid='detail-status']");
const registerButton = document.querySelector("[data-testid='detail-register']");
const cancelButton = document.querySelector("[data-testid='detail-cancel']");
const detailRegistrationModal = document.querySelector("#detail-registration-modal");
const detailRegistrationClose = document.querySelector("#detail-registration-close");
const detailRegistrationCancel = document.querySelector("#detail-registration-cancel");
const detailRegistrationForm = document.querySelector("#detail-registration-form");
const detailRegistrationQuantity = document.querySelector("#detail-registration-quantity");
const detailRegistrationName = document.querySelector("#detail-registration-name");
const detailRegistrationEmail = document.querySelector("#detail-registration-email");
const detailRegistrationPhone = document.querySelector("#detail-registration-phone");
const detailRegistrationSummary = document.querySelector("#detail-registration-summary");
const detailRegistrationQuantityFocus = document.querySelector("#detail-registration-quantity-focus");
const detailRegistrationPriceFocus = document.querySelector("#detail-registration-price-focus");
const attendeeSection = document.querySelector("[data-testid='detail-attendee-section']");
const attendeeList = document.querySelector("#detail-attendee-list");
const loadAttendeesButton = document.querySelector("#detail-load-attendees");
const detailLayout = document.querySelector(".detail-layout");
const detailPosterRail = document.querySelector(".detail-poster-rail");
const detailPoster = document.querySelector(".detail-poster");
const desktopPosterMedia = window.matchMedia("(min-width: 880px)");

const DEFAULT_EVENT_IMAGE = "/static/images/default-event.svg";

const state = {
  user: null,
  event: null,
  eventId: extractEventIdFromPath(),
  galleryIndex: 0,
  registrationOpen: false,
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
  if (!detailPosterRail) {
    return;
  }

  detailPosterRail.classList.remove("is-fixed");
  detailPosterRail.style.removeProperty("--detail-poster-left");
  detailPosterRail.style.removeProperty("--detail-poster-width");
  detailPosterRail.style.removeProperty("--detail-poster-height");
  detailLayout?.style.removeProperty("--detail-layout-min-height");
}

function buildDetailMapQuery(event) {
  return [event?.location, event?.venue_details].filter(Boolean).join(", ").trim();
}

function hasDetailCoordinates(event) {
  const latitude = Number(event?.latitude);
  const longitude = Number(event?.longitude);
  return Number.isFinite(latitude) && Number.isFinite(longitude);
}

function buildDetailMapEmbedUrl(event, query) {
  if (hasDetailCoordinates(event)) {
    return `https://www.google.com/maps?q=${encodeURIComponent(`${Number(event.latitude)},${Number(event.longitude)}`)}&z=16&output=embed`;
  }
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}&z=15&output=embed`;
}

function buildDetailMapOpenUrl(event, query) {
  const explicitUrl = String(event?.map_url || "").trim();
  if (explicitUrl) {
    return explicitUrl;
  }
  if (hasDetailCoordinates(event)) {
    return `https://www.google.com/maps/search/?api=1&query=${Number(event.latitude)},${Number(event.longitude)}`;
  }
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}`;
}

function shouldAutoOpenRegistration() {
  return new URLSearchParams(window.location.search).get("reserve") === "1";
}

function clearAutoOpenRegistrationFlag() {
  const url = new URL(window.location.href);
  url.searchParams.delete("reserve");
  const nextSearch = url.searchParams.toString();
  const nextUrl = `${url.pathname}${nextSearch ? `?${nextSearch}` : ""}${url.hash}`;
  window.history.replaceState({}, "", nextUrl);
}

function renderSpeakerList(speakers) {
  if (!detailSpeakers) {
    return;
  }
  if (!Array.isArray(speakers) || !speakers.length) {
    detailSpeakers.innerHTML = '<p class="subtle">Speaker lineup will be announced soon.</p>';
    return;
  }
  detailSpeakers.innerHTML = speakers.map((speaker) => `<article class="detail-list-item">${escapeHtml(speaker)}</article>`).join("");
}

function renderTicketTypeList(ticketTypes) {
  if (!detailTicketTiers) {
    return;
  }
  if (!Array.isArray(ticketTypes) || !ticketTypes.length) {
    detailTicketTiers.innerHTML = '<p class="subtle">Ticket details will be announced soon.</p>';
    return;
  }
  detailTicketTiers.innerHTML = ticketTypes
    .map(
      (ticket) => `
        <article class="detail-ticket-tier">
          <div>
            <strong>${escapeHtml(ticket.label)}</strong>
            <p class="subtle">${escapeHtml(ticket.details || "Full event access.")}</p>
          </div>
          <span class="event-price-badge">${escapeHtml(formatCurrency(ticket.price))}</span>
        </article>
      `
    )
    .join("");
}

function renderRegistrationSummary() {
  if (!detailRegistrationSummary || !state.event) {
    return;
  }
  const maxQuantity = Math.max(1, Math.min(5, Number(state.event.seats_left || 0) || 1));
  const requestedQuantity = Number(detailRegistrationQuantity?.value || 1);
  const quantity = Math.max(1, Math.min(maxQuantity, Number.isFinite(requestedQuantity) ? requestedQuantity : 1));
  if (detailRegistrationQuantity) {
    detailRegistrationQuantity.value = String(quantity);
    detailRegistrationQuantity.max = String(maxQuantity);
  }
  const pricePerTicket = Number(state.event.price || state.event.ticket_types?.[0]?.price || 0);
  const totalPrice = pricePerTicket * quantity;

  if (detailRegistrationQuantityFocus) {
    detailRegistrationQuantityFocus.innerHTML = `
      <span>Quantity</span>
      <strong>${escapeHtml(String(quantity))} ticket${quantity > 1 ? "s" : ""}</strong>
      <p class="subtle">Limit ${escapeHtml(String(maxQuantity))} for this event.</p>
    `;
  }

  if (detailRegistrationPriceFocus) {
    detailRegistrationPriceFocus.innerHTML = `
      <span>Price</span>
      <strong>${escapeHtml(formatCurrency(pricePerTicket))} per ticket</strong>
      <p class="subtle">Total ${escapeHtml(formatCurrency(totalPrice))}</p>
    `;
  }

  detailRegistrationSummary.innerHTML = `
    <article class="detail-registration-summary-item">
      <span>Event</span>
      <strong>${escapeHtml(state.event.title)}</strong>
    </article>
    <article class="detail-registration-summary-item">
      <span>Attendee</span>
      <strong>${escapeHtml(detailRegistrationName?.value.trim() || state.user?.name || "")}</strong>
      <p class="subtle">${escapeHtml(detailRegistrationEmail?.value.trim() || state.user?.email || "")}</p>
    </article>
    <article class="detail-registration-summary-item">
      <span>Venue</span>
      <strong>${escapeHtml(state.event.location)}</strong>
      <p class="subtle">${escapeHtml(formatDateTime(state.event.start_at))}</p>
    </article>
  `;
}

function openRegistrationModal() {
  if (!state.event || state.event.is_registered || !detailRegistrationModal) {
    return;
  }
  const maxQuantity = Math.max(1, Math.min(5, Number(state.event.seats_left || 0) || 1));
  if (detailRegistrationQuantity) {
    detailRegistrationQuantity.min = "1";
    detailRegistrationQuantity.max = String(maxQuantity);
    detailRegistrationQuantity.value = "1";
  }
  detailRegistrationName.value = state.user?.name || "";
  detailRegistrationEmail.value = state.user?.email || "";
  detailRegistrationPhone.value = state.user?.phone_number || "";
  renderRegistrationSummary();
  detailRegistrationModal.classList.remove("hidden");
  detailRegistrationModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  state.registrationOpen = true;
  detailRegistrationQuantity?.focus();
}

function closeRegistrationModal() {
  detailRegistrationModal?.classList.add("hidden");
  detailRegistrationModal?.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  state.registrationOpen = false;
  if (detailRegistrationSummary) {
    detailRegistrationSummary.innerHTML = "";
  }
  if (detailRegistrationQuantityFocus) {
    detailRegistrationQuantityFocus.innerHTML = "";
  }
  if (detailRegistrationPriceFocus) {
    detailRegistrationPriceFocus.innerHTML = "";
  }
}

function renderEvent() {
  if (!state.event) {
    return;
  }

  renderGallery();
  requestAnimationFrame(syncDetailPosterRail);
  detailTitle.textContent = state.event.title;
  if (detailDescription) {
    detailDescription.textContent = "";
    detailDescription.classList.add("hidden");
  }
  if (detailDescriptionBlock) {
    detailDescriptionBlock.textContent = state.event.description || "Event details will be published soon.";
  }
  detailPrice.textContent = `${formatCurrency(state.event.price)} per ticket`;
  detailPriceChip.textContent = `${formatCurrency(state.event.price)} / ticket`;
  detailLocationChip.textContent = state.event.location;
  detailAttendees.textContent = `${state.event.registered_count} people`;
  detailSeats.textContent = `${state.event.seats_left}/${state.event.capacity}`;
  const detailMapQuery = buildDetailMapQuery(state.event);
  const hasMapTarget = Boolean(detailMapQuery || hasDetailCoordinates(state.event));
  if (detailMapFrame) {
    detailMapFrame.src = hasMapTarget ? buildDetailMapEmbedUrl(state.event, detailMapQuery) : "";
    detailMapFrame.classList.toggle("hidden", !hasMapTarget);
  }
  if (detailMapPreview) {
    detailMapPreview.classList.toggle("is-empty", !hasMapTarget);
  }
  if (detailMapFallback) {
    detailMapFallback.classList.toggle("hidden", hasMapTarget);
    detailMapFallback.textContent = hasMapTarget ? "" : "Map preview will appear here once the venue address is available.";
  }
  detailStartAt.textContent = formatDateTime(state.event.start_at);
  detailCategoryBadge.textContent = state.event.category || "Special Event";
  detailFormatBadge.textContent = state.event.event_format || "Offline";
  detailDeadlineBadge.textContent = state.event.registration_deadline ? `Register by ${formatDateTime(state.event.registration_deadline)}` : "Registration open";
  detailRefundPolicy.textContent = state.event.refund_policy || "Refund policy will be announced soon.";
  detailCheckInPolicy.textContent = state.event.check_in_policy || "Check-in instructions will be announced soon.";
  detailContact.textContent = [state.event.contact_email, state.event.contact_phone].filter(Boolean).join(" - ") || "Support details will be announced soon.";
  const detailMapOpenUrl = hasMapTarget ? buildDetailMapOpenUrl(state.event, detailMapQuery) : "#";
  detailMapLink.href = detailMapOpenUrl;
  detailMapLink.classList.toggle("hidden", !hasMapTarget);
  renderSpeakerList(state.event.speaker_lineup || []);
  renderTicketTypeList(state.event.ticket_types || []);
  detailStatus.textContent = state.event.is_registered ? "Reserved" : "Not reserved yet";
  registerButton.classList.toggle("hidden", state.event.is_registered);
  cancelButton.classList.toggle("hidden", !state.event.is_registered);
  registerButton.disabled = state.event.seats_left === 0;
  renderRegistrationSummary();
}

async function loadEvent() {
  state.event = await api(`/api/events/${state.eventId}`);
  renderEvent();

  if (shouldAutoOpenRegistration()) {
    clearAutoOpenRegistrationFlag();
    if (state.event.is_registered) {
      showToast("You already have a reservation for this event.");
      return;
    }
    if (state.event.seats_left <= 0) {
      showToast("No seats left for this event.", "error");
      return;
    }
    openRegistrationModal();
  }
}

async function loadAttendees() {
  const attendees = await api(`/api/events/${state.eventId}/registrations`);
  attendeeList.innerHTML = attendees.length
    ? `<ul>${attendees
        .map(
          (attendee) =>
            `<li>${escapeHtml(attendee.name)} - ${escapeHtml(attendee.email)} - ${escapeHtml(String(attendee.quantity || 1))} ticket(s) - ${escapeHtml(attendee.status)} - ${escapeHtml(attendee.registered_at)}</li>`
        )
        .join("")}</ul>`
    : "<p>No attendees registered yet.</p>";
}

function handleRegister() {
  clearNotice(messageBox);
  openRegistrationModal();
}

async function handleRegistrationSubmit(event) {
  event.preventDefault();
  try {
    const maxQuantity = Math.max(1, Math.min(5, Number(state.event?.seats_left || 0) || 1));
    const requestedQuantity = Number(detailRegistrationQuantity?.value || 1);
    const quantity = Math.max(1, Math.min(maxQuantity, Number.isFinite(requestedQuantity) ? requestedQuantity : 1));
    state.event = await api(`/api/events/${state.eventId}/register`, {
      method: "POST",
      body: JSON.stringify({
        quantity,
        attendee_name: detailRegistrationName.value.trim(),
        attendee_email: detailRegistrationEmail.value.trim(),
        attendee_phone: detailRegistrationPhone.value.trim(),
      }),
    });
    closeRegistrationModal();
    renderEvent();
    showToast(quantity > 1 ? `${quantity} seats reserved successfully.` : "Seat reserved successfully.");
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
  setupGlobalFooter(state.user);
  attendeeSection.classList.toggle("hidden", state.user.role !== "admin");
  registerButton.addEventListener("click", handleRegister);
  cancelButton.addEventListener("click", handleCancel);
  detailRegistrationClose?.addEventListener("click", closeRegistrationModal);
  detailRegistrationCancel?.addEventListener("click", closeRegistrationModal);
  detailRegistrationForm?.addEventListener("submit", handleRegistrationSubmit);
  detailRegistrationModal?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.closest('[data-action="close-detail-registration"]')) {
      closeRegistrationModal();
    }
  });
  [detailRegistrationQuantity, detailRegistrationName, detailRegistrationEmail, detailRegistrationPhone].forEach((element) => {
    element?.addEventListener("input", renderRegistrationSummary);
    element?.addEventListener("change", renderRegistrationSummary);
  });
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
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.registrationOpen) {
      closeRegistrationModal();
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
















