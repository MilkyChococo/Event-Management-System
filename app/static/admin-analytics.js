import {
  api,
  clearNotice,
  escapeHtml,
  formatCurrency,
  formatDateTime,
  getCurrentUser,
  redirectTo,
  setupAccountMenu,
  showNotice,
} from "/static/shared.js?v=20260316-toast-actions";

const messageBox = document.querySelector("#admin-analytics-message");
const refreshButton = document.querySelector("#admin-analytics-refresh");
const welcomeText = document.querySelector("#welcome-text");
const analyticsTotalRegistrations = document.querySelector("#analytics-total-registrations");
const analyticsTotalRevenue = document.querySelector("#analytics-total-revenue");
const analyticsOccupancyRate = document.querySelector("#analytics-occupancy-rate");
const analyticsAverageTicket = document.querySelector("#analytics-average-ticket");
const analyticsCustomerRatio = document.querySelector("#analytics-customer-ratio");
const analyticsCustomerMix = document.querySelector("#analytics-customer-mix");
const analyticsCountryDistribution = document.querySelector("#analytics-country-distribution");
const analyticsEventGrid = document.querySelector("#admin-event-analytics");

const state = {
  user: null,
  analytics: null,
  analyticsSidebarOpen: true,
  selectedAnalyticsEventId: null,
};

