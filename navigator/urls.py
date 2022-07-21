from django.urls import re_path
from . import views

urlpatterns = [
     re_path(r'^$', views.index, name='index'),
     re_path(r'^add_object$', views.add_object, name='index'),
     re_path(r'^skymap$', views.mapview),
     re_path(r'^search/(?P<object_name>.+)$', views.search_name),
     re_path(r'update_session', views.update_session),
     re_path(r'update_rating', views.update_rating),
     re_path(r'^(?P<object_id>\d+)/$', views.detail, name='detail'),
     re_path(r'^(?P<object_id>\d+)/(?P<view>basic)$',views.detail,name='basic'),
     re_path(r'^(?P<objectid>\d+)/finder$', views.finder, name='finder'),
]
