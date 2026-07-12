"""
drf-spectacular OpenAPI extensions for the developer_api app.

Registering these extensions suppresses the "could not resolve authenticator"
warnings and ensures the X-API-KEY security scheme is emitted in the schema.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension

class APIKeyAuthenticationExtension(OpenApiAuthenticationExtension):
    """
    Maps developer_api.authentication.APIKeyAuthentication to the OpenAPI
    'apiKey' security scheme (header: X-API-KEY).
    """
    target_class = "developer_api.authentication.APIKeyAuthentication"
    name = "DeveloperAPIKey"                 # name used in the OpenAPI schema
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-KEY",
            "description": (
                "Developer API key. Pass your live or sandbox key in the "
                "`X-API-KEY` request header."
            ),
        }

    def get_security_requirement(self, auto_schema):
        return [{self.name: []}]
