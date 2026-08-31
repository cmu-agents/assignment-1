"""Fast checks for setup helpers that must work before student TODOs."""

from assignment.env import _tls_port_configuration


def test_runtime_port_uses_tls_and_is_not_duplicated():
    encrypted, unencrypted, extra = _tls_port_configuration(
        {
            "encrypted_ports": [8000, 9000],
            "unencrypted_ports": [7000, 8000],
            "cpu": 2,
        },
        8000,
    )

    assert encrypted == [8000, 9000]
    assert unencrypted == [7000]
    assert extra == {"cpu": 2}


def test_runtime_port_is_added_when_no_port_lists_are_given():
    encrypted, unencrypted, extra = _tls_port_configuration({}, 8000)

    assert encrypted == [8000]
    assert unencrypted == []
    assert extra == {}
