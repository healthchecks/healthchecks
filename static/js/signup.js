window.addEventListener("DOMContentLoaded", function(e) {
    var email = document.getElementById("signup-email");
    var submitBtn = document.getElementById("signup-go");
    if (!submitBtn) {
        // Registration is not open, nothing to do here.
        return;
    }

    function getTz() {
        try {
            return Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch(err) {
            return "UTC";
        }
    }

    function submitForm() {
        if (submitBtn.disabled) {
            return;
        }
        submitBtn.disabled = true;

        var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
        fetch(base + "/accounts/signup/csrf/")
            .then(csrfResponse => csrfResponse.text())
            .then(csrfToken => {
                var payload = new FormData();
                payload.append("identity", email.value);
                payload.append("tz", getTz());
                payload.append("csrfmiddlewaretoken", csrfToken);
                return fetch(base + "/accounts/signup/", {method: "POST", body: payload});

            })
            .then(signupResponse => signupResponse.text())
            .then(text => {
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
