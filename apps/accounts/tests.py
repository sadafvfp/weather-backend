from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.accounts import login_rate_limit
from backend.apps.device.models import DeviceInfo

User = get_user_model()

LOCMEM = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

CURRENT = "Current-pass-1"
NEW = "Replacement-pass-1"


def client_for(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


@override_settings(CACHES=LOCMEM)
class LoginRateLimitTests(TestCase):
    def test_locks_after_ten_failures(self):
        login_rate_limit.clear("127.0.0.1", "locked.user")
        for _ in range(9):
            status_info = login_rate_limit.record_failures("127.0.0.1", "locked.user")
            self.assertFalse(status_info.locked)
            self.assertEqual(status_info.attempts_until_lockout, 9 - _)

        tenth = login_rate_limit.record_failures("127.0.0.1", "locked.user")
        self.assertTrue(tenth.locked)
        blocked = login_rate_limit.check_blocked("127.0.0.1", "locked.user")
        self.assertIsNotNone(blocked)

    def test_concurrent_failures_reach_lockout(self):
        login_rate_limit.clear("10.0.0.2", "parallel.user")

        def record_once():
            return login_rate_limit.record_failures("10.0.0.2", "parallel.user")

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: record_once(), range(10)))

        self.assertTrue(any(item.locked for item in results))
        self.assertIsNotNone(
            login_rate_limit.check_blocked("10.0.0.2", "parallel.user")
        )

    def test_success_clears_counters(self):
        login_rate_limit.clear("10.0.0.3", "cleared.user")
        login_rate_limit.record_failures("10.0.0.3", "cleared.user")
        login_rate_limit.clear("10.0.0.3", "cleared.user")
        status_info = login_rate_limit.record_failures("10.0.0.3", "cleared.user")
        self.assertEqual(status_info.attempts_until_lockout, 9)


