$(function() {

    $(".leave-project").click(function() {
        $("#leave-project-name").text(this.dataset.name);
        $("#leave-project-code").val(this.dataset.code);
        $('#leave-project-modal').modal("show");
        return false;
    });

});