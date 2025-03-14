window.addEventListener("DOMContentLoaded", function (e) {
    // Event handler for input's oninput event
    var validateAndSubmit = function (e) {
        if (this.validity.valid) {
            // Use requestSubmit() instead of submit() because submit()
            // does not generate the onsubmit event.
            this.form.requestSubmit();
        }
    };

    // Event handler for form's onsubmit event
    var checkDoubleSubmit = function (e) {
        if (this.dataset.submitted) {
            e.preventDefault();
        }

        this.dataset.submitted = true;
    };

    // Hook up validateAndSubmit to all input elements with the
    // "data-auto-submit" attribute
    document.querySelectorAll("input[data-auto-submit]").forEach((input) => {
        input.addEventListener("input", validateAndSubmit);
        input.form.addEventListener("submit", checkDoubleSubmit);
    });
});
