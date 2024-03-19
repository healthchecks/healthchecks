$(function () {
    var slider = document.getElementById("end");

    // Look up the active tz switch to determine the initial display timezone:
    var dateFormat = $(".active", "#format-switcher").data("format");
    function fromUnix(timestamp) {
        var dt = moment.unix(timestamp);
        dateFormat == "local" ? dt.local() : dt.tz(dateFormat);
        return dt;
    }

    function updateSliderPreview() {
        var toFormatted = "now";
        if (slider.value != slider.max) {
            toFormatted = fromUnix(slider.value).format("MMM D, HH:mm");
        }
        $("#end-formatted").text(toFormatted);
    }

    $("#end").on("input", updateSliderPreview);
    $("#end").on("change", function() {
        // Don't send the end parameter if slider is set to "now"
        $("#end").attr("disabled", slider.value == slider.max);
        $("#filters").submit();
    });

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
    });

    switchDateFormat(dateFormat, document.querySelectorAll("#log tr"));
    // The table is initially hidden to avoid flickering as we convert dates.
    // Once it's ready, set it to visible:
    $("#log").css("visibility", "visible");

    function fetchNewEvents() {
        var url = document.getElementById("log").dataset.refreshUrl;
        var firstRow = $("#log tr").get(0);
        if (firstRow) {
            url += "?start=" + firstRow.dataset.dt;
        }

        $.ajax({
            url: url,
            dataType: "json",
            timeout: 2000,
            success: function(data) {
                if (data.events) {
                    var tbody = document.createElement("tbody");
                    tbody.setAttribute("class", "new");
                    tbody.innerHTML = data.events;
                    switchDateFormat(dateFormat, tbody.querySelectorAll("tr"));
                    document.getElementById("log").prepend(tbody);
                    $("#events-count").remove();
                }
            }
        });
    }

    if (slider.value == slider.max) {
        adaptiveSetInterval(fetchNewEvents, false);
    }


});