function formatPercent(value) {
  const numeric = Number(value || 0);
  const digits = Number.isInteger(numeric) ? 0 : 1;
  return `${numeric.toFixed(digits)}%`;
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

function renderAnalyticsEventPanel(event) {
  return `
    <article class="admin-card analytics-event-card">
      <div class="analytics-event-header">
        <div>
          <p class="eyebrow">Event Pulse</p>
          <h3>${escapeHtml(event.title)}</h3>
          <p class="subtle">${escapeHtml(formatDateTime(event.start_at))}</p>
        </div>
        <div class="analytics-pill-row">
          <span class="analytics-pill">${escapeHtml(formatPercent(event.fill_rate))} full</span>
          <span class="analytics-pill">${escapeHtml(formatCurrency(event.revenue))}</span>
        </div>
      </div>

      <div class="analytics-progress-panel">
        <div class="distribution-label-row">
          <strong>Seat fill</strong>
          <span>${escapeHtml(String(event.registered_count))}/${escapeHtml(String(event.capacity))}</span>
        </div>
        <div class="distribution-track distribution-track-large">
          <span class="distribution-fill distribution-fill-accent" style="width: ${Math.max(Number(event.fill_rate || 0), 0)}%;"></span>
        </div>
      </div>

      <div class="analytics-mini-grid">
        <article>
          <span>Revenue</span>
          <strong>${escapeHtml(formatCurrency(event.revenue))}</strong>
        </article>
        <article>
          <span>Ticket</span>
          <strong>${escapeHtml(formatCurrency(event.price))}</strong>
        </article>
        <article>
          <span>Demand share</span>
          <strong>${escapeHtml(formatPercent(event.share_of_registrations))}</strong>
        </article>
        <article>
          <span>Seats left</span>
          <strong>${escapeHtml(String(event.seats_left))}</strong>
        </article>
      </div>

      <div class="analytics-distribution-grid">
        <section class="analytics-distribution-panel">
          <span class="section-tag">Age distribution</span>
          ${toDistributionMarkup(event.age_distribution, "No age distribution yet for this event.")}
        </section>
        <section class="analytics-distribution-panel">
          <span class="section-tag">Country distribution</span>
          ${toDistributionMarkup(event.country_distribution, "No country distribution yet for this event.")}
        </section>
      </div>
    </article>
  `;
}

function renderEventAnalytics(events) {
  if (!Array.isArray(events) || !events.length) {
    return "<p>No event analytics available yet.</p>";
  }

  if (
    state.selectedAnalyticsEventId === null ||
    !events.some((event) => event.id === state.selectedAnalyticsEventId)
  ) {
    state.selectedAnalyticsEventId = events[0].id;
  }

  const selectedEvent = events.find((event) => event.id === state.selectedAnalyticsEventId) || events[0];

  return `
    <div class="analytics-event-shell ${state.analyticsSidebarOpen ? "is-open" : "is-collapsed"}">
      <aside class="admin-card analytics-event-sidebar">
        <button
          class="analytics-sidebar-toggle ${state.analyticsSidebarOpen ? "is-open" : ""}"
          data-action="toggle-event-analytics"
          type="button"
          aria-expanded="${state.analyticsSidebarOpen ? "true" : "false"}"
        >
          <div>
            <p class="eyebrow">Sidebar</p>
            <h3>Event analytics</h3>
          </div>
          <span class="analytics-sidebar-count">${events.length} events</span>
        </button>
        ${
          state.analyticsSidebarOpen
            ? `
                <div class="analytics-sidebar-list">
                  ${events
                    .map(
                      (event) => `
                        <button
                          class="analytics-sidebar-item ${selectedEvent?.id === event.id ? "is-active" : ""}"
                          data-action="select-analytics-event"
                          data-id="${event.id}"
                          type="button"
                          aria-pressed="${selectedEvent?.id === event.id ? "true" : "false"}"
                        >
                          <span>${escapeHtml(formatDateTime(event.start_at))}</span>
                          <strong>${escapeHtml(event.title)}</strong>
                        </button>
                      `
                    )
                    .join("")}
                </div>
              `
            : ""
        }
      </aside>
      <div class="analytics-event-stage ${selectedEvent ? "" : "is-empty"}">
        ${
          state.analyticsSidebarOpen
            ? renderAnalyticsEventPanel(selectedEvent)
            : `
                <section class="admin-card analytics-event-placeholder">
                  <p class="eyebrow">Collapsed</p>
                  <p class="subtle">Open the event sidebar to inspect revenue, seat fill, and distribution event by event.</p>
                </section>
              `
        }
      </div>
    </div>
  `;
}

function renderAnalytics() {
  if (!state.analytics) {
    return;
  }

  const { summary, customer_mix: customerMix, country_distribution: countryDistribution, events } = state.analytics;
  const analyticsEvents = Array.isArray(events) ? events : [];
  analyticsTotalRegistrations.textContent = String(summary.total_registrations);
  analyticsTotalRevenue.textContent = formatCurrency(summary.total_revenue);
  analyticsOccupancyRate.textContent = formatPercent(summary.occupancy_rate);
  analyticsAverageTicket.textContent = formatCurrency(summary.average_ticket_price);
  analyticsCustomerRatio.textContent = `${formatPercent(summary.domestic_customer_ratio)} / ${formatPercent(summary.international_customer_ratio)}`;
  analyticsCustomerMix.innerHTML = toDistributionMarkup(customerMix, "No registrations yet.");
  analyticsCountryDistribution.innerHTML = toDistributionMarkup(countryDistribution, "No market data yet.");
  analyticsEventGrid.innerHTML = renderEventAnalytics(analyticsEvents);
}

async function loadAnalytics() {
  state.analytics = await api("/api/admin/analytics");
  renderAnalytics();
}

async function boot() {
  state.user = await getCurrentUser();
  if (!state.user) {
    redirectTo("/");
    return;
  }
  if (state.user.role !== "admin") {
    redirectTo("/dashboard");
    return;
  }

  setupAccountMenu(state.user);
  welcomeText.textContent = `Welcome, ${state.user.name}`;

  refreshButton?.addEventListener("click", async () => {
    try {
      clearNotice(messageBox);
      await loadAnalytics();
      showNotice(messageBox, "Analytics refreshed.");
    } catch (error) {
      showNotice(messageBox, error.message, "error");
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

  try {
    await loadAnalytics();
  } catch (error) {
    showNotice(messageBox, error.message, "error");
  }
}

boot();
