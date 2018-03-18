$(function () {
    $(".details-btn").on("click", function() {
        $("#ping-details-body").text("Updating...");
        $('#ping-details-modal').modal("show");

        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: this.dataset.url,
            type: "post",
            headers: {"X-CSRFToken": token},
            success: function(data) {
                $("#ping-details-body" ).html(data);
            }
        });

        return false;
    });

    function switchDateFormat(format) {
        $("#log td.datetime").each(function(index, cell) {
            var dt = moment(cell.getAttribute("data-raw"));
            format == "local" ? dt.local() : dt.utc();

            $(".date", cell).text(dt.format("MMM D"));
            $(".time", cell).text(dt.format("HH:mm"));
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
