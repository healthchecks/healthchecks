// Global variable to store the current time display preference
let showAbsoluteTime = false;
let lastPingDetailsUrl = ""; // store the last used URL globally


function loadPingDetails(url) {
    lastPingDetailsUrl =url;
    $("#ping-details-body").html("<div class='loading'><div class='spinner'><div></div><div></div><div></div></div></div>");
    $('#ping-details-modal').modal("show");
    $("#ping-details-body .spinner").addClass("started");

    $.get(url, function(data) {
        $("#ping-details-body").html(data);

        // Handle the time format change based on user preference
        $("#ping-details-body .times span").each(function(i, el) {
            const format = el.dataset.format || "UTC";  // Default to UTC if undefined
            const timestamp = $("#ping-details-body .times").data("dt");

            // Safety check for timestamp
            if (!timestamp) {
                el.innerText = "No timestamp found";
                return;
            }

            let created = moment.unix(timestamp);
            let formattedTime = "";

            // Show either relative or absolute time based on preference
            if (showAbsoluteTime) {
                formattedTime = created.format("YYYY-MM-DD HH:mm:ss");
            } else {
                if (format === "local") {
                    formattedTime = created.local().fromNow();
                } else if (moment.tz.zone(format)) {
                    formattedTime = created.tz(format).fromNow();
                } else if (format === "UTC") {
                    formattedTime = created.utc().fromNow();
                } else {
                    formattedTime = "Invalid format: " + format;
                }
            }

            el.innerText = formattedTime;

            // Add title with absolute time for hover effect
            const absoluteTime = created.format("YYYY-MM-DD HH:mm:ss");
            el.setAttribute("title", absoluteTime);
        });

        var htmlPre = $("#email-body-html pre");
        if (htmlPre.length) {
            var opts = { USE_PROFILES: { html: true } };
            var clean = DOMPurify.sanitize(htmlPre.text(), opts);
            var blob = new Blob([clean], { type: "text/html; charset=utf-8" });

            var iframe = document.createElement("iframe");
            iframe.sandbox = "";
            iframe.src = URL.createObjectURL(blob);

            htmlPre.replaceWith(iframe);
        }
    });

    formatBrowserTime();
}

// Function to format browser-specific time differences
function formatBrowserTime() {
    const elements = document.querySelectorAll(".browser-timezone");

    elements.forEach((element) => {
        const timestamp = element.getAttribute("data-timestamp");
        if (!timestamp) return;

        const pingTime = new Date(timestamp);
        const now = new Date();

        const diffInSeconds = Math.floor((now - pingTime) / 1000);
        const relativeTime = formatRelativeTime(diffInSeconds);
        element.textContent = relativeTime;

        const absoluteTime = pingTime.toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
        });
        element.setAttribute("title", absoluteTime);
    });
}

// Function to format relative time
function formatRelativeTime(diffInSeconds) {
    if (diffInSeconds < 60) {
        return `${diffInSeconds}s ago`;
    } else if (diffInSeconds < 3600) {
        return `${Math.floor(diffInSeconds / 60)}m ago`;
    } else if (diffInSeconds < 86400) {
        return `${Math.floor(diffInSeconds / 3600)}h ago`;
    } else if (diffInSeconds < 2592000) {
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    } else if (diffInSeconds < 31536000) {
        return `${Math.floor(diffInSeconds / 2592000)}mo ago`;
    } else {
        return `${Math.floor(diffInSeconds / 31536000)}y ago`;
    }
}

// Toggle between relative and absolute time display
function toggleTimeFormat() {
    showAbsoluteTime = !showAbsoluteTime;
    loadPingDetails(lastPingDetailsUrl ); // Reload the data to update the time format
}
