from django.db import models


class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    tipo_documento = models.CharField(max_length=20, blank=True)
    num_documento = models.CharField(max_length=20, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=100, blank=True)
    direccion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clientes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
