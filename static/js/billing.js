$(function () {
    var clientTokenRequested = false;
    function requestClientToken() {
        if (!clientTokenRequested) {
            clientTokenRequested = true;
            $.getJSON("/pricing/get_client_token/", setupDropin);
        }
    }

    function setupDropin(data) {
        braintree.dropin.create({
            authorization: data.client_token,
            container: "#dropin",
            paypal: { flow: 'vault' }
        }, function(createErr, instance) {
            $("#payment-form-submit").click(function() {
                instance.requestPaymentMethod(function (requestPaymentMethodErr, payload) {
                    $("#pmm-nonce").val(payload.nonce);
                    $("#payment-form").submit();
                });
            }).prop("disabled", false);
        });
    }

    $("#update-payment-method").hover(requestClientToken);

    $("#update-payment-method").click(function() {
        requestClientToken();
        $("#payment-form").attr("action", this.dataset.action);
        $("#payment-form-submit").text("Update Payment Method");
        $("#payment-method-modal").modal("show");
    });


    $("#billing-history").load( "/accounts/profile/billing/history/" );
    $("#billing-address").load( "/accounts/profile/billing/address/", function() {
        $("#billing-address input").each(function(idx, obj) {
            $("#" + obj.name).val(obj.value);
        });
    });

    $("#payment-method").load( "/accounts/profile/billing/payment_method/", function() {
        $("#next-billing-date").text($("#nbd").val());
    });

});