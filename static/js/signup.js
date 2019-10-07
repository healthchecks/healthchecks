$(function () {

    $("#signup-go").on("click", function() {
        var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
        var email = $("#signup-email").val();
        var token = $('input[name=csrfmiddlewaretoken]').val();

        $("#signup-go").prop("disabled", true);
        $.ajax({
            url: base + "/accounts/signup/",
            type: "post",
            headers: {"X-CSRFToken": token},
            data: {"identity": email},
            success: function(data) {
                $("#signup-result").html(data).show();
                $("#signup-go").prop("disabled", false);
            }
        });

        return false;
    });

});