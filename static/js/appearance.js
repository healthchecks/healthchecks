$(function () {
    $("input[type=radio][name=theme]").change(function() {
        this.form.submit();
    });
});
