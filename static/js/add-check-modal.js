$(function () {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
    var modal = $("#add-check-modal");
    var timezones = document.getElementById("all-timezones").textContent;
    var period = document.getElementById("add-check-period");
    var periodUnit = document.getElementById("add-check-period-unit");
    var scheduleField = document.getElementById("add-check-schedule");
    var grace = document.getElementById("add-check-grace");
    var graceUnit = document.getElementById("add-check-grace-unit");

    function divToOption() {
        return {value: this.textContent};
    }

    $("#add-check-tags").selectize({
        create: true,
        createOnBlur: true,
        delimiter: " ",
        labelField: "value",
        searchField: ["value"],
        hideSelected: true,
        highlight: false,
        options: $("#my-checks-tags div").map(divToOption).get()
    });

    $("#add-check-tz").selectize({
        labelField: "value",
        searchField: ["value"],
        selectOnTab: true,
        options: timezones.split(",").map(tz => {return {value: tz}})
    });


    function updateScheduleExtras() {
        var kind = $('#add-check-modal input[name=kind]:checked').val();
        modal.removeClass("cron").removeClass("simple").addClass(kind);

        if (kind == "simple" && !scheduleField.checkValidity()) {
            scheduleField.setCustomValidity("");
            scheduleField.value = "* * * * *";
        }
    }

    $("#add-check-modal input[type=radio][name=kind]").change(updateScheduleExtras);

    modal.on("shown.bs.modal", function() {
        updateScheduleExtras();
        validateSchedule();
        $("#add-check-name").focus();
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
        var schedule = scheduleField.value;

        // Don't preview if the schedule has not changed
        if (schedule == currentSchedule)
            return;

        currentSchedule = schedule;
        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.getJSON(base + "/checks/validate_schedule/", {schedule: schedule}, function(data) {
            if (schedule != currentSchedule) {
                return;  // ignore stale results
            }

            scheduleField.setCustomValidity(data.result ? "" : "Please enter a valid cron expression");
        });
    }

    $("#add-check-schedule").on("keyup change", validateSchedule);

});
