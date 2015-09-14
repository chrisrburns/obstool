from django.conf.urls import url

from . import views

urlpatterns = [
     url(r'^$', views.index, name='index'),
     #(r'^$', 'django.views.generic.list_detail.object_list', info_dict),
     #(r'^(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', info_dict),
     url(r'^(?P<object_id>\d+)/$', views.detail, name='detail'),
     url(r'^(?P<objectid>\d+)/finder$', views.finder, name='finder'),
     #(r'^(?P<objectid>\d+)/amplot$', 'objects.views.airmassplot'),
]
