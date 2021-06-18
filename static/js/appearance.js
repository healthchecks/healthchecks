$(function () {
    $("input[type=radio][name=theme]").change(function() {
        document.body.classList.toggle("dark", this.value == "dark");
    });
});
