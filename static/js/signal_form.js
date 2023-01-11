$(function() {
    $("#id_number").on("change keyup", function() {
        $("#submit-btn").attr("disabled", true);
    });

    // Show a tooltip on the submit button only if it is disabled
    $("body").tooltip({selector: "#submit-btn:disabled"});

    $("#signal-verify-btn").click(function() {
        $("#signal-verify-btn").attr("disabled", true);

        var url = this.dataset.verifyUrl;
        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: url,
            type: "post",
            headers: {"X-CSRFToken": token},
            data: {"phone": $("#id_number").val()},
            success: function(data) {
                $("#verify-result").html(data);
                $("#submit-btn").attr("disabled", data.indexOf("alert-success") == -1);
                $("#signal-verify-btn").attr("disabled", false);
            }
        });
    });
})