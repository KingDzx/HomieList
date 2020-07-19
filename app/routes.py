from flask import render_template, redirect, url_for, flash, request, g
from flask_login import current_user, login_user, logout_user, login_required
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, ResetPasswordRequestForm, ResetPasswordForm, SearchForm
from app.models import User, Show, Review
from app.email import send_password_reset_email
from werkzeug.urls import url_parse
import pandas as pd
import os
import ast


@app.route('/')
def index():
    reviews = Review.query.order_by(Review.timestamp.desc()).all()
    return render_template('index.html', reviews=reviews)


@app.route('/anime')
@login_required
def animeList():
    page = request.args.get('page', 1, type=int)
    shows = Show.query.filter_by(type="anime").order_by(Show.title).paginate(page, app.config["SHOWS_PER_PAGE"], False)

    next_url = url_for('animeList', page=shows.next_num) if shows.has_next else None
    prev_url = url_for('animeList', page=shows.prev_num) if shows.has_prev else None
    return render_template('shows.html', title="Anime List", shows=shows.items, next_url=next_url, prev_url=prev_url)


@app.route('/shows')
@login_required
def showList():
    page = request.args.get('page', 1, type=int)
    shows = Show.query.filter_by(type="show").order_by(Show.title).paginate(page, app.config["SHOWS_PER_PAGE"], False)

    next_url = url_for('showList', page=shows.next_num) if shows.has_next else None
    prev_url = url_for('showList', page=shows.prev_num) if shows.has_prev else None
    return render_template('shows.html', title="TV Shows List", shows=shows.items, next_url=next_url, prev_url=prev_url)


@app.route('/movies')
@login_required
def movieList():
    page = request.args.get('page', 1, type=int)
    shows = Show.query.filter_by(type="movie").order_by(Show.title).paginate(page, app.config["SHOWS_PER_PAGE"], False)

    next_url = url_for('movieList', page=shows.next_num) if shows.has_next else None
    prev_url = url_for('movieList', page=shows.prev_num) if shows.has_prev else None
    return render_template('shows.html', title="Movies List", shows=shows.items, next_url=next_url, prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        flash('Successfully Logged In')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.lower(), email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    reviews = Review.query.filter_by(user_id=user.id)
    return render_template('user.html', user=user, reviews=reviews)


@app.route('/show/<id>', methods=['GET', 'POST'])
@login_required
def show(id):
    form = PostForm()
    show = Show.query.filter_by(id=id).first_or_404()
    reviews = Review.query.filter_by(show_id=id)
    if form.validate_on_submit():
        review = Review(body=form.post.data, author=current_user, show=show, rating=form.rating.data)
        db.session.add(review)

        totalRating = show.rating * show.watched
        newTotalRating = totalRating + form.rating.data
        newWatched = show.watched + 1
        newRating = newTotalRating / newWatched

        show.rating = newRating
        show.watched = newWatched
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('show.html', show=show, reviews=reviews, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('user', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/edit_review/<showID>', methods=['GET', 'POST'])
@login_required
def edit_review(showID):
    show = Show.query.filter_by(id=showID).first_or_404()
    review = show.reviews.filter(Review.user_id == current_user.id).one()
    form = PostForm()
    if form.validate_on_submit():
        totalRating = show.rating * show.watched
        newTotalRating = totalRating + form.rating.data - review.rating
        newRating = newTotalRating / show.watched
        show.rating = newRating

        review.body = form.post.data
        review.rating = form.rating.data
        flash('Your changes have been saved.')
        db.session.commit()
        return redirect(url_for('index'))
    elif request.method == 'GET':
        form.rating.data = review.rating
        form.post.data = review.body
    return render_template('edit_review.html', title='Edit Review',
                           form=form, show=show)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route("/loadData")
def loadData():
    dir = os.path.dirname(__file__)
    list = pd.read_csv(dir + "\\data\\animes.csv", header=0, usecols=["title", "synopsis", "genre", "img_url"])
    list_clean = list.drop_duplicates(subset=["title"])

    for anime in list_clean.itertuples(index=False, name=None):
        genres = ast.literal_eval(anime[2])
        genres = [n.strip() for n in genres]

        animeShow = Show(title=anime[0], description=anime[1], genre=genres, image=anime[3], type="anime")
        db.session.add(animeShow)

    db.session.commit()
    return redirect(url_for('index'))


@app.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts, total = Show.search(g.search_form.q.data, page, app.config['SHOWS_PER_PAGE'])
    next_url = url_for('search', q=g.search_form.q.data, page=page + 1) \
        if total > page * app.config['SHOWS_PER_PAGE'] else None
    prev_url = url_for('search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title='Search', shows=posts,
                           next_url=next_url, prev_url=prev_url)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        g.search_form = SearchForm()
