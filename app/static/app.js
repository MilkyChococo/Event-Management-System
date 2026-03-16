const state = {
  user: null,
  events: [],
  selectedEvent: null,
  attendees: [],
};

const elements = {
  greeting: document.querySelector("[data-testid='user-greeting']"),
  messageBox: document.querySelector("[data-testid='message-box']"),
  loginForm: document.querySelector("#login-form"),
  registerForm: document.querySelector("#register-form"),
  logoutButton: document.querySelector("#logout-button"),
  refreshButton: document.querySelector("#refresh-events"),
  eventList: document.querySelector("[data-testid='event-list']"),
  eventDetail: document.querySelector("[data-testid='event-detail']"),
  adminPanel: document.querySelector("[data-testid='admin-panel']"),
  attendeeList: document.querySelector("[data-testid='attendee-list']"),
  adminForm: document.querySelector("#admin-event-form"),
  adminReset: document.querySelector("#admin-reset"),
};

function showMessage(message, kind = "info") {
  elements.messageBox.textContent = message;
  elements.messageBox.className = `message ${kind}`;
}

function clearMessage() {
  elements.messageBox.textContent = "";
  elements.messageBox.className = "message hidden";
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.error?.message || "Unexpected request failure.";
    throw new Error(message);
  }
  return payload;
}

function toDatetimeLocal(value) {
  return value.slice(0, 16);
}

function fromDatetimeLocal(value) {
  return `${value}:00`;
}

function setSelectedEvent(event) {
  state.selectedEvent = event;
  renderEventDetail();
}

function renderGreeting() {
  if (state.user) {
    elements.greeting.innerHTML = `
      <strong>Signed in</strong>
      <p>${state.user.name} (${state.user.role})</p>
      <p>${state.user.email}</p>
    `;
    elements.logoutButton.classList.remove("hidden");
  } else {
    elements.greeting.innerHTML = `
      <strong>Anonymous visitor</strong>
      <p>Use seeded accounts or register a new user.</p>
      <p>Admin: admin@example.com / Admin123!</p>
      <p>User: student@example.com / Student123!</p>
    `;
    elements.logoutButton.classList.add("hidden");
  }
  elements.adminPanel.classList.toggle("hidden", state.user?.role !== "admin");
}

function renderEventList() {
  if (!state.events.length) {
    elements.eventList.innerHTML = "<p>No events available.</p>";
    return;
  }

  const cards = state.events
    .map((event) => {
      const registerButton = state.user
        ? event.is_registered
          ? `<button type="button" class="ghost js-cancel" data-id="${event.id}">Cancel</button>`
          : `<button type="button" class="js-register" data-id="${event.id}" ${event.seats_left === 0 ? "disabled" : ""}>Register</button>`
        : `<button type="button" class="ghost" disabled>Login required</button>`;

      const adminActions =
        state.user?.role === "admin"
          ? `
              <button type="button" class="ghost js-edit" data-id="${event.id}">Edit</button>
              <button type="button" class="danger js-delete" data-id="${event.id}">Delete</button>
              <button type="button" class="ghost js-attendees" data-id="${event.id}">Attendees</button>
            `
          : "";

      return `
        <article class="event-card" data-testid="event-card-${event.id}">
          <h3>${event.title}</h3>
          <p>${event.description}</p>
          <p><span class="pill">${event.location}</span><span class="pill">${event.start_at}</span></p>
          <p data-testid="event-seats-${event.id}">Seats left: ${event.seats_left} / ${event.capacity}</p>
          <div class="button-row">
            <button type="button" class="ghost js-detail" data-id="${event.id}">View detail</button>
            ${registerButton}
            ${adminActions}
          </div>
        </article>
      `;
    })
    .join("");

  elements.eventList.innerHTML = cards;
}

function renderEventDetail() {
  const event = state.selectedEvent;
  if (!event) {
    elements.eventDetail.textContent = "Select an event to inspect details.";
    return;
  }
  elements.eventDetail.innerHTML = `
    <h3>${event.title}</h3>
    <p>${event.description}</p>
    <p><strong>Location:</strong> ${event.location}</p>
    <p><strong>Start time:</strong> ${event.start_at}</p>
    <p><strong>Registered:</strong> ${event.registered_count}</p>
    <p><strong>Seats left:</strong> ${event.seats_left}</p>
    <p><strong>Your status:</strong> ${event.is_registered ? "Registered" : "Not registered"}</p>
  `;
}

function renderAttendees() {
  if (!state.attendees.length) {
    elements.attendeeList.textContent = "No attendees yet for the selected event.";
    return;
  }
  elements.attendeeList.innerHTML = `
    <ul>
      ${state.attendees
        .map((attendee) => `<li>${attendee.name} - ${attendee.email} - ${attendee.registered_at}</li>`)
        .join("")}
    </ul>
  `;
}

