from django import forms

class UploadRecipientsForm(forms.Form):
    title = forms.CharField(max_length=255)
    subject = forms.CharField(max_length=255)
    message = forms.CharField(widget=forms.Textarea)
    file = forms.FileField()
