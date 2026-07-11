import unittest

from trinohub.security import hash_password, token_hash, verify_password


class SecurityTests(unittest.TestCase):
    def test_password_hash_verification(self):
        stored = hash_password("correct-horse-password")
        self.assertTrue(verify_password("correct-horse-password", stored))
        self.assertFalse(verify_password("wrong-horse-password", stored))

    def test_token_hash_is_stable(self):
        self.assertEqual(token_hash("abc"), token_hash("abc"))
        self.assertNotEqual(token_hash("abc"), token_hash("def"))


if __name__ == "__main__":
    unittest.main()
