# -*- coding: utf-8 -*-
# Copyright 2012-2013 Rooter Analysis S.L.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.contrib.auth.models import User

from celery import task

from moocng.courses.models import KnowledgeQuantum
from moocng.mongodb import get_db


@task
def on_activity_created_task(activity_created, unit_activity, course_activity):
    db = get_db()
    kq = KnowledgeQuantum.objects.get(id=activity_created['kq_id'])
    kq_type = kq.kq_type()
    update_mark(activity_created)
    # KQ
    data = {
        'viewed': 1
    }
    if kq_type == 'Video':
        data['passed'] = 1
    stats_kq = db.get_collection('stats_kq')
    stats_kq.update(
        {'kq_id': activity_created['kq_id']},
        {'$inc': data},
        safe=True
    )

    # UNIT
    data = {}
    if unit_activity == 1:  # First activity of the unit
        data['started'] = 1
    elif kq.unit.knowledgequantum_set.count() == unit_activity:
        data['completed'] = 1
    # TODO passed
    if data.keys():
        stats_unit = db.get_collection('stats_unit')
        stats_unit.update(
            {'unit_id': kq.unit.id},
            {'$inc': data},
            safe=True
        )

    # COURSE
    course_kqs = KnowledgeQuantum.objects.filter(unit__course__id=activity_created['course_id']).count()
    data = {}
    if course_activity == 1:  # First activity of the course
        data['started'] = 1
    elif course_kqs == course_activity:
        data['completed'] = 1
    # TODO passed
    if data.keys():
        stats_course = db.get_collection('stats_course')
        stats_course.update(
            {'course_id': activity_created['course_id']},
            {'$inc': data},
            safe=True
        )


def update_stats(submitted, data):
    db = get_db()

    # KQ
    # TODO passed
    stats_kq = db.get_collection('stats_kq')
    stats_kq.update(
        {'kq_id': submitted['kq_id']},
        {'$inc': data},
        safe=True
    )

    # UNIT
    data = {}
    # TODO passed
    if data.keys():
        stats_unit = db.get_collection('stats_unit')
        stats_unit.update(
            {'unit_id': submitted['unit_id']},
            {'$inc': data},
            safe=True
        )

    # COURSE
    data = {}
    # TODO passed
    if data.keys():
        stats_course = db.get_collection('stats_course')
        stats_course.update(
            {'course_id': submitted['course_id']},
            {'$inc': data},
            safe=True
        )


def update_kq_mark(db, kq, user, new_mark_kq=None, new_mark_normalized_kq=None):
    from moocng.courses.marks import calculate_kq_mark
    if not new_mark_kq or not new_mark_normalized_kq:
        from moocng.courses.marks_old import calculate_kq_mark_old
        calculate_kq_mark_old(kq, user)
        new_mark_kq, new_mark_normalized_kq, use_in_total = calculate_kq_mark(kq, user)
        if not use_in_total:
            return False
    data_kq = {}
    data_kq['user_id'] = user.pk
    data_kq['course_id'] = kq.unit.course.pk
    data_kq['unit_id'] = kq.unit.pk
    data_kq['kq_id'] = kq.pk

    marks_kq = db.get_collection('marks_kq')
    mark_kq_item = marks_kq.find_one(data_kq)
    if mark_kq_item:
        updated_kq_mark = (new_mark_kq != mark_kq_item['mark'] or
                           new_mark_normalized_kq != mark_kq_item['relative_mark'])
        if updated_kq_mark:
            marks_kq.update(
                data_kq,
                {'$set': {'mark': new_mark_kq,
                          'relative_mark': new_mark_normalized_kq}},
                safe=True
            )
    else:
        updated_kq_mark = True
        data_kq['mark'] = new_mark_kq
        data_kq['relative_mark'] = new_mark_normalized_kq
        marks_kq.insert(data_kq)
    return updated_kq_mark


