$(function() {
    var form = document.getElementById("login-tfa-form");
    var optionsBytes = Uint8Array.from(atob(form.dataset.options), c => c.charCodeAt(0));
    // cbor.js expects ArrayBuffer as input when decoding
    var options = CBOR.decode(optionsBytes.buffer);

    function b64(arraybuffer) {
        return btoa(String.fromCharCode.apply(null, new Uint8Array(arraybuffer)));
    }

    function authenticate() {
        $("#waiting").removeClass("hide");
        $("#error").addClass("hide");

        navigator.credentials.get(options).then(function(assertion) {
            $("#credential_id").val(b64(assertion.rawId));
            $("#authenticator_data").val(b64(assertion.response.authenticatorData));
            $("#client_data_json").val(b64(assertion.response.clientDataJSON));
            $("#signature").val(b64(assertion.response.signature));

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

    $("#retry").click(authenticate);

    authenticate();

});
