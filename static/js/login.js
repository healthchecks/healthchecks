$(function () {
    var passwordInput = $("#password-block input");

    if ($("#password-block").hasClass("hide")) {
       passwordInput.detach();
    }

    $("#password-toggle").click(function() {
        $("#password-toggle").hide();
        $("#password-block").removeClass("hide");
        $("#password-block .input-group").append(passwordInput);
    });
});
