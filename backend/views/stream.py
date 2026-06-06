import uuid

from rest_framework.request import Request
from rest_framework.views import APIView


class StreamView(APIView):
    def get(self, request: Request, space_id: uuid.UUID):
        # try:
        # check_uuid_validation = check_uuid_validation(uuid_string=str(space_id))

        # if not check_uuid_validation:
        #     raise ValueError(f'')
        pass
