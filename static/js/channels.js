$(function() {

    $(".rw .edit-checks").click(function() {
        $("#checks-modal").modal("show");
        $.ajax(this.dataset.url).done(function(data) {
            $("#checks-modal .modal-content").html(data);

        })

        return false;
    });

    var $cm = $("#checks-modal");
    function updateNumAssigned() {
        var numAssigned = $cm.find("input:checked").length;
        $cm.find("#num-assigned").text(numAssigned);
    }
    $cm.on("click", "#select-all", function() {
        $cm.find("input[type='checkbox']").prop("checked", true);
        updateNumAssigned();
    });
    $cm.on("click", "#unselect-all", function() {
        $cm.find("input[type='checkbox']").prop("checked", false);
        updateNumAssigned();
    });
    $cm.on("change", "input", updateNumAssigned);

    $(".channel-remove").click(function() {
        var $this = $(this);

        $("#remove-channel-form").attr("action", $this.data("url"));
        $(".remove-channel-kind").text($this.data("kind"));
        $('#remove-channel-modal').modal("show");

        return false;
    });

    $(".channel-modal").on('shown.bs.modal', function () {
        $(".input-name", this).focus();
    })

    $('[data-toggle="tooltip"]').tooltip();

});