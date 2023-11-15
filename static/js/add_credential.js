$(function() {
    var form = document.getElementById("add-credential-form");

    function requestCredentials() {
        // Hide error & success messages, show the "waiting" message
        $("#name-next").addClass("hide");
        $("#waiting").removeClass("hide");
        $("#error").addClass("hide");
        $("#success").addClass("hide");

        var options = JSON.parse($("#options").text());
        // Override pubKeyCredParams prepared by python-fido2,
        // to only list ES256 (-7) and RS256 (-257), **and omit Ed25519 (-8)**.
        // This is to work around a bug in Firefox < 119. Affected
        // Firefox versions serialize Ed25519 keys incorrectly,
        // the workaround is to exclude Ed25519 from pubKeyCredParams.
        //
        // For reference, different project, similar issue:
        // https://github.com/MasterKale/SimpleWebAuthn/issues/463
        options.publicKey.pubKeyCredParams= [
            {"alg": -7, "type": "public-key"},
            {"alg": -257, "type": "public-key"}
        ]

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
