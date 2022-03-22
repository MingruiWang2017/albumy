import os
import random

from PIL import Image
from faker import Faker
from flask import current_app
from sqlalchemy.exc import IntegrityError

from albumy.extensions import db
from albumy.models import User, Photo

fake = Faker()


def fake_admin():
    admin = User(
        name='Jack Smith',
        username='Jack',
        email='Jack@example.com',
        bio=fake.sentence(),
        website='https://jack.com',
        confirmed=True)
    admin.set_password('helloflask')
    db.session.add(admin)
    db.session.commit()


def fake_user(count=10):
    for i in range(count):
        user = User(name=fake.name(),
                    confirmed=True,
                    username=fake.user_name(),
                    bio=fake.sentence(),
                    location=fake.city(),
                    website=fake.url(),
                    member_since=fake.date_this_decade(),
                    email=fake.email())
        user.set_password('123456')
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:  # 键重复错误--违反唯一性约束
            db.session.rollback()


def fake_photo(count=30):
    """生成纯色图片"""
    upload_path = current_app.config['ALBUMY_PHOTO_PATH']
    for i in range(count):
        print(i)

        filename = 'random_%d.jpg' % i
        r = lambda: random.randint(128, 255)
        img = Image.new(mode='RGB', size=(800, 800), color=(r(), r(), r()))
        img.save(os.path.join(upload_path, filename))

        photo = Photo(
            description=fake.text(),
            filename=filename,
            filename_m=filename + '_m',
            filename_s=filename + '_s',
            author=User.query.get(random.randint(1, User.query.count())),
            timestamp=fake.date_time_this_year()
        )
        db.session.add(photo)
    db.session.commit()
