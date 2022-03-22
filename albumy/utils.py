import os
import uuid
from PIL import Image

from urllib.parse import urljoin, urlparse
from flask import request, redirect, url_for, flash, current_app
from itsdangerous import TimedSerializer as Serializer
from itsdangerous import BadSignature, SignatureExpired

from albumy.extensions import db
from albumy.models import User
from albumy.settings import Operations


def generate_token(user, operation, expire_in=None, **kwargs):
    """生成用于邮箱验证的JWT（json web token）"""
    s = Serializer(current_app.config['SECRET_KEY'], expire_in)

    # 待签名的数据负载
    data = {'id': user.id, 'operation': operation}
    data.update(**kwargs)
    return s.dumps(data)


def validate_token(user, token, operation, new_password=None):
    """用于验证用户注册和用户修改密码或邮箱的token, 并完成相应的确认操作"""
    s = Serializer(current_app.config['SECRET_KEY'])

    try:
        data = s.loads(token)
    except (SignatureExpired, BadSignature):
        return False

    if operation != data.get('operation') or user.id != data.get('id'):
        return False

    if operation == Operations.CONFIRM:  # 用户认证
        user.confirmed = True
    elif operation == Operations.RESET_PASSWORD:  # 重置密码
        user.set_password(new_password)
    elif operation == Operations.CHANGE_EMAIL:  # 变更邮箱
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if User.query.filter_by(email=new_email).first() is not None:
            return False
        user.email = new_email
    else:
        return False

    db.session.commit()
    return True


def rename_image(old_filename):
    ext = os.path.splitext(old_filename)[1]
    new_filename = uuid.uuid4().hex + ext
    return new_filename


def resize_image(image, filename, base_width):
    """为用户上传的图片生成缩略图， base_width表示缩略图的宽"""
    filename, ext = os.path.splitext(filename)
    img = Image.open(image)
    if img.size[0] <= base_width:
        return filename + ext  # 对于小图，不做处理
    w_percent = base_width / float(img.size[0])  # 宽的缩略比
    h_size = int(float(img.size[1]) * float(w_percent))  # 对高做同样比例的计算
    img = img.resize((base_width, h_size), Image.ANTIALIAS)  # 使用抗锯齿缩放

    filename += current_app.config['ALBUMY_PHOTO_SUFFIX'][base_width] + ext
    img.save(os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename),
             optimize=True, quality=85)
    return filename


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def redirect_back(default='main.index', **kwargs):
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return redirect(target)
    return redirect(url_for(default, **kwargs))


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash('Error in the %s field - %s' % (
                getattr(form, field).label.text,
                error
            ))
