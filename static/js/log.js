$(function () {
    var BIG_LABEL = 1;
    var SMALL_LABEL = 2;
    var PIP = 0;
    var NO_PIP = -1;

    var slider = document.getElementById("log-slider");
    var smin = parseInt(slider.dataset.min);
    var smax = parseInt(slider.dataset.max);
    var pixelsPerSecond = slider.clientWidth / (smax - smin);
    var pixelsPerHour = pixelsPerSecond * 3600;
    var pixelsPerDay = pixelsPerHour * 24;
    var dayGap = Math.round(0.5 + 80 / pixelsPerDay);

    var dateFormat = "local";
    function fromUnix(timestamp) {
        var dt = moment.unix(timestamp);
        dateFormat == "local" ? dt.local() : dt.tz(dateFormat);
        return dt;
    }

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

    function updateSliderPreview() {
        var values = slider.noUiSlider.get();
        $("#slider-from-formatted").text(fromUnix(values[0]).format("MMMM D, HH:mm"));
        $("#slider-to-formatted").text(fromUnix(values[1]).format("MMMM D, HH:mm"));
    }

    updateSliderPreview();
    slider.noUiSlider.on("slide", updateSliderPreview);

    slider.noUiSlider.on("change", function(a, b, value) {
        $("#seek-start").val(Math.round(value[0]));
        $("#seek-end").val(Math.round(value[1]));
        $("#seek-form").submit();
    });

    $("#log tr.ok").on("click", function() {
        var n = $("td", this).first().text();
        var tmpl = $("#log").data("url").slice(0, -2);
        loadPingDetails(tmpl + n + "/");
        return false;
    });

    function switchDateFormat(format) {
        dateFormat = format;
        slider.noUiSlider.updateOptions({}, true);
        updateSliderPreview();

        document.querySelectorAll("#log tr").forEach(function(row) {
            var dt = fromUnix(row.dataset.dt);
            row.children[1].textContent = dt.format("MMM D");
            row.children[2].textContent = dt.format("HH:mm");
        })
    }

    $("#format-switcher").click(function(ev) {
        var format = ev.target.dataset.format;
        switchDateFormat(format);
    });

    switchDateFormat("local");
    // The table is initially hidden to avoid flickering as we convert dates.
    // Once it's ready, set it to visible:
    $("#log").css("visibility", "visible");
});
