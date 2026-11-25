from django.db import models


def course_key(course):
    return ' '.join(course.split()).casefold()


class Feedback(models.Model):
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.course}"


def existing_courses():
    courses = {}
    for course in Feedback.objects.order_by('-created_at', '-pk').values_list('course', flat=True):
        courses.setdefault(course_key(course), course)
    return list(courses.values())


def popular_courses(limit):
    names = {}
    counts = {}
    for course in Feedback.objects.order_by('-created_at', '-pk').values_list('course', flat=True):
        key = course_key(course)
        names.setdefault(key, course)
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(names, key=lambda key: -counts[key])
    return [names[key] for key in ranked[:limit]]
