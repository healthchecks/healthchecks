$(function() {

    var reBlankLines = new RegExp("^\\s*[\\r\\n]", "gm");
    var reTrailingWhitespace = new RegExp("\\s+$");

    var clipboard = new Clipboard("button.copy-snippet-link", {
        text: function (trigger) {
            var snippetElement = $(trigger).next(".highlight").children().clone();
            /* remove pygmentize comment elements */
            snippetElement.find(".c, .cm, .cp, .c1, .cs").remove();
            /* remove blank lines and trailing whitespace */
            return snippetElement.text().replace(reBlankLines, '').replace(reTrailingWhitespace, '');
        }
    });

    clipboard.on("success", function(e) {
        e.trigger.textContent = "copied!";
        e.clearSelection();
    });

    $("button.copy-snippet-link").mouseout(function(e) {
        setTimeout(function() {
            e.target.textContent = "copy";
        }, 300);
    })
});
