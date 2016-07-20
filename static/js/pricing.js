$(function () {

    $(".btn-create-payment-method").click(function() {
        var planId = $(this).data("plan-id");
        $("#plan_id").val(planId);
        $.getJSON("/pricing/get_client_token/", function(data) {
            var $modal = $("#payment-method-modal");
            braintree.setup(data.client_token, "dropin", {
                container: "payment-form"
            });
            $modal.modal("show");
        })
    });

    $(".btn-update-payment-method").click(function() {
        $.getJSON("/pricing/get_client_token/", function(data) {
            var $modal = $("#update-payment-method-modal");
            braintree.setup(data.client_token, "dropin", {
                container: "update-payment-form"
            });
            $modal.modal("show");
        })
    });

    $(".pm-modal").on("hidden.bs.modal", function() {
        location.reload();
    })

});