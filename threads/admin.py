from django.contrib import admin
from .models import Thread, Message, Attachment

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "created_at")

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "author", "created_at", "is_system")
    inlines = [AttachmentInline]

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("message", "name", "file")
