import pandas as pd
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import Campaign, Recipient
from .forms import UploadRecipientsForm


def index(request):
    return render(request, 'bulk/index.html')


def upload_campaign(request):
    if request.method == "POST":
        form = UploadRecipientsForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data['title']
            subject = form.cleaned_data['subject']
            message_text = form.cleaned_data['message']
            file = form.cleaned_data['file']

            campaign = Campaign.objects.create(
                title=title,
                subject=subject,
                message=message_text
            )

            try:
                if file.name.endswith(".csv"):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
            except Exception as e:
                return HttpResponse(f"Error reading file: {e}")

            df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

            name_col = next((c for c in df.columns if "name" in c), None)
            email_col = next((c for c in df.columns if "email" in c), None)

            if not name_col or not email_col:
                return HttpResponse("File must contain both name and email columns.")

            for _, row in df.iterrows():
                full_name = str(row.get(name_col, "")).strip()
                email = str(row.get(email_col, "")).strip()
                if email:
                    Recipient.objects.create(
                        campaign=campaign,
                        name=full_name,
                        email=email
                    )

            messages.success(request, f"Campaign '{campaign.title}' created successfully!")
            return redirect('campaign_detail', campaign.id)
    else:
        form = UploadRecipientsForm()

    return render(request, 'bulk/upload_campaign.html', {'form': form})


def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    recipients = campaign.recipients.all()

    total = recipients.count()
    sent_count = recipients.filter(status='Sent').count()
    failed_count = recipients.filter(status='Failed').count()
    pending_count = recipients.filter(status='Pending').count()

    sent_pct = int((sent_count / total) * 100) if total else 0
    failed_pct = int((failed_count / total) * 100) if total else 0
    pending_pct = int((pending_count / total) * 100) if total else 0

    return render(request, 'bulk/campaign_detail.html', {
        'campaign': campaign,
        'recipients': recipients,
        'total': total,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'pending_count': pending_count,
        'sent_pct': sent_pct,
        'failed_pct': failed_pct,
        'pending_pct': pending_pct,
    })


def _send_emails_in_thread(campaign_id):
    """Run in a separate thread to send emails."""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    recipients = campaign.recipients.filter(status='Pending')

    for r in recipients:
        try:
            msg = campaign.message.replace("{{name}}", r.name or "there")
            send_mail(
                subject=campaign.subject,
                message=msg,
                from_email='bulkmailer@example.com',
                recipient_list=[r.email],
                fail_silently=False
            )
            r.status = "Sent"
            r.error_message = ""
            r.sent_at = timezone.now()
        except Exception as e:
            r.status = "Failed"
            r.error_message = str(e)
        finally:
            r.save()


@require_POST
def send_campaign(request, campaign_id):
    """Send campaign emails in background thread."""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    with transaction.atomic():
        # Reset failed emails to pending for retry
        campaign.recipients.filter(status='Failed').update(status='Pending', error_message='')

    thread = threading.Thread(target=_send_emails_in_thread, args=(campaign_id,))
    thread.start()
    return JsonResponse({"status": "started"})


def campaign_status_api(request, campaign_id):
    """Return live status of campaign."""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    recipients = campaign.recipients.all()

    return JsonResponse({
        "total": recipients.count(),
        "sent": recipients.filter(status='Sent').count(),
        "failed": recipients.filter(status='Failed').count(),
        "pending": recipients.filter(status='Pending').count(),
        "recipients": list(recipients.values('id', 'name', 'email', 'status'))
    })


def campaign_list(request):
    """Show all campaigns."""
    campaigns = Campaign.objects.all().order_by('-created_at')

    campaign_data = []
    for c in campaigns:
        recipients = c.recipients.all()
        campaign_data.append({
            'campaign': c,
            'total': recipients.count(),
            'sent': recipients.filter(status='Sent').count(),
            'failed': recipients.filter(status='Failed').count(),
            'pending': recipients.filter(status='Pending').count(),
        })

    return render(request, 'bulk/campaign_list.html', {'campaign_data': campaign_data})
