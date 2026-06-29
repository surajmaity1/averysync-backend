from backend.constants.post import PostType, SpaceStatus


posts_data = [
    {
        "id": "28cbefee-136e-4a33-b73e-8533599e5222",
        "title": "BLR Meetup",
        "description": "HSR Layout",
        "type": PostType.SPACE.name,
        "isRecorded": True,
        "status": SpaceStatus.SCHEDULED.name,
        "createdAt": "2026-06-06T14:09:55.934487Z",
        "updatedAt": "2026-06-09T11:31:48.391439Z",
        "createdBy": "9dee2457-9d0b-4bd8-a509-abaaaf618cfa",
    }
]

update_posts_data = [{"title": "BLR meetup", "status": "SCHEDULED"}]
