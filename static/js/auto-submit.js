$(function() {
    $("input[data-auto-submit]").on("keyup input", function() {
        if (this.validity.valid) {
            this.form.submit();
        }
    });
})