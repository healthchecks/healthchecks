$(function () {

    function submitForm() {
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
    }

    $("#signup-go").on("click", submitForm);

    $("#signup-email").keypress(function (e) {
        if (e.which == 13) {
            return submitForm();
        }
    });

    $("#signup-modal").on('shown.bs.modal', function () {
        $("#signup-email").focus()
    })

});