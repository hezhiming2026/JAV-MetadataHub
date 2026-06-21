def test_package_can_be_imported() -> None:
    import jav_metadatahub

    assert jav_metadatahub.__version__ == "0.1.0"


def test_cli_can_be_imported() -> None:
    from jav_metadatahub.cli import app

    assert app is not None
