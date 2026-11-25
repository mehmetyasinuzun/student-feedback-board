from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import FeedbackForm
from .models import Feedback, course_key, existing_courses


def group_by_course(feedbacks):
    groups = {}
    for feedback in feedbacks:
        groups.setdefault(course_key(feedback.course), []).append(feedback)
    return [{'course': entries[0].course, 'entries': entries} for entries in groups.values()]


def feedback_list(request):
    query = request.GET.get('q', '').replace('\x00', '').strip()[:100]
    feedbacks = Feedback.objects.order_by('-created_at', '-pk')
    if query:
        feedbacks = feedbacks.filter(Q(name__icontains=query) | Q(course__icontains=query))
    context = {'feedbacks': feedbacks, 'course_groups': group_by_course(feedbacks), 'query': query}
    return render(request, 'feedback/feedback_list.html', context)


def feedback_add(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your feedback is on the board.')
            return redirect('feedback_list')
    else:
        course = request.GET.get('course', '').replace('\x00', '').strip()[:100]
        form = FeedbackForm(initial={'course': course} if course else None)
    courses = sorted(existing_courses(), key=str.casefold)
    return render(request, 'feedback/feedback_add.html', {'form': form, 'courses': courses})


@require_http_methods(['GET', 'POST'])
def feedback_delete(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    feedback.delete()
    messages.info(request, 'Feedback removed from the board.')
    return redirect('feedback_list')
