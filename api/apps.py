#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.apps import AppConfig  # type: ignore


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
