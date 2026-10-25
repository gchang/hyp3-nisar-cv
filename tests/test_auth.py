"""Earthdata Login: an EDL token in EARTHDATA_TOKEN, otherwise ~/.netrc. No network needed."""

from unittest import mock

import asf_search as asf
import pytest
import requests

from nisar_cv import gcov


@pytest.fixture
def no_netrc(monkeypatch):
    """Fail the test if ~/.netrc is read."""
    read = mock.Mock(side_effect=AssertionError("~/.netrc was read"))
    monkeypatch.setattr(gcov.netrc, "netrc", read)
    return read


@pytest.fixture
def fake_netrc(monkeypatch):
    entry = mock.Mock()
    entry.authenticators.return_value = ("someone", None, "secret")
    monkeypatch.setattr(gcov.netrc, "netrc", mock.Mock(return_value=entry))
    return entry


@pytest.fixture
def fake_session(monkeypatch):
    session = mock.Mock(spec=asf.ASFSession)
    session.auth_with_token.return_value = session
    session.auth_with_creds.return_value = session
    monkeypatch.setattr(gcov.asf, "ASFSession", mock.Mock(return_value=session))
    return session


def test_token_is_used_when_set(monkeypatch, fake_session, no_netrc):
    monkeypatch.setenv("EARTHDATA_TOKEN", "edl-token")

    assert gcov.earthdata_session() is fake_session
    fake_session.auth_with_token.assert_called_once_with("edl-token")
    fake_session.auth_with_creds.assert_not_called()
    no_netrc.assert_not_called()


@pytest.mark.parametrize("value", [None, ""])
def test_netrc_is_used_without_a_token(monkeypatch, fake_session, fake_netrc, value):
    if value is None:
        monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    else:
        monkeypatch.setenv("EARTHDATA_TOKEN", value)

    assert gcov.earthdata_session() is fake_session
    fake_netrc.authenticators.assert_called_once_with("urs.earthdata.nasa.gov")
    fake_session.auth_with_creds.assert_called_once_with("someone", "secret")
    fake_session.auth_with_token.assert_not_called()


def test_rejected_token_raises_and_does_not_fall_back_to_netrc(monkeypatch, no_netrc):
    """A real ASFSession whose token check gets 401 from Earthdata Login and from CMR."""
    rejected = requests.Response()
    rejected.status_code = 401
    monkeypatch.setattr(asf.ASFSession, "post", mock.Mock(return_value=rejected))
    monkeypatch.setattr(asf.ASFSession, "get", mock.Mock(return_value=rejected))
    monkeypatch.setenv("EARTHDATA_TOKEN", "expired-token")

    with pytest.raises(asf.ASFAuthenticationError, match="EARTHDATA_TOKEN") as raised:
        gcov.earthdata_session()
    assert "expired-token" not in str(raised.value)
    no_netrc.assert_not_called()
