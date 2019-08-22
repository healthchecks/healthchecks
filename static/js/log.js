$(function () {
    $("#log tr.ok").on("click", function() {
        $("#ping-details-body").text("Updating...");
        $('#ping-details-modal').modal("show");

        $.get(this.dataset.url, function(data) {
            $("#ping-details-body").html(data);
        });

        return false;
    });

    function switchDateFormat(format) {
        var tz = format == "local" ? spacetime().timezone().name : format;
        $("#log tr").each(function(index, row) {
            var s = spacetime(row.getAttribute("data-dt")).goto(tz);
            $(".date", row).text(s.unixFmt("MMM d"));
            $(".time", row).text(s.unixFmt("h:mm"));                
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
