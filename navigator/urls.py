from django.conf.urls import url

from . import views

urlpatterns = [
     url(r'^$', views.index, name='index'),
     url(r'^search/(?P<object_name>.+)$', views.search_name),
     url(r'update_session', views.update_session),
     url(r'^(?P<object_id>\d+)/$', views.detail, name='detail'),
     url(r'^(?P<objectid>\d+)/finder$', views.finder, name='finder'),
]
