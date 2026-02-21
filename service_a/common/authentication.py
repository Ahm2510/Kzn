from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication subclass that disables DRF's CSRF enforcement
    for API endpoints.

    In a cross-origin SPA architecture, CSRF protection is provided by:
      - CORS: only allowed origins can make requests
      - SameSite=Lax cookies: prevents cookie attachment from other sites

    CSRF is intentionally disabled for API session auth.

    Protection relies on:
      - SameSite=Lax cookies
      - CORS restrictions
      - Internal service boundaries (frontend talks only to Service A)

    DRF's built-in CSRF check is incompatible with cross-origin session
    auth because Django rotates/masks CSRF tokens on login, making it
    impossible for the frontend to keep the X-CSRFToken header and the
    csrftoken cookie in sync across different origins.

    Django's own CsrfViewMiddleware still runs in the middleware stack
    for non-API views (e.g. admin).
    """

    def enforce_csrf(self, request):
        return
