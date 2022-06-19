$(function() {
    var form = document.getElementById("login-tfa-form");

    function authenticate() {
        $("#pick-method").addClass("hide");
        $("#waiting").removeClass("hide");
        $("#error").addClass("hide");

        var options = JSON.parse($("#options").text());
        webauthnJSON.get(options).then(function(response) {
            $("#response").val(JSON.stringify(response));
            // Show the success message and save button
            $("#waiting").addClass("hide");
            $("#success").removeClass("hide");
            form.submit()
        }).catch(function(err) {
            // Show the error message
            $("#waiting").addClass("hide");
            $("#error-text").text(err);
            $("#error").removeClass("hide");
        });
    }

    $("#use-key-btn").click(authenticate);
    $("#retry").click(authenticate);
});
