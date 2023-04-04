$(function () {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
    var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;

    var currentPreviewHash = "";
    function updateCronPreview() {
        var schedule = $("#schedule").val();

        // Don't try preview with empty values, or if values have not changed
        if (!schedule || schedule == currentPreviewHash)
            return;

        // OK, we're good
        currentPreviewHash = schedule;
        $("#cron-preview-title").text("Updating...");

        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: base + "/checks/cron_preview/",
            type: "post",
            headers: {"X-CSRFToken": token},
            data: {schedule: schedule, tz: tz},
            success: function(data) {
                if (schedule != currentPreviewHash) {
                    return;  // ignore stale results
                }

                $("#cron-preview" ).html(data);
            }
        });
    }

    $("#common-cron-expressions button").click(function() {
        var schedule = $(this).closest("tr").find("td:nth-child(2n)").text();
        $("#schedule").val(schedule);
        updateCronPreview();
    });

    $("#schedule").on("keyup", updateCronPreview);
    updateCronPreview();
});
