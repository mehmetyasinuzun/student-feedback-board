from django import forms

from .models import Feedback, course_key, existing_courses, popular_courses

PICKER_LIMIT = 6


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
        picks = popular_courses(PICKER_LIMIT)
        crowded = len(self.courses) > len(picks)
        self.fields['existing_course'].choices = [('', 'Another course' if crowded else 'A new course')] + [(course, course) for course in picks]
        self.fields['course'].required = False
        if crowded:
            self.fields['existing_course'].label = 'Popular courses'
            self.fields['course'].label = 'Or find your course'
            self.fields['course'].help_text = f'Start typing to search all {len(self.courses)} courses on the board, or enter a new one.'
        else:
            self.fields['course'].label = 'Or type a new course'
        wanted = course_key(self.initial.get('course') or '')
        for course in self.courses:
            if wanted and course_key(course) == wanted:
                self.initial['existing_course'] = course if course in picks else ''
                self.initial['course'] = '' if course in picks else course

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