async function loadSession() {
  try {
    state.user = await api("/api/me");
  } catch {
    state.user = null;
  }
  renderGreeting();
}

async function loadEvents(selectedId = null) {
  state.events = await api("/api/events");
  renderEventList();

  const nextSelected =
    state.events.find((event) => event.id === selectedId) ||
    state.events.find((event) => event.id === state.selectedEvent?.id) ||
    state.events[0] ||
    null;

  if (nextSelected) {
    state.selectedEvent = await api(`/api/events/${nextSelected.id}`);
  } else {
    state.selectedEvent = null;
  }
  renderEventDetail();
}

async function handleLogin(event) {
  event.preventDefault();
  clearMessage();
  const payload = {
    email: document.querySelector("#login-email").value,
    password: document.querySelector("#login-password").value,
  };
  try {
    state.user = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderGreeting();
    await loadEvents(state.selectedEvent?.id || null);
    showMessage("Login successful.");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  clearMessage();
  const payload = {
    name: document.querySelector("#register-name").value,
    email: document.querySelector("#register-email").value,
    password: document.querySelector("#register-password").value,
  };
  try {
    await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showMessage("Account created. You can now login.");
    elements.registerForm.reset();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function handleLogout() {
  clearMessage();
  await api("/api/auth/logout", { method: "POST" });
  state.user = null;
  state.attendees = [];
  renderGreeting();
  renderAttendees();
  await loadEvents(state.selectedEvent?.id || null);
  showMessage("Logged out.");
}

async function handleEventAction(target) {
  const eventId = Number(target.dataset.id);
  if (target.classList.contains("js-detail")) {
    setSelectedEvent(await api(`/api/events/${eventId}`));
    return;
  }
  if (target.classList.contains("js-register")) {
    const updated = await api(`/api/events/${eventId}/register`, { method: "POST" });
    showMessage("Registration successful.");
    await loadEvents(updated.id);
    return;
  }
  if (target.classList.contains("js-cancel")) {
    const updated = await api(`/api/events/${eventId}/register`, { method: "DELETE" });
    showMessage("Registration cancelled.");
    await loadEvents(updated.id);
    return;
  }
  if (target.classList.contains("js-edit")) {
    const eventData = await api(`/api/events/${eventId}`);
    document.querySelector("#event-id").value = eventData.id;
    document.querySelector("#event-title").value = eventData.title;
    document.querySelector("#event-description").value = eventData.description;
    document.querySelector("#event-location").value = eventData.location;
    document.querySelector("#event-start-at").value = toDatetimeLocal(eventData.start_at);
    document.querySelector("#event-capacity").value = eventData.capacity;
    showMessage(`Editing event "${eventData.title}".`);
    return;
  }
  if (target.classList.contains("js-delete")) {
    await api(`/api/admin/events/${eventId}`, { method: "DELETE" });
    showMessage("Event deleted.");
    await loadEvents();
    return;
  }
  if (target.classList.contains("js-attendees")) {
    state.attendees = await api(`/api/events/${eventId}/registrations`);
    renderAttendees();
  }
}

async function handleAdminSave(event) {
  event.preventDefault();
  clearMessage();
  const eventId = document.querySelector("#event-id").value;
  const payload = {
    title: document.querySelector("#event-title").value,
    description: document.querySelector("#event-description").value,
    location: document.querySelector("#event-location").value,
    start_at: fromDatetimeLocal(document.querySelector("#event-start-at").value),
    capacity: Number(document.querySelector("#event-capacity").value),
  };
  const url = eventId ? `/api/admin/events/${eventId}` : "/api/admin/events";
  const method = eventId ? "PUT" : "POST";
  try {
    const saved = await api(url, {
      method,
      body: JSON.stringify(payload),
    });
    showMessage(eventId ? "Event updated." : "Event created.");
    elements.adminForm.reset();
    document.querySelector("#event-id").value = "";
    await loadEvents(saved.id);
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function resetAdminForm() {
  elements.adminForm.reset();
  document.querySelector("#event-id").value = "";
  showMessage("Admin form reset.");
}

async function boot() {
  elements.loginForm.addEventListener("submit", handleLogin);
  elements.registerForm.addEventListener("submit", handleRegister);
  elements.logoutButton.addEventListener("click", handleLogout);
  elements.refreshButton.addEventListener("click", async () => {
    clearMessage();
    await loadEvents(state.selectedEvent?.id || null);
    showMessage("Event list refreshed.");
  });
  elements.eventList.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (!target.dataset.id) {
      return;
    }
    try {
      clearMessage();
      await handleEventAction(target);
    } catch (error) {
      showMessage(error.message, "error");
    }
  });
  elements.adminForm.addEventListener("submit", handleAdminSave);
  elements.adminReset.addEventListener("click", resetAdminForm);

  await loadSession();
  await loadEvents();
  renderAttendees();
}

boot().catch((error) => {
  showMessage(error.message, "error");
});
