$(function() {
    var base = document.getElementById("base-url").getAttribute("href").slice(0, -1);

    var timeout = null;
    function refreshMenu()     {
        if (timeout) return;

        timeout = setTimeout(function() {
            timeout = null
        }, 3000);

        $.ajax({
            url: base + "/projects/menu/",
            timeout: 2000,
            success: function(data) {
                $("#nav-project li.project-item").remove();
                $("#projects-divider").after(data);
            }
        });
    }

    $("#nav-project").on("mouseenter click", refreshMenu);
});
