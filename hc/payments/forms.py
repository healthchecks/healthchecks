from django import forms


class BillToForm(forms.Form):
    bill_to = forms.CharField(max_length=500, required=False)
