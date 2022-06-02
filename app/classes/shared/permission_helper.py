from enum import Enum


class PermissionHelper:
    @staticmethod
    def both_have_perm(
        permission_mask_a: str, permission_mask_b: str, permission_tested: Enum
    ):
        return PermissionHelper.combine_perm_bool(
            permission_mask_a[permission_tested.value],
            permission_mask_b[permission_tested.value],
        )

    @staticmethod
    def combine_perm(permission_mask_a: str, permission_mask_b: str) -> str:
        return "1" if (permission_mask_a == "1" and permission_mask_b == "1") else "0"

    @staticmethod
    def combine_perm_bool(permission_mask_a: str, permission_mask_b: str) -> bool:
        return permission_mask_a == "1" and permission_mask_b == "1"

    @staticmethod
    def combine_masks(permission_mask_a: str, permission_mask_b: str) -> str:
        both_masks = zip(list(permission_mask_a), list(permission_mask_b))
        return "".join(
            map(lambda x: PermissionHelper.combine_perm(x[0], x[1]), both_masks)
        )
