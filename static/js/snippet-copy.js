$(function() {
    var markup = '<button class="btn btn-default hidden-sm">' +
                 '<span class="ic-clippy"></span>' +
                 '</button>';

    $(".highlight").append(markup);

    $(".highlight button")
        .tooltip({title: "Copied", trigger: "manual"})
        .on("mouseleave", function(e) {
            $(e.target).tooltip("hide");
        })
        .click(function() {
            var text = this.parentNode.innerText;
            navigator.clipboard.writeText(text);
            $(this).tooltip("show");
        })

});
