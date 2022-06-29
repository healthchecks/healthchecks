$(function () {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
    var period = document.getElementById("period-value");
    var periodUnit = document.getElementById("period-unit");
    var grace = document.getElementById("grace-value");
    var graceUnit = document.getElementById("grace-unit");

    $(".rw .timeout-grace").click(function() {
        var code = $(this).closest("tr.checks-row").attr("id");
        if (!code) {
            code = this.dataset.code;
        }

        var url = base + "/checks/" + code + "/timeout/";

        $("#update-timeout-form").attr("action", url);
        $("#update-cron-form").attr("action", url);

        // Simple, period
        var parsed = secsToUnits(this.dataset.timeout);
        period.value = parsed.value;
        periodUnit.value = parsed.unit;
        periodSlider.noUiSlider.set(this.dataset.timeout);
        $("#update-timeout-timeout").val(this.dataset.timeout);

        // Simple, grace
        var parsed = secsToUnits(this.dataset.grace);
        grace.value = parsed.value;
        graceUnit.value = parsed.unit;
        graceSlider.noUiSlider.set(this.dataset.grace);
        $("#update-timeout-grace").val(this.dataset.grace);

        // Cron
        currentPreviewHash = "";
        $("#cron-preview").html("<p>Updating...</p>");
        $("#schedule").val(this.dataset.schedule);
        $("#tz")[0].selectize.setValue(this.dataset.tz, true);
        var minutes = parseInt(this.dataset.grace / 60);
        $("#update-timeout-grace-cron").val(minutes);
        updateCronPreview();

        this.dataset.kind == "simple" ? showSimple() : showCron();
        $('#update-timeout-modal').modal({"show":true, "backdrop":"static"});
        return false;
    });

    var secsToUnits = function(secs) {
        if (secs % 86400 == 0) {
            return {value: secs / 86400, unit: 86400}
        }
        if (secs % 3600 == 0) {
            return {value: secs / 3600, unit: 3600}
        }

        return {value: Math.round(secs / 60), unit: 60}
    }

    var pipLabels = {
        60: "1 minute",
        1800: "30 minutes",
        3600: "1 hour",
        43200: "12 hours",
        86400: "1 day",
        604800: "1 week",
        2592000: "30 days",
        31536000: "365 days"
    }

    var periodSlider = document.getElementById("period-slider");
    noUiSlider.create(periodSlider, {
        start: [20],
        connect: "lower",
        range: {
            'min': [60, 60],
            '30%': [3600, 3600],
            '60%': [86400, 86400],
            '75%': [604800, 86400],
            '90%': [2592000, 2592000],
            'max': 31536000
        },
        pips: {
            mode: 'values',
            values: [60, 1800, 3600, 43200, 86400, 604800, 2592000, 31536000],
            density: 4,
            format: {
                to: function(v) { return pipLabels[v] },
                from: function() {}
            }
        }
    });

    // Update inputs and the hidden field when user slides the period slider
    periodSlider.noUiSlider.on("slide", function(a, b, value) {
        var rounded = Math.round(value);
        $("#update-timeout-timeout").val(rounded);

        var parsed = secsToUnits(rounded);
        period.value = parsed.value;
        periodUnit.value = parsed.unit;
    });

    // Update the slider and the hidden field when user changes period inputs
    $("#update-timeout-modal .period-input").on("keyup change", function() {
        var secs = Math.round(period.value * periodUnit.value);
        period.setCustomValidity(secs <= 31536000 ? "" : "Must not exceed 365 days");

        if (secs >= 60) {
            periodSlider.noUiSlider.set(secs);
            $("#update-timeout-timeout").val(secs);
        }
    })

    var graceSlider = document.getElementById("grace-slider");
    noUiSlider.create(graceSlider, {
        start: [20],
        connect: "lower",
        range: {
            'min': [60, 60],
            '30%': [3600, 3600],
            '60%': [86400, 86400],
            '75%': [604800, 86400],
            '90%': [2592000, 2592000],
            'max': 31536000
        },
        pips: {
            mode: 'values',
            values: [60, 1800, 3600, 43200, 86400, 604800, 2592000, 31536000],
            density: 4,
            format: {
                to: function(v) { return pipLabels[v] },
                from: function() {}
            }
        }
    });

    // Update inputs and the hidden field when user slides the grace slider
    graceSlider.noUiSlider.on("slide", function(a, b, value) {
        var rounded = Math.round(value);
        $("#update-timeout-grace").val(rounded);

        var parsed = secsToUnits(rounded);
        grace.value = parsed.value;
        graceUnit.value = parsed.unit;
    });

    // Update the slider and the hidden field when user changes grace inputs
    $("#update-timeout-modal .grace-input").on("keyup change", function() {
        var secs = Math.round(grace.value * graceUnit.value);
        grace.setCustomValidity(secs <= 31536000 ? "" : "Must not exceed 365 days");

        if (secs >= 60) {
            graceSlider.noUiSlider.set(secs);
            $("#update-timeout-grace").val(secs);
        }
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
                var haveError = $("#invalid-arguments").length > 0;
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
