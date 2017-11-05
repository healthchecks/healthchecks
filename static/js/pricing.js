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

    $(".btn-create-payment-method").hover(requestClientToken);
    $(".btn-update-payment-method").hover(requestClientToken);

    $(".btn-create-payment-method").click(function() {
        requestClientToken();
        $("#plan_id").val(this.dataset.planId);
        $("#payment-form").attr("action", this.dataset.action);
        $("#payment-form-submit").text("Set Up Subscription and Pay $" + this.dataset.planPay);
        $("#payment-method-modal").modal("show");
    });

    $(".btn-update-payment-method").click(function() {
        requestClientToken();
        $("#payment-form").attr("action", this.dataset.action);
        $("#payment-form-submit").text("Update Payment Method");
        $("#payment-method-modal").modal("show");
    });

    $("#period-controls :input").change(function() {
        $("#monthly").toggleClass("hide", this.value != "monthly");
        $("#annual").toggleClass("hide", this.value != "annual");
    });

});