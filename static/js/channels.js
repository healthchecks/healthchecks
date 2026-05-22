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
        var numAssigned = $cm.find("input:checkbox:checked").length;
        var numTotal = $cm.find("input:checkbox").length;
        $cm.find("#num-assigned").text(numAssigned);
        $cm.find("#select-all").attr("disabled", numAssigned == numTotal);
        $cm.find("#unselect-all").attr("disabled", numAssigned == 0);
    }
    $cm.on("click", "#select-all", function() {
        $cm.find("input[type='checkbox']").prop("checked", true);
        updateNumAssigned();
    });
    $cm.on("click", "#unselect-all", function() {
        $cm.find("input[type='checkbox']").prop("checked", false);
        updateNumAssigned();
    });
    // When any checkbox changes its value, update the "(x of y)"" in the title
    $cm.on("change", "input", updateNumAssigned);
    // Let the user to click anywhere in the row to toggle the checkbox
    $cm.on("click", "tr", function(ev) {
        if (event.target.type !== 'checkbox') {
            $(":checkbox", this).trigger('click');
        }
    });

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
