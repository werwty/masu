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
"""Accessor for Provider Authentication from koku database."""


from masu.database.koku_database_access import KokuDBAccess


class ProviderAuthDBAccessor(KokuDBAccess):
    """Class to interact with the koku database for Provider Authentication Data."""

    def __init__(self, auth_id, schema='public'):
        """
        Establish Provider Authentication database connection.

        Args:
            auth_id      (String) the provider authentication unique database id
            schema       (String) database schema (i.e. public or customer tenant value)
        """
        super().__init__(schema)
        self._auth_id = auth_id
        self._provider_auth = self.get_base().classes.api_providerauthentication

    def _get_db_obj_query(self):
        """
        Return the sqlachemy query for the provider auth object.

        Args:
            None
        Returns:
            (sqlalchemy.orm.query.Query): "SELECT public.api_customer.group_ptr_id ..."
        """
        obj = self.get_session().query(self._provider_auth).filter_by(id=self._auth_id)
        return obj

    def get_uuid(self):
        """
        Return the provider uuid.

        Args:
            None
        Returns:
            (String): "UUID v4",
                    example: "edf94475-235e-4b64-ba18-0b81f2de9c9e"
        """
        obj = self._get_db_obj_query().first()
        return obj.uuid

    def get_provider_resource_name(self):
        """
        Return the provider resource name.

        Args:
            None
        Returns:
            (String): "Provider Resource Name.  i.e. AWS: RoleARN",
                    example: "arn:aws:iam::589173575777:role/CostManagement"
        """
        obj = self._get_db_obj_query().first()
        return obj.provider_resource_name
