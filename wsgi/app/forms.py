from flask_wtf import FlaskForm
from wtforms import TextField, PasswordField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    login_data = TextField('username or email', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
