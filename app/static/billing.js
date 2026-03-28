import {
  api,
  escapeHtml,
  formatCurrency,
  formatDateTime,
  getCurrentUser,
  redirectTo,
  renderUserAvatar,
  setupAccountMenu,
  setupGlobalFooter,
  showToast,
} from "/static/shared.js?v=20260328-notification-reminder-cta";

const profileAvatar = document.querySelector("[data-testid='profile-avatar']");
const profileRole = document.querySelector("#profile-role");
const billingHeroCopy = document.querySelector("#billing-hero-copy");
const walletBalance = document.querySelector("#wallet-balance");
const walletTopUpForm = document.querySelector("#wallet-topup-form");
const walletTopUpAmount = document.querySelector("#wallet-topup-amount");
const walletTopUpNote = document.querySelector("#wallet-topup-note");
const walletTopUpSubmit = document.querySelector("#wallet-topup-submit");
const walletQrEmpty = document.querySelector("#wallet-qr-empty");
const walletQrShell = document.querySelector("#wallet-qr-shell");
const walletQrImage = document.querySelector("#wallet-qr-image");
const walletQrPayload = document.querySelector("#wallet-qr-payload");
const walletConfirmButton = document.querySelector("#wallet-confirm-button");
const walletTransactionList = document.querySelector("#wallet-transaction-list");
const walletExportButton = document.querySelector("#wallet-export-button");
const walletExportSummary = document.querySelector("#wallet-export-summary");
const walletExportChart = document.querySelector("#wallet-export-chart");
const walletExportEmpty = document.querySelector("#wallet-export-empty");
const billingToggles = Array.from(document.querySelectorAll("[data-billing-toggle]"));
const exportRangeButtons = Array.from(document.querySelectorAll("[data-export-range]"));
const defaultTopUpSubmitLabel = walletTopUpSubmit?.textContent?.trim() || "Generate QR & top up";
const EXPORT_RANGE_LABELS = {
  day: "Last 7 days",
  month: "Last 12 months",
  year: "Last 5 years",
};

const state = {
  user: null,
  walletTransactions: [],
  pendingTopUp: null,
  pendingCountdownTimer: 0,
  openPanels: new Set(),
  exportRange: "month",
};

function roundMoney(value) {
  return Math.round((Number(value || 0) + Number.EPSILON) * 100) / 100;
}

function populateHero(user) {
  renderUserAvatar(profileAvatar, user, "profile-avatar-image");
  if (profileRole) {
    profileRole.textContent = user.role;
  }
  if (billingHeroCopy) {
    billingHeroCopy.textContent = `${user.name}  ${user.email}`;
  }
  setupAccountMenu(user);
  setupGlobalFooter(user);
}

function clearPendingCountdown() {
  if (state.pendingCountdownTimer) {
    window.clearInterval(state.pendingCountdownTimer);
    state.pendingCountdownTimer = 0;
  }
}

function setTopUpFormLocked(locked) {
  walletTopUpForm?.classList.toggle("is-locked", locked);
  [walletTopUpAmount, walletTopUpNote, walletTopUpSubmit].forEach((element) => {
    if (element) {
      element.disabled = locked;
    }
  });
}

function updateTopUpSubmitLabel() {
  if (!walletTopUpSubmit) {
    return;
  }
  if (!state.pendingTopUp) {
    walletTopUpSubmit.textContent = defaultTopUpSubmitLabel;
    return;
  }
  const seconds = Math.max(Number(state.pendingTopUp.seconds_remaining || 0), 0);
  walletTopUpSubmit.textContent = `Generate QR again in ${seconds}s`;
}

function renderBillingAccordion() {
  billingToggles.forEach((toggle) => {
    const target = toggle.dataset.billingToggle;
    if (!target) {
      return;
    }
    const isOpen = state.openPanels.has(target);
    toggle.classList.toggle("is-open", isOpen);
    toggle.classList.toggle("is-active", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));

    const icon = toggle.querySelector("[data-billing-icon]");
    if (icon) {
      icon.textContent = isOpen ? "^" : "v";
    }

    const panel = document.querySelector(`[data-billing-panel='${target}']`);
    if (panel instanceof HTMLElement) {
      panel.classList.toggle("hidden", !isOpen);
      panel.classList.toggle("is-active", isOpen);
    }
  });
}

