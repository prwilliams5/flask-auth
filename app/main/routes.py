from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, current_app, g
from flask_login import current_user, login_required
from app import db
from app.main.forms import EditProfileForm, EmptyForm, CommentForm
from app.models import User, Comment
from app.main import bp
from app.main.forms import SearchForm


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.comment.data, author=current_user)
        db.session.add(comment)
        db.session.commit()
        flash('Comment posted!')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    comments = current_user.followed_posts().paginate(
        page=page, per_page=current_app.config['COMMENTS_PER_PAGE'],
        error_out=False)
    next_url = url_for('main.index', page=comments.next_num) \
        if comments.has_next else None
    prev_url = url_for('main.index', page=comments.prev_num) \
        if comments.has_prev else None
    return render_template('index.html', title='Home', form=form,
                           comments=comments.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    comments = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['COMMENTS_PER_PAGE'],
        error_out=False)
    next_url = url_for('main.explore', page=comments.next_num) \
        if comments.has_next else None
    prev_url = url_for('main.explore', page=comments.prev_num) \
        if comments.has_prev else None
    return render_template('index.html', title='Explore',
                           comments=comments.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    comments = user.comments.order_by(Comment.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['COMMENTS_PER_PAGE'],
        error_out=False)
    next_url = url_for('main.user', username=user.username,
                       page=comments.next_num) if comments.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=comments.prev_num) if comments.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, comments=comments.items,
                           next_url=next_url, prev_url=prev_url, form=form)
    
    
@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User %(username)s not found.', username=username)
            return redirect(url_for('main.index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User %(username)s not found.', username=username)
            return redirect(url_for('main.index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {}.'.format(username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))
    
@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    comments, total = Comment.search(g.search_form.q.data, page, \
                                    current_app.config['COMMENTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page +1 \
        if total > page * current_app.config['COMMENTS_PER_PAGE'] else None)
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page -1 \
        if page > 1 else None)
    return render_template('search.html', title='Search', comments=comments, \
                            next_url=next_url, prev_url=prev_url)