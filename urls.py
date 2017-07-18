from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^p(?P<person_id>[0-9]+)/$', views.detail, name='detail'),
    url(r'^m(?P<marriage_id>[0-9]+)/$', views.mDetail, name='mDetail'),
    url(r'^list/$', views.listjson, name='listjson')
]
