from django.contrib.auth.models import User
from django.db import models


ROL_CHOICES = [
    ('admin', 'Administrador'),
    ('supervisor', 'Supervisor'),
    ('vendedor', 'Vendedor'),
    ('almacenero', 'Almacenero'),
    ('cliente', 'Cliente'),
]


class PerfilUsuario(models.Model):
    """Extiende auth_user de Django con los campos del negocio."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='vendedor')
    telefono = models.CharField(max_length=20, blank=True)
    dni = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'perfil_usuarios'
        verbose_name = 'Perfil de usuario'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.get_rol_display()})'

    @property
    def es_admin(self):
        return self.rol == 'admin'

    @property
    def es_vendedor(self):
        return self.rol in ('admin', 'supervisor', 'vendedor')

    @property
    def es_almacenero(self):
        return self.rol in ('admin', 'supervisor', 'almacenero')


# Accessor conveniente: user.rol, user.es_admin, etc.
def _rol(self):
    return getattr(self, 'perfil', None) and self.perfil.rol or 'vendedor'

def _get_rol_display(self):
    return dict(ROL_CHOICES).get(self.rol, self.rol)

def _es_admin(self):
    return self.rol == 'admin'

def _es_vendedor(self):
    return self.rol in ('admin', 'supervisor', 'vendedor')

User.add_to_class('rol', property(_rol))
User.add_to_class('get_rol_display', _get_rol_display)
User.add_to_class('es_admin', property(_es_admin))
User.add_to_class('es_vendedor', property(_es_vendedor))


class Empresa(models.Model):
    nombre = models.CharField(max_length=200)
    ruc = models.CharField(max_length=11, blank=True)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='empresa/', null=True, blank=True)

    class Meta:
        db_table = 'empresa'
        verbose_name = 'Empresa'

    def __str__(self):
        return self.nombre


class Almacen(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'almacenes'
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'

    def __str__(self):
        return self.nombre


class UsuarioAlmacen(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE)
    es_principal = models.BooleanField(default=False)

    class Meta:
        db_table = 'usuario_almacenes'
        unique_together = ('usuario', 'almacen')


class ChatConversacion(models.Model):
    ESTADO_CHOICES = [('activa', 'Activa'), ('cerrada', 'Cerrada')]
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='usuario_id')
    tipo_usuario = models.CharField(max_length=20, default='vendedor')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    calificacion = models.IntegerField(null=True, blank=True)
    comentario_calificacion = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')
    actualizado_en = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'chat_conversaciones'
        ordering = ['-creado_en']

    def __str__(self):
        return f'Conversación #{self.id} — {self.usuario}'


class ChatMensaje(models.Model):
    ROL_CHOICES = [('user', 'Usuario'), ('assistant', 'Asistente')]
    conversacion = models.ForeignKey(ChatConversacion, on_delete=models.CASCADE, related_name='mensajes')
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    contenido = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'chat_mensajes'
        ordering = ['creado_en']

    def __str__(self):
        return f'{self.rol}: {self.contenido[:50]}'


class RespuestaPredefinida(models.Model):
    pregunta = models.CharField(max_length=200)
    respuesta = models.TextField()
    tipo_usuario = models.CharField(max_length=20, default='vendedor')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'respuestas_predefinidas'

    def __str__(self):
        return self.pregunta


class PalabraProhibida(models.Model):
    palabra = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'palabras_prohibidas_chat'

    def __str__(self):
        return self.palabra
