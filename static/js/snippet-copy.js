$(function() {
    var markup = '<button class="btn btn-default hidden-sm">' +
                 '<span class="ic-clippy"></span>' +
                 '</button>';



    $(".highlight").append(markup);


    var reBlankLines = new RegExp("^\\s*[\\r\\n]", "gm");
    var reTrailingWhitespace = new RegExp("\\s+$");

    var clipboard = new ClipboardJS(".highlight button", {
        text: function (trigger) {
            var snippetElement = $(trigger).parent().children().clone();
            /* remove pygmentize comment elements */
            snippetElement.find(".c, .cm, .cp, .c1, .cs").remove();
            /* remove blank lines and trailing whitespace */
            return snippetElement.text().replace(reBlankLines, '').replace(reTrailingWhitespace, '');
        }
    });


    $(".highlight button")
        .tooltip({title: "Copied", trigger: "manual"})
        .on("mouseleave", function(e) {
            $(e.target).tooltip("hide");
        })

    clipboard.on("success", function(e) {
        $(e.trigger).tooltip("show");
    });

    clipboard.on("error", function(e) {
        prompt("Press Ctrl+C to select:", e.text)
    });
});
