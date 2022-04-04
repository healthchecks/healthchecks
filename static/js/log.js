$(function () {
    $("#log tr.ok").on("click", function() {
        var n = $("td", this).first().text();
        var tmpl = $("#log").data("url").slice(0, -2);
        loadPingDetails(tmpl + n + "/");
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
