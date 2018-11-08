#
# Copyright 2018 Red Hat, Inc.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Database accessor for OCP report data."""
# pylint: skip-file

import logging
import pkgutil
import uuid

from masu.config import Config
from masu.database import OCP_REPORT_TABLE_MAP
from masu.database.report_db_accessor_base import ReportDBAccessorBase

LOG = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class OCPReportDBAccessor(ReportDBAccessorBase):
    """Class to interact with customer reporting tables."""

    def __init__(self, schema, column_map):
        """Establish the database connection.

        Args:
            schema (str): The customer schema to associate with
            column_map (dict): A mapping of report columns to database columns
        """
        super().__init__(schema, column_map)
        self._datetime_format = Config.OCP_DATETIME_STR_FORMAT
        self.column_map = column_map

    def get_current_usage_report(self):
        """Get the most recent usage report object."""
        table_name = OCP_REPORT_TABLE_MAP['report']
        interval_start = getattr(
            getattr(self.report_schema, table_name),
            'interval_start'
        )

        return self._get_db_obj_query(table_name)\
            .order_by(interval_start.desc())\
            .first()

    def get_current_usage_period(self):
        """Get the most recent usage report period object."""
        table_name = OCP_REPORT_TABLE_MAP['report_period']
        report_period_start = getattr(
            getattr(self.report_schema, table_name),
            'report_period_start'
        )

        return self._get_db_obj_query(table_name)\
            .order_by(report_period_start.desc())\
            .first()

    def get_usage_periods_by_date(self, start_date):
        """Return all report period entries for the specified start date."""
        table_name = OCP_REPORT_TABLE_MAP['report_period']
        return self._get_db_obj_query(table_name)\
            .filter_by(report_period_start=start_date)\
            .all()

    def get_usage_period_before_date(self, date):
        """Get the usage report period objects before provided date."""
        table_name = OCP_REPORT_TABLE_MAP['report_period']
        report_start = getattr(
            getattr(self.report_schema, table_name),
            'report_period_start'
        )
        base_query = self._get_db_obj_query(table_name)
        usage_period_query = base_query.filter(report_start <= date)
        return usage_period_query

    # pylint: disable=invalid-name
    def get_usage_period_query_by_provider(self, provider_id):
        """Return all report periods for the specified provider."""
        table_name = OCP_REPORT_TABLE_MAP['report_period']
        return self._get_db_obj_query(table_name)\
            .filter_by(provider_id=provider_id)

    def get_lineitem_query_for_reportid(self, query_report_id):
        """Get the usage report line item for a report id query."""
        table_name = OCP_REPORT_TABLE_MAP['line_item']
        report_id = getattr(
            getattr(self.report_schema, table_name),
            'id'
        )
        base_query = self._get_db_obj_query(table_name)
        line_item_query = base_query.filter(query_report_id == report_id)
        return line_item_query

    def get_item_query_report_period_id(self, report_period_id):
        """Get the usage report line item for a report id query."""
        table_name = OCP_REPORT_TABLE_MAP['line_item']
        period_id = getattr(
            getattr(self.report_schema, table_name),
            'report_period_id'
        )
        base_query = self._get_db_obj_query(table_name)
        line_item_query = base_query.filter(report_period_id == period_id)
        return line_item_query

    def get_report_query_report_period_id(self, report_period_id):
        """Get the usage report line item for a report id query."""
        table_name = OCP_REPORT_TABLE_MAP['report']
        period_id = getattr(
            getattr(self.report_schema, table_name),
            'report_period_id'
        )
        base_query = self._get_db_obj_query(table_name)
        usage_report_query = base_query.filter(report_period_id == period_id)
        return usage_report_query

    def get_report_periods(self):
        """Get all usage period objects."""
        table_name = OCP_REPORT_TABLE_MAP['report_period']

        columns = ['id', 'cluster_id', 'report_period_start']
        periods = self._get_db_obj_query(table_name, columns=columns).all()

        return {(p.cluster_id, p.report_period_start): p.id
                for p in periods}

    def get_reports(self):
        """Make a mapping of reports by time."""
        table_name = OCP_REPORT_TABLE_MAP['report']

        reports = self._get_db_obj_query(table_name).all()

        return {(entry.report_period_id, entry.interval_start.strftime(self._datetime_format)): entry.id
                for entry in reports}

    # pylint: disable=duplicate-code
    def populate_line_item_daily_table(self, start_date, end_date):
        """Populate the daily aggregate of line items table.

        Args:
            start_date (datetime.date) The date to start populating the table.
            end_date (datetime.date) The date to end on.

        Returns
            (None)

        """
        table_name = OCP_REPORT_TABLE_MAP['line_item_daily']

        daily_sql = pkgutil.get_data(
            'masu.database',
            'sql/reporting_ocpusagelineitem_daily.sql'
        )
        daily_sql = daily_sql.decode('utf-8').format(
            uuid=str(uuid.uuid4()).replace('-', '_'),
            start_date=start_date,
            end_date=end_date
        )
        LOG.info(f'Updating %s from %s to %s.',
                 table_name, start_date, end_date)
        self._cursor.execute(daily_sql)
        self._pg2_conn.commit()
        self._vacuum_table(table_name)
        LOG.info('Finished updating %s.', table_name)

    def populate_cpu_charge(self, cpu_rate):
        """Populate the daily aggregate of line items table.

        Args:
            cpu_rate (Float) CPU-hour rate.

        Returns
            (None)

        """
        table_name = OCP_REPORT_TABLE_MAP['line_item_daily_summary']

        daily_charge_sql = pkgutil.get_data(
            'masu.database',
            'sql/reporting_ocpusagelineitem_daily_cpu_charge.sql'
        )
        daily_charge_sql = daily_charge_sql.decode('utf-8').format(
            cpu_rate=str(cpu_rate)
        )
        LOG.info(f'Updating %s with cpu_rate: %s.',
                 table_name, cpu_rate)
        self._cursor.execute(daily_charge_sql)
        self._pg2_conn.commit()
        self._vacuum_table(table_name)
        LOG.info('Finished updating %s.', table_name)

    def populate_memory_charge(self, mem_rate):
        """Populate the daily aggregate of line items table.

        Args:
            mem_rate (Float) Memory-hour rate.

        Returns
            (None)

        """
        table_name = OCP_REPORT_TABLE_MAP['line_item_daily_summary']

        daily_charge_sql = pkgutil.get_data(
            'masu.database',
            'sql/reporting_ocp_usage_lineitem_daily_mem_charge.sql'
        )
        daily_charge_sql = daily_charge_sql.decode('utf-8').format(
            mem_rate=str(mem_rate)
        )
        LOG.info(f'Updating %s with mem_rate: %s.',
                 table_name, mem_rate)
        self._cursor.execute(daily_charge_sql)
        self._pg2_conn.commit()
        self._vacuum_table(table_name)
        LOG.info('Finished updating %s.', table_name)

    def populate_line_item_daily_summary_table(self, start_date, end_date):
        """Populate the daily aggregate of line items table.

        Args:
            start_date (datetime.date) The date to start populating the table.
            end_date (datetime.date) The date to end on.

        Returns
            (None)

        """
        table_name = OCP_REPORT_TABLE_MAP['line_item_daily_summary']

        summary_sql = pkgutil.get_data(
            'masu.database',
            'sql/reporting_ocpusagelineitem_daily_summary.sql'
        )
        summary_sql = summary_sql.decode('utf-8').format(
            uuid=str(uuid.uuid4()).replace('-', '_'),
            start_date=start_date,
            end_date=end_date
        )
        LOG.info(f'Updating %s from %s to %s.',
                 table_name, start_date, end_date)
        self._cursor.execute(summary_sql)
        self._pg2_conn.commit()
        self._vacuum_table(table_name)
        LOG.info('Finished updating %s.', table_name)

    # pylint: disable=invalid-name,duplicate-code
    def populate_line_item_aggregate_table(self):
        """Populate the line item aggregated totals data table."""
        table_name = OCP_REPORT_TABLE_MAP['line_item_aggregates']

        agg_sql = pkgutil.get_data(
            'masu.database',
            f'sql/reporting_ocpusagelineitem_aggregates.sql'
        )
        agg_sql = agg_sql.decode('utf-8').format(
            uuid=str(uuid.uuid4()).replace('-', '_')
        )
        LOG.info('Updating %s.', table_name)
        self._cursor.execute(agg_sql)
        self._pg2_conn.commit()
        self._vacuum_table(table_name)
        LOG.info(f'Finished updating %s.', table_name)
