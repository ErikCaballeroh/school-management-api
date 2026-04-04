from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'nombre', 'rol',
                    'matricula', 'activo', 'is_staff')
    list_filter = ('rol', 'activo', 'is_staff', 'is_superuser')
    search_fields = ('email', 'nombre', 'matricula')

    def save_model(self, request, obj, form, change):
        if obj.pk:
            # Si el usuario ya existe y se cambió la contraseña
            orig_obj = User.objects.get(pk=obj.pk)
            if obj.password != orig_obj.password:
                obj.set_password(obj.password)
        else:
            # Si es un usuario nuevo, encripta la contraseña
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)
