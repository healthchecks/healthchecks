$(function () {
    var activeRequest = null;
    var slider = document.getElementById("end");

    // Look up the active tz switch to determine the initial display timezone:
    var dateFormat = $(".active", "#format-switcher").data("format");
    function fromUnix(timestamp) {
        var dt = moment.unix(timestamp);
        dateFormat == "local" ? dt.local() : dt.tz(dateFormat);
        return dt;
    }

    function updateSliderPreview() {
        var toFormatted = "now, live updates";
        if (slider.value != slider.max) {
            toFormatted = fromUnix(slider.value).format("MMM D, HH:mm");
        }
        $("#end-formatted").html(toFormatted);
    }

    function formatDateSpans() {
        $("span[data-dt]").each(function(i, el) {
            el.innerText = fromUnix(el.dataset.dt).format(el.dataset.fmt);
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
            success: function(data) {
                activeRequest = null;
                var tbody = document.createElement("tbody");
                tbody.innerHTML = data;
                switchDateFormat(dateFormat, tbody.querySelectorAll("tr"));
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

    function switchDateFormat(format, rows) {
        dateFormat = format;
        updateSliderPreview();

        rows.forEach(function(row) {
            var dt = fromUnix(row.dataset.dt);
            row.children[1].textContent = dt.format("MMM D");
            row.children[2].textContent = dt.format("HH:mm");
        })
    }

    $("#format-switcher").click(function(ev) {
        var format = ev.target.dataset.format;
        switchDateFormat(format, document.querySelectorAll("#log tr"));
        formatDateSpans();
    });

    switchDateFormat(dateFormat, document.querySelectorAll("#log tr"));
    formatDateSpans();
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
                switchDateFormat(dateFormat, tbody.querySelectorAll("tr"));
                document.getElementById("log").prepend(tbody);
                updateNumHits();
            }
        });
    }

    adaptiveSetInterval(fetchNewEvents, false);
});