def update_unit_mark(db, unit, user, new_mark_unit=None, new_mark_normalized_unit=None):
    from moocng.courses.marks import calculate_unit_mark
    if not new_mark_unit or not new_mark_normalized_unit:
        new_mark_unit, new_mark_normalized_unit, use_unit_in_total = calculate_unit_mark(unit, user)
        if not use_unit_in_total:
            return False
    data_unit = {}
    data_unit['user_id'] = user.pk
    data_unit['course_id'] = unit.course.pk
    data_unit['unit_id'] = unit.pk

    marks_unit = db.get_collection('marks_unit')
    mark_unit_item = marks_unit.find_one(data_unit)
    if mark_unit_item:
        updated_unit_mark = (new_mark_unit != mark_unit_item['mark'] or
                             new_mark_normalized_unit != mark_unit_item['relative_mark'])
        if updated_unit_mark:
            marks_unit.update(
                data_unit,
                {'$set': {'mark': new_mark_unit,
                          'relative_mark': new_mark_normalized_unit}},
                safe=True
            )
    else:
        updated_unit_mark = True
        data_unit['mark'] = new_mark_unit
        data_unit['relative_mark'] = new_mark_normalized_unit
        marks_unit.insert(data_unit)
    return updated_unit_mark


def update_course_mark(db, course, user, new_mark_course=None):
    from moocng.courses.marks import calculate_course_mark
    if not new_mark_course:
        new_mark_course, units_info = calculate_course_mark(course, user)
    data_course = {}
    data_course['user_id'] = user.pk
    data_course['course_id'] = course.pk
    marks_course = db.get_collection('marks_course')
    mark_course_item = marks_course.find_one(data_course)
    if mark_course_item:
        updated_course_mark = new_mark_course != mark_course_item['mark']
        if updated_course_mark:
            marks_course.update(
                data_course,
                {'$set': {'mark': new_mark_course}},
                safe=True
            )
    else:
        updated_course_mark = True
        data_course['mark'] = new_mark_course
        marks_course.insert(data_course)
    return updated_course_mark


def update_mark(submitted):
    from moocng.courses.marks import calculate_kq_mark, calculate_unit_mark, calculate_course_mark
    updated_kq_mark = updated_unit_mark = updated_course_mark = False
    kq = KnowledgeQuantum.objects.get(pk=submitted['kq_id'])
    user = User.objects.get(pk=submitted['user_id'])
    mark_kq, mark_normalized_kq, use_kq_in_total = calculate_kq_mark(kq, user)
    if not use_kq_in_total:
        return (updated_kq_mark, updated_unit_mark, updated_course_mark)

    db = get_db()

    # KQ
    updated_kq_mark = update_kq_mark(db, kq, user, mark_kq, mark_normalized_kq)

    # UNIT
    if not updated_kq_mark:
        return (updated_kq_mark, updated_unit_mark, updated_course_mark)

    mark_unit, mark_normalized_unit, use_unit_in_total = calculate_unit_mark(kq.unit, user)
    updated_unit_mark = update_unit_mark(db, kq.unit, user, mark_unit, mark_normalized_unit)

    # COURSE
    if not updated_unit_mark or not use_unit_in_total:
        return (updated_kq_mark, updated_unit_mark, updated_course_mark)
    mark_course, units_info = calculate_course_mark(kq.unit.course, user)
    updated_course_mark = update_course_mark(db, kq.unit.course, user, mark_course)
    return (updated_kq_mark, updated_unit_mark, updated_course_mark)


@task
def on_answer_created_task(answer_created):
    update_mark(answer_created)
    update_stats(answer_created, {'submitted': 1})


@task
def on_answer_updated_task(answer_updated):
    update_mark(answer_updated)
    update_stats(answer_updated, {})


@task
def on_peerreviewsubmission_created_task(submission_created):
    data = {
        'course_id': submission_created['course'],
        'unit_id': submission_created['unit'],
        'kq_id': submission_created['kq'],
    }
    update_mark(data)
    update_stats(data, {'submitted': 1})


@task
def on_peerreviewreview_created_task(review_created, user_reviews):
    data = {
        'course_id': review_created['course'],
        'unit_id': review_created['unit'],
        'kq_id': review_created['kq'],
    }

    inc_reviewers = 0
    if user_reviews == 1:  # First review of this guy
        inc_reviewers = 1
    increment = {
        'reviews': 1,
        'reviewers': inc_reviewers
    }
    update_mark(data)
    update_stats(data, increment)
