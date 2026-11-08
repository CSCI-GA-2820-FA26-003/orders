"use strict";

const element = (id) => document.getElementById(id);
const ordersUrl = document.body.dataset.ordersUrl;
let selectedOrder = null;
let busy = false;

function message(text, isError = false) {
  element("message").textContent = text;
  element("message").dataset.error = String(isError);
}

function updateButtons() {
  document.querySelectorAll("button").forEach((button) => { button.disabled = busy; });
  element("save-button").disabled = busy || !selectedOrder;
  document.querySelector("main").setAttribute("aria-busy", String(busy));
}

async function perform(action) {
  if (busy) return;
  busy = true;
  updateButtons();
  message("");
  try {
    await action();
  } catch (error) {
    message(error.message, true);
  } finally {
    busy = false;
    updateButtons();
  }
}

async function request(url, method = "GET", data) {
  const options = { method };
  if (data !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(data);
  }
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("Cannot reach the Orders service. Please try again.");
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `Request failed (${response.status}). Please try again.`);
  }
  return response.status === 204 ? null : response.json();
}

function appendRow(body, values) {
  const row = document.createElement("tr");
  values.forEach((value) => {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
  });
  body.appendChild(row);
}

function showOrder(order) {
  selectedOrder = order;
  element("order-details").hidden = !order;
  element("selection-hint").hidden = Boolean(order);
  const fields = ["id", "customer_id", "status", "subtotal", "created_at", "updated_at"];
  fields.forEach((field) => {
    element(`selected-${field.replaceAll("_", "-")}`).textContent = order ? order[field] : "";
  });
  element("selected-items").replaceChildren();
  element("edit-customer-id").value = order ? order.customer_id : "";
  element("edit-status").value = order ? order.status : "NEW";
  element("no-items").hidden = !order || order.items.length > 0;
  if (order) {
    order.items.forEach((item) => appendRow(element("selected-items"),
      [item.id, item.product_id, item.quantity, item.unit_price, item.line_total]));
  }
  updateButtons();
}

element("create-form").addEventListener("submit", (event) => {
  event.preventDefault();
  perform(async () => {
    const data = {
      customer_id: Number(element("create-customer-id").value),
      status: element("create-status").value,
    };
    const itemFields = ["product-id", "quantity", "unit-price"].map((id) => element(`create-${id}`).value);
    if (itemFields.some((value) => value !== "")) {
      if (itemFields.some((value) => value === "")) throw new Error("Fill all three item fields, or leave all empty.");
      data.items = [{ product_id: Number(itemFields[0]), quantity: Number(itemFields[1]), unit_price: itemFields[2] }];
    }
    const order = await request(ordersUrl, "POST", data);
    showOrder(order);
    element("lookup-id").value = order.id;
    message(`Order #${order.id} created.`);
  });
});

element("lookup-form").addEventListener("submit", (event) => {
  event.preventDefault();
  perform(async () => {
    const id = element("lookup-id").value;
    showOrder(null);
    const order = await request(`${ordersUrl}/${encodeURIComponent(id)}`);
    showOrder(order);
    message(`Order #${order.id} loaded.`);
  });
});

element("edit-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!selectedOrder) return;
  perform(async () => {
    // Only editable fields are sent: omitting items preserves them on the server.
    const order = await request(`${ordersUrl}/${selectedOrder.id}`, "PUT", {
      customer_id: Number(element("edit-customer-id").value),
      status: element("edit-status").value,
    });
    showOrder(order);
    message(`Order #${order.id} saved.`);
  });
});
