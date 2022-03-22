from flask_bootstrap import Bootstrap4
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_moment import Moment

bootstrap = Bootstrap4()
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
moment = Moment()


@login_manager.user_loader
def load_user(user_id):
    """根据session中的user_id获取User对象"""
    from albumy.models import User
    user = User.query.get(int(user_id))
    return user


login_manager.login_view = 'auth.login'  # 未登录用户跳转的登录视图
login_manager.login_message = '请登录后执行操作'  # 未登录用户接收的提示信息
login_manager.login_message_category = 'waring'  # 提示信息的分类
