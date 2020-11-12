$(function() {
    var form = document.getElementById("add-credential-form");
    var optionsBinary = btoa(form.dataset.options);
    var array = Uint8Array.from(atob(form.dataset.options), c => c.charCodeAt(0));
    var options = CBOR.decode(array.buffer);
    console.log("decoded options:", options);

    function b64(arraybuffer) {
        return btoa(String.fromCharCode.apply(null, new Uint8Array(arraybuffer)));
    }

    navigator.credentials.create(options).then(function(attestation) {
        console.log("got attestation: ", attestation);

        document.getElementById("attestationObject").value = b64(attestation.response.attestationObject);
        document.getElementById("clientDataJSON").value = b64(attestation.response.clientDataJSON);
        console.log("form updated, all is well");
        $("#add-credential-submit").prop("disabled", "");
    }).catch(function(err) {
        console.log("Something went wrong", err);
    });
});