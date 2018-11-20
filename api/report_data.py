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

"""View for report_data endpoint."""

import logging

from flask import jsonify, request

from masu.database.provider_db_accessor import ProviderDBAccessor
from masu.processor.tasks import remove_expired_data, update_summary_tables
from masu.util.blueprint import application_route

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

API_V1_ROUTES = {}

LOG = logging.getLogger(__name__)


@application_route('/report_data/', API_V1_ROUTES, methods=('GET',))
def report_data():
    """Update report summary tables in the database."""
    params = request.args

    provider_uuid = params.get('provider_uuid')

    if provider_uuid is None:
        errmsg = 'provider_uuid is a required parameter.'
        return jsonify({'Error': errmsg}), 400

    provider = ProviderDBAccessor(provider_uuid).get_type()
    schema_name = params.get('schema')
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    if provider is None:
        errmsg = 'Unable to determine provider type.'
        return jsonify({'Error': errmsg}), 400

    if schema_name is None:
        errmsg = 'schema is a required parameter.'
        return jsonify({'Error': errmsg}), 400

    if start_date is None:
        errmsg = 'start_date is a required parameter.'
        return jsonify({'Error': errmsg}), 400

    LOG.info('Calling update_summary_tables async task.')

    if end_date:
        async_result = update_summary_tables.delay(
            schema_name,
            provider,
            provider_uuid,
            start_date,
            end_date
        )
    else:
        async_result = update_summary_tables.delay(schema_name, provider,
                                                   provider_uuid, start_date)

    return jsonify({'Report Data Task ID': str(async_result)})


@application_route('/report_data/', API_V1_ROUTES, methods=('DELETE',))
def remove_report_data():
    """Update report summary tables in the database."""
    params = request.args

    schema_name = params.get('schema')
    provider = params.get('provider')
    provider_id = params.get('provider_id')
    simulate = params.get('simulate')

    if schema_name is None:
        errmsg = 'schema is a required parameter.'
        return jsonify({'Error': errmsg}), 400

    if provider is None:
        errmsg = 'provider is a required parameter.'
        return jsonify({'Error': errmsg}), 400

    if provider_id is None:
        errmsg = 'provider_id is a required parameter.'
        return jsonify({'Error': errmsg}), 400

    if simulate is not None and simulate.lower() not in ('true', 'false'):
        errmsg = 'simulate must be a boolean.'
        return jsonify({'Error': errmsg}), 400

    # pylint: disable=simplifiable-if-statement
    if simulate is not None and simulate.lower() == 'true':
        simulate = True
    else:
        simulate = False

    LOG.info('Calling remove_expired_data async task.')

    async_result = remove_expired_data.delay(schema_name, provider, simulate,
                                             provider_id)

    return jsonify({'Report Data Task ID': str(async_result)})
