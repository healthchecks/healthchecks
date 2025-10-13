$(function() {
    function updateSettings() {
        var opt = $('#list-selector').find(":selected");
        $("#board-name").val(opt.data("boardName"));
        $("#list-name").val(opt.data("listName"));
        $("#list-id").val(opt.data("listId"));
    }

    var tokenMatch = window.location.hash.match(/token=(\w+)/);
    if (tokenMatch) {
        $(".jumbotron").hide();
        $("integration-settings").text("Loading...");

        var token = tokenMatch[1];
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
