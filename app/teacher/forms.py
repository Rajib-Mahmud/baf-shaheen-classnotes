from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ChapterForm(FlaskForm):
    title = StringField("Chapter title", validators=[DataRequired(), Length(max=160)])
    order_index = IntegerField(
        "Order", validators=[Optional(), NumberRange(min=0)], default=0
    )
    submit = SubmitField("Save")


class CreateStudentForm(FlaskForm):
    login_id = StringField(
        "Login ID (roll-based)", validators=[DataRequired(), Length(max=64)]
    )
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    password = PasswordField(
        "Initial password",
        validators=[DataRequired(), Length(min=8, message="At least 8 characters.")],
    )
    submit = SubmitField("Create student")


class ResetStudentPasswordForm(FlaskForm):
    new_password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=8, message="At least 8 characters.")],
    )
    submit = SubmitField("Reset password")
