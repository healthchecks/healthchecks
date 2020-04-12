$(function() {

    $(".member-remove").click(function() {
        var $this = $(this);

        $("#rtm-email").text($this.data("email"));
        $("#remove-team-member-email").val($this.data("email"));
        $('#remove-team-member-modal').modal("show");

        return false;
    });

    $('#invite-team-member-modal').on('shown.bs.modal', function () {
        $('#itm-email').focus();
    })

    $('#set-project-name-modal').on('shown.bs.modal', function () {
        $('#project-name').focus();
    })

    $(".add-to-team").click(function() {
        $("#itm-email").val(this.dataset.email);
        $("#invite-team-member-modal form").submit();
        return false;
    });

    // Enable the submit button in transfer form when user selects
    // the target owner:
    $("#new-owner").on("change", function() {
        $("#transfer-confirm").prop("disabled", !this.value);
    });

});
