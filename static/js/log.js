$(function () {
    var activeRequest = null;
    var slider = document.getElementById("end");

    // Look up the active tz switch to determine the initial display timezone:
    var initialTz = $(".active", "#format-switcher").data("format");
    var dateFormatter = new DateFormatter(initialTz);

    function updateSliderPreview() {
        var toFormatted = "now, live updates";
        if (slider.value != slider.max) {
            var dt = new Date(slider.value * 1000);
            toFormatted = dateFormatter.formatDateTime(dt);
        }
        $("#end-formatted").html(toFormatted);
    }

    function formatDateSpans() {
        $("span[data-dt]").each(function(i, el) {
            var dt = new Date(el.dataset.dt * 1000);
            el.innerText = dateFormatter.formatDate(dt, true);
        });
    }

    function updateNumHits() {
        $("#num-hits").text($("#log tr").length);
    }

    function applyFilters() {
        var url = document.getElementById("log").dataset.refreshUrl;
        $("#end").attr("disabled", slider.value == slider.max);
        var qs = $("#filters").serialize();
        $("#end").attr("disabled", false);

        if (activeRequest) {
            // Abort the previous in-flight request so we don't display stale
            // data later
            activeRequest.abort();
        }
        activeRequest = $.ajax({
            url: url + "?" + qs,
            timeout: 2000,
            success: function(data, textStatus, xhr) {
                activeRequest = null;
                lastUpdated = xhr.getResponseHeader("X-Last-Event-Timestamp");
                var tbody = document.createElement("tbody");
                tbody.innerHTML = data;
                formatPingDates(tbody.querySelectorAll("tr"));
                $("#log").empty().append(tbody);
                updateNumHits();
            }
        });
    }

    $("#end").on("input", updateSliderPreview);
    $("#end").on("change", applyFilters);
    $("#filters input:checkbox").on("change", applyFilters);

    $("#log").on("click", "tr.ok", function() {
        var n = $("td", this).first().text();
        var tmpl = $("#log").data("url").slice(0, -2);
        loadPingDetails(tmpl + n + "/");
        return false;
    });

    function formatPingDates(rows) {
        rows.forEach(function(row) {
            var dt = new Date(row.dataset.dt * 1000);
            row.children[1].textContent = dateFormatter.formatDate(dt);
            row.children[2].textContent = dateFormatter.formatTime(dt);
        })
    }

    $("#format-switcher").click(function(ev) {
        dateFormatter.setTimezone(ev.target.dataset.format);
        updateSliderPreview();
        formatDateSpans();
        formatPingDates(document.querySelectorAll("#log tr"));
    });

    updateSliderPreview();
    formatDateSpans();
    formatPingDates(document.querySelectorAll("#log tr"));
    // The table is initially hidden to avoid flickering as we convert dates.
    // Once it's ready, set it to visible:
    $("#log").css("visibility", "visible");

    var lastUpdated = document.getElementById("last-event-timestamp").textContent;
    function fetchNewEvents() {
        // Do not fetch updates if the slider is not set to "now"
        // or there's an AJAX request in flight
        if (slider.value != slider.max || activeRequest) {
            return;
        }

        var url = document.getElementById("log").dataset.refreshUrl;
        var qs = $("#filters").serialize();

        if (lastUpdated) {
            qs += "&u=" + lastUpdated;
        }

        activeRequest = $.ajax({
            url: url + "?" + qs,
            timeout: 2000,
            success: function(data, textStatus, xhr) {
                activeRequest = null;
                if (!data)
                    return;

                lastUpdated = xhr.getResponseHeader("X-Last-Event-Timestamp");
                var tbody = document.createElement("tbody");
                tbody.setAttribute("class", "new");
                tbody.innerHTML = data;
                formatPingDates(dateFormat, tbody.querySelectorAll("tr"));
                document.getElementById("log").prepend(tbody);
                updateNumHits();
            },
            error: function(data, textStatus, xhr) {
                activeRequest = null;
            }
        });
    }

    adaptiveSetInterval(fetchNewEvents, false);
});
