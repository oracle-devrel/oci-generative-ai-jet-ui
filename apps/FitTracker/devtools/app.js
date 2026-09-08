// FitTrack API Test Page JavaScript

// API Configuration
function getApiBaseUrl() {
  return document.getElementById("apiBaseUrl").value;
}

// Tab Navigation
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    // Remove active from all tabs and content
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

    // Add active to clicked tab and its content
    tab.classList.add("active");
    const tabId = tab.getAttribute("data-tab");
    document.getElementById(tabId).classList.add("active");
  });
});

// API Request Helper
async function apiRequest(method, endpoint, data = null) {
  const startTime = performance.now();
  const url = `${getApiBaseUrl()}${endpoint}`;

  const options = {
    method: method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (data) {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(url, options);
    const endTime = performance.now();
    const duration = Math.round(endTime - startTime);

    let result;
    try {
      result = await response.json();
    } catch {
      result = { message: "No JSON response" };
    }

    displayResponse(response.status, duration, result);
    return { status: response.status, data: result };
  } catch (error) {
    const endTime = performance.now();
    const duration = Math.round(endTime - startTime);
    displayResponse("Error", duration, { error: error.message });
    return { status: "error", data: { error: error.message } };
  }
}

// Display Response
function displayResponse(status, duration, data) {
  const statusEl = document.getElementById("response-status");
  const timeEl = document.getElementById("response-time");
  const outputEl = document.getElementById("response-output");

  // Status
  statusEl.textContent = `Status: ${status}`;
  statusEl.className = status >= 200 && status < 300 ? "success" : "error";

  // Time
  timeEl.textContent = `Time: ${duration}ms`;

  // Output with syntax highlighting
  outputEl.innerHTML = syntaxHighlight(JSON.stringify(data, null, 2));
}

// JSON Syntax Highlighting
function syntaxHighlight(json) {
  json = json.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    function (match) {
      let cls = "json-number";
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = "json-key";
        } else {
          cls = "json-string";
        }
      } else if (/true|false/.test(match)) {
        cls = "json-boolean";
      } else if (/null/.test(match)) {
        cls = "json-null";
      }
      return '<span class="' + cls + '">' + match + "</span>";
    }
  );
}

// ==================== User APIs ====================

async function listUsers() {
  const page = document.getElementById("users-page").value || 1;
  const limit = document.getElementById("users-limit").value || 20;
  await apiRequest("GET", `/users?page=${page}&limit=${limit}`);
}

async function getUser() {
  const id = document.getElementById("users-get-id").value;
  if (!id) {
    alert("Please enter a User ID");
    return;
  }
  await apiRequest("GET", `/users/${id}`);
}

async function createUser() {
  const email = document.getElementById("users-email").value;
  const password = document.getElementById("users-password").value;

  if (!email || !password) {
    alert("Please enter email and password");
    return;
  }

  await apiRequest("POST", "/users", { email, password });
}

async function updateUser() {
  const id = document.getElementById("users-update-id").value;
  const status = document.getElementById("users-status").value;
  const role = document.getElementById("users-role").value;

  if (!id) {
    alert("Please enter a User ID");
    return;
  }

  const data = {};
  if (status) data.status = status;
  if (role) data.role = role;

  await apiRequest("PUT", `/users/${id}`, data);
}

async function deleteUser() {
  const id = document.getElementById("users-delete-id").value;
  if (!id) {
    alert("Please enter a User ID");
    return;
  }
  if (!confirm("Are you sure you want to delete this user?")) return;
  await apiRequest("DELETE", `/users/${id}`);
}

// ==================== Profile APIs ====================

async function listProfiles() {
  const page = document.getElementById("profiles-page").value || 1;
  const tier = document.getElementById("profiles-tier").value;
  let url = `/profiles?page=${page}`;
  if (tier) url += `&tier=${tier}`;
  await apiRequest("GET", url);
}

async function getProfileByUser() {
  const userId = document.getElementById("profiles-user-id").value;
  if (!userId) {
    alert("Please enter a User ID");
    return;
  }
  await apiRequest("GET", `/profiles/user/${userId}`);
}

// ==================== Connection APIs ====================

async function listConnections() {
  const userId = document.getElementById("connections-user-id").value;
  let url = "/connections";
  if (userId) url += `?user_id=${userId}`;
  await apiRequest("GET", url);
}

// ==================== Activity APIs ====================

async function listActivities() {
  const userId = document.getElementById("activities-user-id").value;
  const startDate = document.getElementById("activities-start").value;
  const endDate = document.getElementById("activities-end").value;

  let url = "/activities?";
  if (userId) url += `user_id=${userId}&`;
  if (startDate) url += `start_date=${startDate}&`;
  if (endDate) url += `end_date=${endDate}&`;

  await apiRequest("GET", url);
}

// ==================== Transaction APIs ====================

async function listTransactions() {
  const userId = document.getElementById("transactions-user-id").value;
  let url = "/transactions";
  if (userId) url += `?user_id=${userId}`;
  await apiRequest("GET", url);
}

// ==================== Drawing APIs ====================

async function listDrawings() {
  const status = document.getElementById("drawings-status").value;
  let url = "/drawings";
  if (status) url += `?status_filter=${status}`;
  await apiRequest("GET", url);
}

async function listOpenDrawings() {
  await apiRequest("GET", "/drawings/open");
}

// ==================== Ticket APIs ====================

async function listTickets() {
  const drawingId = document.getElementById("tickets-drawing-id").value;
  const userId = document.getElementById("tickets-user-id").value;

  let url = "/tickets?";
  if (drawingId) url += `drawing_id=${drawingId}&`;
  if (userId) url += `user_id=${userId}&`;

  await apiRequest("GET", url);
}

// ==================== Prize APIs ====================

async function listPrizes() {
  const drawingId = document.getElementById("prizes-drawing-id").value;
  let url = "/prizes";
  if (drawingId) url += `?drawing_id=${drawingId}`;
  await apiRequest("GET", url);
}

// ==================== Fulfillment APIs ====================

async function listFulfillments() {
  const status = document.getElementById("fulfillments-status").value;
  let url = "/fulfillments";
  if (status) url += `?status_filter=${status}`;
  await apiRequest("GET", url);
}

// ==================== Sponsor APIs ====================

async function listSponsors() {
  const activeOnly = document.getElementById("sponsors-active-only").checked;
  let url = "/sponsors";
  if (activeOnly) url += "?active_only=true";
  await apiRequest("GET", url);
}

async function searchSponsors() {
  const query = document.getElementById("sponsors-search").value;
  if (!query) {
    alert("Please enter a search query");
    return;
  }
  await apiRequest("GET", `/sponsors/search?q=${encodeURIComponent(query)}`);
}

// ==================== Database Management ====================

async function seedDatabase() {
  if (!confirm("This will seed the database with test data. Continue?")) return;
  await apiRequest("POST", "/devtools/seed");
}

async function resetDatabase() {
  if (!confirm("This will RESET the database. All data will be lost. Continue?")) return;
  await apiRequest("POST", "/devtools/reset");
}

// Initial check
console.log("FitTrack API Test Page loaded");
