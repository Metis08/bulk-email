from django.db import models
from django.utils import timezone

class Campaign(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    progress = models.IntegerField(default=0)
    total = models.IntegerField(default=0)

    def __str__(self):
        return self.title


class Recipient(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Sent', 'Sent'),
        ('Failed', 'Failed')
    ]

    campaign = models.ForeignKey(Campaign, related_name='recipients', on_delete=models.CASCADE)
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.email})"
