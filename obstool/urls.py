"""obstool URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.urls import include, re_path
from django.contrib import admin
from django.views.generic.base import TemplateView
from django.conf.urls.static import static
from .settings import MEDIA_ROOT,SITE_ROOT,BOKEH_JS
#import navigator.urls

urlpatterns = [
    re_path(r'^index.html$', TemplateView.as_view(template_name='main.html')),
    re_path(r'^$', TemplateView.as_view(template_name='main.html')),
    re_path(r'^navigator/', include('navigator.urls')),
    re_path(r'^admin/', admin.site.urls),
#    url(r'^media/js/bokeh/(?P<path>.*)$', serve, {'document_root':BOKEH_JS}),
#    url(r'^media/css/bokeh/(?P<path>.*)$', serve, {'document_root':BOKEH_CSS}),
#    url(r'^media/(?P<path>.*)$', serve, {'document_root':MEDIA_ROOT}),
#    url(r'(?P<path>.*)$', serve, {'document_root':SITE_ROOT}),
]
urlpatterns += static("/media/js/bokeh/", document_root=BOKEH_JS)
#urlpatterns += static("/media/css/bokeh/", document_root=BOKEH_CSS)
urlpatterns += static("/media/", document_root=MEDIA_ROOT)
#urlpatterns += static("/", document_root=SITE_ROOT)
