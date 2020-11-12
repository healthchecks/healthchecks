$(function() {
    var form = document.getElementById("add-credential-form");
    var optionsBytes = Uint8Array.from(atob(form.dataset.options), c => c.charCodeAt(0));
    // cbor.js expects ArrayBuffer as input when decoding
    var options = CBOR.decode(optionsBytes.buffer);
    console.log("decoded options:", options);

    function b64(arraybuffer) {
        return btoa(String.fromCharCode.apply(null, new Uint8Array(arraybuffer)));
    }

    navigator.credentials.create(options).then(function(attestation) {
        console.log("got attestation: ", attestation);

        $("#attestation_object").val(b64(attestation.response.attestationObject));
        $("#client_data_json").val(b64(attestation.response.clientDataJSON));
        console.log("form updated, all is well");

        $("#add-credential-submit").prop("disabled", "");
        $("#add-credential-success").removeClass("hide");
    }).catch(function(err) {
        $("#add-credential-error span").text(err);
        $("#add-credential-error").removeClass("hide");
    });
});