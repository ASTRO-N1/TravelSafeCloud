
document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("travel-search");
    var message = document.getElementById("search-message");
    var dateInput = document.getElementById("travel-date");

    // Do not allow dates earlier than today.
    var today = new Date();
    var localDate = new Date(
        today.getTime() - today.getTimezoneOffset() * 60000
    ).toISOString().slice(0, 10);

    dateInput.min = localDate;

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        var destination = document.getElementById("destination").value;
        var date = dateInput.value;
        var travelers = document.getElementById("travelers").value;

        if (!destination || !date || date < localDate) {
            message.textContent = "Please select a valid destination and travel date.";
            return;
        }

        var destinationName =
            destination.charAt(0).toUpperCase() + destination.slice(1);

        message.textContent =
            "Showing our sample " + destinationName +
            " trip for " + travelers + " traveler(s) on " + date +
            ". Online booking will be available after backend integration.";

        var section = document.getElementById("packages");
        section.scrollIntoView({ behavior: "smooth" });
    });
});
