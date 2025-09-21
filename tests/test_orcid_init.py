from src.core.orcid_client import ORCIDClient


def test_orcid_client_init_without_env():
    client = ORCIDClient(client_id=None, client_secret=None)
    # Should not raise and may not have an access token
    assert hasattr(client, "access_token")
