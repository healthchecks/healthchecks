$(function() {
    var form = document.getElementById("add-credential-form");
    var optionsBytes = Uint8Array.from(atob(form.dataset.options), c => c.charCodeAt(0));
    // cbor.js expects ArrayBuffer as input when decoding
    var options = CBOR.decode(optionsBytes.buffer);

    function b64(arraybuffer) {
        return btoa(String.fromCharCode.apply(null, new Uint8Array(arraybuffer)));
    }

    function requestCredentials() {
        // Hide error & success messages, show the "waiting" message
        $("#name-next").addClass("hide");
        $("#add-credential-waiting").removeClass("hide");
        $("#add-credential-error").addClass("hide");
        $("#add-credential-success").addClass("hide");

        navigator.credentials.create(options).then(function(attestation) {
            $("#attestation_object").val(b64(attestation.response.attestationObject));
            $("#client_data_json").val(b64(attestation.response.clientDataJSON));

            // Show the success message and save button
            $("#add-credential-waiting").addClass("hide");
            $("#add-credential-success").removeClass("hide");
        }).catch(function(err) {
            // Show the error message
            $("#add-credential-waiting").addClass("hide");
            $("#add-credential-error-text").text(err);
            $("#add-credential-error").removeClass("hide");
        });
    }

    $("#name-next").click(requestCredentials);
    $("#retry").click(requestCredentials);

});