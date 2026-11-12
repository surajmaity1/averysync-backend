from backend.constants.messages import ApiErrors


class OrganizationAlreadyExistsException(Exception):
    def __init__(
        self,
        short_name: str,
        message: str = ApiErrors.ORGANIZATION_ALREADY_EXISTS,
    ):
        self.message = message.format(short_name)
        super().__init__(self.message)


class OrganizationNotFoundException(Exception):
    def __init__(
        self,
        org_id: str | None = None,
        message: str = ApiErrors.ORGANIZATION_NOT_FOUND_WITH_ID,
    ):
        if org_id:
            self.message = message.format(org_id)
        else:
            self.message = ApiErrors.ORGANIZATION_NOT_FOUND
        super().__init__(self.message)
