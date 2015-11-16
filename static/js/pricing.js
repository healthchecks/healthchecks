$(function () {
    var prices = [2, 5, 10, 15, 20, 25, 50, 75, 100, 125, 150, 175, 200];
    var priceIdx = 2;

    $("#pay-plus").click(function() {
        if (priceIdx >= 12)
            return;

        priceIdx += 1;
        $("#pricing-value").text(prices[priceIdx]);

        $("#piggy").removeClass().addClass("tada animated").one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function(){
            $(this).removeClass();
        });;

    });

    $("#pay-minus").click(function() {
        if (priceIdx <= 0)
            return;

        priceIdx -= 1;
        $("#pricing-value").text(prices[priceIdx]);

        $("#piggy").removeClass().addClass("tadaIn animated").one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function(){
            $(this).removeClass();
        });;

    });


});