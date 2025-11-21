from django.urls import path
from . import views
from django.views import View
from django.shortcuts import render

class index(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'common.html')

index = index.as_view()