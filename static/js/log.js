$(function () {
    $("#log tr.ok").on("click", function() {
        $("#ping-details-body").text("Updating...");
        $('#ping-details-modal').modal("show");

        $.get(this.dataset.url, function(data) {
            $("#ping-details-body").html(data);

            var htmlPre = $("#email-body-html pre");
            if (htmlPre.length) {
                var opts = {USE_PROFILES: {html: true}};
                var clean = DOMPurify.sanitize(htmlPre.text(), opts);
                var blob = new Blob([clean], {type: "text/html"});

                htmlPre.remove();
                document.getElementById("email-body-html-iframe").src = URL.createObjectURL(blob);
            }
        });

        return false;
    });

    function switchDateFormat(format) {
        $("#log tr").each(function(index, row) {
            var dt = moment(row.getAttribute("data-dt"));
            format == "local" ? dt.local() : dt.tz(format);

            $(".date", row).text(dt.format("MMM D"));
            $(".time", row).text(dt.format("HH:mm"));
        })
    }

    $("#format-switcher").click(function(ev) {
        var format = ev.target.getAttribute("data-format");
        switchDateFormat(format);
    });

    switchDateFormat("local");
    // The table is initially hidden to avoid flickering as we convert dates.
    // Once it's ready, set it to visible:
    $("#log").css("visibility", "visible");
});
