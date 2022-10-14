window.addEventListener("DOMContentLoaded", function(e) {
    var email = document.getElementById("signup-email");
    var submitBtn = document.getElementById("signup-go");

    function submitForm() {
        if (submitBtn.disabled) {
            return;
        }
        submitBtn.disabled = true;

        try {
            var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch(err) {
            var tz = "UTC";
        }

        var payload = new FormData();
        payload.append("identity", email.value);
        payload.append("tz", tz);

        var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
        fetch(base + "/accounts/signup/", {method: "POST", body: payload})
            .then(response => response.text())
            .then(function(text) {
                var resultLine = document.getElementById("signup-result");
                resultLine.innerHTML = text;
                resultLine.style.display = "block";
                submitBtn.disabled = false;
            });

        return false;
    }

    // Wire up the submit button and the Enter key
    submitBtn.addEventListener("click", submitForm);
    email.addEventListener("keyup", function(e) {
        if (e.which == 13) {
            return submitForm();
        }
    });

    var modal = document.getElementById("signup-modal");
    modal.addEventListener("shown.bs.modal", function() {
        email.focus();
    });
});
