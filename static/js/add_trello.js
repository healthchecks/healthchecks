$(function() {
    function updateSettings() {
        var opt = $('#list-selector').find(":selected");
        $("#settings").val(JSON.stringify({
            "token": $("#settings").data("token"),
            "list_id": opt.data("listId"),
            "board_name": opt.data("boardName"),
            "list_name": opt.data("listName")
        }));
    }

    var tokenMatch = window.location.hash.match(/token=(\w+)/);
    if (tokenMatch) {
        $(".jumbotron").hide();
        $("integration-settings").text("Loading...");

        token = tokenMatch[1];
        var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);
        var csrf = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: base + "/integrations/add_trello/settings/",
            type: "post",
            headers: {"X-CSRFToken": csrf},
            data: {token: token},
            success: function(data) {
                $("#integration-settings" ).html(data);
                updateSettings();
            }
        });
    }

    $("#integration-settings").on("change", "#list-selector", updateSettings);
});
