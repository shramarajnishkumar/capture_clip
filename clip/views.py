from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse, HttpResponseRedirect
from .models import User, VideoDetails, CaptureClip
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.conf import settings
from .utils import Util, download_video, copy_audio_video_clip, transcribe_audio
from django.contrib import messages, auth
import jwt
from googleapiclient.discovery import build
from urllib.parse import urlparse
import cv2, json
import numpy as np



class Login(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'login.html')
    
    def post(self, request):
        try:
            email = request.POST.get("email")
            password = request.POST.get("password")
            user = auth.authenticate(email=email, password=password)
            # user = User.objects.get(email=email)
            if user:
                auth.login(request, user)
                messages.success(request, "Login Successfully" )
                return redirect('home')
            else:
                messages.success(request, "Somthing Went Wrong!, Please try Again!" )
                return redirect("login")
        except Exception as e:
            messages.success(request, f"error: {e}" )
            return redirect("login")
    
class SignUp(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'signup.html')
    
    def post(self, request):
        try:
            email = request.POST.get("email")
            print('email: ', email)
            password = request.POST.get("password")
            print('password: ', password)
            repassword = request.POST.get("repassword")
            print('repassword: ', repassword)
            if password == repassword:
                user = User(email=email, username =email)
                user.set_password(password)
                user.save()
                print('user: ', user)
                token = RefreshToken.for_user(user).access_token
                print('token: ', token)
                current_site = get_current_site(request).domain
                relativeLink = reverse('email-verify')
                absurl = 'http://'+current_site+relativeLink+"?token="+str(token)
                email_body = 'Hi '+user.username + \
                ' Use the link below to verify your email \n' + absurl
                data = {'email_body': email_body, 'to_email': user.email,
                    'email_subject': 'Verify your email'}
                Util.send_email(data)
                messages.success(request, "Please check your email and verify your accounts" )
            return HttpResponseRedirect("/login")
        except Exception as e:
            messages.error(request, f"error: {e}" )
            return HttpResponseRedirect("/signup")

class VerifyEmail(View):

    def get(self, request):
        token = request.GET.get('token')
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            user = User.objects.get(id=payload['user_id'])
            if not user.is_verified:
                user.is_verified = True
                user.save()
                messages.success(request, "Successfully activated" )
            else:
                messages.success(request, "Already activated" )
            return redirect("login")
        except Exception as identifier:
            messages.success(request, f"error: {identifier}" )
            return redirect("login")
    
class Logout(View):
    def get(self, request):
        auth.logout(request)
        return redirect('login')

class Home(View):
    def get(self, request):
        return render(request, "home.html")
    
    def post(self, request):
        print('request.user: ', request.user)
        context = {}
        if not request.user.is_authenticated:
            messages.success(request, "Please Login First!" )
            return redirect('home')
        youtube_url = request.POST.get("youtube_url")
        parsed_url = urlparse(youtube_url)
        video_id = parsed_url.query.split("=")[1]

        video_details = VideoDetails.objects.filter(video_id=video_id)
        if video_details.exists():
            video_details = video_details.first()
        else:
            youtube = build('youtube', 'v3', developerKey=settings.GOOGLE_API_KEY)
            youtube_request = youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            )
            response = youtube_request.execute()
            if 'items' in response and len(response['items']) > 0:
                video = response['items'][0]
                title = video['snippet']['title']
            download_video_path = download_video(youtube_url, video_id)
            video_details = VideoDetails.objects.create(
                user = request.user,
                video_id = video_id,
                video_title = title,
                video_url = youtube_url,
                download_video = download_video_path
            )

        context['video'] = video_details
        return render(request, "home.html", context)
    
    def put(self, request):
        return HttpResponse("This is a PUT request")
    
    def delete(self, request):
        return HttpResponse("This is a DELETE request")
    


class CaptureClipView(View):
    
    def get(self, request):

        try:
            video_id = request.GET.get("video_id")
            start_time = request.GET.get("start_time")
            end_time = request.GET.get("end_time")
            saveAudioValue = True if request.GET.get("saveAudioValue") == 'on' else False
            print('saveAudioValue: ', saveAudioValue)
            selectedValues = json.loads(request.GET.get("selectedValues"))
            print('selectedValues: ', type(selectedValues))

            video_details= VideoDetails.objects.filter(video_id=video_id)
            print('video_details: ', video_details)
            audio_clip = None
            video_clip = None
            host_url = request.build_absolute_uri('/')
            if video_details.exists():
                video_details = video_details.first()
                video_path_url = video_details.download_video.url
                print("=============", video_details.download_video)

                data = copy_audio_video_clip(f"{host_url}"+video_path_url, start_time, end_time, is_audio=saveAudioValue)
                video_clip = data.get('video_clip')
                audio_clip = data.get('audio_clip')
            print('video_clip: ', video_clip)
            print('audio_clip: ', audio_clip)

            transcripts_text = None
            if audio_clip:
                transcripts_text = transcribe_audio(f"{settings.MEDIA_ROOT}{audio_clip}")
                print('transcripts_text: ', transcripts_text)
            
            capture_clip = CaptureClip.objects.create(
                video_details = video_details,
                video_clip = video_clip,
                audio_clip=audio_clip,
                transcription=transcripts_text,
                labels = selectedValues
            )
            print('capture_clip: ', capture_clip)
            emailClipValue = True if request.GET.get("emailClipValue") == 'on' else False
            emailOptionValue = request.GET.get("emailOptionValue")
            print('emailOptionValue: ', emailOptionValue)

            print('emailClipValue: ', emailClipValue)
            if emailClipValue and emailOptionValue == "single_clip":
                audio_clip = host_url+capture_clip.audio_clip.url
                video_clip = host_url+capture_clip.video_clip.url
                email_body = 'Hi '+request.user.username + \
                ' Use the link below to verify your email \n audio_clip: ' + audio_clip + '\n video_clip: '+video_clip
                data = {'email_body': email_body, 'to_email': request.user.email,
                    'email_subject': 'Your YouTube Clip links'}
                Util.send_email(data)
            return HttpResponse("Clip has been Capture!")
        except Exception as identifier:
            return HttpResponse(f"{identifier}")
        

class Journal(View):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                messages.success(request, "Please Login First!" )
                return redirect('login')
            
            user = request.user
            host_url = request.build_absolute_uri('/')

            video_details = VideoDetails.objects.filter(user=user)
            combined_data = []
            for video_detail in video_details:
                capture_clips = CaptureClip.objects.filter(video_details=video_detail)
                for capture_clip in capture_clips:
                    combined_data.append({
                        'video_title': capture_clip.video_details.video_title,  # Assuming `title` is the field name in VideoDetails model
                        'clip_date': capture_clip.created_at,  # This will be a queryset of CaptureClip instances
                        'youtube_link': capture_clip.video_details.video_url,
                        'transcription': capture_clip.transcription,
                        'audio_clip': f"{host_url}{capture_clip.audio_clip.url}",
                        'video_clip': capture_clip.video_clip,
                        'labels': capture_clip.labels
                    })
            return render(request, 'journal.html', {"capture_clip":combined_data})
        except Exception as identifier:
            return render(request, 'journal.html', {'error': str(identifier)})
        
    


