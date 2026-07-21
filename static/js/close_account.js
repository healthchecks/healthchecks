window.addEventListener("DOMContentLoaded", function(e) {
    var submitBtn = document.getElementById("close-go");
    submitBtn.addEventListener("click", function() {
        if (!submitBtn.disabled) {
            submitBtn.disabled = true;
            document.forms.close_account.submit();
        }
    });
});