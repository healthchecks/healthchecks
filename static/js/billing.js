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

        $("#plan-id").val(planId);

        if (planId == $("#old-plan-id").val()) {
            $("#change-plan-btn")
                .attr("disabled", "disabled")
                .text("Change Billing Plan");

        } else {
            var caption = "Change Billing Plan";
            if (planId) {
                caption += " And Pay $" + planId.substr(1) + " Now";
            }

            $("#change-plan-btn").removeAttr("disabled").text(caption);
        }
    }
    updateChangePlanForm();

});