$(function() {

    $(".leave-project").click(function() {
        var $this = $(this);

        $("#leave-project-name").text($this.data("name"));
        $("#leave-project-code").val($this.data("code"));
        $('#leave-project-modal').modal("show");

        return false;
    });

});