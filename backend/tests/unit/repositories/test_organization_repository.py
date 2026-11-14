import uuid
from django.test import TestCase

from backend.models.organization import OrganizationModel
from backend.repositories.organization_repository import OrganizationRepository
from backend.tests.factories import create_organization
from backend.tests.fixtures.organization import organizations_data


class OrganizationRepositoryTests(TestCase):
    def test_create_organization_success(self):
        caller_id = str(uuid.uuid4())
        sample = organizations_data[0]
        org = OrganizationModel(
            name=sample["name"],
            short_name=sample["shortName"],
            description=sample["description"],
            type=sample["type"],
            created_by=caller_id,
        )
        created = OrganizationRepository.create(org)

        self.assertIsNotNone(created.id)
        self.assertEqual(created.name, sample["name"])
        self.assertEqual(created.short_name, sample["shortName"])
        self.assertEqual(created.description, sample["description"])
        self.assertEqual(created.type, sample["type"])
        self.assertEqual(created.created_by, caller_id)
        self.assertFalse(created.is_deleted)
        self.assertIsNotNone(created.created_at)

    def test_create_duplicate_short_name_raises_error(self):
        caller_id = str(uuid.uuid4())
        create_organization(
            short_name="duplicate-sn",
            name="Original Org",
            type=OrganizationModel.OrganizationType.COLLEGE,
            created_by=caller_id,
        )

        duplicate = OrganizationModel(
            name="Second Org",
            short_name="duplicate-sn",
            description="Another org",
            type=OrganizationModel.OrganizationType.SCHOOL,
            created_by=caller_id,
        )
        with self.assertRaises(ValueError):
            OrganizationRepository.create(duplicate)

    def test_get_by_short_name(self):
        caller_id = str(uuid.uuid4())
        created = create_organization(
            short_name="unique-sn",
            name="My College",
            type=OrganizationModel.OrganizationType.COLLEGE,
            created_by=caller_id,
        )

        found = OrganizationRepository.get_by_short_name("unique-sn")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, created.id)
        self.assertEqual(found.name, "My College")

        not_found = OrganizationRepository.get_by_short_name("non-existent")
        self.assertIsNone(not_found)

    def test_get_by_short_name_respects_soft_delete(self):
        caller_id = str(uuid.uuid4())
        create_organization(
            short_name="deleted-org",
            name="Deleted Org",
            type=OrganizationModel.OrganizationType.PRIVATE_TUITION,
            is_deleted=True,
            created_by=caller_id,
        )

        found = OrganizationRepository.get_by_short_name("deleted-org")
        self.assertIsNone(found)

    def test_get_by_id(self):
        caller_id = str(uuid.uuid4())
        created = create_organization(
            short_name="id-test",
            name="ID Org",
            type=OrganizationModel.OrganizationType.PRIVATE_SECTOR,
            created_by=caller_id,
        )

        found = OrganizationRepository.get_by_id(str(created.id))
        self.assertIsNotNone(found)
        self.assertEqual(found.id, created.id)

        not_found = OrganizationRepository.get_by_id(str(uuid.uuid4()))
        self.assertIsNone(not_found)

    def test_get_all_returns_only_non_deleted_organizations(self):
        caller_id = str(uuid.uuid4())
        org1 = create_organization(
            short_name="active-org-1",
            name="Active Org 1",
            type=OrganizationModel.OrganizationType.SCHOOL,
            created_by=caller_id,
        )
        org2 = create_organization(
            short_name="active-org-2",
            name="Active Org 2",
            type=OrganizationModel.OrganizationType.COLLEGE,
            created_by=caller_id,
        )
        create_organization(
            short_name="deleted-org",
            name="Deleted Org",
            type=OrganizationModel.OrganizationType.PRIVATE_TUITION,
            is_deleted=True,
            created_by=caller_id,
        )

        results = OrganizationRepository.get_all()

        returned_ids = [org.id for org in results]
        self.assertIn(org1.id, returned_ids)
        self.assertIn(org2.id, returned_ids)
        self.assertEqual(len(results), 2)
        for org in results:
            self.assertFalse(org.is_deleted)

    def test_get_all_returns_empty_list_when_no_active_organizations(self):
        caller_id = str(uuid.uuid4())
        create_organization(
            short_name="deleted-only-org",
            name="Deleted Only Org",
            type=OrganizationModel.OrganizationType.PRIVATE_SECTOR,
            is_deleted=True,
            created_by=caller_id,
        )

        results = OrganizationRepository.get_all()

        self.assertEqual(results, [])

    def test_update_organization_success(self):
        caller_id = str(uuid.uuid4())
        updater_id = str(uuid.uuid4())
        created = create_organization(
            short_name="old-sn",
            name="Old Org Name",
            description="Old description",
            type=OrganizationModel.OrganizationType.SCHOOL,
            created_by=caller_id,
        )

        updated = OrganizationRepository.update(
            org_id=str(created.id),
            update_data={
                "name": "Updated Org Name",
                "short_name": "updated-sn",
                "description": "Updated description",
                "type": OrganizationModel.OrganizationType.COLLEGE,
            },
            updated_by=updater_id,
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.id, created.id)
        self.assertEqual(updated.name, "Updated Org Name")
        self.assertEqual(updated.short_name, "updated-sn")
        self.assertEqual(updated.description, "Updated description")
        self.assertEqual(updated.type, OrganizationModel.OrganizationType.COLLEGE)
        self.assertEqual(updated.created_by, caller_id)
        self.assertEqual(updated.updated_by, updater_id)
        self.assertIsNotNone(updated.updated_at)

    def test_update_organization_not_found_returns_none(self):
        result = OrganizationRepository.update(
            org_id=str(uuid.uuid4()),
            update_data={"name": "Does Not Matter"},
            updated_by=str(uuid.uuid4()),
        )
        self.assertIsNone(result)

    def test_update_organization_soft_deleted_returns_none(self):
        caller_id = str(uuid.uuid4())
        created = create_organization(
            short_name="deleted-update-org",
            name="Deleted Org",
            type=OrganizationModel.OrganizationType.SCHOOL,
            is_deleted=True,
            created_by=caller_id,
        )

        result = OrganizationRepository.update(
            org_id=str(created.id),
            update_data={"name": "New Name"},
            updated_by=caller_id,
        )
        self.assertIsNone(result)
