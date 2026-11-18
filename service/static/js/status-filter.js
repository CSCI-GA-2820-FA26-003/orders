"use strict";

(() => {
  const form = document.getElementById("status_filter_form");
  const statusSelect = document.getElementById("filter_status");
  const filterButton = document.getElementById("filter_button");
  const clearButton = document.getElementById("clear_status_filter");
  const results = document.getElementById("order_results");
  const table = document.getElementById("orders_table");
  const rows = document.getElementById("filtered_orders");
  const message = document.getElementById("status_filter_message");

  /** Fetches the selected status, or omits the parameter to restore the full list. */
  async function loadOrders() {
    const parameters = new URLSearchParams();
    if (statusSelect.value) {
      parameters.set("status", statusSelect.value);
    }
    const query = parameters.toString();
    const url = query ? `${ORDERS_URL}?${query}` : ORDERS_URL;

    // Lock the controls while loading so an older response cannot replace a newer search.
    [statusSelect, filterButton, clearButton].forEach((control) => { control.disabled = true; });
    results.setAttribute("aria-busy", "true");
    rows.replaceChildren();
    table.hidden = true;
    message.className = "alert alert-info";
    message.textContent = "Loading orders...";

    try {
      const orders = await sendRequest(url);
      if (!Array.isArray(orders)) {
        throw new Error("The Orders service returned an invalid response");
      }
      const fragment = document.createDocumentFragment();
      orders.forEach((order) => {
        const row = document.createElement("tr");
        const values = [
          order.id,
          order.customer_id,
          order.status === "NEW" ? "Pending (NEW)" : order.status,
          Number(order.subtotal).toFixed(2),
        ];
        values.forEach((value, index) => {
          const cell = document.createElement("td");
          cell.textContent = value;
          if (index === 0) {
            cell.className = "order-id";
          }
          row.appendChild(cell);
        });
        fragment.appendChild(row);
      });
      rows.appendChild(fragment);
      table.hidden = orders.length === 0;
      message.className = "alert alert-info";
      message.textContent = orders.length === 0
        ? "No orders found."
        : `${orders.length} order${orders.length === 1 ? "" : "s"} found.`;
    } catch (error) {
      message.className = "alert alert-danger";
      message.textContent = error.message;
    } finally {
      results.setAttribute("aria-busy", "false");
      [statusSelect, filterButton, clearButton].forEach((control) => { control.disabled = false; });
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    loadOrders();
  });

  clearButton.addEventListener("click", () => {
    statusSelect.value = "";
    loadOrders();
  });

  loadOrders();
})();
