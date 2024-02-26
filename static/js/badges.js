$(function() {
    function updatePreview() {
        var params = $("#badge-settings-form").serialize();
        var token = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: window.location.href,
            type: "post",
            headers: {"X-CSRFToken": token},
            data: params,
            success: function(data) {
                document.getElementById("preview").innerHTML = data;
                $(".fetch-json").each(function(idx, el) {
                    $.getJSON(el.dataset.url, function(data) {
                        el.innerText = JSON.stringify(data);
                    });
                });
            }
        });
    }

    $("input[type=radio]").change(updatePreview);
    $("select").change(updatePreview);
});
