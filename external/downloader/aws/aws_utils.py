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
"""AWS STS functions."""

import boto3
from dateutil.relativedelta import relativedelta


def get_assume_role_session(arn, session='MasuSession'):
    """
    Assume a Role and obtain session credentials for the given role.

    Args:
        arn (String): Amazon Resource Name
        session (String): A session name

    Usage :
        session = get_assume_role_session(session='ExampleSessionName',
                                          arn='arn:aws:iam::012345678901:role/my-role')
        client = session.client('sqs')

    See: https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html
    """
    client = boto3.client('sts')
    response = client.assume_role(RoleArn=arn, RoleSessionName=session)
    return boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken'])


def month_date_range(for_date_time):
    """
    Get a formatted date range string for the given date.

    Date range is aligned on the first day of the current
    month and ends on the first day of the next month from the
    specified date.

    Args:
        for_date_time (DateTime): The starting datetime object

    Returns:
        (String): "YYYYMMDD-YYYYMMDD", example: "19701101-19701201"

    """
    start_month = for_date_time.replace(day=1, second=1, microsecond=1)
    end_month = start_month + relativedelta(months=+1)
    timeformat = '%Y%m%d'
    return '{}-{}'.format(start_month.strftime(timeformat),
                          end_month.strftime(timeformat))


def establish_aws_session(role_arn, session_name='MasuSession'):
    """
    Establish an AWS connection session.

    Args:
        role_arn     (String) RoleARN for AWS session
        session_name (String) Name of the session

    Returns:
        (Session): AWS Session handle

    """
    session = get_assume_role_session(
        arn=role_arn,
        session=session_name)
    return session


def get_cur_report_definitions(role_arn, session=None):
    """
    Get Cost Usage Reports associated with a given RoleARN.

    Args:
        role_arn     (String) RoleARN for AWS session

    Returns:
        ([String]): List of Cost Usage Report Definitions

    """
    if not session:
        session = establish_aws_session(role_arn)
    cur_client = session.client('cur')
    defs = cur_client.describe_report_definitions()
    report_defs = defs.get('ReportDefinitions', [])
    return report_defs


def get_cur_report_names_in_bucket(role_arn, s3_bucket, session=None):
    """
    Get Cost Usage Reports associated with a given RoleARN.

    Args:
        role_arn     (String) RoleARN for AWS session

    Returns:
        ([String]): List of Cost Usage Report Names

    """
    report_defs = get_cur_report_definitions(role_arn, session)
    report_names = []
    for report in report_defs:
        if s3_bucket == report['S3Bucket']:
            report_names.append(report['ReportName'])
    return report_names
