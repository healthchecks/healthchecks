$(function () {
    $("#edit-name").click(function() {
        $('#update-name-modal').modal("show");
        $("#update-name-input").focus();

        return false;
    });

    $("#new-check-alert a").click(function() {
        $("#" + this.dataset.target).click();
        return false;
    });

    $("#edit-desc").click(function() {
        $('#update-name-modal').modal("show");
        $("#update-desc-input").focus();

        return false;
    });

    $("#pause").click(function(e) {
        $("#pause-form").submit();
        return false;
    });

    $("#ping-now").click(function(e) {
        var button = this;
        $.get(this.dataset.url, function() {
            button.textContent = "Success!";
        });
    });

    $("#ping-now").mouseout(function(e) {
        setTimeout(function() {
            e.target.textContent = "Ping Now!";
        }, 300);
    });

    $("#details-integrations tr").click(function() {
        var isOn = $(this).toggleClass("on").hasClass("on");
        $(".label", this).text(isOn ? "ON" : "OFF");

        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: this.dataset.url,
            type: "post",
            headers: {"X-CSRFToken": token},
            data: {"state": isOn ? "on" : "off"}
        });
    })

    var statusUrl = document.getElementById("edit-timeout").dataset.statusUrl;
    var lastStatusText = "";
    var lastUpdated = "";
    adaptiveSetInterval(function() {
        $.ajax({
            url: statusUrl + (lastUpdated ? "?u=" + lastUpdated : ""),
            dataType: "json",
            timeout: 2000,
            success: function(data) {
                if (data.status_text != lastStatusText) {
                    lastStatusText = data.status_text;
                    $("#log-status-icon").attr("class", "status icon-" + data.status);
                    $("#log-status-text").text(data.status_text);
                }

                if (data.events) {
                    lastUpdated = data.updated;
                    $("#log-container").html(data.events);
                    switchDateFormat(lastFormat);
                }

                if (data.downtimes) {
                    $("#downtimes").html(data.downtimes);
                }

                if (document.title != data.title) {
                    document.title = data.title;
                }
            }
        });
    }, true);

    // Copy to clipboard
    var clipboard = new Clipboard('button.copy-btn');
    $("button.copy-btn").mouseout(function(e) {
        setTimeout(function() {
            e.target.textContent = e.target.dataset.label;
        }, 300);
    });

    clipboard.on('success', function(e) {
        e.trigger.textContent = "Copied!";
        e.clearSelection();
    });

    clipboard.on('error', function(e) {
        var text = e.trigger.getAttribute("data-clipboard-text");
        prompt("Press Ctrl+C to select:", text)
    });

    $("#events").on("click", "tr.ok", function() {
        $("#ping-details-body").text("Updating...");
        $('#ping-details-modal').modal("show");

        $.get(this.dataset.url, function(data) {
                $("#ping-details-body").html(data);
            }
        );

        return false;
    });

    var lastFormat = "local";
    function switchDateFormat(format) {
        lastFormat = format;
        $("#log tr").each(function(index, row) {
            var dt = moment(row.getAttribute("data-dt"));
            format == "local" ? dt.local() : dt.tz(format);

            $(".date", row).text(dt.format("MMM D"));
            $(".time", row).text(dt.format("HH:mm"));                
        })

        // The table is initially hidden to avoid flickering as we convert dates.
        // Once it's ready, set it to visible:
        $("#log").css("visibility", "visible");
    }


    $("#format-switcher").click(function(ev) {
        var format = ev.target.getAttribute("data-format");
        switchDateFormat(format);
    });


    var transferFormLoadStarted = false;
    $("#transfer-btn").on("mouseenter click", function() {
        if (transferFormLoadStarted)
            return;

        transferFormLoadStarted = true;
        $.get(this.dataset.url, function(data) {
            $("#transfer-modal" ).html(data);
            $("#target-project").selectpicker();
        });
    });

    // Enable the submit button in transfer form when user selects
    // the target project:
    $("#transfer-modal").on("change", "#target-project", function() {
        $("#transfer-confirm").prop("disabled", !this.value);
    });


});
