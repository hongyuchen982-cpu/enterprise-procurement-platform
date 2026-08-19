import base64
import hashlib
import hmac
import secrets


class InvalidPasswordHashError(ValueError):
    pass


class PasswordHasher:
    algorithm = "scrypt"
    n = 2**14
    r = 8
    p = 1
    salt_bytes = 16
    derived_key_bytes = 32
    max_memory = 64 * 1024 * 1024

    def hash(self, password: str) -> str:
        self.validate_password(password)
        salt = secrets.token_bytes(self.salt_bytes)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self.n,
            r=self.r,
            p=self.p,
            dklen=self.derived_key_bytes,
            maxmem=self.max_memory,
        )
        return "$".join(
            (
                "",
                self.algorithm,
                str(self.n),
                str(self.r),
                str(self.p),
                base64.b64encode(salt).decode("ascii"),
                base64.b64encode(derived).decode("ascii"),
            )
        )

    def verify(self, password: str, encoded: str) -> bool:
        try:
            empty, algorithm, n_value, r_value, p_value, salt_value, digest_value = encoded.split(
                "$"
            )
            if empty or algorithm != self.algorithm:
                raise InvalidPasswordHashError("unsupported password hash")
            n, r, p = int(n_value), int(r_value), int(p_value)
            if not 2**14 <= n <= 2**18 or not 1 <= r <= 16 or not 1 <= p <= 4:
                raise InvalidPasswordHashError("unsafe password hash parameters")
            salt = base64.b64decode(salt_value, validate=True)
            expected = base64.b64decode(digest_value, validate=True)
            if len(salt) != self.salt_bytes or len(expected) != self.derived_key_bytes:
                raise InvalidPasswordHashError("invalid password hash length")
            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=n,
                r=r,
                p=p,
                dklen=self.derived_key_bytes,
                maxmem=self.max_memory,
            )
        except (ValueError, TypeError) as exc:
            if isinstance(exc, InvalidPasswordHashError):
                raise
            raise InvalidPasswordHashError("malformed password hash") from exc
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def validate_password(password: str) -> None:
        if not 12 <= len(password) <= 128:
            raise ValueError("password must contain between 12 and 128 characters")
