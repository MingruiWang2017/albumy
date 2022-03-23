from flask_avatars import Avatars
from flask_bootstrap import Bootstrap4
from flask_dropzone import Dropzone
from flask_login import LoginManager, AnonymousUserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_moment import Moment
from flask_wtf import CSRFProtect

avatars = Avatars()
bootstrap = Bootstrap4()
db = SQLAlchemy()
dropzone = Dropzone()
login_manager = LoginManager()
mail = Mail()
moment = Moment()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    """根据session中的user_id获取User对象"""
    from albumy.models import User
    user = User.query.get(int(user_id))
    return user


login_manager.login_view = 'auth.login'  # 未登录用户跳转的登录视图
login_manager.login_message = '请登录后执行操作'  # 未登录用户接收的提示信息
login_manager.login_message_category = 'waring'  # 提示信息的分类


class Guest(AnonymousUserMixin):
    """继承匿名用户类，即访客
    当用户未登录时，current_user就会返回该类，
    我们为该类提供和User类相同的属性和方法，确保使用的一致性"""

    def can(self, permission_name):
        return False

    @property
    def is_admin(self):
        return False


login_manager.anonymous_user = Guest  # 说明匿名用户使用Guest类
