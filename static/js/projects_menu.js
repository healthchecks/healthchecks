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
                $("#project-menu li.project-item").remove();
                $("#projects-divider").after(data);
            }
        });
    }

    $("#project-menu").on("mouseenter", refreshMenu);
    $("#project-menu > .dropdown").on("show.bs.dropdown", refreshMenu);
});
