window.addEventListener("DOMContentLoaded", function(e) {
    var validateAndSubmit = function() {
        if (this.validity.valid && !this.dataset.submitted) {
            // Make sure we only submit the form once
            this.dataset.submitted = true;
            this.form.submit();
        }
    }

    // Hook up validateAndSubmit to all input elements with the
    // "data-auto-submit" attribute
    document.querySelectorAll("input[data-auto-submit]").forEach((input) => {
        input.addEventListener("input", validateAndSubmit);
    });
});
