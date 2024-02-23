$(function () {
    var BIG_LABEL = 1;
    var SMALL_LABEL = 2;
    var PIP = 0;
    var NO_PIP = -1;

    var slider = document.getElementById("log-slider");

    // Look up the active tz switch to determine the initial display timezone:
    var dateFormat = $(".active", "#format-switcher").data("format");
    function fromUnix(timestamp) {
        var dt = moment.unix(timestamp);
        dateFormat == "local" ? dt.local() : dt.tz(dateFormat);
        return dt;
    }

    function updateSliderPreview() {
        var values = slider.noUiSlider.get();
        $("#slider-from-formatted").text(fromUnix(values[0]).format("MMMM D, HH:mm"));

        var toFormatted = "now";
        if (values[1] < parseInt(slider.dataset.max)) {
            toFormatted = fromUnix(values[1]).format("MMMM D, HH:mm");
        }

        $("#slider-to-formatted").text(toFormatted);
    }

    function setupSlider() {
        var smin = parseInt(slider.dataset.min);
        var smax = parseInt(slider.dataset.max);
        var pixelsPerSecond = slider.clientWidth / (smax - smin);
        var pixelsPerHour = pixelsPerSecond * 3600;
        var pixelsPerDay = pixelsPerHour * 24;
        var dayGap = Math.round(0.5 + 80 / pixelsPerDay);

        function filterPips(value, type) {
            var m = fromUnix(value);
            if (m.minute() != 0)
                return NO_PIP;

            // Date labels on every day
            if (pixelsPerDay > 60 && m.hour() == 0)
                return BIG_LABEL;

            // Date labels every "dayGap" days
            if (m.hour() == 0 && m.dayOfYear() % dayGap == 0)
                return BIG_LABEL;

            // Hour labels on every hour:
            if (pixelsPerHour > 40)
                return SMALL_LABEL;

            // Hour labels every 3 hours:
            if (pixelsPerHour > 15 && m.hour() % 3 == 0)
                return SMALL_LABEL;

            // Hour labels every 6 hours:
            if (pixelsPerHour > 5 && m.hour() % 6 == 0)
                return SMALL_LABEL;

            // Pip on every hour
            if (pixelsPerHour > 5)
                return PIP;

            // Pip on every day
            if (pixelsPerDay > 10 && m.hour() == 0)
                return PIP;

            return NO_PIP;
        }

        function fmt(ts) {
            var pipType = filterPips(ts);
            return fromUnix(ts).format(pipType == 2 ? "HH:mm" : "MMM D");
        }

        if (slider.noUiSlider) {
            slider.noUiSlider.destroy();
        }
        noUiSlider.create(slider, {
            start: [parseInt(slider.dataset.start), parseInt(slider.dataset.end)],
            range: {'min': smin, 'max': smax},
            connect: true,
            step: 3600,
            pips: {
                mode: "steps",
                density: 3,
                filter: filterPips,
                format: {
                    to: fmt,
                    from: function() {}
                }
            }
        });

        slider.noUiSlider.on("slide", updateSliderPreview);
        slider.noUiSlider.on("change", function(a, b, value) {
            var start = Math.round(value[0]);
            $("#seek-start").val(start).attr("disabled", start == smin);
            var end = Math.round(value[1]);
            $("#seek-end").val(end).attr("disabled", end == smax);
            $("#seek-form").submit();
        });
    }

    setupSlider();
    updateSliderPreview();

    $("#log").on("click", "tr.ok", function() {
        var n = $("td", this).first().text();
        var tmpl = $("#log").data("url").slice(0, -2);
        loadPingDetails(tmpl + n + "/");
        return false;
    });

    function switchDateFormat(format, rows) {
        dateFormat = format;
        slider.noUiSlider.updateOptions({}, true);
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
                // Has a minute has passed since last slider refresh?
                if (data.max - slider.dataset.max > 60) {
                    // If the right handle was all the way to the right,
                    // make sure it is still all the way to the right after
                    // the update:
                    if (slider.dataset.end == slider.dataset.max) {
                        slider.dataset.end = data.max;
                    }
                    slider.dataset.max = data.max;
                    setupSlider();
                }

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

    if (slider.dataset.end == slider.dataset.max) {
        adaptiveSetInterval(fetchNewEvents, false);
    }

});
