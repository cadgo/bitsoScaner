from django import forms
form .models import BitsoAcount

class BitsoAccountForms(forms.ModelForm):
    bitsosecret = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = BitsoAcount

        fields = ['bitsomail', 'bitsokey', 'bitsosecret']
