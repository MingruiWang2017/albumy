from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms import ValidationError
from wtforms.validators import DataRequired, Length, Email

from albumy.forms.user import EditProfileForm
from albumy.models import User, Role


class EditProfileAdminForm(EditProfileForm):
    """管理员的用户管理表单"""
    email = StringField('Email', validators=[DataRequired(), Length(1, 254), Email()])
    role = SelectField('Role', coerce=int)
    active = BooleanField('Active')
    confirmed = BooleanField('Confirmed')
    submit = SubmitField()

    def __init__(self, user, *args, **kwargs):  # 需要传入被管理的用户作为参数
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        # role的下拉选项
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_username(self, field):
        """用户名唯一性验证器"""
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('The username is already in use.')

    def validate_email(self, field):
        """邮箱唯一性验证器"""
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('The email is already in use.')
