$(function () {
    var pw = document.getElementById("password");
    var meter = document.getElementById("meter");
    pw.addEventListener("input", function() {
        if (!pw.value) {
            // If the field is empty, clear the strength meter
            // and let the default validation take over.
            meter.removeAttribute("class");
            pw.setCustomValidity("");
            return
        }

        var score = zxcvbn(pw.value).score;
        meter.setAttribute("class", "score-" + score);
        if (pw.validity.valid && score == 0) {
             pw.setCustomValidity("Please pick a stronger password.");
        } else {
            pw.setCustomValidity("");
        }
    });
});
