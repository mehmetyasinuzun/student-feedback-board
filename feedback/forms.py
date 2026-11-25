from django import forms

from .models import Feedback, course_key, existing_courses


class FeedbackForm(forms.ModelForm):
    existing_course = forms.ChoiceField(label='Pick your course', required=False, widget=forms.RadioSelect)

    class Meta:
        model = Feedback
        fields = ['name', 'existing_course', 'course', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Elif Kaya', 'autocomplete': 'name', 'autofocus': True}),
            'course': forms.TextInput(attrs={'placeholder': 'e.g. Web Programming', 'list': 'course-options', 'autocomplete': 'off'}),
            'message': forms.Textarea(attrs={'rows': 6, 'placeholder': 'What worked, what did not, what would you change?'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.courses = existing_courses()
        if not self.courses:
            del self.fields['existing_course']
            return
        self.fields['existing_course'].choices = [('', 'A new course')] + [(course, course) for course in self.courses]
        self.fields['course'].label = 'Or type a new course'
        self.fields['course'].required = False
        wanted = course_key(self.initial.get('course') or '')
        for course in self.courses:
            if wanted and course_key(course) == wanted:
                self.initial['existing_course'] = course
                self.initial['course'] = ''

    def clean_course(self):
        course = ' '.join(self.cleaned_data['course'].split())
        for existing in self.courses:
            if course_key(existing) == course_key(course):
                return existing
        return course

    def clean(self):
        cleaned_data = super().clean()
        if 'course' in cleaned_data and not cleaned_data['course']:
            picked = cleaned_data.get('existing_course')
            if picked:
                cleaned_data['course'] = picked
            else:
                self.add_error('course', self.fields['course'].error_messages['required'])
        return cleaned_data
