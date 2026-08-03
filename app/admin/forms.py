from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, Optional


class ClassForm(FlaskForm):
    name = StringField("Class name", validators=[DataRequired(), Length(max=64)])
    submit = SubmitField("Save")


class SectionForm(FlaskForm):
    name = StringField("Section name", validators=[DataRequired(), Length(max=32)])
    class_id = SelectField("Class", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Save")


class SubjectForm(FlaskForm):
    name = StringField("Subject name", validators=[DataRequired(), Length(max=64)])
    section_id = SelectField("Class & section", coerce=int, validators=[DataRequired()])
    teacher_id = SelectField("Subject teacher", coerce=int)  # 0 = unassigned
    submit = SubmitField("Save")


class UserForm(FlaskForm):
    login_id = StringField("Login ID", validators=[DataRequired(), Length(max=64)])
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    role = SelectField(
        "Role",
        choices=[
            ("student", "Student"),
            ("class_teacher", "Class Teacher"),
            ("subject_teacher", "Subject Teacher"),
        ],
        validators=[DataRequired()],
    )
    section_id = SelectField("Class & section", coerce=int)  # 0 = none
    password = PasswordField(
        "Initial password",
        validators=[DataRequired(), Length(min=8, message="At least 8 characters.")],
    )
    submit = SubmitField("Create user")


class StudentCSVForm(FlaskForm):
    csv_file = FileField(
        "CSV file",
        validators=[DataRequired(), FileAllowed(["csv"], "CSV files only.")],
    )
    section_id = SelectField("Class & section", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Import students")


class ResetPasswordForm(FlaskForm):
    new_password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=8, message="At least 8 characters.")],
    )
    submit = SubmitField("Reset password")
