from django.contrib import admin
from . import models

# Register your models here.

admin.site.register(models.Gateway)
admin.site.register(models.Configuration)
