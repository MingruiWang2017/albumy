from flask import Blueprint, render_template, jsonify
from flask_login import current_user

from albumy.models import User, Notification, Photo
from albumy.notifications import push_collect_notification, push_follow_notification

ajax_bp = Blueprint('ajax', __name__)


@ajax_bp.route('/notifications-count')
def notification_count():
    """查询当前用户的未读消息数量"""
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403

    count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
    return jsonify(count=count)


@ajax_bp.route('/profile/<int:user_id>')
def get_profile(user_id):
    """通过ajax方式提供用户信息"""
    user = User.query.get_or_404(user_id)
    return render_template('main/profile_popup.html', user=user)


@ajax_bp.route('/followers-count/<int:user_id>')
def followers_count(user_id):
    """查询用户的关注者数量，其中需要减去自己"""
    user = User.query.get_or_404(user_id)
    count = user.followers.count() - 1  # minus user self
    return jsonify(count=count)


# 为ajax请求单独创建关注和取消关注的视图，
# 这里不能使用装饰器返回渲染整个页面的结果，不能通过flash（）发送提示，
# 所以各种情况的错误要自行判断，错误信息需要放在json中返回
@ajax_bp.route('/follow/<username>', methods=['POST'])
def follow(username):
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403
    if not current_user.confirmed:
        return jsonify(message='Confirm account required.'), 400
    if not current_user.can('FOLLOW'):
        return jsonify(message='No permission.'), 403

    user = User.query.filter_by(username=username).first_or_404()
    if current_user.if_following(user):
        return jsonify(message='Already followed.'), 400

    current_user.follow(user)
    if user.receive_follow_notification:
        push_follow_notification(follower=current_user, receiver=user)  # 推送关注消息
    return jsonify(message='User followed.')


@ajax_bp.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403

    user = User.query.filter_by(username=username).first_or_404()
    if not current_user.is_following(user):
        return jsonify(message='Not follow yet.'), 400

    current_user.unfollow(user)
    return jsonify(message='Follow canceled.')


@ajax_bp.route('/<int:photo_id>/collectors-count')
def collectors_count(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    count = len(photo.collectors)
    return jsonify(count=count)


@ajax_bp.route('/collect/<int:photo_id>', methods=['GET', 'POST'])
def collect(photo_id):
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403
    if not current_user.confirmed:
        return jsonify(message='Confirm account required.'), 400
    if not current_user.can('COLLECT'):
        return jsonify(message='No permission.'), 403

    photo = Photo.query.get_or_404(photo_id)
    if current_user.is_collecting(photo):
        return jsonify(message='Already collected.'), 400

    current_user.collect(photo)
    if current_user != photo.author and photo.author.receive_collect_notification:
        push_collect_notification(collector=current_user, photo_id=photo_id, receiver=photo.author)
    return jsonify(message='Photo collected.')


@ajax_bp.route('/uncollect/<int:photo_id>', methods=['POST'])
def uncollect(photo_id):
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403

    photo = Photo.query.get_or_404(photo_id)
    if not current_user.is_collecting(photo):
        return jsonify(message='Not collect yet.'), 400

    current_user.uncollect(photo)
    return jsonify(message='Collect canceled.')
