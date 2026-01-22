import re
import secrets
import string


class OTPGenerator:
    @staticmethod
    def generate_strong_otp() -> str:
        letters = string.ascii_uppercase
        digits = string.digits

        while True:
            sample_letters = [secrets.choice(letters) for _ in range(3)]
            sample_digits = [secrets.choice(digits) for _ in range(4)]
            combined = sample_letters + sample_digits
            secrets.SystemRandom().shuffle(combined)
            otp = "".join(combined)
            if re.search(r"[A-Z]{3,}", otp):
                continue
            if len(set(otp)) < 4:
                continue

            return otp

    @staticmethod
    def validate_otp_format(otp: str) -> bool:
        if len(otp) != 7:
            return False

        letters_count = sum(1 for c in otp if c.isalpha())
        digits_count = sum(1 for c in otp if c.isdigit())

        if letters_count != 3 or digits_count != 4:
            return False

        if re.search(r"[A-Za-z]{3,}", otp):
            return False

        return True
