#
# Copyright 2018 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Asynchronous tasks."""

# pylint: disable=too-many-arguments, too-many-function-args
# disabled module-wide due to current state of task signature.
# we expect this situation to be temporary as we iterate on these details.


import os
from datetime import timedelta

from celery.utils.log import get_task_logger

from masu.celery import celery
from masu.database.report_stats_db_accessor import ReportStatsDBAccessor
from masu.external.date_accessor import DateAccessor
from masu.processor._tasks.download import _get_report_files
from masu.processor._tasks.process import _process_report_file
from masu.processor._tasks.remove_expired import _remove_expired_data

LOG = get_task_logger(__name__)


@celery.task(name='masu.processor.tasks.get_report_files', queue_name='download')
def get_report_files(customer_name,
                     authentication,
                     billing_source,
                     provider_type,
                     schema_name,
                     report_name=None):
    """
    Task to download a Report.

    Note that report_name will be not optional once Koku can specify
    what report we should download.

    FIXME: A 2 hour timeout is arbitrarily set for in progress processing requests.
    Once we know a realistic processing time for the largest CUR file in production
    this value can be adjusted or made configurable.

    Args:
        customer_name     (String): Name of the customer owning the cost usage report.
        authentication    (String): Credential needed to access cost usage report
                                    in the backend provider.
        billing_source    (String): Location of the cost usage report in the backend provider.
        provider_type     (String): Koku defined provider type string.  Example: Amazon = 'AWS'
        schema_name       (String): Name of the DB schema
        report_name       (String): Name of the cost usage report to download.

    Returns:
        files (List) List of filenames with full local path.
               Example: ['/var/tmp/masu/my-report-name/aws/my-report-file.csv',
                         '/var/tmp/masu/other-report-name/aws/other-report-file.csv']

    """
    reports = _get_report_files(customer_name,
                                authentication,
                                billing_source,
                                provider_type,
                                report_name)

    # initiate chained async task
    LOG.info('Reports to be processed: %s', str(reports))
    for report_dict in reports:
        file_name = os.path.basename(report_dict.get('file'))
        stats = ReportStatsDBAccessor(file_name)
        started_date = stats.get_last_started_datetime()
        completed_date = stats.get_last_completed_datetime()
        stats.close_session()

        # Skip processing if already in progress.
        if started_date and not completed_date:
            expired_start_date = started_date + timedelta(hours=2)
            if DateAccessor().today() < expired_start_date:
                LOG.info('Skipping processing task for %s since it was started at: %s.',
                         file_name, str(started_date))
                continue

        # Skip processing if complete.
        if started_date and completed_date:
            LOG.info('Skipping processing task for %s. Started on: %s and completed on: %s.',
                     file_name, str(started_date), str(completed_date))
            continue

        request = {'schema_name': schema_name,
                   'report_path': report_dict.get('file'),
                   'compression': report_dict.get('compression')}
        result = process_report_file.delay(**request)
        LOG.info('Processing task queued - File: %s, Task ID: %s',
                 report_dict.get('file'),
                 str(result))


@celery.task(name='masu.processor.tasks.process_report_file', queue_name='process')
def process_report_file(schema_name, report_path, compression):
    """
    Task to process a Report.

    Args:
        schema_name (String) db schema name
        report_path (String) path to downloaded reports
        compression (String) 'PLAIN' or 'GZIP'

    Returns:
        None

    """
    _process_report_file(schema_name, report_path, compression)


@celery.task(name='masu.processor.tasks.remove_expired_data', queue_name='remove_expired')
def remove_expired_data(schema_name, simulate):
    """
    Remove expired report data.

    Args:
        schema_name (String) db schema name
        simulate    (Boolean) Simulate report data removal

    Returns:
        None

    """
    _remove_expired_data(schema_name, simulate)
