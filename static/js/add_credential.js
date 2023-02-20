$(function() {
    var form = document.getElementById("add-credential-form");

    function requestCredentials() {
        // Hide error & success messages, show the "waiting" message
        $("#name-next").addClass("hide");
        $("#waiting").removeClass("hide");
        $("#error").addClass("hide");
        $("#success").addClass("hide");

        var options = JSON.parse($("#options").text());
        webauthnJSON.create(options).then(function(response) {
            $("#response").val(JSON.stringify(response));
            // Show the success message and save button
            $("#waiting").addClass("hide");
            $("#success").removeClass("hide");
        }).catch(function(err) {
            // Show the error message
            $("#waiting").addClass("hide");
            $("#error-text").text(err);
            $("#error").removeClass("hide");
        });
    }

    $("#name").on('keypress',function(e) {
        if (e.which == 13) {
            e.preventDefault();
            requestCredentials();
        }
    });

    $("#name-next").click(requestCredentials);
    $("#retry").click(requestCredentials);

    // Disable the submit button to prevent double submission
    $("#add-credential-form").submit(function() {
        $("#add-credential-submit").prop("disabled", true);
    });

});
