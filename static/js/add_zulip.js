$(function() {
    function updateForm() {
        var mType = $('input[name=mtype]:checked').val();
        if (mType == "stream") {
            $("#z-to-label").text("Stream");
            $("#z-to-help").text('Example: "general"');
        }
        if (mType == "private") {
            $("#z-to-label").text("User's Email");
            $("#z-to-help").text('Example: "alice@example.org"');
        }

        $("#z-topic-group").toggleClass("hide", mType == "private");
    }

    // Update form labels when user clicks on radio buttons
    $('input[type=radio][name=mtype]').change(updateForm);

    $("#zuliprc").change(function() {
        this.files[0].text().then(function(contents) {
            var keyMatch = contents.match(/key=(.*)/);
            var emailMatch = contents.match(/email=(.*@.*)/);
            var siteMatch = contents.match(/site=(.*)/);

            if (!keyMatch || !emailMatch || !siteMatch) {
                $("#zuliprc-help").text("Invalid file format.");
                $("#save-integration").prop("disabled", true);
                return
            }

            $("#zulip-api-key").val(keyMatch[1]);
            $("#zulip-bot-email").val(emailMatch[1]);
            $("#zulip-site").val(siteMatch[1]);
            $("#zuliprc-help").text("");

            $("#save-integration").prop("disabled", false);
        });
    })

});
