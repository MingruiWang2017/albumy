from functools import wraps

from flask import Markup, flash, url_for, redirect, abort
from flask_login import current_user


def confirm_required(func):
    """该装饰器用户引导用户执行邮箱确认，否则对应操作无法执行"""

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.confirmed:
            message = Markup(  # Markup用来不对其中的html元素转义，正确显示其格式
                'Please confirm your account first.'
                'Not receive the email?'
                '<a class="alert-link" href="%s">Resent Confirm Email</a>' %
                url_for('auth.resend_confirm_email'))
            flash(message, 'warning')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)

    return decorated_function
