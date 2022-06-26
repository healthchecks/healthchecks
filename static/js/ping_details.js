function loadPingDetails(url) {
    $("#ping-details-body").html("<div class='loading'><div class='spinner'><div></div><div></div><div></div></div></div>");
    $('#ping-details-modal').modal("show");
    $("#ping-details-body .spinner").addClass("started");

    $.get(url, function(data) {
            $("#ping-details-body").html(data);

            var htmlPre = $("#email-body-html pre");
            if (htmlPre.length) {
                var opts = {USE_PROFILES: {html: true}};
                var clean = DOMPurify.sanitize(htmlPre.text(), opts);
                var blob = new Blob([clean], {type: "text/html; charset=utf-8"});

                var iframe = document.createElement("iframe");
                iframe.sandbox = "";
                iframe.src = URL.createObjectURL(blob);

                htmlPre.replaceWith(iframe);
            }
        }
    );
}