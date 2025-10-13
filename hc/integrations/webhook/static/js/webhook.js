$(function() {
    $("#method-down").change(function() {
        var method = this.value;
        $("#body-down-group").toggle(method != "GET");
    });

    $("#method-up").change(function() {
        var method = this.value;
        $("#body-up-group").toggle(method != "GET");
    });

    // On page load, check if we need to show "request body" fields
    $("#method-down").trigger("change");
    $("#method-up").trigger("change");
});