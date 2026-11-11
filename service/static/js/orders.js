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

document.getElementById("create_form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const createdOrder = document.getElementById("created_order");
  createdOrder.hidden = true;

  try {
    const order = await sendRequest(ORDERS_URL, "POST", buildNewOrder());
    document.getElementById("created_order_id").textContent = order.id;
    createdOrder.hidden = false;
    showMessage("success", "Order created");
  } catch (error) {
    showMessage("danger", error.message);
  }
});
