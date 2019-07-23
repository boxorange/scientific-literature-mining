from django.urls import path
from . import views

app_name = 'tdm'
urlpatterns = [
	path('', views.index, name='index'),
	path('scrape', views.scrape, name='scrape'),
	path('search', views.search, name='search'),
	path('xas_classification', views.xas_classification, name='xas_classification')
]
