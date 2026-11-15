from django.test import SimpleTestCase

from backend.constants.messages import ApiErrors
from backend.exceptions.organization_exception import (
    OrganizationAlreadyExistsException,
    OrganizationDeleteForbiddenException,
    OrganizationNotFoundException,
    OrganizationShortNameAlreadyUsedException,
    OrganizationUpdateForbiddenException,
)


class OrganizationExceptionTests(SimpleTestCase):
    def test_organization_already_exists_formats_short_name(self):
        exception = OrganizationAlreadyExistsException("tech-uni")
        self.assertEqual(
            str(exception), ApiErrors.ORGANIZATION_ALREADY_EXISTS.format("tech-uni")
        )
        self.assertEqual(
            exception.message, ApiErrors.ORGANIZATION_ALREADY_EXISTS.format("tech-uni")
        )

    def test_organization_short_name_already_used_default_message(self):
        exception = OrganizationShortNameAlreadyUsedException()
        self.assertEqual(str(exception), ApiErrors.ORGANIZATION_SHORT_NAME_ALREADY_USED)
        self.assertEqual(
            exception.message, ApiErrors.ORGANIZATION_SHORT_NAME_ALREADY_USED
        )

    def test_organization_short_name_already_used_with_short_name(self):
        exception = OrganizationShortNameAlreadyUsedException(short_name="tech-uni")
        self.assertEqual(str(exception), ApiErrors.ORGANIZATION_SHORT_NAME_ALREADY_USED)
        self.assertEqual(exception.short_name, "tech-uni")

    def test_organization_not_found_with_id(self):
        exception = OrganizationNotFoundException(org_id="123")
        self.assertEqual(
            str(exception), ApiErrors.ORGANIZATION_NOT_FOUND_WITH_ID.format("123")
        )

    def test_organization_not_found_without_id(self):
        exception = OrganizationNotFoundException()
        self.assertEqual(str(exception), ApiErrors.ORGANIZATION_NOT_FOUND)

    def test_organization_update_forbidden(self):
        exception = OrganizationUpdateForbiddenException(org_id="123")
        self.assertEqual(
            str(exception), ApiErrors.ORGANIZATION_UPDATE_NOT_ALLOWED.format("123")
        )

    def test_organization_delete_forbidden(self):
        exception = OrganizationDeleteForbiddenException(org_id="123")
        self.assertEqual(
            str(exception), ApiErrors.ORGANIZATION_DELETE_NOT_ALLOWED.format("123")
        )
