$(function () {
    $("#log tr.ok").on("click", function() {
        var n = $("td", this).first().text();
        var tmpl = $("#log").data("url").slice(0, -2);
        loadPingDetails(tmpl + n + "/");
        return false;
    });

    function switchDateFormat(format) {
        document.querySelectorAll("#log tr").forEach(function(row) {
            var dt = moment(row.dataset.dt);
            format == "local" ? dt.local() : dt.tz(format);

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
