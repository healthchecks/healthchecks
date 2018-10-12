$(function () {

    $("#signup-go").on("click", function() {
        var email = $("#signup-email").val();
        var token = $('input[name=csrfmiddlewaretoken]').val();

        $.ajax({
            url: "/accounts/signup/",
            type: "post",
            headers: {"X-CSRFToken": token},
            data: {"identity": email},
            success: function(data) {
                $("#signup-result").html(data).show();
            }
        });

        return false;
    });

});