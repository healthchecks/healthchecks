$(function () {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);

    $(".timeout-grace").click(function() {
        var code = $(this).closest("tr.checks-row").attr("id");
        if (!code) {
            code = this.dataset.code;
        }
       
        var url = base + "/checks/" + code + "/timeout/";

        $("#update-timeout-form").attr("action", url);
        $("#update-cron-form").attr("action", url);

        // Simple
        periodSlider.noUiSlider.set(this.dataset.timeout);
        graceSlider.noUiSlider.set(this.dataset.grace);

        // Cron
        currentPreviewHash = "";
        $("#cron-preview").html("<p>Updating...</p>");
        $("#schedule").val(this.dataset.schedule);
        $("#tz").selectpicker("val", this.dataset.tz);
        var minutes = parseInt(this.dataset.grace / 60);
        $("#update-timeout-grace-cron").val(minutes);
        updateCronPreview();

        this.dataset.kind == "simple" ? showSimple() : showCron();
        $('#update-timeout-modal').modal({"show":true, "backdrop":"static"});
        return false;
    });

    var MINUTE = {name: "minute", nsecs: 60};
    var HOUR = {name: "hour", nsecs: MINUTE.nsecs * 60};
    var DAY = {name: "day", nsecs: HOUR.nsecs * 24};
    var WEEK = {name: "week", nsecs: DAY.nsecs * 7};
    var UNITS = [WEEK, DAY, HOUR, MINUTE];

    var secsToText = function(total) {
        var remainingSeconds = Math.floor(total);
        var result = "";
        for (var i=0, unit; unit=UNITS[i]; i++) {
            if (unit === WEEK && remainingSeconds % unit.nsecs != 0) {
                // Say "8 days" instead of "1 week 1 day"
                continue
            }

            var count = Math.floor(remainingSeconds / unit.nsecs);
            remainingSeconds = remainingSeconds % unit.nsecs;

            if (count == 1) {
                result += "1 " + unit.name + " ";
            }

            if (count > 1) {
                result += count + " " + unit.name + "s ";
            }
        }

        return result;
    }

    var periodSlider = document.getElementById("period-slider");
    noUiSlider.create(periodSlider, {
        start: [20],
        connect: "lower",
        range: {
            'min': [60, 60],
            '33%': [3600, 3600],
            '66%': [86400, 86400],
            '83%': [604800, 604800],
            'max': 2592000,
        },
        pips: {
            mode: 'values',
            values: [60, 1800, 3600, 43200, 86400, 604800, 2592000],
            density: 4,
            format: {
                to: secsToText,
                from: function() {}
            }
        }
    });

    periodSlider.noUiSlider.on("update", function(a, b, value) {
        var rounded = Math.round(value);
        $("#period-slider-value").text(secsToText(rounded));
        $("#update-timeout-timeout").val(rounded);
    });

    var graceSlider = document.getElementById("grace-slider");
    noUiSlider.create(graceSlider, {
        start: [20],
        connect: "lower",
        range: {
            'min': [60, 60],
            '33%': [3600, 3600],
            '66%': [86400, 86400],
            '83%': [604800, 604800],
            'max': 2592000,
        },
        pips: {
            mode: 'values',
            values: [60, 1800, 3600, 43200, 86400, 604800, 2592000],
            density: 4,
            format: {
                to: secsToText,
                from: function() {}
            }
        }
    });

    graceSlider.noUiSlider.on("update", function(a, b, value) {
        var rounded = Math.round(value);
        $("#grace-slider-value").text(secsToText(rounded));
        $("#update-timeout-grace").val(rounded);
    });

    function showSimple() {
        $("#update-timeout-form").show();
        $("#update-cron-form").hide();
    }

    function showCron() {
        $("#update-timeout-form").hide();
        $("#update-cron-form").show();
    }

    var currentPreviewHash = "";
    function updateCronPreview() {
        var schedule = $("#schedule").val();
        var tz = $("#tz").val();
        var hash = schedule + tz;

        // Don't try preview with empty values, or if values have not changed
        if (!schedule || !tz || hash == currentPreviewHash)
            return;

        // OK, we're good
        currentPreviewHash = hash;
        $("#cron-preview-title").text("Updating...");

        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: base + "/checks/cron_preview/",
            type: "post",
            headers: {"X-CSRFToken": token},
            data: {schedule: schedule, tz: tz},
            success: function(data) {
                if (hash != currentPreviewHash) {
                    return;  // ignore stale results
                }

                $("#cron-preview" ).html(data);
                var haveError = $("#invalid-arguments").size() > 0;
                $("#update-cron-submit").prop("disabled", haveError);
            }
        });
    }

    // Wire up events for Timeout/Cron forms
    $(".kind-simple").click(showSimple);
    $(".kind-cron").click(showCron);

    $("#schedule").on("keyup", updateCronPreview);
    $("#tz").on("change", updateCronPreview);

});
