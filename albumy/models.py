import os
from datetime import datetime

from flask import current_app
from flask_avatars import Identicon
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


class Collect(db.Model):
    """关系模型，在User和Photo之间建一个收藏关系，它类似于关系表，但是可以储存额外字段，是一个中介"""
    # 收藏者id
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # 收藏的photo
    collected_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系属性：收藏者和被收藏的图片, 使用lazy=joined进行预加载，对关系两侧的表进行联结操作，
    # 最终获得的记录会包含已经预加载的collector和collected对象
    collector = db.relationship('User', back_populates='collections', lazy='joined')
    collected = db.relationship('Photo', back_populates='collectors', lazy='joined')


class Follow(db.Model):
    """自引用的多对多关系模型，关注者和被关注者都是User, 这里设置了两个主键"""
    # 关注者（关注我的人）
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    # 被关注者（我关注的人）
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系属性：这两个字段定义的外键都指向user.id，在建立反向关系时，SQLAlchemy无法判断哪个外键对应哪个关系属性，
    # 所以需要使用foreign_keys参数来明确对应的字段。这会导致在查询时无法通过with_parent()方法进行筛选，但是可以直接使用
    # follower和followed属性获取对应的用户对象。
    # 关注我的人
    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='following', lazy='joined')
    # 我关注的人
    followed = db.relationship('User', foreign_keys=[followed_id], back_populates='followers', lazy='joined')


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
    # 3种不同尺寸的头像
    avatar_s = db.Column(db.String(64))
    avatar_m = db.Column(db.String(64))
    avatar_l = db.Column(db.String(64))

    confirmed = db.Column(db.Boolean, default=False, comment='用户是否已通过邮箱验证')

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', back_populates='users')

    photos = db.relationship('Photo', back_populates='author', cascade='all')
    comments = db.relationship('Comment', back_populates='author', cascade='all')
    notifications = db.relationship('Notification', back_populates='receiver', cascade='all')
    collections = db.relationship('Collect', back_populates='collector', cascade='all')
    following = db.relationship('Follow', foreign_keys=[Follow.follwer_id], back_populates='follower',
                                lazy='dynamic', cascade='all')  # 我正在关注的人
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], back_populates='followed',
                                lazy='dynamic', cascade='all')  # 关注我的人

    def __init__(self, **kwargs):
        """初始化用户对象时自动添加默认的User角色"""
        super(User, self).__init__(**kwargs)
        self.generate_avatar()
        self.set_role()

    def set_role(self):
        """设置默认角色"""
        if self.role is None:
            if self.email == current_app.config['ALBUMY_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='Administrator').first()
            else:
                self.role = Role.query.filter_by(name='User').first()
            db.session.commit()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        """关注用户user"""
        if not self.is_following(user):
            follow = Follow(follower=self, followed=user)
            db.session.add(follow)
            db.session.commit()

    def unfollow(self, user):
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
            db.session.commit()

    def is_following(self, user):
        if user.id is None:  # 用户默认对自己进行关注，当关注自己时， 数据还没写入数据库，查不到user.id，所以直接返回False
            return False
        return self.following.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def collect(self, photo):
        if not self.is_collecting(photo):
            collect = Collect(collector=self, collected=photo)
            db.session.add(collect)
            db.session.commit()

    def uncollect(self, photo):
        collect = Collect.query.with_parent(self).filter_by(collected_id=photo.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    def is_collecting(self, photo):
        """判断当前图片是否已经被收藏"""
        return Collect.query.with_parent(self).filter_by(collected_id=photo.id).first() is not None

    def generate_avatar(self):
        avatar = Identicon()
        # 生成三种尺寸的头像保存到AVATARS_SAVE_PATH，返回文件名
        filenames = avatar.generate(text=self.username)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]
        db.session.commit()

    @property
    def is_admin(self):
        """判断用户是否为管理员"""
        return self.role.name == 'Administrator'

    def can(self, permission_name):
        """判断用户是否具有某项权限"""
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission and self.role and permission in self.role.permissions


# photo与tag之间的多对多关系表
tagging = db.Table('tagging',
                   db.Column('photo_id', db.Integer, db.ForeignKey('photo.id')),
                   db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')))


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500))
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64), comment='小尺寸缩略图文件名，400px')
    filename_m = db.Column(db.String(64), comment='中等尺寸缩略图文件名，800px')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    can_comment = db.Column(db.Boolean, default=True, comment='图片能否评论')
    flag = db.Column(db.Integer, default=0, comment='图片被举报次数计数器')
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    author = db.relationship('User', back_populatest='photos')
    comments = db.relationship('Comment', back_populates='photo', cascade='all')
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')
    tags = db.relationship('Tag', secondary=tagging, back_populates='photos')


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)

    photos = db.relationship('Photo', secondary=tagging, back_populates='tags')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    flag = db.Column(db.Integer, default=0, comment='评论被举报次数计数器')

    # 外键：被回复的评论的id, 本评论的用户id， 被评论的图片的id
    replied_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    # 关系属性: 被评论的图片，评论用户，本评论的回复，被本条评论回复的评论
    photo = db.relationship('Photo', back_populates='comments')
    author = db.relationship('User', back_populates='comments')
    replies = db.relationship('Comment', back_populates='replied', cascade='all')
    replied = db.relationship('Comment', back_populates='replies', remote_sid=[id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    receiver = db.relationship('User', back_populates='notifications')


@db.event.listens_for(Photo, 'after_delete', named=True)
def delete_photo(**kwargs):
    """监听数据库事件，当Photo模型中记录被删除时，到图片目录下删除对应文件"""
    target = kwargs['target']  # 获取photo对象
    for filename in [target.filename, target.filename_s, target.filename_m]:
        path = os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename)
        if os.path.exists(path):  # 验证文件是否存在，因为小图片不会生成缩略图
            os.remove(path)
