$(function () {
    var preloadedToken = null;
    function getToken(callback) {
        if (preloadedToken) {
            callback(preloadedToken);
        } else {
            $.getJSON("/pricing/token/", function(response) {
                preloadedToken = response.client_token;
                callback(response.client_token);
            });
        }
    }

    // Preload client token:
    if ($("#billing-address").length) {
        getToken(function(token){});
    }

    function getAmount(planId) {
        return planId.substr(1);
    }

    function showPaymentMethodForm(planId) {
        $("#plan-id").val(planId);
        $("#nonce").val("");

        if (planId == "") {
            // Don't need a payment method when switching to the free plan
            // -- can submit the form right away:
            $("#update-subscription-form").submit();
            return;
        }

        $("#payment-form-submit").prop("disabled", true);
        $("#payment-method-modal").modal("show");        

        getToken(function(token) {            
            braintree.dropin.create({
                authorization: token,
                container: "#dropin",
                threeDSecure: {
                    amount: getAmount(planId),
                },
                paypal: { flow: 'vault' },
                preselectVaultedPaymentMethod: false
            }, function(createErr, instance) {
                $("#payment-form-submit").off().click(function() {
                    instance.requestPaymentMethod(function (err, payload) {
                        $("#payment-method-modal").modal("hide");
                        $("#please-wait-modal").modal("show");
                        
                        $("#nonce").val(payload.nonce);
                        $("#update-subscription-form").submit();
                    });
                });

                $("#payment-method-modal").off("hidden.bs.modal").on("hidden.bs.modal", function() {
                    instance.teardown();
                });

                instance.on("paymentMethodRequestable", function() {
                    $("#payment-form-submit").prop("disabled", false);
                });

                instance.on("noPaymentMethodRequestable", function() {
                    $("#payment-form-submit").prop("disabled", true);
                });

            });
        });
    }

    $("#change-plan-btn").click(function() {
        $("#change-billing-plan-modal").modal("hide");
        showPaymentMethodForm(this.dataset.planId);
    });

    $("#update-payment-method").click(function() {
        showPaymentMethodForm($("#old-plan-id").val());        
    });

    $("#billing-history").load("/accounts/profile/billing/history/");
    $("#billing-address").load("/accounts/profile/billing/address/", function() {
        $("#billing-address input").each(function(idx, obj) {
            $("#" + obj.name).val(obj.value);
        });
    });

    $("#payment-method").load("/accounts/profile/billing/payment_method/", function() {
        $("#next-billing-date").text($("#nbd").val());
    });

    $("#billing-periods input").click(updateChangePlanForm);

    $("#plan-hobbyist").click(function() {
        $(".plan").removeClass("selected");
        $("#plan-hobbyist").addClass("selected");
        updateChangePlanForm();
    });

    $("#plan-business").click(function() {
        $(".plan").removeClass("selected");
        $("#plan-business").addClass("selected");
        updateChangePlanForm();
    });

    $("#plan-business-plus").click(function() {
        $(".plan").removeClass("selected");
        $("#plan-business-plus").addClass("selected");
        updateChangePlanForm();
    });

    function updateChangePlanForm() {
        var planId = $("#old-plan-id").val();

        // "Monthly" is selected: dispplay monthly prices
        if ($("#billing-monthly").is(":checked")) {
            var period = "monthly";
            $("#business-price").text("$20");
            $("#business-plus-price").text("$80");
        }

        // "Annual" is selected: dispplay annual prices
        if ($("#billing-annual").is(":checked")) {
            var period = "annual";
            $("#business-price").text("$16");
            $("#business-plus-price").text("$64");
        }

        // "Hobbyist" is selected, set planId
        if ($("#plan-hobbyist").hasClass("selected")) {
            planId = "";
        }

        // "Business" is selected, set planId
        if ($("#plan-business").hasClass("selected")) {
            planId = period == "monthly" ? "P20" : "Y192";
        }

        // "Business Plus" is selected, set planId
        if ($("#plan-business-plus").hasClass("selected")) {
            planId = period == "monthly" ? "P80" : "Y768";
        }
        
        if (planId == $("#old-plan-id").val()) {
            $("#change-plan-btn")
                .attr("disabled", "disabled")
                .text("Change Billing Plan");

        } else {
            var caption = "Change Billing Plan";
            if (planId) {
                var amount = planId.substr(1);
                caption += " And Pay $" + amount + " Now";
            }

            $("#change-plan-btn")
                .removeAttr("disabled")
                .text(caption)
                .attr("data-plan-id", planId);
        }
    }
    updateChangePlanForm();

});