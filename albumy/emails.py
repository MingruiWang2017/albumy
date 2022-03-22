from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from albumy.extensions import mail


def _send_async_mail(app, message):
    with app.app_context():
        mail.send(message)


def send_mail(to, subject, template, **kwargs):
    message = Message(current_app.config['ALBUMY_MAIL_SUBJECT_PREFIX'] + subject,
                      recipients=[to])
    # 纯文本
    message.body = render_template(template + '.txt', **kwargs)
    # html
    message.html = render_template(template + '.html', **kwargs)
    app = current_app._get_current_object()
    thr = Thread(target=_send_async_mail, args=[app, message])
    thr.start()
    return thr


def send_confirm_email(user, token, to=None):
    send_mail(to=to or user.email, subject='Email Configrm', template='emails/confirm',
              user=user, token=token)


def send_reset_password_email(user, token):
    send_mail(to=user.email, subject='Password Reset', template='emails/reset_password',
              user=user, token=token)
