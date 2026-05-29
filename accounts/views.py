from django.shortcuts import render


def profile_page(request):
    return render(request, 'accounts/profile.html')

def login(request):
    pass