function renderTransactions() {
  if (!walletTransactionList) {
    return;
  }

  if (!state.walletTransactions.length) {
    walletTransactionList.innerHTML = '<p class="subtle">No completed wallet activity yet. Confirm a QR payment or reserve an event to see movement here.</p>';
    return;
  }

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

function isBillingExportTransaction(transaction) {
  return String(transaction?.kind || "").trim() === "reservation_charge";
}

function buildExportBuckets(range) {
  const now = new Date();

  if (range === "day") {
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return Array.from({ length: 7 }, (_, index) => {
      const start = new Date(todayStart);
      start.setDate(todayStart.getDate() - 6 + index);
      const end = new Date(start);
      end.setDate(start.getDate() + 1);
      return {
        label: start.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        start,
        end,
        total: 0,
      };
    });
  }

  if (range === "year") {
    return Array.from({ length: 5 }, (_, index) => {
      const year = now.getFullYear() - 4 + index;
      const start = new Date(year, 0, 1);
      const end = new Date(year + 1, 0, 1);
      return {
        label: String(year),
        start,
        end,
        total: 0,
      };
    });
  }

  const currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  return Array.from({ length: 12 }, (_, index) => {
    const start = new Date(currentMonthStart.getFullYear(), currentMonthStart.getMonth() - 11 + index, 1);
    const end = new Date(start.getFullYear(), start.getMonth() + 1, 1);
    return {
      label: start.toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
      start,
      end,
      total: 0,
    };
  });
}

function buildExportSeries(range) {
  const buckets = buildExportBuckets(range);
  const spendTransactions = state.walletTransactions.filter(isBillingExportTransaction);

  spendTransactions.forEach((transaction) => {
    const createdAt = new Date(transaction.created_at);
    if (Number.isNaN(createdAt.getTime())) {
      return;
    }
    const bucket = buckets.find(({ start, end }) => createdAt >= start && createdAt < end);
    if (bucket) {
      bucket.total = roundMoney(bucket.total + Math.abs(Number(transaction.amount || 0)));
    }
  });

  return buckets;
}

function buildBillingLineChartSvg(buckets) {
  const width = 780;
  const height = 320;
  const padding = { top: 24, right: 18, bottom: 52, left: 62 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const values = buckets.map((bucket) => Number(bucket.total || 0));
  const rawMax = Math.max(...values, 0);
  const domainMax = rawMax > 0 ? Math.ceil(rawMax / 10) * 10 : 10;
  const baselineY = padding.top + innerHeight;
  const stepX = buckets.length > 1 ? innerWidth / (buckets.length - 1) : 0;
  const toX = (index) => padding.left + stepX * index;
  const toY = (value) => padding.top + innerHeight - (value / domainMax) * innerHeight;

  const linePath = buckets
    .map((bucket, index) => `${index === 0 ? "M" : "L"} ${toX(index).toFixed(2)} ${toY(bucket.total).toFixed(2)}`)
    .join(" ");
  const areaPath = `${linePath} L ${toX(buckets.length - 1).toFixed(2)} ${baselineY.toFixed(2)} L ${toX(0).toFixed(2)} ${baselineY.toFixed(2)} Z`;

  const grid = Array.from({ length: 5 }, (_, index) => {
    const value = (domainMax / 4) * (4 - index);
    const y = toY(value);
    return `
      <g>
        <line x1="${padding.left}" y1="${y.toFixed(2)}" x2="${(width - padding.right).toFixed(2)}" y2="${y.toFixed(2)}" stroke="rgba(17, 57, 70, 0.12)" stroke-width="1" />
        <text x="${padding.left - 10}" y="${(y + 4).toFixed(2)}" fill="rgba(86, 101, 112, 0.88)" font-size="12" text-anchor="end">${escapeHtml(
          formatCurrency(value)
        )}</text>
      </g>
    `;
  }).join("");

  const xLabels = buckets
    .map(
      (bucket, index) => `
        <text x="${toX(index).toFixed(2)}" y="${height - 18}" fill="rgba(86, 101, 112, 0.92)" font-size="12" text-anchor="middle">${escapeHtml(bucket.label)}</text>
      `
    )
    .join("");

  const points = buckets
    .map(
      (bucket, index) => `
        <g>
          <circle cx="${toX(index).toFixed(2)}" cy="${toY(bucket.total).toFixed(2)}" r="4.5" fill="#f7f3eb" stroke="#0e6d68" stroke-width="2.5" />
          <title>${escapeHtml(`${bucket.label}: ${formatCurrency(bucket.total)}`)}</title>
        </g>
      `
    )
    .join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Billing spending chart">
      <defs>
        <linearGradient id="billingExportArea" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#0e6d68" stop-opacity="0.28" />
          <stop offset="100%" stop-color="#0e6d68" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      ${grid}
      <path d="${areaPath}" fill="url(#billingExportArea)" />
      <path d="${linePath}" fill="none" stroke="#0e6d68" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
      ${points}
      ${xLabels}
    </svg>
  `;
}

function renderExportRangeButtons() {
  exportRangeButtons.forEach((button) => {
    const isActive = button.dataset.exportRange === state.exportRange;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function renderBillingExport() {
  renderExportRangeButtons();
  if (!walletExportSummary || !walletExportChart || !walletExportEmpty) {
    return;
  }

  const buckets = buildExportSeries(state.exportRange);
  const spendTransactions = state.walletTransactions.filter(isBillingExportTransaction);
  const totalSpent = roundMoney(buckets.reduce((sum, bucket) => sum + bucket.total, 0));
  const peakBucket = buckets.reduce(
    (currentPeak, bucket) => (bucket.total > currentPeak.total ? bucket : currentPeak),
    buckets[0] || { label: "-", total: 0 }
  );
  const hasSpending = buckets.some((bucket) => bucket.total > 0);

  walletExportSummary.innerHTML = `
    <article class="profile-field">
      <span>Window</span>
      <strong>${escapeHtml(EXPORT_RANGE_LABELS[state.exportRange] || EXPORT_RANGE_LABELS.month)}</strong>
    </article>
    <article class="profile-field">
      <span>Total spent</span>
      <strong>${escapeHtml(formatCurrency(totalSpent))}</strong>
    </article>
    <article class="profile-field">
      <span>Peak period</span>
      <strong>${escapeHtml(hasSpending ? `${peakBucket.label}  ${formatCurrency(peakBucket.total)}` : "No spend yet")}</strong>
    </article>
  `;

  walletExportChart.innerHTML = buildBillingLineChartSvg(buckets);
  walletExportEmpty.classList.toggle("hidden", hasSpending);
  walletExportEmpty.textContent = hasSpending
    ? ""
    : `No event spending has been recorded in the ${String(EXPORT_RANGE_LABELS[state.exportRange] || EXPORT_RANGE_LABELS.month).toLowerCase()} view yet. The chart remains ready for the first reservation charge.`;

  if (walletExportButton) {
    walletExportButton.disabled = !state.walletTransactions.length;
  }
}

async function syncPendingStateAfterExpiry() {
  clearPendingCountdown();
  const hadPending = Boolean(state.pendingTopUp);
  try {
    await loadWallet();
  } catch {
    state.pendingTopUp = null;
    renderWallet();
  }
  if (hadPending && !state.pendingTopUp) {
    showToast("QR request expired and was cancelled.", "error");
  }
}

function startPendingCountdown() {
  clearPendingCountdown();
  if (!state.pendingTopUp) {
    return;
  }

  updateTopUpSubmitLabel();
  if (Number(state.pendingTopUp.seconds_remaining || 0) <= 0) {
    void syncPendingStateAfterExpiry();
    return;
  }

  state.pendingCountdownTimer = window.setInterval(() => {
    if (!state.pendingTopUp) {
      clearPendingCountdown();
      return;
    }

    state.pendingTopUp.seconds_remaining = Math.max(Number(state.pendingTopUp.seconds_remaining || 0) - 1, 0);
    updateTopUpSubmitLabel();
    if (state.pendingTopUp.seconds_remaining <= 0) {
      void syncPendingStateAfterExpiry();
    }
  }, 1000);
}

function renderPendingQr() {
  if (!walletQrShell || !walletQrImage || !walletQrPayload || !walletConfirmButton || !walletQrEmpty) {
    return;
  }

  if (!state.pendingTopUp) {
    clearPendingCountdown();
    walletQrEmpty.classList.remove("hidden");
    walletQrShell.classList.add("hidden");
    walletQrImage.removeAttribute("src");
    walletQrPayload.textContent = "";
    walletConfirmButton.disabled = true;
    setTopUpFormLocked(false);
    updateTopUpSubmitLabel();
    return;
  }

  state.openPanels.add("topup");
  walletQrEmpty.classList.add("hidden");
  walletQrShell.classList.remove("hidden");
  walletQrImage.src = state.pendingTopUp.qr_image_url;
  walletQrPayload.textContent = state.pendingTopUp.qr_payload;
  walletConfirmButton.disabled = false;
  setTopUpFormLocked(true);
  startPendingCountdown();
}

function renderWallet() {
  if (walletBalance) {
    walletBalance.textContent = formatCurrency(state.user?.balance || 0);
  }
  renderTransactions();
  renderBillingExport();
  renderPendingQr();
  renderBillingAccordion();
}

async function loadWallet() {
  const wallet = await api("/api/me/wallet");
  state.user = wallet.user;
  state.walletTransactions = wallet.transactions || [];
  state.pendingTopUp = wallet.pending_top_up || null;
  populateHero(state.user);
  renderWallet();
}

async function handleWalletTopUpSubmit(event) {
  event.preventDefault();
  const response = await api("/api/me/wallet/top-up", {
    method: "POST",
    body: JSON.stringify({
      amount: Number(walletTopUpAmount.value),
      provider: "QR transfer",
      note: walletTopUpNote.value.trim(),
    }),
  });
  state.pendingTopUp = response.pending_top_up;
  state.openPanels.add("topup");
  renderWallet();
  showToast(response.message || "QR request created.");
}

async function handleWalletConfirm() {
  const response = await api("/api/me/wallet/top-up/confirm", { method: "POST" });
  state.user = response.user;
  state.pendingTopUp = null;
  state.walletTransactions = [response.transaction, ...state.walletTransactions];
  state.openPanels.add("transactions");
  clearPendingCountdown();
  populateHero(state.user);
  renderWallet();
  walletTopUpForm?.reset();
  showToast(response.message || "Payment confirmed.");
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
  const csv = rows.map((row) => row.map((value) => `"${String(value ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  createDownload("billing-history.csv", csv, "text/csv;charset=utf-8");
  showToast("Billing export downloaded.");
}

walletTopUpForm?.addEventListener("submit", async (event) => {
  try {
    await handleWalletTopUpSubmit(event);
  } catch (error) {
    showToast(error.message, "error");
  }
});

walletConfirmButton?.addEventListener("click", async () => {
  try {
    await handleWalletConfirm();
  } catch (error) {
    showToast(error.message, "error");
    try {
      await loadWallet();
    } catch {
      // Keep the current UI state if the refresh fails.
    }
  }
});

walletExportButton?.addEventListener("click", exportBillingHistory);

billingToggles.forEach((toggle) => {
  toggle.addEventListener("click", () => {
    const target = toggle.dataset.billingToggle;
    if (!target) {
      return;
    }
    if (state.openPanels.has(target)) {
      state.openPanels.delete(target);
    } else {
      state.openPanels.add(target);
    }
    renderBillingAccordion();
  });
});

exportRangeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const nextRange = button.dataset.exportRange || "month";
    if (state.exportRange === nextRange) {
      return;
    }
    state.exportRange = nextRange;
    renderBillingExport();
  });
});

async function boot() {
  const user = await getCurrentUser();
  if (!user) {
    redirectTo("/");
    return;
  }

  state.user = user;
  populateHero(user);
  renderBillingAccordion();
  renderBillingExport();
  await loadWallet();
}

boot();




