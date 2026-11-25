from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import FeedbackForm
from .models import Feedback


def make_feedback(name, course, message='Great course', age_minutes=0):
    feedback = Feedback.objects.create(name=name, course=course, message=message)
    if age_minutes:
        Feedback.objects.filter(pk=feedback.pk).update(created_at=timezone.now() - timedelta(minutes=age_minutes))
    return feedback


class FeedbackModelTests(TestCase):
    def test_fields_and_auto_timestamp(self):
        feedback = make_feedback('Ada', 'CNG 361')
        self.assertIsNotNone(feedback.created_at)
        self.assertEqual(Feedback._meta.get_field('name').max_length, 100)
        self.assertEqual(Feedback._meta.get_field('course').max_length, 100)
        self.assertEqual(Feedback._meta.get_field('message').get_internal_type(), 'TextField')
        self.assertTrue(Feedback._meta.get_field('created_at').auto_now_add)


class FeedbackFormTests(TestCase):
    def test_all_fields_required(self):
        form = FeedbackForm(data={'name': '', 'course': '', 'message': ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors), {'name', 'course', 'message'})

    def test_whitespace_only_is_rejected(self):
        form = FeedbackForm(data={'name': '   ', 'course': 'CNG 361', 'message': 'ok'})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_too_long_name_is_rejected(self):
        form = FeedbackForm(data={'name': 'x' * 101, 'course': 'CNG 361', 'message': 'ok'})
        self.assertFalse(form.is_valid())

    def test_created_at_not_editable(self):
        self.assertNotIn('created_at', FeedbackForm().fields)


class FeedbackListTests(TestCase):
    def test_empty_state(self):
        response = self.client.get(reverse('feedback_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No feedback yet.')
        self.assertTemplateUsed(response, 'feedback/base.html')

    def test_newest_first(self):
        make_feedback('Middle', 'B', age_minutes=10)
        make_feedback('Newest', 'C')
        make_feedback('Oldest', 'A', age_minutes=30)
        response = self.client.get(reverse('feedback_list'))
        names = [feedback.name for feedback in response.context['feedbacks']]
        self.assertEqual(names, ['Newest', 'Middle', 'Oldest'])
        self.assertNotContains(response, 'No feedback yet.')

    def test_same_course_is_grouped_together(self):
        make_feedback('Elif', 'CNG 361 - Web Programming', age_minutes=30)
        make_feedback('Mert', 'MAT 201', age_minutes=20)
        make_feedback('Can', 'cng 361 -  web programming', age_minutes=10)
        response = self.client.get(reverse('feedback_list'))
        groups = [[feedback.name for feedback in group['entries']] for group in response.context['course_groups']]
        self.assertEqual(groups, [['Can', 'Elif'], ['Mert']])
        self.assertContains(response, 'class="course-group', count=2)

    def test_newest_feedback_leads_the_board(self):
        make_feedback('Old', 'MAT 201', age_minutes=30)
        make_feedback('New', 'CNG 361')
        response = self.client.get(reverse('feedback_list'))
        html = response.content.decode()
        self.assertLess(html.index('New'), html.index('Old'))

    def test_card_shows_all_parts(self):
        feedback = make_feedback('Ada Lovelace', 'CNG 361', 'Loved the labs')
        response = self.client.get(reverse('feedback_list'))
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, 'CNG 361')
        self.assertContains(response, 'Loved the labs')
        self.assertContains(response, reverse('feedback_delete', args=[feedback.pk]))
        self.assertContains(response, reverse('feedback_add'))
        self.assertContains(response, 'css/style.css')

    def test_search_by_name_case_insensitive(self):
        make_feedback('Ada Lovelace', 'Math')
        make_feedback('Alan Turing', 'Logic')
        response = self.client.get(reverse('feedback_list'), {'q': 'ADA'})
        self.assertEqual([feedback.name for feedback in response.context['feedbacks']], ['Ada Lovelace'])

    def test_search_by_course_case_insensitive(self):
        make_feedback('Ada Lovelace', 'Math')
        make_feedback('Alan Turing', 'Logic')
        response = self.client.get(reverse('feedback_list'), {'q': 'logi'})
        self.assertEqual([feedback.name for feedback in response.context['feedbacks']], ['Alan Turing'])

    def test_search_matches_middle_of_text(self):
        make_feedback('Ada Lovelace', 'Math')
        response = self.client.get(reverse('feedback_list'), {'q': 'LOVEL'})
        self.assertEqual(len(response.context['feedbacks']), 1)

    def test_blank_query_shows_everything(self):
        make_feedback('Ada', 'Math')
        response = self.client.get(reverse('feedback_list'), {'q': '   '})
        self.assertEqual(response.context['query'], '')
        self.assertEqual(len(response.context['feedbacks']), 1)

    def test_oversized_query_is_handled(self):
        response = self.client.get(reverse('feedback_list'), {'q': 'a' * 60000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['query']), 100)

    def test_card_shows_created_date(self):
        make_feedback('Ada', 'Math')
        response = self.client.get(reverse('feedback_list'))
        self.assertContains(response, '<time datetime=')
        self.assertContains(response, str(timezone.localtime().year))

    def test_search_does_not_match_message(self):
        make_feedback('Ada', 'Math', message='zebra')
        response = self.client.get(reverse('feedback_list'), {'q': 'zebra'})
        self.assertEqual(len(response.context['feedbacks']), 0)
        self.assertContains(response, 'No feedback yet.')

    def test_query_stays_in_search_box(self):
        response = self.client.get(reverse('feedback_list'), {'q': 'web prog'})
        self.assertEqual(response.context['query'], 'web prog')
        self.assertContains(response, 'value="web prog"')

    def test_query_is_escaped(self):
        response = self.client.get(reverse('feedback_list'), {'q': '"><i>italic</i>'})
        self.assertNotContains(response, '<i>italic</i>')

    def test_stored_content_is_escaped(self):
        make_feedback('<b>bold</b>', 'CNG', '<i>italic</i>')
        response = self.client.get(reverse('feedback_list'))
        self.assertNotContains(response, '<i>italic</i>')
        self.assertNotContains(response, '<b>bold</b>')


