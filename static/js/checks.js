$(function () {
    $('[data-toggle="tooltip"]').tooltip();

    $(".name-edit input").click(function() {
        $form = $(this.parentNode);
        if (!$form.hasClass("inactive"))
            return;

        // Click on all X buttons
        $(".name-edit:not(.inactive) .name-edit-cancel").click();

        // Make this form editable and store its initial value
        $form
            .removeClass("inactive")
            .data("originalValue", this.value);
    });

    $(".name-edit-cancel").click(function(){
        var $form = $(this.parentNode);
        var v = $form.data("originalValue");

        $form
            .addClass("inactive")
            .find(".input-name").val(v);

        return false;
    });

    $(".timeout").click(function() {
        $(".timeout-cell").addClass("inactive");

        $cell = $(this.parentNode);
        $cell.removeClass("inactive");
    });

    $(".timeout-edit-cancel").click(function() {
        $(this).parents("td").addClass("inactive");
        return false;
    });

    $(".check-menu-remove").click(function() {
        var $this = $(this);

        $("#remove-check-form").attr("action", $this.data("url"));
        $(".remove-check-name").text($this.data("name"));
        $('#remove-check-modal').modal("show");

        return false;
    });

});