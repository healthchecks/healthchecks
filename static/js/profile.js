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

    $('#set-team-name-modal').on('shown.bs.modal', function () {
        $('#team-name').focus();
    })

});