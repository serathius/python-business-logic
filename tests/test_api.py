#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_django-application-logic
------------

Tests for `django-application-logic` external API.
"""

import mock
from django.test import TestCase

from application_logic import core, exceptions


def create_validator(should_raise=False, return_value=None):
    @core.validator
    def func(*args, **kwargs):
        if should_raise:
            raise exceptions.ServiceException("Test exception")
        return return_value
    return func


class TestPermissionResult(TestCase):

    def test_permission_result_coercible_to_bool(self):
        result_success = core.ValidationResult(success=True)
        result_failure = core.ValidationResult(success=False)
        self.assertTrue(result_success)
        self.assertFalse(result_failure)

    def test_permission_result_delegates_errors_and_error_code(self):
        exception = exceptions.ServiceException("test", error_code="CODE", errors=object())
        result = core.ValidationResult(success=False, error=exception)
        self.assertEqual(result.error_code, exception.error_code)
        self.assertEqual(result.errors, exception.errors)

    def test_permission_result_repr(self):
        result_success = core.ValidationResult(success=True)
        self.assertEqual(
            repr(result_success),
            u'<PermissionResult success=True error=None>')


class TestValidator(TestCase):

    def test_validator_raises_exception(self):
        func = create_validator(should_raise=True)
        self.assertRaises(exceptions.ServiceException, lambda: func())
        self.assertRaises(exceptions.ServiceException, lambda: func(raise_exception=True))

    def test_passed_validator_returns_success_validation_result(self):
        success_func = create_validator(should_raise=False)
        # when validator passes, raise_exception parameter shouldn't make any difference
        success1 = success_func(raise_exception=False)
        success2 = success_func(raise_exception=True)
        self.assertIsInstance(success1, core.ValidationResult)
        self.assertIsInstance(success2, core.ValidationResult)
        self.assertTrue(success1)
        self.assertTrue(success2)
        self.assertEqual(success1, success2)

    def test_validator_returns_false_permission_when_exception_raised_and_caught(self):
        failure_func = create_validator(should_raise=True)
        failure1 = failure_func(raise_exception=False)
        self.assertIsInstance(failure1, core.ValidationResult)
        self.assertFalse(failure1)

    def test_generic_services_exception_is_raised_when_validator_return_false(self):
        func = create_validator(return_value=False)
        self.assertRaises(core.ServiceException, lambda: func(raise_exception=True))

    def test_returned_failure_contains_exception(self):
        func = create_validator(should_raise=True)
        result = func(raise_exception=False)
        self.assertFalse(result)
        self.assertFalse(result.success)
        self.assertIsInstance(result.error, exceptions.ServiceException)
        # it should be none because exception is not created using ServiceErrors
        self.assertIsNone(result.errors)
        self.assertIsNone(result.error_code)

    def test_raise_exception_argument_is_swallowed(self):
        @core.validator
        def func_without_args():
            return True

        self.assertTrue(func_without_args())
        self.assertTrue(func_without_args(raise_exception=False))
        self.assertTrue(func_without_args(raise_exception=True))


class TestValidatedBy(TestCase):

    def setUp(self):
        self.mock_validator = mock.MagicMock()
        self.validated_func = mock.MagicMock()
        self.decorated_validated_func = core.validated_by(self.mock_validator)(self.validated_func)

    def test_validated_by_swallows_validate_parameter(self):
        self.decorated_validated_func()
        self.validated_func.assert_called_with()

        self.decorated_validated_func(validate=True)
        self.validated_func.assert_called_with()

        self.decorated_validated_func(validate=True)
        self.validated_func.assert_called_with()

    def test_validate_true_calls_validator_with_raise_true(self):
        self.decorated_validated_func(validate=True)
        self.mock_validator.assert_called_with(raise_exception=True)

        self.decorated_validated_func()
        self.mock_validator.assert_called_with(raise_exception=True)

    def test_validate_false_skips_vaidator_entirely(self):
        self.decorated_validated_func(validate=False)
        self.assertFalse(self.mock_validator.called)

    def test_other_parameters_are_passed_to_both_func_and_validator(self):
        self.decorated_validated_func(1, 2, a=3, b=4)
        self.mock_validator.assert_called_with(1, 2, a=3, b=4, raise_exception=True)
        self.validated_func.assert_called_with(1, 2, a=3, b=4)

    def test_exception_from_validator_is_raised(self):
        self.mock_validator.side_effect = exceptions.ServiceException("Fail!")
        self.assertRaises(exceptions.ServiceException, self.mock_validator)
