from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario, Empresa, Almacen, UsuarioAlmacen


class PerfilInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name = 'Perfil TRUX'


class UsuarioAlmacenInline(admin.TabularInline):
    model = UsuarioAlmacen
    extra = 1


class CustomUserAdmin(UserAdmin):
    inlines = [PerfilInline, UsuarioAlmacenInline]
    list_display = ('username', 'get_full_name', 'email', 'get_rol', 'is_active')

    def get_rol(self, obj):
        return obj.rol
    get_rol.short_description = 'Rol'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ruc', 'telefono')


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    inlines = [UsuarioAlmacenInline]
