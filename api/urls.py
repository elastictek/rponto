from django.urls import re_path, include
from django.contrib import admin
from api import rponto 

app_name="api" 

urlpatterns = [
    
   re_path(r'^rponto/sql/$',rponto.Sql),
   re_path(r'^rponto/sync/$',rponto.Sync)
]