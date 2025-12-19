$(function() {
    $("select[name=tz]").selectize();

    $(".leave-project").click(function() {
        $("#leave-project-name").text(this.dataset.name);
        $("#leave-project-code").val(this.dataset.code);
        $('#leave-project-modal').modal("show");
        return false;
    });

    var browserTz = null;
    try {
        var browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch(err) {};

    if (browserTz && $("#tz").val() != browserTz) {
        $("#browser-tz-hint b").text(browserTz);
        $("#browser-tz-hint").removeClass("hide");
    }
    $("#browser-tz-hint a").click(function() {
        $("#tz")[0].selectize.setValue(browserTz, true);
        return false;
    });

});