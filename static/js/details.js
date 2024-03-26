$(function () {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
    var favicon = document.querySelector('link[rel="icon"]');

    $("#edit-name").click(function() {
        $('#update-name-modal').modal("show");
        $("#update-name-input").focus();

        return false;
    });

    // Configure Selectize for entering tags
    function toOption(tag) {
        return {value: tag}
    }

    // Use attr() instead of data() here, as data() converts attribute's string value
    // to a JS object, but we need an unconverted string:
    var allTags = $("#update-tags-input").attr("data-all-tags");
    var options = allTags ? allTags.split(" ").map(toOption) : [];
    $("#update-tags-input").selectize({
        create: true,
        createOnBlur: true,
        selectOnTab: false,
        delimiter: " ",
        labelField: "value",
        searchField: ["value"],
        hideSelected: true,
        highlight: false,
        options: options
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

    $("#current-status-text").on("click", "#resume-btn", function() {
        $("#resume-form").submit();
        return false;
    });

    $("#pause").click(function(e) {
        $("#pause-form").submit();
        return false;
    });

    $("#ping-now").click(function(e) {
        var button = this;
        $.post(this.dataset.url, function() {
            button.textContent = "Success!";
        });
    });

    $("#ping-now").mouseout(function(e) {
        setTimeout(function() {
            e.target.textContent = "Ping Now!";
        }, 300);
    });

    $(".details-integrations.rw tr").click(function() {
        var isOn = $(this).toggleClass("on").hasClass("on");
        $(".label", this).text(isOn ? "ON" : "OFF");

        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: this.dataset.url,
            type: "post",
            headers: {"X-CSRFToken": token},
            data: {"state": isOn ? "on" : "off"}
        });
    });

    var statusUrl = document.getElementById("events").dataset.statusUrl;
    // Look up the active tz switch to determine the initial display timezone:
    var lastFormat = $(".active", "#format-switcher").data("format");
    var lastStatusText = "";
    var lastUpdated = "";
    var lastStarted = false;
    adaptiveSetInterval(function() {
        $.ajax({
            url: statusUrl + (lastUpdated ? "?u=" + lastUpdated : ""),
            dataType: "json",
            timeout: 2000,
            success: function(data) {
                if (data.status_text != lastStatusText) {
                    lastStatusText = data.status_text;
                    $("#current-status-icon").attr("class", "status ic-" + data.status);
                    $("#current-status-text").html(data.status_text);

                    $('#pause-btn').prop('disabled', data.status == "paused");
                }

                if (data.started != lastStarted) {
                    lastStarted = data.started;
                    $("#current-status-spinner").toggleClass("started", data.started);
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
                    var downPostfix = data.status == "down" ? "_down" : "";
                    favicon.href = `${base}/static/img/favicon${downPostfix}.svg`;
                }
            }
        });
    }, true);

    // Copy to clipboard
    $("button.copy-btn")
        .click(function() {
            navigator.clipboard.writeText(this.dataset.clipboardText);
            this.textContent = "Copied!";
        })
        .mouseout(function(e) {
            setTimeout(function() {
                e.target.textContent = e.target.dataset.label;
            }, 300);
        });

    $("#events").on("click", "tr.ok", function() {
        var n = $("td", this).first().text();
        var tmpl = $("#log").data("url").slice(0, -2);
        loadPingDetails(tmpl + n + "/");
        return false;
    });

    function switchDateFormat(format) {
        lastFormat = format;

        document.querySelectorAll("#log tr").forEach(function(row) {
            var dt = moment.unix(row.dataset.dt).utc();
            format == "local" ? dt.local() : dt.tz(format);

            row.children[1].textContent = dt.format("MMM D");
            row.children[2].textContent = dt.format("HH:mm");
        })

        // The table is initially hidden to avoid flickering as we convert dates.
        // Once it's ready, set it to visible:
        $("#log").css("visibility", "visible");
    }


    $("#format-switcher").click(function(ev) {
        var format = ev.target.dataset.format;
        switchDateFormat(format);
    });

    var transferFormLoadStarted = false;
    $("#transfer-btn").on("mouseenter click", function() {
        if (transferFormLoadStarted)
            return;

        transferFormLoadStarted = true;
        $.get(this.dataset.url, function(data) {
            $("#transfer-modal" ).html(data);
        });
    });

    // Enable the submit button in transfer form when user selects
    // the target project:
    $("#transfer-modal").on("change", "#target-project", function() {
        $("#transfer-confirm").prop("disabled", !this.value);
    });


    // Enable/disable fields in the "Filtering Rules" modal
    $("input.filter-toggle").on("change", function() {
        var enableInputs = $("input.filter-toggle:checked").length > 0;
        $(".filter-kw").prop("disabled", !enableInputs);
    });

    // If the URL hash is #ping-<number>,  open the "Ping Details" dialog
    if (document.location.hash.indexOf("#ping-") === 0) {
        var n = parseInt(document.location.hash.substr(6));
        loadPingDetails(`../pings/${n}/`);
    }

});