@override_settings(CACHES=LOCMEM)
class AccountsApiTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="root", password=CURRENT
        )
        self.other_superuser = User.objects.create_superuser(
            username="other.root", password=CURRENT
        )
        self.regular = User.objects.create_user(
            username="regular.user", password=CURRENT
        )

    def test_superuser_registers_regular_user_and_superuser(self):
        client = client_for(self.superuser)

        regular = client.post(
            reverse("accounts-register"),
            {
                "username": "New.User",
                "password": NEW,
                "re_password": NEW,
                "is_superuser": False,
            },
            format="json",
        )
        self.assertEqual(regular.status_code, 201)
        self.assertEqual(set(regular.data), {"uuid", "username", "is_superuser"})
        self.assertEqual(regular.data["username"], "new.user")
        self.assertIs(regular.data["is_superuser"], False)
        created = User.objects.get(username="new.user")
        self.assertFalse(created.is_staff)
        self.assertTrue(created.check_password(NEW))

        admin = client.post(
            reverse("accounts-register"),
            {
                "username": "new.admin",
                "password": NEW,
                "re_password": NEW,
                "is_superuser": True,
            },
            format="json",
        )
        self.assertEqual(admin.status_code, 201)
        self.assertIs(admin.data["is_superuser"], True)
        self.assertTrue(User.objects.get(username="new.admin").is_superuser)

    def test_registration_rejects_bad_username_and_password_mismatch(self):
        client = client_for(self.superuser)
        rejected = client.post(
            reverse("accounts-register"),
            {
                "username": "<script>",
                "password": NEW,
                "re_password": NEW,
                "is_superuser": False,
            },
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("username", rejected.data)

        mismatch = client.post(
            reverse("accounts-register"),
            {
                "username": "valid.name",
                "password": NEW,
                "re_password": "Other-pass-1",
                "is_superuser": False,
            },
            format="json",
        )
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn("re_password", mismatch.data)
        self.assertFalse(User.objects.filter(username="valid.name").exists())

    def test_regular_user_cannot_register_or_list_users(self):
        client = client_for(self.regular)
        response = client.post(
            reverse("accounts-register"),
            {
                "username": "someone",
                "password": NEW,
                "re_password": NEW,
                "is_superuser": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        listing = client.get(reverse("accounts-user-list"))
        self.assertEqual(listing.status_code, 403)

    def test_user_list_is_uuid_and_username_only(self):
        response = client_for(self.superuser).get(reverse("accounts-user-list"))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(
            {row["username"] for row in response.data},
            {"root", "other.root", "regular.user"},
        )
        self.assertTrue(
            all(
                set(row) == {"uuid", "username", "is_superuser", "devices"}
                for row in response.data
            )
        )
        self.assertTrue(all(row["devices"] == [] for row in response.data))

    def test_profile_changes_only_username(self):
        client = client_for(self.regular)

        before = client.get(reverse("accounts-profile"))
        self.assertEqual(before.status_code, 200)
        self.assertEqual(set(before.data), {"uuid", "username", "is_superuser"})
        self.assertIs(before.data["is_superuser"], False)
        self.assertEqual(before.data["username"], "regular.user")

        updated = client.put(
            reverse("accounts-profile"),
            {"username": "Renamed.User", "is_superuser": True},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["username"], "renamed.user")

        self.regular.refresh_from_db()
        self.assertEqual(self.regular.username, "renamed.user")
        self.assertFalse(self.regular.is_superuser)

    def test_superuser_adds_and_removes_device_by_slug(self):
        DeviceInfo.objects.bulk_create(
            [
                DeviceInfo(device_id=101, slug="station-one"),
                DeviceInfo(device_id=202, slug="station-two"),
            ]
        )
        first = DeviceInfo.objects.get(slug="station-one")
        second = DeviceInfo.objects.get(slug="station-two")
        client = client_for(self.superuser)
        url = reverse("accounts-user-devices", kwargs={"uuid": self.regular.uuid})

        added = client.post(url, {"slug": first.slug}, format="json")
        self.assertEqual(added.status_code, 200)
        self.assertEqual(added.data["devices"], [first.slug])
        self.assertTrue(first.user.filter(pk=self.regular.pk).exists())

        added_again = client.post(url, {"slug": first.slug}, format="json")
        self.assertEqual(added_again.status_code, 200)
        self.assertEqual(first.user.filter(pk=self.regular.pk).count(), 1)

        both = client.post(url, {"slug": second.slug}, format="json")
        self.assertEqual(both.status_code, 200)
        self.assertEqual(both.data["devices"], sorted([first.slug, second.slug]))

        listing = client.get(reverse("accounts-user-list"))
        row = next(item for item in listing.data if item["username"] == "regular.user")
        self.assertEqual(row["devices"], sorted([first.slug, second.slug]))

        removed = client.delete(url, {"slug": first.slug}, format="json")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.data["devices"], [second.slug])
        self.assertFalse(first.user.filter(pk=self.regular.pk).exists())

        missing = client.post(url, {"slug": "missing-device"}, format="json")
        self.assertEqual(missing.status_code, 400)

        denied = client_for(self.regular).post(
            url, {"slug": second.slug}, format="json"
        )
        self.assertEqual(denied.status_code, 403)

    def test_superuser_updates_another_users_profile(self):
        DeviceInfo.objects.bulk_create(
            [
                DeviceInfo(device_id=301, slug="station-one"),
                DeviceInfo(device_id=302, slug="station-two"),
            ]
        )
        client = client_for(self.superuser)
        url = reverse("accounts-user-detail", kwargs={"uuid": self.regular.uuid})

        updated = client.put(
            url,
            {
                "username": "Renamed.User",
                "is_superuser": True,
                "devices": ["station-two", "station-one"],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            set(updated.data),
            {"uuid", "username", "is_superuser", "devices"},
        )
        self.assertEqual(updated.data["username"], "renamed.user")
        self.assertIs(updated.data["is_superuser"], True)
        self.assertEqual(updated.data["devices"], ["station-one", "station-two"])

        self.regular.refresh_from_db()
        self.assertEqual(self.regular.username, "renamed.user")
        self.assertTrue(self.regular.is_superuser)
        self.assertTrue(self.regular.is_staff)
        self.assertEqual(
            set(self.regular.deviceinfo_set.values_list("slug", flat=True)),
            {"station-one", "station-two"},
        )

        cleared = client.put(
            url,
            {
                "username": "renamed.user",
                "is_superuser": False,
                "devices": [],
            },
            format="json",
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertIs(cleared.data["is_superuser"], False)
        self.assertEqual(cleared.data["devices"], [])
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_superuser)
        self.assertFalse(self.regular.is_staff)
        self.assertFalse(self.regular.deviceinfo_set.exists())

        missing = client.put(
            url,
            {
                "username": "renamed.user",
                "is_superuser": False,
                "devices": ["missing-device"],
            },
            format="json",
        )
        self.assertEqual(missing.status_code, 400)

        own = client.put(
            reverse("accounts-user-detail", kwargs={"uuid": self.superuser.uuid}),
            {
                "username": "root",
                "is_superuser": False,
                "devices": [],
            },
            format="json",
        )
        self.assertEqual(own.status_code, 403)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_superuser)

        denied = client_for(self.regular).put(
            reverse(
                "accounts-user-detail", kwargs={"uuid": self.other_superuser.uuid}
            ),
            {
                "username": "other.root",
                "is_superuser": False,
                "devices": [],
            },
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_change_password_requires_current_and_matching_new_password(self):
        client = client_for(self.regular)
        url = reverse("accounts-change-password")

        wrong = client.post(
            url,
            {
                "current_password": "nope-pass-1",
                "new_password": NEW,
                "re_new_password": NEW,
            },
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.check_password(CURRENT))

        mismatch = client.post(
            url,
            {
                "current_password": CURRENT,
                "new_password": NEW,
                "re_new_password": "Other-pass-1",
            },
            format="json",
        )
        self.assertEqual(mismatch.status_code, 400)

        changed = client.post(
            url,
            {
                "current_password": CURRENT,
                "new_password": NEW,
                "re_new_password": NEW,
            },
            format="json",
        )
        self.assertEqual(changed.status_code, 204)
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.check_password(NEW))

    def test_superuser_resets_others_but_not_self(self):
        client = client_for(self.superuser)

        own = client.post(
            reverse("accounts-reset-password", kwargs={"uuid": self.superuser.uuid}),
            {"new_password": NEW, "re_new_password": NEW},
            format="json",
        )
        self.assertEqual(own.status_code, 403)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.check_password(CURRENT))

        other = client.post(
            reverse(
                "accounts-reset-password", kwargs={"uuid": self.other_superuser.uuid}
            ),
            {"new_password": NEW, "re_new_password": NEW},
            format="json",
        )
        self.assertEqual(other.status_code, 204)
        self.other_superuser.refresh_from_db()
        self.assertTrue(self.other_superuser.check_password(NEW))

        mismatch = client.post(
            reverse("accounts-reset-password", kwargs={"uuid": self.regular.uuid}),
            {"new_password": NEW, "re_new_password": "Other-pass-1"},
            format="json",
        )
        self.assertEqual(mismatch.status_code, 400)
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.check_password(CURRENT))

        member = client.post(
            reverse("accounts-reset-password", kwargs={"uuid": self.regular.uuid}),
            {"new_password": NEW, "re_new_password": NEW},
            format="json",
        )
        self.assertEqual(member.status_code, 204)
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.check_password(NEW))

        denied = client_for(self.regular).post(
            reverse(
                "accounts-reset-password", kwargs={"uuid": self.superuser.uuid}
            ),
            {"new_password": NEW, "re_new_password": NEW},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_superuser_deletes_others_but_not_self(self):
        client = client_for(self.superuser)

        own = client.delete(
            reverse("accounts-user-detail", kwargs={"uuid": self.superuser.uuid})
        )
        self.assertEqual(own.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())

        removed_admin = client.delete(
            reverse(
                "accounts-user-detail", kwargs={"uuid": self.other_superuser.uuid}
            )
        )
        self.assertEqual(removed_admin.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.other_superuser.pk).exists())

        denied = client_for(self.regular).delete(
            reverse("accounts-user-detail", kwargs={"uuid": self.superuser.uuid})
        )
        self.assertEqual(denied.status_code, 403)

        removed_user = client.delete(
            reverse("accounts-user-detail", kwargs={"uuid": self.regular.uuid})
        )
        self.assertEqual(removed_user.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.regular.pk).exists())
