from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from github import Github
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ['key']
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db = SQLAlchemy(app)
login_manager = LoginManager(app)
gh = Github(os.environ['token'])


class User(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(20), unique=True, nullable=False)
  password = db.Column(db.String(60), nullable=False)


with app.app_context():
  db.create_all()


class LoginForm(FlaskForm):
  username = StringField("Username", validators=[DataRequired()])
  password = PasswordField("Password", validators=[DataRequired()])
  submit = SubmitField("Login")


class RegisterForm(FlaskForm):
  username = StringField("Username", validators=[DataRequired()])
  password = PasswordField("Password", validators=[DataRequired()])
  submit = SubmitField("Register")


@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))


@app.route("/")
def home():
  return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
  form = LoginForm()
  if form.validate_on_submit():
    user = User.query.filter_by(username=form.username.data).first()
    if user and user.password == form.password.data:
      login_user(user)
      return redirect(url_for("dashboard"))
    else:
      flash("Invalid username or password", "danger")
  return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
  form = RegisterForm()
  if form.validate_on_submit():
    if user_exists := User.query.filter_by(
        username=form.username.data).first():
      flash("Username already exists, please choose another one", "danger")
    else:
      new_user = User(username=form.username.data, password=form.password.data)
      db.session.add(new_user)
      db.session.commit()
      flash("Registration successful. You can now log in.", "success")
      return redirect(url_for("login"))
  return render_template("register.html", form=form)


@app.route("/dashboard")
@login_required
def dashboard():
  user_folder = f"users/{current_user.username}"
  repo = gh.get_repo("TotoB12/drive-data")
  try:
    files = repo.get_contents(user_folder)
  except Exception as e:
    if e.status != 404:
      raise e
    repo.create_file(f"{user_folder}/.gitkeep", "Create user folder", "")
    files = []
  return render_template("dashboard.html", files=files)


@app.route("/upload", methods=["POST"])
@login_required
def upload():
  if file := request.files["file"]:
    if file.content_length <= 100 * 1024 * 1024:
      user_folder = f"users/{current_user.username}"
      repo = gh.get_repo("TotoB12/drive-data")
      file_path = f"{user_folder}/{file.filename}"
      try:
        repo.get_contents(file_path)
        flash(f"File '{file.filename}' already exists.", "danger")
      except Exception as e:
        if e.status != 404:
          raise e
        repo.create_file(file_path, f"Uploaded {file.filename}", file.read())
        flash(f"File '{file.filename}' uploaded successfully.", "success")
    else:
      flash("File size exceeds 100 MB limit.", "danger")
  else:
    flash("No file selected.", "danger")
  return redirect(url_for("dashboard"))


@app.route("/download/<path:filename>", methods=["GET"])
@login_required
def download(filename):
  user_folder = f"users/{current_user.username}"
  repo = gh.get_repo("TotoB12/drive-data")
  file = repo.get_contents(f"{user_folder}/{filename}")
  raw_url = file.download_url

  return redirect(raw_url)


@app.route("/logout")
@login_required
def logout():
  logout_user()
  flash("Logged out successfully.", "info")
  return redirect(url_for("home"))


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