class FeedbackAddTests(TestCase):
    def test_get_shows_empty_form(self):
        response = self.client.get(reverse('feedback_add'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_bound)
        self.assertTemplateUsed(response, 'feedback/base.html')
        self.assertContains(response, 'Back to list')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_valid_post_saves_and_redirects(self):
        response = self.client.post(reverse('feedback_add'), {'name': 'Ada', 'course': 'CNG 361', 'message': 'Nice'})
        self.assertRedirects(response, reverse('feedback_list'))
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertEqual(Feedback.objects.get().name, 'Ada')

    def test_valid_post_shows_notice(self):
        data = {'name': 'Ada', 'course': 'CNG 361', 'message': 'Nice'}
        response = self.client.post(reverse('feedback_add'), data, follow=True)
        self.assertContains(response, 'Your feedback is on the board.')

    def test_invalid_post_rerenders_with_errors(self):
        response = self.client.post(reverse('feedback_add'), {'name': 'Ada', 'course': '', 'message': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Feedback.objects.count(), 0)
        self.assertContains(response, 'This field is required.', count=2)
        self.assertContains(response, 'value="Ada"')

    def test_post_without_csrf_token_is_rejected(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('feedback_add'), {'name': 'Ada', 'course': 'CNG', 'message': 'x'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Feedback.objects.count(), 0)


class CourseSuggestionTests(TestCase):
    def test_no_picker_on_an_empty_board(self):
        response = self.client.get(reverse('feedback_add'))
        self.assertNotIn('existing_course', response.context['form'].fields)
        self.assertTrue(response.context['form'].fields['course'].required)

    def test_picker_lists_each_course_once(self):
        make_feedback('Elif', 'Web Programming')
        make_feedback('Can', 'web  programming')
        make_feedback('Mert', 'Data Structures')
        response = self.client.get(reverse('feedback_add'))
        choices = [value for value, label in response.context['form'].fields['existing_course'].choices]
        self.assertEqual(sorted(choices), ['', 'Data Structures', 'web  programming'])
        self.assertContains(response, 'type="radio"', count=3)
        self.assertContains(response, '<datalist id="course-options">')

    def test_crowded_board_offers_only_popular_courses(self):
        for number in range(60):
            make_feedback('Student', f'Course {number:02d}')
        make_feedback('Fan', 'Course 30')
        make_feedback('Fan', 'Course 30')
        response = self.client.get(reverse('feedback_add'))
        form = response.context['form']
        choices = [value for value, label in form.fields['existing_course'].choices]
        self.assertEqual(len(choices), 7)
        self.assertEqual(choices[1], 'Course 30')
        self.assertEqual(len(response.context['courses']), 60)
        self.assertContains(response, 'type="radio"', count=7)
        self.assertContains(response, '<option value=', count=60)
        self.assertContains(response, 'search all 60 courses')

    def test_less_popular_course_is_prefilled_as_text(self):
        for number in range(10):
            make_feedback('Student', f'Course {number:02d}', age_minutes=number)
        form = self.client.get(reverse('feedback_add'), {'course': 'course 09'}).context['form']
        self.assertEqual(form['course'].value(), 'Course 09')
        self.assertFalse(form['existing_course'].value())

    def test_board_gets_a_course_index_when_there_are_many_courses(self):
        for number in range(3):
            make_feedback('Student', f'Course {number}')
        self.assertNotContains(self.client.get(reverse('feedback_list')), 'class="course-index"')
        make_feedback('Student', 'Course 3')
        response = self.client.get(reverse('feedback_list'))
        self.assertContains(response, 'class="course-index"')
        self.assertContains(response, 'href="#course-4"')
        self.assertContains(response, 'id="course-4"')

    def test_plain_get_is_an_empty_form(self):
        make_feedback('Elif', 'Web Programming')
        form = self.client.get(reverse('feedback_add')).context['form']
        self.assertFalse(form.is_bound)
        self.assertFalse(form['course'].value())
        self.assertFalse(form['existing_course'].value())

    def test_picked_course_is_saved(self):
        make_feedback('Elif', 'Web Programming')
        data = {'name': 'Can', 'existing_course': 'Web Programming', 'course': '', 'message': 'ok'}
        response = self.client.post(reverse('feedback_add'), data)
        self.assertRedirects(response, reverse('feedback_list'))
        self.assertEqual(Feedback.objects.get(name='Can').course, 'Web Programming')

    def test_typed_course_wins_over_pick(self):
        make_feedback('Elif', 'Web Programming')
        data = {'name': 'Can', 'existing_course': 'Web Programming', 'course': 'Databases', 'message': 'ok'}
        self.client.post(reverse('feedback_add'), data)
        self.assertEqual(Feedback.objects.get(name='Can').course, 'Databases')

    def test_course_still_required_when_nothing_picked_or_typed(self):
        make_feedback('Elif', 'Web Programming')
        data = {'name': 'Can', 'existing_course': '', 'course': '  ', 'message': 'ok'}
        response = self.client.post(reverse('feedback_add'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['form'].errors), ['course'])
        self.assertContains(response, 'This field is required.', count=1)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_unknown_pick_is_rejected(self):
        make_feedback('Elif', 'Web Programming')
        data = {'name': 'Can', 'existing_course': 'Hacked', 'course': '', 'message': 'ok'}
        response = self.client.post(reverse('feedback_add'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_add_here_link_preselects_the_course(self):
        make_feedback('Elif', 'Web Programming')
        listing = self.client.get(reverse('feedback_list'))
        self.assertContains(listing, reverse('feedback_add') + '?course=Web%20Programming')
        form = self.client.get(reverse('feedback_add'), {'course': 'web programming'}).context['form']
        self.assertEqual(form['existing_course'].value(), 'Web Programming')

    def test_prefill_is_escaped(self):
        response = self.client.get(reverse('feedback_add'), {'course': '"><i>italic</i>'})
        self.assertNotContains(response, '<i>italic</i>')

    def test_existing_spelling_is_reused(self):
        make_feedback('Elif', 'Web Programming')
        data = {'name': 'Can', 'course': '  web   PROGRAMMING ', 'message': 'ok'}
        self.client.post(reverse('feedback_add'), data)
        self.assertEqual(Feedback.objects.get(name='Can').course, 'Web Programming')


class FeedbackDeleteTests(TestCase):
    def test_delete_removes_and_redirects(self):
        first = make_feedback('First', 'A')
        remove = make_feedback('Remove', 'B')
        last = make_feedback('Last', 'C')
        response = self.client.get(reverse('feedback_delete', args=[remove.pk]))
        self.assertRedirects(response, reverse('feedback_list'))
        self.assertEqual(list(Feedback.objects.order_by('pk')), [first, last])

    def test_head_request_does_not_delete(self):
        feedback = make_feedback('Keep', 'A')
        response = self.client.head(reverse('feedback_delete', args=[feedback.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Feedback.objects.filter(pk=feedback.pk).exists())

    def test_delete_shows_notice(self):
        feedback = make_feedback('Gone', 'A')
        response = self.client.get(reverse('feedback_delete', args=[feedback.pk]), follow=True)
        self.assertContains(response, 'Feedback removed from the board.')

    def test_delete_missing_returns_404(self):
        response = self.client.get(reverse('feedback_delete', args=[999]))
        self.assertEqual(response.status_code, 404)


class UrlTests(TestCase):
    def test_named_urls(self):
        self.assertEqual(reverse('feedback_list'), '/')
        self.assertEqual(reverse('feedback_add'), '/add/')
        self.assertEqual(reverse('feedback_delete', args=[7]), '/delete/7/')
