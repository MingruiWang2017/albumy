from datetime import datetime

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from albumy.extensions import db

# 关系表：Role和Permission之间是多对多关系，使用关系表建立联系
roles_permissions = db.Table('roles_permissions',
                             db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
                             db.Column('permission_id', db.Integer, db.ForeignKey('permission.id')))


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    roles = db.relationship('Role', secondary=roles_permissions, back_populates='permissions')


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    users = db.relationship('User', back_populates='role')  # role与user是一对多关系
    permissions = db.relationship('Permission', secondary=roles_permissions, back_populates='roles')

    @staticmethod
    def init_role():
        """初始化与设定的角色与权限关系"""
        roles_permissions_map = {
            # 被锁定的用户：因违规行为别锁定，只能关注其他用户和收藏图片
            'Locked': ['FOLLOW', 'COLLECT'],
            # 普通用户：默认角色，可以关注、收藏、评论和上传
            'User': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD'],
            # 协管员：除普通用户权限外还拥有管理网站内容的权限，负责网站内容的管理与维护
            'Moderator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE'],
            # 管理员：拥有所有权限
            'Administrator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE', 'ADMINISTER']
            # 另外还有访客和被封禁用户角色，他们只能浏览页面
        }

        for role_name in roles_permissions_map:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
            role.permissions = []  # 每次都先清空role和permission的关系，以便在预设表更改时更新关系
            for permission_name in roles_permissions_map[role_name]:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission is None:
                    permission = Permission(name=permission_name)
                    db.session.add(permission)
                role.permissions.append(permission)
        db.session.comit()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, index=True)
    email = db.Column(db.String(254), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(30))
    website = db.Column(db.String(255))
    bio = db.Column(db.String(120), comment='个人经历')
    location = db.Column(db.String(50))
    member_since = db.Column(db.DateTime, default=datetime.utcnow, comment='用户注册时间')

    confirmed = db.Column(db.Boolean, default=False, comment='用户是否已通过邮箱验证')

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', back_populates='users')

    photos = db.relationship('Photo', back_populates='author', cascade='all')

    def __init__(self, **kwargs):
        """初始化用户对象时自动添加默认的User角色"""
        super(User, self).__init__(**kwargs)
        self.set_role()

    def set_role(self):
        """设置默认角色"""
        if self.role is None:
            if self.email == current_app.conifg['ALBUMY_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='Administrator').first()
            else:
                self.role = Role.query.filter_by(name='User').first()
            db.session.commit()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """判断用户是否为管理员"""
        return self.role.name == 'Administrator'

    def can(self, permission_name):
        """判断用户是否具有某项权限"""
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission and self.role and permission in self.role.permissions


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500))
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64), comment='小尺寸缩略图文件名，400px')
    filename_m = db.Column(db.String(64), comment='中等尺寸缩略图文件名，800px')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    author = db.relationship('User', back_populatest='photos')