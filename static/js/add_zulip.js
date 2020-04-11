$(function() {
    function updateForm() {
        var mType = $('input[name=mtype]:checked').val();
        if (mType == "stream") {
            $("#z-to-label").text("Stream Name");
            $("#z-to-help").text('Example: "general"');
        }
        if (mType == "private") {
            $("#z-to-label").text("User's Email");
            $("#z-to-help").text('Example: "alice@example.org"');
        }
    }

    // Update form labels when user clicks on radio buttons
    $('input[type=radio][name=mtype]').change(updateForm);

});
