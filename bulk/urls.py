from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_campaign, name='upload_campaign'),
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaign/<int:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('send-campaign/<int:campaign_id>/', views.send_campaign, name='send_campaign_emails'),
]
