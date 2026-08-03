from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired, MultipleFileField
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class NoteUploadForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField(
        "Description (optional)", validators=[Optional(), Length(max=2000)]
    )
    chapter_id = SelectField("Chapter", coerce=int, validators=[DataRequired()])
    images = MultipleFileField(
        "Note photos",
        validators=[
            FileRequired(message="Choose at least one photo."),
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Only .jpg, .jpeg, .png and .webp images are allowed.",
            ),
        ],
    )
    submit = SubmitField("Upload")


class NoteEditForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField(
        "Description (optional)", validators=[Optional(), Length(max=2000)]
    )
    submit = SubmitField("Save changes")
