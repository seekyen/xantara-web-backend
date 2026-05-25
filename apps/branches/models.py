from django.db import models

class Branch(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    address    = models.TextField(blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    email      = models.EmailField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
