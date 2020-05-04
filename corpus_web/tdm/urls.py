from django.urls import path, include
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from . import views

app_name = 'tdm'
urlpatterns = [
	path('', views.index, name='index'),
	path('scrape', views.scrape, name='scrape'),
	path('search', views.search, name='search'),
	path('xas_classification', views.xas_classification, name='xas_classification'),
	path('xas_page', views.xas_page, name='xas_page'),
	path('xas_page/<int:year>', views.xas_page, name='xas_page'),
	#path('xas_page', views.xas_page, {'foo': 'bar'}, name='xas_page'),
	#url(r'^xas_page/', include(('xas_page.urls','xas_page'),namespace='xas_page')),
	#url(r'^xas_page/(?P<var>\w+)', views.xas_page, name='xas_page'),
	
	#url(r'^xas_page/(?P<fig_file>\w+)/$', views.xas_page, name='xas_page'),
	#url(r'^xas_page/', include(('xas_page.urls', 'xas_page'), namespace='xas_page')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
