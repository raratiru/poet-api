#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
import requests  # type:ignore

from api.business import Communicate


def test_comminucate_session():
    s = requests.Session()
    communication = Communicate(s, "test")
    assert communication.session == s


def test_comminucate_no_session():
    s = "foo"
    with pytest.raises(TypeError):
        Communicate(s, "test")


def test_comminicate_send_default(mocker):
    communicate = mocker.patch("api.business.requests.Session.send")
    s = requests.Session()
    Communicate(s, "test").send("GET", "https://www.google.com")
    assert communicate.is_called()
    assert "Mozilla" in communicate.call_args[0][0].headers["User-Agent"]
    assert communicate.call_args[1]["timeout"] == 5
    assert communicate.call_args[1]["stream"] is False
    assert communicate.call_args[1]["allow_redirects"] is True


def test_comminicate_send(mocker):
    communicate = mocker.patch("api.business.requests.Session.send")
    s = requests.Session()
    Communicate(s, "test", stream=True, allow_redirects=False, timeout=8).send(
        "POST",
        "https://www.google.com",
        headers={"User-Agent": "FOO", "BAR": "ABD"},
        data={"A": 1, "B": 2},
    )
    assert communicate.is_called()
    assert communicate.call_args[0][0].method == "POST"
    assert "FOO" in communicate.call_args[0][0].headers["User-Agent"]
    assert "ABD" in communicate.call_args[0][0].headers["BAR"]
    assert communicate.call_args[1]["timeout"] == 8
    assert communicate.call_args[1]["stream"] is True
    assert communicate.call_args[1]["allow_redirects"] is False


@pytest.mark.only
def test_timeout(mocker):
    communicate = mocker.patch("api.business.requests.Session.send")
    communicate.side_effect = requests.exceptions.ConnectTimeout("Oh Shit")
    sleep = mocker.patch("api.business.sleep", return_value=None)
    # sleep.side_effect = time.sleep(0)
    with pytest.raises(requests.exceptions.ConnectTimeout):
        s = requests.Session()
        Communicate(s, "test", stream=True, allow_redirects=False, timeout=8).send(
            "POST",
            "https://www.google.com",
            headers={"User-Agent": "FOO", "BAR": "ABD"},
            data={"A": 1, "B": 2},
        )
    assert sleep.call_count == 11
