from django import forms
from django.contrib.auth import get_user_model, authenticate

from accounts.models import CustomerProfile, Role, UserSettings

User = get_user_model()


class LoginForm(forms.Form):
    username = forms.CharField(label='Логин')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned_data = super().clean()
        user = authenticate(
            username=cleaned_data.get('username'),
            password=cleaned_data.get('password'),
        )
        if not user:
            raise forms.ValidationError('Неверный логин или пароль.')
        self.user = user
        return cleaned_data


class RegisterForm(forms.Form):
    username = forms.CharField(label='Логин', max_length=150)
    email = forms.EmailField(label='Email')
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повтор пароля', widget=forms.PasswordInput)

    full_name = forms.CharField(label='ФИО', max_length=255)
    phone = forms.CharField(label='Телефон', max_length=32)
    address = forms.CharField(label='Адрес доставки', widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            base_class = 'form-control'
            if name in {'address'}:
                field.widget.attrs.setdefault('rows', 3)
            field.widget.attrs.setdefault('class', base_class)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Такой логин уже занят.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Такой email уже зарегистрирован.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Пароли не совпадают.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('Пароль должен быть не короче 8 символов.')
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        role_customer = Role.objects.get(code='CUSTOMER')

        user = User(
            username=data['username'],
            email=data['email'],
            role=role_customer,
        )
        user.set_password(data['password1'])
        user.save()

        CustomerProfile.objects.create(
            user=user,
            full_name=data['full_name'],
            phone=data['phone'],
            default_address=data.get('address', ''),
        )

        UserSettings.objects.get_or_create(
            user=user,
            defaults={
                'theme': UserSettings.Theme.LIGHT,
                'language': 'ru',
                'date_format': UserSettings.DateFormat.DMY,
                'page_size': UserSettings.PageSize.MEDIUM,
            },
        )

        return user


class UserSettingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-select' if name in {'theme', 'language', 'date_format', 'page_size'} else 'form-control')

    class Meta:
        model = UserSettings
        fields = ['theme', 'language', 'date_format', 'page_size']
