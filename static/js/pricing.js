$(function () {
    var prices = [2, 5, 10, 15, 20, 25, 50, 100];
    var initialPrice = parseInt($("#pricing-value").text());
    var priceIdx = prices.indexOf(initialPrice);

    function updateDisplayPrice(price) {
        $("#pricing-value").text(price);
        $("#pww-switch-btn").text("Switch to $" + price + " / mo");

        if (price == initialPrice) {
            $("#pww-selected-btn").show();
            $("#pww-switch-btn").hide();
        } else {
            $("#pww-selected-btn").hide();
            $("#pww-switch-btn").show();
        }
    }

    $(".btn-create-payment-method").click(function() {
        var planId = $(this).data("plan-id");
        console.log(planId);
        $("#plan_id").val(planId);
        $.getJSON("/pricing/get_client_token/", function(data) {
            var $modal = $("#payment-method-modal");
            braintree.setup(data.client_token, "dropin", {
                container: "payment-form"
            });
            $modal.modal("show");
        })
    });

    $("#payment-method-cancel").click(function() {
        location.reload();
    });

});