



"use strict";

console.log("TravelSafe Cloud Customer Management loaded");

document.addEventListener("DOMContentLoaded", function () {

    const addButton = document.getElementById("add-customer-btn");
    const cancelButton = document.getElementById("cancel-customer-btn");
    const panel = document.getElementById("customer-form-panel");
    const form = document.getElementById("customer-form");
    const tableBody = document.getElementById("customer-table-body");
    const search = document.getElementById("customer-search");

    let customers = [];

    if (!addButton || !cancelButton || !panel ||
        !form || !tableBody || !search) {
        console.error("Customer dashboard elements are missing.");
        return;
    }

    // Open form
    addButton.addEventListener("click", function () {
        panel.hidden = false;
        panel.scrollIntoView({ behavior: "smooth" });
    });

    // Close form
    cancelButton.addEventListener("click", function () {
        panel.hidden = true;
        form.reset();
    });

    // Render customer table
    function renderCustomers() {
        const query = search.value.toLowerCase().trim();

        tableBody.textContent = "";

        const filtered = customers.filter(function (customer) {
            return [
                customer.full_name,
                customer.email,
                customer.phone,
                customer.preferred_destination,
                customer.travel_type
            ].some(function (value) {
                return String(value || "")
                    .toLowerCase()
                    .includes(query);
            });
        });

        if (filtered.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 5;
            cell.className = "empty-state";
            cell.textContent = "No matching customers found.";

            row.appendChild(cell);
            tableBody.appendChild(row);
            return;
        }

        filtered.forEach(function (customer) {
            const row = document.createElement("tr");

            [
                "full_name",
                "email",
                "phone",
                "preferred_destination",
                "travel_type"
            ].forEach(function (key) {
                const cell = document.createElement("td");
                cell.textContent = customer[key] || "";
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    // Load customers from Supabase through Flask
    function loadCustomers() {
        return fetch("/api/customers", {
            method: "GET",
            credentials: "same-origin",
            cache: "no-store"
        })
        .then(function (response) {
            if (!response.ok) {
                throw new Error(
                    "Customer loading failed: HTTP " + response.status
                );
            }
            return response.json();
        })
        .then(function (result) {
            if (!result.success || !Array.isArray(result.customers)) {
                throw new Error("Invalid customer API response");
            }

            customers = result.customers;
            renderCustomers();

            const totalCard = document.querySelector(
                ".customer-stats .stat-card h2"
            );

            if (totalCard) {
                totalCard.textContent = customers.length;
            }

            console.log("Customers loaded successfully");
        })
        .catch(function (error) {
            console.error("Customer load error:", error);

            tableBody.textContent = "";

            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 5;
            cell.className = "empty-state";
            cell.textContent =
                "Unable to load customers from cloud database.";

            row.appendChild(cell);
            tableBody.appendChild(row);
        });
    }

    // Save new customer
    form.addEventListener("submit", function (event) {
        event.preventDefault();

        const customerData = {
            full_name: document.getElementById("full-name").value.trim(),
            email: document.getElementById("email").value.trim(),
            phone: document.getElementById("phone").value.trim(),
            preferred_destination:
                document.getElementById("preferred-destination").value,
            travel_type:
                document.getElementById("travel-type").value
        };

        const csrfMeta = document.querySelector(
            'meta[name="csrf-token"]'
        );

        if (!csrfMeta || !csrfMeta.content) {
            alert(
                "Security token missing. Refresh the page and log in again."
            );
            return;
        }

        const submitButton = form.querySelector(
            'button[type="submit"]'
        );

        submitButton.disabled = true;
        submitButton.textContent = "Saving...";

        fetch("/api/customers", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfMeta.content
            },
            body: JSON.stringify(customerData)
        })
        .then(function (response) {
            return response.json().then(function (result) {
                if (!response.ok || !result.success) {
                    throw new Error(
                        result.error ||
                        "Cloud save failed: HTTP " + response.status
                    );
                }
                return result;
            });
        })
        .then(function () {
            alert("Customer saved successfully to Supabase Cloud!");

            form.reset();
            panel.hidden = true;
            search.value = "";

            return loadCustomers();
        })
        .catch(function (error) {
            console.error("Customer save error:", error);
            alert("Cloud save failed: " + error.message);
        })
        .then(function () {
            submitButton.disabled = false;
            submitButton.textContent = "Save to Cloud";
        });
    });

    // Search customers
    search.addEventListener("input", renderCustomers);

    // Initial customer loading
    loadCustomers();
});
