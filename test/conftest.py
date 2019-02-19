import pytest


@pytest.fixture(scope="session")
def Main(julia):
    """ pytest fixture for providing a Julia `Main` name space. """
    from julia import Main

    return Main
