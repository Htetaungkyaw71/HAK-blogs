from flask import Flask, render_template, redirect, url_for, flash,abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,CreateUserForm,CreateLoginForm, CreateComment
from flask_gravatar import Gravatar
from functools import wraps
import smtplib
import datetime
import os
from dotenv import load_dotenv

load_dotenv()


your_email = os.getenv("EMAIL")
your_password = os.getenv("PASSWORD")


now = datetime.datetime.now()
year = now.year





app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

db.create_all()

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")

db.create_all()

class Comment(db.Model):
    __tablename__ = "comments"
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    blog_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=True)

db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated :
            return redirect('error')
        elif current_user.id != 1 :
            return redirect('error')
        return f(*args, **kwargs)
    return decorated_function



@app.route('/')
def get_all_posts():
    login = current_user.is_authenticated
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, login=login,year=year)


@app.route('/register',methods=["GET","POST"])
def register():
    login = current_user.is_authenticated
    form = CreateUserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash("email has already exists login instand")
            return redirect(url_for('login'))
        else:
            hash_password = generate_password_hash(form.password.data, salt_length=8)
            new = User(
                name=form.name.data,
                email=form.email.data,
                password=hash_password,
            )
            db.session.add(new)
            db.session.commit()
            login_user(new)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=form,login=login,year=year)


@app.route('/login',methods=["GET","POST"])
def login():
    login = current_user.is_authenticated
    form = CreateLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password,form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("password is incorrect")
                return redirect(url_for('login'))
        else:
            flash("email doesn't exist")
            return redirect(url_for('login'))
    return render_template("login.html",form=form,login=login,year=year)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["GET","POST"])
def show_post(post_id):
    login = current_user.is_authenticated
    requested_post = BlogPost.query.get(post_id)
    form = CreateComment()
    if form.validate_on_submit():
        if not login:
            flash("you need to login first to comment")
            return redirect(url_for('login'))
        new = Comment(
            comment_author= current_user,
            parent_post=requested_post,
            text=form.comment_text.data
        )
        db.session.add(new)
        db.session.commit()
    return render_template("post.html", post=requested_post,login=login,year=year,form=form)


@app.route("/about")
def about():
    login = current_user.is_authenticated
    return render_template("about.html",login=login)


@app.route("/contact")
def contact():
    login = current_user.is_authenticated
    return render_template("contact.html",login=login,year=year)



@app.route("/new-post",methods=["GET","POST"])
@admin_required
def add_new_post():
    login = current_user.is_authenticated
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,login=login,year=year)


@app.route("/edit-post/<int:post_id>")
@admin_required
def edit_post(post_id):
    login = current_user.is_authenticated
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, login=login,is_edit=True,year=year)


@app.route("/delete/<int:post_id>")
@admin_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))







@app.route("/error")
def error():
    login = current_user.is_authenticated
    return render_template("error.html",login=login,year=year)


if __name__ == "__main__":
    app.run(debug=True)


