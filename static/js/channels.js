$(function() {
    var placeholders = {
        email: "address@example.org",
        webhook: "http://",
        pd: "service key"
    }

    $("#add-check-kind").change(function() {
        $(".channels-add-help p").hide();

        var v = $("#add-check-kind").val();
        $(".channels-add-help p." + v).show();

        $("#add-check-value").attr("placeholder", placeholders[v]);
    });

    $(".edit-checks").click(function() {
        $("#checks-modal").modal("show");
        var url = $(this).attr("href");
        $.ajax(url).done(function(data) {
            $("#checks-modal .modal-content").html(data);

        })


        return false;
    });


    var $cm = $("#checks-modal");
    $cm.on("click", "#toggle-all", function() {
        var value = $(this).prop("checked");
        $cm.find(".toggle").prop("checked", value);
        console.log("aaa", value);

    });

});