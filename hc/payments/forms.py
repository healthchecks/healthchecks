from django import forms
from hc.accounts.forms import LowercaseEmailField


class InvoiceEmailingForm(forms.Form):
    send_invoices = forms.IntegerField(min_value=0, max_value=2)
    invoice_email = LowercaseEmailField(required=False)

    def update_subscription(self, sub):
        sub.send_invoices = self.cleaned_data["send_invoices"] > 0
        if self.cleaned_data["send_invoices"] == 2:
            sub.invoice_email = self.cleaned_data["invoice_email"]
        else:
            sub.invoice_email = ""

        sub.save()
