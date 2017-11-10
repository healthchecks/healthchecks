$(function() {
    function haveBlankHeaderForm() {
        return $("#webhook-headers .webhook-header").filter(function() {
            var key = $(".key", this).val();
            var value = $(".value", this).val();
            return !key && !value;
        }).length;
    }

    function ensureBlankHeaderForm() {
        if (!haveBlankHeaderForm()) {
            var tmpl = $("#header-template").html();
            $("#webhook-headers").append(tmpl);
        }
    }

    $("#webhook-headers").on("click", "button", function(e) {
        e.preventDefault();
        $(this).closest(".webhook-header").remove();
        ensureBlankHeaderForm();
    })

    $("#webhook-headers").on("keyup", "input", ensureBlankHeaderForm);
    ensureBlankHeaderForm();
});