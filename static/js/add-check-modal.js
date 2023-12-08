$(function () {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
    var modal = $("#add-check-modal");
    var period = document.getElementById("add-check-period");
    var periodUnit = document.getElementById("add-check-period-unit");
    var cronField = document.getElementById("add-check-schedule");
    var onCalendarField = document.getElementById("add-check-schedule-oncalendar");
    var grace = document.getElementById("add-check-grace");
    var graceUnit = document.getElementById("add-check-grace-unit");

    function divToOption() {
        return {value: this.textContent};
    }

    $("#add-check-tags").selectize({
        create: true,
        createOnBlur: true,
        selectOnTab: false,
        delimiter: " ",
        labelField: "value",
        searchField: ["value"],
        hideSelected: true,
        highlight: false,
        options: $("#my-checks-tags div").map(divToOption).get()
    });

    function updateScheduleExtras() {
        var kind = $('#add-check-modal input[name=kind]:checked').val();
        modal.removeClass("simple").removeClass("cron").removeClass("oncalendar").addClass(kind);
        // Include cron schedule in POST data only if kind = "cron"
        cronField.disabled = kind != "cron";
        // Include OnCalendar schedule in POST data only if kind = "oncalendar"
        onCalendarField.disabled = kind != "oncalendar";
    }

    // Show and hide fields when user clicks simple/cron/oncalendar radio buttons
    $("#add-check-modal input[type=radio][name=kind]").change(updateScheduleExtras);

    modal.on("shown.bs.modal", function() {
        updateScheduleExtras();
        validateSchedule();
        $("#add-check-tz")[0].selectize.setValue("UTC", true);
        $("#add-check-name").focus();

        // Pre-select the currently active tags
        var selectedTags = $("#my-checks-tags .checked").map(function() { return this.textContent }).get();
        $("#add-check-tags")[0].selectize.setValue(selectedTags);
    });

    // Update the hidden field when user changes period inputs
    $("#add-check-modal .period-input").on("keyup change", function() {
        var secs = Math.round(period.value * periodUnit.value);
        period.setCustomValidity(secs <= 31536000 ? "" : "Must not exceed 365 days");

        if (secs >= 60) {
            $("#add-check-modal input[name=timeout]").val(secs);
        }
    })

    // Update the hidden field when user changes grace inputs
    $("#add-check-modal .grace-input").on("keyup change", function() {
        var secs = Math.round(grace.value * graceUnit.value);
        grace.setCustomValidity(secs <= 31536000 ? "" : "Must not exceed 365 days");

        if (secs >= 60) {
            $("#add-check-modal input[name=grace]").val(secs);
        }
    });

    var currentSchedule = "";
    function validateSchedule() {
        var kind = $('#add-check-modal input[name=kind]:checked').val();
        if (kind == "simple") return;

        var field = kind == "cron" ? cronField : onCalendarField;

        // Return early if the schedule has not changed
        if (field.value == currentSchedule)
            return;

        currentSchedule = field.value;
        var token = $('input[name=csrfmiddlewaretoken]').val();
        var payload = {kind: kind, schedule: field.value};
        $.getJSON(base + "/checks/validate_schedule/", payload, function(data) {
            if (field.value != currentSchedule)
                return;  // ignore stale results

            field.setCustomValidity(data.result ? "" : "Please enter a valid expression");
        });
    }

    $("#add-check-schedule").on("keyup change", validateSchedule);
    $("#add-check-schedule-oncalendar").on("keyup change", validateSchedule);
});
