"use strict";

const ORDERS_URL = "/orders";

/** Shows the outcome of an action. Type is "success" or "danger". */
function showMessage(type, text) {
  const flash = document.getElementById("flash_message");
  flash.className = `alert alert-${type}`;
  flash.textContent = text;
  flash.hidden = false;
}

/** Sends a request and returns the JSON body. Throws with the service's error message. */
async function sendRequest(url, method = "GET", body = undefined) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("Could not reach the Orders service");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.message || `The request failed with status ${response.status}`);
  }
  return data;
}

/** Returns the trimmed value of a form field. */
function fieldValue(id) {
  return document.getElementById(id).value.trim();
}

/** Builds the create request. The item is included only if one of its fields is filled in. */
function buildNewOrder() {
  const customerId = fieldValue("create_customer_id");
  const productId = fieldValue("create_product_id");
  const quantity = fieldValue("create_quantity");
  const unitPrice = fieldValue("create_unit_price");

  const order = {};
  if (customerId) {
    order.customer_id = Number(customerId);
  }
  if (productId || quantity || unitPrice) {
    const item = {};
    if (productId) {
      item.product_id = Number(productId);
    }
    if (quantity) {
      item.quantity = Number(quantity);
    }
    if (unitPrice) {
      item.unit_price = unitPrice;
    }
    order.items = [item];
  }
  return order;
}

// True while a create request is waiting for the service
let createPending = false;

document.getElementById("create_form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (createPending) {
    return;
  }
  createPending = true;
  const createButton = document.getElementById("create_button");
  createButton.disabled = true;
  const createdOrder = document.getElementById("created_order");
  createdOrder.hidden = true;

  try {
    const order = await sendRequest(ORDERS_URL, "POST", buildNewOrder());
    document.getElementById("created_order_id").textContent = order.id;
    createdOrder.hidden = false;
    showMessage("success", "Order created");
  } catch (error) {
    showMessage("danger", error.message);
  } finally {
    createPending = false;
    createButton.disabled = false;
  }
});

document.getElementById("list_button").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const results = document.getElementById("list_results");
  const rows = document.getElementById("list_rows");
  button.disabled = true;
  results.hidden = true;
  rows.replaceChildren();

  try {
    const orders = await sendRequest(ORDERS_URL);
    for (const order of orders) {
      const row = rows.insertRow();
      row.insertCell().textContent = order.id;
      row.insertCell().textContent = order.status;
    }
    results.hidden = orders.length === 0;
    showMessage("success", orders.length === 0 ? "No orders found" : "Orders loaded");
  } catch (error) {
    showMessage("danger", error.message);
  } finally {
    button.disabled = false;
  }
});

/** Formats a money amount with two decimals. */
function formatMoney(amount) {
  return Number(amount).toFixed(2);
}

let selectedOrderId = null;
let orderChangePending = false;

function clearSelectedOrder() {
  selectedOrderId = null;
  document.getElementById("order_details").hidden = true;
}

/** Shows an order and its items in the lookup panel. */
function showOrderDetails(order) {
  selectedOrderId = order.id;
  document.getElementById("update_customer_id").value = order.customer_id;
  document.getElementById("update_status").value = order.status;
  document.getElementById("order_detail_id").textContent = order.id;
  document.getElementById("order_detail_customer_id").textContent = order.customer_id;
  document.getElementById("order_detail_status").textContent = order.status;
  document.getElementById("order_detail_subtotal").textContent = formatMoney(order.subtotal);

  const rows = document.getElementById("order_detail_items");
  rows.replaceChildren();
  for (const item of order.items) {
    const row = rows.insertRow();
    for (const value of [item.product_id, item.quantity, formatMoney(item.unit_price), formatMoney(item.line_total)]) {
      row.insertCell().textContent = value;
    }
  }
  document.getElementById("order_detail_no_items").hidden = order.items.length > 0;
  document.getElementById("order_details").hidden = false;
}

// True while a lookup request is waiting for the service
let lookupPending = false;

document.getElementById("lookup_form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (lookupPending || orderChangePending) {
    return;
  }
  clearSelectedOrder();

  const orderId = fieldValue("lookup_order_id");
  if (!/^\d+$/.test(orderId)) {
    showMessage("danger", "Enter an order ID to look up");
    return;
  }

  lookupPending = true;
  const lookupButton = document.getElementById("lookup_button");
  lookupButton.disabled = true;
  try {
    const order = await sendRequest(`${ORDERS_URL}/${orderId}`);
    showOrderDetails(order);
    showMessage("success", `Found order ${order.id}`);
  } catch (error) {
    showMessage("danger", error.message);
  } finally {
    lookupPending = false;
    lookupButton.disabled = false;
  }
});

/** Keeps lookup and edits from changing the selected order during a save or delete. */
async function changeSelectedOrder(action) {
  if (selectedOrderId === null || orderChangePending) {
    return;
  }

  orderChangePending = true;
  const buttons = ["lookup_button", "update_button", "delete_button"]
    .map((id) => document.getElementById(id));
  for (const button of buttons) {
    button.disabled = true;
  }
  try {
    await action(selectedOrderId);
  } catch (error) {
    showMessage("danger", error.message);
  } finally {
    orderChangePending = false;
    for (const button of buttons) {
      button.disabled = false;
    }
  }
}

document.getElementById("update_form").addEventListener("submit", (event) => {
  event.preventDefault();
  changeSelectedOrder(async (orderId) => {
    const customerId = fieldValue("update_customer_id");
    if (customerId === "") {
      showMessage("danger", "Enter a customer ID");
      return;
    }

    // Omitting items preserves the existing items on the server.
    const order = await sendRequest(`${ORDERS_URL}/${orderId}`, "PUT", {
      customer_id: Number(customerId),
      status: fieldValue("update_status"),
    });
    showOrderDetails(order);
    showMessage("success", `Order ${order.id} updated`);
  });
});

document.getElementById("delete_button").addEventListener("click", () => {
  changeSelectedOrder(async (orderId) => {
    await sendRequest(`${ORDERS_URL}/${orderId}`, "DELETE");
    clearSelectedOrder();
    showMessage("success", `Order ${orderId} deleted`);
  });
});
