$(function () {
    var prices = [2, 5, 10, 15, 20, 25, 50, 100];
    var initialPrice = parseInt($("#pricing-value").text());
    var priceIdx = prices.indexOf(initialPrice);

    function updateDisplayPrice(price) {
        $("#pricing-value").text(price);
        $(".selected-price").val(price);
        $("#pww-switch-btn").text("Switch to $" + price + " / mo");

        if (price == initialPrice) {
            $("#pww-selected-btn").show();
            $("#pww-switch-btn").hide();
        } else {
            $("#pww-selected-btn").hide();
            $("#pww-switch-btn").show();
        }
    }

    $("#pay-plus").click(function() {
        if (priceIdx > 6)
            return;

        priceIdx += 1;
        updateDisplayPrice(prices[priceIdx]);

        $("#piggy").removeClass().addClass("tada animated").one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function(){
            $(this).removeClass();
        });;

    });

    $("#pay-minus").click(function() {
        if (priceIdx <= 0)
            return;

        priceIdx -= 1;
        updateDisplayPrice(prices[priceIdx]);

        $("#piggy").removeClass().addClass("tadaIn animated").one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function(){
            $(this).removeClass();
        });;

    });

    $("#pww-create-payment-method").click(function(){
        var $modal = $("#payment-method-modal");
        var clientToken = $modal.attr("data-client-token");

        braintree.setup(clientToken, "dropin", {
            container: "payment-form"
        });

        $modal.modal("show");
    });

});