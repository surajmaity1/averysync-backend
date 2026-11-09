# Agent Guidelines & Development Standards

## 1. Test-Driven Development (TDD) Workflow

Before modifying or adding any application code, **always** follow the Red-Green-Refactor cycle:

1. **🔴 RED**:
   - Write a failing unit test first in `backend/tests/unit/<layer>/` using factories from `backend.tests.factories` that clearly defines the expected behavior or reproduces the bug.
   - Run `python manage.py test <test_path>` and verify that the test fails for the expected reason. Do not write implementation code yet.
2. **🟢 GREEN**:
   - Write the minimal implementation in `backend/` across the appropriate layers (View, Service, Repository, or Serializer) required to make the test pass.
   - Run `python manage.py test <test_path>` and verify that the test passes.
3. **🔵 REFACTOR**:
   - Clean up code, eliminate duplication, adhere to type hints, and ensure proper layer isolation without altering behavior.
   - Ensure the entire test suite remains green and lint/format checks pass (`python manage.py test && ruff check && ruff format --check`).

---

## 2. Python & Django Standards and Best Practices

### Python & Language Standards
- **Modern Python (3.13+)**: Use modern typing constructs: built-in generic types (`list[str]`, `dict[str, CUSTOM_TYPES]`, `X | None`), pattern matching, and explicit type hints on all function signatures.
- **No Hardcoded Strings**: Never hardcode user-facing error messages or status strings. Always import or define constants in `backend.constants.messages` (`ApiErrors`, `ValidationErrors`, `RepositoryError`).
- **Clean Exception Handling**: Raise typed domain exceptions from `backend.exceptions` or return structured `ApiErrorResponse` instances. Never leak unhandled database or system tracebacks to callers.

### Django & Clean Architecture
Follow the strict Clean Layered Architecture (`View` $\rightarrow$ `Service` $\rightarrow$ `Repository` $\rightarrow$ `Model`):

- **Views (`backend/views/`)**:
  - Keep views thin: limit logic to HTTP parameter validation (`validate_uuid`), DRF serializer validation (`.is_valid()`), passing DTOs to Services, and returning DRF `Response`.
  - **Never** execute Django ORM queries directly inside views; always delegate data operations to Services.
  - Rely on `request.user_id` and `request.user_email` supplied by `JWTAuthenticationMiddleware`.
- **Services (`backend/services/`)**:
  - Encapsulate domain logic, permission checks, and multi-repository orchestration.
  - Never accept the Django `request` object; accept only scalar values or Pydantic DTOs.
  - Convert Django ORM models to Pydantic DTOs before returning data to the views.
- **Repositories (`backend/repositories/`)**:
  - Mark all query and mutation methods with `@classmethod`.
  - Wrap write operations in `@transaction.atomic`.
  - Use `.select_for_update()` during concurrent read-modify-write operations to prevent race conditions.
  - Always respect soft deletes by filtering `is_deleted=False` by default.
- **DRF Serializers vs. Pydantic DTOs**:
  - **DRF Serializers (`backend/serializers/`)**: Strictly used for incoming HTTP request validation.
  - **Pydantic DTOs (`backend/dto/`)**: Used for inter-layer data transfer and structured API response schemas (`.model_dump(mode="json")`).
- **Database Models (`backend/models/`)**:
  - Use UUID primary keys: `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
  - Enforce data integrity via PostgreSQL constraints (`UniqueConstraint`, `CheckConstraint`) and partial indexes (`condition=models.Q(...)`).
  - Maintain audit fields (`created_at`, `updated_at`, `created_by`, `updated_by`).

---

## 3. Verification Commands

- **Run Full Test Suite**: `python manage.py test`
- **Run Specific Test File**: `python manage.py test backend.tests.unit.<layer>.<test_file>`
- **Run Single Test Method**: `python manage.py test backend.tests.unit.<layer>.<test_file>.<TestCaseClass>.<test_method>`
- **Lint Check**: `ruff check`
- **Lint Auto-Fix**: `ruff check --fix`
- **Format Check**: `ruff format --check`
- **Format Files**: `ruff format`
- **Check Missing Migrations**: `python manage.py makemigrations --check --dry-run`
