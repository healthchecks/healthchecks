$(function() {

    $(".rw .edit-checks").click(function() {
        $("#checks-modal").modal("show");
        $.ajax(this.dataset.url).done(function(data) {
            $("#checks-modal .modal-content").html(data);

        })

        return false;
    });

    var $cm = $("#checks-modal");
    $cm.on("click", "#toggle-all", function() {
        var value = $(this).prop("checked");
        $cm.find(".toggle").prop("checked", value);
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